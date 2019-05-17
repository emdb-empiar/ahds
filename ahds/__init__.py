# -*- coding: utf-8 -*-
# ahds

from . import header
from . import data_stream

class AmiraFile(object):
    """Convenience class to handle Amira (R) files
    
    This class aggregates user-level classes from the :py:mod:`ahds.header` and :py:mod:`ahds.data_stream` modules
    into a single class with a simple interface :py:meth:`AmiraFile.header` for the header and :py:attr:`AmiraFile.data_streams` 
    data streams attribute.
    """
    def __init__(self, fn, *args, **kwargs):
        self._fn = fn
        self._header = header.AmiraHeader.from_file(self._fn, *args, **kwargs)
        self._data_streams = None # only populate on call to read() method
        
    @property
    def header(self):
        return self._header
    
    @property
    def data_streams(self):
        return self._data_streams
    
    def read(self, *args, **kwargs):
        self._data_streams = data_stream.DataStreams(self._fn, *args, **kwargs)
        