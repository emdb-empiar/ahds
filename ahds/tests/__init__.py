# -*- coding: utf-8 -*-
from __future__ import print_function

import os
import sys
from unittest import TestCase

TEST_DATA_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data')


class Py23FixTestCase(TestCase):
    """Mixin to fix method changes in TestCase class"""

    def __init__(self, *args, **kwargs):
        if sys.version_info[0] > 2:
            pass
        else:
            # new names for assert methods
            self.assertCountEqual = self.assertItemsEqual
        super(Py23FixTestCase, self).__init__(*args, **kwargs)
