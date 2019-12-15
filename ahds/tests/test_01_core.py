# -*- coding: utf-8 -*-
from __future__ import print_function

import os
import sys
import unittest
import types
import inspect
import functools as ft
import collections
import copy
import pickle
import numpy as np
import time

from . import TEST_DATA_PATH, Py23FixTestCase
from ahds import AmiraFile
from ahds.grammar import AHDSStreamError
from ahds.core import Block, ListBlock,_decode_string
import ahds.core as not_ahds_core
import ahds as not_ahds


class TestUtils(Py23FixTestCase):
    def test_decode_string(self):
        self.assertTrue(_decode_string(b"hello_world") == "hello_world")
        utf8_encoded = "nät âuß dèsör wölt echt wüld"
        self.assertTrue(_decode_string(utf8_encoded.encode("utf8")) == utf8_encoded)

    def test__dict_literal(self):
        from ahds.core import _dict
        if sys.version_info[0] == 3:
            if sys.version_info[1] < 7:
                self.assertTrue(issubclass(_dict,collections.OrderedDict))
                true_version = sys.version_info
                monkey = list(sys.version_info)
                monkey[1] = 7
                setattr(sys,'version_info',monkey)
                hide_core = sys.modules['ahds.core']
                del sys.modules['ahds.core']
                from ahds.core import _dict
                self.assertTrue(issubclass(_dict,dict))
                setattr(sys,'version_info',true_version)
                sys.modules['ahds_core'] = hide_core
            else:
                self.assertTrue(issubclass(_dict,dict))
        else:
            self.assertTrue(issubclass(_dict,collections.OrderedDict))

    def test__qualname(self):
        from ahds.core import _qualname
        if sys.version_info[0] > 2:
            self.assertTrue(_qualname(TestUtils),TestUtils.__qualname__)
        else:
            self.assertTrue(_qualname(TestUtils),TestUtils.__name__)

    def test_deprecated(self):
        from ahds.core import deprecated
        @deprecated("this is deprecated")
        def i_am_deprecated():
            pass
        with self.assertWarns(DeprecationWarning):
            i_am_deprecated()
        @deprecated("this class is deprecated")
        class i_am_deprecated_class():
            pass
        with self.assertWarns(DeprecationWarning):
            depri = i_am_deprecated_class()
                
        
        
class TestBlock(Py23FixTestCase):
    def test_01_create_class(self):
        if sys.version_info[0] > 2:
            with self.assertRaises(TypeError):
                class broken_block1(Block):
                    __protectedslots__ = ''
                    __slots__ = (READONLY("_ignore"),)

        class ignored_slot(Block):
            __slots__ = (READONLY("_ignore"),'_someslot')

        self.assertTrue(getattr(ignored_slot,'ignore',None) is None and getattr(ignored_slot,'_ignore',None) is not None)
        class noprotect(Block):
            __slots__ = (READONLY('parent'),)

        class lost_internal(Block):
            __slots__ = (READONLY('lost'),)
            __slots__ = ('lost',)

        
    def test_02_create(self):
        b = Block('block')
        self.assertTrue(b.name, 'block')
        self.assertTrue(inspect.isdatadescriptor(Block.name))
        with self.assertRaises(TypeError):
            name = Block.name.__get__(None,TestBlock)
        with self.assertRaises(AttributeError):
            b.name = 'something else'
        with self.assertRaises(AttributeError):
            del b.name
        self.assertTrue(inspect.isdatadescriptor(Block.parent))
        with self.assertRaises(TypeError):
            parent = Block.parent.__get__(None,TestBlock)
        with self.assertRaises(AttributeError):
            b.parent = 2
        with self.assertRaises(AttributeError):
            del b.parent
        with self.assertRaises(ValueError):
            b._parent = 3
        

    def test_03_add_attrs(self):
        b = Block('block')
        i = Block('inner-block')
        b.add_attr(i)
        b.add_attr('user', 'oranges')
        self.assertTrue(hasattr(b, 'inner-block'))
        self.assertTrue(hasattr(b, 'user'))
        b.add_attr(Block('Materials'))
        inside = Block('Inside')
        b.Materials.add_attr(inside)
        b.Materials.Inside.add_attr('Id', 1)
        self.assertEqual(b.Materials[1], inside)
        with self.assertRaises(IndexError):
            mat = b.Materials['b']
        with self.assertRaises(NotImplementedError):
            mat = b[1]
        outside = Block('Outside')
        b.Materials.add_attr(outside)
        b.Materials.Outside.add_attr('Id', 2)
        self.assertEqual(b.Materials[2], outside)
        seaside = Block('Seaside')
        b.Materials.add_attr(seaside)
        b.Materials.Seaside.add_attr('Id', 3)
        with self.assertRaises(IndexError):
            mat = b.Materials[4]
        self.assertEqual(b.Materials[3], seaside)
        self.assertTrue('Materials' in b)
        user_descriptor = getattr(b.__class__,'user')
        clear_objclass = user_descriptor.__objclass__
        with self.assertRaises(AttributeError):
            user_descriptor.__objclass__ = None
        user_descriptor.__class__.__objclass__ = None
        with self.assertRaises(AttributeError):
            b.add_attr("name","capture")
        with self.assertRaises(ValueError):
            b.add_attr(())
        with self.assertRaises(AttributeError):
            b.add_attr('name')
        class DistractingBlock(Block):
            pass
        user_descriptor.__class__.__objclass__ = DistractingBlock
        with self.assertRaises(TypeError):
            b.add_attr('user',12)
        user_descriptor.__class__.__objclass__ = clear_objclass
        self.assertTrue(inside < outside)
        self.assertFalse(inside < 12)
        i.add_attr(b,isparent=True)
        s=str(b)
        print(dir(inside))
        b.add_attr("ndarray",np.random.rand(70,9,4,3))
        s=str(b)
        

    def test_04_rename_attr(self):
        b = Block('block')
        i = Block('inner-block')
        b.add_attr(i)
        self.assertEqual(getattr(b, 'inner-block'), i)
        b.rename_attr('inner_block', 'inner-block')
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
        with self.assertRaises(AttributeError):
            b.rename_attr((), 'inner-block')
        setattr(Block,'some_other',{})
        with self.assertRaises(AttributeError):
            b.rename_attr('other_some','some_other')
        backup = getattr(Block,'_attrs')
        setattr(Block,'_attrs','')
        with self.assertRaises(AttributeError):
            b.add_attr('fails',12)
        setattr(Block,'_attrs',backup)
        b2 = Block("block2")
        b2.inner_block = 42
        self.assertEqual(b2.inner_block,42)
        with self.assertRaises(AttributeError):
            b.inner_block = 42
        b.add_attr('Materials',i)
        mat = Block('Materials')
        b.add_attr(mat)
        self.assertEqual(b.Materials,mat)
        hiden_parent = Block("hiden_parent")
        b.add_attr("hidden",hiden_parent,isparent=True)
        self.assertTrue(b.parent is hiden_parent)
        self.assertTrue(b.hidden is hiden_parent)

    def test_05_del_attr(self):
        b = Block("block")
        b.add_attr("short_life","deleted")
        b.remove_attr("short_life")
        b2 = Block("block2")
        b.add_attr("do_defend","bäää")
        b2.do_defend = "bäää"
        with self.assertRaises(AttributeError):
            delattr(b,'do_defend')
        delattr(b2,"do_defend")
        with self.assertRaises(AttributeError):
            delattr(b2,"do_defend")

    def test_06_get_set_state(self):
        b = Block("block")
        sb = Block("sub_block")
        sb.add_attr("Answer",42)
        sb.add_attr("Question","7*8 is")
        b.add_attr("Important",sb)
        b.add_attr("Mark","E")
        duplicat = copy.copy(b)
        self.assertEqual(duplicat,b)
        self.assertEqual(duplicat.Important,b.Important)
        self.assertEqual(duplicat.Mark,b.Mark)
        duplicat.remove_attr("Mark")
        duplicat2 = copy.copy(duplicat)
        self.assertEqual(duplicat2,duplicat)
        self.assertEqual(duplicat2.Important,b.Important)
        class StrangeBlock(Block):
            __slots__ = (READONLY('fancy',copy=False),READONLY("more_fancy"))
            def __init__(self,name):
                super(StrangeBlock,self).__init__(name)
                self._fancy = 12
        strange = StrangeBlock("strange")
        strange2 = copy.copy(strange)
        with self.assertRaises(AttributeError):
            a=strange2.fancy
        class WithData(Block):
            __slots__ = (READONLY('data',forceload=True),)
            def __getattr__(self,name):
                if name in {'data'}:
                    self._data = "this is some data"
                    return self._data
                raise AttributeError("'{}' attribute unknown".format(name))
        withdata = WithData("withdata")
        withdata2 = copy.copy(withdata)
        self.assertEqual(withdata2.data,"this is some data")
        broken_state = withdata.__getstate__()
        hide_attrs = broken_state.pop('_attrs')
        with self.assertRaises(pickle.UnpicklingError):
            withdata2.__setstate__(broken_state)
        broken_state['_attrs'] = hide_attrs
        hide_name = broken_state.pop('_name')
        with self.assertRaises(pickle.UnpicklingError):
            withdata2.__setstate__(broken_state)

        

            
        
        
        

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
        with self.assertRaises(TypeError):
            Block.Materials.__get__(None,TestBlock)

    def test_list(self):
        l = ListBlock('listblock')
        l.append(Block('one'))
        l.append(Block('two'))
        l[0] = Block('one')
        l[1] = Block('two')
        l[0].add_attr(Block('inside'))
        l[0].add_attr('value', 10)
        self.assertEqual(len(l), 2)
        l.add_attr('internal', 33)
        l.internal
        self.assertTrue(hasattr(l, 'internal'))
        l.append(Block('together'))
        l[0] = Block('together')
        l.insert(4,Block('further_back'))
        str(l)
        with self.assertRaises(ValueError):
            l[1:5] = (Block('1'),Block('2'),12,Block('3'))
        l[0:5] = (Block('0'),Block('1'),Block('2'),Block('3'),Block('4'))
        self.assertTrue(all(b.name == str(index) for index,b in enumerate(l)))
        self.assertTrue(all(b.name == str(4-index) for index,b in enumerate(reversed(l))))
        with self.assertRaises(ValueError):
            l.extend((Block('1'),Block('2'),12,Block('3')))

    def test_parentage(self):
        l = ListBlock('A new listblock')
        self.assertFalse(l.parent)
        l.add_attr('volex', 'Lufthansa')
        self.assertFalse(l.parent)  # is only a parent if the list is populated or if it has subblocks
        l.add_attr(Block('inner_block'))
        self.assertTrue(l is l.inner_block.parent)  # is a parent because the super class is a parent
        k = ListBlock('The other shoe')
        self.assertFalse(k.parent)


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
        with self.assertWarns(DeprecationWarning):
            self.assertEqual(items,l.items)
        l.reverse()
        ritems = list(l)
        self.assertListEqual(items[::-1], ritems)
        # sort
        l.insert(0, Block('zarathusa'))
        self.assertFalse(l[0] < l[1])
        l.sort()
        self.assertTrue(l[0] < l[1])
        l.add_attr(l[0])
        self.assertTrue(block in l)
        with self.assertRaises(ValueError):
            numonestrings = l.count('1')
        with self.assertRaises(ValueError):
            itemindex = l.index('1')
        with self.assertRaises(ValueError):
            l.insert(12,'not block')
        with self.assertRaises(ValueError):
            l.remove('not block')
        

    # def test_insert_listblock(self):
    #     pass


class BlockSubclass(Block):
    """Subclass for test"""
    orange = 'pink'

    __slots__ = ("not_protected")

    def __init__(self, *args, **kwargs):
        super(BlockSubclass, self).__init__(*args, **kwargs)
        self.init_prop = 'init_prop'
        self.not_protected = 42
        

    @property
    def prop(self):
        return 'prop'


class ListBlockSubclass(ListBlock):
    """Subclass for test"""

    def __init__(self, *args, **kwargs):
        super(ListBlockSubclass, self).__init__(*args, **kwargs)

    def __str__(self, prefix="", index=None):
        return super(ListBlockSubclass, self).__str__(prefix=prefix, index=index)


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
        with self.assertRaises(AttributeError):
            b.add_attr('prop', None)
        with self.assertRaises(AttributeError):
            b.add_attr('init_prop')
        with self.assertRaises(AttributeError):
            b.add_attr('orange')
        b_copy = copy.copy(b)
        self.assertEqual(b_copy.not_protected,b.not_protected)

    def test_listblock(self):
        """Test that we cannot interfere with _list attribute"""
        l = ListBlockSubclass('l')
        _list = "a new list with spaces".split(' ')
        l._list = list(map(lambda x: Block(x), _list))
        self.assertEqual(len(l), len(_list))
        # test we can set an empty list
        l._list = []
        self.assertEqual(len(l), 0)



if __name__ == "__main__":
    unittest.main()
