# -*- coding: utf-8 -*-
# core.py
""" Common data structures and utils used accross all submodules of ahds """

import functools as ft
import inspect
import re
import sys
import warnings
import numpy as np

if sys.argv[2] == '0':
    REFACTOR = False
else:
    REFACTOR = True

if sys.version_info[0] > 2:
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
            _deprecated_message = "Class '{}' is deprecated{}".format(func.__qualname__, description)
            _message_filter = re.escape(r"Class '{}' is deprecated".format(func.__qualname__))
        elif inspect.ismethod(func):
            # func is a staticmethod or a classmethod or a classmember issue related DeprecationWarning
            _deprecated_message = "Method '{}' is deprecated{}".format(func.__qualname__, description)
            _message_filter = re.escape(r"Method '{}' is deprecated".format(func.__qualname__))
        elif inspect.isfunction(func):
            # func is a function issue related DeprecationWarning
            _deprecated_message = "Function '{}' is deprecated{}".format(func.__qualname__, description)
            _message_filter = re.escape(r"Function '{}' is deprecated".format(func.__qualname__))
        else:
            # func is none of the above entities issue a general DeprecationWarning stating that it's use
            # is deprecated
            _deprecated_message = "Use of '{}' is deprecated{}".format(func.__qualname__, description)
            _message_filter = re.escape(r"Use of '{}' is deprecated".format(func.__qualname__))
        # return function wrapping the decorated item
        return decorated_deprecated

    if _func is None:
        # called with description, setter or getter attribute set return decorating method
        return deprecated_decorator
    # called with the item to be decorated as first parameter decorate it
    return deprecated_decorator(_func)


if REFACTOR:
    @ft.total_ordering
    class Block(object):
        """Generic block"""
        __slots__ = ('_name', '_attrs', '_is_parent', '_parent')

        def __init__(self, name):
            self._name = name
            self._attrs = dict()
            self._is_parent = False

        @property
        def name(self):
            return self._name

        def attrs(self):
            return list(self._attrs.keys())

        @property
        def is_parent(self):
            return self._is_parent

        def _make_proxy_or_attributeerror(self, name, more_alife=False):
            # just adding to complete the interface
            if name == 'name' or len(self._attrs) > 0 or getattr(self, 'name', None) is not None or more_alife:
                raise AttributeError("-{} instance has not attributes '{}'".format(self.__class__.__name__, name))
            return _AnyBlockProxy(name) if not isinstance(self, _AnyBlockProxy) else self

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
                string += "{} {} object [is_parent? {:<5}]\n".format(
                    format(prefix + "+[{}]-{}".format(index, self.name), '<55'),
                    format(str(type(self)), '>50'),
                    str(self.is_parent)
                )
            else:
                string += "{} {} object [is_parent? {:<5}]\n".format(
                    format(prefix + "+-{}".format(self.name), '<55'),
                    format(str(type(self)), '>50'),
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
                    if isinstance(val, (np.ndarray, )) and len(val.flatten().tolist()) > 4:
                        string += prefix + "|  +-{}: {},...,{}\n".format(attr, val[0], val[-1])
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

        def _make_proxy_or_attributeerror(self, name, more_alife=False):
            return super(ListBlock, self)._make_proxy_or_attributeerror(
                name,
                self._list is None or len(self._list) > 0 or more_alife
            )

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

else:
    class Block(object):
        """Generic block to be loaded with attributes"""
        __slots__ = ("name", "__dict__", "__weakref__", "_parent")

        def __init__(self, name):
            super(Block, self).__setattr__("name", name)
            self._parent = tuple()

        def add_attr(self, name, value, isparent=False):
            """Add an attribute to an ``Block`` object"""
            super(Block, self).__setattr__(name, value)
            if isparent:
                self._parent = self._parent + (value,)

        def move_attr(self, to, name):
            """Rename attribute having name to"""
            _tomove = getattr(self, name, None)
            if _tomove is None or isinstance(_tomove, _AnyBlockProxy):
                raise AttributeError("can not move missing attribute '{}' ".format(name))
            if isinstance(_tomove, Block) and _tomove.name == name:
                _tomove.name = to
            super(Block, self).__setattr__(to, _tomove)
            delattr(self, name)

        def __setattr__(self, name, value):
            """set or update attribute which is not stored within __dict__.

            Attributes stored within dict are dynamic and have to be defined or updated using add_attr.
            any other attributes which are declared by __slots__ structure can be freely accessed unless
            access and modification is restricted by python code conventions like using '_' to define
            protected and private attributes which should only be touched by class and its subclassess.

            In case a public attributed is declared on slots structure the declaring class it self has
            to take care of proper readonly, read/write rules by overloading __setattr__ method.
            """
            if name != "__dict__":

                def gen(obj):
                    def gen0(obj):
                        for _parent in obj.__getattribute__("__class__").__mro__:
                            yield getattr(_parent, "__slots__", None)

                    for _slots in gen0(obj):
                        if _slots is not None and name in _slots:
                            yield True

                for _ in gen(super(Block, self)):
                    super(Block, self).__setattr__(name, value)

                # for _ in (True for _slots in (getattr(_parent, "__slots__", None) for _parent in
                #                               super(Block, self).__getattribute__("__class__").__mro__) if
                #           _slots is not None and name in _slots):
                #     super(Block, self).__setattr__(name, value)
                #     return
                try:
                    super(Block, self).__getattribute__(name)
                except AttributeError:
                    raise AttributeError("New attributes must be added calling add_attr method")
            else:
                raise AttributeError("Attribute '{}' is read only", format(name))

        def __getattribute__(self, name):
            if name in ("attrs", "ids"):
                return super(Block, self).__getattribute__(name)()
            try:
                return super(Block, self).__getattribute__(name)
            except AttributeError:
                return self._make_proxy_or_attributeerror(name)

        @deprecated("user dir(<Block object>) instead")
        def attrs(self):
            return [_attr for _attr in self.__dict__]

        def _make_proxy_or_attributeerror(self, name, more_alife=False):
            if name == 'name' or len(self.__dict__) > 0 or getattr(self, 'name', None) is not None or more_alife:
                raise AttributeError("-{} instance has not attributes '{}'".format(self.__class__.__name__, name))
            return _AnyBlockProxy(name) if not isinstance(self, _AnyBlockProxy) else self

        _recurse = {}

        def __str__(self):
            if self in self.__class__._recurse and isinstance(self.__class__._recurse[self], str):
                # content of block is printed as backreference of child block prepend headerline by string
                # specified by _recurse entry and shorten indent by one level
                indent = " | " * (len(Block._recurse) - 1)
                string = "{} +-{}: {}(<{}.{} object at {}>)\n".format(indent, self.__class__._recurse[self], self.name,
                                                                      self.__module__, self.__class__.__name__,
                                                                      hex(id(self)))
            else:
                # content of block is brinted in its normal hirarchical order
                indent = " | " * len(Block._recurse)
                string = "{} +-{}: (<{}.{} object at {}>)\n".format(indent, self.name, self.__module__,
                                                                    self.__class__.__name__, hex(id(self)))
            # mark block as printed to prevent infinite back reference loops
            self.__class__._recurse[self] = True
            indent += " | "
            for _attr, _attrval in _dict_iter_items(self.__dict__):
                if isinstance(_attrval, Block):
                    if _attrval in self.__class__._recurse or _attrval in self._parent:
                        # print back reference line prefixed by <_attr>: or <_addr>: <_attrval.name> if _attr and _attrvale.name
                        # differt
                        if _attr != _attrval.name:
                            string += "{} +-{}: {}(<{}.{} object at {}>)\n".format(indent, _attr, _attrval.name,
                                                                                   _attrval.__module__,
                                                                                   _attrval.__class__.__name__,
                                                                                   hex(id(_attrval)))
                        else:
                            string += "{} +-{}: (<{}.{} object at {}>)\n".format(indent, _attr, _attrval.__module__,
                                                                                 _attrval.__class__.__name__,
                                                                                 hex(id(_attrval)))
                    else:
                        if _attr != _attrval.name:
                            self.__class__._recurse[_attrval] = _attr
                        string += "{}".format(_attrval)
                else:
                    string += "{} +-{}: {}\n".format(indent, _attr, _attrval)
            del self.__class__._recurse[self]
            return string

        @deprecated("use indexer of Materials node instead to access materials by their id")
        def ids(self):
            """Convenience method to get the ids for Materials present"""
            assert self.name == "Materials"
            ids = list()
            for _attr, _attrval in _dict_iter_items(self.__dict__):
                if hasattr(_attrval, 'Id'):
                    ids.append(int(_attrval.Id))
            return ids

        @deprecated("replace Block by ListBlock for defining indexable list")
        def __getitem__(self, index):
            """Convenience method to get an attribute with 'Id' for a Material"""
            assert self.name == "Materials"
            assert isinstance(index, int)
            for _attrval in (
                    _val
                    for _val in _dict_iter_values(self.__dict__)
                    if hasattr(_val, 'Id') and int(_val.Id) == index
            ):
                return _attrval
            return None

        def __contains__(self, attr):
            """Check if specified attribute is defined on block.

               Compared to hasattr this does not trigger load on demmand mechanism for attributes.
               Exception are attributes defined by HyperSurface files which are designed using the
               load all at once paradigm. In case of HyperSurface files stream_data for intermittend
               blocks and attributes are loaded while searching for quested attribute.
            """
            if attr in self.__dict__:
                # atribute already loaded from header or previous call
                # just report its existance
                return True
            if attr in ("__slots__", "__class__", "__dict__"):
                # attribute
                return True
            for _ in (
                    True
                    for _slots in (
                    getattr(_parent, "__slots__", None)
                    for _parent in super(Block, self).__getattribute__("__class__").__mro__
            )
                    if _slots is not None and attr in _slots
            ):
                # attribute is declared by __slots__ structure it is either present or
                # becomes available as soon as it is first time accessed
                return True
            # final possiblity attribute is defined by HyperMesh file and has to be read
            # once before knowing whether present or not
            try:
                _attrvalue = self.__getattribute__(attr)
            except AttributeError as _inspectondebug:
                return False
            return True


    class ListBlock(Block):
        """Generic block defining List of Blocks. Indexed and named attributes may be mixed allowing to acces
           named attributes in order of their definition or any other indexing rule """
        __slots__ = ("_list",)

        def __init__(self, name):
            super(ListBlock, self).__init__(name)
            self._list = tuple()

        def _make_proxy_or_attributeerror(self, name, more_alife=False):
            return super(ListBlock, self)._make_proxy_or_attributeerror(
                name,
                self._list is None or len(self._list) > 0 or more_alife
            )

        def __setitem__(self, index, value):
            """ set the item with given index to specified value
                :param int index: the index to be set
                :param value: the new value
            """
            if index >= len(self._list):
                self._list = self._list + ((None,) * (index - len(self._list))) + (value,)
                return
            self._list = self._list[:index] + (value,) + self._list[index + 1:]

        def __getitem__(self, index):
            """ return the value indicated by the provided index """
            if index < 0:
                if index < -len(self._list):
                    if len(self._list) < 1 and len(self.__dict__) < 1:
                        return _AnyBlockProxy(str(index)) if not isinstance(self, _AnyBlockProxy) else self
                    raise IndexError("invalid index {}".format(index))
                index = len(self._list) - index
            elif index >= len(self._list):
                if len(self._list) < 1 and len(self.__dict__) < 1:
                    return _AnyBlockProxy(str(index)) if not isinstance(self, _AnyBlockProxy) else self
                raise IndexError("invalid index {}".format(index))
            return self._list[index]

        def __str__(self):
            """ print string representation of ListBlock, if the len(<ListBlock>) > 10 than
                five head elements and five elements from the tail of the list are printed
            """
            string = super(ListBlock, self).__str__()
            indent = " | " * len(Block._recurse)
            if self in Block._recurse or self._list is None:
                return string
            Block._recurse[self] = True
            indent += " | "
            _count = 0
            _idx = -1
            for _count, _entry, _idx in (
                    (_count + 1, _ent, _entid)
                    for _ent, _entid in (
                    (self._list[_entid], _entid)
                    for _entid in xrange(len(self._list))
            )
                    if _ent is not None
            ):
                if isinstance(_entry, Block):
                    string += "{} +-[{}]=({}<{}.{} object at {}>)\n".format(indent, _idx, _entry.name,
                                                                            _entry.__module__,
                                                                            _entry.__class__.__name__, hex(id(_entry)))
                else:
                    string += "{} +-[{}]={}\n".format(indent, _idx, _entry)
                if _count > 4:
                    break
            _back = _idx + 1
            _count = 0
            for _back, _count in (
                    (_bk, _count + 1)
                    for _bk in xrange(len(self._list) - 1, 0, -1)
                    if self._list[_bk] is not None and _bk > _idx
            ):
                if _count > 4:
                    break
            if _back > _idx + 1:
                string += "{} + ...: ... \n"

            for _idx, _entry in (
                    (_entid, _ent)
                    for _entid, _ent in (
                    (_entidx, self._list[_entidx])
                    for _entidx in xrange(_back, len(self._list))
            ) if _ent is not None
            ):
                if isinstance(_entry, Block):
                    _entry = self._list[_idx]
                    string += "{} +-[{}]=({}<{}.{} object at {}>)\n".format(indent, _idx, _entry.name,
                                                                            _entry.__module__,
                                                                            _entry.__class__.__name__, hex(id(_entry)))
                else:
                    string += "{} +-[{}]={}\n".format(indent, _idx, _entry)
            string += "{} +-length: {}\n".format(indent, len(self._list))
            del Block._recurse[self]
            return string

        def __len__(self):
            return len(self._list)

        def __iter__(self):
            """ list iterator """
            for _item in self._list:
                yield _item

        def __contains__(self, item):
            """check whether item is contained in list or if resembling name of attribute is defined on list block"""
            if self._list is not None and item in self._list:
                return True
            return isinstance(item, str) and super(ListBlock, self).__contains__(item)


class _AnyBlockProxy(Block):
    """ dummy block returned by __getattribute__ method of Block in case
        its __dict__ is emtpy and by ListBlock if both __dict__ and _list are emtpy
        it tries to mimic any type the accessing code might expect from attributes
        and items defined by the loaded AmiraMesh and HyperSurface files

        It's main purpos is to keep linters like pylint happy while chekcing code which
        is only excuted when specific amira file could successfully be loaded.
        But linter has no idea which file that could be or what additional attributes
        it might define.
    """

    __slots__ = tuple()

    def __init__(self, name):
        super(_AnyBlockProxy, self).__init__(name)

    def add_attr(self, name, value, isparent=False):
        pass

    def __setattr__(self, name, value):
        pass

    def __getattribute__(self, name):
        return self

    def __getitem__(self, index):
        return self

    def __str__(self):
        return ''

    def __int__(self):
        return 0

    def __float__(self):
        return 0.0

    def __len__(self):
        return 0

    def __index__(self):
        return 0

    def __iter__(self):
        if False:
            yield None

    def __long__(self):
        return 0

    def __complex__(self):
        return complex(0)

    def __oct__(self):
        return '0'

    def __hex__(self):
        return '0'

    def __add__(self, other):
        return other

    def __sub__(self, other):
        return -other

    def __mul__(self, other):
        return 0

    def __floordiv__(self, other):
        return 0

    def __divmod__(self, other):
        return 0

    def __div__(self, other):
        return 0

    def __truediv__(self, other):
        return 0

    def __mod__(self, other):
        return 0

    def __pow__(self, other):
        return 0

    def __lshift__(self, other):
        return 0

    def __rshift__(self, other):
        return 0

    def __and__(self, other):
        return 0

    def __xor__(self, other):
        return other

    def __iadd__(self, other):
        return other

    def __isub__(self, other):
        return -other

    def __imul__(self, other):
        return 0

    def __ifloordiv__(self, other):
        return 0

    def __idivmod__(self, other):
        return 0

    def __idiv__(self, other):
        return 0

    def __itruediv__(self, other):
        return 0

    def __imod__(self, other):
        return 0

    def __ipow__(self, other):
        return 0

    def __ilshift__(self, other):
        return 0

    def __irshift__(self, other):
        return 0

    def __iand__(self, other):
        return 0

    def __ixor__(self, other):
        return other

    def __radd__(self, other):
        return other

    def __rsub__(self, other):
        return -other

    def __rmul__(self, other):
        return 0

    def __rfloordiv__(self, other):
        return 0

    def __rdivmod__(self, other):
        return 0

    def __rdiv__(self, other):
        return 0

    def __rtruediv__(self, other):
        return 0

    def __rmod__(self, other):
        return 0

    def __rpow__(self, other):
        return 0

    def __rlshift__(self, other):
        return 0

    def __rrshift__(self, other):
        return 0

    def __rand__(self, other):
        return 0

    def __rxor__(self, other):
        return other

    def __neg__(self):
        return 0

    def __pos__(self):
        return 0

    def __abs__(self):
        return 0

    def __invert__(self):
        return 0

    def __lt__(self, other):
        return False

    def __le__(self, other):
        return False

    def __eq__(self, other):
        return False

    def __ne__(self, other):
        return False

    def __ge__(self, other):
        return False

    def __gt__(self, other):
        return False

    def __cmp__(self, other):
        return 0

    def __nonzero__(self):
        return False

    def __contains__(self, item):
        return False

    def keys(self):
        return tuple()

    def values(self):
        return []

    def items(self):
        return tuple()

    def iterkeys(self):
        while False:
            yield

    def itervalues(self):
        while False:
            yield

    def iteritems(self):
        while False:
            yield

    def viewkeys(self):
        return tuple()

    def viewvalues(self):
        return []

    def viewitems(self):
        return tuple()
