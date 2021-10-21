# -*- coding: utf-8 -*-
# amira_grammar_parser.py
"""
Grammar to parse headers in Amira (R) files
"""

from __future__ import print_function #, unicode_literals

import re
import sys
import collections
import warnings
import functools as ft
from pprint import pprint

# simpleparse
from simpleparse.parser import Parser
from simpleparse.common import numbers, strings, SOURCES
from simpleparse.dispatchprocessor import DispatchProcessor, getString, dispatchList, dispatch, singleMap, multiMap

# to use relative syntax make sure you have the package installed in a virtualenv in develop mode e.g. use
# pip install -e /path/to/folder/with/setup.py
# or
# python setup.py develop
from .proc import AmiraDispatchProcessor ,set_content_type_filter,clear_content_type_filter,DispatchFilter
from .core import _decode_string, ListBlock

class AHDSStreamError(ValueError):
    pass

# Amira (R) Header Grammar
amira_header_grammar = (r'''
amira                        :=    designation, tsn, comment*, tsn*, array_declarations, tsn, parameters*, materials*, data_definitions, tsn

designation                  :=    ("#", ts, filetype, ts, dimension*, ts*, format, ts, version, ts*, content_type*, tsn) / ("#", ts, filetype, ts, version, ts, format, tsn)
filetype                     :=    "AmiraMesh" / "HyperSurface"
dimension                    :=    "3D"
format                       :=    "BINARY-LITTLE-ENDIAN" / "BINARY" / "ASCII"
version                      :=    number
content_type                 :=    "<", "hxsurface", ">"

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
array_reference              :=    array_name / "Field"
data_type                    :=    hyphname
data_dimension               :=    number
data_name                    :=    hyphname
data_index                   :=    number
data_format                  :=    "HxByteRLE" / "HxZip"
data_length                  :=    number
interpolation_method         :=    "Linear" / "Constant" / "EdgeElem"

hyphname                     :=    [A-Za-z_], [A-Za-z0-9_\-]*
qstring                      :=    "\"", "["*, [A-Za-z0-9_,.\(\):/ \t]*, "]"*, "\""
xstring                      :=    [A-Za-z], [A-Za-z0-9_\- (\xef)(\xbf)(\xbd)]*
number_seq                   :=    number, (ts, number)*

# silent production rules: tsn skips over unix and windows line endings not just unix 
<tsn>                        :=    [ \t\r\n]*
<ts>                         :=    [ \t]*
<c>                          :=    ","
'''
)

# dict representin structure of hypersurface file according to Amira Reference guide
# pp 519-525 # downloaded Dezember 2018 from 
# http://www1.udel.edu/ctcr/sites/udel.edu.ctcr/files/Amira%20Reference%20Guide.pdf
_group_array_declarations = 'array_declarations'
_group_boundaraycurve = 'BoundaryCurve{}'
_group_parameters = 'parameters'
_group_patch = 'Patch{}'
_group_surface = 'Surface{}'
_hyper_surface_file = {
    # <stream_name>: [<group_stream_belongs_to>|[<group1>,<group2>,...],<Block.Name>,<itemsize>|[<itemsize_group1>,<itemsize_group2>,...],<datatype>|[<datatype_group1>,<datatype_group2>,...],<optional>]
    # array_declaration: Vertices #
    # data_definition: Vertices { float[3] Coordinates }
    # optional: False
    # format: ASCII,Binary,Binary Little Endian
    b'Vertices': [
        [_group_array_declarations,'Coordinates', 3, 'float', False],
        [_group_boundaraycurve,'Vertices', 1, 'int', False]
    ],
    # parameters: NBranchingPoints
    # datatype: int
    # optional: True
    # format: ASCII
    b'NBranchingPoints': [_group_array_declarations,'NBranchingPoints', None, 'int', True],
    # parameters: NVerticesOnCurves
    # datatype: int
    # optional: True
    b'NVerticesOnCurves': [_group_array_declarations,'NVerticesOnCurves', None, 'int', True],
    # array_declaration: BoundaryCurve<n>
    # optional: True
    # data_definition: Patch<n> {int BoundaryCurves}
    # optional: True
    # format: ASCII,Binary,Binary Little Endian
    b'BoundaryCurves': [
        [_group_array_declarations,_group_boundaraycurve,1,'group',True],
        [_group_patch,'BoundaryCurves', 1, 'int', True]
    ],
    # array_declaration: Patch<n>
    # optional: False
    # data_definition: Surface<n> { int Patches }
    # optional: True
    # format: ASCII,Binary,Binary Little Endian
    b'Patches': [
        [_group_array_declarations,_group_patch,1,'group',False],
        [_group_surface,'Patches', 1, 'int', False]
    ],
    # data_definition: Patch<n> {byte InnerRegion}
    # optional: False
    # format: ASCII
    b'InnerRegion': [_group_patch,'InnerRegion',None, 'char', False],
    # data_definition: Patch<n> {byte OuterRegion}
    # optional: False
    # format: ASCII
    b'OuterRegion': [_group_patch, 'OuterRegion',None, 'char', False],
    # data_definition: Patch<n> {int[3] OuterRegion}
    # optional: False
    # format: ASCII,Binary,Binary Little Endian
    b'Triangles': [_group_patch, 'Triangles',3, 'int', False],
    # data_definition: Patch<n> {int BranchingPoints}
    # optional: True
    # format: ASCII,Binary,Binary Little Endian
    b'BranchingPoints': [_group_patch,'BranchingPoints', 1 , 'int', True],
    # array_declaration: Surface<n>
    # optional: True
    b'Surfaces': [_group_array_declarations,_group_surface,1,'group',True],
    # data_definition: Surface<n> { bytes Region}
    # optional: False
    # format: ASCII
    b'Region': [_group_surface,'Region', None, 'char', False],
}

_type_sizes = { 'byte':1, 'short':2, 'int':4, 'long':8, 'float':4, 'double':8,'char':1,'group':None }

# string representing all valid keys within the above structure is inserted 
# in the below regular expression patterns
# todo: replace this with something more meaningful

#_hyper_surface_entities = br'|'.join(_dict_iter_keys(_hyper_surface_file))
_hyper_surface_entities = br'|'.join(_hyper_surface_file.keys())

# maximum number of bytes to be rescanned at the end of the already inspected
# _stream_data array after new bytes have been read from the file. In case within this
# range a data block marker (@<Num>) or any of the above HyperSurface section keys has
# alreday been successfully identified rescan starts at the byte following this match
# todo: replace this with something more meaningful
#_rescan_overlap = ( ( max(len(_key) for _key in _dict_iter_keys(_hyper_surface_file) ) + 15 ) // 16 ) * 16 
_rescan_overlap = ( ( max(len(_key) for _key in _hyper_surface_file.keys() ) + 15 ) // 16 ) * 16 

# TODO do we need to distinguish here or could binary version be used for both as string in python2 is 
# anyway ascii and not unicode string

_file_format_match = re.compile(br'^\s*#\s*(?P<format>AmiraMesh|HyperSurface)(?:\s+|$)')

# in python3 and later open(<filename>,'rb') creates a binary file stream which has to be 
# explicitly decoded to unicode strings which are standard in python3 and later. Therefore
# any regular expression and string used to manipulate the raw stream data also has to be
# defined as byte string instead of regular raw pyhton string
_strip_lineend = b'\n'
_stream_delimiters = [
    # pattern for locating stream_header in binary and ascii AmiraMesh type file
    re.compile(br"(?:^|\n)[^\S\n]*@(?P<stream>\d+)[^\S\n]*\n", flags=re.S),
    # pattern for locating stream_header in binary and ascii HyperSurface type file
    re.compile(
        br"(?:^|\n)[^\S\n]*(?P<stream>(?:"+_hyper_surface_entities+ br"))(?:[^\S\n]+(?:(?P<count>\d+)|(?P<string>(?:\w|[^\S\n])+)))?(?P<group>(?:[^\S\n]*(?:\n[^\S\n]*)?\{)+)?[^\S\n]*\n"
    ),
    # same as above for ascii type files which may contain comments will be completed below
    re.compile(br'#[^\n]*(?=\n|$)'),
    # search for end of stream either  followed by closing } and optionally opening { or by name of next stream
    re.compile(br"(?P<stop>\}(?:(?:[^\S\n]|\n)*\{)?[^\S\n]*\n|(?:" + _hyper_surface_entities + b"))", re.I),
    re.compile(br'}(?:\s*{)?')
]
# pattern for locating stream_header and comments in ascii HyperSurface type file
_stream_delimiters[3] = re.compile(_stream_delimiters[3].pattern + br'|' + _stream_delimiters[2].pattern,re.S)
# pattern for locating stream_header and comments in ascii AmiraMesh type file
_stream_delimiters[2] = re.compile(_stream_delimiters[0].pattern + br'|' + _stream_delimiters[2].pattern)
group_end = re.compile(br'}}')

_empty_stream_data = b''
_split_item_counter = re.compile(r'^(?P<basename>(?:\D|\d+(?=\D))+)(?P<itemcount>\d+)$')


def next_amiramesh_binary_stream(fhnd,stream_bytes=32768,stream_data = _empty_stream_data,**kwargs):
    """
    reads the data for the next AmiraMesh data stream 

    :param file fhnd: the file handle to read from
    :param int stream_bytes: number of bytes to read at once, in case of binary AmiraMesh
        file this must be the total number of bytes covered by the stream
    :param bytes stream_data: the resual bytes which remained from a previous call
    returns the encoded data for the current stream, the bytes remaining from current read
        the index of the next stream if any and the offset of the next stream
    """
    read_bytes = stream_bytes + _rescan_overlap - len(stream_data)
    if read_bytes > 0:
        stream_data += fhnd.read(read_bytes)
    next_stream = _stream_delimiters[0].search(stream_data,0)
    if next_stream is not None:
        next_stream_index = int(next_stream.group('stream'))
        stream_remainder = len(stream_data) - next_stream.end()
        return stream_data[:next_stream.start()],stream_data[-stream_remainder:],next_stream_index,fhnd.tell() - stream_remainder
    stream_tail = stream_data[stream_bytes:]
    stream_data = stream_data[:stream_bytes]
    at_end_of_file = fhnd.read(_rescan_overlap)
    if len(stream_data) >= stream_bytes:
        stream_remainder = len(stream_tail) + len(at_end_of_file)
        return stream_data,stream_tail + at_end_of_file,-1,(-1 if not at_end_of_file else fhnd.tell() - stream_remainder)
    return stream_data,_empty_stream_data,-1,-1
    
            
def next_amiramesh_ascii_stream(fhnd,stream_bytes=32768,stream_data = _empty_stream_data,**kwargs):
    read_bytes = stream_bytes + _rescan_overlap - len(stream_data)
    if read_bytes > 0:
        stream_data += fhnd.read(read_bytes)
    at_end_of_file = stream_data
    stream_data = b''
    continue_scanning_at = 0
    while at_end_of_file:
        stream_data += at_end_of_file
        next_stream = _stream_delimiters[2].search(stream_data,continue_scanning_at)
        if next_stream is not None:
            next_stream_index = next_stream.group('stream')
            if next_stream_index is not None:
                next_stream_index = int(next_stream_index)
                stream_remainder = len(stream_data) - next_stream.end()
                return stream_data[:next_stream.start()],stream_data[-stream_remainder :],next_stream_index,fhnd.tell() - stream_remainder
            # strip comment from streamcontent, do not remove newline
            continue_scanning_at = next_stream.start()
            if len(stream_data) - next_stream.end() > _rescan_overlap:
                at_end_of_file = stream_data[next_stream.end():]
                stream_data = stream_data[:next_stream.start()]
                continue
            stream_data = stream_data[:next_stream.start()] + stream_data[next_stream.end():]
            at_end_of_file = fhnd.read(stream_bytes)
            continue
        continue_scanning_at = len(stream_data) - _rescan_overlap
        at_end_of_file = fhnd.read(stream_bytes)
    return stream_data,_empty_stream_data,-1,-1

def readbytes(fhnd,count,stream_data,drop_data = False,**kwargs):
    missing_bytes = count - len(stream_data)
    if missing_bytes < 1:
        return (None if drop_data else stream_data[:count]),stream_data[count:]
    at_end_of_file = fhnd.read(missing_bytes)
    return ( None if drop_data else stream_data + at_end_of_file),_empty_stream_data

def collect_hypersurface_ascii_stream(fhnd,count,stream_data,stream_bytes = 32768,drop_data = False,**kwargs):
    if not stream_data:
        warnings.warn("can this be reached at all?? or is it a bug or a corrupted file as no stream end found??",RuntimeWarning)# pragma: nocover
        stream_data = fhnd.read(stream_bytes - len(stream_data) if stream_bytes > _rescan_overlap else _rescan_overlap) # pragma: nocover
    at_end_of_file = stream_data
    stream_data = b''
    continue_scanning_at = 0
    next_stream = None
    while at_end_of_file:
        stream_data += at_end_of_file
        next_stream = _stream_delimiters[3].search(stream_data,continue_scanning_at)
        if next_stream is None:
            at_end_of_file = fhnd.read(stream_bytes)
            continue_scanning_at = len(stream_data) - _rescan_overlap
            continue
        if next_stream.group('stop') is None:
            # strip comment from stream
            if next_stream.end() >= len(stream_data):
                # comment may span beyond bytes read so far 
                # read more bytes and try rescanning from start of current match
                at_end_of_file = fhnd.read(stream_bytes)
                continue_scanning_at = next_stream.start()
                continue
            at_end_of_file = stream_data[next_stream.end():]
            stream_data = stream_data[:next_stream.start()]
            if len(at_end_of_file) < _rescan_overlap:
                # need more bytes for properly identifying header of next stream if any
                stream_data += at_end_of_file
                at_end_of_file = fhnd.read(stream_bytes)
            continue_scanning_at = next_stream.start()
            continue
        # no decoding necessary as fed into numpy.from_string which can handle binary strings 
        return ( None if drop_data else stream_data[:next_stream.start()] ),stream_data[next_stream.start():]
    # TODO if warning than check where covered and remove nocover
    warnings.warn("can this reached at all?? or is it a bug if or a corrupted file as no stream end found??",RuntimeWarning)# pragma: nocover
    return (None if drop_data else (stream_data[:next_stream.start()] if next_stream is not None else stream_data)),_empty_stream_data # pragma: nocover

def parse_hypersurface_data(fhnd,parsed_data = dict(),verbose = False,stream_bytes=32768,stream_data = _empty_stream_data,**kwargs):
    """
    Extract Amira HyperSurface array_declarations and data_definitions and index corresponding data streams

    :param file fnhd: file handle
    :param dict parsed_data: parsed_data structure as returned by parse_header
    :param int stream_bytes: number of bytes to read at once for idtenifing the next
         data stream
    :param bytes stream_data: the remaining bytes up to the current file position not
         considered by get_header
    :return dict parsed_data: structured metadata as created by parse_header extended
         by addtional array_declarations and data_definitions
    """
    
    array_declarations = None
    designation = parsed_data[0]['designation']
    for parsed_id,parsed_item in enumerate(parsed_data):
        array_declarations = parsed_item.get('array_declarations',None)
        if array_declarations is not None:
            parsed_item_id = parsed_id + 1
            if parsed_item_id >= len(parsed_data):
                parsed_item_id = 0
            break
    else:
        parsed_item_id = 0
        array_declarations = []
        parsed_data[1:1] = [dict(array_declarations = array_declarations)]
    data_definitions = None
    for parsed_item in parsed_data[parsed_item_id:]:
        data_definitions = parsed_item.get('data_definitions',None)
        if data_definitions is not None:
            break
    else:
        for parsed_item in parsed_data[:parsed_item_id]:
            data_definitions = parsed_item.get('data_definitions',None)
            if data_definitions is not None:
                break
        else:
            data_definitions = []
            parsed_data[len(parsed_data):len(parsed_data)] =  [dict(data_definitions = data_definitions)]
    data_format = designation.get("format",'')
    if not isinstance(data_format,str) or not data_format:
        raise AHDSStreamError("'parsed_data' does not represent valid HyperSurface data_definitions")
    if data_format[:6] == "BINARY":
        extract_stream_data = readbytes
    elif data_format[:5] == "ASCII":
        extract_stream_data = collect_hypersurface_ascii_stream
    else:
        raise AHDSStreamError("'parsed_data' does not represent valid HyperSurface data_definitions")
    # stream_info,encoded_data,remaining_bytes,number_of_items,stream_offset
    group_level = 0
    item_count = 1
    group_name = ""
    array_name = ""
    max_items = 0
    # strange replacement for nonlocal statement as python2 does not recognize it
    # clear parse_hypersurface_data. after switch to python3 only
    def iter_hypersurface_stream(stream_data):
        # TODO uncomment after switching to python3 only and convert remaining_bytes to closure variable
        # continue_scanning_at and fhnd are implicitly in python2 as they are not modified inhere but
        # accessible
        #nonlocal remaining_bytes
        #nonlocal continue_scanning_at
        #nonlocal fhnd
        iter_hypersurface_stream.remaining_bytes = stream_data
        if len(stream_data)>_rescan_overlap:
            at_end_of_file = stream_data
        else:
            at_end_of_file = fhnd.read(stream_bytes)
            iter_hypersurface_stream.remaining_bytes += at_end_of_file
        while at_end_of_file:
            #iter_hypersurface_stream.force_expand = False
            yield iter_hypersurface_stream.remaining_bytes
            if len(iter_hypersurface_stream.remaining_bytes) - continue_scanning_at <= _rescan_overlap:# or iter_hypersurface_stream.force_expand:
                at_end_of_file = fhnd.read(stream_bytes)
                iter_hypersurface_stream.remaining_bytes += at_end_of_file
        else:
            if iter_hypersurface_stream.remaining_bytes:
                # yield the tail one last time to ensure all
                # relevant tail bytes are parsed
                yield iter_hypersurface_stream.remaining_bytes

                
    continue_scanning_at = 0
    array_id = ''
    for stream_data in iter_hypersurface_stream(stream_data):
        next_stream = _stream_delimiters[1].search(stream_data, continue_scanning_at)
        if next_stream is None:
            continue_scanning_at = len(stream_data) - _rescan_overlap if len(stream_data) > _rescan_overlap else 0
            continue
        if _stream_delimiters[4].search(stream_data,0,next_stream.start()) is not None:
            if group_level > 0:
                item_count += 1
                if item_count > max_items:
                    group_level -= 1
                    item_count = max_items = 0
                else:
                    array_name = array_id.format(item_count)
                    array_declarations.append(
                        dict(
                            array_name = array_name,
                            array_dimension = 0,
                            array_link = dict(
                                 array_parent = group_name,
                                 array_itemid = item_count
                            )
                        )
                    )
        stream_name = next_stream.group("stream")
        # if _stream_delimiters regular expression for HyperSurface stream headers is not
        # broken than stream group must be valid string or next_stream would be None and thus
        # would not trigger assert here
        assert stream_name is not None , "'{}' unknown HyperSurface file stream: blame ahds team".format(_decode_string(stream_name))
        stream_info = _hyper_surface_file.get(stream_name,None)
        # if the _hyper_surface_file table and the _stream_delimiters regular expression table are in
        # sync than this can not occur. In other words code would be severly broken if this assert would be
        # ever triggered
        assert stream_info is not None,"'{}' unknown HyperSurface file stream: blame ahds team".format(_decode_string(stream_name))
        if isinstance(stream_info[0],(list,tuple)):
            assert len(stream_info) > group_level,"'{}' invalid table len ({}) for group_level {}: blame ahds team".format(_decode_string(stream_name),len(stream_info),group_level)
            stream_info =  stream_info[group_level]
        stream_name = _decode_string(stream_name)
        # <stream_name>: [<group_stream_belongs_to>,<Block.Name>,<itemsize>,<datatype>,<optional>]
        num_items = next_stream.group("count")
        if stream_info[3] == 'group':
            if max_items - item_count > 0:
                raise AHDSStreamError("{} items of '{}' group missing".format(max_items - item_count,group_name))
            if group_level > 0 or stream_info[0] is not _group_array_declarations:
                raise AHDSStreamError("HyperSurface sub groups not suported")
            if num_items is None:
                raise AHDSStreamError("Itemcount not readable on stream '{}'".format(stream_name))
            max_items = int(num_items)
            if max_items > 0:
                group_level = 1
                group_name = stream_name
                array_id = stream_info[1]
                item_count = 1
                array_name = stream_info[1].format(item_count)
                array_declarations.extend((
                    dict(
                        array_name = group_name,
                        array_dimension = max_items + 1,
                        array_blocktype = ListBlock
                    ),
                    dict(
                        array_name = array_name,
                        array_dimension = 0,
                        array_link = dict(
                            array_parent = group_name,
                            array_itemid = item_count
                        )
                    )
                ))
            elif not stream_info[4]:
                raise AHDSStreamError("{} group is mandatory".format(stream_info[1]))
            iter_hypersurface_stream.remaining_bytes = stream_data[next_stream.end():]
            continue_scanning_at = 0
            continue
        if stream_info[2] is not None:
            if num_items is not None:
                num_items = int(num_items)
                num_bytes = num_items * stream_info[2] * _type_sizes[stream_info[3]]
                stream_offset = fhnd.tell() - len(stream_data) + next_stream.end()
                encoded_data,iter_hypersurface_stream.remaining_bytes = extract_stream_data(fhnd,num_bytes,stream_data[next_stream.end():],stream_bytes = stream_bytes,**kwargs)
            else: # pragma: nocover
                # TODO for now do not cover until defined whether hit at all or can go or be converted into 
                # bad stream AHDSStreamError
                encoded_data,iter_hypersurface_stream.remaining_bytes = _decode_string(next_stream.group("string")),stream_data[next_stream.end():]
                stream_offset = fhnd.tell() - len(stream_data) + next_stream.end('string')
                raise AHDSStreamError("'{}' ({}): '{}' stream has element count but does not provide number of items".format(fhnd.name,fhnd.tell() - len(stream_data) + next_stream.start(),stream_name))
        elif num_items is not None:
            encoded_data,iter_hypersurface_stream.remaining_bytes = int(num_items),stream_data[next_stream.end():]
            num_items = None
            stream_offset = fhnd.tell() - len(stream_data) + next_stream.end('count')
        else:
            encoded_data,iter_hypersurface_stream.remaining_bytes = _decode_string(next_stream.group("string")),stream_data[next_stream.end():]
            stream_offset = fhnd.tell() - len(stream_data) + next_stream.end('string')
        continue_scanning_at = 0
        if stream_name == "Vertices":
            if group_level == 0:
                array_declarations.append(
                    dict(
                        array_name = stream_name,
                        array_dimension = num_items
                    )
                )
                data_definitions.append(
                    dict(
                        array_reference = stream_name,
                        data_name = stream_info[1],
                        data_index = -1,
                        data_dimension = stream_info[2],
                        data_type = stream_info[3],
                        stream_offset = stream_offset,
                        stream_data = encoded_data
                    )
                )
                continue
        elif group_level == 0:
            if num_items == None or num_items is encoded_data:
                array_declarations.append(
                    dict(
                        array_name = stream_info[1],
                        array_dimension = None,
                        stream_data = encoded_data,
                        stream_type = stream_info[3]
                    )
                )
                continue
        if array_id is not stream_info[0]:
            raise AHDSStreamError("'{}' stream not expected on '{}' group".format(stream_name,array_name))
        data_definitions.append(
            dict(
                array_reference = array_name,
                data_name = stream_info[1],
                data_index = -1,
                data_dimension = stream_info[2],
                data_type = stream_info[3],
                stream_offset = stream_offset,
                stream_data = encoded_data,
                data_shape = num_items
            )
        )
    if verbose:
        print("\nfhnd:",fhnd,"\npd",parsed_data,"\n")
    return parsed_data


class AmiraMeshParser(Parser):
    __content_type__ = None
    def __init__(self,**kwargs):
        if sys.version_info[0] > 2: # pragma: cover_py3
            super().__init__(amira_header_grammar,root='amira')
        else: # pragma: cover_py2
            Parser.__init__(self,amira_header_grammar,root='amira')
            self._27init=True
        self._kwargs = kwargs
        
    def buildProcessor(self):
        return AmiraDispatchProcessor(content_type=self.__content_type__)

class HyperSufaceParser(AmiraMeshParser):
    __content_type__ = 'hxsurface'

    def parse(self, data, production=None, processor=None, start=0, stop=None):
        if sys.version_info[0] > 2: # pragma: cover_py3
            success,parsed_data,next_item = super().parse(data,production,processor,start,stop)
        else: # pragma: cover_py2
            success,parsed_data,next_item = AmiraMeshParser.parse(self,data,production,processor,start,stop)
        if success:
            try:
                return success,parse_hypersurface_data(parsed_data = parsed_data,**self._kwargs),next_item
            except AHDSStreamError as stream_error:
                if self._kwargs.get('verbose',False):
                    stream_error.args += (success,parsed_data,next_item)
                raise
        return success,parsed_data,next_item
            

def get_header(fhnd, header_bytes=16384, check_format=False, verbose = False,**kwargs):
    """Apply rules for detecting the boundary of the header
    
    :param str,file fhnd: file handle
    :param int header_bytes: number of bytes in which to search for the header [default: 16384]
    :param bool check_format: if true only the file format string is returned
    :return (str,str,bytes) (file_format,header_string,data_bytes): tuple describing the file_format
            the header string and any residual data bytes following the header which have been read 
            while searching for the end of the header. 
    """
    assert header_bytes > 0

    data = fhnd.read(max(_rescan_overlap,50))
    _detected_format = _file_format_match.match(data)
    if _detected_format is not None:
        file_format = _detected_format.group('format')
        if verbose: # pragma: nocover
            print("{} file detected...".format(file_format), file=sys.stderr)
        if check_format:
            return _decode_string(file_format)
    
        if file_format == b"AmiraMesh":
            stream_delimiter = _stream_delimiters[0]
            parser_cls = AmiraMeshParser
        elif file_format == b"HyperSurface":
            stream_delimiter = _stream_delimiters[1]
            parser_cls = HyperSufaceParser
        else: # pragma: nocover # only triggered during adding support for new format
            # file_format == "Undefined":
            raise ValueError("'{}' file detected: not yet supported".format(file_format))
    else:
        if verbose: # pragma: nocover
            print("Undefined file detected...", file=sys.stderr)
        raise ValueError("Unable to parse undefined file")
    if verbose: # pragma: nocover
        print("Using pattern: {}".format(stream_delimiter.pattern), file=sys.stderr)
    # scan the latest chunk for the first @<n> data block start marker or keys listed above
    stream_data,data = data,b''
    _chunklen = 0
    while stream_data:
        data += stream_data
        m = stream_delimiter.search(data, _chunklen)
        if m is not None:
            # cut the data before the delimiter and encode the remaining byte string into ASCII
            # string in case of python 2 and UTF-8 string for python3
            data,stream_data = data[:m.start()],data[m.start():]
            break
            #return _decode_string(file_format),_decode_string(data[:m.start()]),data[m.start():]
        _chunklen = len(data) - _rescan_overlap
        stream_data = fhnd.read(header_bytes)
    parser = parser_cls(fhnd=fhnd,stream_data=stream_data,verbose=verbose,**kwargs)
    # parsing
    if verbose: # pragma: nocover
        print("Parsing data...", file=sys.stderr)
    try:
        success, parsed_data, next_item = parser.parse(_decode_string(data))
    except AHDSStreamError as err:
        if verbose:
            err.args += (len(data),data)
        raise

    if not success:
        raise TypeError("Parse: {}\nNext: {}\n".format(parsed_data, next_item))
    if verbose: # pragma: nocover
        print("Successfully parsed data...", file=sys.stderr)
        return _decode_string(file_format),parsed_data,len(data),data
    return _decode_string(file_format),parsed_data,len(data),None


