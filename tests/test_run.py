import os
import json
import pytest

# from lablib import operators, processors, renderers, utils

# System Constants
FFMPEG_PATH = "vendor/bin/ffmpeg/windows/bin"
OIIO_PATH = "vendor/bin/oiio/windows"
OCIO_PATH = "vendor/bin/ocioconfig/OpenColorIOConfigs/aces_1.2/config.ocio"

# Project Constants
SOURCE_DIR = "resources/public/plateMain/v000"
DATA_PATH = "resources/public/mock_data.json"
EFFECT_PATH = (
    "resources/public/effectPlateMain/v000/BLD_010_0010_effectPlateMain_v000.json"
)
SLATE_TEMPLATE_PATH = "templates/slates/slate_generic/slate_generic.html"
STAGING_DIR = "results"
OUTPUT_WIDTH = 1920
OUTPUT_HEIGHT = 1080


@pytest.mark.skip(reason="Test is not implemented yet")
def test_full():
    # Env Setup
    script_location = os.path.dirname(os.path.realpath(__file__))
    os.environ["PATH"] += os.pathsep + os.path.join(script_location, FFMPEG_PATH)
    os.environ["PATH"] += os.pathsep + os.path.join(script_location, OIIO_PATH)
    os.environ["OCIO"] = OCIO_PATH

    # Get data from Asset
    with open(DATA_PATH, "r") as f:
        working_data = json.loads(f.read())

    # Setup SequenceInfo operator
    main_seq = operators.SequenceInfo().compute_longest(SOURCE_DIR)
    print(f"{main_seq = }")

    # Read image info from first image in sequence
    main_seq_info = utils.read_image_info(main_seq.frames[0])

    # Compute Effects file from AYON
    epr = processors.EffectsFileProcessor(EFFECT_PATH)

    # Compute color transformations
    cpr = processors.ColorProcessor(
        operators=epr.color_operators,
        config_path=OCIO_PATH,
        staging_dir=STAGING_DIR,
        context=working_data["asset"],
        family=working_data["project"]["code"],
        views=["sRGB", "Rec.709", "Log", "Raw"],
    )

    # Compute repo transformations
    rpr = processors.RepoProcessor(
        operators=epr.repo_operators,
        source_width=main_seq_info.display_width,
        source_height=main_seq_info.display_height,
        dest_width=OUTPUT_WIDTH,
        dest_height=OUTPUT_HEIGHT,
    )

    # Render the sequence
    rend = renderers.DefaultRenderer(
        color_proc=cpr,
        repo_proc=rpr,
        source_sequence=main_seq,
        staging_dir=STAGING_DIR,
        format=".png",
    )
    rend.set_debug(True)
    rend.set_threads(8)
    computed_seq = rend.render()

    # Compute slate
    spr = processors.SlateProcessor(
        data=working_data,
        width=OUTPUT_WIDTH,
        height=OUTPUT_HEIGHT,
        staging_dir=STAGING_DIR,
        slate_template_path=SLATE_TEMPLATE_PATH,
        is_source_linear=False,
    )

    # Render the slate
    rend_slate = renderers.DefaultSlateRenderer(
        slate_proc=spr, source_sequence=computed_seq
    )
    # rend_slate.set_debug(True)
    rend_slate.render()
