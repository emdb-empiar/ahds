# -*- coding: utf-8 -*-
from __future__ import print_function

import os
import unittest

import numpy

from ahds import data_stream, AmiraFile, header
from tests import TEST_DATA_PATH


class TestDataStreams(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.af_am = AmiraFile(os.path.join(TEST_DATA_PATH, 'test9.am'))
        cls.af_am.read()
        cls.af_am_hxsurf = AmiraFile(os.path.join(TEST_DATA_PATH, 'test8.am'))
        cls.af_am_hxsurf.read()
        cls.af_hxsurf = AmiraFile(os.path.join(TEST_DATA_PATH, 'test7.surf'))
        cls.af_hxsurf.read()

    def test_amirafile(self):
        self.assertIsInstance(self.__class__.af_am.header, header.AmiraHeader)
        self.assertIsInstance(self.__class__.af_am, AmiraFile)
        self.assertIsInstance(self.__class__.af_am_hxsurf, AmiraFile)
        self.assertIsInstance(self.__class__.af_hxsurf, AmiraFile)

    def test_data_stream(self):
        af_am_data_stream = self.__class__.af_am.data_streams[1]
        self.assertIsInstance(af_am_data_stream, data_stream.AmiraMeshDataStream)
        self.assertEqual(len(self.__class__.af_am.data_streams), 1)
        self.assertEqual(len(self.__class__.af_am_hxsurf.data_streams), 3)
        self.assertEqual(len(self.__class__.af_hxsurf.data_streams), 5)
        self.assertIsInstance(self.__class__.af_hxsurf.data_streams['Patches'], data_stream.PatchesDataStream)
        self.assertIsInstance(
            self.__class__.af_hxsurf.data_streams['NBranchingPoints'],
            data_stream.NBranchingPointsDataStream
        )
        self.assertIsInstance(
            self.__class__.af_hxsurf.data_streams['BoundaryCurves'],
            data_stream.BoundaryCurvesDataStream
        )
        self.assertIsInstance(
            self.__class__.af_hxsurf.data_streams['Vertices'],
            data_stream.VerticesDataStream
        )
        self.assertIsInstance(
            self.__class__.af_hxsurf.data_streams['NVerticesOnCurves'],
            data_stream.NVerticesOnCurvesDataStream
        )
        self.assertTrue(len(af_am_data_stream.encoded_data) > 0)
        self.assertTrue(len(af_am_data_stream.decoded_data) > 0)

    def test_images(self):
        imgs = self.__class__.af_am.data_streams[1].to_images()
        self.assertTrue(len(imgs) > 0)

    def test_images_fail(self):
        with self.assertRaises(ValueError):
            self.__class__.af_am_hxsurf.data_streams[1].to_images()

    def test_volume(self):
        vol = self.__class__.af_am.data_streams[1].to_volume()
        self.assertIsInstance(vol, numpy.ndarray)
        x, y, z = vol.shape
        self.assertTrue(x > 0)
        self.assertTrue(y > 0)
        self.assertTrue(z > 0)

    def test_contours(self):
        imgs = self.__class__.af_am.data_streams[1].to_images()
        # get the middle slice of the image set
        contours = imgs[128].as_contours
        self.assertIsInstance(contours, dict)
