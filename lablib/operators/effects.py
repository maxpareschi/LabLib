from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Union

import PyOpenColorIO as ocio

from lablib.operators import BaseOperator


class LUTFileTransform(BaseOperator):
    def __init__(self, path: str):
        super().__init__(path)
        self.ocio_repr = path

    def update(self):
        # TODO: update from file
        pass

    @property
    def ocio_repr(self):
        return self._ocio_repr

    @ocio_repr.setter
    def ocio_repr(self, value: Union[str, Path, ocio.FileTransform]):
        if isinstance(value, ocio.FileTransform):
            value = value
            self._ocio_repr = value
        else:
            if isinstance(value, Path):
                value = value.as_posix()
            rep = ocio.FileTransform()
            rep.setSrc(value)
            self._ocio_repr = rep
        self.log.debug(f"{dir(self._ocio_repr) = }")

    @property
    def interpolation(self):
        return self.ocio_repr.getInterpolation().name

    @property
    def direction(self):
        return self.ocio_repr.getDirection().name


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
