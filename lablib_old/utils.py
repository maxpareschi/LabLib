from __future__ import annotations
from dataclasses import dataclass
from copy import deepcopy
import os

import subprocess
import opentimelineio as otio


@dataclass
class ImageInfo():
    filename: str = None
    data_origin_x: int = None
    data_origin_y: int = None
    data_width: int = None
    data_height: int = None
    display_width: int = None
    display_height: int = None
    channels: int = None
    fps: float = None
    par: float = None
    timecode: str = None


def read_image_info(path: str,
                    default_timecode: str = None,
                    default_fps: float = None,
                    default_par: float = None,
                    default_channels: int = None) -> ImageInfo:
    

    if not default_timecode: default_timecode = "01:00:00:01"
    if not default_fps: default_fps = 24.0
    if not default_par: default_par = 1.0
    if not default_channels: default_channels = 3

    abspath = os.path.abspath(path).replace("\\", "/")

    result = {
        "filename": abspath,
        "data_width": None,
        "data_height": None,
        "data_origin_x": None,
        "data_origin_y": None,
        "display_width": None,
        "display_height": None,
        "channels": None,
        "fps": None,
        "par": None,
        "timecode": None
    }

    iinfo_res = deepcopy(result)
    ffprobe_res = deepcopy(result)

    iinfo_cmd = [
        "iinfo",
        "-v",
        abspath
    ]

    ffprobe_cmd = [
        "ffprobe",
        "-v", "error",
        "-select_streams", "v:0",
        "-show_entries", "format_tags=timecode:stream_tags=timecode:stream=width,height,r_frame_rate,sample_aspect_ratio",
        "-of", "default=noprint_wrappers=1",
        abspath
    ]

    iinfo_out = subprocess.run(
        iinfo_cmd,
        capture_output=True,
        text=True
    ).stdout.strip().splitlines()
    
    ffprobe_out = subprocess.run(
        ffprobe_cmd,
        capture_output=True,
        text=True
    ).stdout.strip().splitlines()
    
    for l in iinfo_out:
        if abspath in l:
            vars = l.split(": ")[1].split(",")
            size = vars[0].strip().split("x")
            channels = vars[1].strip().split(" ")
            iinfo_res.update({
                "data_width": int(size[0].strip()),
                "data_height": int(size[1].strip()),
                "display_width": int(size[0].strip()),
                "display_height": int(size[1].strip()),
                "channels": int(channels[0].strip())
            })
        if "FramesPerSecond" in l or "framesPerSecond" in l:
            vars = l.split(": ")[1].strip().split(" ")[0].split("/")
            iinfo_res.update({
                "fps": float(round(float(int(vars[0])/int(vars[1])), 3))
            })
        if "full/display size" in l:
            size = l.split(": ")[1].split("x")
            iinfo_res.update({
                "display_width": int(size[0].strip()),
                "display_height": int(size[1].strip())
            })
        if "pixel data origin" in l:
            origin = l.split(": ")[1].strip().split(",")
            iinfo_res.update({
                "data_origin_x": int(origin[0].replace("x=", "").strip()),
                "data_origin_y": int(origin[1].replace("y=", "").strip())
            })
        if "smpte:TimeCode" in l:
            iinfo_res["timecode"] = l.split(": ")[1].strip()
        if "PixelAspectRatio" in l:
            iinfo_res["par"] =  float(l.split(": ")[1].strip())

    for l in ffprobe_out:
        vars = l.split("=")
        if "width" in vars[0]:
            ffprobe_res["display_width"] = int(vars[1].strip())
        if "height" in vars[0]:
            ffprobe_res["display_height"] = int(vars[1].strip())
        if "r_frame_rate" in vars[0]:
            rate = vars[1].split("/")
            ffprobe_res["fps"] = float(round(float(int(rate[0].strip())/int(rate[1].strip())), 3))
        if "timecode" in l:
            ffprobe_res["timecode"] = vars[1]
        if "sample_aspect_ratio" in l:
            par = vars[1].split(":")
            ffprobe_res["par"] = float(int(par[0].strip())/int(par[1].strip()))

    for k, v in iinfo_res.items():
        if v != ffprobe_res[k]:
            if v and not ffprobe_res[k]:
                result[k] = v
            elif ffprobe_res[k] and not v:
                result[k] = ffprobe_res[k]
            else:
                result[k] = None
        else:
            result[k] = v
    
    if not result["data_width"]: result["data_width"] = result["display_width"]
    if not result["data_height"]: result["data_height"] = result["display_height"]
    if not result["data_origin_x"]: result["data_origin_x"] = 0
    if not result["data_origin_y"]: result["data_origin_y"] = 0
    if not result["timecode"]: result["timecode"] = default_timecode
    if not result["fps"]: result["fps"] = default_fps
    if not result["par"]: result["par"] = default_par
    if not result["channels"]: result["channels"] = default_channels

    image_info = ImageInfo(**result)

    return image_info


def offset_timecode(tc: str,
                    frame_offset: int = None,
                    fps: float = None) -> str:
    if not frame_offset:
        frame_offset = -1
    if not fps:
        fps = 24.0
    is_drop = not fps.is_integer()
    rationaltime = otio.opentime.from_timecode(tc, fps)
    frames = rationaltime.to_frames(fps)
    frames += frame_offset
    computed_rationaltime = otio.opentime.from_frames(frames, fps)
    computed_tc = otio.opentime.to_timecode(
        computed_rationaltime,
        fps,
        is_drop
    )
    return computed_tc

