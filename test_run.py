import os

import lablib


# Constants
FFMPEG_PATH = "vendor/bin/ffmpeg/windows/bin"
OIIO_PATH = "vendor/bin/oiio/windows"
OCIO_PATH = "vendor/bin/ocioconfig/OpenColorIOConfigs/aces_1.2/config.ocio"
INPUT_PATH = "resources/public/plateMain/v000/BLD_010_0010_plateMain_v000.1001.exr"
EFFECT_PATH = "resources/public/effectPlateMain/v000/BLD_010_0010_effectPlateMain_v000.json"
OUTPUT_PATH = "results/BLD_010_0010_resultMain_v000.1001.png"
OUTPUT_CONFIG = "results/config.ocio"
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
img_info = lablib.utils.read_image_info(filepath)

# Compute Openpype/AYON effect.json
epr = lablib.processors.EffectsFileProcessor(input_file=EFFECT_PATH)
effect_data = epr.get_data()

# Compute color transforms and build ocio config
cpr = lablib.processors.ColorTransformProcessor(
    context = CONTEXT,
    config_path = OCIO_PATH,
    temp_config_path = OUTPUT_CONFIG,
    active_views = "sRGB, Rec.709, Log, Raw",
    ocio_environment={
        "parent_id": "whatever_id_here",
        "parent_asset": CONTEXT,
        "parent_subset": "effectPlateMain",
        "parent_version": "0"
    }
)
cpr.add_transform(effect_data["color"])

# Compute repo transforms
rpr = lablib.processors.RepoTransformProcessor(
    source_width = img_info.display_width,
    source_height = img_info.display_height,
    dest_width = OUTPUT_WIDTH,
    dest_height = OUTPUT_HEIGHT
)
rpr.add_transform(effect_data["repo"])

# Render Result with Default Renderer
render = lablib.renderers.DefaultRenderer(
    color_transform = cpr,
    repo_transform = rpr
)
render.render_oiio(
    INPUT_PATH,
    OUTPUT_PATH
)


