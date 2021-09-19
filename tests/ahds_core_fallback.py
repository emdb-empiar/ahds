class BlockMetaClassLink():
    """ dummy to be removed when python 2 support is abandoned """
    __slots__ = ()


def deprecated(description):
    """
    dummy decorator 
    """
    raise NotImplementedError("dummy deprecated decorator not collected") 

class ahds_member_descriptor(object):
    """
    dummy descriptor
    """
    __slots__ = ()
    def __new__(cls,blockinstance,name,oldname=None):
        """ dummy constructor """
        raise NotImplementedError("dummy ahds_member_descriptor class not collected")

class Block(BlockMetaClassLink):
    """ dummy block """
    __slots__ = ('name', '_attrs', 'parent', '__dict__', '__weakref__')
    def __init__(self, name):
        self.name = name
        self._attrs = {}
        self.parent = None

class ListBlock(Block):
    """ dummy list block """
    __slots__ = ('_list',)

    def __init__(self, name, initial_len = 0,*args ,**kwargs):
        super().__init__(name)
        self._list = list([None] * initial_len)

def read_only(name,copy=True,forceload=False):
    return "{}".format(name)
__builtins__["READONLY"] = read_only
