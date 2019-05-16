# -*- coding: utf-8 -*-
# amira_grammar_parser.py
"""
Grammar to parse headers in Amira (R) files
"""
from __future__ import print_function

import sys
import re
from pprint import pprint


# simpleparse
from simpleparse.parser import Parser
from simpleparse.common import numbers, strings  # @UnusedImport
from simpleparse.dispatchprocessor import DispatchProcessor, getString, dispatchList, dispatch, singleMap, multiMap  # @UnusedImport


class AmiraDispatchProcessor(DispatchProcessor):
    """Class defining methods to handle each token specified in the grammar"""
    def designation(self, (tag, left, right, taglist), buffer_):  # @UnusedVariable
        return {'designation': singleMap(taglist, self, buffer_)}
    def filetype(self, (tag, left, right, taglist), buffer_):
        return getString((tag, left, right, taglist), buffer_)
    def dimension(self, (tag, left, right, taglist), buffer_):
        return getString((tag, left, right, taglist), buffer_)
    def format(self, (tag, left, right, taglist), buffer_):
        return getString((tag, left, right, taglist), buffer_)
    def version(self, (tag, left, right, taglist), buffer_):
        return getString((tag, left, right, taglist), buffer_)
    def extra_format(self, (tag, left, right, taglist), buffer_):
        return getString((tag, left, right, taglist), buffer_)
    def comment(self, (tag, left, right, taglist), buffer_):  # @UnusedVariable
        return {'comment': singleMap(taglist, self, buffer_)}
    def date(self, (tag, left, right, taglist), buffer_):
        return getString((tag, left, right, taglist), buffer_)
    def definitions(self, (tag, left, right, taglist), buffer_):  # @UnusedVariable
        return {'definitions': dispatchList(self, taglist, buffer_)}
    def definition(self, (tag, left, right, taglist), buffer_):  # @UnusedVariable
        return singleMap(taglist, self, buffer_)
    def definition_name(self, (tag, left, right, taglist), buffer_):
        return getString((tag, left, right, taglist), buffer_)
    def definition_value(self, (tag, left, right, taglist), buffer_):  # @UnusedVariable
        _av = dispatchList(self, taglist, buffer_)
        if len(_av) == 1:
            return _av[0]
        elif len(_av) > 1:
            return _av
        else:
            raise ValueError('definition value list is empty:', _av)
    def parameters(self, (tag, left, right, taglist), buffer_):  # @UnusedVariable
        return {'parameters': dispatchList(self, taglist, buffer_)}
    def parameter(self, (tag, left, right, taglist), buffer_):  # @UnusedVariable
        return singleMap(taglist, self, buffer_)
    def nested_parameter(self, (tag, left, right, taglist), buffer_):  # @UnusedVariable
        return singleMap(taglist, self, buffer_)
    def nested_parameter_name(self, (tag, left, right, taglist), buffer_):
        return getString((tag, left, right, taglist), buffer_)
    def nested_parameter_values(self, (tag, left, right, taglist), buffer_):  # @UnusedVariable
        return dispatchList(self, taglist, buffer_)
    def nested_parameter_value(self, (tag, left, right, taglist), buffer_):  # @UnusedVariable
        return singleMap(taglist, self, buffer_)
    def name(self, (tag, left, right, taglist), buffer_):
        return getString((tag, left, right, taglist), buffer_)
    def attributes(self, (tag, left, right, taglist), buffer_):  # @UnusedVariable
        _a = dispatchList(self, taglist, buffer_)
        if _a:
            return _a
        else:
            return
    def attribute(self, (tag, left, right, taglist), buffer_):  # @UnusedVariable
        return singleMap(taglist, self, buffer_)
    def attribute_name(self, (tag, left, right, taglist), buffer_):
        return getString((tag, left, right, taglist), buffer_)
    def attribute_value(self, (tag, left, right, taglist), buffer_):  # @UnusedVariable
        _av = dispatchList(self, taglist, buffer_)
        if len(_av) == 1:
            return _av[0]
        elif len(_av) > 1:
            return _av
        elif len(_av) == 0:
            return None
        else:
            raise ValueError('attribute value list is empty:', _av)
    def nested_attributes(self, (tag, left, right, taglist), buffer_):  # @UnusedVariable
        return dispatchList(self, taglist, buffer_)
    def nested_attribute(self, (tag, left, right, taglist), buffer_):  # @UnusedVariable
        return singleMap(taglist, self, buffer_)
    def nested_attribute_name(self, (tag, left, right, taglist), buffer_):
        return getString((tag, left, right, taglist), buffer_)
    def nested_attribute_values(self, (tag, left, right, taglist), buffer_):  # @UnusedVariable
        return dispatchList(self, taglist, buffer_)
    def nested_attribute_value(self, (tag, left, right, taglist), buffer_):
        return singleMap(taglist, self, buffer_)
    def nested_attribute_value_name(self, (tag, left, right, taglist), buffer_):
        return getString((tag, left, right, taglist), buffer_)
    def nested_attribute_value_value(self, (tag, left, right, taglist), buffer_):
        _av = dispatchList(self, taglist, buffer_)
        if len(_av) == 1:
            return _av[0]
        elif len(_av) > 1:
            return _av
        elif len(_av) == 0:
            return None
        else:
            raise ValueError('nested attribute value list is empty:', _av)
    def inline_parameter(self, (tag, left, right, taglist), buffer_):
        return singleMap(taglist, self, buffer_)
    def inline_parameter_name(self, (tag, left, right, taglist), buffer_):
        return getString((tag, left, right, taglist), buffer_)
    def inline_parameter_value(self, (tag, left, right, taglist), buffer_):
        if taglist[0][0] == "qstring":
            return getString((tag, left, right, taglist), buffer_)
        else:
            return dispatchList(self, taglist, buffer_)
    def data_pointers(self, (tag, left, right, taglist), buffer_):
        return {'data_pointers': dispatchList(self, taglist, buffer_)}
    def data_pointer(self, (tag, left, right, taglist), buffer_):
        return singleMap(taglist, self, buffer_)
    def pointer_name(self, (tag, left, right, taglist), buffer_):
        return getString((tag, left, right, taglist), buffer_)
    def data_type(self, (tag, left, right, taglist), buffer_):
        return getString((tag, left, right, taglist), buffer_)
    def data_dimension(self, (tag, left, right, taglist), buffer_):
        return int(getString((tag, left, right, taglist), buffer_))
    def data_name(self, (tag, left, right, taglist), buffer_):
        return getString((tag, left, right, taglist), buffer_)
    def data_index(self, (tag, left, right, taglist), buffer_):
        return int(getString((tag, left, right, taglist), buffer_))
    def data_format(self, (tag, left, right, taglist), buffer_):
        return getString((tag, left, right, taglist), buffer_)
    def data_length(self, (tag, left, right, taglist), buffer_):
        return int(getString((tag, left, right, taglist), buffer_))
    def hyphname(self, (tag, left, right, taglist), buffer_):
        return getString((tag, left, right, taglist), buffer_)
    def xstring(self, (tag, left, right, taglist), buffer_):
        return getString((tag, left, right, taglist), buffer_)
    def qstring(self, (tag, left, right, taglist), buffer_):
        return getString((tag, left, right, taglist), buffer_)
    def number(self, (tag, left, right, taglist), buffer_):
        if taglist[0][0] == 'int':
            return int(getString((tag, left, right, taglist), buffer_))
        elif taglist[0][0] == 'float':
            return float(getString((tag, left, right, taglist), buffer_))
        else:
            return getString((tag, left, right, taglist), buffer_)
    def number_seq(self, (tag, left, right, taglist), buffer_):
        return dispatchList(self, taglist, buffer_)


# Amira (R) Header Grammar
amira_header_grammar = r'''
amira                        :=    designation, tsn, comment*, tsn*, definitions, tsn*, parameters*, tsn, data_pointers, tsn

designation                  :=    ("#", ts, filetype, ts, dimension*, ts*, format, ts, version, ts*, extra_format*, tsn) / ("#", ts, filetype, ts, version, ts, format, tsn)
filetype                     :=    "AmiraMesh" / "HyperSurface"
dimension                    :=    "3D"
format                       :=    "BINARY-LITTLE-ENDIAN" / "BINARY" / "ASCII"
version                      :=    number
extra_format                 :=    "<", "hxsurface", ">"

comment                      :=    ts, ("#", ts, "CreationDate:", ts, date) / ("#", ts, xstring) , tsn
date                         :=    xstring

definitions                  :=    definition*
definition                   :=    ("define", ts, definition_name, ts, definition_value) / ("n", definition_name, ts, definition_value), tsn
definition_name              :=    hyphname
definition_value             :=    number, (ts, number)*

parameters                   :=    "Parameters", ts, "{", tsn, parameter*, "}", tsn
parameter                    :=    nested_parameter / inline_parameter / comment

nested_parameter             :=    ts, nested_parameter_name, ts, "{", tsn, nested_parameter_values, ts, "}", tsn
nested_parameter_name        :=    hyphname
nested_parameter_values      :=    nested_parameter_value* 
nested_parameter_value       :=    ts, name, ts, ("{", tsn, attributes, ts, "}") / ("{", tsn, nested_attributes, ts, "}") / inline_parameter_value, tsn
name                         :=    hyphname

attributes                   :=    attribute*
attribute                    :=    ts, attribute_name, ts, attribute_value, c*, tsn
attribute_name               :=    hyphname
attribute_values             :=    attribute_value*
attribute_value              :=    ("-"*, "\""*, ((number, (ts, number)*) / xstring)*, "\""*)

nested_attributes            :=    nested_attribute*
nested_attribute             :=    ts, nested_attribute_name, ts, "{", tsn, nested_attribute_values, ts, "}", tsn 
nested_attribute_name        :=    hyphname
nested_attribute_values      :=    nested_attribute_value*
nested_attribute_value       :=    ts, nested_attribute_value_name, ts, nested_attribute_value_value, c*, tsn
nested_attribute_value_name  :=    hyphname
nested_attribute_value_value :=    "-"*, "\""*, ((number, (ts, number)*) / xstring)*, "\""*

inline_parameter             :=    ts, inline_parameter_name, ts, inline_parameter_value, c*, tsn
inline_parameter_name        :=    hyphname
inline_parameter_value       :=    (number, (ts, number)*) / qstring, c*

data_pointers                :=    data_pointer*
data_pointer                 :=    pointer_name, ts, "{", ts, data_type, "["*, data_dimension*, "]"*, ts, data_name, ts, "}", ts, "="*, ts, "@", data_index, "("*, data_format*, ","*, data_length*, ")"*, tsn
pointer_name                 :=    hyphname
data_type                    :=    hyphname
data_dimension               :=    number
data_name                    :=    hyphname
data_index                   :=    number
data_format                  :=    "HxByteRLE" / "HxZip"
data_length                  :=    number

hyphname                     :=    [A-Za-z_], [A-Za-z0-9_\-]*
qstring                      :=    "\"", "["*, [A-Za-z0-9_,.\(\):/ \t]*, "]"*, "\""
xstring                      :=    [A-Za-z], [A-Za-z0-9_\- (\xef)(\xbf)(\xbd)]*
number_seq                   :=    number, (ts, number)*

# silent production rules
<tsn>                        :=    [ \t\n]*            
<ts>                         :=    [ \t]*
<c>                          :=    ","
'''


def detect_format(fn, format_bytes=50, verbose=False, *args, **kwargs):
    """Detect Amira (R) file format (AmiraMesh or HyperSurface)
    
    :param str fn: file name
    :param int format_bytes: number of bytes in which to search for the format [default: 50]
    :param bool verbose: verbose (default) or not
    :return str file_format: either ``AmiraMesh`` or ``HyperSurface``
    """
    assert format_bytes > 0
    assert verbose in [True, False]

    with open(fn, 'rb') as f:
        rough_header = f.read(format_bytes)

        if re.match(r'.*AmiraMesh.*', rough_header):
            file_format = "AmiraMesh"
        elif re.match(r'.*HyperSurface.*', rough_header):
            file_format = "HyperSurface"
        else:
            file_format = "Undefined"

    if verbose:
        print("{} file detected...".format(file_format), file=sys.stderr)

    return file_format


def get_header(fn, file_format, header_bytes=20000, verbose=False, *args, **kwargs):
    """Apply rules for detecting the boundary of the header
    
    :param str fn: file name
    :param str file_format: either ``AmiraMesh`` or ``HyperSurface``
    :param int header_bytes: number of bytes in which to search for the header [default: 20000]
    :return str data: the header as per the ``file_format``
    """
    assert header_bytes > 0
    assert file_format in ['AmiraMesh', 'HyperSurface']

    with open(fn, 'rb') as f:
        rough_header = f.read(header_bytes)

        if file_format == "AmiraMesh":
            if verbose:
                print("Using pattern: (?P<data>.*)\\n@1", file=sys.stderr)
            m = re.search(r'(?P<data>.*)\n@1', rough_header, flags=re.S)
        elif file_format == "HyperSurface":
            if verbose:
                print("Using pattern: (?P<data>.*)\\nVertices [0-9]*\\n", file=sys.stderr)
            m = re.search(r'(?P<data>.*)\nVertices [0-9]*\n', rough_header, flags=re.S)
        elif file_format == "Undefined":
            raise ValueError("Unable to parse undefined file")

    # select the data
    data = m.group('data')
#     print data
#     print

    return data


def parse_header(data, verbose=False, *args, **kwargs):
    """Parse the data using the grammar specified in this module
    
    :param str data: delimited data to be parsed for metadata
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
    :return list parsed_data: structured metadata
    """
    file_format = detect_format(fn, *args, **kwargs)
    data = get_header(fn, file_format, *args, **kwargs)
    parsed_data = parse_header(data, *args, **kwargs)
    return parsed_data


def main():
    import argparse

    parser = argparse.ArgumentParser(prog='amira_grammar_parser', description='Parser for Amira (R) headers')
    parser.add_argument('amira_fn', help="name of an Amira (R) file with extension .am or .surf")
    parser.add_argument('-v', '--verbose', action='store_true', default=False, help='verbose output')
    parser.add_argument('-H', '--show-header', action='store_true', default=False, help='show raw header')
    parser.add_argument('-P', '--show-parsed', action='store_true', default=False, help='show parsed header')
    parser.add_argument('-f', '--format-bytes', type=int, default=50, help='bytes to search for file format')
    parser.add_argument('-r', '--header-bytes', type=int, default=20000, help='bytes to search for header')

    args = parser.parse_args()

    # get file format
    file_format = detect_format(args.amira_fn, format_bytes=args.format_bytes, verbose=args.verbose)

    # get the exact header
    data = get_header(args.amira_fn, file_format, header_bytes=args.header_bytes, verbose=args.verbose)

    if args.show_header:
        print("raw data:", file=sys.stderr)
        print(data, file=sys.stderr)
        print("", file=sys.stderr)

    # parse the header    
    parsed_data = parse_header(data, verbose=args.verbose)

    if args.show_parsed:
        print("parsed data:", file=sys.stderr)
        pprint(parsed_data, width=318, stream=sys.stderr)

    return 0


if __name__ == "__main__":
    sys.exit(main())