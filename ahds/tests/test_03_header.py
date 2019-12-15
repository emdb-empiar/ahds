# -*- coding: utf-8 -*-
from __future__ import print_function

import os
import sys

from ahds import header
from ahds.tests import Py23FixTestCase, TEST_DATA_PATH
from ahds.data_stream import HEADERONLY,IMMEDIATE
from ahds.grammar import get_header,AHDSStreamError
from ahds.core import Block

class TestHeaderBase(Py23FixTestCase):
    filename = 'test12.am'

    @classmethod
    def setUpClass(cls,noheader = False):
        cls.filepath = os.path.join(TEST_DATA_PATH,cls.filename)
        if noheader:
            return
        cls.header = header.AmiraHeader(cls.filepath)

class TestHeaderBlock(TestHeaderBase):

    def test_amiraheader(self):
        self.assertIsInstance(self.header, header.AmiraHeader)

    def test_add_attr(self):
        self.header.Parameters.add_attr('x', 10)
        self.assertTrue(hasattr(self.header.Parameters, 'x'))
        self.assertEqual(self.header.Parameters.x, 10)

    def test_materials_block(self):
        """Test the structure of the Materials block"""
        self.assertTrue(hasattr(self.header, 'Parameters'))
        self.assertTrue(hasattr(self.header.Parameters, 'Materials'))
        self.assertCountEqual(self.header.Parameters.Materials.ids, [3])

    def test_big_endian_format(self):
        self.assertEqual(self.header.format,"BINARY")
        self.assertEqual(self.header.endian,"BIG")

class TestLoadHeaderOnly(TestHeaderBase):
    @classmethod
    def setUpClass(cls,noheader=False):
        super(TestLoadHeaderOnly,cls).setUpClass(noheader=True)
        cls.header = header.AmiraHeader(cls.filepath,load_streams=False)

    def test_only_amiraheader(self):
        self.assertIsInstance(self.header, header.AmiraHeader)
        self.assertEqual(self.header._load_streams,HEADERONLY)



class TestLoadImmediate(TestHeaderBase):
    @classmethod
    def setUpClass(cls,noheader=False):
        super(TestLoadImmediate,cls).setUpClass(noheader=True)
        cls.header = header.AmiraHeader(cls.filepath,load_streams=True)

    def test_immediate_load_streams(self):
        self.assertIsInstance(self.header, header.AmiraHeader)
        self.assertEqual(self.header._load_streams,IMMEDIATE)

class TestLoadErrorsWarnings(TestHeaderBase):

    def test_invalid_stream_setting(self):
        with self.assertRaises(ValueError):
            header.AmiraHeader(self.filepath,load_streams='12')

    def test_deprecated_from_file(self):
        with self.assertWarns(DeprecationWarning):
            ah = header.AmiraHeader.from_file(self.filepath)
        
class TestProperties(TestHeaderBase):
    def test_literal_data(self):
        _,data,_ = get_header(self.filepath)
        self.assertEqual(self.header.literal_data,data)
        self.assertEqual(len(self.header),len(data))

    def test_designation(self):
        with self.assertWarns(DeprecationWarning):
            self.assertTrue(self.header.designation is self.header)

    def test_definitions(self):
        with self.assertWarns(DeprecationWarning):
            self.assertTrue(self.header.definitions is self.header)

    def test_data_pointers(self):
        with self.assertWarns(DeprecationWarning):
            self.assertTrue(isinstance(self.header.data_pointers,Block) and self.header.data_pointers.name=="data_pointers")
        
    
class test_no_parameters(TestHeaderBase):
    filename = "test12_no_parameters.am"

    def test_created_parameters(self):
        self.assertTrue(getattr(self.header,'Parameters',None) is not None)

class TestLoadSpreadSheet(TestHeaderBase):
    filename = "BinaryHxSpreadSheet62x200.am"
    @classmethod
    def setUpClass(cls,noheader=False):
        super(TestLoadSpreadSheet,cls).setUpClass(noheader=True)

    def test_spread_sheet_regrouping(self):
        self.header = header.AmiraHeader(self.filepath)
        self.assertEqual(self.header.Parameters.ContentType,"HxSpreadSheet")

class TestScalar(TestHeaderBase):
    filename = "testscalar.am"
    def test_little_endian_format(self):
        self.assertEqual(self.header.format,"BINARY")
        self.assertEqual(self.header.endian,"LITTLE")

    def test_stream_by_index(self):
        # no need to get valid stream
        # implicilty tested by load_streams=IMMEDIATE
        with self.assertRaises(ValueError):
            self.header.get_stream_by_index(0)
        with self.assertRaises(ValueError):
            self.header.get_stream_by_index(2)

    def test_get_stream_offset(self):
        # no need to get valid offset
        # implicilty tested by load_streams=IMMEDIATE
        with self.assertRaises(ValueError):
            self.header.get_stream_offset(None)
        no_stream = Block('NoStream')
        with self.assertRaises(ValueError):
            self.header.get_stream_offset(no_stream)
        no_stream.add_attr('stream_index',0)
        with self.assertRaises(ValueError):
            self.header.get_stream_offset(no_stream)
        no_stream.add_attr('stream_index',2)
        with self.assertRaises(ValueError):
            self.header.get_stream_offset(no_stream)
        no_stream.add_attr('stream_index',1)
        with self.assertRaises(ValueError):
            self.header.get_stream_offset(no_stream)

    def test_set_stream_offset(self):
        # no need to set valid offset
        # implicilty tested by load_streams=IMMEDIATE
        any_offset = 12902
        with self.assertRaises(ValueError):
            self.header.set_stream_offset(None,any_offset)
        no_stream = Block('NoStream')
        with self.assertRaises(ValueError):
            self.header.set_stream_offset(no_stream,any_offset)
        no_stream.add_attr('stream_index',0)
        with self.assertRaises(ValueError):
            self.header.set_stream_offset(no_stream,any_offset)
        no_stream.add_attr('stream_index',2)
        with self.assertRaises(ValueError):
            self.header.set_stream_offset(no_stream,any_offset)
        no_stream.add_attr('stream_index',1)
        with self.assertRaises(ValueError):
            self.header.set_stream_offset(no_stream,any_offset)

    def test_print_repr(self):
        self.assertEqual(repr(self.header),"AmiraHeader('{}')".format(self.filepath))
            

class TestLittleASCIIFormat(TestHeaderBase):
    filename = "BinaryCustomLandmarks.elm"
    def test_ascii_format(self):
        self.assertEqual(self.header.format,"ASCII")
        self.assertEqual(self.header.endian,None)


class TestDestinctionListOfMaterialReferences(TestHeaderBase):
    filename = "test_simple_labels.am"
    def test_distinction_list_of_MaterialReferences(self):
        self.assertTrue(isinstance(getattr(self.header.Parameters,'Materials'),Block))
        self.assertEqual(self.header.Parameters.Materials.Exterior.Id,0)
        self.assertEqual(self.header.Parameters.Materials.Something.Id,4)
        self.assertEqual(self.header.Parameters.Materials.Interior.Id,7)

class TestDestinctionListOfMaterialNoParameters(TestHeaderBase):
    filename = "test_simple_materials_noparams.am"
    def test_distinction_list_of_Material_no_parameters(self):
        self.assertTrue(isinstance(getattr(self.header.Parameters,'Materials'),Block))
        self.assertEqual(self.header.Parameters.Materials.Exterior.Id,0)
        self.assertEqual(self.header.Parameters.Materials.Something.Id,4)
        self.assertEqual(self.header.Parameters.Materials.Interior.Id,7)

class TestDestinctionListOfMaterialMixed(TestHeaderBase):
    filename = "test_simple_mixed_mat_spec.am"
    def test_distinction_list_of_Material_mixed(self):
        self.assertTrue(isinstance(getattr(self.header.Parameters,'Materials'),Block))
        self.assertEqual(self.header.Parameters.Materials.Exterior.Id,0)
        self.assertEqual(self.header.Parameters.Materials.Something.Id,4)
        self.assertEqual(self.header.Parameters.Materials.Interior.Id,7)
        self.assertEqual(self.header.Parameters.Materials.Outerspace.Id,9)

class TestSingleMat(TestHeaderBase):
    filename = "testscalar_single_mat.am"
    def test_signle_mat(self):
        self.assertTrue(isinstance(getattr(self.header.Parameters,'Materials'),Block))


class TestSimpleSurf(TestHeaderBase):
    filename = "simple.surf"
    @classmethod
    def setUpClass(cls,noheader=False):
        super(TestSimpleSurf,cls).setUpClass(noheader=noheader)

    def test_simple_surf(self):
        self.assertEqual(self.header.Vertices.length,11)
        self.assertEqual(len(self.header.Patches),4)
        self.assertTrue(self.header.Patches[0] is None)


class TestFullSurf(TestHeaderBase):
    filename = "full.surf"
    @classmethod
    def setUpClass(cls,noheader=False):
        super(TestFullSurf,cls).setUpClass(noheader=noheader)

    def test_full_surf(self):
        self.assertEqual(self.header.Vertices.length,6)
        self.assertEqual(len(self.header.Patches),6)
        self.assertTrue(self.header.Patches[0] is None)
        self.assertEqual(len(self.header.BoundaryCurves),4)
        self.assertTrue(self.header.BoundaryCurves[0] is None)
        self.assertEqual(len(self.header.Surfaces),4)
        self.assertTrue(self.header.Surfaces[0] is None)
        self.assertEqual(self.header.NBranchingPoints,2)
        self.assertEqual(self.header.NVerticesOnCurves,2)


class TestFieldOnTetra(TestHeaderBase):
    filename = "FieldOnTetraMesh.am"

    def test_field_on_tetra_mesh(self):
        self.assertEqual(self.header.Tetrahedra.Data.field_name,'f')


class Test2FieldOnTetra(TestHeaderBase):
    filename = "2FieldOnTetraMesh.am"

    def test_2field_on_tetra_mesh(self):
        self.assertEqual(self.header.Tetrahedra.Data.field_name,'f1')
        self.assertEqual(self.header.Tetrahedra.Data2.field_name,'f2')

class TestBadFieldOnTetra(TestHeaderBase):
    filename = "BadFieldOnTetraMesh.am"
    @classmethod
    def setUpClass(cls,noheader=False):
        try:
            super(TestBadFieldOnTetra,cls).setUpClass()
        except AHDSStreamError as delayed:
            cls.raise_delayed = delayed
        else:
            cls.raise_delayed = None

    def test_bad_field_on_tetra_mesh(self):
        self.assertIsInstance(self.raise_delayed,AHDSStreamError)


class TestBad2FieldOnTetra(TestHeaderBase):
    filename = "Bad2FieldOnTetraMesh.am"
    @classmethod
    def setUpClass(cls,noheader=False):
        try:
            super(TestBad2FieldOnTetra,cls).setUpClass()
        except AHDSStreamError as delayed:
            cls.raise_delayed = delayed
        else:
            cls.raise_delayed = None

    def test_bad2_field_on_tetra_mesh(self):
        self.assertIsInstance(self.raise_delayed,AHDSStreamError)

class TestDoubleDescriptor(TestHeaderBase):
    filename = "testdoubldatadescriptor.am"
    @classmethod
    def setUpClass(cls,noheader=False):
        try:
            super(TestDoubleDescriptor,cls).setUpClass()
        except AHDSStreamError as delayed:
            cls.raise_delayed = delayed
        else:
            cls.raise_delayed = None

    def test_double_descriptor(self):
        self.assertIsInstance(self.raise_delayed,AHDSStreamError)

