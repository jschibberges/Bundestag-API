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
    version='1.3.0',
    packages=find_packages(),
    install_requires=[
         'requests>=2.0.0',
    ],
    extras_require={
        'pandas': ['pandas>=1.2.0'],
    },
    python_requires='>=3.7.0',
    classifiers=[
        # Development Status
        'Development Status :: 4 - Beta',

        # Intended Audience
        'Intended Audience :: Developers',
        'Intended Audience :: Science/Research',
        'Intended Audience :: Education',
        'Intended Audience :: Legal Industry',
        'Intended Audience :: Information Technology',

        # License
        'License :: OSI Approved :: MIT License',

        # Natural Language
        'Natural Language :: English',
        'Natural Language :: German',

        # Operating System
        'Operating System :: OS Independent',

        # Programming Language
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Programming Language :: Python :: 3.12',
        'Programming Language :: Python :: 3 :: Only',

        # Topics
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
        'Topic :: Scientific/Engineering :: Information Analysis',
        'Topic :: Sociology :: History',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Topic :: Text Processing :: General',
        'Topic :: Database :: Front-Ends',
    ],
    keywords='bundestag api parliament germany german politics political data legislation legislative '
             'federal documents drucksache plenarprotokoll politicians government democracy deutscher-bundestag '
             'parliamentary open-data civic-tech transparency political-science policy bundesrepublik deutschland',
)
