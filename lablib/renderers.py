from __future__ import annotations
from dataclasses import dataclass, field

import subprocess
import shutil

from pathlib import Path

from .processors import ColorProcessor, RepoProcessor, SlateProcessor
from .operators import SequenceInfo


@dataclass
class DefaultRenderer:
    color_proc: ColorProcessor = None
    repo_proc: RepoProcessor = None
    sequence: SequenceInfo = None
    staging_dir: str = None
    name: str = None

    def __post_init__(self) -> None:
        self._debug: bool = False
        self._threads: int = 4
        self._command: list = []
        if not self.name:
            self.name = "lablib_export"
    
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

    def set_sequence(self, sequence: SequenceInfo) -> None:
        self.sequence = sequence

    def set_staging_dir(self, dir: str) -> None:
        self.staging_dir = dir

    def set_threads(self, threads: int) -> None:
        self._threads = threads

    def get_oiiotool_cmd(self) -> list:
        return self._command

    def render(self) -> None:
        if not self.color_proc and not self.repo_proc:
            raise ValueError("Missing both valid Processors!")
        self.setup_staging_dir()
        cmd = [
            "oiiotool",
            self.sequence.hash_string,
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
        cmd.extend([
            "-o", Path(
                self.staging_dir,
                self.name,
                "{}#.png".format(self.sequence.head)
            ).resolve().as_posix()
        ])
        self._command = cmd
        if self._debug:
            print("oiiotool cmd >>> {}".format(" ".join(self._command)))
        subprocess.run(cmd)

    def render_repo_ffmpeg(self,
                           src: str,
                           dst: str,
                           cornerpin: list,
                           in_args: list = None,
                           out_args: list = None,
                           resolution: str = None,
                           debug: str = "error") -> None:
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


@dataclass
class DefaultSlateRenderer:
    slate_proc: SlateProcessor = None
    src: str = None
    dst: str = None

    def __post_init__(self) -> None:
        self._thumbs: list = None
        self._debug: bool = False
        self._command: list = []

    def set_slate_processor(self,
                            processor: SlateProcessor) -> None:
        self.slate_proc = processor

    def set_debug(self, debug: bool) -> None:
        self._debug = debug

    def set_source(self, src: str) -> None:
        self.src = src

    def set_destination(self, dst: str) -> None:
        self.dst = dst

    def render(self) -> None:
        if not self.slate_proc:
            raise ValueError("Missing valid SlateProcessor!")
        cmd = ["oiiotool"]
        cmd.extend(self.slate_proc.get_oiiotool_cmd())
        if self._debug:
            cmd.extend([
                "--debug", "-v"
            ])
        cmd.extend([
            "-o", self.dst
        ])
        self._command = cmd
        subprocess.run(cmd)