# -*- coding: utf-8 -*-
from __future__ import print_function

import os
import unittest

from ahds import header
from tests import TEST_DATA_PATH


class TestHeaderBlock(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ah = header.AmiraHeader.from_file(os.path.join(TEST_DATA_PATH, 'test12.am'))

    def test_amiraheader(self):
        self.assertIsInstance(self.__class__.ah, header.AmiraHeader)

    def test_add_attr(self):
        self.ah.parameters.add_attr('x', 10)
        self.assertTrue(hasattr(self.ah.parameters, 'x'))
        self.assertEqual(self.ah.parameters.x, 10)

    def test_materials_block(self):
        self.assertItemsEqual(self.ah.parameters.Materials.ids, [3])