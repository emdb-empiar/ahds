# -*- coding: utf-8 -*-
from __future__ import print_function

import os
import unittest

import numpy

import ahds
from ahds import data_stream, AmiraFile, header
from ahds.tests import TEST_DATA_PATH


class TestDataStreams(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.af_am = AmiraFile(os.path.join(TEST_DATA_PATH, 'test9.am'))
        cls.af_am_hxsurf = AmiraFile(os.path.join(TEST_DATA_PATH, 'test8.am'))
        cls.af_hxsurf = AmiraFile(os.path.join(TEST_DATA_PATH, 'test7.surf'))

    def test_amirafile(self):
        self.assertIsInstance(self.af_am.header, header.AmiraHeader)
        self.assertIsInstance(self.af_am, AmiraFile)
        self.assertIsInstance(self.af_am_hxsurf, AmiraFile)
        self.assertIsInstance(self.af_hxsurf, AmiraFile)

    def test_data_stream(self):
        # af_am_data_stream = self.af_am.data_streams[1]
        # test9.am
        self.assertIsInstance(self.af_am.data_streams, ahds.Block)
        self.assertEqual(self.af_am.header.data_stream_count, 1)
        self.assertEqual(self.af_am.data_streams.name, 'data_streams')
        self.assertEqual(self.af_am.data_streams.Labels.name, 'Labels')

        # test8.am
        self.assertIsInstance(self.af_am_hxsurf.data_streams, ahds.Block)
        self.assertEqual(self.af_am_hxsurf.header.data_stream_count, 3)
        self.assertEqual(self.af_am_hxsurf.data_streams.name, 'data_streams')
        self.assertEqual(self.af_am_hxsurf.data_streams.Vertices.name, 'Vertices')
        self.assertEqual(self.af_am_hxsurf.data_streams.Triangles.name, 'Triangles')
        self.assertEqual(getattr(self.af_am_hxsurf.data_streams, "Patches-0").name, "Patches-0")

        # test7.surf
        self.assertIsInstance(self.af_hxsurf.data_streams, ahds.Block)
        self.assertEqual(self.af_hxsurf.header.data_stream_count, 1)
        self.assertEqual(self.af_hxsurf.data_streams.name, 'data_streams')
        self.assertEqual(self.af_hxsurf.data_streams.Data.name, 'Data')


        # self.assertIsInstance(af_am_data_stream, data_stream.AmiraMeshDataStream)
        # self.assertEqual(len(self.af_am.data_streams), 1)
        # self.assertEqual(len(self.af_am_hxsurf.data_streams), 3)
        # self.assertEqual(len(self.af_hxsurf.data_streams), 5)
        # self.assertIsInstance(self.af_hxsurf.data_streams['Patches'], data_stream.PatchesDataStream)

        # self.assertTrue(len(af_am_data_stream.encoded_data) > 0)
        # self.assertTrue(len(af_am_data_stream.decoded_data) > 0)

    # def test_images(self):
    #     imgs = self.af_am.data_streams[1].to_images()
    #     self.assertTrue(len(imgs) > 0)
    #
    # def test_images_fail(self):
    #     with self.assertRaises(ValueError):
    #         self.af_am_hxsurf.data_streams[1].to_images()

    # def test_volume(self):
    #     vol = self.af_am.data_streams[1].to_volume()
    #     self.assertIsInstance(vol, numpy.ndarray)
    #     x, y, z = vol.shape
    #     self.assertTrue(x > 0)
    #     self.assertTrue(y > 0)
    #     self.assertTrue(z > 0)

    # def test_contours(self):
    #     imgs = self.af_am.data_streams[1].to_images()
    #     # get the middle slice of the image set
    #     contours = imgs[128].as_contours
    #     self.assertIsInstance(contours, dict)
