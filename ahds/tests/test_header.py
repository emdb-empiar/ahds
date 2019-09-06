# -*- coding: utf-8 -*-
from __future__ import print_function

import os
import sys

from ahds import header
from ahds.tests import Py23FixTestCase, TEST_DATA_PATH


class TestHeaderBlock(Py23FixTestCase):
    @classmethod
    def setUpClass(cls):
        cls.header = header.AmiraHeader(os.path.join(TEST_DATA_PATH, 'test12.am'))

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
