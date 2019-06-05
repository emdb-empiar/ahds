# -*- coding: utf-8 -*-
# data_stream
""" module defining  all classes required to """

from __future__ import print_function

import functools as ft
import re
# TODO remove as soon as DataStrams class is removed
import warnings
import zlib

import numpy as np

# definition of numpy data types with dedicated endianess and number of bits
# they are used by the below lookup table
from .core import (
    _dict_iter_keys, _dict_iter_items, _dict_iter_values, Block, ListBlock, xrange, _decode_string, deprecated
)
from .extra import ImageSet
from .grammar import _rescan_overlap, _stream_delimiters, _hyper_surface_file

# to use relative syntax make sure you have the package installed in a virtualenv in develop mode e.g. use
# pip install -e /path/to/folder/with/setup.py
# or
# python setup.py develop


_np_ubytebig = np.dtype(np.uint8).newbyteorder('>')
_np_ubytelittle = np.dtype(np.uint8).newbyteorder('<')
_np_bytebig = np.dtype(np.int8).newbyteorder('>')
_np_bytelitle = np.dtype(np.int8).newbyteorder('<')
_np_shortlitle = np.dtype(np.int16).newbyteorder('<')
_np_shortbig = np.dtype(np.int16).newbyteorder('>')
_np_ushortlitle = np.dtype(np.uint16).newbyteorder('<')
_np_ushortbig = np.dtype(np.uint16).newbyteorder('>')
_np_intlitle = np.dtype(np.int32).newbyteorder('<')
_np_intbig = np.dtype(np.int32).newbyteorder('>')
_np_uintlitle = np.dtype(np.uint32).newbyteorder('<')
_np_uintbig = np.dtype(np.uint32).newbyteorder('>')
_np_longlitle = np.dtype(np.int64).newbyteorder('<')
_np_longbig = np.dtype(np.int64).newbyteorder('>')
_np_ulonglitle = np.dtype(np.uint64).newbyteorder('<')
_np_ulongbig = np.dtype(np.uint64).newbyteorder('>')
_np_floatbig = np.dtype(np.float32).newbyteorder('>')
_np_floatlitle = np.dtype(np.float32).newbyteorder('<')
_np_doublebig = np.dtype(np.float64).newbyteorder('>')
_np_doublelitle = np.dtype(np.float64).newbyteorder('<')
_np_complexbig = np.dtype(np.complex64).newbyteorder('>')
_np_complexlittle = np.dtype(np.complex64).newbyteorder('<')
_np_char = np.dtype(np.string_)

# lookuptable of the differnt data types occuring within
# AmiraMesh and HyperSurface files grouped by their endianess
# which is defined according to Amira Referenceguide [1] as follows
#
#  * BINARY:               for bigendian encoded streams,
#
#  * BINARY-LITTLE-ENDIAN: for little endian encoded streams and
#
#  * ASCII:                for human readable encoded data
#
# The lookup table is split into three sections:
#
#  * True:  for all littleendian data types
#
#  * False: for all bigendian data types and
#
#  * the direct section mapping to the default numpy types for
#    reading ASCII encoded data which have no specific endianness besides the
#    bigendian characteristic intrinsic to decimal numbers.
#
# [1] pp 519-525 # downloaded Dezember 2018 from 
#    http://www1.udel.edu/ctcr/sites/udel.edu.ctcr/files/Amira%20Reference%20Guide.pdf
_type_map = {
    True: {
        'byte': _np_ubytelittle,
        'ubyte': _np_ubytelittle,
        'short': _np_shortlitle,
        'ushort': _np_ushortlitle,
        'int': _np_intlitle,
        'uint': _np_uintlitle,
        'long': _np_longlitle,
        'ulong': _np_ulonglitle,
        'float': _np_floatlitle,
        'double': _np_doublelitle,
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
    'float': np.dtype(np.float32),
    'double': np.dtype(np.float64),
    'complex': np.dtype(np.complex64),
    'char': _np_char,
    'string': _np_char,
    'ascii': _np_char
}

# try to import native byterele_decoder binary and fallback to python implementation
# if import failed for whatever reason
try:
    from ahds.decoders import byterle_decoder
except ImportError:
    def byterle_decoder(data, dtype=None, count=0):
        """Python drop-in replacement for compiled equivalent
        
        :param int output_size: the number of items when ``data`` is uncompressed
        :param str data: a raw stream of data to be unpacked
        :return np.array output: an array of ``np.uint8``
        """
        from warnings import warn

        warn("using pure-Python (instead of Python C-extension) implementation of byterle_decoder")

        input_data = np.frombuffer(data, dtype=_np_ubytelittle, count=len(data))
        output = np.zeros(count, dtype=np.uint8)
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

        assert j == count

        return output

# define common alias for the selected byterle_decoder implementation

"""Decode HxRLE data stream
   
   func:: hxbyterle_decode
   if C-extension is not compiled it will use a (slower) Python equivalent
    
   :param int output_size: the number of items when ``data`` is uncompressed
   :param str data: a raw stream of data to be unpacked
   :return np.array output: an array of ``np.uint8``
"""
hxbyterle_decode = byterle_decoder


def hxzip_decode(data, dtype=None, count=0):
    """Decode HxZip data stream
    
    :param int data_size: the number of items when ``data`` is uncompressed
    :param str data: a raw stream of data to be unpacked
    :return np.array output: an array of ``np.uint8``
    """
    return np.frombuffer(zlib.decompress(data), dtype=_np_ubytelittle, count=count)


# TODO: check if there is a more performant way to express them and may be even get rid of UserList at all
# class Image(object):
#     """Encapsulates individual images"""
#
#     def __init__(self, z, array):
#         self.z = z
#         self._array = array
#         self._byte_values = np.unique(self._array)
#
#     def __getattribute__(self, attr):
#         if attr in ("array", "byte_values"):
#             return super(Image, self).__getattribute__("_" + attr)
#         if attr in ("as_contours", "as_segments"):
#             return super(Image, self).__getattribute__("_" + attr)()
#         return super(Image, self).__getattribute__(attr)
#
#     def equalise(self):
#         """Increase the dynamic range of the image"""
#         multiplier = 255 // len(self._byte_values)
#         return self._array * multiplier
#
#     def _as_contours(self):
#         """A dictionary of lists of contours keyed by byte_value"""
#         contours = dict()
#         _maskbase = np.array([False, True])
#         _indexbase = np.zeros(self._array.shape, dtype=np.int8)
#         for byte_value in self._byte_values[self._byte_values != 0]:
#             mask = _maskbase[np.equal(self._array, byte_value, out=_indexbase)]
#             found_contours = find_contours(mask, 254, fully_connected='high')  # a list of array
#             contours[byte_value] = ContourSet(found_contours)
#         return contours
#
#     def _as_segments(self):
#         return {self.z: self.as_contours}
#
#     def show(self):
#         """Display the image"""
#         with_matplotlib = True
#         try:
#             import matplotlib.pyplot as plt
#         except RuntimeError:
#             import skimage.io as io
#             with_matplotlib = False
#
#         if with_matplotlib:
#             equalised_img = self.equalise()
#
#             _, ax = plt.subplots()
#
#             ax.imshow(equalised_img, cmap='gray')
#
#             import random
#
#             for contour_set in _dict_iter_values(self.as_contours):
#                 r, g, b = random.random(), random.random(), random.random()
#                 [ax.plot(contour[:, 1], contour[:, 0], linewidth=2, color=(r, g, b, 1)) for contour in contour_set]
#
#             ax.axis('image')
#             ax.set_xticks([])
#             ax.set_yticks([])
#
#             plt.show()
#         else:
#             io.imshow(self.equalise())
#             io.show()
#
#     def __repr__(self):
#         return "<Image with dimensions {}>".format(self.array.shape)
#
#     def __str__(self):
#         return "<Image with dimensions {}>".format(self.array.shape)


# class ImageSet(UserList):
#     """Encapsulation for set of ``Image`` objects"""
#
#     def __getitem__(self, index):
#         return Image(index, self.data[index])
#
#     def __getattribute__(self, attr):
#         if attr in ("segments",):
#             return super(ImageSet, self).__getattribute__("_" + attr)()
#         return super(ImageSet, self).__getattribute__(attr)
#
#     def _segments(self):
#         """A dictionary of lists of contours keyed by z-index"""
#         segments = dict()
#         for i in xrange(len(self)):
#             image = self[i]
#             for z, contour in _dict_iter_items(image.as_segments):
#                 for byte_value, contour_set in _dict_iter_items(contour):
#                     if byte_value not in segments:
#                         segments[byte_value] = dict()
#                     if z not in segments[byte_value]:
#                         segments[byte_value][z] = contour_set
#                     else:
#                         segments[byte_value][z] += contour_set
#
#         return segments
#
#     def __repr__(self):
#         return "<ImageSet with {} images>".format(len(self))
#
#
# class ContourSet(UserList):
#     """Encapsulation for a set of ``Contour`` objects"""
#
#     def __getitem__(self, index):
#         return Contour(index, self.data[index])
#
#     def __repr__(self):
#         string = "{} with {} contours".format(self.__class__, len(self))
#         return string
#
#
# class Contour(object):
#     """Encapsulates the array representing a contour"""
#
#     def __init__(self, z, array):
#         self.z = z
#         self.__array = array
#
#     def __len__(self):
#         return len(self.__array)
#
#     def __iter__(self):
#         return iter(self.__array)
#
#     @staticmethod
#     def string_repr(self):
#         string = "<Contour at z={} with {} points>".format(self.z, len(self))
#         return string
#
#     def __repr__(self):
#         return self.string_repr(self)
#
#     def __str__(self):
#         return self.string_repr(self)


class AmiraDataStream(Block):
    """Base class for all Amira DataStreams"""

    __slots__ = ("stream_data", "_decoded_length", "_loader", "_decoder", "_itemsize", "data")

    def __init__(self, name, loader, *args, **kwargs):
        super(AmiraDataStream, self).__init__(name)
        self._decoded_length = 0
        self._loader = loader

    # def __getattribute__(self, name):
    #     if name in ("encoded_data", "decoded_data", "decoded_length"):
    #         return super(AmiraDataStream, self).__getattribute__(name)()
    #     try:
    #         return super(AmiraDataStream, self).__getattribute__(name)
    #     except AttributeError:
    #         if name not in ("stream_data", "data"):
    #             raise
    #         return super(AmiraDataStream, self).__getattribute__("_load_" + name)()

    # def __getattr__(self, item):

    # def __setattr__(self, name, value):
    #     if name in ('stream_data', 'data'):
    #         raise AttributeError("Attribute '{}' is read only call add_attr to update instead", format(name))
    #     super(AmiraDataStream, self).__setattr__(name, value)

    def _load_stream_data(self):
        """All the raw data from the file for the data stream"""
        self._loader.load_stream(self)
        return super(AmiraDataStream, self).__getattribute__("stream_data")

    @deprecated("will be removed in future versions use stream_data instead to access raw data")
    def encoded_data(self):
        """Encoded raw data in this stream"""
        return None

    @deprecated("will be removed in future versions use data instead to access decoded numpy arrays")
    def decoded_data(self):
        """Decoded data for this stream"""
        return None

    def _load_data(self):
        """Decoded numpy array for this stream"""
        if self.__class__ == "AmiraDataStream":
            raise NotImplementedError("_load_data must be implemented by subclass of '{}'".format(self.__class__))
        raise NotImplementedError("_load_data not implemented by class '{}'".format(self.__class__))

    @deprecated("may be removed in future versions use <stream>.data.size instead")
    def decoded_length(self):
        """The length of the decoded stream data in relevant units e.g. tuples, integers (not bytes)"""
        return self._decoded_length

    def __repr__(self):
        try:
            return "{} object of {:,} bytes".format(self.__class__,
                                                    len(super(AmiraDataStream, self).__getattribute__("stream_data")))
        except AttributeError:
            return "{} object of {:,} bytes".format(self.__class__, 0)


# class _AmiraDataStream(Block):
#     __slot__ = ('_data', '_loaded', '_stream_loader')
#
#     def __init__(self, name, stream_loader, *args, **kwargs):
#         super(_AmiraDataStream, self).__init__(name)
#         self._stream_loader = stream_loader
#         # do not load data by default
#         self._data = None
#         self._loaded = False
#
#     @property
#     def data(self):
#         if not self._loaded:
#             self._data = self._load()
#             self._loaded = True
#         return self._data
#
#     def _load(self):
#         return self._stream_loader.load_stream(self)


class AmiraMeshDataStream(AmiraDataStream):
    """Class encapsulating an AmiraMesh data stream"""
    __slots__ = tuple()

    def __init__(self, *args, **kwargs):
        super(AmiraMeshDataStream, self).__init__(*args, **kwargs)

    def add_attr(self, name, value, isparent=False):
        if name == 'dimension':
            value = np.int64(value)
            super(AmiraMeshDataStream, self).add_attr(name, value, isparent)
            _array = getattr(self, 'array', None)
            if _array is None:  # or isinstance(_array,_AnyBlockProxy):
                self._decoded_length = np.prod(value)
                return
            _array_dim = getattr(_array, 'dimension', None)
            if _array_dim is None:  # or isinstance(_array_dim,_AnyBlockProxy):
                self._decoded_length = np.prod(value)
                return
            self._decoded_length = np.prod(value) * np.prod(_array.dimension)
            return
        super(AmiraMeshDataStream, self).add_attr(name, value, isparent)
        if name == 'array':
            _array_dim = getattr(value, 'dimension', None)
            if _array_dim is None:  # or isinstance(_array_dim,_AnyBlockProxy):
                return
            _dimension = getattr(self, 'dimension', None)
            if _dimension is None:  # or isinstance(_dimension,_AnyBlockProxy):
                return
                # pylint: disable=E1101
            self._decoded_length = np.prod(_array_dim) * np.prod(_dimension)
            # pylint: enable=E1101
            return
        if name == 'type':
            self._decoder, self._itemsize = self._loader.select_decoder(self)
            return
        if name == 'data_format' and hasattr(self, 'type'):
            self._decoder, self._itemsize = self._loader.select_decoder(self)
            return

    @deprecated("use <AmiraMeshDataStream instance>.stream_data instead")
    def encoded_data(self):
        try:
            return self.stream_data
        except AttributeError as reason:
            raise AttributeError("'{}' type object does not have a 'encoded_data' property".format(self.__class__))

    @deprecated("use <AmiraMeshHxSurfaceDataStream instance>.data instead")
    def decoded_data(self):
        try:
            return self.data
        except AttributeError as reason:
            raise AttributeError("'{}' type object does not have a 'decoded_data' property".format(self.__class__))

    def _load_data(self):
        # pylint: disable=E1101
        _parentarray = getattr(self, 'array', None)
        if _parentarray is None:
            # not the terminal leave 
            raise AttributeError("'{}' type object does not have a 'data' property".format(self.__class__))
        if np.isscalar(self.dimension):
            if np.isscalar(_parentarray.dimension):
                _final_shape = [_parentarray.dimension, self.dimension]
            elif self.dimension < 2:
                _final_shape = _parentarray.dimension
            else:
                _final_shape = np.append(_parentarray.dimension, self.dimension)
        elif np.isscalar(_parentarray.dimension):
            if _parentarray.dimension < 2:
                _final_shape = self.dimension
            else:
                _final_shape = np.insert(self.dimension, 0, _parentarray.dimension)
        else:
            _final_shape = np.append(self.array_dimension, self.dimension)
        self.add_attr(
            "data",
            self._decoder(
                # pylint: disable=E1136
                self.stream_data if self._itemsize < 1 else self.stream_data[:(self._decoded_length * self._itemsize)],
                # pylint: enable=E1136
                # dtype=self._loader.type_map[self.type],
                count=self._decoded_length
            ).reshape(_final_shape)
        )
        return self.data
        # pylint: enable=E1101

    def to_images(self):
        if self.array.name not in ['Lattice']:
            raise ValueError("Unable to determine size of image stack")
            # X, Y, Z = self.array.dimension
        return ImageSet(np.swapaxes(self.data, 0, self.array.dimension.size - 1))
        # imgs = ImageSet(image_data[:])
        # return imgs

    def to_volume(self):
        """Return a 3D volume of the data"""
        if self.array.name not in ['Latice']:
            raise ValueError("Unable to determine size of 3D volume")
        # X, Y, Z = self.header.definitions.Lattice
        return np.swapaxes(self.data, 0, self.array.dimension.size - 1)


class AmiraMeshArrayList(ListBlock):
    __slots__ = ("_stashed_by", "_stashing_attr")

    def __init__(self, *args, **kwargs):
        super(AmiraMeshArrayList, self).__init__(*args, **kwargs)
        self._stashing_attr = None

    def _make_proxy_or_attributeerror(self, name, more_alife=False):
        return super(AmiraMeshArrayList, self)._make_proxy_or_attributeerror(
            name,
            self._stashing_attr is not None or more_alife
        )

    def __getattribute__(self, name):
        if super(AmiraMeshArrayList, self).__getattribute__("_stashing_attr") == name:
            super(AmiraMeshArrayList, self).__getattribute__("_stashed_by")._stash(self)
        return super(AmiraMeshArrayList, self).__getattribute__(name)

    def add_attr(self, name, value, isparent=False):
        if name == self._stashing_attr:
            if value != self._stashed_by:
                raise AttributeError("can't replace automatic attribute '{}'".format(self._stashing_attr))
            return
        if name == 'dimension':
            value = np.int64(value)
        super(AmiraMeshArrayList, self).add_attr(name, value, isparent)

    def _stash(self, by):
        try:
            if self._stashed_by != by:
                raise TypeError(
                    "object of type '{}' can only be stashed by stasching child stream".format(self.__class__.__name__))
        except AttributeError:
            raise TypeError(
                "object of type '{}' can only be stashed by stasching child stream".format(self.__class__.__name__))
        if self._list is None:
            return tuple()
        _rem = []
        for _attrname in (
                _key
                for _key, _val in _dict_iter_items(self.__dict__)
                if _val in self._list
        ):
            _rem.append(_attrname)
        for _attrname in _rem:
            delattr(self, _attrname)

        _stashed = self._list
        self._list = None
        _stashing_attr, self._stashing_attr = self._stashing_attr, None
        _stashed_by, self._stashed_by = self._stashed_by, None
        self.add_attr(_stashing_attr, _stashed_by)
        return _stashed

    def _will_stash(self, child):
        if not isinstance(child, AmiraMeshDataStream):
            raise TypeError(
                "object of type '{}' can only be stashed by 'AmiraMeshDataStream' type child streams".format(
                    self.__class__.__name__))
        try:
            if self._stashed_by is None:
                raise ValueError("instance of '{}' has already been stashed".format(self.__class__.__name__))
        except AttributeError:
            pass
        _childattr = None
        for _childattr in (
                _key
                for _key, _val in _dict_iter_items(self.__dict__)
                if _val == child
        ):
            break
        if _childattr is None:
            raise TypeError(
                "object of type '{}' can only be stashed by 'AmiraMeshDataStream' type child streams".format(
                    self.__class__.__name__))
        self._stashed_by = child
        self._stashing_attr = _childattr
        delattr(self, _childattr)
        self._stashed_by.add_attr('dimension', len(self))

    def __setitem__(self, index, value):
        try:
            super(AmiraMeshArrayList, self).__setitem__(index, value)
        except TypeError:
            raise TypeError("stashed '{}' object does not support item assignment".format(self.__class__.__name__))
        try:
            self._stashed_by.add_attr('dimension', len(self._list))
        except AttributeError:
            pass

    def __getitem__(self, index):
        try:
            super(AmiraMeshArrayList, self).__getitem__(index)
        except TypeError:
            raise TypeError("stashed '{}' object is not subscriptable".format(self.__class__.__name__))

    def __iter__(self):
        try:
            return iter(super(AmiraMeshArrayList, self).__iter__())
        except TypeError:
            raise TypeError("stashed '{}' object is not iterable".format(self.__class__.__name__))

    def __len__(self):
        try:
            return super(AmiraMeshArrayList, self).__len__()
        except TypeError:
            raise TypeError("stashed object of type '{}' has no len()".format(self.__class__.__name__))

    def __contains__(self, item):
        try:
            return super(AmiraMeshArrayList, self).__contains__(item)
        except TypeError:
            raise TypeError("argument of type '{}' is not iterable after stashing".format(self.__class__.__name__))


class AmiraMeshSheetDataStream(AmiraMeshDataStream):
    __slots__ = ('_stashed_items', '_stack_info')

    def __init__(self, *args, **kwargs):
        super(AmiraMeshSheetDataStream, self).__init__(*args, **kwargs)
        self._stashed_items = tuple()
        self._stack_info = None

    def add_attr(self, name, value, isparent=False):
        super(AmiraMeshSheetDataStream, self).add_attr(name, value, isparent)
        if name in ['array'] and isinstance(value, AmiraMeshArrayList):
            value._will_stash(self)
            self.add_attr('dimension', len(value))
            self._stashed_items = None

    def _stash(self, triggeredby):
        try:
            if self.array != triggeredby:
                raise RuntimeError("stashing can not be completed requester does not match array attribute")
        except AttributeError:
            raise RuntimeError("stashing can not be completed missing array attribute")
        self._stashed_items = self.array._stash(self)
        _dimensions = ()
        _names = ()
        _types = ()
        _defined = False
        for _index, _val in enumerate(self._stashed_items):
            if _val is None:
                if _defined:
                    if np.any(_dimensions[-1][0] != 0):
                        _dimensions = _dimensions + ([0, _index],)
                        _names = _names + ([_names[-1][0], _index],)
                        _types = _types + ([_types[-1][0], _index],)
                    else:
                        _dimensions[-1][1] = _index
                        _types[-1][1] = _index
                        _names[-1][1] = _index
                continue
            _name_nocount = StreamLoader._locate_counter.match(_val.name[::-1])
            if _name_nocount is None:
                _name_nocount = _val.name
            else:
                _name_nocount = _val.name[:-_name_nocount.end()]
            if _defined and _name_nocount == _names[-1][0] and np.all(
                    _val.dimension == _dimensions[-1][0]) and _val.type == _types[-1][0]:
                _names[-1][1] = _index
                _dimensions[-1][1] = _index
                _types[-1][1] = _index
                continue
            if not _defined and _index > 0:
                _names = _names + ([_name_nocount, _index - 1],)
                _dimensions = _dimensions + ([0, _index - 1],)
                _types = _types + ([_val.type, _index - 1],)
            _names = _names + ([_name_nocount, _index],)
            _dimensions = _dimensions + ([_val.dimension, _index],)
            _types = _types + ([_val.type, _index],)
            _defined = True
        if len(_names) == 1:
            self.name = _names[0][0]
        self._stack_info = dict(names=_names, dimensions=_dimensions, types=_types)
        self.add_attr(
            'dimension',
            (
                (
                    0
                    if len(_dimensions) < 1 else
                    (
                        _dimensions[0][1] + 1 if _dimensions[0][0] == 1 else np.array(
                            [_dimensions[0][1] + 1, _dimensions[0][0]])
                    )
                )
                if len(_dimensions) < 2 else
                tuple((
                    (_dim[1] + 1 if _idx < 1 else _dim[1] - _dimensions[_idx - 1][1], _dim[0])
                    for _idx, _dim in enumerate(_dimensions)
                ))
            )
        )
        self.add_attr('type', (None if len(_types) < 1 else _types[0][0]) if len(_types) < 2 else tuple(
            (_tp[0] for _tp in _types)))

    def _load_stream_data(self):
        if self._stashed_items is None or self._stack_info is None:
            raise TypeError(
                "'{}' type object must be successfully stashed before it's stream_data can be computed".format(
                    self.__class__.__name__))
        self.add_attr(
            "stream_data",
            tuple((
                _stream.stream_data if isinstance(_stream, AmiraDataStream) else None
                for _stream in self._stashed_items
            ))
        )
        return self.stream_data

    def _load_data(self):
        _ign = self.stream_data
        _names = self._stack_info.get("names", None)
        if _names is None:
            raise TypeError(
                "'{}' type object must be successfully stashed before it's stream_data can be computed".format(
                    self.__class__.__name__))
        self.array.add_attr("dimension", np.int64(self.array.dimension))
        if len(_names) < 2:
            if len(_names) < 1:
                _dim = np.hstack((self.array.dimension, self.dimension))
                self.add_attr("data", np.zeros(_dim))
            else:
                _dimensions = self._stack_info.get("dimensions", None)
                self.add_attr(
                    "data",
                    (
                        np.concatenate if (_dimensions[0][0].size == 1 and np.all(_dimensions[0][0] == 1)) or
                                          _dimensions[0][0][0] == 1 else np.stack
                    )(
                        [
                            _stream.data
                            for _stream in self._stashed_items
                        ],
                        axis=self.array.dimension.size
                    )
                )
                # if _dimensions[0][0].size == 1 and np.all(_dimensions[0][0] == 1):
                #    self._decoded_data = np.reshape(self._decoded_data,self._decoded_data.shape[:-1])
        else:
            _dimensions = self._stack_info.get("dimensions", None)
            _types = self._stack_info.get("types", None)
            _blocks = []
            _dtypes = []
            _parentdim = self.array.dimension
            _axis = _parentdim.size
            _stashed_items = self._stashed_items
            for _blockid in xrange(len(_names)):
                _name = _names[_blockid]
                _dim = _dimensions[_blockid]
                _type = _types[_blockid]
                if np.all(_dim < 1):
                    if _blockid < 1:
                        _type = self._stashed_items[_type[1] + 1].data.dtype.str
                        _count = _type[1] + 1
                    else:
                        _type = self._stashed_items[_types[_blockid - 1][1]].data.dtype.str
                        _count = _type[1] - _types[_blockid - 1][1]
                    _dim = np.hstack((_parentdim, _count, 0))
                    _blocks += [np.zeros(_dim, dtype=_type)]
                    _dtypes += [(_name[0], _type, _dim)]
                    continue
                if _blockid < 1:
                    _count = _type[1] + 1
                else:
                    _count = _type[1] - _types[_blockid - 1][1]
                _data = _stashed_items[_name[1]].data
                _type = _data.dtype.str
                if len(_data.shape) > 1 or _count > 1:
                    _data = np.repeat(np.expand_dims(_data, axis=_axis), _count, axis=_axis)
                _blocks += [_data]
                _dtypes += [(_name[0], _type, _data.shape)]
            self.add_attr("data", np.array(_blocks, dtype=_dtypes))
        self._stashed_items = None
        self._stack_info = None
        return self.data


class AmiraHxSurfaceDataStream(AmiraDataStream):
    """Base class for all HyperSurface data streams that inherits from ``AmiraDataStream``"""

    def __init__(self, *args, **kwargs):
        super(AmiraHxSurfaceDataStream, self).__init__(*args, **kwargs)

    def __setattr__(self, name, value):
        if name in ("count",):
            super(AmiraHxSurfaceDataStream, self).__getattribute__(name)(value)
            return
        super(AmiraHxSurfaceDataStream, self).__setattr__(name, value)

    @deprecated(
        "use <AmiraHxSurfaceDataStream instance>.dimension instead) or use <AmiraHxSurfaceDataStream instance>.add_attr('dimension',value) for setting instead")
    def count(self, *args):
        return self.dimension

    @deprecated("use <AmiraHxSurfaceDataStream instance>.stream_data instead")
    def encoded_data(self):
        try:
            return self.stream_data
        except AttributeError as reason:
            raise AttributeError("'{}' type object does not have a 'encoded_data' property".format(self.__class__))

    @deprecated("use <AmiraMeshHxSurfaceDataStream instance>.data instead")
    def decoded_data(self):
        try:
            return self.data
        except AttributeError as reason:
            raise AttributeError("'{}' type object does not have a 'decoded_data' property".format(self.__class__))

    def _load_data(self):
        # pylint: disable=E1101
        _parentarray = getattr(self, 'array', None)
        if _parentarray is None:
            raise AttributeError("'{}' type object does not have a 'data' property".format(self.__class__))
        if np.isscalar(self.dimension):
            if np.isscalar(_parentarray.dimension):
                _final_shape = [_parentarray.dimension, self.dimension]
            elif self.dimension < 2:
                _final_shape = _parentarray.dimension
            else:
                _final_shape = np.append(_parentarray.dimension, self.dimension)
        elif np.isscalar(_parentarray.dimension):
            if _parentarray.dimension < 2:
                _final_shape = self.dimension
            else:
                _final_shape = np.insert(self.dimension, 0, _parentarray.dimension)
        else:
            _final_shape = np.append(self.array_dimension, self.dimension)
        self.add_attr(
            "data",
            self._decoder(
                # pylint: disable=E1136
                self.stream_data if self._itemsize < 1 else self.stream_data[:(self._decoded_length * self._itemsize)],
                # pylint: enable=E1136
                # dtype=self._loader.type_map[self.type],
                count=self._decoded_length
            ).reshape(_final_shape)
        )
        return self.data
        # pylint: enable=E1101

    def add_attr(self, name, value, isparent=False):
        """ see:: ahds_common.Block for details """
        if name == 'dimension':
            # name is dimension try co calculate numver of elements in decoded data
            if type(value) in [str, int, float]:
                value = np.int64(value)
            super(AmiraHxSurfaceDataStream, self).add_attr(name, value, isparent)
            if hasattr(self, 'array'):
                # dimension is taken from data definition on specific array
                # multiply number of elements of both to obtain number of decoded 
                # data elements
                self._decoded_length = np.prod(value) * np.prod(self.array.dimension)
                return
            # decoded length is at least the produce of the elements of value
            self._decoded_length = value.prod()
            return
        super(AmiraHxSurfaceDataStream, self).add_attr(name, value, isparent)
        if name == 'array' and hasattr(self, 'dimension'):
            # Stream is linked to parent array decoded length is the product of the number
            # elements in array and in single array item defined by data description 
            # corresponding to this stream
            self._decoded_length = np.prod(value.dimension) * np.prod(self.dimension)
            return
        if name == 'type':
            # select decoding function and result type based upon type name provided by
            # value
            self._decoder, self._itemsize = self._loader.select_decoder(self)
            return
        if name == 'data_format' and hasattr(self, 'type'):
            # data stream is compressed binary stream the format is specified by data_format
            # attribute. select decoding method and datatype of decoded data as specified by
            # the type attribute
            self._decoder, self._itemsize = self._loader.select_decoder(self)
            return


_blob_size = 524288


class DataStreamNotFoundError(Exception):
    pass


class NotSupportedError(Exception):
    pass


class DataStreamError(Exception):
    pass


class StreamLoader(object):
    __slots__ = (
        "_header", "_next_datasection", "_field_data_map", "create_stream", "_section_pattern",
        "_next_key_toload", "create_array", "type_map", "decode", "_header_locked", "_next_stream",
        "_last_checked", "_group_end", "create_list_array"
    )

    # maps stream/block and <block>List names related to HyperSurface sections encoding multiple
    # input streams of same kind
    _array_group_map = {
        'Patch': "Patches",
        'BoundaryCurve': "BoundaryCurves",
        'Surface': "Surfaces",
        'PatchList': "Patches",
        'BoundaryCurveList': "BoundaryCurves",
        'SurfaceList': "Surfaces"
    }

    # maps Labes of multi stream sections found in HyperSurface files to pattern used to generate
    # counted blocknames
    _group_array_map = {
        'Patches': "Patch{}",
        'BoundaryCurves': "BoundaryCurve{}",
        'Surfaces': "Surface{}"
    }

    # regular expression used to locate the start of counter at the tail of
    # block name
    # NOTE: this is applied to reversed slice of block Name
    _locate_counter = re.compile(r'^\d+', re.I)

    def __init__(self, header, data_section_start, field_data_map):
        """ intializes StreamLoader
        :param AmiraHeader header: the header containing the meta information of the file
        :param int data_section_start: byte index at which the the Label of the first
            data steream is located. For AmiraMesh files this id sthe position of @1 and
            for HyperMesh files it will most likely point to label Vertices section
        :param dict field_data_map: dictionary relating AmiraMesh block indices to the
            corresponding AmiraDataStream block the data has to be assigned to. This
            ensures that intermediate data which occurs before the requested data can be
            properly assigned to its corresponding stream block.
        """
        self._header = header
        # initial the position of the next not yet loaded data section tho the byte number
        # of the first one.
        self._next_datasection = data_section_start
        self._field_data_map = field_data_map
        # the if-elses below scream 'polymorphism'
        if self._header.filetype == "AmiraMesh":
            # select instrumentation for AmiraMesh file
            self.create_stream = self._create_amira_mesh_stream
            self.create_array = self._create_amira_mesh_array
            self.create_list_array = self._create_amira_mesh_list_array
            self._section_pattern = _stream_delimiters[0]
            self._header_locked = True
            self._next_stream = self._get_next_block
            # index of next data block to be loaded
            self._last_checked = None
            # in amira mesh block indices are uniqe and independent from each other
            # no need to resolve ambiguities
            self._group_end = None
        elif self._header.filetype == "HyperSurface":
            # select instrumentation for HyperSurface file
            self.create_stream = self._create_hyper_surface_stream
            self.create_array = self._create_hyper_surface_array
            self.create_list_array = self._create_hyper_surface_list_array
            self._section_pattern = _stream_delimiters[1]
            self._header_locked = False
            self._next_stream = self._no_next_block
            # index of next data block to be loaded
            self._last_checked = None
            # Vertices and Patches labels are used on main level for defining
            # list of Coordinates for Veritces and Triangels of individual surface
            # Patches. At the same time they label the list of vertices on Boundary curves
            # and Patches resembling a specific surface. To disitinguish these two cases
            # the input data is searchded for closing } followed by whitespace only before
            # Vertices or Patches keyword. If found this would indicate end of Previous block
            # thus allow to distinguis it from List of Vertices as part of BoundaryCurves and
            # Surfaces sections
            self._group_end = _stream_delimiters[2]
        else:  # for all other filetypes
            raise NotSupportedError("Filetype '{}' not supported".format(self._header.filetype))
        self._next_key_toload = ['', 0, '', None, 0]

    def _get_next_block(self, matched=None):
        """ checks if provided index is found within the _field_data_map shared between
            AmiraHeader and StreamLoader instances
            :param int matched: block index to be checked if a metadata block is present
                or None if id of next not yet loaded block should be returned
                thereby it is assumed that blocks are stored with increasing indices """
        print('matched:', matched)
        print('self._field_data_map:', self._field_data_map)
        if matched is None:
            some_list = [_id for _id in _dict_iter_keys(self._field_data_map) if isinstance(_id, int)]
            if self._last_checked is None:
                matched = min(some_list)
            else:
                matched = self._last_checked
        else:
            matched = int(matched)
        self._last_checked = matched
        return self._field_data_map[matched]

    def _no_next_block(self, matched=None):
        """ dummy selector allways returning None to ensure block meta data is loaded and
            validated along with loading HyperSurface data streams"""
        return None

    def select_decoder(self, stream):
        """ selects the decoder function and result data type based upon the
            type and if present data_format attributes of the passed stream object
            :param AmiraDataStream stream: the stream for which the decoder
                function should be selected """

        if self._header.format is None:
            # header does not specify any of ASCII, BINARY or BINARY-LITTLE-ENDIAN
            _dtype = _type_map[False][stream.type]
            return ft.partial(np.frombuffer, dtype=_dtype), -1
        if self._header.format[0] in ['A', 'a']:
            # Format is ASCII type use numpy.fromstring function for decoding
            # return functools partial object with dtype parameter preset to the datatype
            # defined by the type attribute
            if self._header.format[1:] not in ["SCII", "scii"]:
                raise NotSupportedError("File encoding '{}' not supported".format(self._header.format))
            _dtype = _type_map[stream.type]
            return ft.partial(np.fromstring, dtype=_dtype, sep="\n \t"), 0
        if self._header.format[0] not in ['B', 'b'] or self._header.format[1:6] not in ["INARY", "inary"]:
            raise NotSupportedError("File encoding '{}' not supported".format(self._header.format))
        # check if data stream is compressed (HxByteRLE or HxZip)
        _data_format = getattr(stream, "data_format", None)
        # binary data encoded in bigendian (BINARY) or little endian (BINARY-LITTLER-ENDIAN)
        # use according (True, False) section of _type_map lookuptable above
        _endianess = self._header.format[6:] == "-LITTLE-ENDIAN"
        if _data_format is not None and _data_format.lower() == "hxbyterle":
            # 8 bit binary data compressed using rle encoding
            _dtype = _type_map[stream.type]
            return ft.partial(hxbyterle_decode, dtype=_dtype), (
                _dtype.itemsize * 2 if _dtype.kind in 'cC' else _dtype.itemsize)
        if _data_format in ["HxZip", "hxzip"]:
            # 8 bit binary data zip compressed
            _dtype = _type_map[stream.type]
            return ft.partial(hxzip_decode, dtype=_dtype), (
                _dtype.itemsize * 2 if _dtype.kind in 'cC' else _dtype.itemsize)
        # binary data use numpy frombuffer and return
        # functools.partial object with dtype parameter preset to data type
        # indicated by type attribute and the endianess of the data as specified by
        # file meta data
        _dtype = _type_map[_endianess][stream.type]
        return ft.partial(np.frombuffer, dtype=_dtype), (
            _dtype.itemsize * 2 if _dtype.kind in 'cC' else _dtype.itemsize)

    def _create_amira_mesh_stream(self, name, array=None):
        """ create AmiraMeshDataStream stream block
            :param str name: name of the new stream block
            :param Block array: parent block defining number of elements within array structure
        """
        return AmiraMeshDataStream(name, self)

    def _create_amira_mesh_array(self, name):
        """ create block storing array meta data
            :param str name: name of the data array
        """
        return Block(name)

    def _create_amira_mesh_list_array(self, name, kind='spreadsheet', child_name='Table'):
        _array = AmiraMeshArrayList(name)
        if kind.lower() == 'spreadsheet':
            _sheet = AmiraMeshSheetDataStream(child_name, self)
            # _sheet must be added first to ensure that check for stashability of _array
            # will find it as valid attribute otherwise a TypeError will be issued
            _array.add_attr(child_name, _sheet)
            _sheet.add_attr('array', _array, True)
        return _array

    def _create_hyper_surface_stream(self, name, array=None):
        """ create AmiraHxSurfaceDataStream stream block
            :param str name: name of the new stream block
            :param Block,AmiraMeshHxSurfaceDataStream array: parent block defining number of
                 elements within array structure
        """
        if not isinstance(array, Block) or not hasattr(array, "block"):
            raise ValueError("array must be a valide HyperSurface array block")
        _block = array.block
        if _block not in _hyper_surface_file:
            raise DataStreamError("invalid HyperSurface array block")
        _ingroup = _hyper_surface_file[_block]
        if isinstance(_ingroup, list):
            # either simple list of indices
            if _ingroup[1] is None:
                raise DataStreamError(
                    "cant create AmiraHxSurfaceDataStream within simple parameter '{}'".format(_block))
            if _ingroup[0] != name:
                raise DataStreamError(
                    "Expected '{}' stream name does not match requested '{}' name".format(_ingroup[0], name))
            return AmiraHxSurfaceDataStream(name, self)
        assert isinstance(_ingroup, dict)
        # stream is part of a list of streams
        if name not in _ingroup:
            raise DataStreamError("Expected any of '{}' for stream name but got '{}'".format(
                "', '".join([_key for _key in _dict_iter_keys(_ingroup) if isinstance(_key, str)]), name))
        if isinstance(_ingroup[name], list) and _ingroup[name][1] is None:
            raise DataStreamError(
                "cant create AmiraHxSurfaceDataStream for simple parameter '{}' of array '{}'".format(name, _block))
        return AmiraHxSurfaceDataStream(name, self)

    def _create_hyper_surface_array(self, name):
        # remove trailing counter from name
        _counterstart = self.__class__._locate_counter.match(name[::-1])
        if _counterstart is None:
            # no counter at end of name remap name to corresponding streamlabel
            _group_name = self.__class__._array_group_map.get(name, name)
            _subblock = None
        else:
            # split name into basename and counter pointing to block index
            _basename = name[:-_counterstart.end()]
            _group_name = StreamLoader._array_group_map.get(_basename, _basename)
            _subblock = name[-_counterstart.end():]
        if _group_name not in _hyper_surface_file:
            raise DataStreamError("Invalid HxSurfaceFile array '{}'".format(name))
        if isinstance(_hyper_surface_file[_group_name], list):
            # list of indices and vertices encoded within array
            if _hyper_surface_file[name][1] is None:
                raise DataStreamError("Can't crete AmiraHxSurfaceDataStream for simple parameter '{}'".format(name))
            _block_obj = AmiraHxSurfaceDataStream(name, self)
            _block_obj.add_attr("block", name)
            return _block_obj
        # label starts section of multible streams like Patches, BoundaryCurves etc Surfaces
        assert isinstance(_hyper_surface_file[_group_name], dict)
        _block_obj = AmiraHxSurfaceDataStream(name, self)
        _block_obj.add_attr("block", _group_name)
        if _subblock is not None:
            _block_obj.add_attr("subblock", int(_subblock))
        return _block_obj

    def _create_hyper_surface_list_array(self, name):
        raise DataStreamError("hyper surface does not support listlike array structures")

    def __getattribute__(self, attr):
        if attr in ("data_section_start",):
            return super(StreamLoader, self).__getattribute__("_next_datasection")
        return super(StreamLoader, self).__getattribute__(attr)

    # @property
    # def data_section_start(self):
    #    return self._next_datasection

    def load_stream(self, data_stream):
        """ loads the data described by the passed data_stream metadata block
            and attaches the correponding bytes to the block.

            Any data block which is contained in the bytes between the last location
            loaded and the data to be loaded will implicitly loaded and attached to
            their corresponding metadata blocks. In case of HyperSurface files these
            blocks are implicitly inserted into the AmiraHeader metadata structure
            representing the file.

            :param AmiraDataStream,str data_stream: the data stream the data is
                requested for or string denoting the name of the corresponding
                metadata Block
        """
        if self._next_datasection is None:
            # End of file reached all data loaded
            return
        if isinstance(data_stream, AmiraDataStream):

            # check if data_stream Block represents array block or one of it's substream
            # in the latter case recall using array metadata block if it is a
            # specific AmiraDataStream type block else continue with provided
            # AmiraDataStream instance
            _parent_stream = getattr(data_stream, 'array', None)
            if _parent_stream is not None and isinstance(_parent_stream, AmiraDataStream):
                self.load_stream(_parent_stream)
                return

            # extract block index or name from data_stream it is used in the below machinery
            # for identifying the section containing the requested data and stop after it has
            # been attached to the block
            _block_name = str(data_stream.block)

            # store the block name for generating error messages
            _stream_name = data_stream.name
        elif self._header_locked or not isinstance(data_stream, str):

            # modification of AmiraMesh header is not allowed or
            # HyperSuface file has been loaded and thus was locked for further
            # modification or object passed to data_stream is not string
            raise DataStreamNotFoundError(
                "File '{}': data_stream for block '{}' not found".format(self._header.filename, data_stream))
        elif data_stream not in _hyper_surface_file:

            # data_tream name ist not found in the _hyper_surface_file structure
            # try to strip the string representing a subblock counter from the passed string
            # and split eg 'Patch1' into 'Patch' and '1'. Use the basename to obtain the
            # correponding blockname froom the above _array_group_map structure
            _counterstart = self.__class__._locate_counter.match(data_stream[::-1])
            _block_name = self.__class__._array_group_map.get(
                data_stream[:-_counterstart.end()] if _counterstart is not None else data_stream,
                None
            )
            if _block_name is None:
                raise DataStreamNotFoundError(
                    "File '{}': data_stream for block '{}' not found".format(self._header.filename, data_stream))

            # store the block name for generating error messages
            _stream_name = data_stream
        else:

            # been attached to the block
            _stream_name = data_stream

            # check if the _stream_name has to be mapped to some strange remapping
            # in the above list
            _block_name = self.__class__._array_group_map.get(_stream_name, _stream_name)

        # turn off automatic loading of missing attributes of the header block to prevent
        # recursive calls caused by questing presence of header attributes in the
        # below code
        self._header.autoload(False)

        # open the file in binary mode
        with open(self._header.filename, "rb") as f:

            # skip forward to the next byte to be loaded
            # if supported by the input stream do this using seek
            # else fallback to reading and tossing the already read
            # bytes
            try:
                f.seek(self._next_datasection)
            except OSError:
                if f.seekable():
                    raise
                f.read(self._next_datasection)

            # read the first blob
            _stream_data = f.read(_blob_size)
            if len(_stream_data) < 1:
                raise DataStreamError("File '{}': unexpected EOF encountered".format(self._header.filename))

            # intialize machinery for identify individual blocks and the requested block
            # especially.

            # first byte within the _stream_data array to be rescanned after expanding
            # _stream_data by the next _blob read from the file
            _continue_scan_at = 0

            # data section for requested block not yet identified
            _block_not_found = True

            # if not none than currently the content of a specific
            # HyperSurface block is read for example of a single Patch
            _ingroup = None

            # total number of sub blocks for the currently loaded HyperSurface section
            _numentries = 0

            # index of the next to be read subblock of the curently loaded HyperSurface
            # section, first index is 1
            _entryid = 0

            # initialize reference to metadata block for which the data is expected to
            # be read next. For HyperSuface files this is allways None. For AmiraMesh
            # files this points to the next block following the last loaded
            _current_stream = self._next_stream()

            # byte numer within the _stream_data array where the binary data for the
            # currently loaded block starts.
            _block_start = 0

            # refrence to the array Block object the currently loaded stream is related
            # to
            _current_group = None

            # set of HyperSuface subsection an parameter names already loaded for the currenly
            # inspected subblock for example patch 2
            _subgroup_seen = set()

            # load the data
            while True:

                # scan the remaining bytes of the _stream_data array for the next
                # block index or sectoin name
                _match = self._section_pattern.search(_stream_data, _continue_scan_at)
                if _match is None:

                    # no additonal index or name found ensure that block indices and names
                    # which are split accross blob boundaries are found by the next
                    # scan while at the same time avoiding to rescan already successfully
                    # identified indices and names.
                    _next_scan = _continue_scan_at
                    _continue_scan_at = len(_stream_data) - _rescan_overlap
                    if _continue_scan_at < _next_scan:
                        _continue_scan_at = _next_scan

                    # read the next blob
                    _next_chunk = f.read(_blob_size)
                    if len(_next_chunk) < 1:

                        # end of file has been reached. disable StreamLoader for this file
                        self._header_locked = True
                        self._next_datasection = None
                        self._last_checked = None
                        if _current_stream is not None:
                            # attach bytes for last data_stream extending to the end of file
                            # to the corresponding metadata block
                            _current_stream.add_attr('stream_data', _stream_data[_block_start:])
                        if _block_not_found:
                            raise DataStreamNotFoundError(
                                "File '{}': data_block '{}' for data_stream '{}' not found".format(
                                    self._header.filename, _block_name, _stream_name))
                        # enable autoloading of missing attributes by header block
                        self._header.autoload(True)
                        return

                    # append blob to _stream_data array and rescan
                    _stream_data += _next_chunk
                    continue

                # extract the name or index of the stream
                _match_group = _decode_string(_match.group('stream'))
                if not _ingroup:

                    # process main group or AmiraMesh block
                    if _match_group == _block_name:
                        # reached requested block stop loading when follwoing block or end of
                        # file is reached
                        _block_not_found = False
                    if _current_stream is not None:
                        if _match_group == str(_current_stream.block):
                            # requested block is the one to be loaded and thus _block_not_found
                            # just has been set to true but data has not yet been read for block
                            # simply continue searching the next block following this or the end
                            # of file
                            _block_start = _match.end()
                            _continue_scan_at = _match.end('stream')
                            continue

                        # store the binary data in the _stream_data attribute of the current
                        # stream block
                        _current_stream.add_attr('stream_data', _stream_data[_block_start:_match.start()])

                        # try to get the metadata block for the next stream if available
                        _current_stream = self._next_stream(_match_group)
                        if _current_stream is not None:

                            # loading amira mesh stream block all entities of fiele are already named
                            # just need to load the corresponding stream data
                            if _block_not_found or _match_group == _block_name:
                                _block_start = _match.end()
                                _continue_scan_at = _match.end('stream')
                                continue

                            # data for requested block loaded stop reading and remember the
                            # byte location of the next block
                            self._next_datasection += _match.start()
                            self._header.autoload(True)
                            return

                    # loading HyperSurface stream need to extend header
                    _count = _decode_string(_match.group('count'))
                    _numentries = int(_count) if _count is not None else 1
                    _entryid = 1
                    _block_start = _match.end()
                    _firstentry_name = self._group_array_map.get(_match_group, _match_group).format(1)
                    _ingroup = _hyper_surface_file.get(_match_group, None)
                    if _ingroup is None:
                        raise DataStreamError(
                            "File '{}': Array group '{}' unknown!".format(self._header.filename, _match_group))
                    _current_group = getattr(self._header, _firstentry_name, None)
                    if _current_group is None:
                        if _count is None:
                            raise DataStreamError(
                                "File '{}': Array '{}'({}) counter missing!".format(self._header.filename,
                                                                                    _firstentry_name, _match_group))
                        if isinstance(_ingroup, list) and _ingroup[1] is None:
                            self._header.add_attr(_firstentry_name, int(_count))
                            if _block_not_found:
                                _continue_scan_at = _match.end('count')
                                _ingroup = None
                                continue
                            self._next_datasection += _match.start()
                            self._header.autoload(True)
                            return
                        if _numentries < 1:
                            if _block_not_found:
                                _continue_scan_at = _match.end('count')
                                _ingroup = None
                                continue
                            raise DataStreamError(
                                "File '{}': Array '{}'({}) empty!".format(self._header.filename, _firstentry_name,
                                                                          _match_group))
                        _current_group = self.create_array(_firstentry_name)
                        self._header.add_attr(_firstentry_name, _current_group)
                        self._header._check_siblings(_current_group, _firstentry_name, self._header,
                                                     _current_group.block)
                        _current_group.add_attr('block', _match_group)
                    elif isinstance(_ingroup, list) and _ingroup[1] is None:
                        self._header.add_attr(_firstentry_name,
                                              int(_count) if _count is not None else _match.group('name'))
                        if _block_not_found:
                            _continue_scan_at = _match.end('count' if _count is not None else 'name')
                            _ingroup = None
                            continue
                        self._next_datasection += _match.start()
                        self._header.autoload(True)
                        return
                    elif not isinstance(_current_group, Block):
                        DataStreamError(
                            "<Header>.{} AmiraHxSurfaceDataStream or Block type attribute value expected".format(
                                _match_group))
                    elif _numentries < 1:
                        if _block_not_found:
                            _continue_scan_at = _match.end('count')
                            _ingroup = None
                            continue
                        raise DataStreamError(
                            "File '{}': Array '{}'({}) empty!".format(self._header.filename, _firstentry_name,
                                                                      _match_group))
                    if _firstentry_name == _match_group:
                        _current_group.add_attr('dimension', np.int64(_count))
                        _numentries = 1
                    else:
                        _current_group.add_attr('dimension', 1)
                    if isinstance(_ingroup, list) and _ingroup[0] is not None:
                        _current_stream = getattr(_current_group, _ingroup[0], None)
                        if _current_stream is None:
                            _current_stream = self.create_stream(_ingroup[0], _current_group)
                            _current_group.add_attr(_ingroup[0], _current_stream)
                            self._header._check_siblings(_current_stream, _ingroup[0], _current_group,
                                                         _current_group.block)
                            _current_stream.add_attr('block ', _match_group)
                            _current_stream.add_attr('array', _current_group, True)
                        _current_stream.add_attr('type', _ingroup[2])
                        _current_stream.add_attr('dimension', _ingroup[1])
                    _continue_scan_at = _match.end('count')
                    continue
                if _current_stream is not None:
                    _current_stream.add_attr('stream_data', _stream_data[_block_start:_match.start()])
                    _current_stream = None
                if not isinstance(_ingroup, dict) or _match_group not in _ingroup or (
                        _match_group in _hyper_surface_file and self._group_end.match(
                    _stream_data[-len(_stream_data) - _match.start() - 1::-1]) is not None):
                    # true outer group hit
                    # simply rescan matched bit with _ingroup false and let above code handle
                    _continue_scan_at = _match.start()
                    if _entryid < _numentries:
                        raise DataStreamError(
                            "File: '{}': not enough subgroups ({}/{}) for hyper surface group '{}':".format(
                                self._header.filename, _entryid, _numentries, _ingroup))
                    if _current_group.block == _block_name:
                        self._next_datasection += _continue_scan_at
                        self._header.autoload(True)
                        return
                    _ingroup = None
                    _entryid = 0
                    _numentry = 0
                    _subgroup_seen.clear()
                    continue
                if _match_group in _subgroup_seen:
                    if len([True for _key, _val in _dict_iter_items(_ingroup) if
                            not isinstance(_key, str) or _key == _match_group or _key in _subgroup_seen or _val[
                                3]]) < len(_ingroup):
                        raise DataStreamError(
                            "File '{}': inconsistent '{}' entry {}".format(self._header.filename, _current_group.block,
                                                                           _entryid))

                    _entryid += 1
                    if _entryid > _numentries:
                        raise DataStreamError(
                            "File: '{}': additional subgroup ({}/{}) for hyper surface group '{}':".format(
                                self._header.filename, _entryid, _numentries, _ingroup))
                    _firstentry_name = self._group_array_map.get(_current_group.block).format(_entryid)
                    _common_block = _current_group.block
                    _subgroup_seen.clear()
                    _current_group = getattr(self._header, _firstentry_name, None)
                    if _current_group is None:
                        _current_group = self.create_array(_firstentry_name)
                        self._header.add_attr(_firstentry_name, _current_group)
                        self._header._check_siblings(_current_group, _firstentry_name, self._header,
                                                     _current_group.block)
                    _current_group.add_attr('block', _common_block)
                    _current_group.add_attr('dimension', 1)
                _subgroup_seen.add(_match_group)
                if _ingroup[_match_group][1] is None:
                    _count = _match.group('count')
                    if _count is None:
                        _name = _match.group('name')
                        _last_group = 'name'
                        _current_group.add_attr(_match_group, _decode_string(_name) if _name is not None else None)
                    else:
                        _decode_string(_count)
                        _current_group.add_attr(_match_group, int(_count))
                        _last_group = 'count'
                    _continue_scan_at = _match.end(_last_group)
                    continue
                _current_stream = getattr(_current_group, _match_group, None)
                _data_name = _ingroup[_match_group]
                if _match.group('count') is not None:
                    _dimension = np.int64(
                        [_match.group('count'), _data_name[1]] if _data_name[1] > 1 else _match.group('count')
                    )
                    _last_group = 'count'
                else:
                    _dimension = np.int64(_data_name[1])
                    _last_group = 'name' if _match.group('name') is not None else 'stream'
                if _current_stream is None:
                    _current_stream = self.create_stream(_match_group, _current_group)
                    _current_stream.add_attr('block ', _match_group)
                    _current_stream.add_attr('array', _current_group, True)
                    _current_group.add_attr(_match_group, _current_stream)
                    self._header._check_siblings(_current_stream, _match_group, _current_group, _current_group.block)
                _current_stream.add_attr('dimension', _dimension)
                _current_stream.add_attr('type', _data_name[2])
                _continue_scan_at = _match.end(_last_group)
                _block_start = _match.end()


class AmiraMeshStreamLoader(object):
    def __init__(self, header, *args, **kwargs):
        self._header = header
        # try:
        #     assert self._header.filetype == 'AmiraMesh'
        # except AssertionError:
        #     raise ValueError('invalid filetype for AmiraMeshStreamLoader: {}'.format(self._header.filetype))
        #
        # self._section_pattern = _stream_delimiters[0]
        # self._header_locked = True
        # # index of next data block to be loaded
        # self._last_checked = None
        # # in amira mesh block indices are uniqe and independent from each other
        # # no need to resolve ambiguities
        # self._group_end = None
        # self._next_key_toload = ['', 0, '', None, 0]

    # # todo: hive off methods from superclass (no point for superclass to have all implementations)
    # def create_stream(self, *args, **kwargs):
    #     return super(AmiraMeshStreamLoader, self)._create_amira_mesh_stream(*args, **kwargs)
    #
    # def create_array(self, *args, **kwargs):
    #     return super(AmiraMeshStreamLoader, self)._create_amira_mesh_array(*args, **kwargs)
    #
    # def create_list_array(self, *args, **kwargs):
    #     return super(AmiraMeshStreamLoader, self)._create_amira_mesh_list_array(*args, **kwargs)
    #
    # def _next_stream(self, *args, **kwargs):
    #     return super(AmiraMeshStreamLoader, self)._get_next_block(*args, **kwargs)
    #
    # def load_stream(self, data_stream):
    #     """ loads the data described by the passed data_stream metadata block
    #         and attaches the correponding bytes to the block.
    #
    #         Any data block which is contained in the bytes between the last location
    #         loaded and the data to be loaded will implicitly loaded and attached to
    #         their corresponding metadata blocks. In case of HyperSurface files these
    #         blocks are implicitly inserted into the AmiraHeader metadata structure
    #         representing the file.
    #
    #         :param AmiraDataStream,str data_stream: the data stream the data is
    #             requested for or string denoting the name of the corresponding
    #             metadata Block
    #     """
    #     if self._next_datasection is None:
    #         # End of file reached all data loaded
    #         return
    #     if isinstance(data_stream, _AmiraDataStream):
    #
    #         # check if data_stream Block represents array block or one of it's substream
    #         # in the latter case recall using array metadata block if it is a
    #         # specific AmiraDataStream type block else continue with provided
    #         # AmiraDataStream instance
    #         _parent_stream = getattr(data_stream, 'array', None)
    #         if _parent_stream is not None and isinstance(_parent_stream, AmiraDataStream):
    #             self.load_stream(_parent_stream)
    #             return
    #
    #         # extract block index or name from data_stream it is used in the below machinery
    #         # for identifying the section containing the requested data and stop after it has
    #         # been attached to the block
    #         _block_name = str(data_stream.data_stream)
    #
    #         # store the block name for generating error messages
    #         _stream_name = data_stream.name
    #     elif self._header_locked or not isinstance(data_stream, str):
    #
    #         # modification of AmiraMesh header is not allowed or
    #         # HyperSuface file has been loaded and thus was locked for further
    #         # modification or object passed to data_stream is not string
    #         raise DataStreamNotFoundError(
    #             "File '{}': data_stream for block '{}' not found".format(self._header.filename, data_stream))
    #     elif data_stream not in _hyper_surface_file:
    #
    #         # data_tream name ist not found in the _hyper_surface_file structure
    #         # try to strip the string representing a subblock counter from the passed string
    #         # and split eg 'Patch1' into 'Patch' and '1'. Use the basename to obtain the
    #         # correponding blockname froom the above _array_group_map structure
    #         _counterstart = self.__class__._locate_counter.match(data_stream[::-1])
    #         _block_name = self.__class__._array_group_map.get(
    #             data_stream[:-_counterstart.end()] if _counterstart is not None else data_stream,
    #             None
    #         )
    #         if _block_name is None:
    #             raise DataStreamNotFoundError(
    #                 "File '{}': data_stream for block '{}' not found".format(self._header.filename, data_stream))
    #
    #         # store the block name for generating error messages
    #         _stream_name = data_stream
    #     else:
    #
    #         # been attached to the block
    #         _stream_name = data_stream
    #
    #         # check if the _stream_name has to be mapped to some strange remapping
    #         # in the above list
    #         _block_name = self.__class__._array_group_map.get(_stream_name, _stream_name)
    #
    #     # turn off automatic loading of missing attributes of the header block to prevent
    #     # recursive calls caused by questing presence of header attributes in the
    #     # below code
    #     self._header.autoload(False)
    #
    #     # open the file in binary mode
    #     with open(self._header.filename, "rb") as f:
    #
    #         # skip forward to the next byte to be loaded
    #         # if supported by the input stream do this using seek
    #         # else fallback to reading and tossing the already read
    #         # bytes
    #         try:
    #             f.seek(self._next_datasection)
    #         except OSError:
    #             if f.seekable():
    #                 raise
    #             f.read(self._next_datasection)
    #
    #         # read the first blob
    #         _stream_data = f.read(_blob_size)
    #         if len(_stream_data) < 1:
    #             raise DataStreamError("File '{}': unexpected EOF encountered".format(self._header.filename))
    #
    #         # intialize machinery for identify individual blocks and the requested block
    #         # especially.
    #
    #         # first byte within the _stream_data array to be rescanned after expanding
    #         # _stream_data by the next _blob read from the file
    #         _continue_scan_at = 0
    #
    #         # data section for requested block not yet identified
    #         _block_not_found = True
    #
    #         # if not none than currently the content of a specific
    #         # HyperSurface block is read for example of a single Patch
    #         _ingroup = None
    #
    #         # total number of sub blocks for the currently loaded HyperSurface section
    #         _numentries = 0
    #
    #         # index of the next to be read subblock of the curently loaded HyperSurface
    #         # section, first index is 1
    #         _entryid = 0
    #
    #         # initialize reference to metadata block for which the data is expected to
    #         # be read next. For HyperSuface files this is allways None. For AmiraMesh
    #         # files this points to the next block following the last loaded
    #         print('f.tell()', f.tell())
    #         _current_stream = self._next_stream()
    #
    #         # byte numer within the _stream_data array where the binary data for the
    #         # currently loaded block starts.
    #         _block_start = 0
    #
    #         # refrence to the array Block object the currently loaded stream is related
    #         # to
    #         _current_group = None
    #
    #         # set of HyperSuface subsection an parameter names already loaded for the currenly
    #         # inspected subblock for example patch 2
    #         _subgroup_seen = set()
    #
    #         # load the data
    #         while True:
    #
    #             # scan the remaining bytes of the _stream_data array for the next
    #             # block index or sectoin name
    #             _match = self._section_pattern.search(_stream_data, _continue_scan_at)
    #             if _match is None:
    #
    #                 # no additonal index or name found ensure that block indices and names
    #                 # which are split accross blob boundaries are found by the next
    #                 # scan while at the same time avoiding to rescan already successfully
    #                 # identified indices and names.
    #                 _next_scan = _continue_scan_at
    #                 _continue_scan_at = len(_stream_data) - _rescan_overlap
    #                 if _continue_scan_at < _next_scan:
    #                     _continue_scan_at = _next_scan
    #
    #                 # read the next blob
    #                 _next_chunk = f.read(_blob_size)
    #                 if len(_next_chunk) < 1:
    #
    #                     # end of file has been reached. disable StreamLoader for this file
    #                     self._header_locked = True
    #                     self._next_datasection = None
    #                     self._last_checked = None
    #                     if _current_stream is not None:
    #                         # attach bytes for last data_stream extending to the end of file
    #                         # to the corresponding metadata block
    #                         _current_stream.add_attr('stream_data', _stream_data[_block_start:])
    #                     if _block_not_found:
    #                         raise DataStreamNotFoundError(
    #                             "File '{}': data_block '{}' for data_stream '{}' not found".format(
    #                                 self._header.filename, _block_name, _stream_name))
    #                     # enable autoloading of missing attributes by header block
    #                     self._header.autoload(True)
    #                     return
    #
    #                 # append blob to _stream_data array and rescan
    #                 _stream_data += _next_chunk
    #                 continue
    #
    #             # extract the name or index of the stream
    #             _match_group = _decode_string(_match.group('stream'))
    #             if not _ingroup:
    #
    #                 # process main group or AmiraMesh block
    #                 if _match_group == _block_name:
    #                     # reached requested block stop loading when follwoing block or end of
    #                     # file is reached
    #                     _block_not_found = False
    #                 if _current_stream is not None:
    #                     if _match_group == str(_current_stream.data_stream):
    #                         # requested block is the one to be loaded and thus _block_not_found
    #                         # just has been set to true but data has not yet been read for block
    #                         # simply continue searching the next block following this or the end
    #                         # of file
    #                         _block_start = _match.end()
    #                         _continue_scan_at = _match.end('stream')
    #                         continue
    #
    #                     # store the binary data in the _stream_data attribute of the current
    #                     # stream block
    #                     _current_stream.add_attr('stream_data', _stream_data[_block_start:_match.start()])
    #
    #                     # try to get the metadata block for the next stream if available
    #                     _current_stream = self._next_stream(_match_group)
    #                     if _current_stream is not None:
    #
    #                         # loading amira mesh stream block all entities of fiele are already named
    #                         # just need to load the corresponding stream data
    #                         if _block_not_found or _match_group == _block_name:
    #                             _block_start = _match.end()
    #                             _continue_scan_at = _match.end('stream')
    #                             continue
    #
    #                         # data for requested block loaded stop reading and remember the
    #                         # byte location of the next block
    #                         self._next_datasection += _match.start()
    #                         self._header.autoload(True)
    #                         return
    #
    #                 # loading HyperSurface stream need to extend header
    #                 _count = _decode_string(_match.group('count'))
    #                 _numentries = int(_count) if _count is not None else 1
    #                 _entryid = 1
    #                 _block_start = _match.end()
    #                 _firstentry_name = self._group_array_map.get(_match_group, _match_group).format(1)
    #                 _ingroup = _hyper_surface_file.get(_match_group, None)
    #                 if _ingroup is None:
    #                     raise DataStreamError(
    #                         "File '{}': Array group '{}' unknown!".format(self._header.filename, _match_group))
    #                 _current_group = getattr(self._header, _firstentry_name, None)
    #                 if _current_group is None:
    #                     if _count is None:
    #                         raise DataStreamError(
    #                             "File '{}': Array '{}'({}) counter missing!".format(self._header.filename,
    #                                                                                 _firstentry_name, _match_group))
    #                     if isinstance(_ingroup, list) and _ingroup[1] is None:
    #                         self._header.add_attr(_firstentry_name, int(_count))
    #                         if _block_not_found:
    #                             _continue_scan_at = _match.end('count')
    #                             _ingroup = None
    #                             continue
    #                         self._next_datasection += _match.start()
    #                         self._header.autoload(True)
    #                         return
    #                     if _numentries < 1:
    #                         if _block_not_found:
    #                             _continue_scan_at = _match.end('count')
    #                             _ingroup = None
    #                             continue
    #                         raise DataStreamError(
    #                             "File '{}': Array '{}'({}) empty!".format(self._header.filename, _firstentry_name,
    #                                                                       _match_group))
    #                     _current_group = self.create_array(_firstentry_name)
    #                     self._header.add_attr(_firstentry_name, _current_group)
    #                     self._header._check_siblings(_current_group, _firstentry_name, self._header,
    #                                                  _current_group.data_stream)
    #                     _current_group.add_attr('block', _match_group)
    #                 elif isinstance(_ingroup, list) and _ingroup[1] is None:
    #                     self._header.add_attr(_firstentry_name,
    #                                           int(_count) if _count is not None else _match.group('name'))
    #                     if _block_not_found:
    #                         _continue_scan_at = _match.end('count' if _count is not None else 'name')
    #                         _ingroup = None
    #                         continue
    #                     self._next_datasection += _match.start()
    #                     self._header.autoload(True)
    #                     return
    #                 elif not isinstance(_current_group, Block):
    #                     DataStreamError(
    #                         "<Header>.{} AmiraHxSurfaceDataStream or Block type attribute value expected".format(
    #                             _match_group))
    #                 elif _numentries < 1:
    #                     if _block_not_found:
    #                         _continue_scan_at = _match.end('count')
    #                         _ingroup = None
    #                         continue
    #                     raise DataStreamError(
    #                         "File '{}': Array '{}'({}) empty!".format(self._header.filename, _firstentry_name,
    #                                                                   _match_group))
    #                 if _firstentry_name == _match_group:
    #                     _current_group.add_attr('dimension', np.int64(_count))
    #                     _numentries = 1
    #                 else:
    #                     _current_group.add_attr('dimension', 1)
    #                 if isinstance(_ingroup, list) and _ingroup[0] is not None:
    #                     _current_stream = getattr(_current_group, _ingroup[0], None)
    #                     if _current_stream is None:
    #                         _current_stream = self.create_stream(_ingroup[0], _current_group)
    #                         _current_group.add_attr(_ingroup[0], _current_stream)
    #                         self._header._check_siblings(_current_stream, _ingroup[0], _current_group,
    #                                                      _current_group.data_stream)
    #                         _current_stream.add_attr('block ', _match_group)
    #                         _current_stream.add_attr('array', _current_group, True)
    #                     _current_stream.add_attr('type', _ingroup[2])
    #                     _current_stream.add_attr('dimension', _ingroup[1])
    #                 _continue_scan_at = _match.end('count')
    #                 continue
    #             if _current_stream is not None:
    #                 _current_stream.add_attr('stream_data', _stream_data[_block_start:_match.start()])
    #                 _current_stream = None
    #             if not isinstance(_ingroup, dict) or _match_group not in _ingroup or (
    #                     _match_group in _hyper_surface_file and self._group_end.match(
    #                 _stream_data[-len(_stream_data) - _match.start() - 1::-1]) is not None):
    #                 # true outer group hit
    #                 # simply rescan matched bit with _ingroup false and let above code handle
    #                 _continue_scan_at = _match.start()
    #                 if _entryid < _numentries:
    #                     raise DataStreamError(
    #                         "File: '{}': not enough subgroups ({}/{}) for hyper surface group '{}':".format(
    #                             self._header.filename, _entryid, _numentries, _ingroup))
    #                 if _current_group.data_stream == _block_name:
    #                     self._next_datasection += _continue_scan_at
    #                     self._header.autoload(True)
    #                     return
    #                 _ingroup = None
    #                 _entryid = 0
    #                 _numentry = 0
    #                 _subgroup_seen.clear()
    #                 continue
    #             if _match_group in _subgroup_seen:
    #                 if len([True for _key, _val in _dict_iter_items(_ingroup) if
    #                         not isinstance(_key, str) or _key == _match_group or _key in _subgroup_seen or _val[
    #                             3]]) < len(_ingroup):
    #                     raise DataStreamError(
    #                         "File '{}': inconsistent '{}' entry {}".format(self._header.filename, _current_group.data_stream,
    #                                                                        _entryid))
    #
    #                 _entryid += 1
    #                 if _entryid > _numentries:
    #                     raise DataStreamError(
    #                         "File: '{}': additional subgroup ({}/{}) for hyper surface group '{}':".format(
    #                             self._header.filename, _entryid, _numentries, _ingroup))
    #                 _firstentry_name = self._group_array_map.get(_current_group.data_stream).format(_entryid)
    #                 _common_block = _current_group.data_stream
    #                 _subgroup_seen.clear()
    #                 _current_group = getattr(self._header, _firstentry_name, None)
    #                 if _current_group is None:
    #                     _current_group = self.create_array(_firstentry_name)
    #                     self._header.add_attr(_firstentry_name, _current_group)
    #                     self._header._check_siblings(_current_group, _firstentry_name, self._header,
    #                                                  _current_group.data_stream)
    #                 _current_group.add_attr('block', _common_block)
    #                 _current_group.add_attr('dimension', 1)
    #             _subgroup_seen.add(_match_group)
    #             if _ingroup[_match_group][1] is None:
    #                 _count = _match.group('count')
    #                 if _count is None:
    #                     _name = _match.group('name')
    #                     _last_group = 'name'
    #                     _current_group.add_attr(_match_group, _decode_string(_name) if _name is not None else None)
    #                 else:
    #                     _decode_string(_count)
    #                     _current_group.add_attr(_match_group, int(_count))
    #                     _last_group = 'count'
    #                 _continue_scan_at = _match.end(_last_group)
    #                 continue
    #             _current_stream = getattr(_current_group, _match_group, None)
    #             _data_name = _ingroup[_match_group]
    #             if _match.group('count') is not None:
    #                 _dimension = np.int64(
    #                     [_match.group('count'), _data_name[1]] if _data_name[1] > 1 else _match.group('count')
    #                 )
    #                 _last_group = 'count'
    #             else:
    #                 _dimension = np.int64(_data_name[1])
    #                 _last_group = 'name' if _match.group('name') is not None else 'stream'
    #             if _current_stream is None:
    #                 _current_stream = self.create_stream(_match_group, _current_group)
    #                 _current_stream.add_attr('block ', _match_group)
    #                 _current_stream.add_attr('array', _current_group, True)
    #                 _current_group.add_attr(_match_group, _current_stream)
    #                 self._header._check_siblings(_current_stream, _match_group, _current_group, _current_group.data_stream)
    #             _current_stream.add_attr('dimension', _dimension)
    #             _current_stream.add_attr('type', _data_name[2])
    #             _continue_scan_at = _match.end(_last_group)
    #             _block_start = _match.end()


class AmiraHxSurfaceStreamLoader(StreamLoader):
    def __init__(self, *args, **kwargs):
        super(AmiraHxSurfaceStreamLoader, self).__init__(*args, **kwargs)
        try:
            assert self._header.filetype == 'HyperSurface'
        except AssertionError:
            raise ValueError('invalid filetype for AmiraMeshStreamLoader: {}'.format(self._header.filetype))

        self._section_pattern = _stream_delimiters[1]
        self._header_locked = False
        # index of next data block to be loaded
        self._last_checked = None
        # Vertices and Patches labels are used on main level for defining
        # list of Coordinates for Veritces and Triangels of individual surface
        # Patches. At the same time they label the list of vertices on Boundary curves
        # and Patches resembling a specific surface. To disitinguish these two cases
        # the input data is searchded for closing } followed by whitespace only before
        # Vertices or Patches keyword. If found this would indicate end of Previous block
        # thus allow to distinguis it from List of Vertices as part of BoundaryCurves and
        # Surfaces sections
        self._group_end = _stream_delimiters[2]
        self._next_key_toload = ['', 0, '', None, 0]

    def create_stream(self, *args, **kwargs):
        return super(AmiraHxSurfaceStreamLoader, self)._create_hyper_surface_stream(*args, **kwargs)

    def create_array(self, *args, **kwargs):
        return super(AmiraHxSurfaceStreamLoader, self)._create_hyper_surface_array(*args, **kwargs)

    def create_list_array(self, *args, **kwargs):
        return super(AmiraHxSurfaceStreamLoader, self)._create_hyper_surface_list_array(*args, **kwargs)

    def _next_stream(self, *args, **kwargs):
        return super(AmiraHxSurfaceStreamLoader, self)._no_next_block(*args, **kwargs)


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


class _AmiraDataStream(Block):
    pass


class _AmiraMeshDataStream(_AmiraDataStream):
    __slots__ = ('_stream_data', '_header')

    def __init__(self, name, header, *args, **kwargs):
        self._header = header  # contains metadata for extracting streams
        self._stream_data = None
        super(_AmiraMeshDataStream, self).__init__(name)

    @property
    def load_stream(self):
        return self._header.load_streams

    def read(self):
        with open(self._header.filename, 'rb') as f:
            # rewind the file pointer to the end of the header
            f.seek(len(self._header))
            start = int(self.data_index)  # this data streams index
            end = start + 1
            if self._header.data_stream_count == start:  # this is the last stream
                data = f.read()
                regex = ".*?\n@{}\n(?P<stream>.*)".format(start).encode('ASCII')
                match = re.match(regex, data, re.S)
                self._stream_data = match.group('stream')
            else:
                data = f.read()
                regex = ".*?\n@{}\n(?P<stream>.*)\n@{}".format(start, end).encode('ASCII')
                match = re.match(regex, data, re.S)
                self._stream_data = match.group('stream')

    # @property
    def data(self):
        # print(self._stream_data)
        # print(np.frombuffer(self._stream_data.strip(), dtype=np.dtype(np.string_)))
        # print(len(self._stream_data))
        return self._decode(self._stream_data)

    def _decode(self, data):
        if self._header.format == 'BINARY':
            # _type_map[endianness] uses endianness = True for endian == 'LITTLE'
            is_little_endian = self._header.endian == 'LITTLE'
            if isinstance(self.shape, list):
                return np.frombuffer(
                    data.strip(),
                    dtype=_type_map[is_little_endian][self.type]
                ).reshape(*self.shape, self.dimension)
            elif isinstance(self.shape, int):
                return np.frombuffer(
                    data.strip(),
                    dtype=_type_map[is_little_endian][self.type]
                ).reshape(self.shape, self.dimension)
        else:
            return np.fromstring(
                data,
                dtype=_type_map[self.type],
                sep="\n \t"
            ).reshape(self.shape, self.dimension)


class _AmiraHxSurfaceDataStream(ListBlock, _AmiraDataStream):
    __slots__ = ('_stream_data', '_header')

    def __init__(self, name, header, *args, **kwargs):
        self._header = header
        self._stream_data = None
        super(_AmiraHxSurfaceDataStream, self).__init__(name)

    # fixme: where is this method used?
    def load_stream(self):
        return self._header.load_streams

    def read(self):
        with open(self._header.filename, 'rb') as f:
            # rewind the file pointer to the end of the header
            f.seek(len(self._header))
            data = f.read()
            # get the vertex count and streams
            _vertices_regex = ".*?\n" \
                              "Vertices (?P<vertex_count>\d+)\n" \
                              "(?P<streams>.*)".encode('ASCII')
            vertices_regex = re.compile(_vertices_regex, re.S)
            match_vertices = vertices_regex.match(data)
            vertex_count = int(match_vertices.group('vertex_count'))
            # get the patches
            # fixme: general case for NBranchingPoints, NVerticesOnCurves, BoundaryCurves being non-zero
            stream_regex = "(?P<vertices>.*?)\n" \
                           "NBranchingPoints 0\n" \
                           "NVerticesOnCurves 0\n" \
                           "BoundaryCurves 0\n" \
                           "Patches (?P<patch_count>\d+)\n" \
                           "(?P<patches>.*)".encode('ASCII')
            match_streams = re.match(stream_regex, match_vertices.group('streams'), re.S)
            # instatiate the vertex block
            vertices_block = _AmiraHxSurfaceDataStream('Vertices', self._header)
            # set the data for this stream
            vertices_block._stream_data = match_streams.group('vertices')
            # length, type and dimension are needed for decoding
            vertices_block.add_attr('length', vertex_count)
            vertices_block.add_attr('type', 'float')
            vertices_block.add_attr('dimension', 3)
            vertices_block.add_attr('data', vertices_block.data())
            vertices_block.add_attr('NBranchingPoints', 0)
            vertices_block.add_attr('NVerticesOnCurves', 0)
            vertices_block.add_attr('BoundaryCurves', 0)
            # instantiate the patches block
            patches_block = _AmiraHxSurfaceDataStream('Patches', self._header)
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
            _patch_regex = "[{]\n" \
                           "InnerRegion (?P<patch_inner_region>.*?)\n" \
                           "OuterRegion (?P<patch_outer_region>.*?)\n" \
                           "BoundaryID (?P<patch_boundary_id>\d+)\n" \
                           "BranchingPoints (?P<patch_branching_points>\d+)\n" \
                           "\s+\n" \
                           "Triangles (?P<triangle_count>.*?)\n" \
                           "(?P<triangles>.*?)\n" \
                           "[}]\n[{]".encode('ASCII')
            patch_regex = re.compile(_patch_regex, re.S)
            # start from the beginning
            start_from = 0
            for p_id in range(patch_count):
                # NOTE A
                match_patch = patch_regex.match(match_streams.group('patches') + b'{', start_from)
                patch_block = _AmiraHxSurfaceDataStream('Patch', self._header)
                patch_block.add_attr('InnerRegion', match_patch.group('patch_inner_region').decode('utf-8'))
                patch_block.add_attr('OuterRegion', match_patch.group('patch_outer_region').decode('utf-8'))
                patch_block.add_attr('BoundaryID', int(match_patch.group('patch_boundary_id')))
                patch_block.add_attr('BranchingPoints', int(match_patch.group('patch_branching_points')))
                # let's now add the triangles from the patch
                triangles_block = _AmiraHxSurfaceDataStream('Triangles', self._header)
                # set the raw data stream
                triangles_block._stream_data = match_patch.group('triangles')
                # decoding needs to have the length, type, and dimension
                triangles_block.add_attr('length', int(match_patch.group('triangle_count')))
                triangles_block.add_attr('type', 'int')
                triangles_block.add_attr('dimension', 3)
                # print('debug:', int(match_patch.group('triangle_count')), len(match_patch.group('triangles')))
                # print('debug:', match_patch.group('triangles')[:20])
                # print('debug:', match_patch.group('triangles')[-20:])
                triangles_block.add_attr('data', triangles_block.data())
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

    # @property
    def data(self):
        return self._decode(self._stream_data)

    def _decode(self, data):
        is_little_endian = self._header.endian == 'LITTLE'
        return np.frombuffer(
            data,
            dtype=_type_map[is_little_endian][self.type]
        ).reshape(self.length, self.dimension)


def set_data_stream(name, header):
    if header.filetype == 'AmiraMesh':
        return _AmiraMeshDataStream(name, header)
    elif header.filetype == 'HyperSurface':
        return _AmiraHxSurfaceDataStream(name, header)
