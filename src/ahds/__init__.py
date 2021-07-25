# -*- coding: utf-8 -*-
# ahds

# to use relative syntax make sure you have the package installed in a virtualenv in develop mode e.g. use
# pip install -e /path/to/folder/with/setup.py
# or
# python setup.py develop

import sys
import copy

from .core import Block,ListBlock 
from .header import AmiraHeader
from .data_stream import set_stream_policy,get_stream_policy,ONDEMMAND,IMMEDIATE,HEADERONLY,set_data_stream,load_streams
from .grammar import get_header


if sys.version_info[0] > 2: # pragma: cover_py3
    from shutil import get_terminal_size
    _get_terminal_size = get_terminal_size
else: # pragma: cover_py2
    from backports.shutil_get_terminal_size import get_terminal_size
    _get_terminal_size = get_terminal_size


def check_format(fn):
    with open(fn,'rb') as fhnd:
        return get_header(fhnd,check_format=True)

WIDTH = _get_terminal_size().columns

class AmiraFile(AmiraHeader):
    """Main entry point for working with Amira files"""
    __slots__ = (READONLY("header"),READONLY("data_streams"),READONLY('meta'))

    def __init__(self, fn, load_streams=True, **kwargs):
        """Initialise a new AmiraFile object given the Amira file.

        Passes additional args/kwargs to AmiraHeader class for initialisation of the reading process

        .. code:: python

            from ahds import AmiraFile
            af = AmiraFile('file.am')
            print(af)

        :param str fn: Amira file name
        :param bool load_streams: whether (default) or not to load data streams
        """
        super(AmiraFile, self).__init__(fn,load_streams=load_streams,**kwargs)
        self._header = self
        # meta block
        self._meta = Block('meta')
        self._meta.add_attr('file', self.filename)
        self._meta.add_attr('header_length', len(self))
        self._meta.add_attr('streams_loaded', self._stream_offset < 0 )
        self._data_streams = Block('data_streams')
        if self.file_format == "AmiraMesh":
            self._meta.add_attr('data_streams', self.data_stream_count)
            for stream in ( strm for strm in self._data_streams_block_list if strm is not None ):
                self._data_streams.add_attr(stream,isparent=None)
        else:
            data_block = set_data_stream("Data",self)
            self._data_streams.add_attr(data_block)
            vertices = getattr(self,'Vertices',None)
            if vertices is not None:
                vertices = copy.copy(vertices.Coordinates)
                data_block.add_attr('Vertices',vertices)
            for stream_attribute_name in ('BoundaryCurves','Patches','Surfaces'):
                stream_attribute = getattr(self,stream_attribute_name,None)
                if stream_attribute is None:
                    continue
                vertices.add_attr(stream_attribute_name,stream_attribute,None)
            self._meta.add_attr('data_streams',1)
            self._data_stream_count = 1
                

    def read(self):
        if self._stream_offset >= 0:
            load_streams(self)

    def __repr__(self):
        return "AmiraFile('{}', read={})".format(self.filename, self._stream_offset < 0)

    def __str__(self, prefix="", index=None):
        width = 140
        string = ""
        string += '*' * width + '\n'
        string += "AMIRA (R) HEADER AND DATA STREAMS\n"
        string += "-" * width + "\n"
        string += super(AmiraFile, self).__str__(prefix=prefix, index=index)
        string += "*" * width
        return string


__all__ = [
    'AmiraFile',
    'AmiraHeader',
    'set_stream_policy' ,
    'get_stream_policy',
    'check_format',
    'IMMEDIATE',
    'ONDEMMAND',
    'HEADERONLY'
]
