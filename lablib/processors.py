from __future__ import annotations

import os
import json
import inspect
import uuid
import shutil
from typing import Any, List, Union, Dict, Tuple
from dataclasses import dataclass, field
from pathlib import Path

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

    @property
    def color_operators(self) -> Dict:
        return self._color_ops

    @color_operators.setter
    def color_operators(self, color_ops: List) -> None:
        self._color_ops = color_ops

    @color_operators.deleter
    def color_operators(self) -> None:
        self._color_ops = []

    @property
    def repo_operators(self) -> Dict:
        return self._repo_ops

    @repo_operators.setter
    def repo_operators(self, repo_ops: List) -> None:
        self._repo_ops = repo_ops

    @repo_operators.deleter
    def repo_operators(self) -> None:
        self._repo_ops = []

    def __post_init__(self) -> None:
        self._wrapper_class_members = dict(
            inspect.getmembers(ops, inspect.isclass)
        )
        self._color_ops: List = []
        self._repo_ops: List = []
        self._class_search_key: str = "class"
        self._index_search_key: str = "subTrackIndex"
        self._data_search_key: str = "node"
        self._valid_attrs: Tuple = (
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
        )
        self._valid_attrs_mapping: Dict[str, str] = {
            "in_colorspace": "src",
            "out_colorspace": "dst",
            "file": "src",
            "saturation": "sat"
        }
        if self.src:
            self.load(self.src)

    def _get_operator_class(self, name: str) -> Any:
        name = "{}Transform".format(
            name
            .replace("OCIO", "")
            .replace("Transform", "")
        )
        if name in self._wrapper_class_members:
            return self._wrapper_class_members[name]

        if "Repo{}".format(name) in self._wrapper_class_members:
            return self._wrapper_class_members["Repo{}".format(name)]

        return None

    def _get_operator_sanitized(self, op: Any, data: Dict) -> Any:
        # sanitize for different source data structures.
        # fix for nuke vs ocio, cdl transform should not have a src field by ocio specs
        if "CDL" in op.__name__:
            del data["src"]
        return op(**data)

    def _get_operator(self, data: Dict) -> None:
        result = {}
        for key, value in data[self._data_search_key].items():
            if key not in self._valid_attrs:
                continue

            if key in self._valid_attrs_mapping:
                result[self._valid_attrs_mapping[key]] = value
                continue

            if key == "scale" and isinstance(value, float):
                value = [value, value]
            result[key] = value

        op = self._get_operator_class(data[self._class_search_key])
        return self._get_operator_sanitized(op=op, data=result)

    def _load(self) -> None:
        with open(self.src, "r") as f:
            ops_data = json.load(f)

        ocio_nodes = []
        repo_nodes = []
        for value in ops_data.values():
            if not isinstance(value, dict):
                continue

            class_name = "{}Transform".format(
                value[self._class_search_key]
                .replace("OCIO", "")
                .replace("Transform", "")
            )
            if class_name in self._wrapper_class_members:
                ocio_nodes.append(value)

            elif "Repo{}".format(class_name) in self._wrapper_class_members:
                repo_nodes.append(value)

        ocio_nodes.sort(key=lambda d: d[self._index_search_key])
        repo_nodes.sort(key=lambda d: d[self._index_search_key])
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
    operators: List = field(default_factory=list)
    config_path: str = None
    staging_dir: str = None
    context: str = "LabLib"
    family: str = "LabLib"
    working_space: str = "ACES - ACEScg"
    views: List[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.config_path:
            self.config_path = Path(os.environ.get("OCIO")).as_posix()

        if not self.staging_dir:
            self.staging_dir = Path(
                os.environ.get("TEMP", os.environ["TMP"]),
                "LabLib",
                str(uuid.uuid4())
            ).resolve().as_posix()
        self._description: str = None
        self._vars: Dict = {}
        self._views: List[str] = None
        if self.views:
            self._views: List[str] = self.set_views(self.views)
        self._ocio_config: OCIO.Config = None
        self._ocio_transforms: List = []
        self._ocio_search_paths: List = []
        self._ocio_config_name: str = "config.ocio"
        self._dest_path: str = None

    # @property
    # def operators(self) -> None:
    #     return self.operators
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
    # def views(self) -> List:
    #     return self._views
    #
    # @views.setter
    # def views(self, *args: Union[str, List[str]]) -> None:
    #     self.set_views(*args)
    #
    # @views.deleter
    # def views(self) -> None:
    #     self.clear_views()
    #
    # @property
    # def vars(self) -> List:
    #     return self._vars
    #
    # @vars.setter
    # def vars(self, var_dict: Dict) -> None:
    #     self.set_vars(**var_dict)
    #
    # @vars.deleter
    # def vars(self) -> None:
    #     self.clear_vars()

    def set_ocio_config_name(self, name: str) -> None:
        self._ocio_config_name = name

    def set_staging_dir(self, path: str) -> None:
        self.staging_dir = Path(path).resolve().as_posix()

    def set_views(self, *args: Union[str, List[str]]) -> None:
        self.clear_views()
        self.append_views(*args)

    def set_operators(self, *args) -> None:
        self.clear_operators()
        self.append_operators(*args)

    def set_vars(self, **kwargs) -> None:
        self.clear_vars()
        self.append_vars(**kwargs)

    def set_description(self, desc: str) -> None:
        self._description = desc

    def clear_operators(self) -> None:
        self.operators = []

    def clear_views(self):
        self._views = []

    def clear_vars(self):
        self._vars = {}

    def append_operators(self, *args) -> None:
        for arg in args:
            if isinstance(arg, list):
                self.append_operators(*arg)
            else:
                self.operators.append(arg)

    def append_views(self, *args: Union[str, List[str]]) -> None:
        for arg in args:
            if isinstance(arg, list):
                self.append_views(*arg)
            else:
                self._views.append(arg)

    def append_vars(self, **kwargs) -> None:
        self._vars.update(kwargs)

    def get_config_path(self) -> str:
        return self._dest_path

    def get_description_from_config(self) -> str:
        return self._ocio_config.getDescription()

    def _get_search_paths_from_config(self) -> List[str]:
        return list(self._ocio_config.getSearchPaths())

    def _sanitize_search_paths(self, paths: List[str]) -> List[str]:
        real_paths = []
        for p in paths:
            computed_path = Path(Path(self.config_path).parent, p).resolve()
            if computed_path.is_file():
                computed_path = Path(computed_path.parent).resolve()
                real_paths.append(computed_path.as_posix())
            elif computed_path.is_dir():
                computed_path = computed_path.resolve()
                real_paths.append(computed_path.as_posix())

        real_paths = list(set(real_paths))
        self._search_paths = real_paths
        return real_paths

    def _get_absolute_search_paths_from_ocio(self) -> List[str]:
        paths = self._get_search_paths_from_config()
        for op in self._ocio_transforms:
            try:
                paths.append(op.getSrc())
            except:
                # TODO find out why this crashes and capture explicit
                #   exceptions
                continue
        return self._sanitize_search_paths(paths)

    def _get_absolute_search_paths(self) -> List[str]:
        paths = self._get_search_paths_from_config()
        for op in self.operators:
            if hasattr(op, "src"):
                paths.append(op.src)
        return self._sanitize_search_paths(paths)

    def _read_config(self) -> None:
        self._ocio_config = OCIO.Config.CreateFromFile(self.config_path)

    def load_config_from_file(self, src: str) -> None:
        self.config_path = src
        self._read_config()

    def process_config(self) -> None:
        for op in self.operators:
            props = vars(op)
            if props.get("direction"):
                props["direction"] = (
                    OCIO.TransformDirection.TRANSFORM_DIR_INVERSE)
            else:
                props["direction"] = (
                    OCIO.TransformDirection.TRANSFORM_DIR_FORWARD)
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
            src=self.working_space,
            dst=self.context
        )
        cspace = OCIO.ColorSpace()
        cspace.setName(self.context)
        cspace.setFamily(self.family)
        cspace.setTransform(
            group_transform,
            OCIO.ColorSpaceDirection.COLORSPACE_DIR_FROM_REFERENCE
        )
        look = OCIO.Look(
            name=self.context,
            processSpace=self.working_space,
            transform=look_transform
        )
        self._ocio_config.addColorSpace(cspace)
        self._ocio_config.addLook(look)
        self._ocio_config.addDisplayView(
            self._ocio_config.getActiveDisplays().split(",")[0],
            self.context,
            self.working_space,
            looks=self.context
        )

        if not self._views:
            views_value = self._ocio_config.getActiveViews()
        else:
            views_value = ",".join(self._views)

        self._ocio_config.setActiveViews(
            "{},{}".format(self.context, views_value)
        )
        self._ocio_config.validate()

    def write_config(self, dest: str = None) -> str:
        search_paths = [
            f"  - {path}"
            for path in self._search_paths
        ]

        config_lines = []
        for line in self._ocio_config.serialize().splitlines():
            if "search_path" not in line:
                config_lines.append(line)
                continue
            config_lines.extend(
                ["", "search_path:"] + search_paths + [""]
            )

        final_config = "\n".join(config_lines)
        dest = Path(dest).resolve()
        dest.parent.mkdir(exist_ok=True, parents=True)
        with open(dest.as_posix(), "w") as f:
            f.write(final_config)
        return final_config

    def create_config(self, dest: str = None) -> None:
        if not dest:
            dest = Path(self.staging_dir, self._ocio_config_name)
        dest = Path(dest).resolve().as_posix()
        self.load_config_from_file(Path(self.config_path).resolve().as_posix())
        self._get_absolute_search_paths()
        self.process_config()
        self.write_config(dest)
        self._dest_path = dest
        return dest

    def get_oiiotool_cmd(self) -> List:
        return [
            "--colorconfig",
            self._dest_path,
            "--ociolook:from=\"{}\":to=\"{}\"".format(
                self.working_space, self.working_space
            ),
            self.context
        ]


@dataclass
class RepoProcessor:
    operators: List = field(default_factory=list)
    source_width: int = None
    source_height: int = None
    dest_width: int = None
    dest_height: int = None

    def __post_init__(self):
         self._raw_matrix: List[List[float]] = [[]]
         self._class_search_key = "class"

    def set_source_size(self, width: int, height: int) -> None:
        self.source_width = width
        self.source_height = height

    def set_destination_size(self, width: int, height: int) -> None:
        self.dest_width = width
        self.dest_height = height

    def get_raw_matrix(self) -> List[List[float]]:
        return self._raw_matrix

    def add_operators(self, *args) -> None:
        for a in args:
            if isinstance(a, list):
                self.add_operators(*a)
            else:
                self.operators.append(a)

    def get_matrix_chained(
        self,
        flip: bool = False,
        flop: bool = True,
        reverse_chain: bool = True
    ) -> str:
        chain = []
        tlist = list(self.operators)
        if reverse_chain:
            tlist.reverse()

        if flip:
            chain.append(utils.flip_matrix(self.source_width))

        if flop:
            chain.append(utils.flop_matrix(self.source_height))

        for xform in tlist:
            chain.append(utils.calculate_matrix(
                t=xform.translate,
                r=xform.rotate,
                s=xform.scale,
                c=xform.center
            ))

        if flop:
            chain.append(utils.flop_matrix(self.source_height))

        if flip:
            chain.append(utils.flip_matrix(self.source_width))

        result = utils.identity_matrix()
        for m in chain:
            result = utils.mult_matrix(result, m)
        self._raw_matrix = result
        return result

    def get_cornerpin_data(
        self, matrix: List[List[float]]
    ) -> List:
        return utils.matrix_to_cornerpin(
            m=matrix,
            w=self.source_width,
            h=self.source_height,
            origin_upperleft=False
        )

    def get_oiiotool_cmd(self) -> List:
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
            y_offset = int((fitted_height - self.source_height) / 2)

        elif src_aspect < dest_aspect:
            fitted_width = int(self.source_height * dest_aspect)
            x_offset = int((fitted_width - self.source_width) / 2)

        cropped_area = "{}x{}-{}-{}".format(
            fitted_width, fitted_height, x_offset, y_offset
        )
        dest_size = f"{self.dest_width}x{self.dest_height}"

        return [
            "--warp:filter=cubic:recompute_roi=1", warp_cmd,
            "--crop", cropped_area,
            "--fullsize", cropped_area,
            "--resize", dest_size
        ]


@dataclass
class SlateProcessor:
    data: Dict = field(default_factory=dict)
    width: int = 1920
    height: int = 1080
    staging_dir: str = None
    slate_template_path: str = None
    source_files: List = field(default_factory=list)
    is_source_linear: bool = True

    def __post_init__(self):
        if not self.staging_dir:
            self.staging_dir = utils.get_staging_dir()
        self._thumbs = []
        self._charts = []
        self._thumb_class_name: str = "thumb"
        self._chart_class_name: str = "chart"
        self._template_staging_dirname: str = "slate_staging"
        self._slate_staged_path: str = None
        self._slate_computed: str = None
        self._slate_base_image_path: str = None
        self._remove_missing_parents: bool = True
        self._slate_base_name = "slate_base.png"
        options = Options()
        # THIS WILL NEED TO BE SWITCHED TO NEW MODE, BUT THERE ARE BUGS.
        # WE SHOULD BE FINE FOR A COUPLE OF YEARS UNTIL DEPRECATION.
        # --headless=new works only with 100% display size,
        # if you use a different display scaling (for hidpi monitors)
        # the resizing of the screenshot will not work.
        options.add_argument("--headless")
        options.add_argument("--hide-scrollbars")
        options.add_argument("--show-capture=no")
        options.add_argument("--log-level=OFF")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument('--disable-extensions')
        options.add_argument('--disable-gpu')
        options.add_experimental_option("excludeSwitches", ["enable-logging"])
        self._driver = webdriver.Chrome(options = options)

    def get_staging_dir(self) -> str:
        return self.staging_dir

    def get_thumb_placeholder(self) -> str:
        self._driver.get(self._slate_staged_path)
        thumb_placeholder = self._driver.find_elements(
            By.CLASS_NAME, self._thumb_class_name
        )[0]
        src = thumb_placeholder.get_attribute("src").replace("file:///", "")
        return src

    def set_slate_base_name(self, name: str) -> None:
        self._slate_base_name = "{}.png".format(name)

    def set_remove_missing_parent(self, remove: bool = True) -> None:
        self._remove_missing_parents = remove

    def set_linear_working_space(self, is_linear: bool) -> None:
        self.is_source_linear = is_linear

    def set_source_files(self, files: List) -> None:
        self.source_files = files

    def set_template_path(self, path: str) -> None:
        self.slate_template_path = Path(path).resolve().as_posix()

    def set_staging_dir(self, path: str) -> None:
        self.staging_dir = Path(path).resolve().as_posix()

    def set_data(self, data: Dict) -> None:
        self.data = data

    def set_size(self, width: int, height: int) -> None:
        self.width = width
        self.height = height

    def set_thumb_class_name(self, name: str) -> None:
        self._thumb_class_name = name

    def set_chart_class_name(self, name: str) -> None:
        self._chart_class_name = name

    def set_viewport_size(self, width: int, height: int) -> None:
        window_size = self._driver.execute_script(
            "return [window.outerWidth - window.innerWidth + arguments[0],"
            "window.outerHeight - window.innerHeight + arguments[1]];",
            width,
            height
        )
        self._driver.set_window_size(*window_size)

    def stage_slate(self) -> str:
        if not self.staging_dir:
            raise ValueError("Missing staging dir!")
        if not self.slate_template_path:
            raise ValueError("Missing slate template path!")
        slate_path = Path(self.slate_template_path).resolve()
        slate_dir = slate_path.parent
        slate_name = slate_path.name
        slate_staging_dir = Path(
            self.staging_dir, self._template_staging_dirname
        ).resolve()
        slate_staged_path = Path(slate_staging_dir, slate_name).resolve()
        shutil.rmtree(slate_staging_dir.as_posix(), ignore_errors=True)
        shutil.copytree(
            src=slate_dir.as_posix(),
            dst=slate_staging_dir.as_posix()
        )
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
        elements = self._driver.find_elements(
            By.XPATH,
            "//*[contains(text(),'{}')]".format(
                utils.format_dict._placeholder
            )
        )
        for el in elements:
            self._driver.execute_script(
                "var element = arguments[0];\n"
                "element.style.display = 'none';",
                el
            )
            if self._remove_missing_parents:
                parent = el.find_element(By.XPATH, "..")
                self._driver.execute_script(
                    "var element = arguments[0];\n"
                    "element.style.display = 'none';",
                    parent
                )
        with open(self._slate_staged_path, "w") as f:
            f.write(self._driver.page_source)

    def setup_base_slate(self) -> str:
        self._driver.get(self._slate_staged_path)
        self.set_viewport_size(self.width, self.height)
        thumbs = self._driver.find_elements(
            By.CLASS_NAME, self._thumb_class_name
        )
        for thumb in thumbs:
            src_path = thumb.get_attribute("src")
            if not src_path:
                continue

            aspect_ratio = self.width / self.height
            thumb_height = int(thumb.size["width"] / aspect_ratio)
            self._driver.execute_script(
                "var element = arguments[0];"
                "element.style.height = '{}px'".format(thumb_height),
                thumb
            )
            self._thumbs.append(
                utils.ImageInfo(
                    filename=src_path.replace("file:///", ""),
                    origin_x=thumb.location["x"],
                    origin_y=thumb.location["y"],
                    width=thumb.size["width"],
                    height=thumb_height
                )
            )

        for thumb in thumbs:
            self._driver.execute_script(
                "var element = arguments[0];"
                "element.parentNode.removeChild(element);",
                thumb
            )

        charts = self._driver.find_elements(
            By.CLASS_NAME, self._chart_class_name
        )
        for chart in charts:
            src_path = chart.get_attribute("src")
            if src_path:
                self._charts.append(
                    utils.ImageInfo(
                        filename=src_path.replace("file:///", ""),
                        origin_x=chart.location["x"],
                        origin_y=chart.location["y"],
                        width=chart.size["width"],
                        height=chart.size["height"]
                    )
                )

        for chart in charts:
            self._driver.execute_script(
                "var element = arguments[0];"
                "element.parentNode.removeChild(element);",
                chart
            )

        template_staged_path = Path(self._slate_staged_path).resolve().parent
        slate_base_path = Path(
            template_staged_path,
            self._slate_base_name
        ).resolve()
        self._driver.save_screenshot(slate_base_path.as_posix())
        self._driver.quit()
        self._slate_base_image_path = slate_base_path
        return slate_base_path

    def set_thumbnail_sources(self) -> None:
        thumb_steps = int(len(self.source_files) / (len(self._thumbs) + 1))
        for i, t in enumerate(self._thumbs):
            self._thumbs[i].filename = Path(self.source_files[thumb_steps * (i + 1)]).resolve().as_posix()

    def create_base_slate(self) -> None:
        self.stage_slate()
        self.format_slate()
        # thumb_info = utils.read_image_info(self.get_thumb_placeholder())
        # thumb_cmd = [
        #     "oiiotool",
        #     "-i", thumb_info.filename,
        #     "-resize", "{}x{}".format(self.width, self.height),
        #     "-o", thumb_info.filename
        # ]
        # subprocess.run(thumb_cmd)
        self.setup_base_slate()
        self.set_thumbnail_sources()

    def get_oiiotool_cmd(self) -> List:
        label = "base"
        cmd = [
            "-i", Path(self._slate_base_image_path).resolve().as_posix(),
            "--colorconvert", "sRGB", "linear",
            "--ch", "R,G,B,A=1.0",
            "--label", "slate",
            "--create", "{}x{}".format(self.width, self.height), "4",
            "--ch", "R,G,B,A=0.0",
            "--label", label
        ]
        for thumb in self._thumbs:
            cmd.extend([
                "-i", thumb.filename
            ])
            if not self.is_source_linear:
                cmd.extend(["--colorconvert", "sRGB", "linear"])

            cmd.extend([
                "--ch", "R,G,B,A=1.0",
                "--resample", "{}x{}+{}+{}".format(
                    thumb.width, thumb.height, thumb.origin_x, thumb.origin_y
                ),
                label,
                "--over",
                "--label", "imgs"
            ])
            label = "imgs"

        for chart in self._charts:
            cmd.extend([
                "-i", chart.filename,
                "--colorconvert", "sRGB", "linear",
                "--ch", "R,G,B,A=1.0",
                "--resample", "{}x{}+{}+{}".format(
                    chart.width, chart.height, chart.origin_x, chart.origin_y
                ),
                "imgs",
                "--over",
                "--label", "imgs"
            ])

        cmd.extend([
            "slate",
            "--over",
            "--label", "complete_slate",
        ])
        if not self.is_source_linear:
            cmd.extend([
                "--colorconvert", "linear", "sRGB",
            ])

        return cmd
