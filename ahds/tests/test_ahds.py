# -*- coding: utf-8 -*-
from __future__ import print_function

import os
import re
import sys

import ahds
from . import Py23FixTestCase, TEST_DATA_PATH
from ..ahds import parse_args, get_debug, get_literal, get_paths, set_file_and_paths, get_amira_file
from ..core import _str, _print
import numpy

def _parse_with_shlex(cmd):
    import shlex
    import sys
    sys.argv = shlex.split(cmd)
    args = parse_args()
    return args


class TestArgs(Py23FixTestCase):
    """Tests for the main ahds entry point options"""

    def test_file_only(self):
        """Test command with file only"""
        args = _parse_with_shlex("ahds file.am")
        self.assertFalse(args.debug)
        self.assertEqual(args.file, ['file.am'])
        self.assertFalse(args.literal)
        self.assertFalse(args.load_streams)

    def test_file_with_path(self):
        """Test command with file and path"""
        args = _parse_with_shlex("ahds file.am header.Parameters")
        self.assertFalse(args.debug)
        self.assertEqual(args.file, ['file.am', 'header.Parameters'])
        self.assertFalse(args.literal)
        self.assertFalse(args.load_streams)

    def test_debug(self):
        """Test debug option"""
        args = _parse_with_shlex("ahds -d file.am")
        self.assertTrue(args.debug)

    def test_literal(self):
        """Test literal option"""
        args = _parse_with_shlex("ahds -l file.am")
        self.assertTrue(args.literal)

    def test_load_streams(self):
        """Test load_streams option"""
        args = _parse_with_shlex("ahds -s file.am")
        self.assertTrue(args.load_streams)


class TestMain(Py23FixTestCase):
    """Tests for the main ahds entry point main()"""

    @classmethod
    def setUpClass(cls):
        cls.af_fn = os.path.join(TEST_DATA_PATH, 'test12.am')

    def test_set_file_and_paths(self):
        """Test that we correctly extract file and one or more path"""
        # no paths
        args = _parse_with_shlex("ahds {}".format(self.af_fn))
        f, p = set_file_and_paths(args)
        self.assertEqual(f, self.af_fn)
        self.assertEqual(p, None)
        # one path
        args = _parse_with_shlex("ahds {} path1".format(self.af_fn))
        f, p = set_file_and_paths(args)
        self.assertEqual(f, self.af_fn)
        self.assertEqual(p, ['path1'])
        # two paths
        args = _parse_with_shlex("ahds {} path1 path2".format(self.af_fn))
        f, p = set_file_and_paths(args)
        self.assertEqual(f, self.af_fn)
        self.assertEqual(p, ['path1', 'path2'])
        # three paths
        args = _parse_with_shlex("ahds {} path1 path2 path3".format(self.af_fn))
        f, p = set_file_and_paths(args)
        self.assertEqual(f, self.af_fn)
        self.assertEqual(p, ['path1', 'path2', 'path3'])

    def test_get_amira_file(self):
        """Test that we can get the Amira (R) file"""
        args = _parse_with_shlex("ahds -d {}".format(self.af_fn))
        f, p = set_file_and_paths(args)
        af = get_amira_file(f, args)
        self.assertIsInstance(af, ahds.AmiraFile)

    def test_get_debug(self):
        """Test that we can get debug info"""
        args = _parse_with_shlex("ahds -d {}".format(self.af_fn))
        f, p = set_file_and_paths(args)
        af = get_amira_file(f, args)
        string = get_debug(af, args)
        self.assertIsInstance(string, _str)
        des = re.compile(r".*\'designation\'.*", re.S)
        com = re.compile(r".*\'comment\'.*", re.S)
        par = re.compile(r".*\'parameters\'.*", re.S)
        dat = re.compile(r".*\'data_definitions\'.*", re.S)
        des_m = des.match(string)
        self.assertIsNotNone(des_m)
        com_m = com.match(string)
        self.assertIsNotNone(com_m)
        par_m = par.match(string)
        self.assertIsNotNone(par_m)
        dat_m = dat.match(string)
        self.assertIsNotNone(dat_m)

    def test_get_literal(self):
        """Test that we can get literal header info"""
        args = _parse_with_shlex("ahds -l {}".format(self.af_fn))
        f, p = set_file_and_paths(args)
        af = get_amira_file(f, args)
        string = get_literal(af, args)
        self.assertIsInstance(string, _str)
        am = re.compile(r".*AmiraMesh 3D BINARY.*", re.S)
        cd = re.compile(r".*CreationDate.*", re.S)
        de = re.compile(r".*define Lattice.*", re.S)
        par = re.compile(r".*Parameters.*", re.S)
        mat = re.compile(r".*Materials.*", re.S)
        am_m = am.match(string)
        self.assertIsNotNone(am_m)
        cd_m = cd.match(string)
        self.assertIsNotNone(cd_m)
        de_m = de.match(string)
        self.assertIsNotNone(de_m)
        par_m = par.match(string)
        self.assertIsNotNone(par_m)
        mat_m = mat.match(string)
        self.assertIsNotNone(mat_m)

    def test_get_paths_full(self):
        """Test that we can view the paths full"""
        args = _parse_with_shlex("ahds {}".format(self.af_fn))
        f, p = set_file_and_paths(args)
        af = get_amira_file(f, args)
        string = get_paths(p, af)
        print(string, file=sys.stderr)
        self.assertIsInstance(string, _str)
        am = re.compile(r".*AmiraFile.*", re.S)
        m = re.compile(r".*meta.*", re.S)
        h = re.compile(r".*header.*", re.S)
        ds = re.compile(r".*data_streams.*", re.S)
        am_m = am.match(string)
        self.assertIsNotNone(am_m)
        m_m = m.match(string)
        self.assertIsNotNone(m_m)
        h_m = h.match(string)
        self.assertIsNotNone(h_m)
        ds_m = ds.match(string)
        self.assertIsNotNone(ds_m)

    def test_get_paths_meta(self):
        """Test that we can fiew partial paths"""
        args = _parse_with_shlex("ahds {} meta.streams_loaded".format(self.af_fn))
        f, p = set_file_and_paths(args)
        af = get_amira_file(f, args)
        string = get_paths(p, af)
        print(string, file=sys.stderr)
        self.assertIsInstance(string, _str)
        am = re.compile(r".*AmiraFile.*", re.S)
        m = re.compile(r".*streams_loaded.*", re.S)
        am_m = am.match(string)
        self.assertIsNone(am_m)
        m_m = m.match(string)
        self.assertIsNotNone(m_m)

    def test_get_paths_header(self):
        """Test that we can fiew partial paths"""
        args = _parse_with_shlex("ahds {} header.Parameters.Materials".format(self.af_fn))
        f, p = set_file_and_paths(args)
        af = get_amira_file(f, args)
        string = get_paths(p, af)
        self.assertIsInstance(string, _str)
        am = re.compile(r".*AmiraFile.*", re.S)
        m = re.compile(r".*Inside.*", re.S)
        am_m = am.match(string)
        self.assertIsNone(am_m)
        m_m = m.match(string)
        self.assertIsNotNone(m_m)

    def test_get_paths_data_streams(self):
        """Test that we can fiew partial paths"""
        args = _parse_with_shlex("ahds {} data_streams".format(self.af_fn))
        f, p = set_file_and_paths(args)
        af = get_amira_file(f, args)
        string = get_paths(p, af)
        self.assertIsInstance(string, _str)
        am = re.compile(r".*AmiraFile.*", re.S)
        m = re.compile(r".*data_streams.*", re.S)
        am_m = am.match(string)
        self.assertIsNone(am_m)
        m_m = m.match(string)
        self.assertIsNotNone(m_m)

    # def test_data(self):
    #     """Test that the data is correctly oriented"""
    #     af = ahds.AmiraFile(os.path.join(TEST_DATA_PATH, 'EM04226_2_U19_Cropped_YZ_binned.labels.am'))
        # af = ahds.AmiraFile(os.path.join(TEST_DATA_PATH, 'testscalar.am'))
        # _print(af)
        # _print(af.data_streams.Labels.data.shape)
        # _print(af.header.Lattice.length)
        # import h5py
        # with h5py.File('EM04226_2_U19_Cropped_YZ_binned.labels.h5', 'w') as h:
        #     h['/data'] = af.data_streams.Labels.data
        # import mrcfile
        # _print(af.data_streams.Labels.data.dtype)
        # _print('unique values: ', numpy.unique(af.data_streams.Labels.data.astype(numpy.float32)))
        # with mrcfile.new('EM04226_2_U19_Cropped_YZ_binned.labels.mrc', overwrite=True) as m:
        #     m.set_data(af.data_streams.Labels.data.astype(numpy.float32))
        #     m.voxel_size = (9.0, 9.0, 15.0)
        #     m.update_header_from_data()


