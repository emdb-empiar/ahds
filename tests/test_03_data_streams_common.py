# -*- coding: utf-8 -*-
from __future__ import print_function

import sys
import os
import pytest
import unittest

import numpy
import copy

# import ahds
from ahds import header, data_stream, IMMEDIATE,HEADERONLY,ONDEMMAND
from ahds.grammar import get_header,AHDSStreamError,set_content_type_filter,clear_content_type_filter,DispatchFilter
from ahds.core import Block, ListBlock
#from ahds.data_stream import AmiraSpreadSheet,AmiraMeshDataStream,get_stream_policy,HEADERONLY,IMMEDIATE

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


class DispatchFilterFailedException(Exception):
    """ just to mark that parsing would be invalidated """

@pytest.mark.Skip
class TestAmiraSpreadSheetCollector(Py23FixTestCase):
    # TODO to be moved to dedicated ContentType tests when ContenType's are supported
    #      bejond parser interface and basic structure building during loading of data
    filename = 'BinaryHxSpreadSheet62x200.am'
    strange_file = 'EqualLabeledColumnsSpreadSheet.am'

    @staticmethod
    def dofail():
        raise DispatchFilterFailedException()

    @classmethod
    def setUpClass(cls):
        cls.filepath = os.path.join(TEST_DATA_PATH,cls.filename)
        # disable possibly installed filter for 'HxSpreadSheet'
        filter_backup = clear_content_type_filter('HxSpreadSheet')
        with open(cls.filepath,'rb') as fhnd:
            cls.file_format,cls.parsed_header,cls.header_size,_ = get_header(fhnd)
        cls.header_data = {
            block_key:block_data
            for block in cls.parsed_header
            for block_key,block_data in block.items()
        }
        cls.filepath = os.path.join(TEST_DATA_PATH,cls.strange_file)
        with open(cls.filepath,'rb') as fhnd:
            cls.strange_file_format,cls.strange_parsed_header,cls.strange_header_size,_ = get_header(fhnd)
        cls.strange_header_data = {
            block_key:block_data
            for block in cls.strange_parsed_header
            for block_key,block_data in block.items()
        }
        #  possibly installed filter for 'HxSpreadSheet'
        if issubclass(filter_backup,DispatchFilter):
            set_content_type_filter('HxSpreadSheet',filter_backup)
        else:
            assert False

    def setUp(self):
        self.array_declarations = copy.deepcopy(self.header_data['array_declarations'])
        self.data_definitions = copy.deepcopy(self.header_data['data_definitions'])
        self.strange_array_declarations = copy.deepcopy(self.strange_header_data['array_declarations'])
        self.strange_data_definitions = copy.deepcopy(self.strange_header_data['data_definitions'])

    def test_filter(self):
        dispatchprocessor = data_stream.AmiraSpreadSheetCollector(TestAmiraSpreadSheetCollector.dofail)
        self.assertIsNone(dispatchprocessor.filter({}))

        self.assertEqual(dispatchprocessor.filter(self.array_declarations[1]),('Sheet1',data_stream.AmiraSpreadSheet,1,{},{}))
        test_dec = {key:value for key,value in self.array_declarations[2].items()}
        test_dec['array_name'] = test_dec['array_name'][2:]
        self.assertEqual(dispatchprocessor.filter(test_dec),(test_dec['array_name'][:-4],data_stream.AmiraSpreadSheet,2,{},{}))
        test_dec['array_name'] = self.array_declarations[2]['array_name'][1:]
        self.assertEqual(dispatchprocessor.filter(test_dec),(test_dec['array_name'][1:-4],data_stream.AmiraSpreadSheet,2,{},{}))
        self.assertEqual(len(dispatchprocessor.not_counted_names),0)
        self.assertFalse(dispatchprocessor.post_processing)
        dispatchprocessor = data_stream.AmiraSpreadSheetCollector(TestAmiraSpreadSheetCollector.dofail)
        index = -1
        self.assertFalse(dispatchprocessor.post_processing)
        for index,decl in enumerate(self.strange_array_declarations):
            decl_name = decl['array_name']
            self.assertEqual(dispatchprocessor.filter(decl),(decl_name,data_stream.AmiraSpreadSheet,index,{},{}))
            self.assertEqual(decl['array_name'],'{}{:04d}'.format(decl_name,index))
        self.assertEqual(dispatchprocessor.not_counted_names.get(self.strange_array_declarations[0]['array_name'][:-4],-1),index+1)
        self.assertTrue(dispatchprocessor.post_processing)

    def test_post_process(self):
        dispatchprocessor = data_stream.AmiraSpreadSheetCollector(TestAmiraSpreadSheetCollector.dofail)
        self.assertEqual(dispatchprocessor.post_process({}),{})
        for decl in self.array_declarations:
            dispatchprocessor.filter(decl)
        self.assertFalse(dispatchprocessor.post_processing)
        self.assertEqual(dispatchprocessor.post_process(self.data_definitions[2]),self.data_definitions[2])
        dispatchprocessor = data_stream.AmiraSpreadSheetCollector(TestAmiraSpreadSheetCollector.dofail)
        for decl in self.strange_array_declarations:
            dispatchprocessor.filter(decl)
        self.assertTrue(dispatchprocessor.post_processing)
        for index,definition in enumerate(self.strange_data_definitions):
            definition_name = definition['data_name']
            self.assertEqual(dispatchprocessor.post_process(definition).get('array_reference',''),self.strange_array_declarations[index]['array_name'])
            self.assertEqual(definition['data_name'],'{}{:04d}'.format(definition_name,index))
