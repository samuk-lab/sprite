# Configuration file for the Sphinx documentation builder.

from __future__ import annotations

import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


project = "sprite"
copyright = "2026, sprite contributors"
author = "sprite contributors"

with (ROOT / "pyproject.toml").open("rb") as handle:
    release = tomllib.load(handle)["project"]["version"]
version = release

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
]

source_suffix = {".rst": "restructuredtext"}
master_doc = "index"
language = "en"
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]
pygments_style = "sphinx"
smartquotes = False

html_theme = "sphinx_rtd_theme"
html_theme_options = {
    "collapse_navigation": False,
    "navigation_depth": 4,
}
html_static_path = []
html_title = f"{project} {release}"

htmlhelp_basename = "spritedoc"

latex_documents = [
    (
        master_doc,
        "sprite.tex",
        "sprite Documentation",
        author,
        "manual",
    ),
]

man_pages = [(master_doc, "sprite", "sprite Documentation", [author], 1)]

texinfo_documents = [
    (
        master_doc,
        "sprite",
        "sprite Documentation",
        author,
        "sprite",
        "Build sparse depth-threshold mask BEDs from cohort alignment data or all-sites VCFs.",
        "Miscellaneous",
    ),
]
