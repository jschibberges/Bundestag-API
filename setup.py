# -*- coding: utf-8 -*-

from setuptools import setup, find_packages

from pathlib import Path
this_directory = Path("__file__").parent
long_description = (this_directory / "README.md").read_text()

setup(
    author='Julian Schibberges',
    author_email="julian@schibberges.de",
    description='Python wrapper for the official Bundestag-API',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url="https://github.com/jschibberges/Bundestag-API",
    readme="README.md",
    license="MIT",
    name='bundestag_api',
    version='1.0.4',
    packages=find_packages(),
    install_requires=[
         'requests>=2.0.0',
    ],
    python_requires='>=3.7.0'
)
