from __future__ import annotations

from typing import Any, Union
from dataclasses import dataclass, field
from pathlib import Path

import json
import inspect
import os
import uuid
import copy
import shutil

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

import PyOpenColorIO as OCIO

from . import (
    utils,
    operators as ops
)


@dataclass
class EffectsFileProcessor:
    src: str
    _color_ops: list = field(default_factory = lambda: list([]))
    _repo_ops: list = field(default_factory = lambda: list([]))
    _class_search_key: str = "class"
    _index_search_key: str = "subTrackIndex"
    _data_search_key: str = "node"
    _valid_attrs: tuple = field(default_factory = lambda: tuple((
        "in_colorspace",
        "out_colorspace",
        "file",
        "saturation",
        "display",
        "view",
        "translate",
        "rotate",
        "scale",
        "center",
        "power",
        "offset",
        "slope",
        "direction"
    )))
    _valid_attrs_mapping: dict = field(default_factory = lambda: dict({
        "in_colorspace": "src",
        "out_colorspace": "dst",
        "file": "src",
        "saturation": "sat"
    }))
    _wrapper_class_members: list = field(default_factory = lambda: list([]))
    _wrapper_class_names: list = field(default_factory = lambda: list([]))

    @property
    def color_operators(self) -> dict:
        return self._color_ops
    
    @color_operators.setter
    def color_operators(self, color_ops: list) -> None:
        self._color_ops = color_ops

    @color_operators.deleter
    def color_operators(self) -> None:
        self._color_ops = []
    
    @property
    def repo_operators(self) -> dict:
        return self._repo_ops
    
    @repo_operators.setter
    def repo_operators(self, repo_ops: list) -> None:
        self._repo_ops = repo_ops

    @repo_operators.deleter
    def repo_operators(self) -> None:
        self._repo_ops = []

    def __post_init__(self) -> None:
        self._wrapper_class_members = dict(inspect.getmembers(ops, inspect.isclass))
        self._wrapper_class_names = [v for v in self._wrapper_class_members.keys()]
        if self.src:
            self.load(self.src)

    def _get_operator_class(self, name: str) -> Any:
        name = "{}Transform".format(name.replace("OCIO", "").replace("Transform", ""))
        if name in self._wrapper_class_names:
            return self._wrapper_class_members[name]
        elif "Repo{}".format(name) in self._wrapper_class_names:
            return self._wrapper_class_members["Repo{}".format(name)]
        else:
            return None

    def _get_operator_sanitized(self, op: Any, data: dict) -> Any:
        # sanitize for different source data structures.
        # fix for nuke vs ocio, cdl transform should not have a src field by ocio specs
        if "CDL" in op.__name__:
            del data["src"]
        return op(**data)

    def _get_operator(self, data: dict) -> None:
        result = {}
        for k, v in data[self._data_search_key].items():
            if k in self._valid_attrs:
                if k in self._valid_attrs_mapping:
                    result[self._valid_attrs_mapping[k]] = v
                else:
                    if k == "scale" and isinstance(v, float):
                        v = [v, v]
                    result[k] = v
        op = self._get_operator_class(data[self._class_search_key])
        return self._get_operator_sanitized(op = op, data = result)

    def _load(self) -> None:
        with open(self.src, "r") as f:
            _ops = json.load(f)
        ocio_nodes = []
        repo_nodes = []
        for k, v in _ops.items():
            if isinstance(v, dict):
                class_name = "{}Transform".format(
                    v[self._class_search_key].replace("OCIO", "").replace("Transform", "")
                )
                if class_name in self._wrapper_class_names:
                    ocio_nodes.append(v)
                elif "Repo{}".format(class_name) in self._wrapper_class_names:
                    repo_nodes.append(v)
                else:
                    continue
        ocio_nodes = sorted(ocio_nodes, key=lambda d: d[self._index_search_key])
        repo_nodes = sorted(repo_nodes, key=lambda d: d[self._index_search_key])
        for c in ocio_nodes:
            self._color_ops.append(self._get_operator(c))
        for c in repo_nodes:
            self._repo_ops.append(self._get_operator(c))

    def clear_operators(self) -> None:
        self.color_ops = []
        self.repo_ops = []

    def load(self, src: str) -> None:
        self.src = src
        self.clear_operators()
        self._load()


@dataclass
class ColorProcessor:
    config_path: str = field(default_factory = lambda: Path(
        os.environ.get("OCIO")).as_posix())
    staging_dir: str = field(default_factory = lambda: Path(
        os.environ.get("TEMP", os.environ["TMP"]),
        "LabLib",
        str(uuid.uuid4())).resolve().as_posix())
    context: str = "LabLib"
    family: str = "LabLib"
    working_space: str = "ACES - ACEScg"
    _operators: list = field(default_factory = lambda: list([]))
    _description: str = ""
    _vars: dict = field(default_factory = lambda: dict({}))
    _views: list[str] = None
    _ocio_config: OCIO.Config = None
    _ocio_transforms: list = field(default_factory = lambda: list([]))
    _ocio_search_paths: list = field(default_factory = lambda: list([]))
    _dest_path: str = None

    # @property
    # def operators(self) -> None:
    #     return self._operators
    # 
    # @operators.setter
    # def operators(self, *args) -> None:
    #     self.set_operators(*args)
    # 
    # @operators.deleter
    # def operators(self) -> None:
    #     self.clear_operators()
    #
    # @property
    # def views(self) -> list:
    #     return self._views
    # 
    # @views.setter
    # def views(self, *args: str | list[str]) -> None:
    #     self.set_views(*args)
    # 
    # @views.deleter
    # def views(self) -> None:
    #     self.clear_views()
    #
    # @property
    # def vars(self) -> list:
    #     return self._vars
    # 
    # @vars.setter
    # def vars(self, var_dict: dict) -> None:
    #     self.set_vars(**var_dict)
    # 
    # @vars.deleter
    # def vars(self) -> None:
    #     self.clear_vars()

    def set_dest_path(self, dest: str) -> None:
        self.dest_path = Path(dest).resolve().as_posix()

    def clear_operators(self) -> None:
        self._operators = []

    def append_operators(self, *args) -> None:
        for i in args:
            if isinstance(i, list):
                self.append_operators(*i)
            else:
                self._operators.append(i)

    def set_operators(self, *args) -> None:
        self.clear_operators()
        self.append_operators(*args)

    def clear_views(self):
        self._views = []

    def append_views(self, *args: str | list[str]) -> None:
        for i in args:
            if isinstance(i, list):
                self.append_views(*i)
            else:
                self._views.append(i)

    def set_views(self, *args: str | list[str]) -> None:
        self.clear_views()
        self.append_views(*args)

    def clear_vars(self):
        self._vars = {}

    def append_vars(self, **kwargs) -> None:
        for k, v in kwargs.items():
            self._vars[k] = v

    def set_vars(self, **kwargs) -> None:
        self.clear_vars()
        self.append_vars(**kwargs)
    
    def set_description(self, desc: str) -> None:
        self._description = desc
    
    def get_description_from_config(self) -> str:
        return self._ocio_config.getDescription()
    
    def _get_search_paths_from_config(self) -> list:
        return list(self._ocio_config.getSearchPaths())
    
    def _sanitize_search_paths(self, paths: list) -> list:
        real_paths = []
        for p in paths:
            computed_path = Path(Path(self.config_path).parent, p).resolve()
            if computed_path.is_file():
                computed_path = Path(computed_path.parent).resolve()
                real_paths.append(computed_path.as_posix())
            elif computed_path.is_dir():
                computed_path = computed_path.resolve()
                real_paths.append(computed_path.as_posix())
            else:
                continue
        real_paths = list(set(real_paths))
        self._search_paths = real_paths
        return real_paths
    
    def _get_absolute_search_paths_from_ocio(self) -> list:
        paths = self._get_search_paths_from_config()
        for op in self._ocio_transforms:
            try:
                paths.append(op.getSrc())
            except:
                continue
        return self._sanitize_search_paths(paths)
    
    def _get_absolute_search_paths(self) -> list:
        paths = self._get_search_paths_from_config()
        for op in self._operators:
            if hasattr(op, "src"):
                paths.append(op.src)
        return self._sanitize_search_paths(paths)

    def _read_config(self) -> None:
        self._ocio_config = OCIO.Config.CreateFromFile(self.config_path)

    def load_config_from_file(self, src: str) -> None:
        self.config_path = src
        self._read_config()

    def process_config(self) -> None:
        for op in self._operators:
            props = vars(op)
            if props.get("direction"):
                props["direction"] = OCIO.TransformDirection.TRANSFORM_DIR_INVERSE
            else:
                props["direction"] = OCIO.TransformDirection.TRANSFORM_DIR_FORWARD
            ocio_class_name = getattr(OCIO, op.__class__.__name__)
            if props.get("src"):
                op_path = Path(props["src"]).resolve()
                if op_path.is_file():
                    props["src"] = op_path.name
            self._ocio_transforms.append(ocio_class_name(**props))
        for k, v in self._vars.items():
            self._ocio_config.addEnvironmentVar(k, v)
        self._ocio_config.setDescription(self._description)
        group_transform = OCIO.GroupTransform(self._ocio_transforms)
        look_transform = OCIO.ColorSpaceTransform(
            src = self.working_space,
            dst = self.context
        )
        cspace = OCIO.ColorSpace()
        cspace.setName(self.context)
        cspace.setFamily(self.family)
        cspace.setTransform(
            group_transform,
            OCIO.ColorSpaceDirection.COLORSPACE_DIR_FROM_REFERENCE
        )
        look = OCIO.Look(
            name = self.context,
            processSpace = self.working_space,
            transform = look_transform
        )
        self._ocio_config.addColorSpace(cspace)
        self._ocio_config.addLook(look)
        self._ocio_config.addDisplayView(
            self._ocio_config.getActiveDisplays().split(",")[0],
            self.context,
            self.working_space,
            looks = self.context
        )
        if not self._views:
            self._ocio_config.setActiveViews(
                "{},{}".format(self.context, self._ocio_config.getActiveViews()))
        else:
            self._ocio_config.setActiveViews(
                "{},{}".format(self.context, ",".join(self._views)))
        self._ocio_config.validate()

    def write_config(self, dest: str = None) -> str:
        dest = Path(dest).resolve()
        config_lines = self._ocio_config.serialize().splitlines()
        search_paths = self._search_paths
        for i, sp in enumerate(search_paths):
            search_paths[i] = "  - {}".format(sp)
        for i, l in enumerate(copy.deepcopy(config_lines)):
            if l.find("search_path") >= 0:
                config_lines[i] = "\nsearch_path:"
                for idx, sp in enumerate(search_paths):
                    config_lines.insert(i+idx+1, sp)
                config_lines.insert(i+len(search_paths)+1, "")
                break
        final_config = "\n".join(config_lines)
        dest.parent.mkdir(exist_ok=True, parents=True)
        with open(dest.as_posix(), "w") as f:
            f.write(final_config)
        return final_config

    def create_config(self, dest: str = None) -> None:
        if not dest: dest = Path(self.staging_dir, "config.ocio")
        dest = Path(dest).resolve().as_posix()
        self.load_config_from_file(Path(self.config_path).resolve().as_posix())
        self._get_absolute_search_paths()
        self.process_config()
        self.write_config(dest)
        self._dest_path = dest
        return dest
    
    def get_oiiotool_cmd(self) -> list:
        cmd = [
            "--colorconfig",
            self._dest_path,
            "--ociolook:from=\"{}\":to=\"{}\"".format(self.working_space,
                                                      self.working_space),
            self.context
        ]
        return cmd
    

@dataclass
class RepoProcessor:
    _operators: list[ops.RepoTransform] = field(default_factory = lambda: list([]))
    source_width: int = None
    source_height: int = None
    dest_width: int = None
    dest_height: int = None
    _raw_matrix: list[list[float]] = field(default_factory = lambda: list([list([])]))
    _class_search_key = "class"

    def set_source_size(self, width: int, height: int) -> None:
        self.source_width = width
        self.source_height = height

    def set_destination_size(self, width: int, height: int) -> None:
        self.dest_width = width
        self.dest_height = height

    def get_raw_matrix(self) -> list[list[float]]:
        return self._raw_matrix

    def add_operators(self, *args) -> None:
        for a in args:
            if isinstance(a, list):
                self.add_operators(*a)
            else:
                self._operators.append(a)

    def get_matrix_chained(self,
                           flip: bool = False,
                           flop: bool = True,
                           reverse_chain: bool = True) -> str:
        chain = []
        tlist = self._operators
        if reverse_chain:
            tlist.reverse()
        if flip:
            chain.append(utils.flip_matrix(self.source_width))
        if flop:
            chain.append(utils.flop_matrix(self.source_height))
        for xform in tlist:
            chain.append(utils.calculate_matrix(t = xform.translate,
                                                r = xform.rotate,
                                                s = xform.scale,
                                                c = xform.center))
        if flop:
            chain.append(utils.flop_matrix(self.source_height))
        if flip:
            chain.append(utils.flip_matrix(self.source_width))
        result = utils.identity_matrix()
        for m in chain:
            result = utils.mult_matrix(result, m)
        self._raw_matrix = result
        return result

    def get_cornerpin_data(self,
                           matrix: list[list[float]]) -> list:
        cp = utils.matrix_to_cornerpin(m = matrix,
                                       w = self.source_width,
                                       h = self.source_height,
                                       origin_upperleft = False)
        return cp

    def get_oiiotool_cmd(self) -> list:

        if not self.source_width:
            raise ValueError(f"Missing source width!")
        if not self.source_height:
            raise ValueError(f"Missing source height!")
        if not self.dest_width:
            raise ValueError(f"Missing destination width!")
        if not self.dest_height:
            raise ValueError(f"Missing destination height!")
        
        matrix = self.get_matrix_chained()
        matrix_tr = utils.transpose_matrix(matrix)
        warp_cmd = utils.matrix_to_csv(matrix_tr)
        
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
        
        cropped_area = "{}x{}-{}-{}".format(fitted_width, fitted_height, x_offset, y_offset)
        dest_size = "{}x{}".format(self.dest_width, self.dest_height)

        cmd = [
            "--warp:filter=cubic:recompute_roi=1",
            warp_cmd,
            "--crop",
            cropped_area,
            "--fullsize",
            cropped_area,
            "--resize",
            dest_size
        ]

        return cmd


@dataclass
class SlateProcessor:
    thumbs: list = field(default_factory = lambda: list([]))
    charts: list = field(default_factory = lambda: list([]))
    data: dict = field(default_factory = lambda: dict({}))
    width: int = 1920
    height: int = 1080
    staging_dir: str = ""
    slate_template_path: str = None
    source_files: list = field(default_factory = lambda: list([]))
    is_source_linear: bool = True

    def __post_init__(self):
        options = Options()
        options.add_argument("--headless=new")
        options.add_argument("--disable-gpu")
        options.add_argument("--hide-scrollbars")
        options.add_argument("--show-capture=no")
        options.add_experimental_option("excludeSwitches", ["enable-logging"])
        self.staging_dir = utils.get_staging_dir()
        self._driver = webdriver.Chrome(options = options)
        self._thumb_class_name: str = "thumb"
        self._chart_class_name: str = "chart"
        self._template_staging_dirname: str = "template_staging"
        self._slate_staged_path: str = None
        self._slate_computed: str = None
        self._slate_base_image_path: str = None
        self._remove_missing_parents: bool = True

    def get_staging_dir(self) -> str:
        return self.staging_dir

    def set_remove_missing_parent(self, remove: bool = True) -> None:
        self._remove_missing_parents = remove

    def set_linear_working_space(self, is_linear: bool) -> None:
        self.is_source_linear = is_linear

    def set_source_files(self, files: list) -> None:
        self.source_files = files

    def set_template_path(self, path: str) -> None:
        self.slate_template_path = Path(path).resolve().as_posix()
    
    def set_staging_dir(self, path: str) -> None:
        self.staging_dir = Path(path).resolve().as_posix()
    
    def set_data(self, data: dict) -> None:
        self.data = data

    def set_size(self, width: int, height: int) -> None:
        self.width = width
        self.height = height

    def set_thumb_class_name(self, name: str) -> None:
        self._thumb_class_name = name
    
    def set_chart_class_name(self, name: str) -> None:
        self._chart_class_name = name

    def set_viewport_size(self, width: int, height: int) -> None:
        window_size = self._driver.execute_script("""
            return [window.outerWidth - window.innerWidth + arguments[0],
            window.outerHeight - window.innerHeight + arguments[1]];
            """, width, height)
        self._driver.set_window_size(*window_size)
    
    def stage_slate(self) -> str:
        if not self.staging_dir:
            raise ValueError("Missing staging dir!")
        if not self.slate_template_path:
            raise ValueError("Missing slate template path!")
        slate_path = Path(self.slate_template_path).resolve()
        slate_dir = slate_path.parent
        slate_name = slate_path.name
        slate_staging_dir = Path(self.staging_dir, self._template_staging_dirname).resolve()
        slate_staged_path = Path(slate_staging_dir, slate_name).resolve()
        slate_staging_dir.mkdir(parents = True, exist_ok = True)
        shutil.rmtree(slate_staging_dir.as_posix())
        shutil.copytree(src = slate_dir.as_posix(),
                        dst = slate_staging_dir.as_posix())
        self._slate_staged_path = slate_staged_path.as_posix()
        return self._slate_staged_path

    def format_slate(self) -> None:
        if not self.data:
            raise ValueError("Missing subst_data to format template!")
        with open(self._slate_staged_path, "r+") as f:
            formatted_slate = f.read().format_map(
                utils.format_dict(self.data))
            f.seek(0)
            f.write(formatted_slate)
            f.truncate()
        self._driver.get(self._slate_staged_path)
        elements = self._driver.find_elements(By.XPATH,
            "//*[contains(text(),'{}')]".format(utils.format_dict._placeholder))
        for el in elements:
            self._driver.execute_script("""
                var element = arguments[0];
                element.style.display = 'none';                  
                """, el)
            if self._remove_missing_parents:
                parent = el.find_element(By.XPATH, "..")
                self._driver.execute_script("""
                    var element = arguments[0];
                    element.style.display = 'none';                  
                    """, parent)
        with open(self._slate_staged_path, "w") as f:
            f.seek(0)
            f.write(self._driver.page_source)
            f.truncate()

    def set_thumbnail_sources(self) -> None:
        thumb_steps = int(len(self.source_files) / (len(self.thumbs) + 1))
        for i, t in enumerate(self.thumbs):
            self.thumbs[i].filename = Path(self.source_files[thumb_steps * (i + 1)]).resolve().as_posix()

    def setup_base_slate(self) -> str:
        self._driver.get(self._slate_staged_path)
        self.set_viewport_size(self.width, self.height)
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
                        origin_x = t.location["x"],
                        origin_y = t.location["y"],
                        width = t.size["width"],
                        height = thumb_height
                    )
                )
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
                        origin_x = c.location["x"],
                        origin_y = c.location["y"],
                        width = c.size["width"],
                        height = c.size["height"]
                    )
                )
                self._driver.execute_script("""
                    var element = arguments[0];
                    element.parentNode.removeChild(element);
                    """, c)
        slate_base_path = Path(
            Path(self.staging_dir),
            "slate_base.png"
        ).resolve()
        self._driver.save_screenshot(slate_base_path.as_posix())
        self._driver.quit()
        template_staged_path = Path(self._slate_staged_path).resolve().parent
        shutil.rmtree(template_staged_path)
        # template_staged_path.rmdir()
        return slate_base_path

    def get_oiiotool_cmd(self) -> list:
        label = "base"
        cmd = [
            "--colorconvert", "sRGB", "linear",
            "--ch", "R,G,B,A=1.0",
            "--label", "slate",
            "--create", "{}x{}".format(self.width, self.height), "4",
            "--ch", "R,G,B,A=0.0",
            "--label", label
        ]
        for i, t in enumerate(self.thumbs):
            if i > 0:
                label = "imgs"
            cmd.extend([
                "-i", t.filename
            ])
            if not self.is_source_linear:
                cmd.extend(["--colorconvert", "sRGB", "linear"])
            cmd.extend([
                "--ch", "R,G,B,A=1.0",
                "--resample", "{}x{}+{}+{}".format(t.width,
                                                   t.height,
                                                   t.origin_x,
                                                   t.origin_y),
                label, "--over",
                "--label", "imgs"
            ])
        for i, c in enumerate(self.charts):
            cmd.extend([
                "-i", c.filename,
                "--colorconvert", "sRGB", "linear",
                "--ch", "R,G,B,A=1.0",
                "--resample", "{}x{}+{}+{}".format(c.width,
                                                   c.height,
                                                   c.origin_x,
                                                   c.origin_y),
                "imgs", "--over",
                "--label", "imgs"
            ])
        cmd.extend([
            "slate", "--over",
            "--label", "complete_slate",
        ])

        return cmd

    def create_slate(self) -> None:
        self.stage_slate()
        self.format_slate()
        self.setup_base_slate()
        self.set_thumbnail_sources()
        # self.get_oiiotool_cmd()