# -*- coding: utf-8 -*-
from __future__ import print_function

import os
import pytest
import unittest
import numpy as np
import copy
import re
import types

from ahds import grammar, core, proc
from . import TEST_DATA_PATH,Py23FixTestCase

class TestStreamDelimiters(unittest.TestCase):
    # TODO not working check how todo in unittest grrr
    @Py23FixTestCase.parametrize(
        ['filename','stream_delimiters'],
        [
            ("testscalar.am",grammar._stream_delimiters[0]),
            ("BinaryCustomLandmarks.elm",grammar._stream_delimiters[0]),
            ("simple.surf",grammar._stream_delimiters[1]),
            ("full.surf",grammar._stream_delimiters[1]),
            ("BinaryHyperSurface.surf",grammar._stream_delimiters[1])
        ]
    )
    def test_stream_header_patterns(self,filename,stream_delimiters):
        filepath = os.path.join(TEST_DATA_PATH,filename)
        with open(filepath,'rb') as fhnd:
            data = fhnd.read(max(grammar._rescan_overlap,50))
            _detected_format = grammar._file_format_match.match(data)
            file_format = core._decode_string(_detected_format.group('format')) if _detected_format else '<<unknown>>'
            self.assertIn(file_format,{'AmiraMesh',"HyperSurface"})
            more_header_data,data = data,b''
            _chunklen = 0
            while more_header_data:
                data += more_header_data
                m = stream_delimiters.search(data, _chunklen)
                if m is not None:
                    data,stream_data = data[:m.start()],data[m.start():]
                    break
                _chunklen = len(data) - grammar._rescan_overlap
                more_header_data = fhnd.read(16384)
            else:
                self.fail("missed stream handle/header")
    
class TestGramarBase(unittest.TestCase):
    filename = 'testscalar.am'
    @classmethod
    def setUpClass(cls,noheader=False,noparse=False):
        cls.filepath = os.path.join(TEST_DATA_PATH,cls.filename)
        with open(cls.filepath,'rb') as fhnd:
            data = fhnd.read(max(grammar._rescan_overlap,50))
            _detected_format = grammar._file_format_match.match(data)
            cls.file_format = core._decode_string(_detected_format.group('format')) if _detected_format else '<<unknown>>'
            if noheader:
                return
            if cls.file_format == "HyperSurface":
                stream_delimiter = grammar._stream_delimiters[1]
            else:
                stream_delimiter = grammar._stream_delimiters[0]
            more_header_data,data = data,b''
            _chunklen = 0
            while more_header_data:
                data += more_header_data
                m = stream_delimiter.search(data, _chunklen)
                if m is not None:
                    data,stream_data = data[:m.start()],data[m.start():]
                    break
                _chunklen = len(data) - grammar._rescan_overlap
                more_header_data = fhnd.read(16384)
            cls.header = core._decode_string(data)
            cls.header_size = len(cls.header)
        if noparse:
            return
        parser = grammar.AmiraMeshParser()
        success,cls.parsed_header,next_item = parser.parse(cls.header)

class AmiraSpreadSheet(core.Block):
    pass

class SomeContentTypeDispatchFilter(proc.DispatchFilter):
        
    def filter(self,array_definition):
        return None

    def post_process(self,data_definition):
        return data_definition
        
class AddSomeMetaDataDispatchFilter(proc.DispatchFilter):
    def filter(self,array_definition):
        array_name = array_definition.get('array_name',None)
        if array_name is None:
            return None
        has_counter = TestContentFilters._extract_trailing_counter.match(array_name[::-1])
        if has_counter is None:
            return None
        base_name = array_name[:-has_counter.end()]
        array_index = int(array_name[-has_counter.end():])
        #    base_name,array_blocktype,array_index,meta_data = result
        return (
            'Sheet1',
            AmiraSpreadSheet,
            array_index,
            dict(more_meta_data = 'hello world'),
            dict(more_link_data = 'hello world')
        )
    
    

class TestContentFilters(TestGramarBase):
    filename = 'BinaryHxSpreadSheet62x200.am'
    @classmethod
    def setUpClass(cls,noheader=False,noparse=False):
        super(TestContentFilters,cls).setUpClass(noparse=True)
        cls.single_shot = False

    _extract_trailing_counter = re.compile(r'^\d+(?![-_]\d)')

        
    def test_set_content_filter(self):
        backup_filters = copy.copy(proc.AmiraDispatchProcessor._array_declarations_processors)
        with self.assertRaises(ValueError):
            proc.AmiraDispatchProcessor.set_content_type_filter(12,lambda a,b,c,d:())
        with self.assertRaises(ValueError):
            proc.AmiraDispatchProcessor.set_content_type_filter('',lambda a,b,c,d:())
        with self.assertRaises(ValueError):
            proc.AmiraDispatchProcessor.set_content_type_filter('HxSpreadSheet',None)
        with self.assertRaises(ValueError):
            proc.AmiraDispatchProcessor.set_content_type_filter('HxSpreadSheet',proc.DispatchFilter)
        with self.assertRaises(ValueError):
            proc.AmiraDispatchProcessor.set_content_type_filter('HxSpreadSheet',TestContentFilters)
        proc.AmiraDispatchProcessor.set_content_type_filter('SomeContenType',SomeContentTypeDispatchFilter)
        with self.assertRaises(ValueError):
            proc.AmiraDispatchProcessor.clear_content_type_filter(12)
        with self.assertRaises(ValueError):
            proc.AmiraDispatchProcessor.clear_content_type_filter('')
        proc.AmiraDispatchProcessor.clear_content_type_filter('SomeContentTypeDispatchFilter')
        proc.AmiraDispatchProcessor.set_content_type_filter('HxSpreadSheet',AddSomeMetaDataDispatchFilter)
        parser = grammar.AmiraMeshParser()
        success,self.parsed_header,next_item = parser.parse(self.header)
        self.assertEqual(self.parsed_header[2]['array_declarations'][0].get('more_meta_data',None),'hello world')
        self.assertEqual(
            self.parsed_header[2]['array_declarations'][1]['array_link'].get('more_link_data',None),
            'hello world'
        )
        proc.AmiraDispatchProcessor.clear_content_type_filter('HxSpreadSheet')
        parser = grammar.AmiraMeshParser()
        success,self.parsed_header,next_item = parser.parse(self.header)
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
        with open(self.filepath,'rb') as fhnd:
            with self.assertRaises(ValueError):
                header = grammar.get_header(fhnd,check_format=True)
        with open(self.filepath,'rb') as fhnd:
            with self.assertRaises(ValueError):
                header = grammar.get_header(fhnd,check_format=False)

class TestCorruptHeader(TestGramarBase):
    filename = 'testcorruptheader.am'
    @classmethod
    def setUpClass(cls,noheader=False,noparse=False):
        super(TestCorruptHeader,cls).setUpClass(noparse=True)

    def test_get_header_bad_format(self):
        with open(self.filepath,'rb') as fhnd:
            with self.assertRaises(TypeError):
                file_format,self.parsed_header,header_len,stream_data = grammar.get_header(fhnd)
        

class TestGrammar(TestGramarBase):

    def test_detect_format(self):
        with open(self.filepath,'rb') as fhnd:
            file_format = grammar.get_header(fhnd,check_format=True)
        self.assertTrue(len(file_format)>1)
        self.assertEqual(file_format,self.file_format)
        self.assertIn(file_format, ['AmiraMesh', 'HyperSurface'])

    def test_get_header(self):
        with open(self.filepath,'rb') as fhnd:
            file_format,parsed_header,header_len,header = grammar.get_header(fhnd,verbose=True)
        self.assertEqual(self.header,core._decode_string(header))
        self.assertTrue(len(parsed_header)>0)

    #def test_parse_header(self):
    #    self.assertTrue(len(self.parsed_header) > 0)


class TestMultipleHeaderChunks(TestGramarBase):
    filename = 'BinaryHxSpreadSheet62x200.am'
 
    def test_multiple_chunks(self):
        with open(self.filepath,'rb') as fhnd:
            file_format,parsed_header,header_len,header = grammar.get_header(fhnd,verbose=True)
        self.assertTrue(len(header) > 2)
        self.assertEqual(core._decode_string(header),self.header)
        self.assertEqual(file_format,self.file_format)
        self.assertEqual(file_format,'AmiraMesh')

class TestNextAmiraBinaryStream(TestGramarBase):
    filename = "test8.am"

    def test_next_amira_mesh_binary_stream(self):
        current_offset = self.header_size
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
        current_offset = self.header_size
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
        self.assertEqual(self.file_format,'HyperSurface')
        current_offset = self.header_size
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
                self.assertEqual(item['array_link']['array_parent'],'Patches')
                self.assertEqual(item['array_link']['array_itemid'],index)

            self.assertEqual(len(self.parsed_header[4]['data_definitions']),10)
            self.assertEqual(
                [item['array_reference'] for item in self.parsed_header[4]['data_definitions']],
                ['Vertices', 'Patch1', 'Patch1', 'Patch1', 'Patch2', 'Patch2', 'Patch2', 'Patch3', 'Patch3', 'Patch3']
            )
    def test_trigger_errors(self):
        self.assertEqual(self.file_format,'HyperSurface')
        true_format = self.parsed_header[0]['designation']['format']
        self.parsed_header[0]['designation']['format'] = 12
        self.assertEqual(self.file_format,'HyperSurface')
        current_offset = self.header_size
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
        self.assertEqual(self.file_format,'HyperSurface')
        current_offset = self.header_size
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
 
    def test_mixedup_header(self):
        self.assertEqual(self.file_format,'HyperSurface')
        current_offset = self.header_size
        stream_remainder = b''
        filecontent1 = copy.deepcopy(self.parsed_header[:1] + self.parsed_header[2:])
        filecontent2 = copy.deepcopy(self.parsed_header[:1] + self.parsed_header[-1:] + self.parsed_header[1:-1])
        filecontent3 = copy.deepcopy(self.parsed_header[:-1])
        filecontent4 = copy.deepcopy(self.parsed_header[:1] + self.parsed_header[2:] + self.parsed_header[1:2])
        with open(self.filepath,'rb') as fhnd:
            fhnd.seek(current_offset)
            try:
                self.parsed_header = grammar.parse_hypersurface_data(
                    fhnd,
                    parsed_data = self.parsed_header,
                    stream_data = stream_remainder
                )
            except grammar.AHDSStreamError as err:
                self.assertEqual(2,sum( 1 for item in  self.parsed_header for name in item if name in {'array_declarations','data_definitions'}))
        with open(self.filepath,'rb') as fhnd:
            fhnd.seek(current_offset)
            try:
                filecontent1 = grammar.parse_hypersurface_data(
                    fhnd,
                    parsed_data = filecontent1,
                    stream_data = stream_remainder
                )
            except grammar.AHDSStreamError as err:
                self.assertEqual(2,sum( 1 for item in  self.parsed_header for name in item if name in {'array_declarations','data_definitions'}))
        with open(self.filepath,'rb') as fhnd:
            fhnd.seek(current_offset)
            try:
                filecontent2 = grammar.parse_hypersurface_data(
                    fhnd,
                    parsed_data = filecontent2,
                    stream_data = stream_remainder
                )
            except grammar.AHDSStreamError as err:
                self.assertEqual(2,sum( 1 for item in  self.parsed_header for name in item if name in {'array_declarations','data_definitions'}))
        with open(self.filepath,'rb') as fhnd:
            fhnd.seek(current_offset)
            try:
                filecontent3 = grammar.parse_hypersurface_data(
                    fhnd,
                    parsed_data = filecontent3,
                    stream_data = stream_remainder
                )
            except grammar.AHDSStreamError as err:
                self.assertEqual(2,sum( 1 for item in  self.parsed_header for name in item if name in {'array_declarations','data_definitions'}))

    def test_parse_bad_simple_surf(self):
        self.assertEqual(self.file_format,'HyperSurface')
        current_offset = self.header_size
        stream_remainder = b''
        with open(self.filepath,'rb') as fhnd:
            fhnd.seek(current_offset)
            with self.assertRaises(grammar.AHDSStreamError):
                self.parsed_header = grammar.parse_hypersurface_data(
                    fhnd,
                    parsed_data = self.parsed_header,
                    stream_data = stream_remainder
                )

    def test_parse_bad_simple_surf_not_success(self):
        self.assertEqual(self.file_format,'HyperSurface')
        parser = grammar.HyperSufaceParser()
        success,self.parsed_header,next_item = parser.parse(self.header[1:])
        self.assertEqual(success,0)
        current_offset = self.header_size
        with open(self.filepath,'rb') as fhnd:
            fhnd.seek(current_offset)
            parser = grammar.HyperSufaceParser(fhnd=fhnd,verbose=True)
            with self.assertRaises(grammar.AHDSStreamError):
                success,self.parsed_header,next_item = parser.parse(self.header)
                
    def test_get_header(self):
        self.assertEqual(self.file_format,'HyperSurface')
        with open(self.filepath,'rb') as fhnd:
            with self.assertRaises(grammar.AHDSStreamError):
                 file_format,self.parsed_header,header_len,stream_data = grammar.get_header(fhnd,verbose=True)

class TestHyperSurfaceEmptyPatches(TestGramarBase):
    filename = 'simple_missing_patches.surf'

    def test_missing_patches(self):
        self.assertEqual(self.file_format,'HyperSurface')
        current_offset = self.header_size
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
        self.assertEqual(self.file_format,'HyperSurface')
        current_offset = self.header_size
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
        self.assertEqual(self.file_format,'HyperSurface')
        current_offset = self.header_size
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
        self.assertEqual(self.file_format,'HyperSurface')
        current_offset = self.header_size
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
        self.assertEqual(self.file_format,'HyperSurface')
        current_offset = self.header_size
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
        self.assertEqual(self.file_format,'HyperSurface')
        current_offset = self.header_size
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
        self.assertEqual(self.file_format,'HyperSurface')
        current_offset = self.header_size
        stream_remainder = b''
        with open(self.filepath,'rb') as fhnd:
            fhnd.seek(current_offset)
            self.parsed_header = grammar.parse_hypersurface_data(
                fhnd,
                parsed_data = self.parsed_header,
                stream_data = stream_remainder
            )

            
            
            
            

        
        

