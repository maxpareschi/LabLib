from __future__ import annotations
from dataclasses import dataclass, field

import subprocess
import shutil

from pathlib import Path

from .utils import read_image_info, offset_timecode
from .processors import ColorProcessor, RepoProcessor, SlateProcessor
from .operators import SequenceInfo


@dataclass
class DefaultRenderer:
    color_proc: ColorProcessor = None
    repo_proc: RepoProcessor = None
    source_sequence: SequenceInfo = None
    staging_dir: str = None
    name: str = None
    format: str = None

    def __post_init__(self) -> None:
        self._debug: bool = False
        self._threads: int = 4
        self._command: list = []
        if not self.name:
            self.name = "lablib_render"
    
    def setup_staging_dir(self) -> None:
        render_staging_dir = Path(self.staging_dir, self.name)
        if not render_staging_dir.resolve().is_dir():
            shutil.rmtree(render_staging_dir.as_posix(), ignore_errors = True)
            render_staging_dir.mkdir(parents = True, exist_ok = True)
            
    def set_color_processor(self,
                            processor: ColorProcessor) -> None:
        self.color_proc = processor

    def set_repo_processor(self,
                           processor: RepoProcessor) -> None:
        self.repo_proc = processor

    def set_debug(self, debug: bool) -> None:
        self._debug = debug

    def set_source_sequence(self, sequence: SequenceInfo) -> None:
        self.source_sequence = sequence

    def set_staging_dir(self, dir: str) -> None:
        self.staging_dir = dir

    def set_threads(self, threads: int) -> None:
        self._threads = threads

    def get_oiiotool_cmd(self) -> list:
        return self._command

    def render(self) -> SequenceInfo:
        if not self.color_proc and not self.repo_proc:
            raise ValueError("Missing both valid Processors!")
        self.setup_staging_dir()
        cmd = [
            "oiiotool",
            "-i", Path(self.source_sequence.path,
                       self.source_sequence.hash_string).resolve().as_posix(),
            "--threads", str(self._threads),
        ]
        if self.repo_proc:
            cmd.extend(self.repo_proc.get_oiiotool_cmd())
        if self.color_proc:
            self.color_proc.create_config()
            cmd.extend(self.color_proc.get_oiiotool_cmd())
        cmd.extend([
            "--ch", "R,G,B"
        ])
        if self._debug:
            cmd.extend([
                "--debug", "-v"
            ])
        if self.format:
            dest_path = "{}{}{}".format(
                self.source_sequence.head,
                "#",
                ".{}".format(self.format) if self.format.find(".") < 0 else self.format
            )
        else:
            dest_path = self.source_sequence.hash_string
        cmd.extend([
            "-o", Path(
                self.staging_dir,
                self.name,
                dest_path
            ).resolve().as_posix()
        ])
        self._command = cmd
        if self._debug:
            print("oiiotool cmd >>> {}".format(" ".join(self._command)))
        subprocess.run(cmd)
        result = SequenceInfo()
        Path(self.color_proc._dest_path).resolve().unlink()
        return result.compute_longest(
            Path(self.staging_dir, self.name).resolve().as_posix()
        )

    def render_repo_ffmpeg(self,
                           src: str,
                           dst: str,
                           cornerpin: list,
                           in_args: list = None,
                           out_args: list = None,
                           resolution: str = None,
                           debug: str = "error") -> SequenceInfo:
        if not resolution:
            resolution = "1920x1080"
        width, height = resolution.split("x")
        cmd = ["ffmpeg"]
        cmd.extend(["-y", "-loglevel", debug, "-hide_banner"])
        if in_args:
            cmd.extend(in_args)
        cmd.extend(["-i", src])
        cmd.extend(["-vf", ",".join([
                "perspective={}:{}:{}:{}:{}:{}:{}:{}:{}".format(
                    cornerpin[0], cornerpin[1],
                    cornerpin[2], cornerpin[3],
                    cornerpin[4], cornerpin[5],
                    cornerpin[6], cornerpin[7],
                    "sense=destination:eval=init"
                ),
                f"scale={width}:-1",
                f"crop={width}:{height}"
            ])
        ])
        if out_args:
            cmd.extend(out_args)
        cmd.append(dst)
        subprocess.run(cmd)
        result = SequenceInfo()
        return result.compute_longest(
            Path(dst).resolve().parent.as_posix()
        )


@dataclass
class DefaultSlateRenderer:
    slate_proc: SlateProcessor = None
    source_sequence: SequenceInfo = None
    dest: str = None

    def __post_init__(self) -> None:
        self._thumbs: list = None
        self._debug: bool = False
        self._command: list = []
        if self.source_sequence:
            self.set_source_sequence(self.source_sequence)
            self.slate_proc.source_files = self.source_sequence.frames
        if self.dest:
            self.set_destination(self.dest)

    def set_slate_processor(self,
                            processor: SlateProcessor) -> None:
        self.slate_proc = processor

    def set_debug(self, debug: bool) -> None:
        self._debug = debug

    def set_source_sequence(self, source_sequence: SequenceInfo) -> None:
        self.source_sequence = source_sequence
        head, frame, tail = source_sequence._get_file_splits(source_sequence.frames[0])
        self.dest = "{}{}{}".format(head,
                                    str(int(frame) - 1).zfill(source_sequence.padding),
                                    tail)

    def set_destination(self, dest: str) -> None:
        self.dest = dest

    def render(self) -> None:
        first_frame = read_image_info(self.source_sequence.frames[0])
        timecode = offset_timecode(
            tc = first_frame.timecode,
            frame_offset = -1,
            fps = first_frame.fps
        )
        self.slate_proc.create_base_slate()
        if not self.slate_proc:
            raise ValueError("Missing valid SlateProcessor!")
        cmd = ["oiiotool"]
        cmd.extend( self.slate_proc.get_oiiotool_cmd())
        cmd.extend([
            "--ch", "R,G,B",
            "--attrib:type=timecode",
            "smpte:TimeCode", timecode
        ])
        if self._debug:
            cmd.extend([
                "--debug", "-v"
            ])
        cmd.extend([
            "-o", self.dest
        ])
        self._command = cmd
        subprocess.run(cmd)
        slate_base_image_path = Path(self.slate_proc._slate_base_image_path).resolve()
        slate_base_image_path.unlink()
        shutil.rmtree(slate_base_image_path.parent)