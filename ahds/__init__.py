# -*- coding: utf-8 -*-
# ahds

# to use relative syntax make sure you have the package installed in a virtualenv in develop mode e.g. use
# pip install -e /path/to/folder/with/setup.py
# or
# python setup.py develop

import sys
import copy

if __package__:
    from .core import Block,READONLY
    from .header import AmiraHeader
    from .data_stream import set_stream_policy,get_stream_policy,ONDEMMAND,IMMEDIATE,HEADERONLY,set_data_stream,load_streams
else:
    from core import Block,READONLY
    from header import AmiraHeader
    from data_stream import set_stream_policy,get_stream_policy,ONDEMMAND,IMMEDIATE,HEADERONLY,set_data_stream,load_streams


if sys.version_info[0] > 2:
    from shutil import get_terminal_size
    _get_terminal_size = get_terminal_size
else:
    from backports.shutil_get_terminal_size import get_terminal_size
    _get_terminal_size = get_terminal_size


WIDTH = _get_terminal_size().columns

class AmiraFile(AmiraHeader):
    """Main entry point for working with Amira files"""
    __slots__ = ('_read',READONLY("header"),READONLY("data_streams"),READONLY('meta'))#'_fn', '_load_streams', '_meta' '_header', '_data_streams')

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
        self._read = self.load_streams == IMMEDIATE
        self.header = self
        # meta block
        self.meta = Block('meta')
        self.meta.add_attr('file', self.filename)
        self.meta.add_attr('header_length', len(self))
        self.meta.add_attr('streams_loaded', self._read)
        self.data_streams = Block('data_streams')
        if self.filetype == "AmiraMesh":
            self.meta.add_attr('data_streams', self.data_stream_count)
            for stream in self._data_streams_block_list:
                if stream is None:
                    continue
                self.data_streams.add_attr(stream,isparent=None)
        else:
            data_block = set_data_stream("Data",self)
            self.data_streams.add_attr(data_block)
            vertices = getattr(self,'Vertices',None)
            if vertices is not None:
                vertices = copy.copy(vertices.Coordinates)
                data_block.add_attr('Vertices',vertices)
            for stream_attribute_name in ('BoundaryCurves','Patches','Surfaces'):
                stream_attribute = getattr(self,stream_attribute_name,None)
                if stream_attribute is None:
                    continue
                vertices.add_attr(stream_attribute_name,stream_attribute,None)
            self.meta.add_attr('data_streams',1)
            self.data_stream_count = 1
                

    def read(self):
        if not self._read:
            load_streams(self)
            self._read = True

    def __repr__(self):
        return "AmiraFile('{}', read={})".format(self.filename, self._read)

    def __str__(self, prefix="", index=None):
        width = 140
        string = ""
        string += '*' * width + '\n'
        string += "AMIRA (R) HEADER AND DATA STREAMS\n"
        string += "-" * width + "\n"
        string += super(AmiraFile, self).__str__(prefix=prefix, index=index)
        string += "*" * width
        return string


__all__ = ['AmiraFile', 'AmiraHeader', 'set_stream_policy' , 'get_stream_policy', 'IMMEDIATE', 'ONDEMMAND', 'HEADERONLY']
