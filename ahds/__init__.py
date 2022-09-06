# -*- coding: utf-8 -*-
"""
ahds
====

This module provides a simple entry-point for using the underlying functionality
through the `AmiraFile` class which automatically handles both `AmiraMesh` and
`HxSurface` files. An `AmiraFile` is also a `Block` subclass with special attributes
`meta` - for metadata not explicitly provided in the file (such as `header_length`),
`header` - for the parse header and `data_streams` with the actual data stream data.

The only required argument is the name of the file to be read. By default, data streams
are loaded but can be turned off (for quick reading) by
setting `load_stream=False`. Additional `kwargs` are passed to the `AmiraHeader` class
call.

There is a `read` method which (if data streams have not yet been read) will read
the data streams.

An `AmiraFile` object may be printed to view the hierarchy of entities above or
passed to `repr` to view the instatiation call that represents it.

"""

import sys

from .core import Block
from .data_stream import set_data_stream
from .header import AmiraHeader

if sys.version_info[0] > 2:
    from shutil import get_terminal_size

    _get_terminal_size = get_terminal_size
else:
    from backports.shutil_get_terminal_size import get_terminal_size

    _get_terminal_size = get_terminal_size

WIDTH = _get_terminal_size().columns


class AmiraFile(Block):
    """Main entry point for working with Amira files"""
    __slots__ = ('_fn', '_load_streams', '_meta' '_header', '_data_streams')

    def __init__(self, fn, load_streams=True, *args, **kwargs):
        """Initialise a new AmiraFile object given the Amira file.

        Passes additional args/kwargs to AmiraHeader class for initialisation of the reading process

        .. code:: python

            from ahds import AmiraFile
            af = AmiraFile('file.am')
            print(af)

        :param str fn: Amira file name
        :param bool load_streams: whether (default) or not to load data streams
        """
        super(AmiraFile, self).__init__(fn)
        self._fn = fn
        self._load_streams = load_streams
        self._streams_loaded = False
        # the header contains a lot of information relied on for reading streams
        self._header = AmiraHeader(fn, load_streams=load_streams, *args, **kwargs)
        # meta block
        super(AmiraFile, self).add_attr('meta', Block('meta'))
        self.meta.add_attr('file', self._fn)
        self.meta.add_attr('header_length', len(self._header))
        self.meta.add_attr('data_streams', self._header.data_stream_count)
        self.meta.add_attr('streams_loaded', self._load_streams)
        # header block
        super(AmiraFile, self).add_attr('header', self._header)
        # data streams block
        super(AmiraFile, self).add_attr(Block('data_streams'))
        if self._load_streams:
            self.read()
            self._streams_loaded = True

    def read(self):
        """Read the data streams if they are not read yet"""
        if not self._streams_loaded:
            if self._header.filetype == "AmiraMesh":
                for ds in self._header._data_streams_block_list:
                    ds.read()
                    ds.add_attr('data', ds.get_data())
                    self.data_streams.add_attr(ds)
            elif self._header.filetype == "HyperSurface":
                block = set_data_stream('Data', self._header)
                block.read()
                self.data_streams.add_attr(block)
            self._load_streams = self._header.load_streams = True
            self._streams_loaded = True

    def __repr__(self):
        return "AmiraFile('{}', read={})".format(self._fn, self._read)

    def __str__(self, prefix="", index=None,alt_name=None):
        width = 140
        string = ""
        string += '*' * width + '\n'
        string += "AMIRA (R) HEADER AND DATA STREAMS\n"
        string += "-" * width + "\n"
        string += super(AmiraFile, self).__str__(prefix=prefix, index=index,alt_name=alt_name)
        string += "*" * width
        return string


__all__ = ['AmiraFile', 'AmiraHeader']
