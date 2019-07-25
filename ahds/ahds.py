# -*- coding: utf-8 -*-
# ahds.py
"""

Main entry point for console.

"""

from __future__ import print_function

import argparse
import os

# to use relative syntax make sure you have the package installed in a virtualenv in develop mode e.g. use
# pip install -e /path/to/folder/with/setup.py
# or
# python setup.py develop
from . import AmiraFile


def main():
    parser = argparse.ArgumentParser(prog='ahds', description='Python tool to read and display Amira files')
    parser.add_argument('file', help='a valid Amira file')
    parser.add_argument('-s', '--load-streams', default=False, action='store_true',
                        help="whether to load data streams or not [default: False]")
    parser.add_argument('-d', '--debug', default=False, action='store_true',
                        help="display debugging information [default: False]")

    args = parser.parse_args()

    af = AmiraFile(args.file, load_streams=args.load_streams, debug=args.debug)
    print(af)
    return os.EX_OK
