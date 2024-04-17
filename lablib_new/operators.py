from __future__ import annotations
from dataclasses import dataclass, field


@dataclass
class ImageInfo:
    filename: str = None
    origin_x: int = 0
    origin_y: int = 0
    width: int = 1920
    height: int = 1080
    display_width: int = 1920
    display_height: int = 1080
    channels: int = 3
    fps: float = 24.0
    par: float = 1.0
    timecode: str = "01:00:00:01"


@dataclass
class RepoTransform:
    translate: list[float] = field(default_factory = lambda: list([0.0, 0.0]))
    rotate: float = 0.0
    scale: list[float] = field(default_factory = lambda: list([0.0, 0.0]))
    center: list[float] = field(default_factory = lambda: list([0.0, 0.0]))


@dataclass
class FileTransform:
    src: str = ""
    cccId: str = "0"
    direction: int = 0


@dataclass
class DisplayViewTransform:
    src: str = "ACES - ACEScg"
    display: str = "ACES"
    view: str = "Rec.709"
    direction: int = 0


@dataclass
class ColorSpaceTransform:
    src: str = "ACES - ACEScg"
    dst: str = "ACES - ACEScg"


@dataclass
class CDLTransform:
    # src: str = "" # NOT NEEDED, USE FILETRANSFORM FOR CDL FILES
    offset: list[float] = field(default_factory = lambda: list([0.0, 0.0, 0.0]))
    power: list[float] = field(default_factory = lambda: list([1.0, 1.0, 1.0]))
    slope: list[float] = field(default_factory = lambda: list([0.0, 0.0, 0.0]))
    sat: float = 1.0
    description: str = ""
    id: str = ""
    direction: int = 0


