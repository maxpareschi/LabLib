import os
import json

from selenium import webdriver
from selenium.webdriver.chrome.options import Options

from lablib_old import processors as prc

root_dir = os.path.dirname(os.path.realpath(__file__)).replace("\\", "/")
staging_dir = os.path.abspath(f"{root_dir}/results")
slate_template_path = os.path.abspath("templates/slates/slate_generic/slate_generic.html")
data_path = os.path.abspath("resources/public/mock_data.json")
slate_dest_path = os.path.abspath("results/slate_screen.png")

with open(data_path, "r") as j:
    data = json.loads(j.read())

slateproc = prc.SlateProcessor(
    width=3840,
    height=2160,
    staging_dir=staging_dir,
    slate_template_path=slate_template_path,
    data=data
)

slateproc.format_slate()
res = slateproc.render_slate(slate_dest_path)
slateproc.clean_staged_files()
