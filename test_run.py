import os
import json

import clique

import lablib


# System Constants
FFMPEG_PATH = "vendor/bin/ffmpeg/windows/bin"
OIIO_PATH = "vendor/bin/oiio/windows"
OCIO_PATH = "vendor/bin/ocioconfig/OpenColorIOConfigs/aces_1.2/config.ocio"

# Project Constants
SOURCE_DIR = "resources/public/plateMain/v000"
DATA_PATH = "resources/public/mock_data.json"
EFFECT_PATH = "resources/public/effectPlateMain/v000/BLD_010_0010_effectPlateMain_v000.json"
SLATE_TEMPLATE_PATH = "templates/slates/slate_generic/slate_generic.html"
STAGING_DIR = "results"
OUTPUT_WIDTH = 1920
OUTPUT_HEIGHT = 1080

# Env Setup
script_location = os.path.dirname(os.path.realpath(__file__))
os.environ["PATH"] += os.pathsep + os.path.join(script_location, FFMPEG_PATH)
os.environ["PATH"] += os.pathsep + os.path.join(script_location, OIIO_PATH)
os.environ["OCIO"] = OCIO_PATH

# Get data from Asset
with open(DATA_PATH, "r") as f:
    working_data = json.loads(f.read())

# Setup SequenceInfo operator
# IMPORTANT: if you fill the constructor by yourself you need to adhere
# to clique output: head is always with a trailing dot, tail is always
# with a leading dot. This is to have separators baked in and also
# have a clean number to use or derive.
main_seq = lablib.operators.SequenceInfo()
if len(os.listdir(SOURCE_DIR)) > 1:
    # We want just a single sequence without any other file
    # What needs to be derived is just a single clique.Collection object
    # to use the compute method in SequenceInfo. Otherwise you can
    # fill SequenceInfo by hand.
    working_sequence = clique.assemble(
        os.listdir(SOURCE_DIR),
        patterns = [clique.PATTERNS["frames"]],
        minimum_items = working_data["frameEndHandle"] - working_data["frameStartHandle"]
    )[0][0]
    main_seq.compute(working_sequence, SOURCE_DIR)
else:
    main_seq.frames = ["D:/DEV/LabLib/resources/public/plateMain/v000/BLD_010_0010_plateMain_v000.1001.exr"]
    main_seq.frame_start = 1001
    main_seq.frame_end = 1001
    main_seq.head = "BLD_010_0010_plateMain_v000."
    main_seq.tail = ".exr"
    main_seq.padding = 4
    main_seq.hash_string = "D:/DEV/LabLib/resources/public/plateMain/v000/BLD_010_0010_plateMain_v000.#.exr"
    main_seq.format_string = "D:/DEV/LabLib/resources/public/plateMain/v000/BLD_010_0010_plateMain_v000.%04d.exr"

# Read image info from first image in sequence
main_seq_info = lablib.utils.read_image_info(main_seq.frames[0])

# Compute color transformations
epr = lablib.processors.EffectsFileProcessor(EFFECT_PATH)
cpr = lablib.processors.ColorProcessor(
    operators=epr.color_operators,
    config_path=OCIO_PATH,
    staging_dir=STAGING_DIR,
    context=working_data["asset"],
    family=working_data["project"]["code"],
)
cpr.set_views(["sRGB", "Rec.709", "Log", "Raw"])

# Compute repo transformations
rpr = lablib.processors.RepoProcessor(
    operators = epr.repo_operators,
    source_width = main_seq_info.display_width,
    source_height = main_seq_info.display_height,
    dest_width = OUTPUT_WIDTH,
    dest_height = OUTPUT_HEIGHT
)

# Render the sequence
rend = lablib.renderers.DefaultRenderer(
    color_proc = cpr,
    repo_proc = rpr,
    sequence = main_seq,
    staging_dir = STAGING_DIR,
    name = "BLD_010_0010_Converted"
)
rend.set_debug(True)
rend.set_threads(8)
rend.render()

# spr = lablib.processors.SlateProcessor(
#     data = working_data,
#     
# )
# 
# rend = lablib.renderers.DefaultSlateRenderer(
# 
# )