from __future__ import annotations

import os
from pathlib import Path
import re
from typing import Dict, List, Optional

from lablib.operators import BaseOperator, ImageInfo


class SequenceInfo(BaseOperator):
    def __init__(self, path: Path, imageinfos: List[ImageInfo]):
        super().__init__(path, imageinfos)
        # self.imageinfos = imageinfos
        # self.update(imageinfos)

    def _get_file_splits(self, file_name: str) -> None:
        head, ext = os.path.splitext(file_name)
        frame = int(re.findall(r"\d+$", head)[0])
        return head.replace(str(frame), ""), frame, ext

    def _get_length(self) -> int:
        return int(self.frame_end) - int(self.frame_start) + 1

    def compute_all(self, scan_dir: str) -> List:
        files = os.listdir(scan_dir)
        sequenced_files = []
        matched_files = []
        for f in files:
            head, tail = os.path.splitext(f)
            matches = re.findall(r"\d+$", head)
            if matches:
                sequenced_files.append(f)
                matched_files.append(head.replace(matches[0], ""))
        matched_files = list(set(matched_files))

        results = []
        for m in matched_files:
            seq = SequenceInfo()
            for sf in sequenced_files:
                if m in sf:
                    seq.frames.append(os.path.join(scan_dir, sf).replace("\\", "/"))

            head, frame, ext = self._get_file_splits(seq.frames[0])
            seq.path = os.path.abspath(scan_dir).replace("\\", "/")
            seq.frame_start = frame
            seq.frame_end = self._get_file_splits(seq.frames[-1])[1]
            seq.head = os.path.basename(head)
            seq.tail = ext
            seq.padding = len(str(frame))
            seq.hash_string = "{}#{}".format(os.path.basename(head), ext)
            seq.format_string = "{}%0{}d{}".format(
                os.path.basename(head), len(str(frame)), ext
            )
            results.append(seq)

        return results

    def compute_longest(self, scan_dir: str) -> SequenceInfo:
        return self.compute_all(scan_dir=scan_dir)[0]

    @classmethod
    def scan(cls, directory: str | Path) -> List[SequenceInfo]:
        cls.log.info(f"Scanning {directory}")
        if not isinstance(directory, Path):
            directory = Path(directory)

        if not directory.is_dir():
            raise NotImplementedError(f"{directory} is no directory")

        files_map: Dict[Path, ImageInfo] = {}
        for item in directory.iterdir():
            if not item.is_file():
                continue
            if item.suffix not in (".exr"):
                cls.log.warning(f"{item.suffix} not in (.exr)")
                continue

            _parts = item.stem.split(".")
            if len(_parts) > 2:
                cls.log.warning(f"{_parts = }")
                continue
            seq_key = Path(item.parent, _parts[0])

            if seq_key not in files_map.keys():
                files_map[seq_key] = []
            files_map[seq_key].append(ImageInfo(item))

        for seq_files in files_map.values():
            return cls(path=seq_key.parent, imageinfos=seq_files)

    def update(self, imageinfos: Optional[List[ImageInfo]]):
        if imageinfos:
            self.log.debug(f"Updating from new frames: {imageinfos}")
            self.imageinfos = imageinfos

        # TODO: check for missing frames

    @property
    def imageinfos(self) -> List[int]:
        return self._imageinfos

    @imageinfos.setter
    def imageinfos(self, value: List[ImageInfo]):
        self._imageinfos = value

    @property
    def frames(self) -> List[int]:
        return self.imageinfos

    @property
    def start_frame(self) -> int:
        return min(self.frames).frame_number

    @property
    def end_frame(self) -> int:
        return max(self.frames).frame_number

    @property
    def hash_string(self) -> str:
        frame: ImageInfo = min(self.frames)
        ext: str = frame.extension
        basename = frame.name.split(".")[0]
        frame_number: int = frame.frame_number

        result = f"{basename}.{frame_number}#{len(self.frames)}{ext}"
        return result

    @property
    def padding(self) -> int:
        frame = min(self.frames)
        result = len(str(frame.frame_number))
        return result

    @property
    def frames_missing(self) -> bool:
        start = min(self.frames).frame_number
        end = max(self.frames).frame_number
        expected: int = len(range(start, end)) + 1
        return not expected == len(self.frames)

    @property
    def width(self) -> int:
        return self.imageinfos[0].width

    @property
    def display_width(self) -> int:
        return self.imageinfos[0].display_width

    @property
    def height(self) -> int:
        return self.imageinfos[0].height

    @property
    def display_height(self) -> int:
        return self.imageinfos[0].display_height
