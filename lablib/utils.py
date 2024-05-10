from __future__ import annotations
import os
import math
import uuid
import logging
from pathlib import Path
from typing import List

import opentimelineio as otio


log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)


class format_dict(dict):
    _placeholder = "**MISSING**"

    def __missing__(self, key) -> str:
        return self._placeholder


def offset_timecode(tc: str, frame_offset: int = None, fps: float = None) -> str:
    if not frame_offset:
        frame_offset = -1
    if not fps:
        fps = 24.0
    is_drop = not fps.is_integer()
    rationaltime = otio.opentime.from_timecode(tc, fps)
    frames = rationaltime.to_frames(fps) + frame_offset
    computed_rationaltime = otio.opentime.from_frames(frames, fps)
    return otio.opentime.to_timecode(computed_rationaltime, fps, is_drop)


def get_staging_dir() -> str:
    return (
        Path(os.environ.get("TEMP", os.environ["TMP"]), "lablib", str(uuid.uuid4()))
        .resolve()
        .as_posix()
    )


def zero_matrix() -> List[List[float]]:
    return [[0.0] * 3 for _ in range(3)]


def identity_matrix() -> List[List[float]]:
    return translate_matrix([0.0, 0.0])


def translate_matrix(t: List[float]) -> List[List[float]]:
    return [[1.0, 0.0, t[0]], [0.0, 1.0, t[1]], [0.0, 0.0, 1.0]]


def rotate_matrix(r: float) -> List[List[float]]:
    rad = math.radians(r)
    cos = math.cos(rad)
    sin = math.sin(rad)
    return [[cos, -sin, 0.0], [sin, cos, 0.0], [0.0, 0.0, 1.0]]


def scale_matrix(s: List[float]) -> List[List[float]]:
    return [[s[0], 0.0, 0.0], [0.0, s[1], 0.0], [0.0, 0.0, 1.0]]


def mirror_matrix(x: bool = False) -> List[List[float]]:
    direction = [1.0, -1.0] if not x else [-1.0, 1.0]
    return scale_matrix(direction)


def mult_matrix(m1: List[List[float]], m2: List[List[float]]) -> List[List[float]]:
    return [
        [sum(a * b for a, b in zip(m1_row, m2_col)) for m2_col in zip(*m2)]
        for m1_row in m1
    ]


def mult_matrix_vector(m: List[List[float]], v: List[float]) -> List[float]:
    result = [0.0, 0.0, 0.0]
    for i in range(len(m)):
        for j in range(len(v)):
            result[i] += m[i][j] * v[j]
    return result


def flip_matrix(w: float) -> List[List[float]]:
    result = identity_matrix()
    chain = [translate_matrix([w, 0.0]), mirror_matrix(x=True)]
    for m in chain:
        result = mult_matrix(result, m)
    return result


def flop_matrix(h: float) -> List[List[float]]:
    result = identity_matrix()
    chain = [translate_matrix([0.0, h]), mirror_matrix()]
    for m in chain:
        result = mult_matrix(result, m)
    return result


def transpose_matrix(m: List[List[float]]) -> List[List[float]]:
    res = identity_matrix()
    for i in range(len(m)):
        for j in range(len(m[0])):
            res[i][j] = m[j][i]
    return res


def matrix_to_44(m: List[List[float]]) -> List[List[float]]:
    result = m
    result[0].insert(2, 0.0)
    result[1].insert(2, 0.0)
    result[2].insert(2, 0.0)
    result.insert(2, [0.0, 0.0, 1.0, 0.0])
    return result


def matrix_to_list(m: List[List[float]]) -> List[float]:
    result = []
    for i in m:
        for j in i:
            result.append(str(j))
    return result


def matrix_to_csv(m: List[List[float]]) -> str:
    l = []
    for i in m:
        for k in i:
            l.append(str(k))
    return ",".join(l)


def matrix_to_cornerpin(
    m: List[List[float]], w: int, h: int, origin_upperleft: bool = True
) -> List:
    cornerpin = []
    if origin_upperleft:
        corners = [[0, h, 1], [w, h, 1], [0, 0, 1], [w, 0, 1]]
    else:
        corners = [[0, 0, 1], [w, 0, 1], [0, h, 1], [w, h, 1]]
    transformed_corners = [mult_matrix_vector(m, corner) for corner in corners]
    transformed_corners = [
        [corner[0] / corner[2], corner[1] / corner[2]] for corner in transformed_corners
    ]
    for corner in transformed_corners:
        cornerpin.extend(corner)
    return cornerpin


def calculate_matrix(
    t: List[float], r: float, s: List[float], c: List[float]
) -> List[List[float]]:
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
