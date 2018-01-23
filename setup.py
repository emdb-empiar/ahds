# -*- coding: utf-8 -*-
# setup.py
from setuptools import setup, find_packages, Extension
import numpy as np
import os

decoders = Extension('ahds.decoders', sources=['src/decodersmodule.cpp'])

here = os.path.abspath(os.path.dirname(__file__))

# long description
with open(os.path.join(here, 'README.rst')) as f:
    long_description = f.read()

setup(
      name = "ahds",
      version = "0.1.9",
      packages = find_packages(),
      author = "Paul K. Korir, PhD",
      author_email = "pkorir@ebi.ac.uk, paul.korir@gmail.com",
      description = "Python package to parse and provide access to headers and data streams in Amira(R) files",
      long_description=long_description,
      url="https://github.com/emdb-empiar/ahds.git",
      license = "Apache License",
      keywords = "header, parser, data streams",
      install_requires=["simpleparse==2.1.1", "scikit-image"],
      ext_modules=[decoders],
      include_dirs=[np.get_include()],
)
