from __future__ import annotations
from dataclasses import dataclass, field

import os
import math
import json
import copy
import shutil
import subprocess

import PyOpenColorIO as OCIO

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

from . import (
    operators as ops,
    utils
)


class format_dict(dict):
    def __missing__(self, key): 
        #return key.join("{}")
        return ""


@dataclass
class EffectsFileProcessor:
    input_file: str = None
    color_ops: list = field(default_factory = lambda: list([]))
    repo_ops: list = field(default_factory = lambda: list([]))
    _class_search_key = "class"
    _index_search_key = "subTrackIndex"

    def __post_init__(self):
        if self.input_file:
            self.load(self.input_file)
            self.process()

    def _load_append(self, file: str = None) -> None:
        if file:
            self.input_file = file
        if self.input_file:
            with open(self.input_file, "r") as f:
                _ops = json.load(f)
        else:
            raise ValueError(
                f"Couldn't open file at location {self.input_file}"
            )
        ocio_nodes = []
        repo_nodes = []
        if isinstance(_ops, dict):
            for k, v in _ops.items():
                if isinstance(v, dict) and v[self._class_search_key] in ops.get_OCIO_class_names():
                    ocio_nodes.append(v)
                elif isinstance(v, dict) and v[self._class_search_key] in ops.get_repo_class_names():
                    repo_nodes.append(v)
                else:
                    continue
        elif isinstance(_ops, list):
            for i in _ops:
                if isinstance(i, dict) and i[self._class_search_key] in ops.get_OCIO_class_names():
                    ocio_nodes.append(i)
                elif isinstance(i, dict) and i[self._class_search_key] in ops.get_repo_class_names():
                    repo_nodes.append(i)
                else:
                    continue
        ocio_nodes = sorted(ocio_nodes, key=lambda d: d[self._index_search_key])
        repo_nodes = sorted(repo_nodes, key=lambda d: d[self._index_search_key])
        for c in ocio_nodes:
            self.color_ops.append(dict(ops.get_valid_keys(c, ops.get_valid_parameters())))
        for r in repo_nodes:
            self.repo_ops.append(dict(ops.get_valid_keys(r, ops.get_valid_parameters())))
        for i, r in enumerate(self.repo_ops):
            if not isinstance(r["scale"], list):
                self.repo_ops[i]["scale"] = [r["scale"], r["scale"]]

    def clear_data(self) -> None:
        self.input_file = ""
        self.color_ops = []
        self.repo_ops = []

    def load(self, file: str = None) -> None:
        self.clear_data()
        self._load_append(file)

    def process(self) -> None:
        for i, x in enumerate(copy.deepcopy(self.color_ops)):
            for k, v in x.items():
                if k in ops.CLASS_PARAMS_MAPPING:
                    self.color_ops[i][ops.CLASS_PARAMS_MAPPING[k]] = v
                    self.color_ops[i].pop(k)
            self.color_ops[i].pop(self._index_search_key)
            try:
                class_name = getattr(ops, x[self._class_search_key].replace("OCIO", ""))
            except:
                class_name = getattr(ops, f"{x[self._class_search_key].replace('OCIO', '')}Transform")
            valid_class_parameters = ops.get_valid_class_parameters(class_name)
            for k, v in copy.deepcopy(self.color_ops[i]).items():
                if k not in valid_class_parameters:
                    self.color_ops[i].pop(k)
        for i, x in enumerate(copy.deepcopy(self.repo_ops)):
            for k, v in x.items():
                if k in ops.CLASS_PARAMS_MAPPING:
                    self.repo_ops[i][ops.CLASS_PARAMS_MAPPING[k]] = v
                    self.repo_ops[i].pop(k)
            self.repo_ops[i].pop(self._index_search_key)
            try:
                class_name = getattr(ops, f"Repo{x[self._class_search_key]}")
            except:
                class_name = getattr(ops, f"Repo{x[self._class_search_key]}")
            valid_class_parameters = ops.get_valid_class_parameters(class_name)
            for k, v in copy.deepcopy(self.repo_ops[i]).items():
                if k not in valid_class_parameters:
                    self.repo_ops[i].pop(k)

    def get_data(self) -> dict:
        return dict({
            "color": self.color_ops,
            "repo": self.repo_ops
        })
   

@dataclass
class ColorTransformProcessor:
    transform_list: list = field(default_factory = lambda: list([]))
    context: str = "lablib_context"
    working_space: str = "ACES - ACEScg"
    config_path: str = None
    temp_config_path: str = None
    active_views: str = None
    ocio_environment: dict = field(default_factory = lambda: dict({}))
    _class_search_key: str = "class"

    def add_transform(self, *args) -> None:
        arglist = []
        for a in args:
            if isinstance(a, list):
                for b in a:
                    arglist.append(b)
            else:
                arglist.append(a)
        for obj in arglist:
            if isinstance(obj, ops.get_OCIO_classes()):
                self.transform_list.append(obj)
            else:
                try:
                    class_name = getattr(ops, obj.get(self._class_search_key).replace("OCIO", ""))
                except:
                    class_name = getattr(ops, f"{obj.get(self._class_search_key).replace('OCIO', '')}Transform")
                obj.pop(self._class_search_key)
                self.transform_list.append(class_name(**obj))

    def set_active_views(self, views: str | list[str] | tuple[str]) -> None:
        if isinstance(views, str):
            self.active_views = views
        elif isinstance(views, list) or isinstance(views, tuple):
            self.active_views = ",".join(views)
        else:
            raise ValueError("Views argument need to be either \
                             a comma separated string, a list or a tuple.")
            
    def clear_transforms(self) -> None:
        self.transform_list = []
    
    def create_ocio_config(self,
                           source: str = None,
                           dest: str = None) -> str:
        if not source:
            if not self.config_path:
                ocio_env = os.environ.get("OCIO", None)
                if not ocio_env:
                    raise ValueError("Missing source config path!")
                else:
                    self.config_path = ocio_env
            else:
                source = self.config_path        
        if not dest:
            if not self.temp_config_path:
                raise ValueError("Missing destination config path!")
            else:
                dest = self.temp_config_path
        config = OCIO.Config.CreateFromFile(source)
        search_paths = []
        ocio_transforms_list = []
        view_name = f"{self.context}"
        for obj in self.transform_list:
            class_name = getattr(OCIO, obj.__class__.__name__)
            props = vars(obj)
            if props.get("direction"):
                props["direction"] = OCIO.TransformDirection.TRANSFORM_DIR_INVERSE
            else:
                props["direction"] = OCIO.TransformDirection.TRANSFORM_DIR_FORWARD
            ocio_transforms_list.append(class_name(**props))
        for p in config.getSearchPaths():
            search_paths.append(
                os.path.join(
                    os.path.dirname(os.path.abspath(source)),
                    p
                ).replace("\\", "/")
            )
        for ctd in ocio_transforms_list:
            try:
                ctd_source = ctd.getSrc()
                if ctd_source:
                    search_paths.append(
                        os.path.dirname(ctd_source)
                    )
            except:
                continue
        search_paths = list(dict.fromkeys(
            [x for x in search_paths.copy() if x != ""])
        )
        for i, sp in enumerate(search_paths):
            search_paths[i] = f"  - {sp}"
        group = OCIO.GroupTransform(ocio_transforms_list)
        look = OCIO.Look(
            name = view_name,
            processSpace = self.working_space,
            transform = group
        )
        config.addLook(look)
        config.addDisplayView(
            "ACES",
            view_name,
            self.working_space,
            looks = view_name
        )
        if not self.active_views:
            config.setActiveViews(
                f"{view_name},{config.getActiveViews()}"
            )
        else:
            config.setActiveViews(
                f"{view_name},{self.active_views}"
            )
        for k, v in self.ocio_environment.items():
            config.addEnvironmentVar(k, v)
        config.setDescription(str(self.ocio_environment))
        config.validate()
        config_lines = config.serialize().splitlines()
        for i, l in enumerate(config_lines.copy()):
            if l.find("search_path") >= 0:
                config_lines[i] = "search_path:"
                for idx, sp in enumerate(search_paths):
                    config_lines.insert(i+idx+1, sp)
                config_lines.insert(i+len(search_paths)+1, "")
                break
        final_config = "\n".join(config_lines)
        with open(dest, "w") as f:
            f.write(final_config)
        return dest

    def compute_color_cmd(self,
                          colorconfig: str = None,
                          from_colorspace: str = None,
                          to_colorspace: str = None,
                          context: str = None) -> list:
        if not colorconfig:
            colorconfig = self.temp_config_path
        if not from_colorspace:
            from_colorspace = self.working_space
        if not to_colorspace:
            to_colorspace = self.working_space
        if not context:
            context = self.context
        cmd = ["--colorconfig"]
        cmd.append(colorconfig)
        cmd.append(f"--ociolook:from={from_colorspace}:to={to_colorspace}")
        cmd.append(context)
        return cmd
    

@dataclass
class RepoTransformProcessor:
    transform_list: list[ops.RepoTransform] = field(default_factory= lambda: list([]))
    source_width: int = None
    source_height: int = None
    dest_width: int = None
    dest_height: int = None
    _raw_matrix: list[list[float]] = field(default_factory= lambda: list([list([])]))
    _class_search_key = "class"

    def get_raw_matrix(self) -> list[list[float]]:
        return self._raw_matrix

    def add_transform(self, *args) -> None:
        arglist = []
        for a in args:
            if isinstance(a, list):
                for b in a:
                    arglist.append(b)
            else:
                arglist.append(a)
        for obj in arglist:
            if isinstance(obj, ops.RepoTransform):
                self.transform_list.append(obj)
            else:
                obj.pop(self._class_search_key)
                self.transform_list.append(
                    ops.RepoTransform(**obj)
                )

    def clear_transforms(self) -> None:
        self.transform_list = []

    def zero_matrix(self) -> list[list[float]]:
        return [[0.0 for i in range(3)] for j in range(3)]

    def identity_matrix(self) -> list[list[float]]:
        return self.translate_matrix([0.0, 0.0])

    def translate_matrix(self,
                         t: list[float]) -> list[list[float]]:
        return [
            [1.0, 0.0, t[0]],
            [0.0, 1.0, t[1]],
            [0.0, 0.0, 1.0]
        ]

    def rotate_matrix(self,
                      r: float) -> list[list[float]]:
        rad = math.radians(r)
        cos = math.cos(rad)
        sin = math.sin(rad)
        return [
            [cos, -sin, 0.0],
            [sin, cos, 0.0],
            [0.0, 0.0, 1.0]
        ]

    def scale_matrix(self,
                     s: list[float]) -> list[list[float]]:
        return [
            [s[0], 0.0, 0.0],
            [0.0, s[1], 0.0],
            [0.0, 0.0, 1.0]
        ]

    def mirror_matrix(self,
                      x: bool = False) -> list[list[float]]:
        dir = [1.0, -1.0] if not x else [-1.0, 1.0]
        return self.scale_matrix(dir)

    def mult_matrix(self,
                    m1: list[list[float]],
                    m2: list[list[float]]) -> list[list[float]]:
        return [[sum(a * b for a, b in zip(m1_row, m2_col)) for m2_col in zip(*m2)] for m1_row in m1]

    def mult_matrix_vector(self,
                           m: list[list[float]],
                           v: list[float]) -> list[float]:
        result = [0.0, 0.0, 0.0]
        for i in range(len(m)):
            for j in range(len(v)):
                result[i] += m[i][j] * v[j]
        return result

    def flip_matrix(self,
                    w: float) -> list[list[float]]:
        result = self.identity_matrix()
        chain = [
            self.translate_matrix([w, 0.0]),
            self.mirror_matrix(x = True)
        ]
        for m in chain:
            result = self.mult_matrix(result, m)
        return result

    def flop_matrix(self,
                    h: float) -> list[list[float]]:
        result = self.identity_matrix()
        chain = [
            self.translate_matrix([0.0, h]),
            self.mirror_matrix()
        ]
        for m in chain:
            result = self.mult_matrix(result, m)
        return result

    def transpose_matrix(self,
                         m: list[list[float]]) -> list[list[float]]:
        res = self.identity_matrix()
        for i in range(len(m)):
            for j in range(len(m[0])):
                res[i][j] = m[j][i]
        return res

    def matrix_to_44(self,
                     m: list[list[float]]) -> list[list[float]]:
        result = m
        result[0].insert(2, 0.0)
        result[1].insert(2, 0.0)
        result[2].insert(2, 0.0)
        result.insert(2, [0.0, 0.0, 1.0, 0.0])
        return result

    def matrix_to_list(self,
                       m: list[list[float]]) -> list[float]:
        result = []
        for i in m:
            for j in i:
                result.append(str(j))
        return result

    def matrix_to_csv(self,
                      m: list[list[float]]) -> str:
        l = []
        for i in m:
            for k in i:
                l.append(str(k))
        return ",".join(l)

    def matrix_to_cornerpin(self,
                            m: list[list[float]],
                            origin_upperleft: bool = True) -> list:
        w = self.source_width
        h = self.source_height
        cornerpin = []
        if origin_upperleft:
            corners = [[0, h, 1], [w, h, 1], [0, 0, 1], [w, 0, 1]]
        else:
            corners = [[0, 0, 1], [w, 0, 1], [0, h, 1], [w, h, 1]]
        transformed_corners = [self.mult_matrix_vector(m, corner) for corner in corners]
        transformed_corners = [[corner[0] / corner[2], corner[1] / corner[2]] for corner in transformed_corners]
        for i, corner in enumerate(transformed_corners):
            x, y = corner
            cornerpin.extend([x,y])
        return cornerpin

    def get_matrix(self,
                   t: list[float],
                   r: float,
                   s: list[float],
                   c: list[float]) -> list[list[float]]:
        c_inv = [-c[0], -c[1]]
        center = self.translate_matrix(c)
        center_inv = self.translate_matrix(c_inv)
        translate = self.translate_matrix(t)
        rotate = self.rotate_matrix(r)
        scale = self.scale_matrix(s)
        result = self.mult_matrix(translate, center)
        result = self.mult_matrix(result, scale)
        result = self.mult_matrix(result, rotate)
        result = self.mult_matrix(result, center_inv)
        return result  

    def get_matrix_chained(self,
                           flip: bool = False,
                           flop: bool = True,
                           reverse_chain: bool = True) -> str:
        chain = []
        tlist = self.transform_list
        if reverse_chain:
            tlist.reverse()
        if flip:
            chain.append(self.flip_matrix(self.source_width))
        if flop:
            chain.append(self.flop_matrix(self.source_height))
        for xform in tlist:
            chain.append(
                self.get_matrix(
                    xform.translate,
                    xform.rotate,
                    xform.scale,
                    xform.center)
            )
        if flop:
            chain.append(self.flop_matrix(self.source_height))
        if flip:
            chain.append(self.flip_matrix(self.source_width))
        result = self.identity_matrix()
        for m in chain:
            result = self.mult_matrix(result, m)
        self._raw_matrix = result
        return result

    def get_cornerpin_data(self,
                           matrix: list[list[float]]) -> list:
        cp = self.matrix_to_cornerpin(
            matrix,
            self.source_width,
            self.source_height,
            origin_upperleft=False
        )
        return cp

    def compute_repotransform_cmd(self) -> list:

        if not self.source_width:
            raise ValueError(f"Missing source width!")
        if not self.source_height:
            raise ValueError(f"Missing source height!")
        if not self.dest_width:
            raise ValueError(f"Missing destination width!")
        if not self.dest_height:
            raise ValueError(f"Missing destination height!")
        
        matrix = self.get_matrix_chained()
        matrix_tr = self.transpose_matrix(matrix)
        warp_cmd = self.matrix_to_csv(matrix_tr)
        
        src_aspect = self.source_width /self.source_height
        dest_aspect = self.dest_width / self.dest_height
        
        fitted_width = self.source_width
        fitted_height = self.source_height

        x_offset = 0
        y_offset = 0

        if src_aspect > dest_aspect:
            fitted_height = int(self.source_width / dest_aspect)
            y_offset = int((fitted_height-self.source_height)/2)
        elif src_aspect < dest_aspect:
            fitted_width = int(self.source_height * dest_aspect)
            x_offset = int((fitted_width-self.source_width)/2)

        cmd = []

        cmd.extend([
            "--warp:filter=cubic:recompute_roi=1",
            warp_cmd,
            "--crop",
            f"{fitted_width}x{fitted_height}-{x_offset}-{y_offset}",
            "--fullsize",
            f"{fitted_width}x{fitted_height}-{x_offset}-{y_offset}",
            #"--fullpixels",
            "--resize",
            f"{self.dest_width}x{self.dest_height}"
        ])

        return cmd


@dataclass
class SlateProcessor():
    slates: list = field(default_factory=lambda: list([]))
    thumbs: list = field(default_factory=lambda: list([]))
    charts: list = field(default_factory=lambda: list([]))
    data: dict = field(default_factory = lambda: dict({}))
    width: int = None
    height: int = None
    staging_dir: str = None
    slate_template_path: str = None
    _staged_template_path: str = None
    _driver: webdriver.Chrome = None
    _thumb_class_name = "thumb"
    _chart_class_name = "chart"

    def __post_init__(self):
        options = Options()
        options.add_argument("--headless=new")
        options.add_argument("--disable-gpu")
        options.add_argument("--hide-scrollbars")
        options.add_argument("--show-capture=no")
        options.add_experimental_option("excludeSwitches", ["enable-logging"])
        self._driver = webdriver.Chrome(options=options)

    def set_viewport_size(self, width: int, height: int) -> None:
        window_size = self._driver.execute_script("""
            return [window.outerWidth - window.innerWidth + arguments[0],
            window.outerHeight - window.innerHeight + arguments[1]];
            """, width, height)
        self._driver.set_window_size(*window_size)
    
    def format_slate(self,
                     data: dict = None,
                     slate_template_path: str = None,
                     staging_dir: str = None) -> str:

        if not data:
            if not self.data:
                raise ValueError("Missing subst_data to format template!")
            else:
                data = self.data
        
        if not slate_template_path:
            if not self.slate_template_path:
                raise ValueError("Missing slate template path!")
            else:
                slate_template_path = self.slate_template_path
        
        if not staging_dir:
            if not self.staging_dir:
                raise ValueError("Missing staging dir!")
            else:
                staging_dir = self.staging_dir
        
        slate_staging_path = os.path.join(
            self.staging_dir,
            os.path.basename(
                os.path.dirname(slate_template_path)
            ),
            os.path.basename(slate_template_path)
        )

        with open(slate_template_path, "r") as p:
            formatted_slate = p.read().format_map(format_dict(data))
        
        dest_dir = os.path.dirname(slate_staging_path)

        if os.path.isdir(dest_dir):
            self.clean_staged_files(dest_dir)
        
        shutil.copytree(
            src=os.path.dirname(slate_template_path),
            dst=dest_dir
        )

        with open(slate_staging_path, "w") as p:
            p.write(formatted_slate)

        self._staged_template_path = slate_staging_path

        return formatted_slate

    def render_slate(self,
                     output_path: str,
                     slate_template_path: str = None,
                     width: int = None,
                     height: int = None) -> dict:
        
        if not output_path:
            raise ValueError("No output path specified!")

        if not slate_template_path:
            if not self._staged_template_path:
                raise ValueError("Missing formatted template!")
            else:
                slate_template_path = self._staged_template_path
        
        if not width:
            if not self.width:
                raise ValueError("Missing width!")
            else:
                width = self.width

        if not height:
            if not self.height:
                raise ValueError("Missing height!")
            else:
                height = self.height

        self._driver.get(slate_template_path)
        self.set_viewport_size(width, height)
        
        self.slates.append(
            utils.ImageInfo(
                filename = output_path,
                data_width = width,
                data_height = height,
                data_origin_x = 0,
                data_origin_y = 0
            )
        )

        thumbs = self._driver.find_elements(By.CLASS_NAME, self._thumb_class_name)
        for t in thumbs:
            src_path = t.get_attribute("src")
            if src_path:
                aspect_ratio = self.width/self.height
                thumb_height = int(t.size["width"]/aspect_ratio)
                self._driver.execute_script("""
                    var element = arguments[0];
                    element.style.height = '{}px'
                    """.format(thumb_height), t)
                self.thumbs.append(
                    utils.ImageInfo(
                        filename = src_path.replace("file:///", ""),
                        data_origin_x = t.location["x"],
                        data_origin_y = t.location["y"],
                        data_width = t.size["width"],
                        data_height = thumb_height
                    )
                )
        for t in thumbs:
            self._driver.execute_script("""
                var element = arguments[0];
                element.parentNode.removeChild(element);
                """, t)
        
        charts = self._driver.find_elements(By.CLASS_NAME, self._chart_class_name)
        for c in charts:
            src_path = c.get_attribute("src")
            if src_path:
                self.charts.append(
                    utils.ImageInfo(
                        filename = src_path.replace("file:///", ""),
                        data_origin_x = c.location["x"],
                        data_origin_y = c.location["y"],
                        data_width = c.size["width"],
                        data_height = c.size["height"]
                    )
                )
        for c in charts:
            self._driver.execute_script("""
                var element = arguments[0];
                element.parentNode.removeChild(element);
                """, c)

        self._driver.save_screenshot(output_path)

        self._driver.quit()

        label = "base"

        cmd = ["oiiotool"]
        cmd.extend([
            "-i", output_path,
            "--colorconvert", "sRGB", "linear",
            "--ch", "R,G,B,A=1.0",
            "--label", "slate",
            "--create", f"{self.width}x{self.height}", "4",
            "--ch", "R,G,B,A=0.0",
            "--label", label
        ])
        for i, t in enumerate(self.thumbs):
            if i > 0:
                label = "thumbs"
            cmd.extend([
                "-i", t.filename,
                "--ch", "R,G,B,A=1.0",
                "--resample", f"{t.data_width}x{t.data_height}+{t.data_origin_x}+{t.data_origin_y}",
                label, "--over",
                "--label", "thumbs"
            ])
        cmd.extend([
            "-o", "results/thumb.exr",
            "slate", "--over",
            "-o", "results/test.exr",
            "--colorconvert", "linear", "sRGB",
            "--ch", "R,G,B"
            "-o", os.path.join(os.path.dirname(output_path), "test.png")
        ])

        subprocess.run(cmd)

        return {
            "slates": self.slates,
            "thumbs": self.thumbs,
            "charts": self.charts
        }

    def clean_staged_files(self, slate_template_path: str = None) -> None:
        if not slate_template_path:
            if not self._staged_template_path:
                raise ValueError("Can't determine staged slate path!")
            else:
                slate_template_path = self._staged_template_path
        shutil.rmtree(os.path.dirname(slate_template_path))