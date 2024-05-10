# LabLib

Generate intermediate sequences for VFX processing using OIIO and FFMPEG!

This module aims to help by providing helper classes and functions to:
- Get basic info from videos and images using iinfo and ffprobe as a fallback.
- Read and parse effect json outputted by [AYON/Openpype](https://github.com/ynput) for pipeline automation.
- Create a custom OCIO config file for direct use.
- Create OIIO and FFMPEG matrix values to be used in filters for repositioning.
- Create correctly formed OIIO commandline strings automatically.
- Render out frames with Color and Repositioning baked in using oiiotool

**DISCLAIMER**
This is still a wip, and it's currently missing a lot of functionality.
Use at your own risk!

## Instructions
The core functionality relies on using **Processors** and **Operators** to compute the correct commandline parameters.

**Operators** are single operation classes that hold your operation parameters (translation, luts, cdls etc.)

**Processors** (usually classes such as `ColorTransformProcessor`) compute **Operators** chains together. They can be fed ordered lists of dicts (with same name attributes as Operator classes) or ordered lists of **Operators** objects, or one at a time for secondary processing between the chained operations. On compute they return their relevant section of commandline flags to be passed to oiio.

**Renderers** take care of returning the fully formed commanline command and executing it.

Please see the sample `tests/test_run.py` for an usage example.

---

## Testing
Please see `tests/test_run.py` globals for dependent binary locations.

- `poetry install`
- `poetry run pytest -s`


### Features (Planned and Done)

- [x] Repo Processor
- [x] Color Processor
- [x] Slate Processor
- [ ] Burnins Processor
- [ ] FFMPEG final compression to format
- [ ] Settings and presets from json
- [ ] Commandline parser
- [ ] QT gui (will probably never happen)

### Dev Features

- [x] Type Hints
- [ ] Docstrings
- [ ] Documentation
- [ ] Tests (probably will never happen)

---

### Required Dependencies
- Python >= 3.7 (but keep in mind that otio and ocio wheels need to be built for >= 3.11)
- [Download OIIO](https://www.patreon.com/posts/openimageio-oiio-53939451)
- [Download FFMPEG](https://www.ffmpeg.org/download.html)
- [Download OCIO Configs](https://github.com/imageworks/OpenColorIO-Configs)
- Install PyOpenColorIO: `pip install opencolorio`
- Install OpenTimelineIO: `pip install opentimelineio`
- Install Selenium: `pip install selenium`

or even better just `pip install requirements.txt` in your own virtual environment! 

