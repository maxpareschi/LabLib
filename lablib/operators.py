from __future__ import annotations
from dataclasses import dataclass, field
import inspect
import sys


EXTRA_SEARCH_PARAMS = (
    "class",
    "in_colorspace",
    "out_colorspace",
    "file",
    "saturation",
    "working_space",
    "subTrackIndex"
)
EXTRA_OCIO_CLASS_NAMES = (
    "OCIOColorSpace",
)
CLASS_PARAMS_MAPPING = {
    "in_colorspace": "src",
    "out_colorspace": "dst",
    "file": "src",
    "saturation": "sat"
}


@dataclass
class RepoTransform:
    translate: list[float] = field(default_factory = lambda: list([0.0, 0.0]))
    rotate: float = 0.0
    scale: list[float] = field(default_factory = lambda: list([0.0, 0.0]))
    center: list[float] = field(default_factory = lambda: list([0.0, 0.0]))


@dataclass
class FileTransform:
    src: str = None
    cccId: str = "0"
    direction: int = 0


@dataclass
class DisplayViewTransform:
    src: str = "data"
    display: str = "ACES"
    view: str = "Rec.709"
    direction: int = 0


@dataclass
class ColorSpaceTransform:
    src: str = "data"
    dst: str = "data"


@dataclass
class CDLTransform:
    # src: str = "" # NOT NEEDED, USE FILETRANSFORM FOR CDL FILES
    offset: list[float] = field(default_factory = lambda: list([0.0, 0.0, 0.0]))
    power: list[float] = field(default_factory = lambda: list([0.0, 0.0, 0.0]))
    slope: list[float] = field(default_factory = lambda: list([0.0, 0.0, 0.0]))
    sat: float = 1.0
    description: str = ""
    id: str = ""
    direction: int = 0


def get_OCIO_classes() -> tuple:
    return (FileTransform, ColorSpaceTransform, DisplayViewTransform, CDLTransform)


def get_repo_classes() -> tuple:
    return (RepoTransform,)


def get_OCIO_class_names() -> tuple:
    return tuple([f"OCIO{c.__name__}" for c in get_OCIO_classes()]) + EXTRA_OCIO_CLASS_NAMES


def get_repo_class_names() -> tuple:
    return tuple([c.__name__.replace('Repo', '') for c in get_repo_classes()])


def get_valid_parameters() -> tuple:
    valid_parameters = []
    valid_parameters.extend(EXTRA_SEARCH_PARAMS)
    for name, obj in inspect.getmembers(sys.modules[__name__], inspect.isclass):
        for k in obj.__annotations__.keys():
            valid_parameters.append(k)
    valid_parameters = tuple(list(dict.fromkeys(valid_parameters)))
    return valid_parameters


def get_valid_class_parameters(obj) -> tuple:
    valid_parameters = []
    for k in obj.__annotations__.keys():
        valid_parameters.append(k)
    valid_parameters = tuple(list(dict.fromkeys(valid_parameters))) + ("class",)
    return valid_parameters


def get_valid_keys(test_dict: dict, key_list: tuple) -> dict:
    for i, j in test_dict.items():
        if i in key_list:
            yield (i, j)
        yield from [] if not isinstance(j, dict) else get_valid_keys(j, key_list)


