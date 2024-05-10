from dataclasses import dataclass, field
from typing import List


@dataclass
class RepoTransform:
    translate: List[float] = field(default_factory=lambda: [0.0, 0.0])
    rotate: float = 0.0
    scale: List[float] = field(default_factory=lambda: [0.0, 0.0])
    center: List[float] = field(default_factory=lambda: [0.0, 0.0])


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
    offset: List[float] = field(default_factory=lambda: [0.0, 0.0, 0.0])
    power: List[float] = field(default_factory=lambda: [1.0, 1.0, 1.0])
    slope: List[float] = field(default_factory=lambda: [0.0, 0.0, 0.0])
    sat: float = 1.0
    description: str = ""
    id: str = ""
    direction: int = 0
