# -*- coding: utf-8 -*-
from __future__ import print_function

import os
import sys
import re
import unittest
import random
import ahds

from . import Py23FixTestCase, TEST_DATA_PATH
from ahds.ahds import parse_args, get_debug, get_literal, get_paths, set_file_and_paths, get_amira_file, AmiraFile
from ahds import check_format
from ahds.core import _str
from ahds.grammar import AHDSStreamError


def _parse_with_shlex(cmd):
    import shlex
    import sys
    sys.argv = shlex.split(cmd)
    args = parse_args()
    return args



class HxSurfSegment(object):
    """Generic HxSurface segment class

    The `ahds <http://ahds.readthedocs.io/en/latest/>`_ package provides a better abstraction of this filetype
    """

    def __init__(self, material, vertices, triangles, prune=True):
        """A single segment from an Amira HxSurface file

        Each such segment corresponds to an HxSurface patch. This is a convenience class to present
        key attributes (id, name, colour).

        :param material: an individual Block object with the Material block
        :param dict vertices: a dictionary of vertices indexed by vertex_ids (which appear in the triangles list)
        :param list triangles: a list of 3-lists containing vertex IDs which define each triangle
        :param bool prune: whether or not the prune the vertices for this segment/patch so that we only bear the
        vertices referenced here; default is True
        """
        self._material = material
        # id
        self._segment_id = self._material.Id
        # name
        if self._material.name:
            self._name = self._material.name
        else:
            self._name = None
        # colour
        if self._material.Color:
            self._colour = self._material.Color
        else:
            r, g, b = random.random(), random.random(), random.random()
            self._colour = r, g, b
            print("Warning: random colour ({:.4f}, {:.4f}, {:.4f}) for segment {}".format(r, g, b, self._segment_id),
                  file=sys.stderr)
        # vertices and triangles
        if prune:
            self._vertices = self._prune_vertices(vertices, triangles)
        else:
            self._vertices = vertices
        self._triangles = triangles
        # print(self._triangles[:20], list(map(lambda x: (x, self._vertices[x]), list(self._vertices.keys())[:20])))

    @property
    def id(self):
        """The segment ID"""
        return self._segment_id

    @property
    def name(self):
        """The name of the segment"""
        return self._name

    @property
    def colour(self):
        """The colour of the segment"""
        return self._colour

    @property
    def vertices(self):
        """A dictionary of vertices in this segment indexed by vertex ID"""
        return self._vertices

    @property
    def triangles(self):
        """A list of triangles (lists with 3 vertex IDs) in this segment"""
        return self._triangles

    def _prune_vertices(self, vertices, triangles):
        """Reduce the vertices and triangles to only those required by this segment"""
        # flatten the list of vertex ids in triangles
        unique_vertex_ids = set([vertex for triangle in triangles for vertex in triangle])
        # get only those vertices present in this segments triangles
        unique_vertices = {vertex: vertices[vertex] for vertex in unique_vertex_ids}
        return unique_vertices


def extract_segments(af, *args, **kwargs):
    """Extract patches as segments

    :param af: an `AmiraFile` object
    :return dict segments: a dictionary of segments with keys set to Material Ids (voxel values)
    """
    # make sure it's an AmiraFile object
    try:
        assert isinstance(af, AmiraFile)
    except AssertionError:
        raise TypeError("must be a valid AmiraFile object")
    # make sure it's read otherwise read it
    if not af.meta.streams_loaded:
        print("Data streams not yet loaded. Reading...", file=sys.stderr)
        af.read()
    segments = dict()
    # first we make a dictionary of vertices
    # keys are indices (1-based)
    vertices_list = af.data_streams.Data.Vertices.data
    # a dictionary of all vertices
    vertices_dict = dict(zip(range(1, len(vertices_list) + 1), vertices_list))
    # then we repack the vertices and patches into vertices and triangles (collate triangles from all patches)
    for patch in af.data_streams.Data.Vertices.Patches:
        if patch is None: # first patch is None as AmiraMesh and HyperSurface file indices start with 1
            continue
        material = af.header.Parameters.Materials.material_dict[patch.InnerRegion]
        patch_id = material.Id
        # sanity check
        if patch_id is None:
            raise ValueError('patch ID is None')
        # now collate triangles and vertices
        triangles = patch.Triangles.data
        hxsurfsegment = HxSurfSegment(material, vertices_dict, triangles.tolist(), *args, **kwargs)
        if patch_id not in segments:
            segments[patch_id] = [hxsurfsegment]
        else:
            segments[patch_id] += [hxsurfsegment]
    return segments

class test_init_functions(unittest.TestCase):
    """
    Test for check_format public function
    """
    def test_check_format(self):
        self.assertEqual(check_format(os.path.join(TEST_DATA_PATH, 'testscalar.am')),'AmiraMesh')
        


class TestAmiraFile(unittest.TestCase):
    """Tests for the ahds.AmiraFile class"""

    def test_default(self):
        af = AmiraFile(os.path.join(TEST_DATA_PATH, 'BinaryCustomLandmarks.elm'), load_streams=True)
        print(af)
        print()
        print()
        af = AmiraFile(os.path.join(TEST_DATA_PATH, 'testscalar.am'), load_streams=True)
        print(af)
        print()
        print()
        af = AmiraFile(os.path.join(TEST_DATA_PATH, 'test7.surf'), load_streams=True)
        print(af)

    """
    af = ahds.AmiraFile(fn, *args, **kwargs)
    header = af.header

    # TODO: handle hxsurface from .am files
    if header.designation.content_type == "hxsurface":
        return header, None
    else:
        # read now
        af.read()
        data_streams = af.data_streams

        if len(data_streams) == 1:
            # get the index for the first (and only) data pointer
            index = header.data_pointers.data_pointer_1.data_index
            volume = data_streams[index].to_volume()
            return header, volume
        else:
            # get the first one and warn the user
            print_date("Multiple lattices defined. Is this file formatted properly? Trying to work with the first one...")
            index = header.data_pointers.data_pointer_1.data_index
            volume = data_streams[index].to_volume()
            return header, volume
    """

    def test_amreader_amiramesh(self):
        """Starting point for integrating into sfftk"""
        af = AmiraFile(os.path.join(TEST_DATA_PATH, 'test9.am'), load_streams=False)
        print(af.header)
        self.assertEqual(af.header.data_stream_count, 1)
        if sys.version_info[0] > 2:
            with self.assertRaises(AHDSStreamError):
                af.read()
        else:
            with self.assertRaises(AHDSStreamError):
                af.read()
        print(af.data_streams)

    def test_amreader_hxsurface(self):
        """Test that it correctly handles AmirMesh hxsurf files"""
        af = AmiraFile(os.path.join(TEST_DATA_PATH, 'test8.am'), load_streams=True)
        self.assertEqual(af.header.content_type, "hxsurface")

    def test_amreader_amiramesh_multiple_volumes(self):
        """We assume a segmentation has one volume so..."""
        af = AmiraFile(os.path.join(TEST_DATA_PATH, 'TetraMesh.am'), load_streams=True)
        self.assertTrue(af.header.data_stream_count > 1)
        print(af.data_streams)

    """
    header = ahds.header.AmiraHeader.from_file(fn, *args, **kwargs)
    data_streams = ahds.data_stream.DataStreams(fn, *args, **kwargs)
    segments = dict()
    for patch_name in data_streams['Patches']:
        patch_material = getattr(header.Parameters.Materials, patch_name)
        patch_vertices, patch_triangles = vertices_for_patches(data_streams['Vertices'], data_streams['Patches'][patch_name])
        # we use the material ID as the key because it is a unique reference to the patch
        segments[patch_material.Id] = HxSurfSegment(patch_material, patch_vertices, patch_triangles)
    return header, segments
    """

    def test_surfreader(self):
        """The way sfftk uses ahds"""
        af = AmiraFile(os.path.join(TEST_DATA_PATH, 'test7.surf'))
        print(af.data_streams.Data.Vertices)
        with self.assertRaises(TypeError):
            extract_segments(list())
        segments = extract_segments(af)
        # check the structure of segments
        self.assertIsInstance(segments, dict)
        self.assertIsInstance(list(segments.values())[0], list)
        self.assertIsInstance(list(segments.keys())[0], int)
        self.assertIsInstance(list(segments.values())[0][0], HxSurfSegment)
        # if we have Materials verify that material_dict is not None
        if hasattr(af.header.Parameters, 'Materials'):
            self.assertIsNotNone(af.header.Parameters.Materials.material_dict)
        else:
            self.assertIsNone(af.header.Parameters.Materials.material_dict)

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
        cls.af_scalar_fn = os.path.join(TEST_DATA_PATH,'testscalar.am')

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
        args = _parse_with_shlex("ahds -s -d {}".format(self.af_fn))
        f, p = set_file_and_paths(args)
        af = get_amira_file(f, args)
        self.assertIsInstance(af, ahds.AmiraFile)

    def test_amiraf_file_read(self):
        args = _parse_with_shlex("ahds -s {}".format(self.af_scalar_fn))
        f, p = set_file_and_paths(args)
        af = get_amira_file(f, args)
        self.assertIsInstance(af, ahds.AmiraFile)
        af.read()
        self.assertEqual(repr(af),"AmiraFile('{}', read={})".format(af.filename,True))
        

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
        print("\n-",string,"*",f,"+",p)
        self.assertIsInstance(string, _str)
        am = re.compile(r".*AmiraFile.*", re.S)
        #m = re.compile(r".*meta.*", re.S)
        h = re.compile(r".*header.*", re.S)
        #ds = re.compile(r".*data_streams.*", re.S)
        am_m = am.match(string)
        self.assertIsNotNone(am_m)
        #m_m = m.match(string)
        #self.assertIsNotNone(m_m)
        h_m = h.match(string)
        self.assertIsNotNone(h_m)
        #ds_m = ds.match(string)
        #self.assertIsNotNone(ds_m)


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

