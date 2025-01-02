# Configuration file for the Sphinx documentation builder.
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Path setup --------------------------------------------------------------

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#
# import os
# import sys
# sys.path.insert(0, os.path.abspath('.'))

import pak

# -- Project information -----------------------------------------------------

project   = "Pak"
copyright = "2021-2025, friedkeenan"
author    = "friedkeenan"
release   = pak.__version__


# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    "sphinx.ext.napoleon",
    "sphinx.ext.autodoc",
    "sphinx.ext.autosummary",
    "sphinx.ext.viewcode",
    "sphinx.ext.doctest",
    "sphinx_copybutton",
]

napoleon_include_private_with_doc = True
napoleon_include_special_with_doc = True

add_module_names     = False
autoclass_content    = "both"
autosummary_generate = True

# Add any paths that contain templates here, relative to this directory.
templates_path = ["_templates"]

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = []

# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
html_theme = "furo"

html_static_path = ["_static"]
html_css_files   = ["css/uniform_tables.css", "css/highlighting.css"]
html_js_files    = ["js/highlighting.js"]

# Make literal nodes like ``text`` and :class:`text` syntax-highlighted.
#
# We could instead make a custom ':python:' role and
# then explicitly use that throughout the docs, but
# that seemed to me less terse and idiomatic.
import docutils.nodes

old_literal_init = docutils.nodes.literal.__init__

def new_literal_init(self, rawsource="", text="", *children, classes=None, language="", **attributes):
    if classes is None and len(language) <= 0:
        # These settings emulate what a ':code:' directive
        # would do with its language set to 'python'.
        classes  = ["code", "highlight", "python"]
        language = "python"
    elif "highlight" not in classes and language == "":
        classes = [*classes, "code", "highlight", "python"]
        language = "python"

    return old_literal_init(self, rawsource, text, *children, classes=classes, language=language, **attributes)

docutils.nodes.literal.__init__ = new_literal_init
