# -*- coding: utf-8 -*-
# data_stream
"""
Data stream module

Here we define the set of classes that define and manage data streams




"""
from __future__ import print_function

import re
import sys
# TODO remove as soon as DataStreams class is removed
import warnings
import zlib

import numpy as np

# to use relative syntax make sure you have the package installed in a virtualenv in develop mode e.g. use
# pip install -e /path/to/folder/with/setup.py
# or
# python setup.py develop
from .core import _dict_iter_keys, _dict_iter_values, Block,ListBlock, deprecated 
from .grammar import next_amiramesh_ascii_stream, next_amiramesh_binary_stream,_rescan_overlap,set_content_type_filter,clear_content_type_filter,AHDSStreamError
    

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
    True: {# dtypes for binary little endian encoded data
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
    False: {# dtypes for binary big endian encoded data
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
    },# dtypes for for ascii encoded data 
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

try:
    from .decoders import byterle_decoder
except ImportError:
    def byterle_decoder(data, count,**kwargs):
        """If the C-ext. failed to compile or is unimportable use this slower Python equivalent

        :param str data: a raw stream of data to be unpacked
        :param int output_size: the number of items when ``data`` is uncompressed
        :return np.array output: an array of ``np.uint8``
        """

        from warnings import warn
        warn("using pure-Python (instead of Python C-extension) implementation of byterle_decoder")

        # load input data into numpy array buffer
        input_data = np.frombuffer(data, dtype=_np_ubytelittle, count=len(data))
        # output buffer 
        output = np.zeros(count, dtype=np.uint8)
        get = 0 # index of next byte to read
        put = 0 # index to write next decoded byte to
        while get < len(input_data):
            # read size of next output block
            numbytes = input_data[get]
            get += 1
            if numbytes & 0x80:
                # MSB set indicating that following block of bytes is not encoded
                # copy as is. The lower 7 Bytes provide the number of bytes to be
                # copied
                numbytes &= 0x7F
                nextput = put + numbytes
                nextget = get + numbytes
                output[put:nextput] = input_data[get:nextget]
                get = nextget
                put = nextput
                continue
            # encoded block of numbytes bytes expand
            nextput = put + numbytes
            output[put:nextput] = input_data[get]
            get += 1
            put = nextput

        assert put == count

        return output

# define common alias for the selected byterle_decoder implementation
hxbyterle_decode = byterle_decoder
def hxraw_decode(data):
    """
    noop decoder to keep code below simple happy
    """
    return data

ONDEMMAND = -1
HEADERONLY = 0
IMMEDIATE = 1

# TODO need common decision what should be the default stream policy
#      current suggestion ONDEMMAND
_stream_policy = ONDEMMAND

def set_stream_policy(policy):
    """
    sets global stream loading policy
    HEADERONLY: load file hader and structure only,
         data attribute of AmiraMesh and HyperSuface streams is not available, 
    ONDEMMAND: load and decode data on first access to data attribute of
        AmiraMesh and HyperSuface streams
    IMMEDIATE: load immediately along with the header and file structure
    """

    if policy not in (ONDEMMAND, HEADERONLY,IMMEDIATE):
        raise ValueError('stream policy must be one of HEADERONLY, ONDEMMAND, IMMEDIATE')

    global _stream_policy

    _stream_policy = policy

def get_stream_policy():
    """
    returns the global stream loading policy currently set
    """

    global _stream_policy

    return _stream_policy


# used to extract counter indices from the tail of array_names
# and collect them within a common meta_array_declaration of the
# common base_name. Is applied to reversed array_name string
# a counter is any trailing number which is preceeded by non numerical
# character exempt '-' and '_' if they are preceeded by at least one digit
_extract_trailing_counter = re.compile(r'^\d+(?![-_]\d)')

def select_array_block(array_declaration):
    """
    return Block corresponding to provided array_declaration

    currently only array_name and array_dimension keys are considered to either
    create ListBlock or Block type block. In case filter functions emmit not None
    other_meta dict than this method has to be modified to reflect the additional
    array_declaration keys injected by other_meta dict.
    """
    block_type = array_declaration.get('array_blocktype',Block)
    if issubclass(block_type,ListBlock):
        return block_type(array_declaration['array_name'],initial_len=array_declaration['array_dimension'])
    block = block_type(array_declaration['array_name'])
    block.add_attr('length',array_declaration['array_dimension'])
    return block

class AmiraSpreadSheet(ListBlock):
    """
    ListBlock joining array declarations representing columns of
    HxSpreadSheet object.
    """
    def __init__(self,name,initial_len,*args,**kwargs):
        super(AmiraSpreadSheet,self).__init__(name,initial_len,*args,**kwargs)

    @staticmethod
    def identify_columns(typed_meta_declaration,array_declaration,content_type,base_contenttype):
        """
        filter function called by AmiraDispatchProcessor to collect all array declaration
        structures which could be part of HxSpreadSheet structure
        """
        if content_type != 'HxSpreadSheet' and base_contenttype != 'HxSpreadSheet':
            return None
        
        array_name = array_declaration.get('array_name',None)
        if array_name is None:
            return None
        has_counter = _extract_trailing_counter.match(array_name[::-1])
        if has_counter is None:
            return None
        base_name = array_name[:-has_counter.end()]
        array_index = int(array_name[-has_counter.end():])
        return 'Sheet1',array_index,AmiraSpreadSheet,None,None

set_content_type_filter('HxSpreadSheet',AmiraSpreadSheet.identify_columns)

def set_data_stream(name, header,file_offset = None,encoded_data = None):
    """Factory function used by AmiraHeader to determine the type of data stream present"""
    if header.file_format == 'AmiraMesh':
        return AmiraMeshDataStream(name, header,file_offset,encoded_data)
    elif header.file_format == 'HyperSurface':
        return AmiraHxSurfaceDataStream(name, header,file_offset,encoded_data)
    raise AHDSStreamError("'{}' data stream format not supported'".format(header.file_format)) # pragma: nocover

class AmiraDataStream(ListBlock):
    """common base for all datastreams in AmiraMesh or HxSurface format"""
    __slots__ = ('_stream_data', '_header','_offset',READONLY('data'))

    def __init__(self, name, header,file_offset = None,encoded_data = None):
        self._header = header  # contains metadata for extracting streams
        if header.load_streams is not HEADERONLY:
            self._offset = file_offset
            if encoded_data is not None:
                assert self._offset is not None
                self._stream_data = encoded_data
            else:
                assert self._offset is None
        super(AmiraDataStream, self).__init__(name)


    def __getattr__(self,attr):
        if self._header.load_streams != HEADERONLY:
            if attr == "data":
                #if not self._stream_data:
                #    raise AHDSStreamError('empty stream')
                self._data = self._decode(self._stream_data)
                return self._data
            if attr == '_stream_data':
                self._read()
                assert self._offset is not None and self._offset > len(self._header)
                return self._stream_data
        raise AttributeError("'{}' type object has no '{}' attribute".format(self.__class__.name,attr))

    def __str__(self, prefix="", index=None,is_parent=False,printed = set(),name = None):
        """Convert the ListBlock into a string

        :param str prefix: prefix to signify depth in the tree
        :param int index: applies for list items [default: None]
        :returns str string: formatted string of attributes
        """
        # first we use the superclass to populate everything else
        string = super(AmiraDataStream, self).__str__(prefix=prefix, index=index,is_parent=is_parent,printed=printed,name = name)
        if self._header.load_streams == HEADERONLY:
            return string
        if self._offset is None or self._offset <= len(self._header):
            return string + "{}|  +-{}: {}\n".format(prefix,"data", "<<not loaded>>")
        try:
            return string + self._format_array(prefix,"data",self._data,80)
        except AttributeError:
            if self._header.load_streams == IMMEDIATE:
                return string + self._format_array(prefix,"data",self.data,80)
            return string + "{}|  +-{}: {}\n".format(prefix,"data", "<<not loaded>>")

def load_streams(header):
    """
    called by AmiraFile.read and AmiraHeader._load method when load_streams = IMMEDIATE was used when
    loading header of amria file or default stream loading policy is set to IMMEDIATE
    """
    if header.load_streams == HEADERONLY:
        raise AHDSStreamError("HADERONLY stream policy set for '{}' file".format(header.filename))
    if header.file_format == "HyperSurface":
        # nothing to load for HypeSurface encoded_data has either already been
        # added or is not needed
        return
    stream_with_highest_index = header.get_stream_by_index(header.data_stream_count)
    stream_with_highest_index._read()
    for validate_stream in ( 
        validate
        for validate in (
            header.get_stream_by_index(stream_index) 
            for stream_index in range(1,header.data_stream_count+1)
        )
        if validate._offset is None
    ):
        validate_stream._read()

class AmiraMeshDataStream(AmiraDataStream):
    """Class that defines an AmiraMesh data stream"""
    __decode_data__ = {
        'HxZip':(np.frombuffer,zlib.decompress),
        'HxByteRLE':(hxbyterle_decode,hxraw_decode),
        None:(np.frombuffer,hxraw_decode)
    }

    def _read(self):
        """Extract the data streams from the AmiraMesh file"""

        if self._header.load_streams == HEADERONLY:
            raise AHDSStreamError("HADERONLY stream policy for '{}' file".format(self._header.filename))
        if self._offset is not None and self._offset > len(self._header):
            # stream_data already loaded
            return
        next_stream = next_amiramesh_ascii_stream if self._header.format == 'ASCII' else next_amiramesh_binary_stream
        with open(self._header.filename, 'rb') as f:
            # rewind the file pointer to the end of the header
            current_offset = self._header.get_stream_offset(self)
            f.seek(current_offset)
            stream_data,stream_remainder,next_stream_index,next_offset = next_stream(f)
            while next_stream_index != self.data_index:
                if next_stream_index < 0:
                    raise AHDSStreamError("AmiraMesch file '{}' corrupted".format(self._header.filename))
                side_loaded_stream = self._header.get_stream_by_index(next_stream_index)
                side_loaded_stream._offset = next_offset
                num_stream_bytes = np.prod(side_loaded_stream.shape) * side_loaded_stream.dimension * _type_map[side_loaded_stream.type].itemsize
                side_loaded_stream._stream_data,stream_remainder,next_stream_index,next_offset = next_stream(
                    f,
                    stream_bytes = num_stream_bytes if num_stream_bytes > 32768 else 32768,
                    stream_data = stream_remainder,
                )
            self._offset = next_offset
            num_stream_bytes = np.prod(self.shape) * self.dimension * _type_map[self.type].itemsize
            self._stream_data,stream_remainder,next_stream_index,next_offset = next_stream(
                f,
                stream_bytes = num_stream_bytes,
                stream_data = stream_remainder
            )
            if next_stream_index >= 0:
                next_offset -= _rescan_overlap
            self._header.set_stream_offset(self,next_offset)

    def _decode(self, data):
        """Performs data stream decoding by introspecting the header information"""
        if isinstance(self.shape,np.ndarray):
            new_shape = self.shape.tolist()
        else:
            new_shape = [self.shape] if not isinstance(self.shape,(list,tuple)) else list(self.shape)
        if self.dimension > 1:
            new_shape += [self.dimension]
        # first we handle binary files
        if self._header.format == 'BINARY':
            try:
                decode,extract = self.__decode_data__[self.format]
            except KeyError:
                raise AHDSStreamError("Data stream format '{}' not supported".format(self.format))
            # _type_map[endianness] uses endianness = True for endian == 'LITTLE'
            is_little_endian = self._header.endian == 'LITTLE'
            return decode(
                extract(data),
                dtype=_type_map[is_little_endian][self.type],
                count=np.prod(new_shape).tolist()
            ).reshape(*new_shape)
        # assume the file is ASCII
        #else:
        return np.fromstring(
            data,
            dtype=_type_map[self.type],
            sep="\n \t"
        ).reshape(*new_shape)


class AmiraHxSurfaceDataStream(AmiraDataStream):
    """Class that defines an Amira HxSurface data stream"""

    def _read(self):
        if self._header.load_streams == HEADERONLY:
            raise AHDSStreamError("HADERONLY stream policy for '{}' file".format(self._header.filename))
        # nothing to read: data either already stored or not available

    def _decode(self, data):
        new_shape = [self.shape] if not isinstance(self.shape,(list,tuple)) else list(self.shape)
        if self.dimension > 1:
            new_shape += [self.dimension]
        if self._header.format == 'BINARY':
            is_little_endian = self._header.endian == 'LITTLE'
            return np.frombuffer(
                data,
                dtype=_type_map[is_little_endian][self.type]
            ).reshape(*new_shape)
        # assume file is ascii
        #elif self._header.format == 'ASCII':
        return np.fromstring(
            data,
            dtype=_type_map[self.type],
            sep="\n \t"
        ).reshape(*new_shape)

def check_stream_data(datastream): # pragma: nocover
    if datastream.file_format == "AmiraMesh":
        if datastream.format != "ASCII":
            vertices = getattr(datastream,'Nodes',None)
            if vertices is None:
                vertices = getattr(datastream,'Vertices',None)
                if vertices is None:
                    return 0
            coordinates = getattr(vertices,'Coordinates',None)
            if coordinates is None:
                coordinates = getattr(vertices,'Vertices',None)
                if coordinates is None:
                    return 0
            print(coordinates.data)
            tetrahedra = getattr(datastream,"Tetrahedra",None)
            if tetrahedra is None:
                return 0
            materials = getattr(tetrahedra,"Materials",None)
            if materials is None:
                return 0
            print(materials.data)
            return 0
        electrodes = getattr(datastream,"Electrodes",None)
        if electrodes is None:
            return 0
        leadidentifier = getattr(electrodes,"LeadIdentifer",None)
        if leadidentifier is None:
            return 0
        print(leadidentifier.data)
        return 0
    print(datastream.Vertices.Coordinates.data)
    print(datastream.Patches[1].Triangles.data)
    return 0
    
    
    

if __name__ == "__main__": # pragma: nocover
    from ahds.header import main
    import sys
    sys.exit( main(check_stream_data))
