# -*- coding: utf-8 -*-
from __future__ import print_function

import os
import unittest

from ahds import grammar
from ahds.tests import TEST_DATA_PATH


class TestGrammar(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.file_format = grammar.detect_format(os.path.join(TEST_DATA_PATH, 'testscalar.am'))
        cls.header = grammar.get_header(os.path.join(TEST_DATA_PATH, 'testscalar.am'))
        cls.parsed_header = grammar.parse_header(cls.header[1] if len(cls.header) > 2 else '')

    def test_detect_format(self):
        self.assertTrue(len(self.file_format)>1)
        self.assertIn(self.file_format[0], ['AmiraMesh', 'HyperSurface'])

    def test_get_header(self):
        self.assertTrue(len(self.header) > 2 and self.header[0] == self.file_format[0] and len(self.header[1]) > 0)

    def test_parse_header(self):
        self.assertTrue(len(self.parsed_header) > 0)


