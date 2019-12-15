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

class ahds_moduleshadow(object):
    """
    common base class for all _ahds_localproxy classes established by the BlockMetaClass.__prepare__ method.
    """

    @staticmethod
    def create_shadow(mod,methodname,shadowby):
        """
        crate a proxcy class for any import and alias import of ahds and ahds.core module
        to ensure that all calls to ahds.core.READONLY method will be properly redirected
        to the above BlockMetaClass.readonly_slot method.
        """
        # as it is not predicable how the above READONLY method will be accessed
        # wheter it will be imported using 
        # from ahds import READONLY
        # from ahds.core import READONLY as LS
        # or whether just the ahds or ahds.core modules will be imported
        # import ahds
        # import ahds.core as ac
        # .....
        # the current set of global variables is scanned for any occurence of ahds,ahds.core
        # module / package and any direct import of READONLY method independent whether 
        # an alias was defined during import or not 
        # For all occurences a corresponding redirect is created in local name space
        class ahds_metashadow(type):
            """
            proxy meta class hiding _ahds_local_proxy class from isinstances and issubclass
            methods
            """
            def __getattribute__(cls,name):
                return getattr(mod.__class__,name)
    
            def __instancecheck__(cls,instance):
                return isinstance(instance,(ahds_moduleshadow,mod.__class__)) 
    
            def __subclasscheck__(cls,subclass):
                return issubclass(subclass,(mod.__class__,ahds_moduleshadow))
        if sys.version_info[0] >= 3:
            ahds_metashadow_link = types.new_class("ahds_metashadow_link",(ahds_moduleshadow,),dict(metaclass=ahds_metashadow))
        else:
            ahds_metashadow_link = type("ahds_metashadow_link",(ahds_moduleshadow,),dict(__metaclass__ = ahds_metashadow))
                    
        class _ahds_shadow(ahds_metashadow_link):
            """
            proxy class filtering and redirecting calls to READONLY method to
            BlockMetaClass.readonly_slot method. Modification of READONLY method
            is blocked.
            """
            def __getattribute__(self,attr):
                if attr == methodname:
                    return shadowby
                return getattr(mod,attr)
            def __setattr__(self,attr,val):
                if attr == methodname:
                    raise AttributeError("'{}' decorator can not be modified".format(methodname))
                return setattr(mod,attr)
            def __delattr__(self,attr):
                if attr == methodname:
                    raise AttributeError("'{}' decorator can not be modified".format(methodname))
                return delattr(mod,attr)
        return _ahds_shadow()


def _instance_lock(instance,slotname):
    """
    checks if the calling method was called from within the namespace of a
    Block type class or instance method.

    :param instance: the instance of the Block type class the attribute belongs to
    :param slotname: the name of the attribute to be protected
    :raises: AttributeError if attribute is to be modified from outside any Block
             type class context.

    This method is called by the __set__ and __delete__ methods of the
    ahds_readonly_descriptor protecing the specified slot attribute
    """
    for _frame,_,_,_,_,_ in inspect.stack()[1:]:
        _context = _frame.f_locals.get('self') # for now assume that all blocks define self as instance pointer
        if _context is None:
            _context = _frame.f_locals.get('cls')
            if _context is None:
                break
            if issubclass(_context,(readonly_descriptor_base,parent_descriptor_base)):
                continue
            if issubclass(_context,instance.__class__):
                return
        elif isinstance(_context,(readonly_descriptor_base,parent_descriptor_base)):
            continue
        elif _context is instance or isinstance(_context,Block):
            return
        break
    raise AttributeError("'{}' object attribute '{}' is read-only".format(instance.__class__.__name__,slotname))

class readonly_descriptor_base(object):
    """
    common base class for all ahds_readonly_descriptor classes
    """

    valuenotset = ()

    @staticmethod
    def create_descriptor(blockclass,slotname,allowcopy,loadoncopy):
        """
        creates the ahds_readonly_descriptor for the specified slot and tunes
        the behavior in case the current sate of the slot content is requested 
        during a call to copy.copy or copy.deepcopy mainly
        """
        _descriptor = getattr(blockclass,slotname,None)
        _hosting_class = getattr(_descriptor,'__objclass__',blockclass)
        _getter = _descriptor.__get__
        _setter = _descriptor.__set__
        _deleter = _descriptor.__delete__

        class ahds_readonly_descriptor(readonly_descriptor_base):
            def __get__(self,instance,owner):
                if instance is not None:
                    return _getter(instance,owner)
                if owner is self.__objclass__:
                    return owner.__dict__[slotname]
                if issubclass(owner,self.__objclass__):
                    return getattr(self.__objclass__,slotname)
                raise TypeError("'{}' type not a subclass of '{}'".format(owner,self.__objclass__))

            def __set__(self,instance,value):
                _instance_lock(instance,slotname)
                _setter(instance,value)

            def __delete__(self,instance):
                _instance_lock(instance,slotname)
                _deleter(instance)
                
            def get_memberstate(self,instance):
                try:
                    _value = _getter(instance,instance.__class__)
                except AttributeError:
                    # value has not yet been provided for slot
                    # return None or valuenotset dummy according to
                    # allowcopy and loadoncopy parameters passed to
                    # BlockMetaClass.create_descriptor methods
                    if not loadoncopy:
                        return readonly_descriptor_base.valuenotset
                    try:
                        _value = getattr(instance,slotname)
                    except AttributeError:
                        return readonly_descriptor_base.valuenotset
                    else:
                        return _value if allowcopy else None                        
                else:
                    return _value if allowcopy else None
            __objclass__ = _hosting_class

        # create new descriptor
        # set __objectclass__ special attribute to _hosting_class
        # which should be identical to blockclass and replace
        # original descriptor by ahds_readonly_descriptor
        _descriptor = ahds_readonly_descriptor()
        #setattr(_descriptor,'__objclass__',_hosting_class)
        setattr(blockclass,slotname,_descriptor)

class parent_descriptor_base(object):
    """
    common base class for all ahds_parentmember_descriptor classes
    """

    @staticmethod
    def activate_parent(blockclass):
        _parent_descriptor = getattr(blockclass,'parent',None)
        if not isinstance(_parent_descriptor,parent_descriptor_base):
            _hosting_class = getattr(_parent_descriptor,'__objclass__',blockclass)
            _parent_getter = _parent_descriptor.__get__
            _parent_setter = _parent_descriptor.__set__
            _parent_deleter = _parent_descriptor.__delete__
            class ahds_parentmember_descriptor(parent_descriptor_base):
                def __get__(self,instance,owner):
                    if instance is not  None:
                        _parent = _parent_getter(instance,owner)
                        _alifeparent = _parent() if _parent is not None else None
                        return _alifeparent if _alifeparent is not None else None
                    if owner is self.__objclass__:
                        return owner.__dict__['parent']
                    if issubclass(owner,Block):
                         return getattr(self.__objclass__,'parent')
                    raise TypeError("'{}' type class not a subclass of 'Block'".format(owner))
            
                def __set__(self,instance,value):
                    _instance_lock(instance,'parent')
                    if not isinstance(value,Block):
                        if value is not None:
                            raise ValueError('parent must either be Block type object or None')
                        _parent_setter(instance,value)
                        return
                    _weakcleanuplink = weakref.ref(instance)
                    def _cleanup(reference):
                        _instance = _weakcleanuplink()
                        if _instance is not None:
                            _parent_setter(_instance,None)
                    _parent_setter(instance,weakref.ref(value,_cleanup))

                def __delete__(self,instance):
                    raise AttributeError("'{}' type object 'parent' attribute can not be removed")

                __objclass__ = _hosting_class

            _descriptor = ahds_parentmember_descriptor()
            setattr(_hosting_class,'parent',_descriptor)

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
    valuenotset = ()

    @staticmethod
    def readonly_slot(name,copy=True,forceload=False,namespace = dict()):
        # This method is inserted into the local namespace of class declaration 
        # shadowing the global READONLY method defined above. It stores the 
        # provide parameters in a dictionary hosted by the __protectedslots__ 
        # special member variable. The items stored inside this dictionary will
        # be passed to the BlockMetaClass.create_descriptor method by the 
        # BlockMetaClass.__new__ method below.
        
        _protectedslots = namespace.get('__protectedslots__',None)
        if _protectedslots is None:
            return
        _protectedslots[name] = dict(
            allowcopy = copy,
            loadoncopy = forceload
        )
        return name

    @classmethod
    def __prepare__(metacls,name,bases,**kwords):
        """
        pre populate the namespace used to collect the class declaration and definition
        of the mew Block type class with an empty dictionary for the __protectedslots__
        structure and establish all local shadows for the READONLY method and any possible
        calls through module references to adhs and ahds.core module.
        """
        _namespace = kwords.get('namespace',dict())
        _namespace.update({
            '__protectedslots__' : dict(),
        })
        _currentglobals = globals()

        # create partial method object for which namespace parameter is preset
        # with the namespace structure to be used by the current class declaration and definition.
        _local_readonlyslot = ft.partial(BlockMetaClass.readonly_slot,namespace=_namespace)


        if '__readonly__' in _namespace:
            # hack for python 2 to populate namespace with hidden special name __readonly__ called by
            # global READONLY method stub to properly record first slot marked READONLY. This will be removed
            # by READONLY before returning control to class declaration context which after wards calls 
            # local shadowing proxies and methods instead of versions from global namespace
            _namespace['__readonly__'] = _local_readonlyslot

        # scan global namespace
        for _importname,_mustproxy in _dict_iter_items(_currentglobals):
            # check if global item referes to ahds package or any of its sub modules
            if inspect.ismodule(_mustproxy) and "ahds" in ( _mustproxy.__package__, _mustproxy.__name__ ) :
                # if the ahds related module exports the READONLY function create a proxy for it
                # redirecting any call to READONLY qualified by import name of module to the
                # BlockMetaClass.readonly_slot method while transparently passing any other 
                # attribute request to the module it self
                if inspect.isfunction(getattr(_mustproxy,'READONLY',None)):
                    _namespace[_importname] = ahds_moduleshadow.create_shadow(_mustproxy,"READONLY",_local_readonlyslot)
                continue
            # check if the global item refers to the above READONLY method directly 
            if not inspect.isfunction(_mustproxy) or _mustproxy is not READONLY:
                continue
            # insert a local redirect to BlockMetaClass.readonly_slot method
            _namespace[_importname] = _local_readonlyslot
        return _namespace

    def __new__(cls,name,bases,namespace,**kwords):
        """
        establishes a new Block type class using the class description defined
        by the local namespace structure
        """

        # remove any instance of ahds_moduleshadow or BlockMetaClass.readonly_slot method inserted by
        # BlockMetaClass.__prepare__ method above. They are not needed any more and should not
        # occure as class or instance members of the new class.
        _extract = []
        for _shadowed in (
            _shadowname
            for _shadowname,_shadow in _dict_iter_items(namespace)
            if (
                isinstance(_shadow,ahds_moduleshadow) or
                ( callable(_shadow) and isinstance(_shadow,ft.partial) and _shadow.func is BlockMetaClass.readonly_slot )
            )
        ):
            _extract.append(_shadowed)
        for _pop in _extract:
            namespace.pop(_pop)
                
        # create the class object instance for the new class
        _blockclass = super(BlockMetaClass,cls).__new__(cls,name,bases,namespace)

        # list all slots attributes python has reserved space for
        _slots = getattr(_blockclass,'__slots__',tuple())
        # establish parent descriptor handling all the conversion between weak reference and 
        # full reference and unlinking if parent is garbage collected as well as protecting it
        # from beeing modified from outside block class hierarchy and deletion
        if "parent" in _slots:
            parent_descriptor_base.activate_parent(_blockclass)
        # enforce readonly and selected copy semantics for all slots marked by READONLY decorator
        # the required information was stored by the BlockMetaClass.readonly_slot method
        # inside the __protectedslots__ special attribute. 
        # Remove all names which are not declared by the  __slots__ structure as well as special names
        # like parent, __dict__ or __weakref__.
        # Establish ahds_readonly_descriptor for all remaining slots in list
        _protectedslots = getattr(_blockclass,'__protectedslots__',dict())
        for _slotname,_protection in _dict_iter_items(dict(_protectedslots)):
            if _slotname in ('parent','__dict__','__weakref__') or _slotname not in _slots:
                _protectedslots.pop(_slotname)
                continue
            readonly_descriptor_base.create_descriptor(_blockclass,_slotname,**_protection)
        return _blockclass

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

    if sys.version_info[1] >= 7:
        _dict = dict
    else:
        from collections import OrderedDict
        _dict = OrderedDict

    def _qualname(o):
        return o.__qualname__

    _str = str

    def READONLY(name,copy=True,forceload=False):
        """
        Marks slot with name as readonly. Use as follows

            __slots__ = READONLY("readlonlyslot"[,...])
            __slots__ = ( ..., "_otherslot",READONLY("readonlyslot"[,...]),"_anotherslot", ...)

        :param str name: the name of the slot to be protected
        :param bool copy: If True value will be copied by copy.copy or copy.deepcopy method
                          If False value will be left uset by copy.copy and copy.deepcopy
        :paran bool forceload: If true __gettattr__ will be called if value is unset when
                          block is copied using copy.copy or copy.deepcopy.
                          If False value will left unset if not loaded by a preceeding call
                          to __getattr__
        """
        # empty stub will be shadowed by BlockMetaCalss.__prepare__ method
        # through adding local variable of same name to class name space when
        # class declaration is read
        return  name 

    def populate_namespace(namespace):
        namespace.update(
            dict(
                __slots__ = ()
            )
        )
        return namespace

    BlockMetaClassLink = types.new_class("BlockMetaClassLink",(object,),dict(metaclass=BlockMetaClass),populate_namespace)
    #class BlockMetaClassLink(object,metaclass = BlockMetaClass):
    #    """
    #    empty stub to define BlockMetaClass as metaclass of Block class leveling differences in
    #    declaration between python 2 and python3 
    #    """

    #    # define empty slots dictionary to supress creation of __weakref__ and __dict__ attributes
    #    # before requested by Block class below.
    #    __slots__ = ()

else:
    # All defnitions for Python2.x newer which differ from their counterparts in Python3.x and newer
    reload(sys)
    sys.setdefaultencoding("utf-8")

    def _decode_string(data):
        """ in python2.x no decoding is necessary thus just returns data without any change """
        return data

    # try to define xrange alias pointing to the builtin xrange
    import __builtin__
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

    def _qualname(o):
        return o.__name__

    _str = __builtin__.unicode

    def READONLY(name,copy=True,forceload=False):
        """
        Marks slot with name as readonly. Use as follows

            __slots__ = READONLY("readlonlyslot"[,...])
            __slots__ = ( ..., "_otherslot",READONLY("readonlyslot"[,...]),"_anotherslot", ...)

        :param str name: the name of the slot to be protected
        :param bool copy: If True value will be copied by copy.copy or copy.deepcopy method
                          If False value will be left uset by copy.copy and copy.deepcopy
        :paran bool forceload: If true __gettattr__ will be called if value is unset when
                          block is copied using copy.copy or copy.deepcopy.
                          If False value will left unset if not loaded by a preceeding call
                          to __getattr__
                          If None obey _loadstreams
        """

        # if everything works as expected this function should be called only
        # on the first occurence of READONLY call and be shadowed by
        # local variable referencing correspoinding method of BlockMetaClass
        _stack = inspect.stack()
        if len(_stack) < 2:
            raise Exception("Must be called from within class definition")# TODO appropriate error not inside class
        _caller = _stack[1]
        _namespace = _caller[0].f_locals
        if '__module__' not in _namespace:
            return name
        # define fallback method which will be called below if BlockMetaClass.__prepare__ 
        # isnt' called or __readonly__ has been removed form namespace before returning from
        # BlockMetaClass.__prepare__ call.
        def fallback_decorator(name,copy=True,forceload=False):
            return name
        _namespace['__readonly__'] = fallback_decorator
        _namespace = BlockMetaClass.__prepare__(_caller[3],None,namespace=_namespace)
        # call method stored in _namespace as __readonly__ and remove it from
        # namespace it will be not needed any more
        return _namespace.pop('__readonly__')(name,copy,forceload,namespace=_namespace)
    def python3_object__dir__moc(self):
            """
            mimicks Python 3 object.__dir__ default implementation at its best, which is
            called by __dir__ method of Block class
            """
            _self_dict = getattr(self,'__dict__',{})
            return _self_dict.keys() + dir(self.__class__)

    class BlockMetaClassLink(object):
        """
        empty stub to define BlockMetaClass as metaclass of Block class leveling differences in
        declaration between python 2 and python3 
        """
        __metaclass__ = BlockMetaClass

        # define empty slots dictionary to supress creation of __weakref__ and __dict__ attributes
        # before requested by Block cleass below.
        __slots__ = ()



def deprecated(description):
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

class _ahds_member_descriptor_base(object):
    """
    base class for all ahds_member_descriptor classes which provide and
    protect access to dynamic attributed defined by the content of AmiraMesh
    and Amira HyperSurface files.
    """

    # dictionary storing finalizer objects for all Block type class instances on which
    # the corresponding attribute is defined
    __slots__ = "_alifeinstances"

    # dummy value used to distinguis between instance attribute for which no content is available
    # and instance attributes which have explicitly set to the value None
    _name_not_a_valid_key = ()

    def __init__(self):
        self._alifeinstances = dict()

    def _makealife(self,blockinstance,name):
        instanceid = id(blockinstance)
        if instanceid in self._alifeinstances:
            return
        self._alifeinstances.update({
            instanceid: weakref.ref(blockinstance,lambda ref:self._cleanup(instanceid,name))
        })

    def _cleanup(self,instanceid,name,force = True):
        _vanish = self._alifeinstances.pop(instanceid,None)
        if _vanish is None:
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
    def _nocleanup(instanceid,name,force = True):
        pass

    @staticmethod
    def establish_descriptor(blockinstance,name,oldname = None):
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
        if name in blockinstance._attrs:
            # rename only possible if name does not exist on _attrs
            # otherwise undefined behavior may occur. Just replacing value of attribute
            # is safe. Indicate that descriptor is already maintained for blockinstance
            return False
        if name in blockinstance.__dict__:
            # name is inside instance __dict__
            raise AttributeError("'{}' type object attributes '{}' already defined".format(blockinstance.__class__.__name__,name))
        for _ in ( 
            name in _slots
            for _parentclass in inspect.getmro(blockinstance.__class__)
            for _slots in (getattr(_parentclass,'__slots__',()),)
            if name in _slots
        ):
            # name refers to any of the attributes declared through __slots__ special attribute
            raise AttributeError("'{}' type object attributes '{}' already defined".format(blockinstance.__class__.__name__,name))
        # prepare moving of attribute
        _docleanup = _ahds_member_descriptor_base._nocleanup
        if oldname is not None:
            _olddescriptor = getattr(blockinstance.__class__,oldname,None)
            if _olddescriptor is None:
                raise AttributeError("'{}' type object has no attribute '{}'".format(blockinstance.__class__.__name__,oldname))
            if not isinstance(_olddescriptor,_ahds_member_descriptor_base):
                # only attributes for which the corresponding data descriptor is maintained through
                # ahds_member_descriptor classes can be renamed
                raise AttributeError("'{}' type object attribute '{}' is not a valid AmiraMesh or HyperSurface parameter".format(blockinstance.__class__.__name__,oldname))
            if name is None:
                _olddescriptor._cleanup(id(blockinstance),oldname)
                return True
            _docleanup = _olddescriptor._cleanup
        if not isinstance(name,str):
            raise AttributeError("attribute name must be string")
        # maintain ahds_member_descriptor for attribute using specified name 
        _descriptor = getattr(blockinstance.__class__,name,None)
        if _descriptor is not None:
            if not isinstance(_descriptor,_ahds_member_descriptor_base):
                raise AttributeError("'{}' type object attribute '{}' exists".format(blockinstance.__class__.__name__,name))
            _docleanup(id(blockinstance),oldname)
            _descriptor._makealife(blockinstance,name)
            return True
        _docleanup(id(blockinstance),oldname)
        # store unbound _attrs getter and dictionary get methods in closoure variables
        # to directly access both without the need for further attribute lookups
        _attrs_getter  = getattr(blockinstance.__class__,'_attrs')
        if type(_attrs_getter).__name__ != 'member_descriptor':
            # indicate that attribute is now provided for specified blockinstance
            return True
        _get_attrs = _attrs_getter.__get__
        _value_get = dict.get

        class ahds_member_descriptor(_ahds_member_descriptor_base):
            def __init__(self):
                super(ahds_member_descriptor,self).__init__()
                self._makealife(blockinstance,name)
                
            def __get__(self,instance,owner):
                if instance is None:
                    # pylint: disable=E1101
                    if owner is self.__objclass__:
                        return owner.__dict__[name]
                    if issubclass(owner,self.__objclass__):
                        return getattr(self.__objclass__,name)
                    raise TypeError("'{}' type class not a subclass of 'Block'".format(owner))
                # load _attrs dictionary of Block instance
                _instance_attrs = _get_attrs(instance,owner)
                # lookup name in instance._attrs dictionary if not present use _name_not_a_valid_key as default to indicate
                # that blockattributes is not defined 
                _value = _value_get(_instance_attrs,name,_ahds_member_descriptor_base._name_not_a_valid_key)
                if _value is not _ahds_member_descriptor_base._name_not_a_valid_key:
                    return _value
                # check if name is stored in __dict__ of instance
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
                    raise AttributeError("'{}' type object attribute '{}' can not be modified. use add_attr, rename_attr instead".format(instance.__class__.__name__,name))
                # name not stored inside _attrs on this instance allow modifcation through delattr
                try:
                    instance.__dict__.pop(name)
                except KeyError:
                    raise AttributeError("'{}' type object has no '{}' attribute".format(instance.__class__.__name__,name))
                    
        # create instance of descriptor fill its __objcalss__ special variable to make it look alike 
        # true member_descriptor and property data descriptors and to facilitate the removal of the descriptor later on 
        # when not needed any more. Insert the descriptor into the classdict of the blockinstance
        _descriptor = ahds_member_descriptor()
        setattr(_descriptor,'__objclass__',blockinstance.__class__)
        setattr(blockinstance.__class__,name,_descriptor)
        # indicate that attribute is now provided for specified blockinstance
        return True

@ft.total_ordering
class Block(BlockMetaClassLink):
    """Generic block"""
    __slots__ = (READONLY('name',True,False), '_attrs', 'parent', '__dict__', '__weakref__')

    def __init__(self, name):
        self.parent = None
        self.name = name
        self._attrs = _dict()

    def __getstate__(self):
        """
        return state of Block class instance describing currently available content of Block.

        The main purpose is to provide proper copy of Block using copy.copy and copy.deepcopy methods.
        """
        _state = dict(
            _attrs = self._attrs,
            parent = self.parent
        )
        _state.update(self.__dict__)
            
        # separate handling of __slots__ necessary as some of them may be marked READONLY, 
        # as well as it may the case that their content has not yet been loaded at all may
        # not bee loaded when block is copied or can not be loaded at all
        # to get current state of READONLY slots call get_memberstate method of corresponding
        # ahds_readonly_descriptor data descriptor instance instead of calling __get__ method of
        # descriptor directly. Filter _attrs,__dict__,__weakref__ and parent as they either have
        # already been handled above or should not be copied at all
        for _slotname,_value in (
            (_membername,_descriptor.__get__(self,self.__class__) if not isinstance(_descriptor,readonly_descriptor_base) else _descriptor.get_memberstate(self))
            for _parent in inspect.getmro(self.__class__)
            for _membername in getattr(_parent,'__slots__',tuple())
            if _membername not in ('_attrs','__dict__','__weakref__','parent')
            for _descriptor in (getattr(_parent,_membername,None),)
            if _descriptor is not None
        ):
            if _value is BlockMetaClass.valuenotset:
                # no value available skip attribute for this block instance
                # it will left unset by __setstate__
                continue
            _state[_slotname] = _value
        return _state

    def __setstate__(self,state):
        """
        restore state of Block class retrieved through __getstate__ above on new Block instance.

        The main purpose is to provide proper copy of Block using copy.copy and copy.deepcopy methods.
        """

        if '_attrs' not in state:
            raise pickle.UnpicklingError("not a valid Block instance state: '_attrs' dictionary missing")
        if 'name' not in state:
            raise pickle.UnpicklingError("not a valid Block instance state: name attribute required")
        self._attrs = _dict()
        # restore all attributes provided through _attr structure. Ensure that for all 
        # the corresponding ahds_member_descriptor data descriptor is maintained
        for _name,_value in _dict_iter_items(state['_attrs']):
            self.add_attr(_name,_value)
        self.parent = None
        # slower but does not need any distinction between attributes defined through __slots__ structure
        # and those hosted in  __dict__
        for _attrname,_attrvalue in (
            (_name,_val)
            for _name,_val in  _dict_iter_items(state)
            if _name not in ('_attrs','__dict__','__weakref__')
        ):
            setattr(self,_attrname,_attrvalue)

    @property
    def is_parent(self):
        return self.parent is not None

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
        if not _ahds_member_descriptor_base.establish_descriptor(self,attr):
            _oldval = self._attrs[attr]
            if isinstance(_oldval,Block) and _oldval.parent is self:
                _oldval.parent = None
        self._attrs[attr] = value
        if isinstance(value,Block):
            if isparent:
                self.parent = value
            elif isparent is not None:
                value.parent = self

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
        if not _ahds_member_descriptor_base.establish_descriptor(self,new_name,name):
            raise ValueError("'{}' attribute already defined for '{}' type object".format(new_name,self.__class__.__name__))
        self._attrs[new_name] = self._attrs[name]
        del self._attrs[name]

    def remove_attr(self,name):
        if not _ahds_member_descriptor_base.establish_descriptor(self,None,name):
           return
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
        string += '{}|  +<Parent>: {}\n'.format(prefix,self.parent.name) if self.parent else ''
        for attr in self._attrs:
            # check if the attribute is Block or non-Block
            if isinstance(self._attrs[attr], Block):
                # if it is a Block then the prefix will change by having extra '| ' before it
                # string += 'something\n'
                string += self._attrs[attr].__str__(prefix=prefix + "|  ",is_parent = self.parent == self._attrs[attr],printed=printed,name = attr)
            else:
                # if it is not a Block then we construct the repr. manually
                val = self._attrs[attr]
                # don't print the whole array for large arrays
                if isinstance(val, (np.ndarray,)):
                    # we construct a tuple for the first array element (0,...,0) and the last
                    # one (-1,...,-1); however, we have to do this independent of the dimensions
                    # we use a tuple constructed using shape - 1 in both cases
                    if self._attrs[attr].ndim <= 1 or sum( nelem > 1 for nelem in self._attrs[attr].shape ) > 1:
                        string += "{}|  +-{}: {}\n".format(prefix,attr, self._attrs[attr])
                    else:
                        start = tuple([0] * (len(val.shape) - 1))
                        end = tuple([-1] * (len(val.shape) - 1))
                        string += "{}|  +-{}: {},...,{}\n".format(prefix,attr, val[start], val[end])
                else:
                    string += "{}|  +-{}: {}\n".format(prefix,attr, self._attrs[attr])
        printed.remove(self)
        return string

    def __getitem__(self, index):
        if not isinstance(index,int):
            raise ValueError('index must be an integer or long')
        if self.name != 'Materials':
            raise NotImplementedError("'{}' type object instance is not Materials list".format(self.__class__.__name__))
        for _block in _dict_iter_values(self._attrs):
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
        return [
            _name
            for _name,_descriptor in (
                (_checkname,getattr(self.__class__,_checkname,None))
                for _checkname in super(Block,self).__dir__()
            )
            if not isinstance(_descriptor,_ahds_member_descriptor_base) or _name in self._attrs or _name in self.__dict__
        ]
                 

class ListBlock(Block):
    """Extension of Block which has an iterable attribute to which Block objects can be added"""
    __slots__ = ('_list',)

    def __init__(self, name, initial_len = 0,*args ,**kwargs):
        super(ListBlock, self).__init__(name,*args, **kwargs)
        self._list = list() if initial_len < 1 else [None] * initial_len # separate attribute for ease of management

    def items(self):
        return self._list

    @property
    def is_parent(self):
        """A ListBlock is a parent if it has a Block attribute or if it has list items"""
        # TODO: testcase
        if super(ListBlock, self).is_parent:
            return True
        else:
            if len(self._list) > 0:
                return True
            else:
                return False

    def __str__(self, prefix="", index=None,is_parent=False,printed = set(),name = None):
        """Convert the ListBlock into a string

        :param str prefix: prefix to signify depth in the tree
        :param int index: applies for list items [default: None]
        :returns str string: formatted string of attributes
        """
        # first we use the superclass to populate everything else
        string = super(ListBlock, self).__str__(prefix=prefix, index=index,is_parent=is_parent,printed=printed,name = name)
        # now we stringify the list-blocks
        for index, block in enumerate(self.items()):
            if block is None:
                if index > 0:
                    string += "{}+[{}]-{}\n".format(prefix + "|  ",index,block)
                continue
            string += block.__str__(prefix=prefix + "|  ", index=index,is_parent= block == self.parent,printed=printed)
        return string

    def __len__(self):
        return len(self._list)

    def __setitem__(self, key, value):
        if isinstance(key,slice):
            # raise value error if item in iterable is not a valid Block instance 
            # will only be called if below isinstance check fails
            def reject_iterable(item):
                raise ValueError('iterable may contain Block class/subclass instances only')

            rollback = self._list[:]
            try:
                self._list[key] = (( item for item in value if isinstance(item,Block) or reject_iterable(item)))
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

def _main():


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
    #ahds: block=block_test attribute=Dimension value=c"[3,5,6]"
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
    #ahds: block=block_test attribute=FlowerPower value=c"ahds.Block("FlowerPower")"
    #ahds: block=block_test.FlowerPower attribute=Dimension value=c"[3,5,6]"
    print("Fulldimension:",block_test.Dimension , block_test.FlowerPower.Dimension)
    a = block_test.FlowerPower.Dimension + 12
    
if __name__ == "__main__":
    _main()
        
