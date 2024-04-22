from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import subprocess
import os
import math
import uuid

import opentimelineio as otio

from .operators import ImageInfo


class format_dict(dict):
    _placeholder = "**MISSING**"
    def __missing__(self, key) -> str: 
        return self._placeholder


def read_image_info(path: str,
                    default_timecode: str = None,
                    default_fps: float = None,
                    default_par: float = None,
                    default_channels: int = None) -> ImageInfo:
    
    if not default_timecode: default_timecode = "01:00:00:01"
    if not default_fps: default_fps = 24.0
    if not default_par: default_par = 1.0
    if not default_channels: default_channels = 3

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
        if abspath in l and l.find(abspath) < 2:
            vars = l.split(": ")[1].split(",")
            size = vars[0].strip().split("x")
            channels = vars[1].strip().split(" ")
            iinfo_res.update({
                "width": int(size[0].strip()),
                "height": int(size[1].strip()),
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
                "origin_x": int(origin[0].replace("x=", "").strip()),
                "origin_y": int(origin[1].replace("y=", "").strip())
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
            if vars[1] != "N/A":
                ffprobe_res["par"] = float(int(par[0].strip())/int(par[1].strip()))
            else:
                ffprobe_res["par"] = 1

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
    
    if not result["width"]: result["width"] = result["display_width"]
    if not result["height"]: result["height"] = result["display_height"]
    if not result["origin_x"]: result["origin_x"] = 0
    if not result["origin_y"]: result["origin_y"] = 0
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


def get_staging_dir() -> str:
    temp_dir = Path(
        os.environ.get("TEMP", os.environ["TMP"]),
        "lablib",
        str(uuid.uuid4())).resolve().as_posix()
    return temp_dir


def zero_matrix() -> list[list[float]]:
    return [[0.0 for i in range(3)] for j in range(3)]


def identity_matrix() -> list[list[float]]:
    return translate_matrix([0.0, 0.0])


def translate_matrix(t: list[float]) -> list[list[float]]:
    return [
        [1.0, 0.0, t[0]],
        [0.0, 1.0, t[1]],
        [0.0, 0.0, 1.0]
    ]


def rotate_matrix(r: float) -> list[list[float]]:
    rad = math.radians(r)
    cos = math.cos(rad)
    sin = math.sin(rad)
    return [
        [cos, -sin, 0.0],
        [sin, cos, 0.0],
        [0.0, 0.0, 1.0]
    ]


def scale_matrix(s: list[float]) -> list[list[float]]:
    return [
        [s[0], 0.0, 0.0],
        [0.0, s[1], 0.0],
        [0.0, 0.0, 1.0]
    ]


def mirror_matrix(x: bool = False) -> list[list[float]]:
    dir = [1.0, -1.0] if not x else [-1.0, 1.0]
    return scale_matrix(dir)


def mult_matrix(m1: list[list[float]],
                m2: list[list[float]]) -> list[list[float]]:
    return [[sum(a * b for a, b in zip(m1_row, m2_col)) for m2_col in zip(*m2)] for m1_row in m1]


def mult_matrix_vector(m: list[list[float]],
                       v: list[float]) -> list[float]:
    result = [0.0, 0.0, 0.0]
    for i in range(len(m)):
        for j in range(len(v)):
            result[i] += m[i][j] * v[j]
    return result


def flip_matrix(w: float) -> list[list[float]]:
    result = identity_matrix()
    chain = [
        translate_matrix([w, 0.0]),
        mirror_matrix(x = True)
    ]
    for m in chain:
        result = mult_matrix(result, m)
    return result


def flop_matrix(h: float) -> list[list[float]]:
    result = identity_matrix()
    chain = [
        translate_matrix([0.0, h]),
        mirror_matrix()
    ]
    for m in chain:
        result = mult_matrix(result, m)
    return result


def transpose_matrix(m: list[list[float]]) -> list[list[float]]:
    res = identity_matrix()
    for i in range(len(m)):
        for j in range(len(m[0])):
            res[i][j] = m[j][i]
    return res


def matrix_to_44(m: list[list[float]]) -> list[list[float]]:
    result = m
    result[0].insert(2, 0.0)
    result[1].insert(2, 0.0)
    result[2].insert(2, 0.0)
    result.insert(2, [0.0, 0.0, 1.0, 0.0])
    return result


def matrix_to_list(m: list[list[float]]) -> list[float]:
    result = []
    for i in m:
        for j in i:
            result.append(str(j))
    return result


def matrix_to_csv(m: list[list[float]]) -> str:
        l = []
        for i in m:
            for k in i:
                l.append(str(k))
        return ",".join(l)


def matrix_to_cornerpin(m: list[list[float]],
                        w: int,
                        h: int,
                        origin_upperleft: bool = True) -> list:
    cornerpin = []
    if origin_upperleft:
        corners = [[0, h, 1], [w, h, 1], [0, 0, 1], [w, 0, 1]]
    else:
        corners = [[0, 0, 1], [w, 0, 1], [0, h, 1], [w, h, 1]]
    transformed_corners = [mult_matrix_vector(m, corner) for corner in corners]
    transformed_corners = [[corner[0] / corner[2], corner[1] / corner[2]] for corner in transformed_corners]
    for i, corner in enumerate(transformed_corners):
        x, y = corner
        cornerpin.extend([x,y])
    return cornerpin


def calculate_matrix(t: list[float],
                     r: float,
                     s: list[float],
                     c: list[float]) -> list[list[float]]:
    c_inv = [-c[0], -c[1]]
    center = translate_matrix(c)
    center_inv = translate_matrix(c_inv)
    translate = translate_matrix(t)
    rotate = rotate_matrix(r)
    scale = scale_matrix(s)
    result = mult_matrix(translate, center)
    result = mult_matrix(result, scale)
    result = mult_matrix(result, rotate)
    result = mult_matrix(result, center_inv)
    return result
