# -*- coding: utf-8 -*-
from __future__ import print_function

import unittest

from ahds.core import Block, ListBlock


class TestUtils(unittest.TestCase):
    pass


class TestBlock(unittest.TestCase):
    def test_create(self):
        b = Block('block')
        self.assertTrue(b.name, 'block')
        self.assertFalse(b.is_parent)
        with self.assertRaises(AttributeError):
            b.name = 'something else'

    def test_add_attrs(self):
        b = Block('block')
        i = Block('inner-block')
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
        b.Materials.Inside.add_attr('Id', 1)
        outside = Block('Outside')
        b.Materials.add_attr(outside)
        b.Materials.Outside.add_attr('Id', 2)
        seaside = Block('Seaside')
        b.Materials.add_attr(seaside)
        b.Materials.Seaside.add_attr('Id', 3)
        self.assertListEqual(b.Materials.ids, [1, 2, 3])
        self.assertEqual(b.Materials[1], inside)
        self.assertEqual(b.Materials[2], outside)
        self.assertEqual(b.Materials[3], seaside)
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


class TestListBlock(unittest.TestCase):
    def test_create(self):
        l = ListBlock('listblock')
        self.assertTrue(hasattr(l, '_list'))

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


# class TestBlock(unittest.TestCase):
#     def test_test(self):
#         b = Block('block')
#         _b = Block('_block')
#         print(_b)
#         ah = AmiraHeader.from_file(os.path.join(TEST_DATA_PATH, 'BinaryCustomLandmarks.elm'))
#         print(ah)
#     @classmethod
#     def setUpClass(cls):
#         cls.block = Block('block')
#
#     def test_default(self):
#         self.assertEqual(self.__class__.block.name, 'block')
#         self.assertTrue(hasattr(self.__class__.block, 'name'))
#         self.assertTrue(hasattr(self.__class__.block, '__dict__'))
#         self.assertTrue(hasattr(self.__class__.block, '__weakref__'))
#         self.assertTrue(hasattr(self.__class__.block, '_parent'))
#
#     def test_add_attr(self):
#         non-parent attribute
#         self.__class__.block.add_attr('test', 10)
#         self.assertTrue(hasattr(self.__class__.block, 'test'))
#         self.assertEqual(self.__class__.block.test, 10)
#         self.assertEqual(len(self.__class__.block._parent), 0)
#         parent attribute
#         self.__class__.block.add_attr('result', 20, isparent=True)
#         self.assertEqual(len(self.__class__.block._parent), 1)
#

if __name__ == "__main__":
    unittest.main()
