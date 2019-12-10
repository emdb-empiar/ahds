# -*- coding: utf-8 -*-
"""
console entry point
===================

The `ahds` command calls this script which performs the following tasks:

* parse command-line arguments
* run the command

"""

from __future__ import print_function

import argparse
import os
import sys

from . import AmiraFile, WIDTH
from .core import _str


def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(prog='ahds', description='Python tool to read and display Amira files')
    parser.add_argument('file', nargs='+', help='a valid Amira file with an optional block path')
    parser.add_argument('-s', '--load-streams', default=False, action='store_true',
                        help="whether to load data streams or not [default: False]")
    parser.add_argument('-d', '--debug', default=False, action='store_true',
                        help="display debugging information [default: False]")
    parser.add_argument('-l', '--literal', default=False, action='store_true',
                        help="display the literal header [default: False]")

    args = parser.parse_args()
    return args


def main():
    args = parse_args()

    _file, _paths = set_file_and_paths(args)

    af = get_amira_file(_file, args)

    if args.literal:
        print(get_literal(af, args), file=sys.stderr)
    if args.debug:
        print(get_debug(af, args), file=sys.stderr)
    # always show paths
    print(get_paths(_paths, af), file=sys.stderr)
    return os.EX_OK


def get_amira_file(_file, args):
    af = AmiraFile(_file, load_streams=args.load_streams, debug=args.debug)
    return af


def get_paths(_paths, af):
    if _paths:
        string = ""
        for _path in _paths:
            _path_list = _path.split('.')
            current_block = af  # the AmiraFile object
            for block in _path_list:
                current_block = getattr(current_block, block, None)
            if current_block is None:
                print("""Path '{}' not found.""".format(_path))
            else:
                string += u'*' * WIDTH + u'\n'
                string += u"ahds: Displaying path '{}'\n".format(_path)
                string += u"-" * WIDTH + "\n"
                string += _str(current_block)
    else:
        string = _str(af)
    return string


def get_debug(af, args):
    string = ""
    if args.debug:
        from pprint import pformat
        string += u"*" * WIDTH + "\n"
        string += u"ahds: Displaying parsed header data\n"
        string += u"-" * WIDTH + "\n"
        string += pformat(af.header.parsed_data) + '\n'
    return string


def get_literal(af, args):
    string = u""
    if args.literal:
        string += u'*' * WIDTH + u'\n'
        string += u"ahds: Displaying literal header\n"
        string += u"-" * WIDTH + "\n"
        string += _str(af.header.literal_data)
    return string #.encode('utf-8')


def set_file_and_paths(args):
    if len(args.file) == 1:
        _file = args.file[0]
        _paths = None
    else:
        _file = args.file[0]
        _paths = args.file[1:]
    return _file, _paths


if __name__ == "__main__":
    sys.exit(main())
