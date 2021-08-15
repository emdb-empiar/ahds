# -*- coding: utf-8 -*-
from __future__ import print_function
import warnings

import os
import os.path
import sys
import types
from unittest import TestCase

AHDS_PACKAGE_PATH = os.path.dirname(os.path.abspath(__file__))
TEST_DATA_PATH = os.path.join(AHDS_PACKAGE_PATH, r'data')

class Py23FixAssertWarnsContext():
    """context manager mocking assertWarns context missing in python 2 unittest"""
    def __init__(self,expected,test_case):
        self.expected = expected
        self.test_case = test_case

    def __enter__(self):
        for v in list(sys.modules.values()):
            if getattr(v,'__warningregistry__',None):
                v.__warningregistry__ = {}
        self.warnings_manager = warnings.catch_warnings(record = True)
        self.warnings = self.warnings_manager.__enter__()
        warnings.simplefilter("always",self.expected)

    def __exit__(self,exc_type,exc_value,tb):
        self.warnings_manager.__exit__(exc_type,exc_value,tb)
        if exc_type is not None:
            return
        for w in self.warnings:
            if not isinstance(w,self.expected):
                continue
            self.warning = w
            self.filename = w.filename
            self.lineno = w.lineno
        try:
            exc_name = self.expected.__name__
        except AttributeError:
            exc_name = str(self.expected)
        self.test_case.failureException("'{} not triggered",exc_name)

    def handle(self,name,args,kwargs):
        try:
            if not issubclass(self.expected,Warning):
                raise TypeError('{:s} arg 1 must be a warning type or tuple of warning types'.format(name))
            if not args:
                self.msg = kwargs.pop('msg',None)
                if kwargs:
                    raise TypeError('{!r} is an invalid keyword argument for this function'.format(next(iter(kwargs))))
                return self
            callable_obj = args[0]
            args = args[1:]
            try:
                self.obj_name = callable_obj.__name__
            except AttributeError:  
                self.obj_name = str(callable_obj)
            with self:
                callable_obj(*args,**kwargs)
        finally:
            pass #self = None

class Py23FixTestCase(TestCase):
    """Mixin to fix method changes in TestCase class"""

    def __init__(self, *args, **kwargs):
        if sys.version_info[0] > 2:
            pass
        else:
            # new names for assert methods
            self.assertCountEqual = self.assertItemsEqual
            if not callable(getattr(self,'assertWarns',None)):
                self.assertWarns = self._assertWarns
        super(Py23FixTestCase, self).__init__(*args, **kwargs)

    def _assertWarns(self,expected_warning,*args,**kwargs):
        _context = Py23FixAssertWarnsContext(expected_warning,self)
        return _context.handle('assertWarns',args,kwargs)
