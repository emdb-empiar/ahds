# -*- coding: utf-8 -*-
from __future__ import print_function

import os
import random
import sys
import unittest

from . import TEST_DATA_PATH, Py23FixTestCase
from .. import AmiraFile
from ..core import Block, ListBlock, _print


# class TestUtils(unittest.TestCase):
#     pass


class TestBlock(Py23FixTestCase):
    def test_create(self):
        b = Block('block')
        self.assertTrue(b.name, 'block')
        self.assertFalse(b.is_parent)
        with self.assertRaises(AttributeError):
            b.name = 'something else'

    def test_add_attrs(self):
        b = Block('block')
        i = Block('inner-block')
        print(dir(b))
        print(dir(i))
        b.add_attr(i)
        b.add_attr('user', 'oranges')
        self.assertTrue(b.is_parent)
        self.assertFalse(i.is_parent)
        self.assertListEqual(b.attrs(), ['inner-block', 'user'])
        self.assertTrue(hasattr(b, 'inner-block'))
        self.assertTrue(hasattr(b, 'user'))
        with self.assertRaises(ValueError):
            b.add_attr(i)
        b.add_attr(Block('Materials'))
        inside = Block('Inside')
        b.Materials.add_attr(inside)
        # b.Materials.Inside.add_attr('Id', 1)
        outside = Block('Outside')
        b.Materials.add_attr(outside)
        # b.Materials.Outside.add_attr('Id', 2)
        seaside = Block('Seaside')
        b.Materials.add_attr(seaside)
        # b.Materials.Seaside.add_attr('Id', 3)
        # self.assertCountEqual(b.Materials.ids, [1, 2, 3])
        # self.assertEqual(b.Materials[1], inside)
        # self.assertEqual(b.Materials[2], outside)
        # self.assertEqual(b.Materials[3], seaside)
        self.assertTrue('Materials' in b)

    def test_rename_attr(self):
        b = Block('block')
        i = Block('inner-block')
        b.add_attr(i)
        self.assertEqual(getattr(b, 'inner-block'), i)
        b.rename_attr('inner-block', 'inner_block')
        self.assertEqual(b.inner_block, i)
        self.assertFalse(hasattr(b, 'inner-block'))
        # now retry to see if we can overwrite
        b = Block('block')
        b.add_attr(Block('inner-block'))
        b.add_attr(Block('inner_block'))
        with self.assertRaises(ValueError):
            b.rename_attr('inner-block', 'inner_block')
        with self.assertRaises(AttributeError):
            b.rename_attr('_inner-block', 'a')


class TestListBlock(Py23FixTestCase):
    def test_create(self):
        l = ListBlock('listblock')
        self.assertTrue(hasattr(l, '_list'))

    def test_add_attr(self):
        b = Block('block')
        b.add_attr(ListBlock('Materials'))
        inside = Block('Inside')
        b.Materials.append(inside)
        # b.Materials.add_attr(inside)
        b.Materials[0].add_attr('Id', 1)
        outside = Block('Outside')
        b.Materials.append(outside)
        b.Materials[1].add_attr('Id', 2)
        seaside = Block('Seaside')
        seaside.add_attr('Id', 3)
        b.Materials.append(seaside)
        self.assertCountEqual(b.Materials.ids, [1, 2, 3])
        self.assertEqual(b.Materials[0], inside)
        self.assertEqual(b.Materials[1], outside)
        self.assertEqual(b.Materials[2], seaside)
        self.assertTrue('Materials' in b)

    def test_list(self):
        l = ListBlock('listblock')
        l.append(Block('one'))
        l.append(Block('two'))
        # l[0] = Block('one')
        # l[1] = Block('two')
        l[0].add_attr(Block('inside'))
        l[0].add_attr('value', 10)
        self.assertEqual(len(l), 2)
        l.add_attr('internal', 33)
        l.internal
        self.assertTrue(hasattr(l, 'internal'))

    def test_parentage(self):
        l = ListBlock('A new listblock')
        self.assertFalse(l.is_parent)
        l.add_attr('volex', 'Lufthansa')
        self.assertFalse(l.is_parent)  # is only a parent if the list is populated or if it has subblocks
        l.add_attr(Block('inner-block'))
        self.assertTrue(l.is_parent)  # is a parent because the super class is a parent
        k = ListBlock('The other shoe')
        self.assertFalse(k.is_parent)
        k.append(Block('together'))
        # k[0] = Block('together')
        self.assertTrue(k.is_parent)

    def test_errors(self):
        l = ListBlock('test')
        # try to add a non-block as a list
        with self.assertRaises(ValueError):
            l[0] = 'yes'
        # try to get a non-existent value from the list
        with self.assertRaises(IndexError):
            l[1]
        # try to delete non-existent
        with self.assertRaises(IndexError):
            del l[1]

    def test_list_methods(self):
        """Mutable sequences should provide methods append(), count(), index(), extend(), insert(), pop(), remove(), reverse() and sort(), like Python standard list objects."""
        # append
        l = ListBlock('listblock')
        block = Block('nothing')
        l.append(block)
        self.assertEqual(len(l), 1)
        # fails for non-block
        with self.assertRaises(ValueError):
            l.append(1)
        # count
        l.append(block)
        self.assertEqual(l.count(block), 2)
        # index
        self.assertEqual(l.index(block), 0)
        # extend
        l.extend([Block('new-item')])
        self.assertEqual(len(l), 3)
        # insert
        l.insert(1, Block('inserted'))
        self.assertEqual(l[1].name, 'inserted')
        # pop
        l.pop()
        self.assertEqual(len(l), 3)
        # remove
        l.remove(block)
        self.assertEqual(l.count(block), 1)
        self.assertEqual(len(l), 2)
        # reverse
        l.append(Block('true'))
        l.append(Block('false'))
        items = list(l)
        l.reverse()
        ritems = list(l)
        self.assertListEqual(items[::-1], ritems)
        # sort
        l.insert(0, Block('zarathusa'))
        self.assertFalse(l[0] < l[1])
        l.sort()
        self.assertTrue(l[0] < l[1])

    # def test_insert_listblock(self):
    #     pass


class BlockSubclass(Block):
    """Subclass for test"""
    orange = 'pink'

    def __init__(self, *args, **kwargs):
        super(BlockSubclass, self).__init__(*args, **kwargs)
        self.init_prop = 'init_prop'

    @property
    def prop(self):
        return 'prop'


class ListBlockSubclass(ListBlock):
    """Subclass for test"""

    def __init__(self, *args, **kwargs):
        super(ListBlockSubclass, self).__init__(*args, **kwargs)

    def __str__(self, prefix="", index=None):
        return super(ListBlockSubclass, self).__str__(prefix=prefix, index=index)


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


class TestBlockSubclass(unittest.TestCase):
    def test_block(self):
        """Test for attribute conflicts

        - properties
        - class attributes
        - instance attributes
        - custom attributes (retrieved using __getattr__)
        """
        b = BlockSubclass('b')
        b.add_attr('nothing', 0)
        self.assertTrue(hasattr(b, 'prop'))
        self.assertTrue(hasattr(b, 'init_prop'))
        self.assertTrue(hasattr(b, 'nothing'))
        self.assertTrue(hasattr(b.__class__, 'orange'))
        self.assertTrue(hasattr(b, 'orange'))
        with self.assertRaises(ValueError):
            b.add_attr('prop', None)
        with self.assertRaises(ValueError):
            b.add_attr('init_prop')
        with self.assertRaises(ValueError):
            b.add_attr('orange')
        # all other attributes are not affected
        with self.assertRaises(ValueError):
            b._attrs = 'attrs'
        with self.assertRaises(ValueError):
            b._attrs = list()
        # we can set an empty dictionary though
        b._attrs = dict()
        self.assertEqual(len(b._attrs), 0)
        # we can set a dictionary with string keys and anything as values
        _dict = {
            'a': 1,
            'very': 2,
            'big': Block('blocker'),
            'orangutang': 'that is what we hoped for'
        }
        b._attrs = _dict
        print(b)
        self.assertEqual(b._attrs, _dict)
        # check that we catch wrong dicts
        _bad_dict = {
            1: 1,
            2: 2,
            'big': Block('blocker'),
            'orangutang': 'that is what we hoped for'
        }
        with self.assertRaises(ValueError):
            b._attrs = _bad_dict

    def test_listblock(self):
        """Test that we cannot interfere with _list attribute"""
        l = ListBlockSubclass('l')
        _list = "a new list with spaces".split(' ')
        with self.assertRaises(ValueError):
            l._list = _list
        l._list = list(map(lambda x: Block(x), _list))
        self.assertEqual(len(l), len(_list))
        # test we can set an empty list
        l._list = []
        self.assertEqual(len(l), 0)


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

    # TODO: handle <hxsurface> from .am files
    if header.designation.extra_format == "<hxsurface>":
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
        # print(af)
        print(af.header)
        # print(af.data_streams)
        self.assertEqual(af.header.data_stream_count, 1)
        # print(data_streams.Lattice.data.shape)
        af.read()
        print(af.data_streams)
        # print(dir(af))
        # print(af.attrs())
        # print(af.data_streams.attrs())
        data = getattr(af.data_streams, af.data_streams.attrs()[0], None)
        self.assertIsNotNone(data)
        # print(data.attrs())
        self.assertEqual(data.data_index, 1)
        _print(data.shape, type(data.shape))
        _print(af.header.Lattice.length, type(af.header.Lattice.length))
        self.assertEqual(data.shape, tuple(af.header.Lattice.length.tolist()))
        print(data.shape)

    def test_amreader_hxsurface(self):
        """Test that it correctly handles AmirMesh hxsurf files"""
        af = AmiraFile(os.path.join(TEST_DATA_PATH, 'test8.am'), load_streams=True)
        self.assertEqual(af.header.extra_format, "<hxsurface>")

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
        # af = AmiraFile(os.path.join(TEST_DATA_PATH, 'test7.surf'), load_streams=True)
        # af = AmiraFile(os.path.join(TEST_DATA_PATH, 'BinaryHyperSurface.surf'), load_streams=True)
        # af = AmiraFile('/Users/pkorir/data/segmentations/surf/test8.surf')
        af = AmiraFile(os.path.join(TEST_DATA_PATH, 'test7.surf'))
        # print(af.header.attrs())
        # print(af.header.Parameters.Materials)
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
        # print(segments)
        # print(list(map(lambda s: (s.id, s.name, s.colour, len(s.vertices), len(s.triangles)), segments.values())))
        # print(segments[patch_id].id)
        # print(segments[patch_id].name)
        # print(segments[patch_id].colour)
        # print(len(segments[patch_id].vertices))  # , len(segments[2].vertices))
        # print(len(segments[patch_id].triangles))  # , len(segments[2].triangles))
        # self.assertEqual(segments[patch_id].id, )
        # for patch_id, hxsurfsegments in segments.items():
        #     print("""patch_id: {}""".format(patch_id))
        #     for s in hxsurfsegments:
        #         print(
        #             """Id:{}
        #             \rName:{}
        #             \rColour:{}
        #             \rNo. vertices: {}
        #             \rNo. triangles: {}
        #             """.format(s.id, s.name, s.colour, len(s.vertices), len(s.triangles)))


if __name__ == "__main__":
    unittest.main()
