from __future__ import annotations
from dataclasses import dataclass, field
from copy import deepcopy

import os
import re

import clique

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
class SequenceInfo:
    frames: list[str] = field(default_factory = lambda: list([]))
    frame_start: int = None
    frame_end: int = None
    head: str = None
    tail: str = None
    padding: int = 0
    hash_string: str = None
    format_string: str = None

    def _get_file_splits(self, file_name: str) -> None:
        head, ext = os.path.splitext(file_name)
        frame = int(re.findall(r'\d+$', head))
        return head, frame, ext

    def compute(self,
                collection: clique.Collection,
                collection_path: str) -> None:
        self.frames = [f for f in collection]
        self.frame_start = int(self.frames[0].replace(collection.head, "").replace(collection.tail,""))
        self.frame_end = int(self.frames[len(self.frames)-1].replace(collection.head, "").replace(collection.tail,""))
        self.head = collection.head
        self.tail = collection.tail
        self.padding = len(str(self.frame_start))
        self.frames = [os.path.abspath(os.path.join(collection_path, f)).replace("\\", "/") for f in collection]
        self.hash_string = os.path.abspath(
            os.path.join(
                collection_path,
                collection.format("{head}#{tail}")
            )
        ).replace("\\", "/")
        self.format_string = os.path.abspath(
            os.path.join(
                collection_path,
                "{}{}{}".format(collection.head, "%0{}d".format(self.padding), collection.tail)
            )
        ).replace("\\", "/")

    def computee(self, scan_dir: str) -> None:
        frames = os.listdir(scan_dir)
        for f in enumerate(deepcopy(frames)):
            pass

        


        

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


