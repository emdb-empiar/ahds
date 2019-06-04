# -*- coding: utf-8 -*-
# ahds

from .header import AmiraHeader, AmiraHeaderError
from .data_stream import DataStreams, DataStreamError, DataStreamNotFoundError, NotSupportedError
from .core import deprecated


class AmiraFile(AmiraHeader):
    """Convenience class to handle Amira files
    
    This class is a user-level alias classe for the :py:class:`ahds.header.AmiraHeader` and 
    binds it to the deprecated :py:class: `ahds.data_stream.DataStreams` class.
    the latter is marked deprecated and will be removed in future. As a consequence
    the AmiraHeader class will be merged into AmiraFile class and will be marked deprecated.
    """

    __slots__ = ("_data_streams",)

    def __init__(self, fn, *args, **kwargs):
        super(AmiraFile, self).__init__(fn, *args, **kwargs)
        self._data_streams = None  # create wrapper on call to read

    def __getattribute__(self, name):
        if name in ("header", "data_streams"):
            return super(AmiraFile, self).__getattribute__(name)()
        return super(AmiraFile, self).__getattribute__(name)

    @deprecated("AmiraFile is a subclass of AmiraHeader access header attributes directly from it")
    def header(self):
        return self

    @deprecated(
        "data streams are loaded into their metadata blocks when accessed for the fist time through the dedicated stream_data and data attributes of corresponding metadata blocks")
    def data_streams(self):
        return self._data_streams

    @deprecated(
        "data streams are read on demmand when dedicated stream_data and data attributes are accessed for the first time")
    def read(self):
        self._data_streams = DataStreams(self)
