# -*- coding: utf-8 -*-
"""
core
====

Core functionality for `ahds` package

Contains:

* Python2/3 adapters
* decorator for marking deprecation
* core base classes: `Block` and `ListBlock`

"""
from __future__ import print_function

import functools as ft
import inspect
import sys
import warnings

import numpy as np

# print to stderr
_print = ft.partial(print, file=sys.stderr)

if sys.version_info[0] > 2:
    # All definitions for Python3 and newer which differ from their counterparts in Python2.x
    def _decode_string(data):
        """ decodes binary ASCII string to python3 UTF-8 standard string """
        try:
            return data.decode("ASCII")
        except:
            return data.decode("UTF8")


    # in define xrange alias which has been removed in Python3 as range now is equal to
    xrange = range  # xrange
    # define _dict_iter_values, _dict_iter_items, _dict_iter_keys aliases imported by the
    # other parts for dict.values, dict.items and dict.keys
    _dict_iter_values = dict.values
    _dict_iter_items = dict.items
    _dict_iter_keys = dict.keys
    if sys.version_info[1] >= 7:
        _dict = dict
    else:
        from collections import OrderedDict

        _dict = OrderedDict


    def _qualname(o):
        return o.__qualname__


    _str = str

    # UserList
    from collections import UserList
    _UserList = UserList

else:
    import __builtin__


    # Python2.x definitions
    def _decode_string(data):
        """No decoding in Python2.x"""
        return data


    # try to define xrange alias pointing to the builtin xrange
    try:
        xrange = __builtins__['xrange']
    except AttributeError:
        xrange = getattr(__builtins__, 'xrange')
    # define _dict_iter_values, _dict_iter_items, _dict_iter_keys aliases imported by the
    # other parts for dict.itervalues, dict.iteritems and dict.iterkeys
    _dict_iter_values = dict.itervalues
    _dict_iter_items = dict.iteritems
    _dict_iter_keys = dict.iterkeys
    from collections import OrderedDict

    _dict = OrderedDict

    def _qualname(o):
        return o.__name__

    _str = __builtin__.unicode

    # UserList
    from UserList import UserList
    _UserList = UserList


def deprecated(description):
    """Function/Class/Method decorator for warning about deprecations"""
    def outer_wrapper(o):
        @ft.wraps(o)
        def inner_wrapper(*args, **kwargs):
            if inspect.isfunction(o):
                warnings.warn('function/method {} is deprecated: {}'.format(_qualname(o), description),
                              DeprecationWarning)
            elif inspect.isclass(o):
                warnings.warn('class {} is deprecated: {}'.format(_qualname(o), description), DeprecationWarning)
            return o(*args, **kwargs)

        return inner_wrapper

    return outer_wrapper


@ft.total_ordering
class Block(object):
    """Data content block for atomic entities"""
    __slots__ = ('_name', '_attrs', '_is_parent', '__dict__', '__weakref__')

    def __init__(self, name):
        self._name = name
        self._attrs = _dict()
        self._is_parent = False

    @property
    def name(self):
        return self._name

    def attrs(self):
        return list(self._attrs.keys())

    @property
    def is_parent(self):
        return self._is_parent

    def add_attr(self, attr, value=None, isparent=False):
        """Add an attribute to this block object"""
        try:
            assert hasattr(attr, 'name') or isinstance(attr, str)
        except AssertionError:
            raise ValueError('attr should be str or have .name attribute')
        if hasattr(attr, 'name'):
            value = attr
            attr = attr.name
        elif not isinstance(attr, str):
            raise ValueError("invalid type for attr: {}".format(type(attr)))
        # first check that the attribute does not exist on the class
        if hasattr(self, attr):
            raise ValueError("will not overwrite attribute '{}'".format(attr))
        try:
            assert attr not in self._attrs
        except AssertionError:
            raise ValueError("attribute '{}' already exists".format(attr))

        if isinstance(value, Block):
            self._attrs[attr] = value
            self._is_parent = True
        else:
            self._attrs[attr] = value

    def __setattr__(self, key, value):
        """Guard against unintentional modification of _attrs"""
        if key == '_attrs':  # we can't prevent it but we can control it's type and content
            # value must be a dictionary
            try:
                assert isinstance(value, dict)
            except AssertionError:
                raise ValueError('{} must be a dict'.format(key))
            # value must have strings for keys
            try:
                keys = list(value.keys())
                keys_are_strings = map(lambda x: isinstance(x, str), keys)
                assert all(keys_are_strings)  # or len(keys) == 0
            except AssertionError:
                raise ValueError("all keys of {} must be strings".format(key))
        super(Block, self).__setattr__(key, value)

    # todo: rename to 'rename_attr'
    # todo: change signature to rename(self, name, new_name)
    def move_attr(self, new_name, name):
        """Rename an attribute"""
        try:
            assert new_name not in self._attrs
        except AssertionError:
            raise ValueError("will not overwrite attribute '{}'".format(new_name))
        else:
            try:
                self._attrs[new_name] = self._attrs[name]
                del self._attrs[name]
            except KeyError:
                raise AttributeError('''no attribute '{}' found'''.format(name))

    def rename_attr(self, attr, new_name):
        self.move_attr(new_name, attr)

    def __getattr__(self, name):
        try:
            return self._attrs[name]
        except KeyError:
            raise AttributeError('''attribute {} not found'''.format(name))

    def __str__(self, prefix="", index=None,alt_name=None):
        """Compile the hierarchy of Blocks into a tree

        :param str prefix: prefix to signify depth in the tree
        :param int index: applies for list items [default: None]
        :returns str string: formatted string of attributes
        """
        # the root Block will have an empty prefix
        # but the prefix will be updated calls for __str__ for nested Blocks
        # we use the format() function to pass a format_spec which does alignment
        string = ''
        if index is not None:
            string += "{} {} [is_parent? {:<5}]\n".format(
                format(prefix + "+[{}]-{}".format(index, self.name if alt_name in (self.name,None,'') else alt_name), '<55'),
                format(type(self).__name__, '>50'),
                str(self.is_parent)
            )
        else:
            name = format(prefix + "+-{}".format(self.name if alt_name in (self.name,None,'') else alt_name), '<55')
            if len(name) > 55:
                name = name[:52] + '...'
            string += "{} {} [is_parent? {:<5}]\n".format(
                name,
                format(type(self).__name__, '>50'),
                str(self.is_parent)
            )
        for attr in self._attrs:
            # check if the attribute is Block or non-Block
            if isinstance(self._attrs[attr], Block):
                # if it is a Block then the prefix will change by having extra '| ' before it
                # string += 'something\n'
                string += self._attrs[attr].__str__(prefix=prefix + "|  ",alt_name=attr)
            else:
                # if it is not a Block then we construct the repr. manually
                val = self._attrs[attr]
                # don't print the whole array for large arrays
                if isinstance(val, (np.ndarray,)):
                    # we construct a tuple for the first array element (0,...,0) and the last
                    # one (-1,...,-1); however, we have to do this independent of the dimensions
                    # we use a tuple constructed using shape - 1 in both cases
                    start = tuple([0] * (len(val.shape) - 1))
                    end = tuple([-1] * (len(val.shape) - 1))
                    if start == end:
                        string += prefix + "|  +-{}: {}\n".format(attr, val[start])
                    else:
                        string += prefix + "|  +-{}: {},...,{}\n".format(attr, val[start], val[end])
                else:
                    if isinstance(self._attrs[attr], str):
                        if attr == "@alias" and alt_name == self._attrs[attr]:
                            string += prefix + "|  +-{}: {}\n".format(attr, self.name)
                        elif len(self._attrs[attr]) > 55:
                            string += prefix + "|  +-{}: {}\n".format(attr, self._attrs[attr][:52] + '...')
                        else:
                            string += prefix + "|  +-{}: {}\n".format(attr, self._attrs[attr])
                    else:
                        string += prefix + "|  +-{}: {}\n".format(attr, self._attrs[attr])
        return string

    def __getitem__(self, index):
        try:
            assert isinstance(index, int)
        except AssertionError:
            raise ValueError('index must be an integer or long')
        if self.name == 'Materials':
            for attr in self.attrs():
                block = getattr(self, attr)
                if hasattr(block, 'Id'):
                    if getattr(block, 'Id') == index:
                        return block
                    else:
                        continue
        return

    def __contains__(self, item):
        if item in self._attrs:
            return True
        return False

    def __eq__(self, other):
        try:
            assert isinstance(other, Block)
        except AssertionError:
            raise ValueError('item must be a Block class/subclass')
        if self.name == other.name:
            return True
        return False

    def __le__(self, other):
        try:
            assert isinstance(other, Block)
        except AssertionError:
            raise ValueError('item must be a Block class/subclass')
        if self.name < other.name:
            return True
        return False


class ListBlock(Block):
    """Data content block for sequence entities"""
    __slots__ = ('_list', '_material_dict')

    def __init__(self, *args, **kwargs):
        super(ListBlock, self).__init__(*args, **kwargs)
        self._list = list()  # separate attribute for ease of management
        self._material_dict = dict()  # a dictionary used by Materials to extract material by material name

    def items(self):
        return self._list

    @property
    def ids(self):
        ids = list()
        if self.name == 'Materials':
            # first check non-list items
            for attr in self.attrs():
                _attrval = getattr(self, attr)
                if hasattr(_attrval, 'Id'):
                    ids.append(int(_attrval.Id))
                elif hasattr(_attrval, 'id'):
                    ids.append(int(_attrval.id))
            # then check list items
            for list_item in self:
                if hasattr(list_item, 'Id'):
                    ids.append(int(list_item.Id))
                elif hasattr(list_item, 'id'):
                    ids.append(int(list_item.id))
        return ids

    @property
    def material_dict(self):
        """A convenience dictionary of materials indexed by material name

        If this is not a Materials ListBlock (name = 'Material') then it should return None
        """
        # todo: testcase: name == 'Materials' ? dictionary of material blocks : None
        return self._material_dict

    @material_dict.setter
    def material_dict(self, value):
        """Check that this is a material block"""
        if self.name == "Materials":
            if isinstance(value, dict):
                keys_are_strings = map(lambda k: isinstance(k, str), value.keys())
                values_are_blocks = map(lambda v: isinstance(v, Block), value.values())
                try:
                    assert all(keys_are_strings)
                except AssertionError:
                    raise ValueError("keys for material_dict dictionary must be strings")
                try:
                    assert all(values_are_blocks)
                except AssertionError:
                    raise ValueError("values for material_dict dictionary must be Blocks (or subclasses)")
                # now we can set
                self._material_dict = value
            else:
                raise TypeError("value must be a dict")
        else:
            raise ValueError("the material_dict attribute can only be set for Materials ListBlocks")

    def __setattr__(self, key, value):
        """We do some sanity checks before allowing direct setting"""
        # we only allow modification of _list if it meets some criteria
        if key == '_list':
            # it must be a list
            try:
                assert isinstance(value, list)
            except AssertionError:
                raise ValueError("_list attribute must be a list")
            # make sure it's either empty or has block subclasses
            if len(value) > 0:
                try:
                    assert all(map(lambda x: isinstance(x, Block), value))
                except AssertionError:
                    raise ValueError("list contains non-Block class/subclass")
        super(ListBlock, self).__setattr__(key, value)

    @property
    def is_parent(self):
        """A ListBlock is a parent if it has a Block attribute or if it has list items"""
        # todo: testcase
        if super(ListBlock, self)._is_parent:
            return True
        else:
            if len(self._list) > 0:
                return True
            else:
                return False

    def __str__(self, prefix="", index=None,alt_name=None):
        """Convert the ListBlock into a string

        :param str prefix: prefix to signify depth in the tree
        :param int index: applies for list items [default: None]
        :returns str string: formatted string of attributes
        """
        # first we use the superclass to populate everything else
        string = super(ListBlock, self).__str__(prefix=prefix, index=index,alt_name=alt_name)
        # now we stringify the list-blocks
        for index, block in enumerate(self.items()):
            string += block.__str__(prefix=prefix + "|  ", index=index)
        return string

    def __len__(self):
        return len(self._list)

    def __setitem__(self, key, value):
        try:
            assert isinstance(value, Block)
        except AssertionError:
            raise ValueError('value must be a Block class/subclass')
        try:
            self._list[key] = value
        except IndexError:
            self._list.append(value)
            # raise ValueError("index {} does not exist".format(key))

    def __getitem__(self, item):
        try:
            return self._list[item]
        except KeyError:
            raise IndexError("no item with index '{}'".format(item))

    def __iter__(self):
        return iter(self._list)

    def __contains__(self, item):
        if item in self._list:
            return True
        return False

    def __delitem__(self, key):
        try:
            del self._list[key]
        except KeyError:
            raise IndexError("missing item at index'{}'".format(key))

    # Mutable sequences should provide methods append(), count(), index(), extend(), insert(), pop(), remove(),
    # reverse() and sort(), like Python standard list objects.
    def append(self, item):
        try:
            assert isinstance(item, Block)
        except AssertionError:
            raise ValueError('item must be a Block class/subclass')
        self._list.append(item)

    def count(self, item, *args):
        try:
            assert isinstance(item, Block)
        except AssertionError:
            raise ValueError('item must be a Block class/subclass')
        return self._list.count(item, *args)

    def index(self, item, *args):
        try:
            assert isinstance(item, Block)
        except AssertionError:
            raise ValueError('item must be a Block class/subclass')
        return self._list.index(item, *args)

    def extend(self, item):
        try:
            assert isinstance(item, list)
        except AssertionError:
            raise ValueError('item must be a Block class/subclass')
        self._list.extend(item)

    def insert(self, index, item):
        try:
            assert isinstance(item, Block)
        except AssertionError:
            raise ValueError('item must be a Block class/subclass')
        self._list.insert(index, item)

    def pop(self, *args):
        return self._list.pop(*args)

    def remove(self, item):
        try:
            assert isinstance(item, Block)
        except AssertionError:
            raise ValueError('item must be a Block class/subclass')
        return self._list.remove(item)

    def reverse(self):
        self._list.reverse()

    def sort(self, **kwargs):
        return self._list.sort(**kwargs)
