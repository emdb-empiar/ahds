# -*- coding: utf-8 -*-
# setup.py
from __future__ import print_function
import os
import sys

# fixme: how can I pre-install numpy???
from subprocess import Popen, PIPE

AHDS_VERSION = '0.2.0.dev0'

print('xxxxxxx', file=sys.stderr)
with open("requirements.txt", 'r') as f:
    for row in f:
        if row[0] == "#":
            continue
        print("Attempting to install {}...".format(row.strip()))
        cmd = "pip install {}".format(row.strip())
        print(cmd)
        p = Popen(cmd, stdout=PIPE, stderr=PIPE, shell=True)
        o, e = p.communicate()
print('xxxxxxx', file=sys.stderr)
import numpy as np

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

if sys.version_info[0] > 2:
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
        install_requires=["simpleparse>=2.1.1", "scikit-image"],
        ext_modules=[decoders],
        include_dirs=[np.get_include()],
        entry_points={
            'console_scripts': [
                'ahds = ahds.ahds:main',
            ]
        }
    )
else:
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
        install_requires=["simpleparse==2.1.1", "scikit-image<0.14", "scipy<1.2"],
        ext_modules=[decoders],
        include_dirs=[np.get_include()],
        entry_points={
                    'console_scripts': [
                          'ahds = ahds.ahds:main',
                    ]
              }
    )
