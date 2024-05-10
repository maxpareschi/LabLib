from __future__ import annotations

from dataclasses import field
import os
from pathlib import Path
import re
from typing import List

from lablib.operators import BaseOperator, ImageInfo


class SequenceInfo(BaseOperator):
    path: str = None
    frames: List[str] = field(default_factory=list)
    frame_start: int = None
    frame_end: int = None
    head: str = None
    tail: str = None
    padding: int = 0
    hash_string: str = None
    format_string: str = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.update_from_path(self.path)

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
        cls.log.info(f"{directory = }")
        if not isinstance(directory, Path):
            directory = Path(directory)

        if not directory.is_dir():
            raise NotImplementedError(f"{directory} is no directory")

        files_map = {}
        for item in directory.iterdir():
            if not item.is_file():
                continue
            if item.suffix not in (".exr"):
                cls.log.warning(f"{item.suffix} not in (.exr)")
                continue

            if re.findall(r"\.(\d+)", item.stem):
                name = item.stem.split(".")[0]
            else:
                name = item.stem
            cls.log.info(f"{name = }")

            if name not in files_map.keys():
                files_map[name] = []
            files_map[name].append(ImageInfo(item))

        for seq_name, seq_files in files_map.items():
            cls.log.info(f"{seq_name = }")
            cls.log.info(f"{seq_files = }")
            cls.log.info(f"{len(seq_files) = }")

