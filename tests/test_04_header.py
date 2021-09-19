# -*- coding: utf-8 -*-
from __future__ import print_function

import os
import sys
import numpy as np
import pytest

from . import Py23FixTestCase, TEST_DATA_PATH

from ahds import header
from ahds.data_stream import AmiraSpreadSheet,AmiraMeshDataStream,get_stream_policy,HEADERONLY,IMMEDIATE
from ahds.grammar import get_header,AHDSStreamError
from ahds.core import Block,ListBlock,_decode_string


class TestHeaderBase(Py23FixTestCase):
    filename = 'test12.am'

    @classmethod
    def setUpClass(cls,noheader = False,rawheader=False):
        cls.filepath = os.path.join(TEST_DATA_PATH,cls.filename)
        if noheader:
            cls.header = header.AmiraHeader.__new__(header.AmiraHeader)
            Block.__init__(cls.header,'header')
            cls.header._filename = cls.filepath
            with open(cls.filepath,'rb') as fhnd:
                cls.file_format,cls.parsed_header,cls.header_size,cls.raw_header = get_header(fhnd,verbose=rawheader)
            if rawheader:
                cls.raw_header = _decode_string(cls.header)
            cls.header._header_length = cls.header_size
            cls.header._file_format = cls.file_format
            cls.header._data_stream_count = None
            cls.header._stream_offset = cls.header._header_length
            cls.header._load_streams = get_stream_policy()
            cls.header._parsed_data = cls.parsed_header
            cls.header_blocks = {
                block_key:block_data
                for block in cls.parsed_header
                #for block_key,block_data in _dict_iter_items(block)
                for block_key,block_data in block.items()
            }
            return
        cls.header = header.AmiraHeader(cls.filepath,verbose=rawheader)
        cls.file_format = cls.header.file_format
        cls.parsed_header = cls.header._parsed_data
        cls.header_size = cls.header._header_length
        cls.raw_header = _decode_string(cls.header._literal_data) if rawheader else None

class TestInitHeaderBlock(TestHeaderBase):
    @classmethod
    def setUpClass(cls,noheader=False):
        super(TestInitHeaderBlock,cls).setUpClass(noheader=True)

    def test_load_designation(self):
        designation = self.header_blocks['designation']
        self.header._load_designation(self.header_blocks['designation'])
        self.assertEqual(self.header.dimension,designation['dimension'])
        self.assertEqual(self.header.version,designation['version'])
        self.assertEqual(('format',self.header.format,'endian',self.header.endian),header.AmiraHeader.__decode_format__[designation['format']])
        backup_format = designation['format']
        designation['format'] = "HelloWord"
        with self.assertRaises(ValueError):
            self.header._load_designation(self.header_blocks['designation'])
        designation['format'] = backup_format

    def test_load_parameters(self):
        designation = self.header_blocks['designation']
        self.header._load_designation(self.header_blocks['designation'])
        parameters = self.header_blocks['parameters']
        loaded_parameters = self.header._load_parameters(self.header_blocks['parameters'])
        self.assertIsInstance(getattr(loaded_parameters,'Materials',None),Block)
        self.assertIsInstance(getattr(loaded_parameters.Materials,'Exterior',None),Block)
        self.assertIn(getattr(loaded_parameters.Materials.Exterior,'Id',-1),range(1,3))
        self.assertIs(loaded_parameters.Materials[loaded_parameters.Materials.Exterior.Id],loaded_parameters.Materials.Exterior)
        self.assertIsInstance(getattr(loaded_parameters.Materials,'Inside',None),Block)
        self.assertEqual(getattr(loaded_parameters.Materials.Inside,'Color',[]),[0.64,0,0.8])
        self.assertIs(loaded_parameters.Materials[loaded_parameters.Materials.Inside.Id],loaded_parameters.Materials.Inside)
        self.assertIsInstance(getattr(loaded_parameters.Materials,'Spikes',None),Block)
        self.assertEqual(getattr(loaded_parameters.Materials.Spikes,'Id',-1),3)
        self.assertEqual(getattr(loaded_parameters.Materials.Spikes,'Color',[]),[0.16,0.481757,0.8])
        self.assertIs(loaded_parameters.Materials[loaded_parameters.Materials.Spikes.Id],loaded_parameters.Materials.Spikes)
        self.assertIsInstance(getattr(loaded_parameters,'Seeds',None),Block)
        self.assertIsInstance(getattr(loaded_parameters.Seeds,'Slice0142',None),Block)
        self.assertEqual(getattr(loaded_parameters.Seeds.Slice0142,'S0172x0109',[]),[2,0,2000,12])
        self.assertEqual(getattr(loaded_parameters.Seeds.Slice0142,'S0172x0119',[]),[2,0,2000,12])
        self.assertEqual(getattr(loaded_parameters,'Content',''),"319x286x280 byte, uniform coordinates")
        self.assertEqual(getattr(loaded_parameters,'BoundingBox',[]),[118, 436, 281, 566, 0, 279])
        self.assertEqual(getattr(loaded_parameters,'CoordType',''),"uniform")

    def test_trigger_odd_parameter(self):
        designation = self.header_blocks['designation']
        self.header._load_designation(self.header_blocks['designation'])
        parameters = self.header_blocks['parameters']
        last_param_backup = parameters[-1]
        parameters[-1] = {'parameter_name':last_param_backup['parameter_name'],'par_value':last_param_backup['parameter_value']}
        loaded_parameters = self.header._load_parameters(self.header_blocks['parameters'])
        self.assertEqual(getattr(loaded_parameters,'CoordType',None),None)
        parameters[-1] = last_param_backup

    def test_append_material_fillers(self):
        designation = self.header_blocks['designation']
        self.header._load_designation(self.header_blocks['designation'])
        parameters = self.header_blocks['parameters']
        for material_list in parameters:
            if material_list['parameter_name'] == 'Materials':
                materials = material_list['parameter_value']
                break
        else:
            materials = []
            parameters.append({'parameter_name':'Materials','parameter_value':materials})
        materials.extend([
            {'parameter_name':'Shade','parameter_value':[]},
            {'parameter_name':'Screen','parameter_value':[]}
        ])
        loaded_parameters = self.header._load_parameters(self.header_blocks['parameters'])
        self.assertIsInstance(getattr(loaded_parameters.Materials,'Shade',None),Block)
        self.assertIn(getattr(loaded_parameters.Materials.Shade,'Id',-1),range(len(materials)-1,len(materials)+1))
        self.assertIs(loaded_parameters.Materials[loaded_parameters.Materials.Shade.Id],loaded_parameters.Materials.Shade)
        self.assertIsInstance(getattr(loaded_parameters.Materials,'Screen',None),Block)
        self.assertIn(getattr(loaded_parameters.Materials.Screen,'Id',-1),range(len(materials)-1,len(materials)+1))
        self.assertIs(loaded_parameters.Materials[loaded_parameters.Materials.Screen.Id],loaded_parameters.Materials.Screen)
        materials[-2:] = []

    def test_load_declarations(self):
        designation = self.header_blocks['designation']
        self.header._load_designation(self.header_blocks['designation'])
        declarations = self.header_blocks['array_declarations']
        self.header._load_declarations(self.header_blocks['array_declarations'])
        self.assertIsInstance(getattr(self.header,'Lattice',None),Block)
        self.assertTrue(np.all(getattr(self.header.Lattice,'length',[])==[319, 286, 280]))
        
    def test_load_definitions(self):
        designation = self.header_blocks['designation']
        self.header._load_designation(self.header_blocks['designation'])
        declarations = self.header_blocks['array_declarations']
        self.header._load_declarations(self.header_blocks['array_declarations'])
        definitions = self.header_blocks['data_definitions']
        stream_block_list = self.header._load_definitions(self.header_blocks['data_definitions'])
        self.assertIsInstance(stream_block_list[0],Block)
        self.assertEqual(stream_block_list[0].name,'None')
        self.assertIsInstance(stream_block_list[1],AmiraMeshDataStream)
        self.assertIsInstance(stream_block_list[1].parent,Block)
        self.assertEqual(stream_block_list[1].parent.name,definitions[0]['array_reference'])
        self.assertEqual(stream_block_list[1].name,definitions[0]['data_name'])
        self.assertEqual(stream_block_list[1].type,definitions[0]['data_type'])
        self.assertEqual(stream_block_list[1].data_index,definitions[0]['data_index'])
        self.assertEqual(stream_block_list[1].format,definitions[0]['data_format'])
        definitions.append(definitions[-1])
        with self.assertRaises(AHDSStreamError):
            stream_block_list = self.header._load_definitions(self.header_blocks['data_definitions'])
        definitions[-1:] = []

    def test_load(self):
        self.header._load()
        #assert False

    def test_init(self):
        header_simple = header.AmiraHeader(self.filepath)
        # assert False
        header_true = header.AmiraHeader(self.filepath,load_streams=False)
        # assert False
        with self.assertRaises(ValueError):
            header_failed = header.AmiraHeader(self.filepath,load_streams='FORCELOAD')

class TestInitHxSurfaceHeader(TestHeaderBase):
    filename = "full.surf"
    @classmethod
    def setUpClass(cls,noheader=False):
        super(TestInitHxSurfaceHeader,cls).setUpClass(noheader=True)
    
    def test_load_hxsurface_array_declarations(self):
        designation = self.header_blocks['designation']
        self.header._load_designation(self.header_blocks['designation'])
        declarations = self.header_blocks['array_declarations']
        self.header._load_declarations(self.header_blocks['array_declarations'])
        self.assertIsInstance(getattr(self.header,'Vertices',None),Block)
        self.assertEqual(getattr(self.header.Vertices,'length',-1),self.header_blocks['array_declarations'][0]['array_dimension'])
        self.assertIsInstance(getattr(self.header,'Patches',None),ListBlock)
        self.assertEqual(getattr(self.header,'NBranchingPoints',-1),2)
        self.assertEqual(getattr(self.header,'NVerticesOnCurves',-1),2)
        seen = set()
        for decl in self.header_blocks['array_declarations']:
            if decl['array_name'] in {'Patches','Surfaces','BoundaryCurves'}:
                self.assertNotIn(decl['array_name'],seen)
                checkitems = getattr(self.header,decl['array_name'],None)
                self.assertIsInstance(checkitems,Block)
                self.assertEqual(len(checkitems),decl['array_dimension'])
                for itemid,item in enumerate(checkitems):
                    if itemid < 1:
                        self.assertIsNone(item)
                        continue
                    self.assertIsInstance(item,Block)
                    self.assertEqual(int(item.name[-1:]),itemid)
                    self.assertIs(getattr(checkitems,item.name),item)
                seen.add(decl['array_name'])
        self.assertEqual(len(seen),3)

    def test_load_definitions(self):
        designation = self.header_blocks['designation']
        self.header._load_designation(self.header_blocks['designation'])
        declarations = self.header_blocks['array_declarations']
        self.header._load_declarations(self.header_blocks['array_declarations'])
        definitions = self.header_blocks['data_definitions']
        stream_block_list = self.header._load_definitions(self.header_blocks['data_definitions'])
        self.assertEqual(self.header.Vertices.length,6)
        self.assertEqual(len(self.header.Patches),6)
        self.assertTrue(self.header.Patches[0] is None)
        self.assertEqual(len(self.header.BoundaryCurves),4)
        self.assertTrue(self.header.BoundaryCurves[0] is None)
        self.assertEqual(len(self.header.Surfaces),4)
        self.assertTrue(self.header.Surfaces[0] is None)
        self.assertEqual(self.header.NBranchingPoints,2)
        self.assertEqual(self.header.NVerticesOnCurves,2)

    def test_load(self):
        self.header._load()
        #assert False
        
        

class TestInitHeaderSimpleMaterials(TestHeaderBase):
    filename = "test_simple_materials_noparams.am"
    @classmethod
    def setUpClass(cls,noheader=False):
        super(TestInitHeaderSimpleMaterials,cls).setUpClass(noheader=True)

    def test_load_materials(self):
        designation = self.header_blocks['designation']
        self.header._load_designation(self.header_blocks['designation'])
        parameters = self.header_blocks['materials']
        loaded_parameters = self.header._load_parameters(self.header_blocks['materials'],name='Materials')
        self.assertIsInstance(getattr(loaded_parameters,'Exterior',None),Block)
        self.assertEqual(getattr(loaded_parameters.Exterior,'Id',-1),0)
        self.assertIs(loaded_parameters[loaded_parameters.Exterior.Id],loaded_parameters.Exterior)
        self.assertIsInstance(getattr(loaded_parameters,'Something',None),Block)
        self.assertEqual(getattr(loaded_parameters.Something,'Id',-1),4)
        self.assertIs(loaded_parameters[loaded_parameters.Something.Id],loaded_parameters.Something)
        self.assertIsInstance(getattr(loaded_parameters,'Interior',None),Block)
        self.assertEqual(getattr(loaded_parameters.Interior,'Id',-1),7)
        self.assertIs(loaded_parameters[loaded_parameters.Interior.Id],loaded_parameters.Interior)
        parameters.append({'parameter_name':'red','parameter_value':['<!?c?!>',1,0,0]})
        with self.assertWarns(UserWarning):
            loaded_parameters = self.header._load_parameters(self.header_blocks['materials'],name='Materials')
        self.assertIsInstance(getattr(loaded_parameters,'red',None),Block)
        self.assertIn(getattr(loaded_parameters.red,'Id',-1),range(1,4))
        self.assertIs(loaded_parameters[loaded_parameters.red.Id],loaded_parameters.red)
        parameters.append({'parameter_name':'Signal','parameter_value':'red'})
        with self.assertWarns(UserWarning):
            loaded_parameters = self.header._load_parameters(self.header_blocks['materials'],name='Materials')
        self.assertEqual(getattr(loaded_parameters,'Signal',''),'red')
        del parameters[-2:]

    def test_load(self):
        self.header._load()
        #assert False
        

class TestInitHeaderSimpleMixedMaterials(TestHeaderBase):
    filename = "test_simple_mixed_mat_spec.am"
    @classmethod
    def setUpClass(cls,noheader=False):
        super(TestInitHeaderSimpleMixedMaterials,cls).setUpClass(noheader=True)

    def test_load(self):
        self.header._load()
        #assert False
        
class TestInitHeaderMetaDeclarations(TestHeaderBase):
    filename = "BinaryHxSpreadSheet62x200.am"
    @classmethod
    def setUpClass(cls,noheader=False):
        super(TestInitHeaderMetaDeclarations,cls).setUpClass(noheader=True)

    def test_load_with_meta_declarations(self):
        designation = self.header_blocks['designation']
        self.header._load_designation(self.header_blocks['designation'])
        declarations = self.header_blocks['array_declarations']
        self.header._load_declarations(self.header_blocks['array_declarations'])
        self.assertIsInstance(getattr(self.header,'Sheet1',None),AmiraSpreadSheet)
        self.assertEqual(len(self.header.Sheet1),len(declarations)-1)
        for itemid,item in enumerate(self.header.Sheet1):
            self.assertIsInstance(item,Block)
            self.assertEqual(int(item.name[-4:]),itemid)
            self.assertEqual(getattr(item,'length',0),62)

    def test_load(self):
        self.header._load()
        #assert False

 
class TestInitFieldOnTetra(TestHeaderBase):
    filename = "FieldOnTetraMesh.am"
    @classmethod
    def setUpClass(cls,noheader=False):
        super(TestInitFieldOnTetra,cls).setUpClass(noheader=True)
 

    def test_load_definitions(self):
        designation = self.header_blocks['designation']
        self.header._load_designation(self.header_blocks['designation'])
        declarations = self.header_blocks['array_declarations']
        self.header._load_declarations(self.header_blocks['array_declarations'])
        definitions = self.header_blocks['data_definitions']
        stream_block_list = self.header._load_definitions(self.header_blocks['data_definitions'])
        self.assertEqual(self.header.Tetrahedra.Data.field_name,'f')

class TestInit2FieldOnTetra(TestHeaderBase):
    filename = "2FieldOnTetraMesh.am"
    @classmethod
    def setUpClass(cls,noheader=False):
        super(TestInit2FieldOnTetra,cls).setUpClass(noheader=True)

    def test_2field_on_tetra_mesh(self):
        designation = self.header_blocks['designation']
        self.header._load_designation(self.header_blocks['designation'])
        declarations = self.header_blocks['array_declarations']
        self.header._load_declarations(self.header_blocks['array_declarations'])
        definitions = self.header_blocks['data_definitions']
        stream_block_list = self.header._load_definitions(self.header_blocks['data_definitions'])
        self.assertEqual(self.header.Tetrahedra.Data.field_name,'f1')
        self.assertEqual(self.header.Tetrahedra.Data2.field_name,'f2')

class TestInitBadFieldOnTetra(TestHeaderBase):
    filename = "BadFieldOnTetraMesh.am"
    @classmethod
    def setUpClass(cls,noheader=False):
        super(TestInitBadFieldOnTetra,cls).setUpClass(noheader=True)

    def test_bad_field_on_tetra_mesh(self):
        designation = self.header_blocks['designation']
        self.header._load_designation(self.header_blocks['designation'])
        declarations = self.header_blocks['array_declarations']
        self.header._load_declarations(self.header_blocks['array_declarations'])
        definitions = self.header_blocks['data_definitions']
        with self.assertRaises(AHDSStreamError):
            stream_block_list = self.header._load_definitions(self.header_blocks['data_definitions'])


class TestInitBad2FieldOnTetra(TestHeaderBase):
    filename = "Bad2FieldOnTetraMesh.am"
    @classmethod
    def setUpClass(cls,noheader=False):
        super(TestInitBad2FieldOnTetra,cls).setUpClass(noheader=True)

    def test_bad2_field_on_tetra_mesh(self):
        designation = self.header_blocks['designation']
        self.header._load_designation(self.header_blocks['designation'])
        declarations = self.header_blocks['array_declarations']
        self.header._load_declarations(self.header_blocks['array_declarations'])
        definitions = self.header_blocks['data_definitions']
        with self.assertRaises(AHDSStreamError):
            stream_block_list = self.header._load_definitions(self.header_blocks['data_definitions'])

class TestInitDoubleDatadescriptor(TestHeaderBase):
    filename = "testdoubldatadescriptor.am"
    @classmethod
    def setUpClass(cls,noheader=False):
        super(TestInitDoubleDatadescriptor,cls).setUpClass(noheader=True)

    def test_bad2_field_on_tetra_mesh(self):
        designation = self.header_blocks['designation']
        self.header._load_designation(self.header_blocks['designation'])
        declarations = self.header_blocks['array_declarations']
        self.header._load_declarations(self.header_blocks['array_declarations'])
        definitions = self.header_blocks['data_definitions']
        with self.assertRaises(AHDSStreamError):
            stream_block_list = self.header._load_definitions(self.header_blocks['data_definitions'])


# class TestHeaderBlock(TestHeaderBase):
# 
#     def test_amiraheader(self):
#         self.assertIsInstance(self.header, header.AmiraHeader)
# 
#     def test_add_attr(self):
#         self.header.Parameters.add_attr('x', 10)
#         self.assertTrue(hasattr(self.header.Parameters, 'x'))
#         self.assertEqual(self.header.Parameters.x, 10)
# 
#     def test_materials_block(self):
#         """Test the structure of the Materials block"""
#         self.assertTrue(hasattr(self.header, 'Parameters'))
#         self.assertTrue(hasattr(self.header.Parameters, 'Materials'))
#         self.assertCountEqual(self.header.Parameters.Materials.ids, [1,3])
# 
#     def test_big_endian_format(self):
#         self.assertEqual(self.header.format,"BINARY")
#         self.assertEqual(self.header.endian,"BIG")
# 
# class TestLoadHeaderOnly(TestHeaderBase):
#     @classmethod
#     def setUpClass(cls,noheader=False):
#         super(TestLoadHeaderOnly,cls).setUpClass(noheader=True)
#         cls.header = header.AmiraHeader(cls.filepath,load_streams=False)
# 
#     def test_only_amiraheader(self):
#         self.assertIsInstance(self.header, header.AmiraHeader)
#         self.assertEqual(self.header._load_streams,HEADERONLY)
# 
# 
# 
# class TestLoadImmediate(TestHeaderBase):
#     @classmethod
#     def setUpClass(cls,noheader=False,verbose=False):
#         super(TestLoadImmediate,cls).setUpClass(noheader=True)
#         cls.header = header.AmiraHeader(cls.filepath,load_streams=True)
# 
#     def test_immediate_load_streams(self):
#         self.assertIsInstance(self.header, header.AmiraHeader)
#         self.assertEqual(self.header._load_streams,IMMEDIATE)
# 

class TestLoadErrorsWarnings(TestHeaderBase):

    def test_invalid_stream_setting(self):
        with self.assertRaises(ValueError):
            header.AmiraHeader(self.filepath,load_streams='12')

    def test_deprecated_from_file(self):
        with self.assertWarns(DeprecationWarning):
            ah = header.AmiraHeader.from_file(self.filepath)

class TestProperties(TestHeaderBase):

    @classmethod
    def setUpClass(cls,noheader=False,verbose=False):
        super(TestProperties,cls).setUpClass(noheader=noheader,rawheader=True)

    def test_literal_data(self):
        with open(self.filepath,'rb') as fhnd:
            data_format,_,data_size,data = get_header(fhnd,verbose=True)
        self.assertEqual(self.header.literal_data,data)
        self.assertEqual(len(self.header),data_size)
        self.assertEqual(self.header.file_format,data_format)

    def test_designation(self):
        with self.assertWarns(DeprecationWarning):
            self.assertTrue(self.header.designation is self.header)

    def test_definitions(self):
        with self.assertWarns(DeprecationWarning):
            self.assertTrue(self.header.definitions is self.header)

    def test_data_pointers(self):
        with self.assertWarns(DeprecationWarning):
            self.assertTrue(isinstance(self.header.data_pointers,Block) and self.header.data_pointers.name=="data_pointers")

    def test_filetype(self):
        with self.assertWarns(DeprecationWarning):
            self.assertEqual(self.header.filetype,self.file_format)
        
class test_no_parameters(TestHeaderBase):
    filename = "test12_no_parameters.am"

    def test_created_parameters(self):
        self.assertTrue(getattr(self.header,'Parameters',None) is not None)
 
class TestScalar(TestHeaderBase):
    filename = "testscalar.am"
    def test_little_endian_format(self):
        self.assertEqual(self.header.format,"BINARY")
        self.assertEqual(self.header.endian,"LITTLE")

    def test_stream_by_index(self):
        # no need to get valid stream
        # implicilty tested by load_streams=IMMEDIATE
        with self.assertRaises(IndexError):
            self.header.get_stream_by_index(0)
        with self.assertRaises(IndexError):
            self.header.get_stream_by_index(2)
        stream = self.header.get_stream_by_index(1)
        self.assertIsInstance(stream,AmiraMeshDataStream)
        self.assertIs(stream.parent,self.header.Lattice)
        self.assertEqual(stream.data_index,1)
        self.assertEqual(stream.name,'Data')

    def test_get_stream_offset(self):
        # no need to get valid offset
        # implicilty tested by load_streams=IMMEDIATE
        with self.assertRaises(ValueError):
            self.header.get_stream_offset(None)

        no_stream = Block('NoStream')
        with self.assertRaises(ValueError):
            self.header.get_stream_offset(no_stream)
        no_stream.add_attr('data_index',0)
        with self.assertRaises(ValueError):
            self.header.get_stream_offset(no_stream)
        no_stream.add_attr('data_index',2)
        with self.assertRaises(ValueError):
            self.header.get_stream_offset(no_stream)
        no_stream.add_attr('data_index',1)
        with self.assertRaises(ValueError):
            self.header.get_stream_offset(no_stream)

        class FakeBlock():
            def __init__(self):
                self.data_index = 1
        fake_block = FakeBlock()
        with self.assertRaises(ValueError):
            self.header.get_stream_offset(fake_block)
        first_stream = self.header.get_stream_by_index(1)
        first_stream_offset = self.header.get_stream_offset(first_stream)
        self.assertEqual(first_stream_offset,self.header._header_length)
        self.assertEqual(first_stream_offset,self.header._stream_offset)
        

    def test_set_stream_offset(self):
        # no need to set valid offset
        # implicilty tested by load_streams=IMMEDIATE
        any_offset = 12902
        with self.assertRaises(ValueError):
            self.header.set_stream_offset(None,any_offset)
        no_stream = Block('NoStream')
        with self.assertRaises(ValueError):
            self.header.set_stream_offset(no_stream,any_offset)
        no_stream.add_attr('data_index',0)
        with self.assertRaises(ValueError):
            self.header.set_stream_offset(no_stream,any_offset)
        no_stream.add_attr('data_index',2)
        with self.assertRaises(ValueError):
            self.header.set_stream_offset(no_stream,any_offset)
        no_stream.add_attr('data_index',1)
        with self.assertRaises(ValueError):
            self.header.set_stream_offset(no_stream,any_offset)

        class FakeBlock():
            def __init__(self):
                self.data_index = 1
        fake_block = FakeBlock()
        with self.assertRaises(ValueError):
            self.header.set_stream_offset(fake_block,any_offset)
        first_stream = self.header.get_stream_by_index(1)
        first_stream_offset = self.header.get_stream_offset(first_stream)
        self.header.set_stream_offset(first_stream,any_offset)
        self.assertEqual(self.header._stream_offset,any_offset)

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


# class TestDestinctionListOfMaterialNoParameters(TestHeaderBase):
#     filename = "test_simple_materials_noparams.am"
#     def test_distinction_list_of_Material_no_parameters(self):
#         self.assertTrue(isinstance(getattr(self.header.Parameters,'Materials'),Block))
#         self.assertEqual(self.header.Parameters.Materials.Exterior.Id,0)
#         self.assertEqual(self.header.Parameters.Materials.Something.Id,4)
#         self.assertEqual(self.header.Parameters.Materials.Interior.Id,7)
# 
# class TestDestinctionListOfMaterialMixed(TestHeaderBase):
#     filename = "test_simple_mixed_mat_spec.am"
#     def test_distinction_list_of_Material_mixed(self):
#         self.assertTrue(isinstance(getattr(self.header.Parameters,'Materials'),Block))
#         self.assertEqual(self.header.Parameters.Materials.Exterior.Id,0)
#         self.assertEqual(self.header.Parameters.Materials.Something.Id,4)
#         self.assertEqual(self.header.Parameters.Materials.Interior.Id,7)
#         self.assertEqual(self.header.Parameters.Materials.Outerspace.Id,9)

class TestSingleMat(TestHeaderBase):
    filename = "testscalar_single_mat.am"
    def test_signle_mat(self):
        self.assertTrue(isinstance(getattr(self.header.Parameters,'Materials'),Block))


class TestSimpleSurf(TestHeaderBase):
    filename = "simple.surf"

    def test_simple_surf(self):
        self.assertEqual(self.header.Vertices.length,11)
        self.assertEqual(len(self.header.Patches),4)
        self.assertTrue(self.header.Patches[0] is None)


# class TestFullSurf(TestHeaderBase):
#     filename = "full.surf"
#     @classmethod
#     def setUpClass(cls,noheader=False):
#         super(TestFullSurf,cls).setUpClass(noheader=noheader)
# 
#     def test_full_surf(self):
#         self.assertEqual(self.header.Vertices.length,6)
#         self.assertEqual(len(self.header.Patches),6)
#         self.assertTrue(self.header.Patches[0] is None)
#         self.assertEqual(len(self.header.BoundaryCurves),4)
#         self.assertTrue(self.header.BoundaryCurves[0] is None)
#         self.assertEqual(len(self.header.Surfaces),4)
#         self.assertTrue(self.header.Surfaces[0] is None)
#         self.assertEqual(self.header.NBranchingPoints,2)
#         self.assertEqual(self.header.NVerticesOnCurves,2)
# 
# 
# class TestFieldOnTetra(TestHeaderBase):
#     filename = "FieldOnTetraMesh.am"
# 
#     def test_field_on_tetra_mesh(self):
#         self.assertEqual(self.header.Tetrahedra.Data.field_name,'f')
# 
# 
# class Test2FieldOnTetra(TestHeaderBase):
#     filename = "2FieldOnTetraMesh.am"
# 
#     def test_2field_on_tetra_mesh(self):
#         self.assertEqual(self.header.Tetrahedra.Data.field_name,'f1')
#         self.assertEqual(self.header.Tetrahedra.Data2.field_name,'f2')
# 
# class TestBadFieldOnTetra(TestHeaderBase):
#     filename = "BadFieldOnTetraMesh.am"
#     @classmethod
#     def setUpClass(cls,noheader=False):
#         try:
#             super(TestBadFieldOnTetra,cls).setUpClass()
#         except AHDSStreamError as delayed:
#             cls.raise_delayed = delayed
#         else:
#             cls.raise_delayed = None
# 
#     def test_bad_field_on_tetra_mesh(self):
#         self.assertIsInstance(self.raise_delayed,AHDSStreamError)
# 
# 
# class TestBad2FieldOnTetra(TestHeaderBase):
#     filename = "Bad2FieldOnTetraMesh.am"
#     @classmethod
#     def setUpClass(cls,noheader=False):
#         try:
#             super(TestBad2FieldOnTetra,cls).setUpClass()
#         except AHDSStreamError as delayed:
#             cls.raise_delayed = delayed
#         else:
#             cls.raise_delayed = None
# 
#     def test_bad2_field_on_tetra_mesh(self):
#         self.assertIsInstance(self.raise_delayed,AHDSStreamError)
# 
# class TestDoubleDescriptor(TestHeaderBase):
#     filename = "testdoubldatadescriptor.am"
#     @classmethod
#     def setUpClass(cls,noheader=False):
#         try:
#             super(TestDoubleDescriptor,cls).setUpClass()
#         except AHDSStreamError as delayed:
#             cls.raise_delayed = delayed
#         else:
#             cls.raise_delayed = None
# 
#     def test_double_descriptor(self):
#         self.assertIsInstance(self.raise_delayed,AHDSStreamError)

