from __future__ import annotations
from dataclasses import dataclass

import subprocess

from . import processors as procs


@dataclass
class DefaultRenderer:
    color_transform: procs.ColorTransformProcessor = None
    repo_transform: procs.RepoTransformProcessor = None
    source = None
    dest = None
    debug = False

    def compute_oiio(self,
                     source: str = None,
                     dest: str = None,
                     debug: bool = False) -> str:
        if not source:
            if not self.source:
                raise ValueError("Missing source file path!")
            else:
                source = self.source
        if not dest:
            if not self.source:
                raise ValueError("Missing destination file path!")
            else:
                dest = self.dest
        cmd = ["oiiotool"]
        cmd.append(source)
        if self.repo_transform:
            cmd.extend(self.repo_transform.compute_repotransform_cmd())
        if self.color_transform:
            self.color_transform.create_ocio_config()
            cmd.extend(self.color_transform.compute_color_cmd())
        cmd.extend(["--ch", "R,G,B"])
        if debug:
            cmd.extend(["--debug", "-v"])
        cmd.extend(["-o", dest])
        return cmd

    def render_oiio(self,
                    source: str = None,
                    dest: str = None,
                    debug: bool = False) -> list:
        cmd = self.compute_oiio(
            source=source,
            dest=dest,
            debug=debug
        )
        subprocess.run(cmd)

    def render_repo_ffmpeg(self,
                           src_path: str,
                           dest_path: str,
                           cornerpin: list,
                           in_args: list = None,
                           out_args: list = None,
                           resolution: str = None,
                           debug: str = "error") -> str:
        if not resolution:
            resolution = "1920x1080"
        width, height = resolution.split("x")
        cmd = ["ffmpeg"]
        cmd.extend(["-y", "-loglevel", debug, "-hide_banner"])
        if in_args:
            cmd.extend(in_args)
        cmd.extend(["-i", src_path])
        cmd.extend(["-vf", ",".join([
                "perspective={}:{}:{}:{}:{}:{}:{}:{}:{}".format(
                    cornerpin[0], cornerpin[1],
                    cornerpin[2], cornerpin[3],
                    cornerpin[4], cornerpin[5],
                    cornerpin[6], cornerpin[7],
                    "sense=destination:eval=init"
                ),
                #"crop=(in_w-2):(in_h-2)",
                f"scale={width}:-1",
                f"crop={width}:{height}"
            ])
        ])
        if out_args:
            cmd.extend(out_args)
        cmd.append(dest_path)
        
        print(cmd)
        # subprocess.run(cmd)

        return dest_path