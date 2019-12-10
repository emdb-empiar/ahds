# -*- coding: utf-8 -*-
"""
data_stream
===========

Classes that define data streams (DataList) in Amira (R) files

There are two main types of data streams:

* `AmiraMeshDataStream` is for `AmiraMesh` files
* `AmiraHxSurfaceDataStream` is for `HxSurface` files

Both classes inherit from `AmiraDataStream` class, which handles common functionality such as:

* initialisation with the header metadata
* the `get_data` method calls each subclass's `_decode` method

"""
from __future__ import print_function

import re
import sys
# todo: remove as soon as DataStreams class is removed
import warnings
import zlib

import numpy as np


from .core import _dict_iter_keys, _dict_iter_values, ListBlock, deprecated
from .grammar import _hyper_surface_file

# definition of numpy data types with dedicated endianess and number of bits
# they are used by the below lookup table
_np_ubytebig = np.dtype(np.uint8).newbyteorder('>')
_np_ubytelittle = np.dtype(np.uint8).newbyteorder('<')
_np_bytebig = np.dtype(np.int8).newbyteorder('>')
_np_bytelittle = np.dtype(np.int8).newbyteorder('<')
_np_shortlittle = np.dtype(np.int16).newbyteorder('<')
_np_shortbig = np.dtype(np.int16).newbyteorder('>')
_np_ushortlittle = np.dtype(np.uint16).newbyteorder('<')
_np_ushortbig = np.dtype(np.uint16).newbyteorder('>')
_np_intlittle = np.dtype(np.int32).newbyteorder('<')
_np_intbig = np.dtype(np.int32).newbyteorder('>')
_np_uintlittle = np.dtype(np.uint32).newbyteorder('<')
_np_uintbig = np.dtype(np.uint32).newbyteorder('>')
_np_longlittle = np.dtype(np.int64).newbyteorder('<')
_np_longbig = np.dtype(np.int64).newbyteorder('>')
_np_ulonglittle = np.dtype(np.uint64).newbyteorder('<')
_np_ulongbig = np.dtype(np.uint64).newbyteorder('>')
_np_floatbig = np.dtype(np.float32).newbyteorder('>')
_np_floatlittle = np.dtype(np.float32).newbyteorder('<')
_np_doublebig = np.dtype(np.float64).newbyteorder('>')
_np_doublelittle = np.dtype(np.float64).newbyteorder('<')
_np_complexbig = np.dtype(np.complex64).newbyteorder('>')
_np_complexlittle = np.dtype(np.complex64).newbyteorder('<')
_np_char = np.dtype(np.string_)

"""
lookuptable of the different data types occurring within
AmiraMesh and HyperSurface files grouped by their endianess
which is defined according to Amira Referenceguide [1] as follows

 * BINARY:               for bigendian encoded streams,

 * BINARY-LITTLE-ENDIAN: for little endian encoded streams and

 * ASCII:                for human readable encoded data

The lookup table is split into three sections:

 * True:  for all littleendian data types

 * False: for all bigendian data types and

 * the direct section mapping to the default numpy types for
   reading ASCII encoded data which have no specific endianness besides the
   bigendian characteristic intrinsic to decimal numbers.

[1] pp 519-525 # downloaded Dezember 2018 from 
   http://www1.udel.edu/ctcr/sites/udel.edu.ctcr/files/Amira%20Reference%20Guide.pdf
"""
_type_map = {
    True: {
        'byte': _np_ubytelittle,
        'ubyte': _np_ubytelittle,
        'short': _np_shortlittle,
        'ushort': _np_ushortlittle,
        'int': _np_intlittle,
        'uint': _np_uintlittle,
        'long': _np_longlittle,
        'ulong': _np_ulonglittle,
        'uint64': _np_ulonglittle,
        'float': _np_floatlittle,
        'double': _np_doublelittle,
        'complex': _np_complexlittle,
        'char': _np_char,
        'string': _np_char,
        'ascii': _np_char
    },
    False: {
        'byte': _np_ubytebig,
        'ubyte': _np_ubytebig,
        'short': _np_shortbig,
        'ushort': _np_ushortbig,
        'int': _np_intbig,
        'uint': _np_uintbig,
        'long': _np_longbig,
        'ulong': _np_ulongbig,
        'uint64': _np_ulongbig,
        'float': _np_floatbig,
        'double': _np_doublebig,
        'complex': _np_complexbig,
        'char': _np_char,
        'string': _np_char,
        'ascii': _np_char
    },
    'byte': np.dtype(np.int8),
    'ubyte': np.dtype(np.uint8),
    'short': np.dtype(np.int16),
    'ushort': np.dtype(np.uint16),
    'int': np.dtype(np.int32),
    'uint': np.dtype(np.uint32),
    'long': np.dtype(np.int64),
    'ulong': np.dtype(np.uint64),
    'uint64': np.dtype(np.uint64),
    'float': np.dtype(np.float32),
    'double': np.dtype(np.float64),
    'complex': np.dtype(np.complex64),
    'char': _np_char,
    'string': _np_char,
    'ascii': _np_char
}

# try to import native byterele_decoder binary and fallback to python implementation
try:
    # if import failed for whatever reason
    if sys.version_info[0] > 2:
        from ahds.decoders import byterle_decoder
    else:
        from .decoders import byterle_decoder
except ImportError:
    def byterle_decoder(data, output_size):
        """If the C-ext. failed to compile or is unimportable use this slower Python equivalent

        :param str data: a raw stream of data to be unpacked
        :param int output_size: the number of items when ``data`` is uncompressed
        :return np.array output: an array of ``np.uint8``
        """

        from warnings import warn
        warn("using pure-Python (instead of Python C-extension) implementation of byterle_decoder")

        input_data = np.frombuffer(data, dtype=_np_ubytelittle, count=len(data))
        output = np.zeros(output_size, dtype=np.uint8)
        i = 0
        count = True
        repeat = False
        no = None
        j = 0
        while i < len(input_data):
            if count:
                no = input_data[i]
                if no > 127:
                    no &= 0x7f  # 2's complement
                    count = False
                    repeat = True
                    i += 1
                    continue
                else:
                    i += 1
                    count = False
                    repeat = False
                    continue
            elif not count:
                if repeat:
                    # value = input_data[i:i + no]
                    repeat = False
                    count = True
                    # output[j:j+no] = np.array(value)
                    output[j:j + no] = input_data[i:i + no]
                    i += no
                    j += no
                    continue
                elif not repeat:
                    # value = input_data[i]
                    # output[j:j+no] = value
                    output[j:j + no] = input_data[i]
                    i += 1
                    j += no
                    count = True
                    repeat = False
                    continue

        assert j == output_size

        return output

# define common alias for the selected byterle_decoder implementation
hxbyterle_decode = byterle_decoder


def hxzip_decode(data, output_size):
    """Decode HxZip data stream

    :param str data: a raw stream of data to be unpacked
    :param int output_size: the number of items when ``data`` is uncompressed
    :return np.array output: an array of ``np.uint8``
    """
    return np.frombuffer(zlib.decompress(data), dtype=_np_ubytelittle, count=output_size)


def set_data_stream(name, header):
    """Factory function used by AmiraHeader to determine the type of data stream present"""
    if header.filetype == 'AmiraMesh':
        return AmiraMeshDataStream(name, header)
    elif header.filetype == 'HyperSurface':
        return AmiraHxSurfaceDataStream(name, header)


class AmiraDataStream(ListBlock):
    """"""
    __slots__ = ('_stream_data', '_header')

    def __init__(self, name, header):
        self._header = header  # contains metadata for extracting streams
        self._stream_data = None
        super(AmiraDataStream, self).__init__(name)

    @property
    def load_stream(self):
        """Reports whether data streams are loaded or not"""
        return self._header.load_streams

    def get_data(self):
        """Decode and return the stream data in this stream"""
        try:
            assert len(self._stream_data) > 0
        except AssertionError:
            raise ValueError('empty stream found')
        return self._decode(self._stream_data)


class AmiraMeshDataStream(AmiraDataStream):
    """Class that defines an AmiraMesh data stream"""

    def read(self):
        """Extract the data streams from the AmiraMesh file"""
        with open(self._header.filename, 'rb') as f:
            # rewind the file pointer to the end of the header
            f.seek(len(self._header))
            start = int(self.data_index)  # this data streams index
            end = start + 1
            if self._header.data_stream_count == start:  # this is the last stream
                data = f.read()
                _regex = ".*?\n@{}\n(?P<stream>.*)\n".format(start).encode('ASCII')
                regex = re.compile(_regex, re.S)
                match = regex.match(data)
                _stream_data = match.group('stream')
                self._stream_data = _stream_data[:-1] if _stream_data[-1] == 10 else _stream_data
            else:
                data = f.read()
                _regex = ".*?\n@{}\n(?P<stream>.*)\n@{}\n".format(start, end).encode('ASCII')
                regex = re.compile(_regex, re.S)
                match = regex.match(data)
                self._stream_data = match.group('stream')

    def _decode(self, data):
        """Performs data stream decoding by introspecting the header information"""
        # determine the new output shape
        # take into account shape and dimension
        if isinstance(self.shape, tuple):
            if self.dimension > 1:
                new_shape = tuple(list(self.shape) + [self.dimension])
            else:
                new_shape = (self.shape, )
        elif isinstance(self.shape, int):
            if self.dimension > 1:
                new_shape = tuple([self.shape, self.dimension])
            else:
                new_shape = (self.shape, )
        # first we handle binary files
        # NOTE ON HOW LATTICES ARE STORED
        # AmiraMesh files state the dimensions of the lattice as nx, ny, nz
        # The data is stored such that the first value has index (0, 0, 0) then
        # (1, 0, 0), ..., (nx-1, 0, 0), (0, 1, 0), (1, 1, 0), ..., (nx-1, 1, 0)
        # In other words, the first index changes fastest.
        # The last index is thus the stack index
        # (see pg. 720 of https://assets.thermofisher.com/TFS-Assets/MSD/Product-Guides/user-guide-amira-software.pdf
        if self._header.format == 'BINARY':
            # _type_map[endianness] uses endianness = True for endian == 'LITTLE'
            is_little_endian = self._header.endian == 'LITTLE'
            if self.format is None:
                return np.frombuffer(
                    data,
                    dtype=_type_map[is_little_endian][self.type]
                ).reshape(*new_shape)
            elif self.format == 'HxZip':
                return np.frombuffer(
                    zlib.decompress(data),
                    dtype=_type_map[is_little_endian][self.type]
                ).reshape(*new_shape)
            elif self.format == 'HxByteRLE':
                size = int(np.prod(np.array(self.shape)))
                return hxbyterle_decode(
                    data,
                    size
                ).reshape(*new_shape)
            else:
                raise ValueError('unknown data stream format: \'{}\''.format(self.format))
        # explicit instead of assumption
        elif self._header.format == 'ASCII':
            return np.fromstring(
                data,
                dtype=_type_map[self.type],
                sep="\n \t"
            ).reshape(*new_shape)
        else:
            raise ValueError("unknown file format: {}".format(self._header.format))


class AmiraHxSurfaceDataStream(AmiraDataStream):
    """Class that defines an Amira HxSurface data stream"""

    def read(self):
        """Extract the data streams from the HxSurface file"""
        with open(self._header.filename, 'rb') as f:
            # rewind the file pointer to the end of the header
            f.seek(len(self._header))
            data = f.read()
            # get the vertex count and streams
            _vertices_regex = r".*?\n" \
                              r"Vertices (?P<vertex_count>\d+)\n" \
                              r"(?P<streams>.*)".encode('ASCII')
            vertices_regex = re.compile(_vertices_regex, re.S)
            match_vertices = vertices_regex.match(data)
            # todo: fix for full.surf and simple.surf
            # print(f"streams: {match_vertices.group('streams')}")
            vertex_count = int(match_vertices.group('vertex_count'))
            # get the patches
            # fixme: general case for NBranchingPoints, NVerticesOnCurves, BoundaryCurves being non-zero
            stream_regex = r"(?P<vertices>.*?)\n" \
                           r"NBranchingPoints (?P<branching_point_count>\d+)\n" \
                           r"NVerticesOnCurves (?P<vertices_on_curves_count>\d+)\n" \
                           r"BoundaryCurves (?P<boundary_curve_count>\d+)\n" \
                           r"Patches (?P<patch_count>\d+)\n" \
                           r"(?P<patches>.*)".encode('ASCII')
            match_streams = re.match(stream_regex, match_vertices.group('streams'), re.S)
            # instatiate the vertex block
            vertices_block = AmiraHxSurfaceDataStream('Vertices', self._header)
            # set the data for this stream
            vertices_block._stream_data = match_streams.group('vertices')
            # length, type and dimension are needed for decoding
            vertices_block.add_attr('length', vertex_count)
            vertices_block.add_attr('type', 'float')
            vertices_block.add_attr('dimension', 3)
            vertices_block.add_attr('data', vertices_block.get_data())
            vertices_block.add_attr('NBranchingPoints', 0)
            vertices_block.add_attr('NVerticesOnCurves', 0)
            vertices_block.add_attr('BoundaryCurves', 0)
            # instantiate the patches block
            patches_block = AmiraHxSurfaceDataStream('Patches', self._header)
            patch_count = int(match_streams.group('patch_count'))
            patches_block.add_attr('length', patch_count)
            # get the triangles and contents of each patch
            # fixme: general case for BoundaryID, BranchingPoints being non-zero
            #  i've not seen an example with loaded fields
            # todo: consider compiling regular expressions
            # NOTE:
            # There is a subtlety with this regex:
            # It might be the case that the last part matches bytes that end in '\n[}]\n'
            # that are not the end of the stream. The only way to remede this is to include the
            # extra brace [{] so that it now matches '\n[}]\n[{]', which is more likely to
            # correspond to the end of the patch. However this introduces a problem:
            # we will not be able to match the last patch unless we also add [{] to the stream to match.
            # This also means that start_from argument will be wrong given that it will have past
            # the starting point of the next patch. This is trivial to solve because we simply
            # backtrack start_from by 1.
            # These are noted in NOTE A and NOTE B below.
            _patch_regex = r"[{]\n" \
                           r"InnerRegion (?P<patch_inner_region>.*?)\n" \
                           r"OuterRegion (?P<patch_outer_region>.*?)\n" \
                           r"BoundaryID (?P<patch_boundary_id>\d+)\n" \
                           r"BranchingPoints (?P<patch_branching_points>\d+)\n" \
                           r"\s+\n" \
                           r"Triangles (?P<triangle_count>.*?)\n" \
                           r"(?P<triangles>.*?)\n" \
                           r"[}]\n[{]".encode('ASCII')
            patch_regex = re.compile(_patch_regex, re.S)
            # start from the beginning
            start_from = 0
            for p_id in range(patch_count):
                # NOTE A
                match_patch = patch_regex.match(match_streams.group('patches') + b'{', start_from)
                patch_block = AmiraHxSurfaceDataStream('Patch', self._header)
                patch_block.add_attr('InnerRegion', match_patch.group('patch_inner_region').decode('utf-8'))
                patch_block.add_attr('OuterRegion', match_patch.group('patch_outer_region').decode('utf-8'))
                patch_block.add_attr('BoundaryID', int(match_patch.group('patch_boundary_id')))
                patch_block.add_attr('BranchingPoints', int(match_patch.group('patch_branching_points')))
                # let's now add the triangles from the patch
                triangles_block = AmiraHxSurfaceDataStream('Triangles', self._header)
                # set the raw data stream
                triangles_block._stream_data = match_patch.group('triangles')
                # decoding needs to have the length, type, and dimension
                triangles_block.add_attr('length', int(match_patch.group('triangle_count')))
                triangles_block.add_attr('type', 'int')
                triangles_block.add_attr('dimension', 3)
                # print('debug:', int(match_patch.group('triangle_count')), len(match_patch.group('triangles')))
                # print('debug:', match_patch.group('triangles')[:20])
                # print('debug:', match_patch.group('triangles')[-20:])
                triangles_block.add_attr('data', triangles_block.get_data())
                # now we can add the triangles block to the patch...
                patch_block.add_attr(triangles_block)
                # then we collate the patches
                patches_block.append(patch_block)
                # the next patch begins where the last patch ended
                # NOTE B
                start_from = match_patch.end() - 1  # backtrack by 1
            # add the patches to the vertices
            vertices_block.add_attr(patches_block)
            # add the vertices to the data stream
            self.add_attr(vertices_block)

    def _decode(self, data):
        is_little_endian = self._header.endian == 'LITTLE'
        if self._header.format == 'BINARY':
            return np.frombuffer(
                data,
                dtype=_type_map[is_little_endian][self.type]
            ).reshape(self.length, self.dimension)
        elif self._header.format == 'ASCII':
            return np.fromstring(
                data,
                dtype=_type_map[self.type],
                sep="\n \t"
            ).reshape(self.length, self.dimension)


@deprecated(
    "DataStreams class is obsolete, access data using stream_data and data attributes of corresponding metadata block attributes of AmiraHeader instance")
class DataStreams(object):
    __slots__ = ("_header", "__stream_data")

    def __init__(self, header):
        self._header = header
        with warnings.catch_warnings():
            warnings.simplefilter('ignore')
            if self._header.filetype == "AmiraMesh":
                self.__stream_data = self._header.data_pointers
            else:
                self.__stream_data = dict()
                for _streamblock in _dict_iter_keys(_hyper_surface_file):
                    _streamlist = _streamblock  # self._header._stream_loader.__class__._group_array_map.get(_streamblock,_streamblock).format('List')
                    _streamlist = getattr(self._header, _streamlist, None)
                    if _streamlist is None:
                        continue
                    self.__stream_data[_streamblock] = _streamlist

    def __getattribute__(self, attr):
        if attr in ("file", "header", "stream_data", "filetype"):
            return super(DataStreams, self).__getattribute__(attr)()
        return super(DataStreams, self).__getattribute__(attr)

    @deprecated("use <AmiraHeader>.filename instead")
    def file(self):
        return self._header.filename

    @deprecated("use AmiraHeader instance directly")
    def header(self):
        return self._header

    @deprecated(
        "access data of individual streams through corresponding attributes and dedicated stream_data and data attributes of meta data blocks")
    def stream_data(self):
        return self.__stream_data

    @deprecated("use <AmiraHeader>.filetype attribute instead")
    def filetype(self):
        return self._header.filetype

    @deprecated
    def __len__(self):
        return len(self.__stream_data)

    @deprecated
    def __iter__(self):
        return iter(_dict_iter_values(self.__stream_data))

    @deprecated
    def __getitem__(self, key):
        return self.__stream_data[key]

    @deprecated
    def __repr__(self):
        return "{} object with {} stream(s): {} ".format(
            self.__class__,
            len(self),
            ", ".join(_dict_iter_keys(self.__stream_data))
        )
