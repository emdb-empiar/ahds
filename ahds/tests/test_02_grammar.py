# -*- coding: utf-8 -*-
from __future__ import print_function

import os
import unittest
import numpy as np
import copy
import re

from ahds import grammar, core, proc
from ahds.tests import TEST_DATA_PATH

class TestGramarBase(unittest.TestCase):
    filename = 'testscalar.am'
    @classmethod
    def setUpClass(cls,noheader=False,noparse=False):
        cls.filepath = os.path.join(TEST_DATA_PATH,cls.filename)
        cls.file_format = grammar.detect_format(cls.filepath)
        if noheader:
            return
        cls.header = grammar.get_header(cls.filepath)
        if noparse:
            return
        cls.parsed_header = grammar.parse_header(cls.header[1] if len(cls.header) > 2 else '')

class AmiraSpreadSheet(core.Block):
    pass

class TestContentFilters(TestGramarBase):
    filename = 'BinaryHxSpreadSheet62x200.am'
    @classmethod
    def setUpClass(cls,noheader=False,noparse=False):
        super(TestContentFilters,cls).setUpClass(noparse=True)
        cls.single_shot = False

    _extract_trailing_counter = re.compile(r'^\d+(?![-_]\d)')
        
    @classmethod
    def add_some_meta_data(cls,typed_meta_declaration,array_declaration,content_type,base_contenttype):
        if content_type != 'HxSpreadSheet' and base_contenttype != 'HxSpreadSheet':
            return None
        if typed_meta_declaration is not None:
            if cls.single_shot:
                return
        array_name = array_declaration.get('array_name',None)
        if array_name is None:
            return None
        has_counter = TestContentFilters._extract_trailing_counter.match(array_name[::-1])
        if has_counter is None:
            return None
        base_name = array_name[:-has_counter.end()]
        array_index = int(array_name[-has_counter.end():])
        return (
            'Sheet1',
            array_index,
            AmiraSpreadSheet,
            dict(more_meta_data = 'hello world'),
            dict(more_link_data = 'hello world')
        )

        
    def test_set_content_filter(self):
        backup_filters = copy.copy(proc.AmiraDispatchProcessor._array_declarations_processors)
        with self.assertRaises(ValueError):
            proc.AmiraDispatchProcessor.set_content_type_filter(12,lambda a,b,c,d:())
        with self.assertRaises(ValueError):
            proc.AmiraDispatchProcessor.set_content_type_filter('',lambda a,b,c,d:())
        with self.assertRaises(ValueError):
            proc.AmiraDispatchProcessor.set_content_type_filter('HxSpreadSheet',None)
        
        proc.AmiraDispatchProcessor.set_content_type_filter('not_relevant',lambda a,b,c,d:())
        with self.assertRaises(ValueError):
            proc.AmiraDispatchProcessor.clear_content_type_filter(12)
        with self.assertRaises(ValueError):
            proc.AmiraDispatchProcessor.clear_content_type_filter('')
        proc.AmiraDispatchProcessor.clear_content_type_filter('not_relevant')
        proc.AmiraDispatchProcessor.set_content_type_filter('HxSpreadSheet',TestContentFilters.add_some_meta_data)
        self.parsed_header = grammar.parse_header(self.header[1])
        self.assertEqual(self.parsed_header[2]['array_declarations'][0].get('more_meta_data',None),'hello world')
        self.assertEqual(
            self.parsed_header[2]['array_declarations'][1]['array_links']['HxSpreadSheet'].get('more_link_data',None),
            'hello world'
        )
        self.__class__.single_shot = True
        self.parsed_header = grammar.parse_header(self.header[1])
        self.assertEqual(
            self.parsed_header[2]['array_declarations'][0].get('array_links',None),{}
        )
        self.assertEqual(
            self.parsed_header[2]['array_declarations'][1].get('array_links',None),{}
        )
        proc.AmiraDispatchProcessor.clear_content_type_filter('HxSpreadSheet')
        self.parsed_header = grammar.parse_header(self.header[1])
        proc.AmiraDispatchProcessor._array_declarations_processors.update(backup_filters)
        

class TestBadContentTypeParameter(TestGramarBase):
    filename = 'corrupt_content_type.lmb'
    
    def test_bad_contenttype_parameter(self):
        self.assertTrue(
            any( 
                par['parameter_name'] == 'ContentType' and par['parameter_value'] == 12 
                for par in self.parsed_header[-2]['parameters']
            )
        )

class TestMultipleContentType(TestGramarBase):
    filename = 'multiple_content_type.lmb'

    def test_multiple_content_type(self):
        self.assertEqual(sum(par.get('parameter_name','')=='ContentType' for par in self.parsed_header[-2]['parameters']),3)

class TestBadFormat(TestGramarBase):
    filename = 'testbadformat.am'
    @classmethod
    def setUpClass(cls,noheader=False,noparse=False):
        super(TestBadFormat,cls).setUpClass(noheader=True)

    def test_get_header_bad_format(self):
        with self.assertRaises(ValueError):
            header = grammar.get_header(self.filepath)

class TestCorruptHeader(TestGramarBase):
    filename = 'testcorruptheader.am'
    @classmethod
    def setUpClass(cls,noheader=False,noparse=False):
        super(TestCorruptHeader,cls).setUpClass(noparse=True)

    def test_get_header_bad_format(self):
        with self.assertRaises(TypeError):
            self.parsed_header = grammar.parse_header(self.header[1] if len(self.header) > 2 else '')
        

class TestGrammar(TestGramarBase):

    def test_detect_format(self):
        self.assertTrue(len(self.file_format)>1)
        self.assertIn(self.file_format[0], ['AmiraMesh', 'HyperSurface'])

    def test_get_header(self):
        self.assertTrue(len(self.header) > 2 and self.header[0] == self.file_format[0] and len(self.header[1]) > 0)

    def test_parse_header(self):
        self.assertTrue(len(self.parsed_header) > 0)


class TestMultipleHeaderChunks(TestGramarBase):
    filename = 'BinaryHxSpreadSheet62x200.am'

    def test_multiple_chunks(self):
        self.assertTrue(len(self.header) > 2 and self.header[0] == self.file_format[0] and len(self.header[1]) > 0)

class TestNextAmiraBinaryStream(TestGramarBase):
    filename = "test8.am"

    def test_next_amira_mesh_binary_stream(self):
        current_offset = len(self.header[1])
        stream_remainder = b''
        bytestoread = (
            self.parsed_header[1]['array_declarations'][0]['array_dimension'] *
            self.parsed_header[3]['data_definitions'][0]['data_dimension'] * 4
        )
        bytestoread2 = (
            self.parsed_header[1]['array_declarations'][4]['array_dimension'] *
            self.parsed_header[3]['data_definitions'][1]['data_dimension'] * 4
        )
        bytestoread3 = (
            self.parsed_header[1]['array_declarations'][6]['array_dimension'] * 4 
        )
        with open(self.filepath,'rb') as fhnd:
            fhnd.seek(current_offset)
            stream_data,stream_remainder,next_stream_index,next_offset = grammar.next_amiramesh_binary_stream(fhnd,stream_bytes=64)
            self.assertEqual(next_stream_index,1)
            self.assertTrue(len(stream_remainder)>0)
            current_offset = next_offset
            stream_data,stream_remainder,next_stream_index,next_offset = grammar.next_amiramesh_binary_stream(
                fhnd,
                stream_bytes=bytestoread,
                stream_data = stream_remainder
            )
            self.assertEqual(len(stream_data),bytestoread)
            self.assertEqual(next_stream_index,2)
            stream_data,stream_remainder,next_stream_index,next_offset = grammar.next_amiramesh_binary_stream(
                fhnd,
                stream_bytes=bytestoread2,
                stream_data=stream_remainder
            )
            self.assertEqual(next_stream_index,3)
            stream_data,stream_remainder,next_stream_index,next_offset = grammar.next_amiramesh_binary_stream(
                fhnd,
                stream_bytes=bytestoread3,
                stream_data=stream_remainder
            )
            self.assertEqual(next_stream_index,-1)
            self.assertEqual(next_offset,-1)
            if stream_remainder:
                stream_data,no_stream_remainder,next_stream_index,next_offset = grammar.next_amiramesh_binary_stream(
                    fhnd,
                    stream_bytes=1024,
                    stream_data=stream_remainder
                )
                self.assertEqual(next_stream_index,-1)
                self.assertEqual(next_offset,-1)
                self.assertEqual(stream_data,stream_remainder)
                self.assertEqual(no_stream_remainder,b'')

class TestNextAmiraASCIIStream(TestGramarBase):
    filename = "BinaryCustomLandmarks.elm"

    def test_next_amira_mesh_ascii_stream(self):
        current_offset = len(self.header[1])
        stream_remainder = b''
        elementstoread = (
            self.parsed_header[2]['array_declarations'][0]['array_dimension'] *
            self.parsed_header[4]['data_definitions'][0]['data_dimension']
        )
        bytestoread = elementstoread * 4
        elementstoread2 = (
            self.parsed_header[2]['array_declarations'][0]['array_dimension']
        )
        bytestoread2 = elementstoread2 * 4
        with open(self.filepath,'rb') as fhnd:
            fhnd.seek(current_offset)
            stream_data,stream_remainder,next_stream_index,next_offset = grammar.next_amiramesh_ascii_stream(fhnd,stream_bytes=64)
            self.assertEqual(next_stream_index,1)
            self.assertTrue(len(stream_remainder)>0)
            current_offset = next_offset
            stream_data,stream_remainder,next_stream_index,next_offset = grammar.next_amiramesh_ascii_stream(
                fhnd,
                stream_bytes=bytestoread,
                stream_data = stream_remainder
            )
            self.assertEqual(np.fromstring(stream_data,sep=' ').size,elementstoread)
            self.assertEqual(next_stream_index,2)
            stream_data,stream_remainder,next_stream_index,next_offset = grammar.next_amiramesh_ascii_stream(
                fhnd,
                stream_bytes=bytestoread2,
                stream_data=stream_remainder
            )
            self.assertEqual(np.fromstring(stream_data,sep=' ').size,elementstoread2)
            if stream_remainder:
                stream_data,no_stream_remainder,next_stream_index,next_offset = grammar.next_amiramesh_ascii_stream(
                    fhnd,
                    stream_data=stream_remainder
                )
                self.assertEqual(next_stream_index,-1)
                self.assertEqual(next_offset,-1)
                self.assertEqual(stream_data,stream_remainder)
                self.assertEqual(no_stream_remainder,b'')

class TestHyperSurfaceSimple(TestGramarBase):
    filename = "simple.surf"
         
    def test_parse_simple_hxsurf_ascii(self):
        self.assertEqual(self.file_format[0],'HyperSurface')
        current_offset = len(self.header[1])
        stream_remainder = b''
        with open(self.filepath,'rb') as fhnd:
            fhnd.seek(current_offset)
            self.parsed_header = grammar.parse_hypersurface_data(
                fhnd,
                parsed_data = self.parsed_header,
                stream_data = stream_remainder,
                stream_bytes = 128
            )
            self.assertEqual(len(self.parsed_header[1]['array_declarations']),5)
            self.assertEqual(
                [(item['array_name'],item['array_dimension']) for item in self.parsed_header[1]['array_declarations']],
                [('Vertices',11),('Patches',4),('Patch1',0),('Patch2',0),('Patch3',0)]
            )
            self.assertEqual(self.parsed_header[1]['array_declarations'][1]['array_blocktype'],core.ListBlock)
            for index,item in enumerate(self.parsed_header[1]['array_declarations'][2:],1):
                self.assertEqual(item['array_links']['hxsurface']['array_parent'],'Patches')
                self.assertEqual(item['array_links']['hxsurface']['array_itemid'],index)

            self.assertEqual(len(self.parsed_header[4]['data_definitions']),10)
            self.assertEqual(
                [item['array_reference'] for item in self.parsed_header[4]['data_definitions']],
                ['Vertices', 'Patch1', 'Patch1', 'Patch1', 'Patch2', 'Patch2', 'Patch2', 'Patch3', 'Patch3', 'Patch3']
            )
    def test_trigger_errors(self):
        self.assertEqual(self.file_format[0],'HyperSurface')
        true_format = self.parsed_header[0]['designation']['format']
        self.parsed_header[0]['designation']['format'] = 12
        self.assertEqual(self.file_format[0],'HyperSurface')
        current_offset = len(self.header[1])
        stream_remainder = b''
        with open(self.filepath,'rb') as fhnd:
            fhnd.seek(current_offset)
            with self.assertRaises(grammar.AHDSStreamError):
                self.parsed_header = grammar.parse_hypersurface_data(
                    fhnd,
                    parsed_data = self.parsed_header,
                    stream_data = stream_remainder
                )

        self.parsed_header[0]['designation']['format'] = '@?%$-)/(§"!#'
        stream_remainder = b''
        with open(self.filepath,'rb') as fhnd:
            fhnd.seek(current_offset)
            with self.assertRaises(grammar.AHDSStreamError):
                self.parsed_header = grammar.parse_hypersurface_data(
                    fhnd,
                    parsed_data = self.parsed_header,
                    stream_data = stream_remainder
                )
        self.parsed_header[0]['designation']['format'] = true_format

class TestHyperSurfaceMixup(TestGramarBase):
    filename = "simple.surf"
    def test_mixedup_header(self):
        self.assertEqual(self.file_format[0],'HyperSurface')
        current_offset = len(self.header[1])
        stream_remainder = b''
        filecontent1 = copy.deepcopy(self.parsed_header[:1] + self.parsed_header[2:])
        filecontent2 = copy.deepcopy(self.parsed_header[:1] + self.parsed_header[-1:] + self.parsed_header[1:-1])
        filecontent3 = copy.deepcopy(self.parsed_header[:-1])
        filecontent4 = copy.deepcopy(self.parsed_header[:1] + self.parsed_header[2:] + self.parsed_header[1:2])
        with open(self.filepath,'rb') as fhnd:
            fhnd.seek(current_offset)
            self.parsed_header = grammar.parse_hypersurface_data(
                fhnd,
                parsed_data = self.parsed_header,
                stream_data = stream_remainder
            )
        with open(self.filepath,'rb') as fhnd:
            fhnd.seek(current_offset)
            filecontent1 = grammar.parse_hypersurface_data(
                fhnd,
                parsed_data = filecontent1,
                stream_data = stream_remainder
            )
        with open(self.filepath,'rb') as fhnd:
            fhnd.seek(current_offset)
            filecontent2 = grammar.parse_hypersurface_data(
                fhnd,
                parsed_data = filecontent2,
                stream_data = stream_remainder
            )
        with open(self.filepath,'rb') as fhnd:
            fhnd.seek(current_offset)
            filecontent3 = grammar.parse_hypersurface_data(
                fhnd,
                parsed_data = filecontent3,
                stream_data = stream_remainder
            )
        with open(self.filepath,'rb') as fhnd:
            fhnd.seek(current_offset)
            filecontent4 = grammar.parse_hypersurface_data(
                fhnd,
                parsed_data = filecontent4,
                stream_data = stream_remainder
            )
        self.assertEqual(filecontent1,self.parsed_header)
        self.assertEqual(filecontent2[:1] + filecontent2[2:] + filecontent2[1:2],self.parsed_header)
        self.assertEqual(filecontent3,self.parsed_header)
        self.assertEqual(filecontent4[:1] + filecontent4[-1:] + filecontent4[1:-1],self.parsed_header)
        

class TestHyperSurfaceBrokenSimple(TestGramarBase):
    filename = "broken_simple.surf"

    def test_parse_broken(self):
        self.assertTrue(getattr(self.header,'Vertices',None) is None)

class TestHyperSurfaceBroken2Simple(TestGramarBase):
    filename = "broken2_simple.surf"

    def test_parse_broken2(self):
        self.assertTrue(getattr(self.header,'Vertices',None) is None)
    
         
            
class TestHyperSurfaceBad(TestGramarBase):
    filename = 'bad_simple.surf'
    def test_parse_bad_simple_surf(self):
        self.assertEqual(self.file_format[0],'HyperSurface')
        current_offset = len(self.header[1])
        stream_remainder = b''
        with open(self.filepath,'rb') as fhnd:
            fhnd.seek(current_offset)
            with self.assertRaises(grammar.AHDSStreamError):
                self.parsed_header = grammar.parse_hypersurface_data(
                    fhnd,
                    parsed_data = self.parsed_header,
                    stream_data = stream_remainder
                )

class TestHyperSurfaceEmptyPatches(TestGramarBase):
    filename = 'simple_missing_patches.surf'
    def test_missing_patches(self):
        self.assertEqual(self.file_format[0],'HyperSurface')
        current_offset = len(self.header[1])
        stream_remainder = b''
        with open(self.filepath,'rb') as fhnd:
            fhnd.seek(current_offset)
            with self.assertRaises(grammar.AHDSStreamError):
                self.parsed_header = grammar.parse_hypersurface_data(
                    fhnd,
                    parsed_data = self.parsed_header,
                    stream_data = stream_remainder
                )

class TestHyperSurfaceBadCounter(TestGramarBase):
    filename = 'simple_bad_counter.surf'
    def test_missing_bad_counter(self):
        self.assertEqual(self.file_format[0],'HyperSurface')
        current_offset = len(self.header[1])
        stream_remainder = b''
        with open(self.filepath,'rb') as fhnd:
            fhnd.seek(current_offset)
            with self.assertRaises(grammar.AHDSStreamError):
                self.parsed_header = grammar.parse_hypersurface_data(
                    fhnd,
                    parsed_data = self.parsed_header,
                    stream_data = stream_remainder
                )

class TestHyperSurfaceBadGroup(TestGramarBase):
    filename = 'simple_bad_placed_group.surf'
    def test_missing_placed_group(self):
        self.assertEqual(self.file_format[0],'HyperSurface')
        current_offset = len(self.header[1])
        stream_remainder = b''
        with open(self.filepath,'rb') as fhnd:
            fhnd.seek(current_offset)
            with self.assertRaises(grammar.AHDSStreamError):
                self.parsed_header = grammar.parse_hypersurface_data(
                    fhnd,
                    parsed_data = self.parsed_header,
                    stream_data = stream_remainder
                )

class TestHyperSurfaceIncomplete(TestGramarBase):
    filename = 'simple_incomplete.surf'
    def test_incomplete_group(self):
        self.assertEqual(self.file_format[0],'HyperSurface')
        current_offset = len(self.header[1])
        stream_remainder = b''
        with open(self.filepath,'rb') as fhnd:
            fhnd.seek(current_offset)
            with self.assertRaises(grammar.AHDSStreamError):
                self.parsed_header = grammar.parse_hypersurface_data(
                    fhnd,
                    parsed_data = self.parsed_header,
                    stream_data = stream_remainder
                )

class TestHyperSurfaceFull(TestGramarBase):
    filename = "full.surf"
         
    def test_parse_full_hxsurf_ascii(self):
        self.assertEqual(self.file_format[0],'HyperSurface')
        current_offset = len(self.header[1])
        stream_remainder = b''
        with open(self.filepath,'rb') as fhnd:
            fhnd.seek(current_offset)
            self.parsed_header = grammar.parse_hypersurface_data(
                fhnd,
                parsed_data = self.parsed_header,
                stream_data = stream_remainder,
                stream_bytes = 128
            )
            self.assertEqual(len(self.parsed_header[1]['array_declarations']),17)
            self.assertEqual(
                [(item['array_name'],item.get('array_dimension',None)) for item in self.parsed_header[1]['array_declarations']],
                [
                    ('Vertices',6),('NBranchingPoints',None),('NVerticesOnCurves',None),
                    ('BoundaryCurves',4),('BoundaryCurve1',0),('BoundaryCurve2',0),('BoundaryCurve3',0),
                    ('Patches',6),('Patch1',0),('Patch2',0),('Patch3',0), ('Patch4',0),('Patch5',0),
                    ('Surfaces',4),('Surface1',0),('Surface2',0),('Surface3',0)
                ]
            )
            self.assertEqual(len(self.parsed_header[2]['data_definitions']),35)
            self.assertEqual(
                [
                    (item['array_reference'],item['data_dimension'],item.get('data_shape',None),item['data_name'],item['data_type'])
                     for item in self.parsed_header[2]['data_definitions']
                ],
                [
                    ('Vertices', 3, None, 'Coordinates', 'float'),
                    ('BoundaryCurve1', 1, 3, 'Vertices', 'int'),
                    ('BoundaryCurve2', 1, 2, 'Vertices', 'int'),
                    ('BoundaryCurve3', 1, 3, 'Vertices', 'int'),
                    ('Patch1', None, None, 'InnerRegion', 'char'),
                    ('Patch1', None, None, 'OuterRegion', 'char'),
                    ('Patch1', 1, 0, 'BranchingPoints', 'int'),
                    ('Patch1', 1, 2, 'BoundaryCurves', 'int'),
                    ('Patch1', 3, 3, 'Triangles', 'int'),
                    ('Patch2', None, None, 'InnerRegion', 'char'),
                    ('Patch2', None, None, 'OuterRegion', 'char'),
                    ('Patch2', 1, 0, 'BranchingPoints', 'int'),
                    ('Patch2', 1, 2, 'BoundaryCurves', 'int'),
                    ('Patch2', 3, 2, 'Triangles', 'int'),
                    ('Patch3', None, None, 'InnerRegion', 'char'),
                    ('Patch3', None, None, 'OuterRegion', 'char'),
                    ('Patch3', 1, 0, 'BranchingPoints', 'int'),
                    ('Patch3', 1, 2, 'BoundaryCurves', 'int'),
                    ('Patch3', 3, 3, 'Triangles', 'int'),
                    ('Patch4', None, None, 'InnerRegion', 'char'),
                    ('Patch4', None, None, 'OuterRegion', 'char'),
                    ('Patch4', 1, 0, 'BranchingPoints', 'int'),
                    ('Patch4', 1, 2, 'BoundaryCurves', 'int'),
                    ('Patch4', 3, 1, 'Triangles', 'int'),
                    ('Patch5', None, None, 'InnerRegion', 'char'),
                    ('Patch5', None, None, 'OuterRegion', 'char'),
                    ('Patch5', 1, 0, 'BranchingPoints', 'int'),
                    ('Patch5', 1, 2, 'BoundaryCurves', 'int'),
                    ('Patch5', 3, 1, 'Triangles', 'int'),
                    ('Surface1', None, None, 'Region', 'char'),
                    ('Surface1', 1, 2, 'Patches', 'int'),
                    ('Surface2', None, None, 'Region', 'char'),
                    ('Surface2', 1, 3, 'Patches', 'int'),
                    ('Surface3', None, None, 'Region', 'char'),
                    ('Surface3', 1, 2, 'Patches', 'int')
                ]
            )
            

class TestHyperSurfaceBinary(TestGramarBase):
    filename = "BinaryHyperSurface.surf"
    def test_parse_hxsurface_binary(self):
        self.assertEqual(self.file_format[0],'HyperSurface')
        current_offset = len(self.header[1])
        stream_remainder = b''
        with open(self.filepath,'rb') as fhnd:
            fhnd.seek(current_offset)
            self.parsed_header = grammar.parse_hypersurface_data(
                fhnd,
                parsed_data = self.parsed_header,
                stream_data = stream_remainder
            )
            

class TestHyperSurfaceBinary7(TestGramarBase):
    filename = "test7.surf"
    def test_parse_hxsurface_7_binary(self):
        self.assertEqual(self.file_format[0],'HyperSurface')
        current_offset = len(self.header[1])
        stream_remainder = b''
        with open(self.filepath,'rb') as fhnd:
            fhnd.seek(current_offset)
            self.parsed_header = grammar.parse_hypersurface_data(
                fhnd,
                parsed_data = self.parsed_header,
                stream_data = stream_remainder
            )
        
class TestGetParsedData(TestGramarBase):
    filename = "test7.surf"
    def test_get_parsed_data(self):
        raw_header,header,stream_offset,file_format = grammar.get_parsed_data(self.filepath)
        self.assertEqual(len(raw_header),stream_offset)
            

            
            
            
            

        
        

