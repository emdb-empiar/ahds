# -*- coding: utf-8 -*-
# core.py
""" Common data structures and utils used accross all submodules of ahds """

from __future__ import print_function
import functools as ft
import weakref
import inspect
import pickle
import re
import sys
import warnings
import numpy as np
import types


class ahds_readonly_descriptor(object):
    """
    common base class for all ahds_readonly_descriptor classes
    """

    __slots__ = ()

    #valuenotset = ()
    __objclass__ = None

    def __new__(cls,blockclass,slotname,slot):
        """
        creates the ahds_readonly_descriptor for the specified slot and
        creates the corresponding slotname attribute.

        Parameters:
        ===========
            :param Block blockclass:
                the Block type class for which readonly access to slot shall
                be established

            :param str slotname:
                the public attribute-name of the read-only access to the slot
                
            :param str slot:
                the private/protected attribute-name of the slot

        """
        _descriptor = getattr(blockclass,slot,None)
        _hosting_class = getattr(_descriptor,'__objclass__',blockclass)
        _getter = _descriptor.__get__

        class ahds_readonly_descriptor_(cls):
            __slots__ = ()
            def __get__(self,instance,owner):
                if instance is not None:
                    return _getter(instance,owner)
                if owner is self.__objclass__ or issubclass(owner,self.__objclass__):
                    return self.__objclass__.__dict__[slotname]
                raise TypeError("'{}' type not a subclass of '{}'".format(owner.__name__,self.__objclass__.__name__))

            def __set__(self,instance,value):
                raise AttributeError("'{}' object attribute '{}' is read-only".format(self.__objclass__.__name__,slotname))

            def __delete__(self,instance):
                raise AttributeError("'{}' object attribute '{}' is read-only".format(self.__objclass__.__name__,slotname))
                
            __objclass__ = _hosting_class

        # create new descriptor
        return super(ahds_readonly_descriptor,cls).__new__(ahds_readonly_descriptor_)

class ahds_parent_descriptor(object):
    """
    common base class for all ahds_parentmember_descriptor classes
    """

    __slots__ = ()
    __objclass__ = None

    def __new__(cls,blockclass):
        """
        adds protection and automatic reference management for the parent
        slot representing a weak reference to the parent Block type object.
        This reference can be accessed through the read-only parent attribute.
        Modifications are only posible when accessed through the protected
        _parent attribute. The reference can not be deleted. In case 
        The parent object is garbage collected or deleted the parent references
        of all objects linking to it are reset to None when accessed the next
        time. 
        """
        
        _parent_descriptor = getattr(blockclass,'parent',None)
        if isinstance(_parent_descriptor,cls): # pragma: nocover should not be triggered
            return
        # class does not yet have a parent, _parent attribute pair which
        # manages weak references.
        _hosting_class = getattr(_parent_descriptor,'__objclass__',blockclass)
        _parent_getter = _parent_descriptor.__get__
        _parent_setter = _parent_descriptor.__set__

        # create the descriptor preventing modification and assign it to the
        # parent attribute
        class ahds_parent_descriptor_(cls):
            __slots__ = ()

            def __get__(self,instance,owner):
                if instance is not  None:
                    _parent = _parent_getter(instance,owner)
                    if _parent:
                        _alifeparent = _parent()
                        if not _alifeparent:
                            _parent_setter(instance,_alifeparent)
                        return _alifeparent
                    return None 
                if owner is self.__objclass__ or issubclass(owner,self.__objclass__):
                    return self.__objclass__.__dict__['parent']
                raise TypeError("'{}' type class not a subclass of 'Block'".format(owner))
        
            def __set__(self,instance,value):
                raise AttributeError("'{}' object attribute 'parent' is read-only".format(self.__objclass__.__name__,))

            def __delete__(self,instance):
                raise AttributeError("'{}' type object 'parent' attribute can not be removed")

            __objclass__ = _hosting_class

        _public_descriptor = super(ahds_parent_descriptor,cls).__new__(ahds_parent_descriptor_)
        print(_public_descriptor)

        # create a wrapper for the parent member_descriptor which only accepts Block
        # type objects and the special value None for clearing reference. 
        # For any valid Block type object a weak reference is store to the underlying
        # parent slot.
        cascade_descriptors = ahds_parent_descriptor_
        class ahds_parent_descriptor_(cascade_descriptors):

            __slots__ = ()
            def __set__(self,instance,value):
                if not isinstance(value,blockclass):
                    if value is None:
                        _parent_setter(instance,value)
                        return
                    raise ValueError('parent must either be Block type object or None')
                _parent_setter(instance,weakref.ref(value))

        _private_descriptor = super(ahds_parent_descriptor,cls).__new__(ahds_parent_descriptor_)
        print(_private_descriptor)
        return _public_descriptor,_private_descriptor

# TODO as soon as Python 2 is history introduce BlockNamespace dict providing __protectedslots__ as
# out of band data of class namespace dict. will be cleared by BlockMetaClass.__new__ and its content
# added to class namespace before creation of class.

class BlockMetaClass(type):
    """
    Meta class for any kind of Block. It ensures that slots marked read only using ReadOnly
    decorator method are read only and that weak parent reference is dereferenced 
    transparently on accessing the parent parameter and updated appropriately when
    assigning a new value to it.
    """

    __slots__ = ()
    # used to represent the value of slot attributes to which no value has been assigned
    # most likely this will be used on attributes the content of which will be made
    # available by some load on demmand mechanisms implemented through the __getattr__
    # method of dedicated subclasses of the Block class. It us utilized by the
    # ahds_readonly_descriptor.get_membersteate method to indicate that value has not
    # been provided so far.
    #valuenotset = ()

    @staticmethod
    def readonly_slot(name,copy=True,forceload=False,namespace = dict()):
        """
        This method is inserted into the local namespace of class declaration.
        It stores the provided parameters in a dictionary hosted by the __protectedslots__ 
        special member variable. The items stored inside this dictionary will
        be passed to initialize instances of the ahds_readonly_descriptor by the 
        BlockMetaClass.__new__ method below. 
        
        On return an _ is prepended to name marking corresponding slot protected
        """
        
        _protectedslots = namespace.get('__protectedslots__',None)
        if not isinstance(_protectedslots,dict): #pragma: cover_py3
            raise TypeError("special attribute '__protectedslots__' must be dict")
        if not name or name[0] == '_':
            # only public slots can be labeld read-only. Protected, private slots and
            # slots mimicking special attributes are ignored.
            return name
        # record name, prepend with '_' and pass on name as protected slot instead 
        _protectedslots[name] = dict(
            allowcopy = copy,
            loadoncopy = forceload,
        )
        return "_{}".format(name)

    @classmethod
    def __prepare__(metacls,name,bases,**kwords):
        """
        pre populate the namespace used to collect the class declaration and definition
        of the mew Block type class with an empty dictionary for the __protectedslots__
        structure and make the readonly_slot method available as READONLY decorator within
        class namespace.
        """
        # TODO on removing Python 2 support skip following line and replace _namespace.update
        # by simple _namespace = BlockNamespace(READONLY = ft.partial(...)) see above TODO
        _namespace = kwords.get('namespace',dict())
        _namespace.update(
            dict(
                __protectedslots__ = dict(),
                READONLY = ft.partial(BlockMetaClass.readonly_slot,namespace=_namespace)
            )
        )
        
        if kwords.pop('__readonly_2_hook__',False): #pragma: cover_py2
            # hack for python 2 to provide global READONLY stub with the appropriate readonly hook
            # to properly record first slot marked READONLY. The next call will allready be handled
            # by installed shadows
            #
            # TODO remove when Python 2 support is finally dropped
            return _namespace,_namespace['READONLY']
        return _namespace # pragma: cover_py3

    def __new__(cls,name,bases,namespace,**kwords):
        """
        establishes a new Block type class using the class description defined
        by the local namespace structure
        """

        _local_readonlyslot = namespace.get('READONLY')
        if (
            _local_readonlyslot is BlockMetaClass.readonly_slot or 
            ( isinstance(_local_readonlyslot,ft.partial) and _local_readonlyslot.func is BlockMetaClass.readonly_slot )
        ):
            namespace.pop('READONLY')
            
        # list all slots attributes python has to reserve space for
        _slots = namespace.get('__slots__',())
        if isinstance(_slots,str):
            namespace['__slots__'] = _slots = (_slots,)

        # check if 'parent' has already been defined on base class and if remove from slots
        have_parent = 'parent' in _slots
        for base_name in ( base.__name__ for base in bases if 'parent' in base.__dict__.get('__slots__',()) and have_parent):
            raise TypeError("'parent' attribute already defined by '{}' base class".format(base_name))
            
        _protectedslots = namespace.get('__protectedslots__',dict())
            
        # create the class object instance for the new class
        _blockclass = super(BlockMetaClass,cls).__new__(cls,name,bases,namespace)
        assert(_blockclass.__dict__.get('__protectedslots__',dict()) == _protectedslots)

        # establish parent descriptor handling all the conversion between weak reference and 
        # full reference and unlinking if parent is garbage collected as well as protecting it
        # from beeing modified from outside block class hierarchy and deletion
        if have_parent:
            _public_descriptor,_private_descriptor = ahds_parent_descriptor(_blockclass)
            setattr(_private_descriptor.__objclass__,'_parent',_private_descriptor)
            setattr(_public_descriptor.__objclass__,'parent',_public_descriptor)
        # enforce readonly and selected copy semantics for all slots marked by READONLY decorator
        # the required information was stored by the BlockMetaClass.readonly_slot method
        # inside the __protectedslots__ special attribute. 
        # Remove all names which are not declared by the  __slots__ structure as well as special names
        # like parent, __dict__ or __weakref__.
        # Establish ahds_readonly_descriptor for all remaining slots in list
        for _slotname in dict(_protectedslots):
            if _slotname in ('parent','__dict__','__weakref__'):
                _protectedslots.pop(_slotname)
                continue
            internal_name = "_{}".format(_slotname)
            if internal_name not in _slots:
                _protectedslots.pop(_slotname)
                continue
            _public_descriptor = ahds_readonly_descriptor(_blockclass,_slotname,internal_name)
            setattr(_public_descriptor.__objclass__,_slotname,_public_descriptor)
        return _blockclass

if sys.version_info[0] >= 3: #pragma: cover_py3
    # All defnitions for Python3 and newer which differ from their counterparts in Python2.x
    from collections.abc import Iterable as IterableType

    def _decode_string(data):
        """ decodes binary ASCII string to python3 UTF-8 standard string """
        try:
            return data.decode("ASCII")
        except:
            return data.decode("UTF8")


    # in define xrange alias which has been removed in Python3 as range now is equal to
    # xrange
    # TODO would like to remove and ignore from now on eventhough this would on some places slow down
    # python 2
    #xrange = range

    # define _dict_iter_values, _dict_iter_items, _dict_iter_keys aliases imported by the
    # other parts for dict.values, dict.items and dict.keys

    # pylint: disable=E1101
    #_dict_iter_values = dict.values

    #_dict_iter_items = dict.items

    #_dict_iter_keys = dict.keys
    # pylint: enable=E1101

    if sys.version_info[0] > 3 or sys.version_info[1] >= 7: # pragma: nocover
        _dict = dict
    else:
        from collections import OrderedDict # pargma: nocover
        _dict = OrderedDict

    def _qualname(o):
        return o.__qualname__

    _str = str

    # TODO inlcude in documentation that it can be used to
    # mark slots read only
    # def READONLY(name,copy=True,forceload=False):
    #     """
    #     Marks slot with name as readonly. Use as follows

    #         __slots__ = READONLY("readlonlyslot"[,...])
    #         __slots__ = ( ..., "_otherslot",READONLY("readonlyslot"[,...]),"_anotherslot", ...)

    #     :param str name: the name of the slot to be protected
    #     :param bool copy: If True value will be copied by copy.copy or copy.deepcopy method
    #                       If False value will be left unset by copy.copy and copy.deepcopy
    #     :paran bool forceload: If true __gettattr__ will be called if value is unset when
    #                       block is copied using copy.copy or copy.deepcopy.
    #                       If False value will left unset if not loaded by a preceeding call
    #                       to __getattr__

    #     NOTE: READONLY decorator has no impact on slot attributes whitch start with a _ like
    #         protected and private attributes as well as slots mimicking special attributes
    #     """
    #     # empty stub will be shadowed by BlockMetaCalss.__prepare__ method
    #     # through adding local variable of same name to class name space when
    #     # class declaration is read
    #     # TODO if really really really necessary check if inside class definition and 
    #     #      and add any kind of incarnation of this method on calling namespace which is not yet
    #     #      replaced by proper shadow on local namespace or if that is to complex and unstable
    #     #      simply throw Exception stateign that read ONLY must be on global import
    #     return  name 

    def populate_namespace(namespace):
        """
        helper to ensure no __dict__ and __weakref__ attributes are created on 
        BlockMetaClassLink class before Block class below
        """
        namespace.update(
            dict(
                __slots__ = ()
            )
        )
        return namespace

    # TODO on skipping python 2 support whole BlockMetaClassLink class can be dropped and metaclass
    #      directly defined on Block class declaration
    BlockMetaClassLink = types.new_class("BlockMetaClassLink",(object,),dict(metaclass=BlockMetaClass),populate_namespace)

else: #pragma: cover_py2
    # All defnitions for Python 2.x which differ from their counterparts in Python 3.x and newer
    # TODO drop whole else clause when dropping Python 2 support
    from imp import reload
    from collections import Iterable as IterableType
    reload(sys)
    sys.setdefaultencoding("utf-8")

    def _decode_string(data):
        """
        in python2.x no decoding is necessary thus just returns data without any change
        """
        return data

    # try to define xrange alias pointing to the builtin xrange
    # TODO would like to remove and ignore from now on eventhough this would on some places slow down
    # python 2
    #import __builtin__
    #try:
    #    xrange = __builtins__['xrange']
    #except: # pragma: nocover
    #    xrange = getattr(__builtins__, 'xrange', xrange)

    # replace dict by a subclass swapping standard items, values and keys methods
    # with viewitems, viewvalues and viewkeys methods. Unless external code importing
    # ahds strictly relies upon dict items, values and keys are an indexable copy 
    # of the original items this should simplify dropping python 2 support lateron
    # pylint: disable=E1101
 
    _native_dict = dict

    class make_work_meta(type):
        """ metaclass to ensure isinstance(inst,dict) and issubclass(cls,dict)
            behave as expected """

        __slots__ = ()
        @classmethod
        def __instancecheck__(cls,inst):
            return any(cls.__subclasscheck__(c) for c in {type(inst),inst.__class__})

        @classmethod
        def __subclasscheck__(cls,sub):
            return any(c in {_native_dict,cls} for c in sub.mro())

    class dict(_native_dict):
        """ facade doing the actual swapping """
        __metaclass__ = make_work_meta
        items = _native_dict.viewitems
        values = _native_dict.viewvalues
        keys = _native_dict.viewkeys
        listitems = _native_dict.items
        listvalues = _native_dict.values
        listkeys = _native_dict.keys

    __builtins__['dict'] = dict if isinstance(__builtins__,_native_dict) else setattr(__builtins__,'dict',dict)
    #_dict_iter_values = dict.itervalues
    #
    #_dict_iter_items = dict.iteritems

    #_dict_iter_keys = dict.iterkeys
    # pylint: enable=E1101

    # patch range to be compatible to python3 same as above if some external code expects 
    # result of range be a list and checks for it than remove this line and go with 
    # slow memory consuming range function.
    __builtins__['range'],__builtins__['slow_range'] = __builtins__['xrange'],__builtins__['range']

    from collections import OrderedDict

    _dict = OrderedDict

    def _qualname(o):
        return o.__name__

    _str = __builtins__['unicode']

    def READONLY(name,copy=True,forceload=False):
        """
        Marks slot with name as readonly. Use as follows

            __slots__ = READONLY("readlonlyslot"[,...])
            __slots__ = ( ..., "_otherslot",READONLY("readonlyslot"[,...]),"_anotherslot", ...)

        :param str name: the name of the slot to be protected
        :param bool copy: If True value will be copied by copy.copy or copy.deepcopy method
                          If False value will be left unset by copy.copy and copy.deepcopy
        :param bool forceload: If true __gettattr__ will be called if value is unset when
                          block is copied using copy.copy or copy.deepcopy.
                          If False value will be left unset if not loaded by a preceeding call
                          to __getattr__

        NOTE: READONLY decorator has no impact on slot attributes whitch start with a _ like
            protected and private attributes as well as slots mimicking special attributes
        """

        # if everything works as expected this function should be called only
        # on the first occurence of READONLY call and be shadowed by
        # local variable referencing corresponding method of BlockMetaClass
        _stack = inspect.stack()[1:]
        if len(_stack) < 1: # pragma: nocover
            raise TypeError("Must be called from within class definition")# TODO appropriate error not inside class
        _caller = _stack[0]
        _namespace = _caller[0].f_locals
        if '__module__' not in _namespace: # pragma: nocover
            # not a namespace dictionary of a class, which would be prepopulated with 
            # special __module__ reference
            return name
        _globals = _caller[0].f_globals
        if _namespace is _globals: # pragma: nocover
            # not in class declartion there locals and globals must be different
            return name

        # force call to BlockMetaClass.__prepare__ method 
        _namespace,_readonly_hook = BlockMetaClass.__prepare__(_caller[3],None,namespace=_namespace,__readonly_2_hook__ = True)
        return _readonly_hook(name,copy,forceload,namespace=_namespace)

    # add above READONLY decorator to __builtins__ dictionary to ensure it can be called on the first
    # slot name to be made read-only as if initialized by __prepare__ method of meta class.
    __builtins__['READONLY'] = READONLY

    class BlockMetaClassLink(object):
        """
        empty stub to define BlockMetaClass as metaclass of Block class leveling differences in
        declaration between python 2 and python3 
        """
        __metaclass__ = BlockMetaClass

        # define empty slots dictionary to supress creation of __weakref__ and __dict__ attributes
        # before requested by Block class below.
        __slots__ = ()
        def __dir__(self):
            """
            mimicks Python 3 object.__dir__ default implementation at its best, which is
            called by __dir__ method of Block class
            """
            _self_dict = getattr(self,'__dict__',{})
            return dir(self.__class__) + list(_self_dict.keys())


assert ft is not None

def deprecated(description):
    """
    decorator for marking functions, classes and methods as deprecated.
    If properties or their getter, setter or deleter method shall be marked
    deprecated apply decorators in following order from outer most to inner:
        @property
        @deprecated
        def deprecated_method(self,...):
            pass
    """
    def outer_wrapper(o):
        @ft.wraps(o)
        def inner_wrapper(*args, **kwargs):
            if isinstance(o,(
                types.FunctionType,types.BuiltinFunctionType,types.LambdaType,
                types.MethodType,types.BuiltinMethodType
            )):
                warnings.warn(
                    "function/method/property '{}' is deprecated: {}".format(_qualname(o), description),
                    DeprecationWarning
                )
            elif isinstance(o,type): # pragma: cover_py3
                warnings.warn("class '{}' is deprecated: {}".format(_qualname(o), description), DeprecationWarning)
            return o(*args, **kwargs)
        return inner_wrapper
    return outer_wrapper

class ahds_member_descriptor(object):
    """
    base class for all ahds_member_descriptor classes which provide and
    protect access to dynamic attributes defined by the content of AmiraMesh
    and Amira HyperSurface files.
    """

    # dictionary storing finalizer objects for all Block type class instances on which
    # the corresponding attribute is defined
    __slots__ = "_alifeinstances"

    # dummy value used to distinguish between instance attribute for which no content is available
    # and instance attributes which have explicitly set to the value None
    _name_not_a_valid_key = ()

    __objclass__ = None

    def _makealife(self,blockinstance,name):
        instanceid = id(blockinstance)
        if instanceid in self._alifeinstances: # pragma: nocover
            return
        self._alifeinstances.update({
            instanceid: weakref.ref(blockinstance,lambda ref:self._cleanup(instanceid,name))
        })

    def _cleanup(self,instanceid,name):
        
        _vanish = self._alifeinstances.pop(instanceid,None)
        if _vanish is None: # pragma: nocover
            # just in case called recursively by below dettach call or already
            # dettached
            return
        # just ensure that finalizer is dead afterwards in any case
        if self._alifeinstances:
            # still instances left providing the corresponding attribute
            return
        # no more instances providing content for the  attribute with specified name.
        # remove descriptor from defining block class as denoted by __objclass__
        _hosting_class = getattr(self,'__objclass__',None)
        if _hosting_class is None:
            return
        delattr(_hosting_class,name)

    @staticmethod
    def _nocleanup(instanceid,name):
        pass

    def __new__(cls,blockinstance,name,oldname=None):
        """
        called by Block.add_attr, and Block.rename_attr methods to maintain
        the ahds_member_descriptor data descriptors providing access to the
        attributes defined through the content of AmiraMesh and HyperSurface
        files.

        :param Block blockinstance: the instance of Block or any of its subclasses for
                which the data descriptor has to be maintained.
        :param str name: the name of the attribute to be granted access to
        :param str oldname: the previous name in case attribute is to be renamed to name
        :raises AttributeError: 
            in case name is already declared by __slots__ or instance and __class__, __dict__ structures
            in case old name is not found on the _attrs structure 
        """


        if name in blockinstance.__dict__:
            raise AttributeError("'{}' type object attributes '{}' already defined".format(blockinstance.__class__.__name__,name))
        # prepare moving of attribute
        if oldname is not None:
            if not isinstance(oldname,str):
                raise AttributeError("'{}' type object attribute '{}' is not a valid AmiraMesh or HyperSurface parameter".format(blockinstance.__class__.__name__,oldname))
            _olddescriptor = getattr(blockinstance.__class__,oldname,None)
            if _olddescriptor is None or not isinstance(_olddescriptor,cls) or oldname not in blockinstance._attrs:
                # only attributes existent in _atts for which the corresponding data descriptor is maintained through
                # ahds_member_descriptor classes can be renamed
                raise AttributeError("'{}' type object has no attribute '{}'".format(blockinstance.__class__.__name__,oldname))
            if name is None:
                # called by remove_attr
                _olddescriptor._cleanup(id(blockinstance),oldname)
                return True
            _docleanup = _olddescriptor._cleanup
        else:
            _docleanup = cls._nocleanup
        if not isinstance(name,str):
            raise AttributeError("attribute name must be string")
        # maintain ahds_member_descriptor for attribute using specified name 
        _descriptor = getattr(blockinstance.__class__,name,None)
        if _descriptor is not None:
            if not isinstance(blockinstance,_descriptor.__objclass__): # pragma: nocover
                # somebody who really wants to break shall break
                raise RuntimeError("inconsistent descriptor")
            _hosting_dict = _descriptor.__objclass__.__dict__
            if name in _hosting_dict.get('__slots__',()) or name in _hosting_dict.get('__protectedslots__',{}):
                raise AttributeError("'{}' type object attributes '{}' already defined".format(blockinstance.__class__.__name__,name))
            if not isinstance(_descriptor,cls): # pragma: nocover
                # somebody who really wants to break shall break
                raise AttributeError("'{}' type object attribute '{}' exists".format(blockinstance.__class__.__name__,name))
            if name in blockinstance._attrs:
                # rename only possible if name does not exist on _attrs
                # otherwise undefined behavior may occur. Just replacing value of attribute
                # is safe. Indicate that descriptor is already maintained for blockinstance
                return False
            _docleanup(id(blockinstance),oldname)
            _descriptor._makealife(blockinstance,name)
            return True
        # store unbound _attrs getter and dictionary get methods in closoure variables
        # to directly access both without the need for further attribute lookups
        _attrs_getter  = getattr(blockinstance.__class__,'_attrs')
        if not isinstance(_attrs_getter,types.MemberDescriptorType):
            # indicate that attribute is not provided or broken for specified blockinstance
            raise AttributeError("'{}' type object attribute '_attrs' inconsitent or missing".format(blockinstance.__class__.__name__))
        _docleanup(id(blockinstance),oldname)
        _get_attrs = _attrs_getter.__get__
        _value_get = dict.get

        class ahds_member_descriptor_(cls):
            __slots__ = ()
                
            def __get__(self,instance,owner):
                if instance is None:
                    # pylint: disable=E1101
                    if owner is self.__objclass__ or issubclass(owner,self.__objclass__):
                        return self.__objclass__.__dict__[name]
                    raise TypeError("'{}' type class not a subclass of '{}'".format(owner,self.__objclass__))
                # load _attrs dictionary of Block instance
                _instance_attrs = _get_attrs(instance,owner)
                # lookup name in instance._attrs dictionary if not present use _name_not_a_valid_key as default to indicate
                # that block attribute is not defined 
                _value = _value_get(_instance_attrs,name,cls._name_not_a_valid_key)
                if _value is not cls._name_not_a_valid_key:
                    return _value
                # check if name is stored in __dict__ of instance and if return its value
                try:
                    return instance.__dict__[name]
                except KeyError:
                    raise AttributeError("'{}' type object has no '{}' attribute".format(instance.__class__.__name__,name))

            def __set__(self,instance,value):
                if name in _get_attrs(instance,instance.__class__):
                    # __set__ may fail allways as represented values are set by modifying _attrs dictionary of blockinstance directly
                    raise AttributeError("'{}' type object attribute '{}' can not be modified. use add_attr, rename_attr instead".format(instance.__class__.__name__,name))
                # name not stored inside _attrs on this instance allow modification through setattr
                instance.__dict__[name] = value

            def __delete__(self,instance):
                if name in _get_attrs(instance,instance.__class__):
                    # __delete__ may fail allways as represented values are deleted by removing them from _attrs dictionary of blockinstance directly
                    raise AttributeError("'{}' type object attribute '{}' can not be deleted. use remove_attr instead".format(instance.__class__.__name__,name))
                # name not stored inside _attrs on this instance allow modifcation through delattr
                try:
                    instance.__dict__.pop(name)
                except KeyError:
                    raise AttributeError("'{}' type object has no '{}' attribute".format(instance.__class__.__name__,name))

            # define __objeclass__ special class attribute to make descriptor look alike true member_descriptor
            # and property data descriptors as well as to facilitate the removal of the descriptor later on 
            # when not needed any more.
            __objclass__ = blockinstance.__class__
                    
        # create instance of descriptor and insert it into the classdict of the blockinstance
        _descriptor = super(ahds_member_descriptor,cls).__new__(ahds_member_descriptor_)
        _descriptor._alifeinstances = dict()
        _descriptor._makealife(blockinstance,name)
        return _descriptor

@ft.total_ordering
class Block(BlockMetaClassLink):
    """Generic block"""
    __slots__ = (READONLY('name',True,False), '_attrs', 'parent', '__dict__', '__weakref__')

    def __init__(self, name):
        self._attrs = _dict()
        self._parent = None
        self._name = name

    def __getstate__(self):
        """
        return state of Block class instance describing currently available content of Block.

        The main purpose is to provide proper copy of Block using copy.copy and copy.deepcopy methods.
        """
        _state = dict(
            _attrs = self._attrs,
            _parent = self._parent
        )
        _state.update(self.__dict__)
            
        # separate handling of __slots__ necessary as some of them may be marked READONLY, 
        # as well as it may the case that their content has not yet been loaded at all may
        # not bee loaded when block is copied or can not be loaded at all
        # to get current state of READONLY slots check if name with first _ removed is listed
        # in __protectedslots__ attribute of hosting class. In case not protected try to read
        # its value. If not allowed to copy ignore it. In case not forced loading required when 
        # copied ignore it  Filter _attrs,__dict__,__weakref__ and parent as they either have
        # already been handled above or should not be copied at all.
        # To ensure that __slots__ and __protectedslots__ match access them through 
        # class __dict__ of inspected class if present
        for _slotname,_descriptor,_protectedslots,_inspected_parent in (
            (_membername,_parent.__dict__.get(_membername,None),_ro_slots,_parent)
            for _parent,_ro_slots,_slots in (
                (_par,_par.__dict__.get('__protectedslots__',{}),_par.__dict__.get('__slots__',()))
                for _par in type.mro(self.__class__)
            )
            for _membername in _slots
            if _membername not in ('_attrs','__dict__','__weakref__','parent')
        ):
            if _descriptor is None: # pragma: nocover
                continue
            _protection = _protectedslots.get(_slotname[1:],None)
            if _protection is None:
                _state[_slotname] = _descriptor.__get__(self,self.__class__)
                continue
            if not _protection["allowcopy"]:
                continue
            try:
                _value = _descriptor.__get__(self,self.__class__)
            except AttributeError as what:
                if not _protection['loadoncopy']:
                    continue
                _value = getattr(self,_slotname[1:])
            _state[_slotname] = _value
        return _state

    def __setstate__(self,state):
        """
        restore state of Block class retrieved through __getstate__ above on new Block instance.

        The main purpose is to provide proper copy of Block using copy.copy and copy.deepcopy methods.
        """

        if '_attrs' not in state:
            raise pickle.UnpicklingError("not a valid Block instance state: '_attrs' dictionary missing")
        if '_name' not in state:
            raise pickle.UnpicklingError("not a valid Block instance state: name attribute required")
        self._attrs = _dict()
        # restore all attributes provided through _attr structure. Ensure that for all 
        # the corresponding ahds_member_descriptor data descriptor is maintained
        #for _name,_value in _dict_iter_items(state['_attrs']):
        for _name,_value in state['_attrs'].items():
            self.add_attr(_name,_value)
        self._parent = None
        # slower but does not need any distinction between attributes defined through __slots__ structure
        # and those hosted in  __dict__
        for _attrname,_attrvalue in (
            (_name,_val)
            #for _name,_val in  _dict_iter_items(state)
            for _name,_val in  state.items()
            if _name not in ('_attrs','__dict__','__weakref__')
        ):
            setattr(self,_attrname,_attrvalue)

    @property
    def ids(self):
        return [
            int(_matid) 
            for _val in self._list #_dict_iter_items(self._attrs)
            if isinstance(_val,Block)
            for _matid in (_val._attrs.get('Id',None),)
            if _matid is not None
        ] if self.name == 'Materials' else []

    def add_attr(self, attr, value=None, isparent=False):
        """
        Add an attribute to this block object
        :param attr: name of attribute or Block object
        :param value: the value to be represented by the attribute
        :param bool isparent:
           True .... value is parent of this block
           False ... this block is parent of value
           None .... do neither alter parent of this block nor value 
        :raises ValueError:
             if attr is neither a string specifying name of attribute nor a valid Block instance
        :raises AttributeError:
            in case name is already declared by __slots__ or instance and __class__, __dict__ structures
        """
        if not isinstance(attr,str):
            if not isinstance(attr,Block):
                raise ValueError("attr must be string or Block with .name attribute set")
            value = attr
            attr = attr.name
        _descriptor = ahds_member_descriptor(self,attr)
        if not _descriptor:
            _oldval = self._attrs[attr]
            if isinstance(_oldval,Block) and _oldval._parent is self:
                _oldval._parent = None
        elif isinstance(_descriptor,ahds_member_descriptor):
            setattr(_descriptor.__objclass__,attr,_descriptor)
        self._attrs[attr] = value
        if isinstance(value,Block):
            if isparent:
                self._parent = value
            elif isparent is not None:
                value._parent = self

    def rename_attr(self, new_name, name):
        """
        Rename an attribute
        :param str new_name: the new name of the attribute
        :param str name: the current name of the attribute to be renamed
        :raises ValueError:
            if new_name already exists
        :raises AttributeError:
            in case new_name is already declared by __slots__ or instance and __class__, __dict__ structures
            in case old name is not found on the _attrs structure 
        """
        _descriptor = ahds_member_descriptor(self,new_name,name)
        if not _descriptor:
            raise ValueError("'{}' attribute already defined for '{}' type object".format(new_name,self.__class__.__name__))
        elif isinstance(_descriptor,ahds_member_descriptor):
            setattr(_descriptor.__objclass__,new_name,_descriptor)
        self._attrs[new_name] = self._attrs[name]
        del self._attrs[name]

    def remove_attr(self,name):
        ahds_member_descriptor(self,None,name)
        del self._attrs[name]

    def __str__(self, prefix="", index=None,is_parent = False,printed = set(),name = None):
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
                format("{}+[{}]-{}".format(prefix,index, self.name if name is None else name), '<55'),
                format(type(self).__name__, '>50'),
                str(is_parent)
            )
        else:
            string += "{} {} [is_parent? {:<5}]\n".format(
                format(prefix + "+-{}".format(self.name if name is None else name), '<55'),
                format(type(self).__name__, '>50'),
                str(is_parent)
            )
        if printed:
            if self in printed:
                return string
            printed.add(self)
        else:
            printed = {self}
        string += '{}|  +<Parent>: {}\n'.format(prefix,self._parent.name) if self._parent else ''
        #for attr,value in _dict_iter_items(self._attrs):
        for attr,value in self._attrs.items():
            # check if the attribute is Block or non-Block
            if isinstance(value, Block):
                # if it is a Block then the prefix will change by having extra '| ' before it
                # string += 'something\n'
                string += value.__str__(prefix=prefix + "|  ",is_parent = self._parent == value,printed=printed,name = attr)
            else:
                # if it is not a Block then we construct the repr. manually
                # don't print the whole array for large arrays
                if isinstance(value, (np.ndarray,)):
                    string += self._format_array(prefix,attr,value,80)
                else:
                    string += "{}|  +-{}: {}\n".format(prefix,attr, value)
        printed.remove(self)
        return string

    @staticmethod
    def _format_array(prefix,attr,value,linewidth):
        """
        formats numy array data for prity printing along with all other block
        attributes
        """
        string = "{}|  +-{}:".format(prefix,attr)
        array_prefix = "\n{}|  |   ".format(prefix)
        formatted = np.array2string(
            value,
            precision = 9, # number of float digits printed max
            # number of total elements in array which shall trigger sumarized output
            # independent of dimensions and number of elements printed per edge
            # if total number is lower all array elements will be printed in any
            # case
            threshold = 20,
            # number of items printed at start and end of dimension
            # if number of entries in dimension is <= 2 * edgeitems than
            # all elements of dimension are printed otherwise ... are inserted
            # along dimension
            edgeitems = 3,
            max_line_width = linewidth - len(array_prefix) + 1,
            floatmode = 'maxprec_equal'
        ).split('\n')
        return string + "{}{}\n".format(array_prefix,array_prefix.join(formatted))

    def __getitem__(self, index):
        if not isinstance(index,int):
            raise IndexError('index must be an integer or long')
        if self.name != 'Materials':
            raise NotImplementedError("'{}' type object instance is not Materials list".format(self.__class__.__name__))
        #for _block in _dict_iter_values(self._attrs):
        for _block in self._attrs.values():
            _id = getattr(_block,'Id',None)
            if _id is not None and _id == index:
                return _block
        raise IndexError("No material with specified Index")

    def __contains__(self, item):
        return item in self._attrs

    def __eq__(self, other):
        
        if not isinstance(other,Block):
            return False
        return self.name == other.name

    def __le__(self, other):
        if not isinstance(other,Block):
            return False
        return self.name < other.name

    def __hash__(self):
             return id(self)

    def __dir__(self):
        """
        filters any AmiraMesh and HyperSurface attribute from raw dir() output which is
        not hosted by self._attrs
        """
        _attrs = getattr(self,'_attrs',{})
        return [
            _name
            for _name,_descriptor in (
                (_checkname,getattr(self.__class__,_checkname,None))
                for _checkname in super(Block,self).__dir__()
            )
            if not isinstance(_descriptor,ahds_member_descriptor) or _name in _attrs or _name in self.__dict__
        ]
                 

class ListBlock(Block):
    """Extension of Block which has an iterable attribute to which Block objects can be added"""
    __slots__ = ('_list',)

    def __init__(self, name, initial_len = 0,*args ,**kwargs):
        super(ListBlock, self).__init__(name,*args, **kwargs)
        self._list = list() if initial_len < 1 else [None] * initial_len # separate attribute for ease of management

    @property
    @deprecated("use of items on listblock is deprecated. ListBlock can be used directly where mutable sequence is expected and required")
    def items(self):
        return self._list

    def __str__(self, prefix="", index=None,is_parent=False,printed = set(),name = None):
        """Convert the ListBlock into a string

        :param str prefix: prefix to signify depth in the tree
        :param int index: applies for list items [default: None]
        :returns str string: formatted string of attributes
        """
        # first we use the superclass to populate everything else
        string = super(ListBlock, self).__str__(prefix=prefix, index=index,is_parent=is_parent,printed=printed,name = name)
        # now we stringify the list-blocks
        for index, block in enumerate(self._list):
            if block is None:
                if index > 0:
                    string += "{}+[{}]-{}\n".format(prefix + "|  ",index,block)
                continue # pragma: cover_py3
            string += block.__str__(prefix=prefix + "|  ", index=index,is_parent= block == self._parent,printed=printed)
        return string

    def __len__(self):
        return len(self._list)

    def __setitem__(self, key, value):
        if isinstance(key,slice):
            # raise value error if item in iterable is not a valid Block instance 
            # will only be called if below isinstance check fails
            def reject_iterable():
                raise ValueError('iterable may contain Block class/subclass instances only')

            rollback = list(self._list[:])
            try:
                self._list[key] = (( item for item in value if isinstance(item,Block) or reject_iterable()))
            except ValueError:
                # reset any item already replaced
                self._list[:] = rollback
                raise
            return
        if not isinstance(value,Block):
            raise ValueError('value must be a Block class/subclass')
        self._list[key] = value

    def __getitem__(self, index):
        return self._list[index]

    def __iter__(self):
        # TODO as soon as Python2 Support is stalled activate below line and remove for loop
        #yield from self._list

        for item in self._list:
            yield item

    def __reversed__(self):
        # TODO as soon as Python2 Support is stalled activate below line and remove for loop
        # yield from reversed(self._list)
        for item in reversed(self._list):
            yield item

    def __contains__(self, item):
        return item is not None and item in self._list

    def __delitem__(self,key):
        if key is not None:
            del self._list[key]

    def append(self, item):
        if not isinstance(item,Block):
            raise ValueError('item must be a Block class/subclass')
        self._list.append(item)

    def count(self, item, *args):
        if not isinstance(item,Block):
            raise ValueError('item must be a Block class/subclass')
        return self._list.count(item, *args)

    def index(self, item, *args):
        if not isinstance(item,Block):
            raise ValueError('item must be a Block class/subclass')
        return self._list.index(item, *args)

    def extend(self, iterable):
        # raise value error if item in iterable is not a valid Block instance 
        # will only be called if below isinstance check fails
        def reject_iterable(item):
            raise ValueError('iterable may contain Block class/subclass instances only')

        rollback = len(self._list)
        try:
            self._list.extend(( item for item in iterable if isinstance(item,Block) or reject_iterable(item)))
        except ValueError:
            # remove any item already appended by extend method
            self._list[rollback:] = []
            raise

    def insert(self, index, item):
        if not isinstance(item,Block):
            raise ValueError('item must be a Block class/subclass')
        if index >= len(self._list):
            self._list.extend([None] * (index-len(self._list) + 1) )
        if self._list[index] is None:
            self._list[index] = item
        else:
            self._list.insert(index, item)

    def pop(self, *args):
        return self._list.pop(*args)

    def remove(self, item):
        if not isinstance(item,Block):
            raise ValueError('item must be a Block class/subclass')
        return self._list.remove(item)

    def reverse(self):
        self._list.reverse()

    def sort(self, **kwargs):
        return self._list.sort(**kwargs)

def _main(): # pragma: nocover


    block_test = Block("TestRoot")
    # das it ein normaler comment
    #ahds: block=TestRoot attribute=Number value=10
    block_test.add_attr("Number",10)
    second_block = Block("SecondBlock")
    block_test.add_attr("any_block",second_block)
    third_block = Block("NameFromBlock")
    block_test.add_attr(third_block)
    second_block.add_attr("Weired","kkk")
    third_block.add_attr("hallo","welt")
    try:
        block_test.add_attr(12,7)
    except ValueError:
        pass
    block_test.rename_attr("FlowerPower","NameFromBlock")
    try:
        block_test.rename_attr("NewChild","SecondBlock")
    except ValueError:
        pass
    except AttributeError:
        pass
    try:
        block_test.rename_attr("Number","any_block")
    except ValueError:
        pass
    except AttributeError:
        pass
    try:
        block_test.add_attr("parent",10)
    except AttributeError:
        pass
    try:
        block_test.name=0
    except AttributeError:
        pass
    print("model:\n",block_test)
    import copy

    silblings = copy.copy(block_test)
    print("shallow:\n",silblings)
    deep_silblings = copy.deepcopy(block_test)
    print("deep:\n",deep_silblings)
    print(dir(block_test),"\n",dir(second_block))
    print("Works")
    #ahds: block=block_test attribute=Dimension value=p```[3,5,6]```
    block_test.add_attr("Dimension",[3,5,6])
    dir(block_test)
    nblock = ListBlock("k")
    dir(nblock)
    #ahds: some pragma
    """
somestring
"""
    print("Dimension:",block_test.Dimension[0] + 12)
    third_block.add_attr("Dimension",4)
    #ahds: block=block_test attribute=FlowerPower value=p```ahds.Block("FlowerPower")```
    #ahds: block=block_test.FlowerPower attribute=Dimension value=p```[3,5,6]```
    print("Fulldimension:",block_test.Dimension , block_test.FlowerPower.Dimension)
    a = block_test.FlowerPower.Dimension + 12
    
if __name__ == "__main__": # pragma: nocover
    _main()
        
