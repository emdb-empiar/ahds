# -*- coding: utf-8 -*-
# core.py
""" Common data structures and utils used accross all submodules of ahds """

import functools as ft
import inspect
import re
import sys
import warnings

import numpy as np

if sys.version_info[0] >= 3:
    # All defnitions for Python3 and newer which differ from their counterparts in Python2.x

    def _decode_string(data):
        """ decodes binary ASCII string to python3 UTF-8 standard string """
        try:
            return data.decode("ASCII")
        except:
            return data.decode("UTF8")


    # in define xrange alias which has been removed in Python3 as range now is equal to
    # xrange
    xrange = range

    # define _dict_iter_values, _dict_iter_items, _dict_iter_keys aliases imported by the
    # other parts for dict.values, dict.items and dict.keys

    # pylint: disable=E1101
    _dict_iter_values = dict.values

    _dict_iter_items = dict.items

    _dict_iter_keys = dict.keys
    # pylint: enable=E1101

    _dict = dict

else:
    # All defnitions for Python3 and newer which differ from their counterparts in Python2.x

    def _decode_string(data):
        """ in python2.x no decoding is necessary thus just returns data without any change """
        return data


    # try to define xrange alias pointing to the builtin xrange
    try:
        xrange = __builtins__['xrange']
    except:
        xrange = getattr(__builtins__, 'xrange', xrange)

    # define _dict_iter_values, _dict_iter_items, _dict_iter_keys aliases imported by the
    # other parts for dict.itervalues, dict.iteritems and dict.iterkeys
    # pylint: disable=E1101
    _dict_iter_values = dict.itervalues

    _dict_iter_items = dict.iteritems

    _dict_iter_keys = dict.iterkeys
    # pylint: enable=E1101

    from collections import OrderedDict

    _dict = OrderedDict


def deprecated(description=None):
    """ decorator used to mark methods, classes, classmethods and properies as deprecated
        :param str description: the additional information printed along with the DeprecationWarning
    """

    # check if description prarameter is set and whether it is a valid string
    if description is None:
        # no addtional message just print a '!' at the end of the basic DeprecationWarning
        # message
        description = '!'
        _func = None
    elif isinstance(description, (type(b''), type(r''), type(''))):
        # extend the description such that it can be appended to the DeprecationWarning separating
        # it from the latter by ': '
        description = ': {}'.format(description)
        _func = None
    else:
        # description is likely the decorated entity it self gehave like a simple decorator
        _func = description
        description = ''

    def deprecated_decorator(func, msg=None):
        _deprecated_message = '<!?!>'
        _message_filter = '<!?!>'

        @ft.wraps(func)
        def decorated_deprecated(*args, **kwargs):
            # issue DeprecationWarning within the context of the module the decorated entitiy
            # is accessed
            _callstack = inspect.stack()
            # locate caller of deprecated entity. In case this message decorates a mixed_property
            # the mimediate caller following this function on callstack is  the __get__, __set__
            # or __delete__ special methods of the above mixed_property decorator class or any other 
            # element which is defined within this module. Just walk up the call stack until
            # __name__ points to any other module
            _select_level = 1
            _self = _callstack[0]
            _selfframe = _self.frame
            _selffname = (
                _selfframe.f_globals['__name__'][:-3] if _selfframe.f_globals['__name__'][-3:].lower() == '.py' else
                _selfframe.f_globals['__name__']) if '__name__' in _selfframe.f_globals else "<string>"
            _fname = _selffname
            while _select_level < len(_callstack):
                _caller = _callstack[_select_level]
                _callerframe = _caller.frame
                _fname = (_callerframe.f_globals['__name__'][:-3] if _callerframe.f_globals['__name__'][
                                                                     -3:].lower() == '.py' else _callerframe.f_globals[
                    '__name__']) if '__name__' in _callerframe.f_globals else "<string>"
                if _fname != _selffname:
                    break
                _select_level += 1

            # define filter ensuring warning for func is issued only onece per module and file it is called
            warnings.filterwarnings('module', message=_message_filter, category=DeprecationWarning, module=_fname)
            warnings.warn(
                _deprecated_message,
                category=DeprecationWarning,
                stacklevel=_select_level + 1
            )
            return func(*args, **kwargs)

        # if msg is not None:
        #    _deprecated_message = msg.format(func.__qualname__,description)
        #    _message_filter = re.escape(msg.format(func.__qualname__,r''))
        if inspect.isclass(func):
            # issue DeprecationWarning specific to class object and its instances
            _deprecated_message = "Class '{}' is deprecated{}".format(
                getattr(func, '__qualname__', getattr(func, '__name__')), description)
            _message_filter = re.escape(
                r"Class '{}' is deprecated".format(getattr(func, '__qualname__', getattr(func, '__name__'))))
        elif inspect.ismethod(func):
            # func is a staticmethod or a classmethod or a classmember issue related DeprecationWarning
            _deprecated_message = "Method '{}' is deprecated{}".format(
                getattr(func, '__qualname__', getattr(func, '__name__')), description)
            _message_filter = re.escape(
                r"Method '{}' is deprecated".format(getattr(func, '__qualname__', getattr(func, '__name__'))))
        elif inspect.isfunction(func):
            # func is a function issue related DeprecationWarning
            _deprecated_message = "Function '{}' is deprecated{}".format(
                getattr(func, '__qualname__', getattr(func, '__name__')), description)
            _message_filter = re.escape(
                r"Function '{}' is deprecated".format(getattr(func, '__qualname__', getattr(func, '__name__'))))
        else:
            # func is none of the above entities issue a general DeprecationWarning stating that it's use
            # is deprecated
            _deprecated_message = "Use of '{}' is deprecated{}".format(
                getattr(func, '__qualname__', getattr(func, '__name__')), description)
            _message_filter = re.escape(
                r"Use of '{}' is deprecated".format(getattr(func, '__qualname__', getattr(func, '__name__'))))
        # return function wrapping the decorated item
        return decorated_deprecated

    if _func is None:
        # called with description, setter or getter attribute set return decorating method
        return deprecated_decorator
    # called with the item to be decorated as first parameter decorate it
    return deprecated_decorator(_func)


@ft.total_ordering
class Block(object):
    """Generic block"""
    __slots__ = ('_name', '_attrs', '_is_parent', '_parent', '__dict__', '__weakref__')

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

    @property
    def ids(self):
        ids = list()
        if self.name == 'Materials':
            for attr in self.attrs():
                _attrval = getattr(self, attr)
                if hasattr(_attrval, 'Id'):
                    ids.append(int(_attrval.Id))
        return ids

    def add_attr(self, attr, value=None, isparent=False):
        """Add an attribute to this block object"""
        try:
            assert hasattr(attr, 'name') or isinstance(attr, str)
        except AssertionError:
            raise ValueError('attr should be str or have .name attribute')
        try:
            if hasattr(attr, 'name'):
                attr_name = attr.name
            elif isinstance(attr, str):
                attr_name = attr
            assert attr_name not in self._attrs
        except AssertionError:
            raise ValueError("attribute '{}' already exists".format(attr))

        if isinstance(attr, Block):
            self._attrs[attr.name] = attr
            self._is_parent = True
        else:
            self._attrs[attr] = value

    # todo: rename to 'rename_attr'
    # todo: change signature to rename(self, name, new_name)
    def move_attr(self, new_name, name):
        """Rename an attribute"""
        try:
            assert new_name not in self._attrs
        except AssertionError:
            raise ValueError('''will not overwrite attribute \'{}\''''.format(new_name))
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

    def __str__(self, prefix="", index=None):
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
                format(prefix + "+[{}]-{}".format(index, self.name), '<55'),
                format(type(self).__name__, '>50'),
                str(self.is_parent)
            )
        else:
            string += "{} {} [is_parent? {:<5}]\n".format(
                format(prefix + "+-{}".format(self.name), '<55'),
                format(type(self).__name__, '>50'),
                str(self.is_parent)
            )
        for attr in self._attrs:
            # check if the attribute is Block or non-Block
            if isinstance(self._attrs[attr], Block):
                # if it is a Block then the prefix will change by having extra '| ' before it
                # string += 'something\n'
                string += self._attrs[attr].__str__(prefix=prefix + "|  ")
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
                    string += prefix + "|  +-{}: {},...,{}\n".format(attr, val[start], val[end])
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
    """Extension of Block which has an iterable attribute to which Block objects can be added"""
    __slots__ = ('_list',)

    def __init__(self, *args, **kwargs):
        super(ListBlock, self).__init__(*args, **kwargs)
        self._list = list()  # separate attribute for ease of management

    def items(self):
        return self._list

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

    def __str__(self, prefix="", index=None):
        """Convert the ListBlock into a string

        :param str prefix: prefix to signify depth in the tree
        :param int index: applies for list items [default: None]
        :returns str string: formatted string of attributes
        """
        # first we use the superclass to populate everything else
        string = super(ListBlock, self).__str__(prefix=prefix, index=index)
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

    """
    Mutable sequences should provide methods append(), count(), index(), extend(), insert(), pop(), remove(), reverse() and sort(), like Python standard list objects."""

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
