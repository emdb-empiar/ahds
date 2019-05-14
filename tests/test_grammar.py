# -*- coding: utf-8 -*-
from __future__ import print_function

import os
import unittest

from ahds import grammar
from tests import TEST_DATA_PATH


class TestGrammar(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.file_format = grammar.detect_format(os.path.join(TEST_DATA_PATH, 'testscalar.am'))
        cls.header = grammar.get_header(os.path.join(TEST_DATA_PATH, 'testscalar.am'), cls.file_format)
        cls.parsed_header = grammar.parse_header(cls.header)

    def test_detect_format(self):
        self.assertIn(self.file_format, ['AmiraMesh', 'HyperSurface'])

    def test_get_header(self):
        self.assertTrue(len(self.header) > 0)

    def test_parse_header(self):
        self.assertTrue(len(self.parsed_header) > 0)


