import os
import json

from lablib import (
    utils,
    processors
)


# Constants
FFMPEG_PATH = "vendor/bin/ffmpeg/windows/bin"
OIIO_PATH = "vendor/bin/oiio/windows"
OCIO_PATH = "vendor/bin/ocioconfig/OpenColorIOConfigs/aces_1.2/config.ocio"
INPUT_PATH = "resources/public/plateMain/v000/BLD_010_0010_plateMain_v000.1001.exr"
MOCK_DATA_PATH = "resources/public/mock_data.json"
EFFECT_PATH = "resources/public/effectPlateMain/v000/BLD_010_0010_effectPlateMain_v000.json"
SLATE_PATH = "templates/slates/slate_generic/slate_generic.html"
OUTPUT_PATH = "results/BLD_010_0010_resultMain_v000.1001.png"
OUTPUT_CONFIG = "results/ocio_staging/config.ocio"
OUTPUT_SLATE = "results/slate_staging"
OUTPUT_WIDTH = 1920
OUTPUT_HEIGHT = 1080
CONTEXT = "BLD_010_0010"


# Env setup
script_location = os.path.dirname(os.path.realpath(__file__))
os.environ["PATH"] += os.pathsep + os.path.join(script_location, FFMPEG_PATH)
os.environ["PATH"] += os.pathsep + os.path.join(script_location, OIIO_PATH)
os.environ["OCIO"] = OCIO_PATH


filepath = os.path.abspath(INPUT_PATH).replace("\\", "/")

# Read Image Info
img_info = utils.read_image_info(filepath)

with open(MOCK_DATA_PATH, "r") as f:
    mock_data = json.loads(f.read())

# Compute Openpype/AYON effect.json
epr = processors.EffectsFileProcessor(src = EFFECT_PATH)

description = {
    "parent_id": "whatever_id_here",
    "parent_asset": CONTEXT,
    "parent_subset": "effectPlateMain",
    "parent_version": "0",
    "SHOT": CONTEXT,
}

# Compute color transforms and build ocio config
cpr = processors.ColorProcessor()
cpr.set_operators(epr.color_operators)
cpr.set_views(["sRGB", "Rec.709", "Log", "Raw"])
cpr.set_description(json.dumps(description))
cpr.set_vars(**description)
cpr_path = cpr.create_config(dest = OUTPUT_CONFIG)

# Compute repo transforms
rpr = processors.RepoProcessor()
rpr.set_source_size(width = img_info.display_width,
                    height = img_info.display_height)
rpr.set_destination_size(width = OUTPUT_WIDTH,
                         height = OUTPUT_HEIGHT)
rpr.add_operators(epr.repo_operators)

# Compute slate
slt = processors.SlateProcessor()
slt.set_template_path(SLATE_PATH)
slt.set_staging_dir(OUTPUT_SLATE)
slt.set_base_sequence([img_info.filename])
slt.set_data(mock_data)
slt.set_size(width = OUTPUT_WIDTH,
             height = OUTPUT_HEIGHT)
slt.create_slate()
