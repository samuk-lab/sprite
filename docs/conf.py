# Configuration file for the Sphinx documentation builder.

from __future__ import annotations

import sys
from pathlib import Path

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


project = "wisp"
copyright = "2026, wisp contributors"
author = "wisp contributors"

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

htmlhelp_basename = "wispdoc"

latex_documents = [
    (
        master_doc,
        "wisp.tex",
        "wisp Documentation",
        author,
        "manual",
    ),
]

man_pages = [(master_doc, "wisp", "wisp Documentation", [author], 1)]

texinfo_documents = [
    (
        master_doc,
        "wisp",
        "wisp Documentation",
        author,
        "wisp",
        "Build sparse depth-threshold mask BEDs from cohort alignment data or all-sites VCFs.",
        "Miscellaneous",
    ),
]
