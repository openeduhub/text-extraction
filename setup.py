#!/usr/bin/env python3
from setuptools import setup
from text_extraction._version import __version__

setup(
    name="text-extraction",
    version=__version__,
    description="Extract text from URLs, discarding technical artifacts",
    author="",
    author_email="",
    packages=["text_extraction"],
    install_requires=[
        d for d in open("requirements.txt").readlines() if not d.startswith("--")
    ],
    package_dir={"": "."},
    entry_points={
        "console_scripts": [
            "text-extraction = text_extraction.webservice:main",
        ]
    },
)
