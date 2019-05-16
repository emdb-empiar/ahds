# -*- coding: utf-8 -*-
# setup.py
from setuptools import setup, find_packages, Extension
import numpy as np
import os
from ahds import AHDS_VERSION

decoders = Extension(
    'ahds.decoders',
    sources=['src/decodersmodule.cpp'],
)

here = os.path.abspath(os.path.dirname(__file__))

# long description
with open(os.path.join(here, 'README.rst')) as f:
    long_description = f.read()

setup(
    name="ahds",
    version=AHDS_VERSION,
    packages=find_packages(),
    author="Paul K. Korir, PhD",
    author_email="pkorir@ebi.ac.uk, paul.korir@gmail.com",
    description="Python package to parse and provide access to headers and data streams in Amira (R) files",
    long_description=long_description,
    long_description_content_type='text/x-rst',
    url="https://github.com/emdb-empiar/ahds.git",
    license="Apache License",
    keywords="header, parser, data streams",
    setup_requires=["numpy"],
    # additional dependencies to prevent failed install due to no support for Py27
    install_requires=["simpleparse==2.1.1", "scikit-image<0.14", "networkx==2.2", "scipy<1.2"],
    ext_modules=[decoders],
    include_dirs=[np.get_include()],
)
