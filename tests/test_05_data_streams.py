# -*- coding: utf-8 -*-
from __future__ import print_function

import sys
import os
import os.path
import pytest
import unittest
import re

if sys.version_info[0] >= 3:
    import importlib 
else:
    import imp
from . import TEST_DATA_PATH,Py23FixTestCase
import numpy

#import ahds
from ahds import header, data_stream,IMMEDIATE,HEADERONLY,ONDEMMAND
from ahds.grammar import AHDSStreamError
from ahds.core import Block
from ahds.proc import set_content_type_filter


class TestDataStreamsBase(Py23FixTestCase):
    @classmethod
    def setUpClass(cls,load_streams=IMMEDIATE):
        cls.af_am = header.AmiraHeader(os.path.join(TEST_DATA_PATH, 'test9.am'))
        cls.af_am_hxsurf = header.AmiraHeader(os.path.join(TEST_DATA_PATH, 'test8.am'),load_streams=load_streams)
        cls.af_hxsurf = header.AmiraHeader(os.path.join(TEST_DATA_PATH, 'test7.surf'))

class TestDataStreams(TestDataStreamsBase):
    @classmethod
    def setUpClass(cls,load_streams=IMMEDIATE):
        super(TestDataStreams,cls).setUpClass(load_streams = load_streams)
        cls.spread_sheet = header.AmiraHeader(os.path.join(TEST_DATA_PATH, 'BinaryHxSpreadSheet62x200.am'))

    def test_amirafile(self):
        self.assertIsInstance(self.af_am, header.AmiraHeader)
        self.assertIsInstance(self.af_am_hxsurf, header.AmiraHeader)
        self.assertIsInstance(self.af_hxsurf, header.AmiraHeader)

    def test_data_stream(self):
        # test9.am
        self.assertIsInstance(self.af_am.Lattice, Block)
        self.assertEqual(self.af_am.data_stream_count, 1)
        self.assertEqual(self.af_am.Lattice.Labels.name, 'Labels')

        # test8.am
        self.assertIsInstance(self.af_am_hxsurf, Block)
        self.assertEqual(self.af_am_hxsurf.data_stream_count, 3)
        self.assertEqual(self.af_am_hxsurf.Vertices.name, 'Vertices')
        self.assertEqual(self.af_am_hxsurf.Triangles.name, 'Triangles')
        self.assertEqual(getattr(self.af_am_hxsurf,'Patches-0').name, "Patches-0")

        # test7.surf
        self.assertIsInstance(self.af_hxsurf, Block)
        self.assertEqual(self.af_hxsurf.data_stream_count, 5)
        self.assertEqual(self.af_hxsurf.Patches[1].name,'Patch1')

    def test_spread_sheet(self):
        self.assertIsInstance(getattr(self.spread_sheet,'Sheet1',None),data_stream.AmiraSpreadSheet)
        self.assertEqual(len(self.spread_sheet.Sheet1),500)
        self.assertEqual(self.spread_sheet.Sheet1[100].name, '__Column0100')
        self.assertIsInstance(getattr(self.spread_sheet.Sheet1[100],'__Column0100',None),data_stream.AmiraMeshDataStream)
        self.assertEqual(getattr(self.spread_sheet.Sheet1[100],'__Column0100',Block('')).name, '__Column0100')
        self.assertEqual(self.spread_sheet.Sheet1[499].name, '__Column0499')
        self.assertIsInstance(getattr(self.spread_sheet.Sheet1[499],'__Column0499',None),data_stream.AmiraMeshDataStream)
        self.assertEqual(getattr(self.spread_sheet.Sheet1[499],'__Column0499',Block('')).name, '__Column0499')
        #self.assertEqual(self.spread_sheet.Sheet1[0].dimension,62)


    @staticmethod
    def byterle_encoder(array_data):
        array_data = array_data.flatten()
        changes = numpy.ones(array_data.size,dtype=bool)
        changes[1:] = array_data[1:] != array_data[:-1]
        changes = changes.tolist()
        start = 0
        output_data = bytearray()
        while start < array_data.size:
            try:
                stop = changes.index(True,start+1)
            except ValueError:
                stop = len(changes)
            if stop - start < 2:
                try:
                    stop = changes.index(False,start+1) - 1
                except ValueError:
                    stop = len(changes)
                while stop - start > 127:
                    output_data.append(255)
                    nextstart = start + 127
                    output_data.extend(array_data[start:nextstart])
                    start = nextstart
                if start < stop:
                    output_data.append(stop - start + 128)
                    output_data.extend(array_data[start:stop])
                start = stop
                continue
            value = array_data[start]
            while stop - start > 127:
                output_data.extend((127,value))
                start += 127
            if start < stop:
                output_data.extend((stop - start,value))
            start = stop
        output_data.extend((0x00,ord('\n')))
        return bytes(output_data)
                
                
            
    #@pytest.mark.skip(reason="just exclude for testing why test damn")
    def test_decoder_import(self):
        import sys
        import inspect
        
        self.assertTrue(inspect.isbuiltin(data_stream.byterle_decoder))
        self.assertIs(data_stream,sys.modules['ahds.data_stream'])

        if sys.version_info[0] >= 3:
            decoder_path = os.path.join(os.path.dirname(data_stream.__spec__.origin),'decoders')
        else:
            decoder_path = os.path.join(os.path.dirname(data_stream.__file__),'decoders')
        backup_decoders_module = dict()
        backup_data_stream_decoder = data_stream.byterle_decoder
        for name,module in sys.modules.items():
            if sys.version_info[0] >= 3:
                spec = getattr(module,'__spec__',None)
                if spec is None or not spec.has_location or not spec.origin.startswith(decoder_path):
                    continue
            elif not getattr(module,'__file__','').startswith(decoder_path):
                continue
            backup_decoders_module[name] = module
            if sys.version_info[0] >= 3:
                sys.modules[name] = None
            else:
                fake_module = sys.modules[name] = imp.new_module(name)
                fake_module.__file__ = './fake_decoders.py'

        self.assertTrue(len(backup_decoders_module) > 0)
        
        if sys.version_info[0] >= 3:
            data_stream_fallback_spec = importlib.util.find_spec('ahds.data_stream')
            data_stream_fallback_module = importlib.util.module_from_spec(data_stream_fallback_spec)
            data_stream_fallback_spec.loader.exec_module(data_stream_fallback_module)
            byterle_decoder = data_stream_fallback_module.byterle_decoder
        else:
            ahds_data_stream_backup = sys.modules['ahds.data_stream']
            sys.modules.pop('ahds.data_stream')
            data_stream_fallback_spec = imp.find_module('data_stream',sys.modules['ahds'].__path__)
            data_stream_fallback_module = imp.load_module('ahds.data_stream',*data_stream_fallback_spec)
            data_stream_fallback_spec[0].close()
            byterle_decoder = data_stream_fallback_module.byterle_decoder
            sys.modules['ahds.data_stream'] = ahds_data_stream_backup
        for name,module in backup_decoders_module.items():
            sys.modules[name] = module
        
        self.assertIs(data_stream,sys.modules['ahds.data_stream'])
        self.assertIs(sys.modules['ahds.data_stream'].byterle_decoder,backup_data_stream_decoder)
        self.assertIs(data_stream.AmiraSpreadSheet,sys.modules['ahds.data_stream'].AmiraSpreadSheet)

        #######################################################################################
        ## !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!         NOTE         !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
        ## !! above faking of import failure in 'ahds.data_stream' to fallback to
        ## !! pure python implementation of byterle_decoder replaces the DispatchFilter for
        ## !! 'HxSpreadSheet' 'ContentType' files with a new incompatible version.
        ## !! must be reset here to version from initial import otherwise following tests will
        ## !! fail
        ## !!
        ## !! Remove not before HxSpreadSheet related classes and items have been moved to
        ## !! dedicated HxSpreadSheet ContentType module and thus above error faking does not
        ## !! trigger update
        ## !!
        set_content_type_filter('HxSpreadSheet',data_stream.AmiraSpreadSheetCollector)

        self.assertEqual(byterle_decoder.__module__,'ahds.data_stream')
        self.assertEqual(data_stream.byterle_decoder.__module__,'ahds.decoders')
        # these seem to always be bytes so no type introspection
        labels = self.af_am.Lattice.Labels
        if isinstance(labels.shape, numpy.ndarray):
            new_shape = labels.shape.tolist() + [labels.dimension]
        else:
            new_shape = [labels.shape] if not isinstance(labels.shape,(list,tuple)) else list(labels.shape)
        bufsize = numpy.prod(new_shape).tolist()
        with self.assertWarns(UserWarning):
            decoded_bytes = byterle_decoder(
                labels._stream_data,
                bufsize = bufsize
            )
        self.assertIsInstance(decoded_bytes,bytearray,msg="decoded_bytes must be a valid bytearray")
        # just a test to identify whether numpy contains breaking changes?
        linear_labels = numpy.frombuffer(decoded_bytes,count=bufsize,dtype=numpy.uint8)
        self.assertIs(linear_labels.base,decoded_bytes)
        label_data = linear_labels.reshape(*new_shape)
        self.assertIs(label_data.base,linear_labels)
        #print("inbytes",len(labels._stream_data),"outbytes",labels.shape.prod())
        self.assertIsInstance(labels.data.base,numpy.ndarray)
        self.assertIsInstance(labels.data.base.base,bytearray)
        self.assertTrue(numpy.all(label_data == labels.data))
        label_data = label_data.flatten()
        label_data[128:144] = label_data[-144:-128] = range(1,17)
        encoded_data = TestDataStreams.byterle_encoder(label_data)
        label_data2 = data_stream.byterle_decoder(encoded_data,bufsize=int(labels.shape.prod()))
        self.assertTrue(numpy.all(label_data2 == label_data))
        with self.assertWarns(UserWarning):
            label_data3 = numpy.asarray(
                byterle_decoder(
                    encoded_data,
                    bufsize=int(labels.shape.prod())
                )
            )
            self.assertTrue(numpy.all(label_data3 == label_data))
        with self.assertWarns(UserWarning):
            with self.assertRaises(AHDSStreamError):
                broken_stream = byterle_decoder(encoded_data,bufsize=int(labels.shape.prod())+1)
            

class TestLoadOndemmand(TestDataStreamsBase):
    @classmethod
    def setUpClass(cls,load_streams=IMMEDIATE):
        super(TestLoadOndemmand,cls).setUpClass(load_streams=HEADERONLY)
        cls.af_am_swapped = header.AmiraHeader(os.path.join(TEST_DATA_PATH, 'test_swapped_streams.am'))
        cls.af_am_missing = header.AmiraHeader(os.path.join(TEST_DATA_PATH, 'test_missing_stream.am'))
        cls.af_am_vector3 = header.AmiraHeader(os.path.join(TEST_DATA_PATH, 'testvector3c.am'))
        cls.af_am_landmarks = header.AmiraHeader(os.path.join(TEST_DATA_PATH, 'BinaryNativeLandmarkSet.lmb'))
        cls.af_hxsurf_header = header.AmiraHeader(os.path.join(TEST_DATA_PATH, 'test7.surf'),load_streams=HEADERONLY)
        cls.af_hxsurf_ascii = header.AmiraHeader(os.path.join(TEST_DATA_PATH,'full.surf'))

    def test_lost_data(self):
        backup_streamdata = self.af_am.Lattice.Labels._stream_data
        self.af_am.Lattice.Labels._stream_data = b''
        #del self.af_am.Lattice.Labels._data
        with self.assertRaises(AHDSStreamError):
            missing_data = self.af_am.Lattice.Labels.data
        self.af_am.Lattice.Labels._stream_data = backup_streamdata
        with self.assertRaises(AttributeError):
            something = self.af_am.Lattice.Labels.id

    def test_stream_loading(self):
        with self.assertRaises(AHDSStreamError):
            data_stream.load_streams(self.af_am_hxsurf)
        data_stream.load_streams(self.af_hxsurf)
        data_stream.load_streams(self.af_am_swapped)
        probability = self.af_am_swapped.Lattice.Probability.data

        with self.assertRaises(AHDSStreamError):
            self.af_am_hxsurf.Vertices.Vertices._read()
        self.af_am_swapped.Lattice.Probability._read()
        with self.assertRaises(AHDSStreamError):
            self.af_am_missing.Lattice.Probability._read()

        self.assertEqual(
            self.af_am_vector3.Lattice.Data._decode(
                self.af_am_vector3.Lattice.Data._stream_data
            ).shape, (4,6,8,3)
        )
        self.assertEqual(
            self.af_am_landmarks.Markers.Coordinates._decode(
                self.af_am_landmarks.Markers.Coordinates._stream_data
            ).shape, (125,3)
        )
        backup_format = self.af_am_landmarks.Markers.Coordinates.format
        self.af_am_landmarks.Markers.Coordinates.add_attr('format','WWWW')
        with self.assertRaises(AHDSStreamError):
            fail = self.af_am_landmarks.Markers.Coordinates._decode(
                self.af_am_landmarks.Markers.Coordinates._stream_data
            )
        self.af_hxsurf.Vertices.Coordinates._read()
        with self.assertRaises(AHDSStreamError):
            self.af_hxsurf_header.Vertices.Coordinates._read()
        self.assertEqual(
            self.af_hxsurf.Vertices.Coordinates._decode(
                self.af_hxsurf.Vertices.Coordinates._stream_data
            ).shape,
            (78030,3)
        )
        self.assertEqual(
            self.af_hxsurf_ascii.Patches[1].Triangles._decode(
                self.af_hxsurf_ascii.Patches[1].Triangles._stream_data
            ).shape,
            (3,3)
        )


    def test_printing(self):
        self.assertIsNone(re.search(r'.*\+-\s+data:.*',str(self.af_am_hxsurf)))
        backup_streamdata = self.af_am.Lattice.Labels._stream_data
        backup_offset = self.af_am.Lattice.Labels._offset
        self.af_am.Lattice.Labels._offset = None
        del self.af_am.Lattice.Labels._stream_data
        self.assertIsNotNone(re.search(r'.*\+-\s*data:\s*<<not loaded>>.*',str(self.af_am)))
        self.af_am.Lattice.Labels._stream_data = backup_streamdata
        self.af_am.Lattice.Labels._offset = backup_offset
        no_data = ()
        try:
            data_backup = self.af_am.Lattice.Labels._data
        except AttributeError:
            data_backup = no_data
        self.assertIsNotNone(re.search(r'.*\+-\s*data:\s*<<not loaded>>.*',str(self.af_am)))
        if data_backup is not no_data:
            self.af_am.Lattice.Labels._data = data_backup
        else:
            data_backup = self.af_am.Lattice.Labels.data
        self.assertIsNotNone(re.search(r'.*\+-\s*data:.*',str(self.af_am)))
        immediate_load = header.AmiraHeader(os.path.join(TEST_DATA_PATH, 'test8.am'),load_streams=IMMEDIATE)
        self.assertIsNotNone(re.search(r'.*\+-\s*data:.*',str(immediate_load)))
        
        
        
class TestStrangeHxSpreadSheet(Py23FixTestCase):
    @classmethod
    def setUpClass(cls,load_streams=IMMEDIATE):
        cls.spread_sheet = header.AmiraHeader(os.path.join(TEST_DATA_PATH, 'EqualLabeledColumnsSpreadSheet.am'))

    def test_equal_named_column_arrays(self):
        self.assertIsInstance(getattr(self.spread_sheet,'AT',None),data_stream.AmiraSpreadSheet)
        self.assertEqual(len(self.spread_sheet.AT),9)
        self.assertEqual(self.spread_sheet.AT[0].name, 'AT0000')
        self.assertIsInstance(getattr(self.spread_sheet.AT[0],'AT0000',None),data_stream.AmiraMeshDataStream)
        self.assertEqual(self.spread_sheet.AT[0].AT0000.name, 'AT0000')
        self.assertEqual(self.spread_sheet.AT[8].name, 'AT0008')
        self.assertIsInstance(getattr(self.spread_sheet.AT[8],'AT0008',None),data_stream.AmiraMeshDataStream)
        self.assertEqual(self.spread_sheet.AT[8].AT0008.name, 'AT0008')
        
