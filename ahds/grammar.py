# -*- coding: utf-8 -*-
# amira_grammar_parser.py
"""
grammar
=======

We define an EBNF grammar for Amira (R) headers to extract all metadata. In addition to that,
we also define how `HxSurface` files are structured.

This module also includes several helper functions that use the grammar resources:

*   the `get_header` function returns only the header up to the first data stream; data is returned as a decoded string (`UTF-8`);

*   the `parse_header` function applies the grammar to return a nested set of Python primitives to be transformed into an `AmiraHeader` object;

*   the `get_parsed_data` function transparently applied both above functions given the Amira (R) filename

"""

from __future__ import print_function

import re
import sys

# simpleparse
from simpleparse.parser import Parser
from simpleparse.common import numbers, strings
from simpleparse.dispatchprocessor import DispatchProcessor, getString, dispatchList, dispatch, singleMap, multiMap

from .core import _decode_string, _dict_iter_items, _dict_iter_keys
from .proc import AmiraDispatchProcessor

# on autoformat these two lines disappear; adding them here in case that happens
# from simpleparse.common import numbers, strings
# from simpleparse.dispatchprocessor import DispatchProcessor, getString, dispatchList, dispatch, singleMap, multiMap


# Amira (R) Header Grammar
amira_header_grammar = (r'''
amira                        :=    designation, tsn, comment*, tsn*, array_declarations, tsn, parameters*, materials*, data_definitions, tsn

designation                  :=    ("#", ts, filetype, ts, dimension*, ts*, format, ts, version, ts*, extra_format*, tsn) / ("#", ts, filetype, ts, version, ts, format, tsn)
filetype                     :=    "AmiraMesh" / "HyperSurface" / "Avizo"
dimension                    :=    "3D"
format                       :=    "BINARY-LITTLE-ENDIAN" / "BINARY" / "ASCII"
version                      :=    number
extra_format                 :=    "<", "hxsurface", ">"

comment                      :=    ts, ("#", ts, "CreationDate:", ts, date) / ("#", ts, xstring) , tsn
date                         :=    xstring

array_declarations           :=    array_declaration*
array_declaration            :=    ("define", ts, array_name, ts, array_dimension) / ("n", array_name, ts, array_dimension), tsn
array_name                   :=    hyphname
array_dimension              :=    number, (ts, number)*

parameters                   :=    "Parameters" , ts, parameter_list, tsn 
parameter                    :=    ts, parameter_name, ts, parameter_value, c*, tsn
parameter_name               :=    hyphname
parameter_value              :=    parameter_list / inline_parameter_value / attribute_value
parameter_list               :=    "{", tsn, ( parameter / comment )*, "}" 
attribute_value              :=    ("-"*, "\""*, ((number, (ts, number)*) / xstring)*, "\""*)
inline_parameter_value       :=    (number, (ts, number)*) / qstring

materials                    :=    "Materials" , tsn, "{", tsn*, ( parameter_list, tsn* )+, "}", tsn 

data_definitions             :=    data_definition*
data_definition              :=    array_reference , ts, "{", ts, data_type, "["*, data_dimension*, "]"*, ts, data_name, ts, "}", ts, "="*, ts*, interpolation_method*, "("*, "@", data_index, ")"* , "("*, data_format*, ","*, data_length* , ")"* , tsn
array_reference              :=    hyphname / "Field"
data_type                    :=    hyphname
data_dimension               :=    number
data_name                    :=    hyphname
data_index                   :=    number
data_format                  :=    "HxByteRLE" / "HxZip"
data_length                  :=    number
interpolation_method         :=    "Linear" / "Constant" / "EdgeElem"

hyphname                     :=    [A-Za-z_&], [-A-Za-z0-9_:]*
qstring                      :=    "\"", "["*, [-A-Za-z0-9_,.:/ tÅ�$;\n]*, "]"*, "\""
xstring                      :=    [A-Za-z], [A-Za-z0-9_\- �(\xc5)]*
number_seq                   :=    number, (ts, number)*

# silent production rules
<tsn>                        :=    [ \t\n]*            
<ts>                         :=    [ \t]*
<c>                          :=    ","
'''
                        )

# dict representing structure of hypersurface file according to Amira Reference guide
# pp 519-525 # downloaded Dezember 2018 from 
# http://www1.udel.edu/ctcr/sites/udel.edu.ctcr/files/Amira%20Reference%20Guide.pdf
_hyper_surface_file = {
    'Vertices': ['Coordinates', 3, 'float', False],
    'NBranchingPoints': [None, None, 'int', True],
    'NVerticesOnCurves': [None, None, 'int', True],
    'BoundaryCurves': {
        'Vertices': [None, 1, 'int', False],
        0: True
    },
    'Patches': {
        'InnerRegion': [None, None, 'str', False],
        'OuterRegion': [None, None, 'str', False],
        'Triangles': [None, 3, 'int', False],
        'BranchingPoints': [None, 0, 'int', True],
        'BoundaryCurves': [None, 0, 'int', True],
        0: False
    },
    'Surfaces': {
        'Region': [None, None, 'str', False],
        'Patches': [None, 0, 'int', False],
        0: True
    }
}

# string representing all valid keys within the above structure is inserted 
# in the below regular expression patterns
# todo: replace this with something more meaningful
_hyper_surface_entities = '|'.join(['|'.join(
    [_key] + ([_vk for _vk in _dict_iter_keys(_val) if isinstance(_vk, str)] if isinstance(_val, dict) else [])) for
    _key, _val in _dict_iter_items(_hyper_surface_file) if isinstance(_key, str)])

# maximum number of bytes to be rescanned at the end of the already inspected
# _stream_data array after new bytes have been read from the file. In case within this
# range a data stream marker (@<Num>) or any of the above HyperSurface section keys has
# alreday been successfully identified rescan starts at the byte following this match
# todo: replace this with something more meaningful
_rescan_overlap = max((
    max([len(_key)] + (
        [len(_vk) for _vk in _dict_iter_keys(_val) if isinstance(_vk, str)] if isinstance(_val, dict) else []))
    for _key, _val in _dict_iter_items(_hyper_surface_file)
    if isinstance(_key, str)
)) + 16

if sys.version_info[0] > 2:
    # definitions required by python3 and newer for properly parsing binary byte strings without converting
    # them first into regular UTF-8 strings

    _file_format_match = (
        re.compile(b'.*AmiraMesh.*'),
        re.compile(b'.*HyperSurface.*'),
        re.compile(b'.*Avizo.*')
    )

    # in python3 and later open(<filename>,'rb') creates a binary file stream which has to be 
    # explicitly decoded to unicode strings which are standard in python3 and later. Therefore
    # any regular expression and string used to manipulate the raw stream data also has to be
    # defined as byte string instead of regular raw pyhton string
    _strip_lineend = b'\n'
    _stream_delimiters = [
        re.compile(b"(?:^|\n)@(?P<stream>\\d+)\n", flags=re.S),
        re.compile(r"(?:^|\n)\s*(?P<stream>(?:{}))(?:\s+(?:(?P<count>\d+)|(?P<name>\w+)))?(?:\s*\n|\s+{{)".format(
            _hyper_surface_entities).encode('ASCII')),
        re.compile(b"^\\s*}", re.I)  # NOTE this is applied to reverse slice of stream_data therefore ^
    ]
else:
    # definitions required by python2.x and older which does not destinguish between string and 
    # binary byte string as standard string are still relying on ASCII and alike encoding.
    # Therefore regular stirngs can be used to define all the necessary pattern without encoding
    # them to ASCII byte string
    _file_format_match = (
        re.compile(r'.*AmiraMesh.*'),
        re.compile(r'.*HyperSurface.*'),
        re.compile(r'.*Avizo.*')
    )

    # in python2.x and before strings are per default ascii type strings and thus open(<filename>,'rb') does not 
    # return standarad filesream. Therefore all regulare expression and strings used to manipulate 
    # the raw byte stream can be formulated using regular raw strings
    _strip_lineened = r'\n}{\t '
    _stream_delimiters = [
        re.compile(r"(?:^|\n)@(?P<stream>\d+)\n", flags=re.S),
        re.compile(r"(?:^|\n)\s*(?P<stream>(?:{}))(?:\s+(?:(?P<count>\d+)|(?P<name>\w+)))?(?:\s*\n|\s+{{)".format(
            r"".join(_hyper_surface_entities))),
        re.compile(r"^\s*}'", re.I)  # NOTE this is applied to reverese slice of stream_data therefore ^
    ]


def detect_format(fn, format_bytes=50, verbose=False, *args, **kwargs):
    """Detect Amira (R) file format (AmiraMesh/Avizo or HyperSurface)
    
    :param str fn: file name
    :param int format_bytes: number of bytes in which to search for the format [default: 50]
    :param bool verbose: verbose (default) or not
    :return str file_format: either ``AmiraMesh`` or ``HyperSurface``
    """
    assert format_bytes > 0
    assert verbose in [True, False]

    with open(fn, 'rb') as f:
        rough_header = f.read(format_bytes)

        if _file_format_match[0].match(rough_header):
            file_format = "AmiraMesh"
        elif _file_format_match[1].match(rough_header):
            file_format = "HyperSurface"
        elif _file_format_match[2].match(rough_header):
            file_format = "Avizo"
        else:
            file_format = "Undefined"

    if verbose:
        print("{} file detected...".format(file_format), file=sys.stderr)

    return file_format


SEQ_MAP = [
    (b'\xc5', u'Å'.encode('utf-8')),  # Angstrom char
]


def _swap_illegal_chars(byte_seq, seq_map):
    """Replace illegal byte sequences with legal ones"""
    for s, r in seq_map:
        _byte_seq = byte_seq
        while _byte_seq.find(s) > 1:
            _byte_seq = _byte_seq.replace(s, r)
    swapped_byte_seq = _byte_seq
    return swapped_byte_seq


def get_header(fn, file_format, header_bytes=20000, verbose=False, *args, **kwargs):
    """Apply rules for detecting the boundary of the header
    
    :param str fn: file name
    :param str file_format: either ``AmiraMesh`` or ``HyperSurface``
    :param bool verbose: verbose output; default False
    :param int header_bytes: number of bytes in which to search for the header [default: 20000]
    :return str data: the header as per the ``file_format``
    """
    assert header_bytes > 0
    try:
        assert file_format in ['AmiraMesh', 'HyperSurface', 'Avizo']
    except AssertionError:
        raise ValueError("unknown file format: {}".format(file_format))

    with open(fn, 'rb') as f:
        # read a first chunk and store it in the first element of the list of header chunks
        _data = f.read(header_bytes if header_bytes >= _rescan_overlap else _rescan_overlap)

        data = _swap_illegal_chars(_data, SEQ_MAP)

        if file_format == "AmiraMesh" or file_format == "Avizo":
            if verbose:
                print("Using pattern: {}".format(_stream_delimiters[0].pattern), file=sys.stderr)
            # scan the latests chunk  for the first @<n> data block start marker
            m = _stream_delimiters[0].search(data)
            while m is None:
                _chunklen = len(data) - _rescan_overlap
                data += f.read(header_bytes)
                m = _stream_delimiters[0].search(data, _chunklen)
        elif file_format == "HyperSurface":
            if verbose:
                print("Using pattern: {}".format(_stream_delimiters[1].pattern), file=sys.stderr)
            # scan the latests chunk for the the first occurance of any of the keys of the above
            # _hyper_surface_file structure
            m = _stream_delimiters[1].search(data)
            while m is None:
                _chunklen = len(data) - _rescan_overlap
                data += f.read(header_bytes)
                m = _stream_delimiters[1].search(data, _chunklen)
        elif file_format == "Undefined":
            raise ValueError("Unable to parse undefined file")
    # cut the data before the delimter and encode the remaining byte string into ASCII
    # string in case of python 2 and UTF-8 string for python3
    return _decode_string(data[:m.start()])


def parse_header(data, verbose=False, *args, **kwargs):
    """Parse the data using the grammar specified in this module
    
    :param str data: delimited data to be parsed for metadata
    :param bool verbose: verbose output; default False
    :return list parsed_data: structured metadata
    """
    # the parser
    if verbose:
        print("Creating parser object...", file=sys.stderr)
    parser = Parser(amira_header_grammar)

    # the processor
    if verbose:
        print("Defining dispatch processor...", file=sys.stderr)
    amira_processor = AmiraDispatchProcessor()

    # parsing
    if verbose:
        print("Parsing data...", file=sys.stderr)
    success, parsed_data, next_item = parser.parse(data, production='amira', processor=amira_processor)

    if success:
        if verbose:
            print("Successfully parsed data...", file=sys.stderr)
        return parsed_data
    else:
        raise TypeError("Parse: {}\nNext: {}\n".format(parsed_data, next_item))


def get_parsed_data(fn, *args, **kwargs):
    """All above functions as a single function
    
    :param str fn: file name
    :return tuple(list,int) parsed_data,header_length: structured metadata and total number of header bytes
    """
    file_format = detect_format(fn, *args, **kwargs)
    data = get_header(fn, file_format, *args, **kwargs)
    parsed_data = parse_header(data, *args, **kwargs)
    return data, parsed_data, len(data), file_format
