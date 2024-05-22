# Configuration file for the Sphinx documentation builder.
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Path setup --------------------------------------------------------------

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.

import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "scancodeio.settings")

# -- Project information -----------------------------------------------------

project = "ScanCode.io"
copyright = "nexB Inc."
author = "nexB Inc."


# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named "sphinx.ext.*") or your custom
# ones.
extensions = [
    "sphinx.ext.autodoc",
    "sphinxcontrib_django",
    "sphinx_rtd_dark_mode",  # For the Dark Mode
]

# Add any paths that contain templates here, relative to this directory.
templates_path = ["_templates"]

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]


# -- Autodoc -----------------------------------------------------------------

# The default options for autodoc directives.
# They are applied to all autodoc directives automatically.
# It must be a dictionary which maps option names to the values.
autodoc_default_options = {
    # Keep the source code order for the autodoc content, as we want to keep
    # the processing order for the Pipelines doc.
    "member-order": "bysource",
    "exclude-members": (
        "DoesNotExist, "
        "MultipleObjectsReturned, "
        "objects, "
        "from_db, "
        "get_absolute_url, "
        "get_next_by_created_date, "
        "get_previous_by_created_date"
    ),
}

# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
html_theme = "sphinx_rtd_theme"

# The style name to use for Pygments highlighting of source code.
pygments_style = "emacs"

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
# html_static_path = ["_static"]

master_doc = "index"

# user starts in light mode (Default Mode)
default_dark_mode = False
