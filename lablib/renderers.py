from __future__ import annotations
from dataclasses import dataclass, field

import subprocess

from . import processors as procs


@dataclass
class DefaultRenderer:
    color_proc: procs.ColorProcessor = None
    repo_proc: procs.RepoProcessor = None
    src: str = None
    dst: str = None

    def __post_init__(self) -> None:
        self._debug: bool = False
        self._threads: int = 4
        self._command: list = []

    def set_color_processor(self,
                            processor: procs.ColorProcessor) -> None:
        self.color_proc = processor

    def set_repo_processor(self,
                           processor: procs.ColorProcessor) -> None:
        self.repo_proc = processor

    def set_debug(self, debug: bool) -> None:
        self._debug = debug

    def set_source(self, src: str) -> None:
        self.src = src

    def set_destination(self, dst: str) -> None:
        self.dst = dst

    def set_threads(self, threads: int) -> None:
        self._threads = threads

    def get_oiiotool_cmd(self) -> list:
        return self._command

    def render(self) -> None:
        if not self.color_proc and not self.repo_proc:
            raise ValueError("Missing both valid Processors!")
        cmd = [
            "oiiotool",
            "--threads", self._threads,
            "-i", self.src
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
            "-o", self.dst
        ])
        self._command = cmd
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
    slate_proc: procs.SlateProcessor = None
    src: str = None
    dst: str = None

    def __post_init__(self) -> None:
        self._thumbs: list = None
        self._debug: bool = False
        self._command: list = []

    def set_slate_processor(self,
                           processor: procs.SlateProcessor) -> None:
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