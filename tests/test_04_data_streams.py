# -*- coding: utf-8 -*-
from __future__ import print_function

import sys
import os
import unittest

import numpy

import ahds
from ahds import header, data_stream, IMMEDIATE,HEADERONLY,ONDEMMAND
from . import TEST_DATA_PATH,Py23FixTestCase
from ahds.grammar import AHDSStreamError


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
        self.assertIsInstance(self.af_am.Lattice, ahds.Block)
        self.assertEqual(self.af_am.data_stream_count, 1)
        self.assertEqual(self.af_am.Lattice.Labels.name, 'Labels')

        # test8.am
        self.assertIsInstance(self.af_am_hxsurf, ahds.Block)
        self.assertEqual(self.af_am_hxsurf.data_stream_count, 3)
        self.assertEqual(self.af_am_hxsurf.Vertices.name, 'Vertices')
        self.assertEqual(self.af_am_hxsurf.Triangles.name, 'Triangles')
        self.assertEqual(getattr(self.af_am_hxsurf,'Patches-0').name, "Patches-0")

        # test7.surf
        self.assertIsInstance(self.af_hxsurf, ahds.Block)
        self.assertEqual(self.af_hxsurf.data_stream_count, 5)
        self.assertEqual(self.af_hxsurf.Patches[1].name,'Patch1')

    def test_spread_sheet(self):
        self.assertTrue(isinstance(getattr(self.spread_sheet,'Sheet1',None),ahds.ListBlock))
        self.assertEqual(len(self.spread_sheet.Sheet1),500)
        #self.assertEqual(self.spread_sheet.Sheet1[0].dimension,62)

        self.assertTrue(data_stream.AmiraSpreadSheet.identify_columns({},{},'','') is None)
        self.assertTrue(data_stream.AmiraSpreadSheet.identify_columns({},{},'HxSpreadSheet','HxSpreadSheet') is None)
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
                
                
            
    def test_decoder_import(self):
        import sys
        backup_modules = [
            'decoders','.decoders','ahds.decoders',
            'data_stream','.data_stream','ahds.data_stream',
            'header','.header','ahds.header'
        ]
        backup = {}
        for module in backup_modules:
            backup[module] = sys.modules.pop(module,None)
        trick_import = sys.modules[__name__]
        for decoder in backup_modules[:3]:
            if backup[decoder] is not None:
                sys.modules[decoder] = trick_import
        from ahds.data_stream import  byterle_decoder
        
        for name,module in backup.items():
            if module is not None:
               sys.modules[name] = module
        
        self.assertEqual(byterle_decoder.__module__,'ahds.data_stream')
        # these seem to always be bytes so no type introspection
        labels = self.af_am.Lattice.Labels
        with self.assertWarns(UserWarning):
            if isinstance(labels.shape, numpy.ndarray):
                new_shape = labels.shape.tolist() + [labels.dimension]
            else:
                new_shape = [labels.shape] if not isinstance(labels.shape,(list,tuple)) else list(labels.shape)
            label_data = byterle_decoder(
                labels._stream_data,
                int(labels.shape.prod())
            ).reshape(*new_shape)
        print("inbytes",len(labels._stream_data),"outbytes",labels.shape.prod())
        self.assertTrue(numpy.all(label_data == labels.data))
        label_data = label_data.flatten()
        label_data[128:144] = label_data[-144:-128] = range(1,17)
        encoded_data = TestDataStreams.byterle_encoder(label_data)
        label_data2 = data_stream.byterle_decoder(encoded_data,count=int(labels.shape.prod()))
        self.assertTrue(numpy.all(label_data2 == label_data))
        with self.assertWarns(UserWarning):
            label_data3 = byterle_decoder(
                encoded_data,
                count=int(labels.shape.prod())
            )
            self.assertTrue(numpy.all(label_data3 == label_data))
            

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
        

        
        
