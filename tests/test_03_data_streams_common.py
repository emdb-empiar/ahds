# -*- coding: utf-8 -*-
from __future__ import print_function

import sys
import os
import pytest
import unittest

import numpy

import ahds
from ahds import header, data_stream, IMMEDIATE,HEADERONLY,ONDEMMAND
from ahds.grammar import AHDSStreamError
from ahds.core import Block, ListBlock

from . import TEST_DATA_PATH,Py23FixTestCase

class TestHelpers(unittest.TestCase):
    def test_get_set_stream_policy(self):
        initial_policy = data_stream.get_stream_policy()
        self.assertTrue(initial_policy != IMMEDIATE)
        data_stream.set_stream_policy(IMMEDIATE)
        self.assertEqual(data_stream.get_stream_policy(),IMMEDIATE)
        with self.assertRaises(ValueError):
            data_stream.set_stream_policy('somthing')
        data_stream.set_stream_policy(initial_policy)
        self.assertEqual(data_stream.get_stream_policy(),initial_policy)

    def test_select_array_block(self):
        declaration_block = dict(
            array_blocktype = Block,
            array_name = "SimpleBlock",
            array_dimension = 3333
        )
        selected = data_stream.select_array_block(declaration_block)
        self.assertIsInstance(selected,declaration_block['array_blocktype'])
        self.assertEqual(selected.name,declaration_block['array_name'])
        self.assertEqual(selected.length,declaration_block['array_dimension'])
        declaration_listblock = dict(
            array_blocktype = ListBlock,
            array_name = "ListBlock",
            array_dimension = 777
        )
        selected = data_stream.select_array_block(declaration_listblock)
        self.assertIsInstance(selected,declaration_listblock['array_blocktype'])
        self.assertEqual(selected.name,declaration_listblock['array_name'])
        self.assertEqual(len(selected),declaration_listblock['array_dimension'])
        declaration_spreadsheet = dict(
            array_blocktype = data_stream.AmiraSpreadSheet,
            array_name = "SpreadSheet",
            array_dimension = 13
        )
        selected = data_stream.select_array_block(declaration_spreadsheet)
        self.assertIsInstance(selected,declaration_spreadsheet['array_blocktype'])
        self.assertEqual(selected.name,declaration_spreadsheet['array_name'])
        self.assertEqual(len(selected),declaration_spreadsheet['array_dimension'])

    def test_AmiraDataStream(self):
        class FakeHeader():
            load_streams = HEADERONLY

        fake_header = FakeHeader()
        base_stream = data_stream.AmiraDataStream("WithoutData",fake_header)
        self.assertIsInstance(base_stream,data_stream.AmiraDataStream)
        self.assertEqual(base_stream.name,"WithoutData")
        self.assertEqual(len(base_stream),0)
        with self.assertRaises(AttributeError):
            self.assertIsNone(base_stream._offset)

        FakeHeader.load_streams = IMMEDIATE
        base_stream = data_stream.AmiraDataStream("ImmediateData",fake_header)
        self.assertIsInstance(base_stream,data_stream.AmiraDataStream)
        self.assertEqual(base_stream.name,"ImmediateData")
        self.assertIsNone(base_stream._offset)
        some_data = b'ka392a'
        with self.assertRaises(AssertionError):
            base_stream = data_stream.AmiraDataStream("DataWithoutOffset",fake_header,None,some_data)
        with self.assertRaises(AssertionError):
            base_stream = data_stream.AmiraDataStream("OffsetWithoutData",fake_header,1024)
        base_stream = data_stream.AmiraDataStream("PreloadedData",fake_header,1024,some_data)
        self.assertIsInstance(base_stream,data_stream.AmiraDataStream)
        self.assertEqual(base_stream.name,"PreloadedData")
        self.assertEqual(base_stream._stream_data,some_data)
        self.assertEqual(base_stream._offset,1024)
        
            
    def test_set_datastream(self):
        class FakeHeader():
            load_streams = HEADERONLY
            file_format = 'AmiraMesh'

        fake_header = FakeHeader()
        base_stream = data_stream.set_data_stream("AmiraMeshStream",fake_header)
        self.assertIsInstance(base_stream,data_stream.AmiraMeshDataStream)
        self.assertEqual(base_stream.name,"AmiraMeshStream")
        self.assertEqual(len(base_stream),0)
        with self.assertRaises(AttributeError):
            self.assertIsNone(base_stream._offset)

        FakeHeader.load_streams = IMMEDIATE
        FakeHeader.file_format = 'SurfaceMesh'
        with self.assertRaises(AHDSStreamError):
            base_stream = data_stream.set_data_stream("SufaceMehsStream",fake_header)
        FakeHeader.file_format = 'HyperSurface'
        base_stream = data_stream.set_data_stream("HyperSufaceStream",fake_header)
        self.assertIsInstance(base_stream,data_stream.AmiraHxSurfaceDataStream)
        self.assertEqual(base_stream.name,"HyperSufaceStream")
        self.assertIsNone(base_stream._offset)

