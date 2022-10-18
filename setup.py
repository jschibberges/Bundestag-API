# -*- coding: utf-8 -*-

from setuptools import setup, find_packages

setup(
    author='Julian Schibberges',
    description='Python wrapper for the official Bundestag-API',
    name='bundestag_api',
    version='0.0.1',
    packages=find_packages(),
    install_requires=[
         'requests>=2.28.1',
    ],
    python_requires='>=3.8.8'
)
