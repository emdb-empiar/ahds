# -*- coding: utf-8 -*-
from __future__ import print_function

import os
import sys
import pytest
import unittest
import types
import inspect
import functools as ft
import collections
import copy
import pickle
import numpy as np
import time
import weakref

from . import TEST_DATA_PATH, Py23FixTestCase
from ahds.core import (
    Block, ListBlock,_decode_string,ahds_readonly_descriptor,ahds_parent_descriptor,ahds_member_descriptor,
    BlockMetaClass,_str
)
                
python2_backport_test = pytest.mark.skipif(sys.version_info[0] >= 3, reason="python 2 backport specific fix")

class HasReadOnlySlots(object):
    __slots__ = ('_name','_wow','CCC','all_one_but')

    def __init__(self):
        self._name = 'peopleprox'
        self._wow = 42
        self.CCC = 1==0
        self.all_one_but = 0

@pytest.mark.run_recover
class Test_read_only_descriptor(Py23FixTestCase):
    def test_descriptor(self):
        name_descriptor = ahds_readonly_descriptor(HasReadOnlySlots,'name','_name')
        self.assertTrue(issubclass(name_descriptor.__class__,ahds_readonly_descriptor))
        self.assertIs(name_descriptor.__objclass__,HasReadOnlySlots)
        setattr(HasReadOnlySlots,'name',name_descriptor)
        self.assertIsInstance(name_descriptor.__get__(None,HasReadOnlySlots),ahds_readonly_descriptor)
        self.assertIs(name_descriptor.__get__(None,HasReadOnlySlots),name_descriptor)
        with self.assertRaises(TypeError):
            descriptor = name_descriptor.__get__(None,self.__class__)
        has_read_only_slots = HasReadOnlySlots()
        self.assertEqual(name_descriptor.__get__(has_read_only_slots,HasReadOnlySlots),has_read_only_slots._name)
        with self.assertRaises(TypeError):
            name = name_descriptor.__get__(self,self.__class__)
        with self.assertRaises(AttributeError):
            name_descriptor.__set__(has_read_only_slots,'dent')
        with self.assertRaises(AttributeError):
            name_descriptor.__delete__(has_read_only_slots)
        wow_descriptor = ahds_readonly_descriptor(HasReadOnlySlots,'wow','_wow')
        setattr(HasReadOnlySlots,'wow',wow_descriptor)
        self.assertEqual(getattr(has_read_only_slots,'wow'),has_read_only_slots._wow)
        self.assertIsInstance(getattr(HasReadOnlySlots,'wow'),ahds_readonly_descriptor)
        self.assertIs(getattr(HasReadOnlySlots,'wow'),wow_descriptor)
        self.assertEqual(has_read_only_slots.wow,has_read_only_slots._wow)
        with self.assertRaises(AttributeError):
            has_read_only_slots.wow = 56
        with self.assertRaises(AttributeError):
            del has_read_only_slots.wow
        has_read_only_slots._wow = 56
        self.assertEqual(has_read_only_slots._wow,56)
        self.assertEqual(has_read_only_slots.wow,has_read_only_slots._wow)

class HasParent(object):
    __slots__ = ('name','parent')

    def __init__(self,name):
        self.name = name

@pytest.mark.run_recover
class Test_parent_descriptor(Py23FixTestCase):
    def test_01_descriptor(self):
        public_descriptor,private_descriptor = ahds_parent_descriptor(HasParent)
        self.assertIsInstance(public_descriptor,ahds_parent_descriptor)
        self.assertIsInstance(private_descriptor,ahds_parent_descriptor)
        setattr(HasParent,'parent',public_descriptor)
        setattr(HasParent,'_parent',private_descriptor)
        self.assertTrue(issubclass(private_descriptor.__class__,public_descriptor.__class__))
        self.assertIs(public_descriptor.__objclass__,HasParent)
        self.assertIs(private_descriptor.__objclass__,HasParent)
        self.assertIsInstance(public_descriptor.__get__(None,HasParent),ahds_parent_descriptor)
        self.assertIsInstance(private_descriptor.__get__(None,HasParent),ahds_parent_descriptor)
        with self.assertRaises(TypeError):
            descriptor = public_descriptor.__get__(None,self.__class__)
        with self.assertRaises(TypeError):
            descriptor = private_descriptor.__get__(None,self.__class__)
        has_parent = HasParent('i_parent')
        with self.assertRaises(AttributeError):
            public_descriptor.__set__(has_parent,None)
        with self.assertRaises(AttributeError):
            has_parent.parent = None
        private_descriptor.__set__(has_parent,None)
        self.assertIs(private_descriptor.__get__(has_parent,HasParent),None)
        self.assertEqual(
            public_descriptor.__get__(has_parent,HasParent),
            private_descriptor.__get__(has_parent,HasParent)
        )
        with self.assertRaises(ValueError):
            private_descriptor.__set__(has_parent,self)
        has_parent._parent = None
        self.assertIs(has_parent._parent,None)
        self.assertEqual(has_parent.parent,has_parent._parent)
        with self.assertRaises(AttributeError):
            public_descriptor.__delete__(has_parent)
        with self.assertRaises(AttributeError):
            private_descriptor.__delete__(has_parent)
        with self.assertRaises(AttributeError):
            del has_parent._parent
        with self.assertRaises(AttributeError):
            del has_parent.parent
        
@pytest.mark.run_recover
class TestBlockMetaClass(Py23FixTestCase):
    def test_01_read_only_slot(self):
        with self.assertRaises(TypeError):
            protected_name = BlockMetaClass.readonly_slot('some_mane')
        name_space = dict()
        with self.assertRaises(TypeError):
            protected_name = BlockMetaClass.readonly_slot('some_mane')
        name_space['__protectedslots__'] = []
        with self.assertRaises(TypeError):
            protected_name = BlockMetaClass.readonly_slot('some_mane')
        protected_slots = name_space['__protectedslots__'] = dict()
        protected_slot = '_protected'
        self.assertEqual(BlockMetaClass.readonly_slot(protected_slot,namespace=name_space),protected_slot)
        private_slot = '__private'
        self.assertEqual(BlockMetaClass.readonly_slot(private_slot,namespace=name_space),private_slot)
        public_slot = 'public'  
        protected_handle = '_public'
        self.assertEqual(BlockMetaClass.readonly_slot(public_slot,namespace=name_space),protected_handle)
        self.assertIn(public_slot,protected_slots)
        self.assertEqual(protected_slots[public_slot],{'allowcopy':True,'loadoncopy':False})
        public_name = 'name'
        protected_name = '_name'
        self.assertEqual(BlockMetaClass.readonly_slot(public_name,forceload=True,namespace=name_space),protected_name)
        self.assertIn(public_name,protected_slots)
        self.assertEqual(protected_slots[public_name],{'allowcopy':True,'loadoncopy':True})
        public_stale = 'stale'
        protected_stale = '_stale'
        self.assertEqual(BlockMetaClass.readonly_slot(public_stale,copy=False,forceload=False,namespace=name_space),protected_stale)
        self.assertIn(public_stale,protected_slots)
        self.assertEqual(protected_slots[public_stale],{'allowcopy':False,'loadoncopy':False})
        public_wierd = 'wierd'
        protected_wierd = '_wierd'
        self.assertEqual(BlockMetaClass.readonly_slot(public_wierd,copy=False,forceload=True,namespace=name_space),protected_wierd)
        self.assertIn(public_wierd,protected_slots)
        self.assertEqual(protected_slots[public_wierd],{'allowcopy':False,'loadoncopy':True})
        
        
    def test_02__prepare__(self):
        namespace = BlockMetaClass.__prepare__('SomeBlock',(Block,))
        readonly_func = namespace.get('READONLY',None)
        self.assertIsInstance(readonly_func,ft.partial)
        self.assertEqual(readonly_func.func,BlockMetaClass.readonly_slot)
        self.assertIs(readonly_func.keywords.get('namespace',{}),namespace)
        custom_namespace = dict(self_reference=id(self))
        namespace = BlockMetaClass.__prepare__('SomeBlock',(Block,),namespace=custom_namespace)
        self.assertIs(namespace,custom_namespace)
        self.assertEqual(custom_namespace['self_reference'],id(self))
        readonly_func = namespace.get('READONLY',None)
        self.assertIsInstance(readonly_func,ft.partial)
        self.assertEqual(readonly_func.func,BlockMetaClass.readonly_slot)
        self.assertIs(readonly_func.keywords.get('namespace',{}),custom_namespace)
        namespace,immediate_call = BlockMetaClass.__prepare__('SomeBlock',(Block,),namespace=custom_namespace,__readonly_2_hook__=True)
        self.assertIs(namespace,custom_namespace)
        self.assertEqual(custom_namespace['self_reference'],id(self))
        readonly_func = namespace.get('READONLY',None)
        self.assertIsInstance(readonly_func,ft.partial)
        self.assertIs(immediate_call,readonly_func)
        self.assertEqual(readonly_func.func,BlockMetaClass.readonly_slot)
        self.assertIs(readonly_func.keywords.get('namespace',{}),custom_namespace)
        

    def test_03__new__(self):
        namespace = dict(
        )
        class TestBase(object):
            __slots__ = ()
            def __init__(self,name):
                try:
                    self.name = name
                except AttributeError:
                    self._name = name
        some_block = BlockMetaClass.__new__(BlockMetaClass,'SomeBlock',(TestBase,),namespace)
        self.assertIsInstance(some_block,BlockMetaClass)
        self.assertTrue(issubclass(some_block,TestBase))
        namespace = BlockMetaClass.__prepare__('SomeBlock',(TestBase,))
        some_block = BlockMetaClass.__new__(BlockMetaClass,'SomeBlock',(TestBase,),namespace)
        self.assertIsInstance(some_block,BlockMetaClass)
        self.assertTrue(issubclass(some_block,TestBase))
        self.assertIsNone(getattr(some_block,'READONLY',None))
        namespace = BlockMetaClass.__prepare__('SomeBlock',(TestBase,))
        namespace['__slots__'] = 'string_slot'
        some_block = BlockMetaClass.__new__(BlockMetaClass,'SomeBlock',(TestBase,),namespace)
        self.assertIsInstance(some_block,BlockMetaClass)
        self.assertTrue(issubclass(some_block,TestBase))
        self.assertIsNone(getattr(some_block,'READONLY',None))
        self.assertIsInstance(getattr(some_block,'__slots__',None),tuple)
        self.assertIn('string_slot',getattr(some_block,'__slots__',None))
        self.assertIsInstance(getattr(some_block,'string_slot',None),(types.MemberDescriptorType,types.GetSetDescriptorType))
        namespace = BlockMetaClass.__prepare__('SomeBlock',(TestBase,))
        namespace['__slots__'] = ('string_slot',)
        some_block = BlockMetaClass.__new__(BlockMetaClass,'SomeBlock',(TestBase,),namespace)
        self.assertIsInstance(some_block,BlockMetaClass)
        self.assertTrue(issubclass(some_block,TestBase))
        self.assertIsNone(getattr(some_block,'READONLY',None))
        self.assertIsInstance(getattr(some_block,'__slots__',None),tuple)
        self.assertIn('string_slot',getattr(some_block,'__slots__',None))
        self.assertIsInstance(getattr(some_block,'string_slot',None),(types.MemberDescriptorType,types.GetSetDescriptorType))
        namespace = BlockMetaClass.__prepare__('SomeBlock',(TestBase,))
        namespace['__slots__'] = ('parent','name','__weakref__')
        some_block = BlockMetaClass.__new__(BlockMetaClass,'SomeBlock',(TestBase,),namespace)
        self.assertIsInstance(some_block,BlockMetaClass)
        self.assertTrue(issubclass(some_block,TestBase))
        self.assertIsNone(getattr(some_block,'READONLY',None))
        self.assertIsInstance(getattr(some_block,'__slots__',None),tuple)
        self.assertIn('name',getattr(some_block,'__slots__',None))
        self.assertIsInstance(getattr(some_block,'name',None),(types.MemberDescriptorType,types.GetSetDescriptorType))
        self.assertIn('parent',getattr(some_block,'__slots__',None))
        self.assertIsNotNone(getattr(some_block,'_parent',None))
        self.assertIsInstance(getattr(some_block,'parent',None),ahds_parent_descriptor)
        self.assertIsInstance(getattr(some_block,'_parent',None),ahds_parent_descriptor)
        some_item = some_block('some_item')
        with self.assertRaises(AttributeError):
            some_item.parent = None
        some_item._parent = None
        self.assertIsNone(some_item.parent)
        self.assertIsNone(some_item._parent)
        some_parent = some_block('some_parent')
        with self.assertRaises(AttributeError):
            some_item.parent = some_parent
        with self.assertRaises(AttributeError):
            del some_item.parent
        some_item._parent = some_parent
        self.assertIs(some_item._parent,some_parent)
        self.assertIs(some_item.parent,some_item._parent)
        del some_parent
        some_parent = None
        self.assertIsNone(some_item._parent)
        self.assertIsNone(some_item.parent)
        morenamespace = BlockMetaClass.__prepare__('MoreBlock',(some_block,))
        morenamespace['__slots__'] = ('parent','other')
        with self.assertRaises(TypeError):
            more_block = BlockMetaClass.__new__(BlockMetaClass,'MoreBlock',(some_block,),namespace)
        namespace = BlockMetaClass.__prepare__('some_block',(TestBase,))
        READONLY = namespace['READONLY']
        namespace['__slots__'] = (READONLY('name'),READONLY('data'),'_encoded_data')
        some_block = BlockMetaClass.__new__(BlockMetaClass,'SomeBlock',(TestBase,),namespace)
        self.assertIsInstance(some_block,BlockMetaClass)
        self.assertTrue(issubclass(some_block,TestBase))
        self.assertIsNotNone(getattr(some_block,'name',None))
        self.assertIsInstance(getattr(some_block,'name',None),ahds_readonly_descriptor)
        self.assertIsNotNone(getattr(some_block,'_name',None))
        self.assertIsNotNone(getattr(some_block,'data',None))
        self.assertIsInstance(getattr(some_block,'data',None),ahds_readonly_descriptor)
        self.assertIsNotNone(getattr(some_block,'_data',None))
        some_item = some_block('some_item')
        self.assertEqual(some_item.name,'some_item')
        self.assertEqual(some_item._name,'some_item')
        with self.assertRaises(AttributeError):
            some_item.name = 'any_item'
        some_item._name = 'any_item'
        self.assertEqual(some_item.name,'any_item')
        self.assertEqual(some_item._name,'any_item')
        namespace = BlockMetaClass.__prepare__('some_block',(TestBase,))
        READONLY = namespace['READONLY']
        namespace['__slots__'] = (READONLY('name'),READONLY('data'),'_encoded_data')
        namespace['__protectedslots__'].update({ 'parent':42,'__dict__':{},'__weakref__':'weak' })
        some_block = BlockMetaClass.__new__(BlockMetaClass,'SomeBlock',(TestBase,),namespace)
        self.assertFalse(any(key in {'parent','__dict__','__weakref__'} for key in some_block.__protectedslots__))
        namespace = BlockMetaClass.__prepare__('some_block',(TestBase,))
        READONLY = namespace['READONLY']
        namespace['__slots__'] = (READONLY('name'),READONLY('data'),'_encoded_data')
        namespace['__protectedslots__'].update({ 'sneak':'in'})
        some_block = BlockMetaClass.__new__(BlockMetaClass,'SomeBlock',(TestBase,),namespace)
        self.assertIsNone(getattr(some_block,'sneak',None))

    def test_04_test_BlockMetaClassLink(self):
        if sys.version_info[0] >= 3:
            from ahds.core import populate_namespace

            namespace = dict(hello='world')
            populated = populate_namespace(namespace)
            self.assertIs(populated,namespace)
            self.assertEqual(namespace['hello'],'world')
            self.assertIn('__slots__',populated)
            self.assertIsInstance(populated['__slots__'],tuple)
            self.assertFalse(populated['__slots__'])

        from ahds.core import BlockMetaClassLink
            
        self.assertIsInstance(BlockMetaClassLink,BlockMetaClass)
        self.assertFalse(BlockMetaClassLink.__slots__)

        if sys.version_info[0] < 3:
            link_check = BlockMetaClassLink()
            self.assertEqual(
                link_check.__dir__(),
                dir(BlockMetaClassLink) + list(getattr(link_check,'__dict__',dict()).keys())
            )

@python2_backport_test
@pytest.mark.run_recover
class TestPython2Backport(Py23FixTestCase):
    def test_dict_backport(self):
        from ahds.core import make_work_meta, dict as ahds_core_dict, _native_dict
        self.assertIn(_native_dict.__module__,('__builtin__','builtins'))
        self.assertTrue(make_work_meta.__subclasscheck__(_native_dict))
        self.assertTrue(make_work_meta.__subclasscheck__({}.__class__))
        _dict_native = _native_dict()
        _dict_syntax = {}
        self.assertTrue(make_work_meta.__instancecheck__(_dict_native))
        self.assertTrue(make_work_meta.__instancecheck__(_dict_syntax))
        self.assertTrue(issubclass(ahds_core_dict,_native_dict))
        self.assertTrue(issubclass(_native_dict,ahds_core_dict))
        self.assertTrue(issubclass(dict,ahds_core_dict))
        self.assertTrue(issubclass(ahds_core_dict,{}.__class__))
        self.assertTrue(issubclass({}.__class__,ahds_core_dict))
        _dict_callable = dict()
        self.assertIsInstance(_dict_native,dict)
        self.assertIsInstance(_dict_native,_native_dict)
        self.assertIsInstance(_dict_native,ahds_core_dict)
        self.assertIsInstance(_dict_syntax,dict)
        self.assertIsInstance(_dict_syntax,_native_dict)
        self.assertIsInstance(_dict_callable,ahds_core_dict)
        self.assertIsInstance(_dict_callable,dict)
        self.assertIsInstance(_dict_callable,_native_dict)
        self.assertEqual(dict.listkeys,_native_dict.keys)
        self.assertEqual(dict.listvalues,_native_dict.values)
        self.assertEqual(dict.listitems,_native_dict.items)
        self.assertEqual(dict.keys,_native_dict.viewkeys)
        self.assertEqual(dict.values,_native_dict.viewvalues)
        self.assertEqual(dict.items,_native_dict.viewitems)

    def test_range_literal(self):
        self.assertIsInstance(slow_range(1),list)
        self.assertIs(range,xrange)

    def test_READONLY(self):
        from ahds.core import READONLY as readonly

        self.assertEqual(eval("readonly('hello')"),'hello')
        self.assertEqual(eval("readonly('hello')",{'readonly':readonly}),'hello')
        self.assertEqual(eval("readonly('hello')",{'readonly':readonly,'__module__':'module'}),'hello')
        namespace = {'__module__':'module'}
        self.assertEqual(eval("readonly('hello')",{'readonly':readonly},namespace),'_hello')
        readonly_func = namespace.get('READONLY',None)
        self.assertIsInstance(readonly_func,ft.partial)
        self.assertEqual(readonly_func.func,BlockMetaClass.readonly_slot)
        self.assertIs(readonly_func.keywords.get('namespace',{}),namespace)

        
        

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
        pass
        #from ahds.core import _qualname
        #if sys.version_info[0] > 2:
        #    self.assertTrue(_qualname(TestUtils),TestUtils.__qualname__)
        #else:
        #    self.assertTrue(_qualname(TestUtils),TestUtils.__name__)

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

    def test_str_literal(self):
        _test_txt = _str(u"koa göd koa musi ois z'spät")
        _encoded = _test_txt.encode('utf8')
        self.assertIsInstance(_encoded,bytes)
        self.assertEqual(_encoded,b"koa g\xc3\xb6d koa musi ois z'sp\xc3\xa4t")

class HasMembers(object):
    __slots__ = ('_attrs','__dict__','__weakref__','conflict','_more_conflict')
    __protectedslots__ = {'more_conflict':13}
    def __init__(self):
        self._attrs = dict()
        self.conflict = False
        self._more_conflict = False

class HaveMembers(HasMembers):
    __slots__ = ()

class Test_ahds_member_descriptor(Py23FixTestCase):
    def test_01_cleanup(self):
        class member_descriptor(ahds_member_descriptor):
            __objclass__ = HasMembers
        descriptor_instance = object.__new__(member_descriptor)
        has_members = HasMembers()
        descriptor_instance._alifeinstances = {
            id(has_members):weakref.ref(has_members,lambda ref:descriptor_instance._cleanup(id(has_members),'some_attr'))
        }
        dont_have_members = HasMembers()
        descriptor_instance._cleanup(id(dont_have_members),'some_attr')
        self.assertIn(id(has_members),descriptor_instance._alifeinstances)
        self.assertIsNotNone(descriptor_instance._alifeinstances[id(has_members)]())
        have_members = HasMembers()
        descriptor_instance._alifeinstances[id(have_members)] = weakref.ref(have_members,lambda ref:descriptor_instance._cleanup(id(have_members),'some_attr'))
        descriptor_instance._cleanup(id(has_members),'some_attr')
        self.assertTrue(id(has_members) not in descriptor_instance._alifeinstances)
        self.assertIn(id(have_members),descriptor_instance._alifeinstances)
        self.assertIsNotNone(descriptor_instance._alifeinstances[id(have_members)]())
        class no_objclass(ahds_member_descriptor):
            __objclass__ = None
        strange_descriptor = object.__new__(no_objclass)
        strange_descriptor._alifeinstances = {id(has_members): weakref.ref(has_members,lambda ref:descriptor_instance._cleanup(id(has_members),'some_attr'))}
        strange_descriptor._cleanup(id(has_members),'some_attr')
        self.assertNotIn(id(has_members),strange_descriptor._alifeinstances)
        setattr(HasMembers,'some_attr',descriptor_instance)
        descriptor_instance._cleanup(id(have_members),'some_attr')
        self.assertNotIn(id(have_members),descriptor_instance._alifeinstances)
        self.assertIsNone(getattr(HasMembers,'some_attr',None))

        # test _nocleanup
        descriptor_instance._alifeinstances[id(has_members)]= weakref.ref(has_members,lambda ref:descriptor_instance._cleanup(id(has_members),'some_attr'))
        descriptor_instance._nocleanup(id(has_members),'some_attr')
        self.assertIn(id(has_members),descriptor_instance._alifeinstances)
        self.assertIsNotNone(descriptor_instance._alifeinstances[id(has_members)]())

    def test_02_make_life(self):
        class member_descriptor(ahds_member_descriptor):
            __objclass__ = HasMembers
        descriptor_instance = object.__new__(member_descriptor)
        has_members = HasMembers()
        weak_instance_handle = weakref.ref(has_members,lambda ref:descriptor_instance._cleanup(id(has_members),'some_attr'))
        descriptor_instance._alifeinstances = { id(has_members):weak_instance_handle }
        descriptor_instance._makealife(has_members,'some_attr')
        self.assertEqual(len(descriptor_instance._alifeinstances),1)
        self.assertIn(id(has_members),descriptor_instance._alifeinstances)
        self.assertIs(descriptor_instance._alifeinstances[id(has_members)],weak_instance_handle)
        have_members = HasMembers()
        descriptor_instance._makealife(have_members,'some_attr')
        self.assertIn(id(have_members),descriptor_instance._alifeinstances)
        self.assertIsInstance(descriptor_instance._alifeinstances[id(have_members)],weakref.ref)
        self.assertIsNotNone(descriptor_instance._alifeinstances[id(have_members)]())
        if sys.version_info[0] >= 3:
            self.assertIsInstance(descriptor_instance._alifeinstances[id(have_members)].__callback__,(types.FunctionType,types.MethodType,types.LambdaType,types.BuiltinFunctionType,types.BuiltinMethodType))
        have_members_id = id(have_members)
        #del have_members
        have_members = None
        # required to give python2 and the system time to collect and delete have_members
        time.sleep(0.2)
        self.assertNotIn(have_members_id,descriptor_instance._alifeinstances)

    def test_03__new__(self):
        has_members = HasMembers()
        has_members.some_attr = 42
        with self.assertRaises(AttributeError):
            descriptor_instance = ahds_member_descriptor(has_members,'some_attr')
        delattr(has_members,'some_attr')
        with self.assertRaises(AttributeError):
            descriptor_instance = ahds_member_descriptor(has_members,())
        attrs_getter_backup = getattr(HasMembers,'_attrs')
        setattr(HasMembers,'_attrs',None)
        with self.assertRaises(AttributeError):
            descriptor_instance = ahds_member_descriptor(has_members,'some_attr')
        setattr(HasMembers,'_attrs',attrs_getter_backup)
        descriptor_instance = ahds_member_descriptor(has_members,'some_attr')
        self.assertIsInstance(descriptor_instance,ahds_member_descriptor)
        self.assertIs(descriptor_instance.__objclass__,HasMembers)
        with self.assertRaises(AttributeError):
            descriptor_instance = ahds_member_descriptor(has_members,'renamed_attr',())
        with self.assertRaises(AttributeError):
            descriptor_instance = ahds_member_descriptor(has_members,'renamed_attr','attr_some')
        setattr(HasMembers,'some_attr',42)
        with self.assertRaises(AttributeError):
            descriptor_instance = ahds_member_descriptor(has_members,'renamed_attr','some_attr')
        setattr(HasMembers,'some_attr',descriptor_instance)
        with self.assertRaises(AttributeError):
            descriptor_instance = ahds_member_descriptor(has_members,'renamed_attr','some_attr')
        has_members._attrs['some_attr'] = 42
        renamed_descriptor_instance = ahds_member_descriptor(has_members,'renamed_attr','some_attr')
        self.assertIsNone(getattr(HasMembers,'some_attr',None))
        self.assertFalse(len(descriptor_instance._alifeinstances))
        setattr(HasMembers,'renamed_attr',renamed_descriptor_instance)
        has_members._attrs['renamed_attr'] = 42
        self.assertTrue(ahds_member_descriptor(has_members,None,'renamed_attr'))
        self.assertIsNone(getattr(HasMembers,'renamed_attr',None))
        descriptor_instance = ahds_member_descriptor(has_members,'some_attr')
        has_members._attrs['some_attr'] = 42
        setattr(HasMembers,'some_attr',descriptor_instance)
        renamed_descriptor_instance = ahds_member_descriptor(has_members,'renamed_attr')
        setattr(HasMembers,'renamed_attr',renamed_descriptor_instance)
        has_members._attrs['renamed_attr'] = 56
        self.assertFalse(ahds_member_descriptor(has_members,'renamed_attr','some_attr'))
        has_members._attrs.pop('renamed_attr')
        self.assertTrue(ahds_member_descriptor(has_members,'renamed_attr','some_attr'))


        class conflicting_descriptor(object):
            def __get__(self,instance,owner):
                if not instance:
                    return self
                return 42
            def __set__(self,instance,value):
                return
            def __delete__(self,instance):
                return

            __objclass__ = HaveMembers

        conflict_backup = getattr(HasMembers,'conflict',None)
        setattr(HasMembers,'conflict',conflicting_descriptor())
        with self.assertRaises(RuntimeError):
            descriptor_instance = ahds_member_descriptor(has_members,'conflict')
        setattr(HasMembers,'conflict',conflict_backup)
        with self.assertRaises(AttributeError):
            descriptor_instance = ahds_member_descriptor(has_members,'conflict')
        read_only_descriptor = ahds_readonly_descriptor(HasMembers,'more_conflict','_more_conflict')
        setattr(HasMembers,'more_conflict',read_only_descriptor)
        with self.assertRaises(AttributeError):
            descriptor_instance = ahds_member_descriptor(has_members,'more_conflict')
        existing_descriptor = ahds_member_descriptor(has_members,'exists')
        setattr(HasMembers,'exists',existing_descriptor)
        has_members._attrs['exists'] = 42
        self.assertFalse(ahds_member_descriptor(has_members,'exists'))

    def test_04__get__(self):
        has_members = HasMembers()
        descriptor_instance = ahds_member_descriptor(has_members,'some_attr')
        setattr(HasMembers,'some_attr',descriptor_instance)
        self.assertIs(descriptor_instance.__get__(None,HasMembers),descriptor_instance)
        with self.assertRaises(TypeError):
            descriptor = descriptor_instance.__get__(None,self.__class__)
        has_members._attrs['some_attr'] = 42
        self.assertEqual(descriptor_instance.__get__(has_members,HasMembers),42)
        has_members._attrs.pop('some_attr',None)
        has_members.__dict__['some_attr'] = 42
        self.assertEqual(descriptor_instance.__get__(has_members,HasMembers),42)
        has_members.__dict__.pop('some_attr',None)
        with self.assertRaises(AttributeError):
            no_value = descriptor_instance.__get__(has_members,HasMembers)

    def test_05__set__(self):
        has_members = HasMembers()
        descriptor_instance = ahds_member_descriptor(has_members,'some_attr')
        setattr(HasMembers,'some_attr',descriptor_instance)
        has_members._attrs['some_attr'] = 42
        with self.assertRaises(AttributeError):
            descriptor_instance.__set__(has_members,13)
        has_members._attrs.pop('some_attr')
        descriptor_instance.__set__(has_members,13)
        self.assertEqual(has_members.some_attr,13)

    def test_06__delete__(self):
        has_members = HasMembers()
        descriptor_instance = ahds_member_descriptor(has_members,'some_attr')
        setattr(HasMembers,'some_attr',descriptor_instance)
        has_members._attrs['some_attr'] = 42
        with self.assertRaises(AttributeError):
            descriptor_instance.__delete__(has_members)
        has_members._attrs.pop('some_attr')
        has_members.some_attr = 13
        descriptor_instance.__delete__(has_members)
        self.assertIsNone(getattr(has_members,'some_attr',None))
        with self.assertRaises(AttributeError):
            descriptor_instance.__delete__(has_members)
            
        
        
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
        with self.assertRaises(AttributeError):
            b2.remove_attr(str)
        

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
