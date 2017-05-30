# -*- coding: utf-8 -*-
# setup.py
from setuptools import setup, find_packages, Extension
import numpy as np

decoders = Extension('ahds.decoders', sources=['src/decodersmodule.c'])

setup(
      name = "ahds",
      version = "0.1",
      packages = find_packages(),
      author = "Paul K. Korir, PhD",
      author_email = "pkorir@ebi.ac.uk, paul.korir@gmail.com",
      description = "Python package to parse and provide access to headers and data streams in Amira(R) files",
      license = "Apache License",
      keywords = "header, parser, data streams",
      install_requires=["simpleparse", "numpy", "scikit-image"],
      ext_modules=[decoders],
      include_dirs=[np.get_include()],
)