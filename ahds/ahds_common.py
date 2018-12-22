# -*- coding: utf-8 -*-
# ahds_common.py
""" Common data structures and utils used accross all submodules of ahds """

import sys
import functools as ft
import warnings
import inspect
import re


if sys.version_info[0] > 2:
    # All defnitions for Python3 and newer which differ from their counterparts in Python2.x


    def _doraise(v,b=None,t=None,cause = None):
        """ reraise passed exception attaching provided exceptoin as cause to it """    
        #pylint disable=E0001
        if cause is not None:
            e = v.with_traceback(b)
            raise e from cause
        raise v.with_traceback(b)
        #pylint enable=E0001

    class PropertyTriggeredAttributeError(Exception):
        """ Exception used to rewrite AttributeError exceptions by below mixed_property class
            Ensuring Attribute errors which occure during excecution of its fget,fset,fdel
            member are properly preserved while avoiding to trigger a call to __getattr__ of
            its owning class
        """
        pass

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

    #pylint: disable=E1101
    _dict_iter_values = dict.values

    _dict_iter_items = dict.items

    _dict_iter_keys = dict.keys
    #pylint: enable=E1101

else:
    # All defnitions for Python3 and newer which differ from their counterparts in Python2.x
    def _doraise(v,b=None,t=None,cause = None):
        """ reraise passed exception attaching provided exceptoin as cause to it """    
        if t is None:
            #pylint disable=E0001
            exec("""raise v.__class__, v""")
            #pylint enable=E0001
        if cause is not None:
            setattr(v,'cause',cause)
        #pylint disable=E0001
        exec("""raise t, v, b""")
        #pylint enable=E0001

    class PropertyTriggeredAttributeError(BaseException):
        """ Exception used to rewrite AttributeError exceptions by below mixed_property class
            Ensuring Attribute errors which occure during excecution of its fget,fset,fdel
            member are properly preserved while avoiding to trigger a call to __getattr__ of
            its owning class
        """
        pass

    def _decode_string(data):
        """ in python2.x no decoding is necessary thur just returns data without any change """
        return data

    # try to define xrange alias pointing to the builtin xrange
    try:
        xrange = __builtins__['xrange']
    except:
        xrange = getattr(__builtins__,'xrange',xrange)
    
    # define _dict_iter_values, _dict_iter_items, _dict_iter_keys aliases imported by the
    # other parts for dict.itervalues, dict.iteritems and dict.iterkeys
    #pylint: disable=E1101
    _dict_iter_values = dict.itervalues

    _dict_iter_items = dict.iteritems

    _dict_iter_keys = dict.iterkeys
    #pylint: enable=E1101

class mixed_property(property):
    """ property decorator which rewrites any AttributeError exception occuring during
        a call to fget, fstet or fdel members to PropertyTriggeredAttributeError. Thereby
        it ensures that the captured AttributeError does not trigger a call to __getattr__
        member of its enclosing class while ensuring that it is still reconizeable as 
        AttributeError """

    def __init__(self,fget = None,fset = None, fdel = None, doc = None):
        """ see:: @property decorator class documentation """
        super(mixed_property,self).__init__(fget,fset,fdel,doc)

    def __get__(self,obj,objtype = None):
        """ modified version of the __get__ member of @property decorator class """
        if obj is None:
            return self
        if self.fget is None:
            raise AttributeError("unreadable attribute")
        try:
            return self.fget(obj)
        except AttributeError:
            et,ev,eb = sys.exc_info()
            ev = PropertyTriggeredAttributeError(ev)
            _doraise(ev,eb,PropertyTriggeredAttributeError)

    
    def __set__(self,obj,value):
        """ modified version of the __set__ member of @property decorator class """
        if self.fset is None:
            raise AttributeError("can't set attribute")
        try:
            self.fset(obj,value)
        except AttributeError:
            et,ev,eb = sys.exc_info()
            ev = RuntimeError(ev)
            _doraise(ev,eb,RuntimeError)

    
    def __delete__(self,obj):
        """ modified version of the __delete__ member of @property decorator class """
        if self.fdel is None:
            raise AttributeError("can't delete attribute")
        try:
            self.fdel(obj)
        except Exception:
            et,ev,eb = sys.exc_info()
            if isinstance(ev,AttributeError):
                et = RuntimeError
                ev = et(ev)
            _doraise(ev,eb,et)

class _deprecated_prop(property):
    """ @property derived decorator class used by the @deprecated decorator method
        below to issue a DeprecationWarning message when the decorated property is
        accessed 
        :param fget: see:: @property decorator
        :param fset: see:: @property decorator
        :param fdel: see:: @property decorator
        :param decorator:: decorator the fset, fget and fdel functions passed to
            setter, getter and deleter methods have to be decorated with"""
    def __init__(self,fget = None,fset = None, fdel = None, doc = None,decorator = None):
        super(_deprecated_prop,self).__init__(fget,fset,fdel,doc)
        # store the decorator method the passed fset and fdel methods should wrapped
        # before passed on to the @property decorator getter, setter deleter methods
        self._decorator = decorator

    def decorator(self):
        return self._decorator

    def getter(self,fget):
        """ see:: @property decorator """
        _newprop = super(_deprecated_prop,self).getter(self._decorator(fget))
        _newprop._decorator = self._decorator
        return _newprop

    def setter(self,fset):
        """ see:: @property decorator """
        _newprop =  super(_deprecated_prop,self).setter(self._decorator(fset))
        _newprop._decorator = self._decorator
        return _newprop

    def deleter(self,fdel):
        """ see:: @property decorator """
        _newprop = super(_deprecated_prop,self).deleter(self._decorator(fdel))
        _newprop._decorator = self._decorator
        return _newprop

class _deprecated_mixed_prop(mixed_property):
    """ same as _deprecated_prop excempt that it wraps @mixed_property decorator instead of
        @property decorator """

    def __init__(self,fget = None,fset = None, fdel = None, doc = None,decorator = None):
        super(_deprecated_mixed_prop,self).__init__(fget,fset,fdel,doc)
        self._decorator = decorator

    def decorator(self):
        return self._decorator

    def getter(self,fget):
        _newprop = super(_deprecated_mixed_prop,self).getter(self._decorator(fget))
        _newprop._decorator = self._decorator
        return _newprop

    def setter(self,fset):
        _newprop = super(_deprecated_mixed_prop,self).setter(self._decorator(fset))
        _newprop._decorator = self._decorator
        return _newprop

    def deleter(self,fdel):
        _newprop = super(_deprecated_mixed_prop,self).deleter(self._decorator(fdel))
        _newprop._decorator = self._decorator
        return _newprop

    

def deprecated(description=None,setter = None,deleter = None):
    """ decorator used to mark methods, classes, classmethods and properies as deprecated
        :param str description: the additional information printed along with the DeprecationWarning
        :param bool setter: flag indicating that deprecation warning should only affect @<property>.setter.
            is ignored if decorator is not applied to @<property>.setter decorator
        :param bool deleter: flag indicating that deprecation warning should only affect @<property>.deleter.
            is ignored if decorator is not applied to @<property>.deleter decorator

        NOTE: If applied to @proerty decorator definig getter of <property> than DeprecationWarning will be
            issued on setter and deleter implicity stating that the whole property is deprecated. If
            applied to setter or deleter only whith corresponding flags set to True will limit DeprecationWarning
            to setter or deleter only. Setting both flags to True at the same time will trigger a ValueError
            exception
    """

    # check if description prarameter is set and whether it is a valid string
    if description is None:
        # no addtional message just print a '!' at the end of the basic DeprecationWarning
        # message
        description = '!'
        _func = None
    elif isinstance(description,(type(b''),type(r''),type(''))):
        # extend the description such that it can be appended to the DeprecationWarning separating
        # it from the latter by ': '
        description = ': {}'.format(description)
        _func = None
    else:
        # description is likely the decorated entity it self gehave like a simple decorator
        _func = description
        description = ''
    def deprecated_decorator(func,msg=None):
        _deprecated_message = '<!?!>'
        _message_filter = '<!?!>'
        @ft.wraps(func)
        def decorated_deprecated(*args,**kwargs):
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
            _selffname = ( _selfframe.f_globals['__name__'][:-3] if _selfframe.f_globals['__name__'][-3:].lower() == '.py' else _selfframe.f_globals['__name__'] ) if '__name__' in _selfframe.f_globals else "<string>"
            _fname = _selffname
            while _select_level < len(_callstack):
                _caller = _callstack[_select_level]
                _callerframe = _caller.frame
                _fname = ( _callerframe.f_globals['__name__'][:-3] if _callerframe.f_globals['__name__'][-3:].lower() == '.py' else _callerframe.f_globals['__name__'] ) if '__name__' in _callerframe.f_globals else "<string>"
                if _fname != _selffname:
                    break
                _select_level += 1
            
            # define filter ensuring warning for func is issued only onece per module and file it is called
            warnings.filterwarnings('module',message =  _message_filter,category=DeprecationWarning,module = _fname)
            warnings.warn(
               _deprecated_message,
                category=DeprecationWarning,
                stacklevel = _select_level + 1
            )
            return func(*args,**kwargs)
        if msg is not None:
            # recalled by _deprecated_prop or _deprecated_mixed_prop setter, getter or deleter methods 
            # to wrap the new fset, fget or fdel method or by the below code to define the initial getter
            # if appied to the @property @mixed_property decorators
            _deprecated_message = msg.format(func.__qualname__,description)
            _message_filter = re.escape(msg.format(func.__qualname__,r''))
        elif inspect.isclass(func):
            # issue DeprecationWarning specific to class object and its instances
            _deprecated_message = "Class '{}' is deprecated{}".format(func.__qualname__,description)
            _message_filter = re.escape(r"Class '{}' is deprecated".format(func.__qualname__))
        elif inspect.isdatadescriptor(func) or isinstance(func,property):
            # issue deprecation warning for property or property alike
            if isinstance(func,mixed_property):
                _proptype = _deprecated_mixed_prop
            elif isinstance(func,property):
                _proptype = _deprecated_prop
            else:
                _proptype = type(func)
            _decorator = None
            if isinstance(func,_deprecated_prop) or isinstance(func,_deprecated_mixed_prop):
                # preserve decorator of _deprecated_prop and _deprecated_mixed_prop 
                # as the whole property is deprecated and therefore no setter or delter specific
                # messages are to be printed
                if func.decorator() is not None:
                    if isinstance(func.decorator(),ft.partial):
                        if func.decorator().func == deprecated_decorator:
                            _decorator = func.decorator()
                    elif func.decorator() == deprecated_decorator:
                         _decorator = func.decorator()
            if deleter: 
                if func.fdel is None:
                    raise ValueError("property deleter not set")
                if setter:
                    raise ValueError("setter and deleter decorator attribute are mutual exclusive")
                if isinstance(func.fdel,ft.partial):
                    if func.fdel.func == deprecated_decorator or func.fdel.func == decorated_deprecated:
                        # fdel is already marked deprecated no need to decorated it again    
                        # return func with out any change
                        return func
                elif func.fdel == deprecated_decorator or func.fdel == decorated_deprecated:
                    # fdel is already marked deprecated no need to decorated it again    
                    # return func with out any change
                    return func
                # create deprecation waring specific to <property>.deleter only
                _depmsg = "Property deleter '{}' is deprecated{}"
                return _proptype(
                    fget = func.fget,
                    fset = func.fset,
                    fdel = deprecated_decorator(func.fdel,_depmsg),
                    doc = func.__doc__,
                    decorator = _decorator
                )
            if setter:
                if func.fset is None:
                    raise ValueError("property setter is not set")
                if func.fset == decorated_deprecated or func.fset == deprecated_decorator:
                    # fset is already marked deprecated no need to decorated it again    
                    # return func with out any change
                    return func
                if isinstance(func.fset,ft.partial):
                    if func.fset.func == deprecated_decorator or func.fset.func == decorated_deprecated:
                        # fset is already marked deprecated no need to decorated it again    
                        # return func with out any change
                        return func
                _depmsg = "Property setter '{}' is deprecated{}"
                # create deprecation waring specific to <property>.setter only
                return _proptype(
                    fget = func.fget,
                    fset = deprecated_decorator(func.fset,_depmsg),
                    fdel = func.fdel,
                    doc = func.__doc__,
                    decorator = _decorator
                )
            if isinstance(func.fget,ft.partial):
                if func.fget.func == deprecated_decorator or func.fget.func == decorated_deprecated:
                    return func
            elif func.fget == deprecated_decorator or func.fget == decorated_deprecated:
                return func
            _depmsg = "Property '{}' is deprecated{}"
            return _proptype(
                fget = deprecated_decorator(func.fget,_depmsg),
                fset = deprecated_decorator(func.fset,_depmsg) if func.fset is not None else None,
                fdel = deprecated_decorator(func.fdel,_depmsg) if func.fdel is not None else None,
                doc = func.__doc__,
                decorator = ft.partial(deprecated_decorator,msg =  _depmsg)
            )
        elif inspect.ismethod(func):
            # func is a staticmethod or a classmethod or a classmember issue related DeprecationWarning
            _deprecated_message = "Method '{}' is deprecated{}".format(func.__qualname__,description)
            _message_filter = re.escape(r"Method '{}' is deprecated".format(func.__qualname__))
        elif inspect.isfunction(func):
            # func is a function issue related DeprecationWarning
            _deprecated_message = "Function '{}' is deprecated{}".format(func.__qualname__,description)
            _message_filter = re.escape(r"Function '{}' is deprecated".format(func.__qualname__))
        else:
            # func is none of the above entities issue a general DeprecationWarning stating that it's use
            # is deprecated
            _deprecated_message = "Use of '{}' is deprecated{}".format(func.__qualname__,description)
            _message_filter = re.escape(r"Use of '{}' is deprecated".format(func.__qualname__))
        # return function wrapping the decorated item
        return decorated_deprecated
    if _func is None:
        # called with description, setter or getter attribute set return decorating method
        return deprecated_decorator
    # called with the item to be decorated as first parameter decorate it
    return deprecated_decorator(_func)


class Block(object):
    """Generic block to be loaded with attributes"""
    def __init__(self, name):
        self.name = name
        
    __slots__ = ( "name","__dict__","__weakref__" )

    def add_attr(self, name, value):
        """Add an attribute to an ``Block`` object"""
        setattr(self, name, value)

    def move_attr(self,to,name):
        _tomove = getattr(self,name,None)
        if _tomove is None or isinstance(_tomove,_AnyBlockProxy):
            raise AttributeError("can not move missing attribute '{}' ".format(name))
        if isinstance(_tomove,Block) and _tomove.name == name:
            _tomove.name = to
        setattr(self,to,_tomove)
        delattr(self,name)

    @deprecated("user dir(<Block object>) instead")
    @mixed_property
    def attrs(self):
        return [ _attr for _attr in self.__dict__ ]

    def _make_proxy_or_attributeerror(self,name,more_alife = False):
        if name == 'name' or len(self.__dict__) > 0 or getattr(self,'name',None) is not None or more_alife:
            raise AttributeError("-{} instance has not attributes '{}'".format(self.__class__.__name__,name))
        return _AnyBlockProxy(name) if not isinstance(self,_AnyBlockProxy) else self

    def __getattr__(self,name):
        try:
            return self.__dict__[name]
        except KeyError:
            return self._make_proxy_or_attributeerror(name)
        
    _recurse = {}
    def __str__(self):
        if self in self.__class__._recurse and isinstance(self.__class__._recurse[self],str):
            # content of block is printed as backreference of child block prepend headerline by string
            # specified by _recurse entry and shorten indent by one level
            indent = " | " * ( len(Block._recurse) - 1)
            string = "{} +-{}: {}(<{}.{} object at {}>)\n".format(indent,self.__class__._recurse[self],self.name,self.__module__,self.__class__.__name__,hex(id(self)))
        else:
            # content of block is brinted in its normal hirarchical order 
            indent = " | " * len(Block._recurse)
            string = "{} +-{}: (<{}.{} object at {}>)\n".format(indent,self.name,self.__module__,self.__class__.__name__,hex(id(self)))
        # mark block as printed to prevent infinite back reference loops
        self.__class__._recurse[self] = True
        indent += " | "
        for _attr,_attrval in _dict_iter_items(self.__dict__):
            if isinstance(_attrval, Block):
                if _attrval in Block._recurse:
                    # print back reference line prefixed by <_attr>: or <_addr>: <_attrval.name> if _attr and _attrvale.name
                    # differt
                    if _attr != _attrval.name:
                        string += "{} +-{}: {}(<{}.{} object at {}>)\n".format(indent,_attr,_attrval.name,_attrval.__module__,_attrval.__class__.__name__,hex(id(_attrval)))
                    else:
                        string += "{} +-{}: (<{}.{} object at {}>)\n".format(indent,_attr,_attrval.__module__,_attrval.__class__.__name__,hex(id(_attrval)))
                else:
                    if _attr != _attrval.name:
                        self.__class__._recurse[_attrval] = _attr
                    string += "{}".format(_attrval)
            else:
                string += "{} +-{}: {}\n".format(indent,_attr, _attrval)
        del self.__class__._recurse[self]
        return string
    
    @deprecated("use indexer of Materials node instead to access materials by their id")
    @mixed_property
    def ids(self):
        """Convenience method to get the ids for Materials present"""
        assert self.name == "Materials"
        ids = list()
        for _attr,_attrval in _dict_iter_items(self.__dict__):
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
            if hasattr(_val,'Id') and int(_val.Id) == index
        ):
            return _attrval
        return None

class ListBlock(Block):
    """Generic block defining List of Blocks. Indexed and named attributes may be mixed allowing to acces 
       named attributes in order of their definition or any other indexing rule """
    __slots__ = ("_list",)
    def __init__(self,name):
        super(ListBlock,self).__init__(name)
        self._list = tuple() 


    def _make_proxy_or_attributeerror(self,name,more_alife = False):
        return super(ListBlock,self)._make_proxy_or_attributeerror(
            name,
            self._list is None or len(self._list) > 0 or more_alife
        )

    def __setitem__(self,index,value):
        """ set the item with given index to specified value
            :param int index: the index to be set
            :param value: the new value
        """
        if index >= len(self._list):
            self._list = self._list + ( (None,) * ( index  - len(self._list) ) ) + (value,)
            return
        self._list = self._list[:index] + (value,) + self._list[index+1:]

    def __getitem__(self,index):
        """ return the value indicated by the provided index """
        if index < 0:
            if index < -len(self._list):
                if len(self._list) < 1 and len(self.__dict__) < 1:
                    return _AnyBlockProxy(str(index)) if not isinstance(self,_AnyBlockProxy) else self
                raise IndexError("invalid index {}".format(index))
            index = len(self._list) - index
        elif index >= len(self._list):
            if len(self._list) < 1 and len(self.__dict__) < 1:
                return _AnyBlockProxy(str(index)) if not isinstance(self,_AnyBlockProxy) else self
            raise IndexError("invalid index {}".format(index))
        return self._list[index]

    def __str__(self):
        """ print string representation of ListBlock, if the len(<ListBlock>) > 10 than 
            five head elements and five elements from the tail of the list are printed
        """
        string = super(ListBlock,self).__str__()
        indent = " | " * len(Block._recurse)
        if self in Block._recurse or self._list is None:
            return string
        Block._recurse[self] = True
        indent += " | "
        _count = 0
        _idx = -1
        for _count,_entry,_idx in (
            (_count + 1,_ent,_entid)
            for _ent,_entid in (
                (self._list[_entid],_entid)
                for _entid in xrange(len(self._list))
            )
            if _ent is not None
        ):
            if isinstance(_entry, Block):
                string += "{} +-[{}]=({}<{}.{} object at {}>)\n".format(indent,_idx,_entry.name,_entry.__module__,_entry.__class__.__name__,hex(id(_entry)))
            else:
                string += "{} +-[{}]={}\n".format(indent,_idx, _entry)
            if _count > 4:
                break
        _back = _idx + 1
        _count = 0
        for _back,_count in (
            ( _bk,_count + 1 )
            for _bk in xrange(len(self._list)-1,0,-1)
            if self._list[_bk] is not None and _bk > _idx
        ):
            if _count > 4:
                break
        if _back > _idx + 1:
            string += "{} + ...: ... \n"
            
        for _idx,_entry in (
            (_entid,_ent)
            for _entid,_ent in (
                (_entidx,self._list[_entidx])
                for _entidx in xrange(_back,len(self._list))
            ) if _ent is not None
        ):
            if isinstance(_entry, Block):
                _entry = self._list[_idx]
                string += "{} +-[{}]=({}<{}.{} object at {}>)\n".format(indent,_idx,_entry.name,_entry.__module__,_entry.__class__.__name__,hex(id(_entry)))
            else:
                string += "{} +-[{}]={}\n".format(indent,_idx, _entry)
        string += "{} +-length: {}\n".format(indent,len(self._list))
        del Block._recurse[self]
        return string

    def __len__(self):
        return len(self._list)

    def __iter__(self):
        """ list iterator """
        for _item in self._list:
            yield _item

    def __contains__(self,item):
        return item in self._list

class _AnyBlockProxy(Block):
    """ dummy block returned by __getattr__ method of Block in case
        its __dict__ is emtpy and by ListBlock if both __dict__ and _list are emtpy
        it tries to mimic any type the accessing code might expect from attributes
        and items defined by the loaded AmiraMesh and HyperSurface files 
    """

    __slots__ = tuple()
    def __init__(self,name):
        super(_AnyBlockProxy,self).__init__(name)
    
    def add_attr(self,name,value):
        pass

    def __setattr__(self,name,value):
        pass

    def __getattr__(self,name):
        return self

    def __getitem__(self,index):
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

    def __add__(self,other):
        return other

    def __sub__(self,other):
        return -other

    def __mul__(self,other):
        return 0

    def __floordiv__(self,other):
        return 0

    def  __divmod__(self,other):
        return 0

    def __div__ (self,other):
        return 0

    def __truediv__(self,other):
        return 0

    def __mod__(self,other):
        return 0

    def __pow__(self,other):
        return 0

    def __lshift__(self,other):
        return 0

    def __rshift__(self,other):
        return 0

    def __and__(self,other):
        return 0

    def __xor__(self,other):
        return other

    def __iadd__(self,other):
        return other

    def __isub__(self,other):
        return -other

    def __imul__(self,other):
        return 0

    def __ifloordiv__(self,other):
        return 0

    def  __idivmod__(self,other):
        return 0

    def __idiv__ (self,other):
        return 0

    def __itruediv__(self,other):
        return 0

    def __imod__(self,other):
        return 0

    def __ipow__(self,other):
        return 0

    def __ilshift__(self,other):
        return 0

    def __irshift__(self,other):
        return 0

    def __iand__(self,other):
        return 0

    def __ixor__(self,other):
        return other

    def __radd__(self,other):
        return other

    def __rsub__(self,other):
        return -other

    def __rmul__(self,other):
        return 0

    def __rfloordiv__(self,other):
        return 0

    def  __rdivmod__(self,other):
        return 0

    def __rdiv__ (self,other):
        return 0

    def __rtruediv__(self,other):
        return 0

    def __rmod__(self,other):
        return 0

    def __rpow__(self,other):
        return 0

    def __rlshift__(self,other):
        return 0

    def __rrshift__(self,other):
        return 0

    def __rand__(self,other):
        return 0

    def __rxor__(self,other):
        return other


    def __neg__(self):
        return 0

    def __pos__(self):
        return 0

    def __abs__(self):
        return 0

    def __invert__(self):
        return 0

    def __lt__(self,other):
        return False

    def __le__(self,other):
        return False

    def __eq__(self,other):
        return False

    def __ne__(self,other):
        return False

    def __ge__(self,other):
        return False

    def __gt__(self,other):
        return False

    def __cmp__(self,other):
        return 0

    def __nonzero__(self):
        return False

    def __contains__(self):
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
