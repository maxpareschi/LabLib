import pytest
import logging
from pathlib import Path

from lablib.operators import ImageInfo, SequenceInfo

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)


@pytest.mark.parametrize(
    "path", ["resources/public/plateMain/v000/BLD_010_0010_plateMain_v000.1001.exr"]
)
def test_ImageInfo(path: str):
    image_info = ImageInfo(path)
    path = Path(path)
    log.info(f"{image_info = }")
    assert image_info.par == 1.0
    assert image_info.fps == 25.0
    assert image_info.width == 4382
    assert image_info.height == 2310
    assert image_info.channels == 3
    assert image_info.filepath == path
    assert image_info.filename == path.name
    assert image_info.timecode == "02:10:04:17"


@pytest.mark.parametrize("directory", ["resources/public/plateMain/v000"])
def test_ImageInfo_scan(directory: str):
    image_infos = ImageInfo.scan(directory)
    image_info = image_infos[0]

    log.info(f"{image_info = }")
    assert image_info.par == 1.0
    assert image_info.fps == 25.0
    assert image_info.width == 4382
    assert image_info.height == 2310
    assert image_info.channels == 3
    assert image_info.filepath == Path(
        directory, "BLD_010_0010_plateMain_v000.1001.exr"
    )
    assert image_info.filename == "BLD_010_0010_plateMain_v000.1001.exr"
    assert image_info.timecode == "02:10:04:17"


@pytest.mark.skip(reason="SequenceInfo is not implemented yet")
@pytest.mark.parametrize(
    "path",
    [
        "resources/public/plateMain/v000",
        "resources/public/plateMain/v001",
    ],
)
def test_SequenceInfo(path: str):
    seq_infos = SequenceInfo.scan(path)
    path = Path(path)
    log.info(f"{seq_infos = }")
    # assert image_info.par == 1.0
    # assert image_info.fps == 25.0
    # assert image_info.width == 4382
    # assert image_info.height == 2310
    # assert image_info.channels == 3
    # assert seq_info.path == path
    # assert image_info.filename == path.name
    # assert image_info.timecode == "02:10:04:17"
