# -*- coding: utf-8 -*-
# setup.py
from __future__ import print_function

import os
import sys

import numpy as np

AHDS_VERSION = '0.2.4'

from setuptools import setup, find_packages, Extension

"""
The build may fail on macOS. Try the following:

open /Library/Developer/CommandLineTools/Packages/macOS_SDK_headers_for_macOS_10.14.pkg

Credits: https://blog.driftingruby.com/updated-to-mojave/
"""
decoders = Extension(
    'ahds.decoders',
    sources=['src/decodersmodule.cpp'],
)

here = os.path.abspath(os.path.dirname(__file__))

# long description
with open(os.path.join(here, 'README.rst')) as f:
    long_description = f.read()

AHDS_NAME = "ahds"
AHDS_AUTHOR = "Paul K. Korir, PhD"
AHDS_AUTHOR_EMAIL = "pkorir@ebi.ac.uk, paul.korir@gmail.com"
AHDS_DESCRIPTION = "Python package to parse and provide access to headers and data streams in Amira (R) files"
AHDS_DESCRIPTION_CONTENT_TYPE = 'text/x-rst'
AHDS_URL = "https://github.com/emdb-empiar/ahds.git"
AHDS_LICENSE = "Apache License"
AHDS_KEYWORDS = "header, parser, data streams"
AHDS_ENTRY_POINT = 'ahds = ahds.ahds:main'
AHDS_CLASSIFIERS = [
    u"Development Status :: 2 - Pre-Alpha",
    u"Environment :: Console",
    u"Intended Audience :: Developers",
    u"License :: OSI Approved :: Apache Software License",
    u"Operating System :: OS Independent",
    u"Programming Language :: Python :: 2",
    u"Programming Language :: Python :: 2.7",
    u"Programming Language :: Python :: 3",
    u"Programming Language :: Python :: 3.5",
    u"Programming Language :: Python :: 3.6",
    u"Programming Language :: Python :: 3.7",
    u"Topic :: Software Development :: Libraries :: Python Modules",
    u"Topic :: Terminals",
    u"Topic :: Text Processing",
    u"Topic :: Text Processing :: Markup",
    u"Topic :: Utilities",
]

if sys.version_info[0] > 2:
    AHDS_INSTALL_REQUIRES = ["simpleparse"]
    if sys.version_info[1] > 5:
        AHDS_INSTALL_REQUIRES += ["scikit-image"]
    else:
        AHDS_INSTALL_REQUIRES += ["matplotlib<3.1", "scikit-image<0.16"]
    setup(
        name=AHDS_NAME,
        version=AHDS_VERSION,
        packages=find_packages(),
        author=AHDS_AUTHOR,
        author_email=AHDS_AUTHOR_EMAIL,
        description=AHDS_DESCRIPTION,
        long_description=long_description,
        long_description_content_type=AHDS_DESCRIPTION_CONTENT_TYPE,
        url=AHDS_URL,
        license=AHDS_LICENSE,
        keywords=AHDS_KEYWORDS,
        setup_requires=["numpy"],
        # additional dependencies to prevent failed install due to no support for Py27
        install_requires=AHDS_INSTALL_REQUIRES,
        ext_modules=[decoders],
        include_dirs=[np.get_include()],
        entry_points={
            'console_scripts': [
                AHDS_ENTRY_POINT,
            ]
        },
        classifiers=AHDS_CLASSIFIERS,
    )
else:
    setup(
        name=AHDS_NAME,
        version=AHDS_VERSION,
        packages=find_packages(),
        author=AHDS_AUTHOR,
        author_email=AHDS_AUTHOR_EMAIL,
        description=AHDS_DESCRIPTION,
        long_description=long_description,
        long_description_content_type=AHDS_DESCRIPTION_CONTENT_TYPE,
        url=AHDS_URL,
        license=AHDS_LICENSE,
        keywords=AHDS_KEYWORDS,
        setup_requires=["numpy"],
        # additional dependencies to prevent failed install due to no support for Py27
        install_requires=["simpleparse==2.1.1", "scikit-image<0.14", "scipy<1.2", "backports.shutil_get_terminal_size",
                          "networkx==2.2", "matplotlib<3.0", "PyWavelets<1.1.0", "Pillow<7.0.0"],
        ext_modules=[decoders],
        include_dirs=[np.get_include()],
        entry_points={
            'console_scripts': [
                AHDS_ENTRY_POINT,
            ]
        },
        classifiers=AHDS_CLASSIFIERS,
    )
