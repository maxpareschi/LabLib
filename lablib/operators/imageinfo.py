from __future__ import annotations
from copy import deepcopy
from pathlib import Path
import subprocess
from typing import List

import opentimelineio.opentime as opentime

from lablib.operators import BaseOperator
import lablib.utils as llu


class ImageInfo(BaseOperator):
    """ImageInfo class for reading image metadata."""

    filepath: Path = None
    filename: str = None
    origin_x: int = 0
    origin_y: int = 0
    width: int = 1920
    height: int = 1080
    display_width: int = width
    display_height: int = height
    channels: int = 3
    fps: float = 24.0
    par: float = 1.0
    timecode: str = None  # "01:00:00:01"

    def __init__(self, path: str, **kwargs):
        super().__init__(path, **kwargs)

        # handle path
        if not path:
            raise ValueError("Path is required.")
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {path}")
        if path.suffix not in (".exr"):
            raise ValueError(f"Invalid file type: {path}")

        self.filepath = path
        self.filename = path.name

        self.log.info(f"Reading image info from {path}")
        self.update_from_path()
        # self.read_image_info(path)

    def __gt__(self, other: ImageInfo) -> bool:
        return self.frame_no > other.frame_no

    def __lt__(self, other: ImageInfo) -> bool:
        return self.frame_no < other.frame_no

    @classmethod
    def scan(cls, directory: str | Path) -> List[ImageInfo]:
        """Scan a directory for image files and return a list of ImageInfo objects."""
        if not isinstance(directory, Path):
            directory = Path(directory)

        if not directory.is_dir():
            raise NotImplementedError(f"{directory} is not a directory")

        files = [item for item in directory.iterdir() if item.is_file()]
        if not files:
            raise FileNotFoundError(f"No image files found in {directory}")

        return [cls(file) for file in files]

    def update_from_path(self, force_ffprobe=True):
        """Update ImageInfo from a given file path.
        NOTE: force_ffprobe overrides iinfo values with ffprobe values.
              It's used since they report different framerates for testing exr files.
        """
        iinfo_res = llu.call_iinfo(self.filepath)
        ffprobe_res = llu.call_ffprobe(self.filepath)

        for k, v in iinfo_res.items():
            if not v:
                continue
            self[k] = v
            if ffprobe_res.get(k) and force_ffprobe:

    @property
    def rational_time(self) -> opentime.RationalTime:
        if not all([self.timecode, self.fps]):
            # NOTE: i should use otio here
            raise Exception("no timecode and fps found")

        result = opentime.from_timecode(self.timecode, self.fps)
        return result

    @property
    def frame_no(self) -> int:
        if not self.filename:
            raise Exception("needs filename for querying frame number")
        matches = re.findall(r"\.(\d+)\.", self.filename)
        if len(matches) > 1:
            raise ValueError("can't handle multiple found frame numbers")

        result = int(matches[0])

        self.log.debug(f"frame_no = {result}")
        return result

    def read_image_info(
        self,
        path: str,
        default_timecode: str = None,
        default_fps: float = None,
        default_par: float = None,
        default_channels: int = None,
    ) -> ImageInfo:
        if default_timecode is None:
            default_timecode = "01:00:00:01"
        if default_fps is None:
            default_fps = 24.0
        if default_par is None:
            default_par = 1.0
        if default_channels is None:
            default_channels = 3

        abspath = Path(path).as_posix()

        result = {
            "filename": abspath,
            "origin_x": None,
            "origin_y": None,
            "width": None,
            "height": None,
            "display_width": None,
            "display_height": None,
            "channels": None,
            "fps": None,
            "par": None,
            "timecode": None,
        }

        iinfo_res = deepcopy(result)
        ffprobe_res = deepcopy(result)

        iinfo_cmd = ["iinfo", "-v", abspath]

        ffprobe_cmd = [
            "ffprobe",
            "-v",
            "error",
            "-select_streams",
            "v:0",
            "-show_entries",
            "format_tags=timecode:stream_tags=timecode:stream=width,height,r_frame_rate,sample_aspect_ratio",
            "-of",
            "default=noprint_wrappers=1",
            abspath,
        ]

        iinfo_out = (
            subprocess.run(iinfo_cmd, capture_output=True, text=True)
            .stdout.strip()
            .splitlines()
        )

        ffprobe_out = (
            subprocess.run(ffprobe_cmd, capture_output=True, text=True)
            .stdout.strip()
            .splitlines()
        )

        for l in iinfo_out:
            if abspath in l and l.find(abspath) < 2:
                vars = l.split(": ")[1].split(",")
                size = vars[0].strip().split("x")
                channels = vars[1].strip().split(" ")
                iinfo_res.update(
                    {
                        "width": int(size[0].strip()),
                        "height": int(size[1].strip()),
                        "display_width": int(size[0].strip()),
                        "display_height": int(size[1].strip()),
                        "channels": int(channels[0].strip()),
                    }
                )
            if "FramesPerSecond" in l or "framesPerSecond" in l:
                vars = l.split(": ")[1].strip().split(" ")[0].split("/")
                iinfo_res.update(
                    {"fps": float(round(float(int(vars[0]) / int(vars[1])), 3))}
                )
            if "full/display size" in l:
                size = l.split(": ")[1].split("x")
                iinfo_res.update(
                    {
                        "display_width": int(size[0].strip()),
                        "display_height": int(size[1].strip()),
                    }
                )
            if "pixel data origin" in l:
                origin = l.split(": ")[1].strip().split(",")
                iinfo_res.update(
                    {
                        "origin_x": int(origin[0].replace("x=", "").strip()),
                        "origin_y": int(origin[1].replace("y=", "").strip()),
                    }
                )
            if "smpte:TimeCode" in l:
                iinfo_res["timecode"] = l.split(": ")[1].strip()
            if "PixelAspectRatio" in l:
                iinfo_res["par"] = float(l.split(": ")[1].strip())

        for l in ffprobe_out:
            vars = l.split("=")
            if "width" in vars[0]:
                ffprobe_res["display_width"] = int(vars[1].strip())
            if "height" in vars[0]:
                ffprobe_res["display_height"] = int(vars[1].strip())
            if "r_frame_rate" in vars[0]:
                rate = vars[1].split("/")
                ffprobe_res["fps"] = float(
                    round(float(int(rate[0].strip()) / int(rate[1].strip())), 3)
                )
            if "timecode" in l:
                ffprobe_res["timecode"] = vars[1]
            if "sample_aspect_ratio" in l:
                par = vars[1].split(":")
                if vars[1] != "N/A":
                    ffprobe_res["par"] = float(
                        int(par[0].strip()) / int(par[1].strip())
                    )
                else:
                    ffprobe_res["par"] = 1

        for k, v in iinfo_res.items():
            ffprobe_value = ffprobe_res[k]
            if v == ffprobe_value:
                result[k] = v
            elif v and not ffprobe_value:
                result[k] = v
            elif ffprobe_value and not v:
                result[k] = ffprobe_value
            else:
                result[k] = None

        for key, default_value in (
            ("width", result["display_width"]),
            ("height", result["display_height"]),
            ("origin_x", 0),
            ("origin_y", 0),
            ("timecode", default_timecode),
            ("fps", default_fps),
            ("par", default_par),
            ("channels", default_channels),
        ):
            if not result[key]:
                result[key] = default_value

        for k, v in result.items():
            self.log.info(f"{k} = {v}")
            self[k] = v
