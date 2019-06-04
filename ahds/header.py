# -*- coding: utf-8 -*-
# header.py
"""
Module to convert parsed data from an Amira header into a set of nested objects. The key class is :py:class:``AmiraHeader``.

Usage:

::

    >>> from ahds.header import AmiraHeader
    >>> ah = AmiraHeader.from_file('<somfile>.am')
    >>> print ah

Each nested object is constructed from the :py:class:``Block`` class defined.

There are fife top-level attributes that every ``AmiraHeader`` will have:

*    designation

*    definitions

*    parameters

*    materials

*    data_pointers

All of them, exempt materials and parameters are marked deprecated and may be removed in
future. The designation and defintions attributes just return the reference to the AmiraHeader
instance which host all the attributes and data array declarations (definitions) found within
the AmiraMesh and HyperSurface files. The data_pointers attribute collects from each
attribute representing a valid array declaration the defined data definitions and returns the resulting
list. New code should directly access the Block objects describing the available data directly
from the corresponding array attribute of the AmiraHeader object. 

The blocks defining the available data structures extend the basic Block to the corresponding 
AmiraMeshDataStream and AmiraHxSurfaceDataStream blocks which allow to load and access the correspinding
data using the data property defined by theses blocks. The additional stream_data, encoded_data and
decoded_data attributes are deprecated and may be removed in future versions.

The attrs attribute of all Blocks and extended Block objects including AmiraHeader it self
which allows to query the attributes added during loading is deprecated and may be removed in future version.
To query which attributes are defined on each block use the builtin dir function instead. To 
access the defined attributes just use them liḱe any other static attribute.

The following attributes are moved from the designation attribute to the basic header block:
        
        *    filetype e.g. ``AmiraMesh`` or ``HyperSurface``
        *    dimensions e.g. ``3D``
        *    format e.g. ``BINARY-LITTLE-ENDIAN``
        *    version e.g. ``2.1``
        *    extra_format (if present)
        
:: 

    >>> print(ah.Nodes)
    print(ah.Nodes)
     +-Nodes: (<ahds.ahds_common.Block object at 0x7f5dc1a74d08>)
     |  |  +-Coordinates: (<ahds.data_stream.AmiraMeshDataStream object at 0x7f5dc1a97458>)
     |  |  |  +-block: 1
     |  |  |  +-array: Nodes(<ahds.ahds_common.Block object at 0x7f5dc1a74d08>)
     |  |  |  +-type: float
     |  |  |  +-dimension: 3
     |  +-dimension: 3154
    >>> print(ah.Tetrahedra.Nodes)
     +-Nodes: (<ahds.data_stream.AmiraMeshDataStream object at 0x7ffa3da25180>)
     |  +-type: int
     |  +-dimension: 4
     |  +-array: Tetrahedra(<ahds.ahds_common.Block object at 0x7ffa3da3a9c8>)
     |  |  |  +-Materials: (<ahds.data_stream.AmiraMeshDataStream object at 0x7ffa3da25118>)
     |  |  |  |  +-type: byte
     |  |  |  |  +-dimension: 1
     |  |  |  |  +-array: Tetrahedra(<ahds.ahds_common.Block object at 0x7ffa3da3a9c8>)
     |  |  |  |  +-block: 4
     |  |  +-Nodes: (<ahds.data_stream.AmiraMeshDataStream object at 0x7ffa3da25180>)
     |  |  +-dimension: 14488
     |  +-block: 3


The special array attribute indicates that the corresponding block is linked to a specific data array.
In the above examples to the Nodes structure defining the 3D coordenates of the corners of the Tetrahedra
and the Tetrahedra structure defining which nodes belong to which tetrahedron.
In the frist example only the block header is repeated to indicate the backreference in the second
example the full information is displayed for the parent array.

The dimensions attributes indicate the number of nodes on which the corresponding data is defined and the
dimension of the Coordinates block defines how many elements each entry has. By calling

    >>> print(ah.Nodes.Coordinates.data.shape)
    (3154, 3)

the corresponding data block is loaded and converted into a numpy array having the exact shape as
indicated by the two dimension attributes. The number of rows corresponds to the the dimension 
attribute of the Nodes Block and the number of columns is equal to the dimensions attribute.

    >>> ah.Nodes.Coordinates.data[:5,:]
    array([[ 0.09844301, -0.007811  , -0.0869359 ],
           [ 0.055759  ,  0.02217599,  0.093963  ],
           [ 0.1167009 ,  0.03151399, -0.0842569 ],
           [ 0.11912691,  0.03461899, -0.046145  ],
           [ 0.11671901,  0.028787  , -0.0340129 ]], dtype=float32)

The datatype of the array corresponds to the one indicated by the type attribute. The endianess of the
file is transparently handled during the loading of the data.


    >>> print ah.data_pointers.data_pointer_1
    data_pointer_1
    pointer_name: VERTEX
    data_format: None
    data_dimension: 3
    data_type: float
    data_name: VertexCoordinates
    data_index: 1
    data_length: None

Data pointers are identified by the name ``data_pointer_<n>`` where <n> is the number indicated by the
block attibute in the above examples.

The above approach can also be used to load Amira HyperSurface files.

    >>> ah = AmiraHeader.from_file('<somfile>.surf')

The restulting structure and behavior is the same as for AmiraMesh files.

    >>> print(ah)
    AMIRA HEADER (<somfile>.surf)
     +-path: <somepath>
     +-data section at: 355
    --------------------------------------------------
     +-parameters: (<ahds_common.Block object at 0x7efd1cc9ed48>)
     |  |  +-Materials: (<ahds_common.ListBlock object at 0x7efd1cfcc8b8>)
     |  |  |  +-Exterior2: []
     |  |  |  +-Exterior: (<ahds_common.Block object at 0x7efd1cfd5108>)
     |  |  |  |  +-Id: 1
     |  |  |  +-RA: (<ahds_common.Block object at 0x7efd1cfd5088>)
     |  |  |  |  +-Id: 2
     |  |  |  |  +-Color: [0.94902, 0.847059, 0.0901961]
     |  |  +-[0]=None
     |  |  +-[1]=(Exterior<ahds_common.Block object at 0x7efd1cfd5108>)
     |  |  +-[2]=(RA<ahds_common.Block object at 0x7efd1cfd5088>)
     |  |  +-length: 3
     |  +-BoundaryIds: "BoundaryConditions"(<ahds_common.Block object at 0x7efd1cfd5608>)
     |  |  |  +-IdList: (<ahds_common.ListBlock object at 0x7efd1cfcc870>)
     |  |  |  +-[0]=(Id0<ahds_common.Block object at 0x7efd1cc9e048>)
     |  |  |  +-length: 1
     |  |  |  +-Id0: (<ahds_common.Block object at 0x7efd1cc9e048>)
     |  |  |  |  +-Id: 0
     |  |  |  |  +-Info: "undefined"
    --------------------------------------------------
     +-RBloodAtrium.surf: (<__main__.AmiraHeader object at 0x7efd1cfb7b10>)
     |  +-extra_format: None
     |  +-filetype: HyperSurface
     |  +-version: 0.1
     |  +-dimension: None
     |  +-format: BINARY

Any HyperSurface file implicitly defines the following basic elements.

    * Parameters
    * Vertices
    * Patch<n>
    * PatchList

As there can be more than one Patch within the a HyperSuface file, for each additional Patch a
Patch<n> block is insereted into the header on accessing the corresponding data. The
PatcheList attribute allows to access all defined patches in their order as they are defined within
the file. Additionally the following attributes may be present and added when accessing them.

    * Surface<n>
    * SurfaceList
    * BoundaryCurve<n>
    * BoundaryCurveList
    * NBranchingPoints
    * NVerticesOnCurves

The Vertices contains the follwoing datastream
    * Coordinates

The Patch<n> contains the follwoing datastreams and attributes
    * InnerRegion
    * OuterRegion
    * BranchingPoints
    * Triangles

The Surface<n> contains the following datastream and attributes
    * Region
    * Patches

The BoundaryCurve<n> defindes teh followng data stream
    * Vertices

The NBranchingPoints and NVerticesOnCurves are repesented by value attributes of
the AmiraHeader Block.

"""
from __future__ import print_function

import functools as ft
import os.path as path
import re
import sys
from pprint import pprint

import numpy as np

# to use relative syntax make sure you have the package installed in a virtualenv in develop mode e.g. use
# pip install -e /path/to/folder/with/setup.py
# or
# python setup.py develop
from .core import _dict_iter_items, Block, deprecated, \
    ListBlock, REFACTOR
from .data_stream import StreamLoader, set_data_stream, set_stream_loader
# definition of numpy data types with dedicated endianess and number of bits
# they are used by the below lookup table
from .grammar import get_parsed_data

# empty arrays passed to _load_declarations and _load_definitions on creation
# of HyperSuface header. The commented elements may be used for debuging purposes
# in this case the elements with on # have to be present the ones with two are 
# optional. For all uncomented declarations all correpsonding definitions 
# indicated by the 'array_reference' field have to be uncommented too.
_hyper_surface_declarations = [
    # { 'array_name': "Vertices",'array_dimension':"0" }, #
    ##{ 'array_name': "NBranchingPoints",'array_dimension':1 }, ##
    ##{ 'array_name': "NVerticesOnCurves",'array_dimension':1 }, ##
    ##{ 'array_name': "BoundaryCurve1",'array_dimension':0 }, ##
    # { 'array_name': "Patch1",'array_dimension':0 }, #
    ##{ 'array_name': "Surface1",'array_dimension':0 }, ##
]

_hyper_surface_base_definitions = [
    # { 'array_reference': "Vertices",'data_dimension':3,'data_index':None,'data_name':"Coordinates",'data_type':'float' }, #
    ##{ 'array_reference': "BoundaryCurve1",'data_dimension':0,'data_index':None,'data_name':"Vertices",'data_type':'listitem' }, ##
    # { 'array_reference': "Patch1",'data_dimension':None,'data_index':None,'data_name':"InnerRegion",'data_type':'str' }, #
    # { 'array_reference': "Patch1",'data_dimension':None,'data_index':None,'data_name':"OuterRegion",'data_type':'str' }, #
    # { 'array_reference': "Patch1",'data_dimension':0,'data_index':None,'data_name':"BranchingPoints",'data_type':'int' }, #
    # { 'array_reference': "Patch1",'data_dimension':0,'data_index':None,'data_name':"BoundaryCurves",'data_type':'int' }, #
    # { 'array_reference': "Patch1",'data_dimension':0,'data_index':None,'data_name':"Triangles",'data_type':'int' }, #
    ##{ 'array_reference': "Surface1",'data_dimension':1,'data_index':None,'data_name':"Region",'data_type':'int' }, ##
    ##{ 'array_reference': "Surface1",'data_dimension':0,'data_index':None,'data_name':"Patches",'data_type':'int' } ##
]

# regular expression applied to names of array declarations and corresponding data definitions to identifiy
# whether they shall be joinded within an additional <commonname>List array attribute. 
_match_sibling = re.compile(r'^\d+')


class AmiraHeaderError(Exception):
    pass


class AmiraHeader(Block):
    """Class to encapsulate Amira metadata and accessors to amria data streams"""

    # __slots__ field is used to separate internal attributes from the dynamic attributes
    # representing the metadata and the accessors to the content of the data streams
    # which will be stored inside the __dict__ attribute of the Block base class
    if REFACTOR:
        __slots__ = (
        '_fn', '_parsed_data', '_stream_loader', '_header_length', '_file_format', '_parameters', '_load_streams', '_data_stream_count')
    else:
        __slots__ = (
            "_fn", "_parsed_data", "_stream_loader", "_parameters", "_materials", "_field_data_map", "_noload",
            "_array_data_rename", "_data_section_start"
        )

    if REFACTOR:
        def __init__(self, fn, load_streams=True, *args, **kwargs):
            """Construct an AmiraHeader object from parsed data"""
            self._fn = fn
            self._parsed_data, self._header_length, self._file_format = get_parsed_data(fn, *args, **kwargs)
            # introspect the stream loader to use
            self._stream_loader = set_stream_loader(self._file_format)
            pprint(self._parsed_data)
            # load the streams
            self._load_streams = load_streams
            # data stream count
            self._data_stream_count = None
            super(AmiraHeader, self).__init__(fn)
            # load the parse data into this object
            self._load()

    else:
        def __init__(self, parsed_data, fn):
            # for debuging purpose of linter issues parsed data and fn can be
            # set to None to create an emtyp AmiraHeader object
            if parsed_data is None and fn is None:
                super(AmiraHeader, self).__init__('')
                return
            # initialize the name of the AmiraHeader block to the base name of the
            # loaded file
            super(AmiraHeader, self).__init__(path.basename(fn))
            self._fn = fn
            # split the parsed_data into the meta data list and the byte index at which the
            # first data stream starts
            self._parsed_data, self._data_section_start = parsed_data
            self._field_data_map = dict()
            self._array_data_rename = dict()
            self._noload = 0
            # construct the metadata structure represented by this header and establish all
            # initial datastream accessors if possible
            self._load(self._data_section_start)

    @property
    def filename(self):
        return self._fn

    @property
    def stream_loader(self):
        return self._stream_loader

    @property
    def load_streams(self):
        return self._load_streams

    @property
    def data_stream_count(self):
        return self._data_stream_count

    @classmethod
    def from_file(cls, fn, *args, **kwargs):
        """Constructor to build an AmiraHeader object from a file
        
        :param str fn: Amira file
        :return ah: object of class ``AmiraHeader`` containing header metadata
        :rtype: ah: :py:class:`ahds.header.AmiraHeader`
        """
        data = get_parsed_data(fn, *args, **kwargs)
        pprint(data)
        return cls(data, fn)

    # def __getattribute__(self, name):
    #     """tries to load the quested attribute from the file if not already present in this header"""
    #     if name in ("filename", "path"):
    #         return super(AmiraHeader, self).__getattribute__("_fn")
    #     if name in ("raw_header",):
    #         return super(AmiraHeader, self).__getattribute__("_parsed_data")
    #     if name in ("designation", "definitions", "data_pointers"):
    #         return super(AmiraHeader, self).__getattribute__(name)()
    #     if name in ("parameters",):
    #         return super(AmiraHeader, self).__getattribute__("_" + name)
    #     try:
    #         return super(AmiraHeader, self).__getattribute__(name)
    #     except AttributeError as attributenotfound:
    #         if self._noload:
    #             # autoload is already off reraise AttributeError
    #             raise
    #         et, ev, eb = sys.exc_info()
    #         # turn off autoload to prevent infinite recursion and
    #         # try to load attribute from file
    #         self.autoload(False)
    #         try:
    #             self._stream_loader.load_stream(name)
    #         except DataStreamNotFoundError:
    #             raise attributenotfound
    #         finally:
    #             # turn on autoload again before reraising the error triggered by loader
    #             # or continuing
    #             self.autoload(True)
    #         # turn on autoload again and try to return the newly loaded attribute
    #         # from the __dict__ of the base class
    #         return super(AmiraHeader, self).__getattribute__(name)

    def autoload(self, on):
        """ 
        turn on or off automatic loading of attributes from the underlying file

        :param book on: Turn auto loading of data streams on (True) or off (False)
            NOTE:: repeated calls to autoload with on set to True accumulate and have to
                   be undone by calling with on = False before streams are again automatically
                   loaded 
        """
        if not on:
            self._noload += 1
            return
        elif self._noload < 1:
            return
        self._noload -= 1

    def __len__(self):
        if REFACTOR:
            return self._header_length
        else:
            return len(self._parsed_data)

    @staticmethod
    def flatten_dict(in_dict):
        block_data = dict()
        for block in in_dict:
            for block_keys0 in block.keys():
                block_data[block_keys0] = block[block_keys0]
                break
        return block_data

    if REFACTOR:
        def _load(self):
            # first flatten the dict
            block_data = self.flatten_dict(self._parsed_data)
            # load file designations
            self._load_designation(block_data['designation'])
            # load parameters
            if 'parameters' in block_data:
                self._parameters = self._load_parameters(block_data['parameters'], 'Parameters', parent=self)
            else:
                # just create an empty parameters block to keep header consistent
                self._parameters = Block('Parameters')
            # load array declarations
            self._load_declarations(block_data['array_declarations'])
            # load data stream definitions
            data_streams = self._load_definitions(block_data['data_definitions'])
            self._data_stream_count = len(data_streams)
            if self.load_streams:
                for ds in data_streams:
                    ds.read()
                    ds.add_attr('data', ds.data)


    else:
        def _load(self, _data_section_start):
            # disable automatic  loading of data streams while construction of header
            self.autoload(False)
            # first flatten the dict
            block_data = self.flatten_dict(self._parsed_data)
            if len(block_data) < 1:
                # empty non recognizeable header at least create structures for empty AmiraMesh header
                block_data['designation'] = {"filetype": "AmiraMesh"}
                block_data['array_declarations'] = {}
                block_data['data_definitions'] = {}

            self._load_designation(block_data['designation'])
            self._stream_loader = StreamLoader(self, _data_section_start, self._field_data_map)
            # if present load parameters section, it may be missing on Files describing vector fields only
            if 'parameters' in block_data:
                self._parameters = self._load_parameters(block_data['parameters'], 'Parameters', parent=self)
                # self._parameters = self._load_parameters(block_data['parameters'])
            else:
                # just create an empty parameters block to keep header consistent
                self._parameters = Block('Parameters')
            # """
            if 'materials' in block_data:
                # HyperSurface files may enconde Materials structure within a dedicate Materials section instead
                # of a subsection within the Parameters structure
                if not hasattr(self._parameters, 'Materials'):
                    # create Materias section within parameters block
                    self._parameters.add_attr('Materials', ListBlock("Materials"))
                # load dedicated materials section and insert it within the Materials section of the parameters block
                self._materials = self._load_parameters(block_data['materials'], 'materials',
                                                        self._parameters.Materials)
            # """
            #         self._load_date()
            # load declarations after parameters in case AmiraMesh file represents HxSpreadSheet.
            # in that case parameters contain ContentType and numRows attribute and for each column the labeling of the columns
            # which allows to collate array_declarations for spreadsheet into one listblock labeled and attach a data and a stream_data
            # attribute to ListBlock in case all columns have same data type.
            _finish = self._load_declarations(block_data['array_declarations'])
            self._load_definitions(block_data['data_definitions'])
            for _call in _finish:
                print('_call:', _call)
                _call()
            # enable automatic loading of data streams
            self.autoload(True)

    @property
    def parameters(self):
        return self._parameters

    @deprecated(" use header attributes version, dimension, fileformat, format and extra_format istead")
    def designation(self):
        """Designation of the Amira file defined in the first row
        
        Designations consist of some or all of the following data:
        
        *    filetype e.g. ``AmiraMesh`` or ``HyperSurface``
        
        *    dimensions e.g. ``3D``
        
        *    format e.g. ``BINARY-LITTLE-ENDIAN``
        
        *    version e.g. ``2.1``
        
        *    extra format e.g. ``<hxsurface>``

        NOTE: this property is deprecated use the corresponding attributes of the AmiraHeader
        instead to access the above informations
        """
        return self

    @deprecated(" use data array attributes instead eg. Vertices, Triangles, ...")
    def definitions(self):
        """Definitions consist of a key-value pair specified just after the 
        designation preceded by the key-word 'define'      

        NOTE: this property is deprecated access the corresponding attributes directly
        eg. ah.Nodes instead of ah.definitions.Nodes or ah.Tetrahedra instead of ah.defintions.Tetrahedra
        """
        return self

    @deprecated(" use data attributes of data arrays  instead eg. header.Vertices.Coordinates")
    def data_pointers(self):
        """The list of data pointers together with a name, data type, dimension, 
        index, format and length

        NOTE: deprecated access the data defnitions for each data array through the corresponding attributes
        eg.: ah.Nodes.Coordinates instead of ah.data_pointers.data_pointer_1 ah.Tetrahedra.Nodes instead of 
        ah.data_pointers.data_pointer_2 etc.
        """

        _data_pointers = Block("data_pointers")
        _i = 0
        for _idx, _data in _dict_iter_items(self._field_data_map):
            _data_pointers.add_attr("data_pointer_{}".format(_i), _data)
            _i += 1
        return _data_pointers

    def _load_designation(self, block_data):
        self.add_attr('filetype', block_data.get('filetype', None))
        self.add_attr('dimension', block_data.get('dimension', None))
        self.add_attr('format', block_data.get('format', None))
        self.add_attr('version', block_data.get('version', None))
        self.add_attr('extra_format', block_data.get('extra_format', None))

    def _check_siblings(self, block_obj, name, parent, listnameformat='{}List'):
        # check if the last characters in the name could resemble a valid counter
        # search reverse from tail of name any digit character
        _issibling = _match_sibling.match(name[::-1])
        if _issibling is None:
            # no counter found
            return
        # try to load an existing <commonname>List attribute from the specified parent Node
        if isinstance(parent, ListBlock):
            _list_name = parent.name
            _siblinglist = parent
        else:
            _list_name = listnameformat.format(name[:-_issibling.end()])
            _siblinglist = getattr(parent, _list_name, None)
            if _siblinglist is None:  # or isinstance(_siblinglist,_AnyBlockProxy):
                # create a new ListBlock allowing to access the attributes of the Parentblock by index
                _siblinglist = ListBlock(_list_name)
                parent.add_attr(_list_name, _siblinglist)
            elif not isinstance(_siblinglist, ListBlock):
                # an attribute with name of list exists but does not resemble a ListBlock
                raise AmiraHeaderError("conversion of Block({0}) to ListBlock({0}) not supported".format(_list_name))
        # insert new block in addition into the corresponding list
        _siblinglist[int(name[-_issibling.end():])] = block_obj

    if REFACTOR:
        def _load_parameters(self, block_data, name='Parameters', **kwargs):
            # treat materials specially (and possibly others in the future)
            if name in ["Materials"]:
                block = ListBlock(name)
                for param in block_data:
                    if isinstance(param['parameter_value'], list):
                        if len(param['parameter_value']) > 0:
                            if param['parameter_value'][0] == '<!?c?!>':
                                block.add_attr(param['parameter_name'], param['parameter_value'][1:])
                            else:
                                block.append(
                                    self._load_parameters(
                                        param['parameter_value'],
                                        name=param['parameter_name']
                                    )
                                )
                        else:
                            block.add_attr(param['parameter_name'], param['parameter_value'])
                    else:
                        block.add_attr(param['parameter_name'], param['parameter_value'])
            else:
                block = Block(name)
                for param in block_data:
                    if isinstance(param['parameter_value'], list):
                        if len(param['parameter_value']) > 0:
                            if param['parameter_value'][0] == '<!?c?!>':
                                block.add_attr(param['parameter_name'], param['parameter_value'][1:])
                            else:
                                block.add_attr(
                                    self._load_parameters(param['parameter_value'], name=param['parameter_name']))
                        else:
                            print(param['parameter_name'], type(param['parameter_name']))
                            block.add_attr(param['parameter_name'], param['parameter_value'])
                    else:
                        block.add_attr(param['parameter_name'], param['parameter_value'])
            return block

        def _load_declarations(self, block_data):
            """Load the array definition blocks which will contain the data streams"""
            for decl in block_data:
                block = Block(decl['array_name'])
                block.add_attr('length', decl['array_dimension'])
                self.add_attr(block)
            # fixme: remove empty tuple eventually
            return ()

        def _load_definitions(self, block_data):
            """We want to load data definitions to the appropriate array definition block"""
            data_streams = list()
            data_stream_indices = set()
            for defn in block_data:
                # check whether the array_ref is an attribute on self
                try:
                    parent = getattr(self, defn['array_reference'])
                except AttributeError:
                    parent = self
                # set the data streams
                block = set_data_stream(defn['data_name'], self)
                block.add_attr('data_index', defn['data_index'])
                # conditionally add the data stream if its index is unique e.g. Fields do not have unique ds
                if defn['data_index'] not in data_stream_indices:
                    data_streams.append(block)
                # keep track of the data stream indices
                data_stream_indices.add(defn['data_index'])
                block.add_attr('dimension', defn.get('data_dimension', 1))  # assume dimension of 1
                block.add_attr('type', defn['data_type'])
                block.add_attr('interpolation_method', defn.get('interpolation_method', None))
                block.add_attr('shape', parent.length)
                # insert this definition as an attribute
                parent.add_attr(block)
                # keep track of data streams
            return data_streams
    else:
        def _load_parameters(self, block_data, parameter_name="<unknown>", block_obj=None, parent=None):
            if type(block_data) not in [list, tuple]:
                # load terminal parameter values
                assert type(block_data) in [dict] and "parameter_name" in block_data and "parameter_value" in block_data
                if block_obj is None:
                    # create new Block object using the provided parameter_name, if block represents Materials Section
                    block_obj = Block(parameter_name) if parameter_name not in ['Materials'] else ListBlock(
                        parameter_name)
                    if parent is not None:
                        # check if parameter has already siblings in its parent
                        self._check_siblings(block_obj, parameter_name, parent)
                if type(block_data["parameter_value"]) not in (list, tuple):
                    # the parameter value is a plain scalar parameter or a dict defining additional parameter lists
                    if type(block_data["parameter_value"]) not in (dict,):
                        # insert scalar parameter
                        block_obj.add_attr(block_data["parameter_name"], block_data["parameter_value"])
                        return block_obj
                elif len(block_data["prarameter_value"]) < 1 or block_data["parameter_value"][0] == "<!?c?!>":
                    # parameter value is either empty list or a non scalar terminal list or tuple type parameter
                    # simply insert it into the current block
                    block_obj.add_attr(block_data["parameter_name"], block_data["parameter_value"][1:])
                    return block_obj
                # load the list of subparameters
                block_obj.add_attr(block_data["parameter_name"],
                                   self._load_parameters(block_data["parameter_value"], block_data["parameter_name"],
                                                         parent=block_obj))
                if parent is not None and isinstance(parent, ListBlock):
                    # check if current object has an Id field if use its Id to add it to the List part of its parent
                    _id_attr = getattr(block_obj, 'Id', None)
                    if _id_attr is not None and not isinstance(_id_attr, Block):
                        parent[int(_id_attr)] = block_obj
                return block_obj
            if block_obj is None:
                # create new Block object using the provided parameter_name, if block represents Materials Section
                block_obj = Block(parameter_name) if parameter_name not in ['Materials'] else ListBlock(parameter_name)
                if parent is not None:
                    # check if parameter has already siblings in its parent
                    self._check_siblings(block_obj, parameter_name, parent)
            for parameter in block_data:
                # ensure that parameter represents a valid dict describing parameterlist of current block
                assert type(parameter) in [dict] and "parameter_name" in parameter and "parameter_value" in parameter
                if type(parameter["parameter_value"]) not in (list, tuple):
                    # the parameter value is a plain scalar parameter or a dict defining additional parameter lists
                    if type(parameter["parameter_value"]) not in (dict,):
                        # insert scalar parameter
                        block_obj.add_attr(parameter["parameter_name"], parameter["parameter_value"])
                        continue
                elif len(parameter["parameter_value"]) < 1 or parameter["parameter_value"][0] == "<!?c?!>":
                    # parameter value is either empty list or a non scalar terminal list or tuple type parameter
                    # simply insert it into the current block
                    block_obj.add_attr(parameter["parameter_name"], parameter["parameter_value"][1:])
                    continue
                # load the list of subparameters
                block_obj.add_attr(parameter["parameter_name"],
                                   self._load_parameters(parameter["parameter_value"], parameter["parameter_name"],
                                                         parent=block_obj))
            # check if current object has an Id field if use its Id to add it to the List part of its parent
            if parent is not None and isinstance(parent, ListBlock):
                _id_attr = getattr(block_obj, 'Id', None)
                if _id_attr is not None and not isinstance(_id_attr, Block):
                    parent[int(_id_attr)] = block_obj
            return block_obj

        def _load_declarations(self, block_data):
            if len(block_data) < 1:
                if self.filetype != "HyperSurface":
                    raise AmiraHeaderError(
                        "no array declarations found for '{}' type file '{}'".format(self.filetype, self.path))
                block_data = _hyper_surface_declarations
            elif self.filetype == 'HyperSurface':
                raise ("array declarations found on file '{}' designated having '{}' file type".format(
                    self.path,
                    self.filetype)
                )
            # handle special content
            # content type is only presently used to process HxSpreadSheet
            _special_content = getattr(self._parameters, 'ContentType', None)
            _finish = tuple()
            # START CRYPTIC!!!
            # in order to make loading of streams as generic as possible the following section defines a number of
            # anon. functions to use
            if _special_content in ['HxSpreadSheet']:
                _numrows = getattr(self._parameters, 'numRows', None)
                if _numrows is not None:
                    _numrows = np.int64(_numrows)

                    def _flatten(name):
                        _counterat = _match_sibling.match(name[::-1])
                        return name if _counterat is None else name[:-_counterat.end()]

                    def _relabel(name, counter, formatter):
                        _column_label = getattr(self.parameters, "__ColumnName{:04d}".format(counter), None)
                        name = formatter.format(name, counter)
                        if _column_label is None:  # or isinstance(_column_label,_AnyBlockProxy):
                            return name, name
                        return name, _column_label

                    check_dimension_exists = lambda dim: np.all(np.int64(dim) == _numrows)
                    dimension_error_string = "array_dimension={} does not match number of rows ({}) in spreadsheet"
                    get_array_name = _flatten
                    create_array = lambda name: self._stream_loader.create_list_array(
                        name, kind='spreadsheet',
                        child_name='{}Sheet'.format(
                            name.strip('_ \t\r\n\f')
                        )
                    )
                    rename_array = _relabel
                    cleanup_array_names = lambda name, array: (
                        ft.partial(getattr, array, '{}Sheet'.format(name.strip('_ \t\r\n\f')), None),)
                else:
                    check_dimension_exists = lambda dim: True
                    dimension_error_string = AmiraHeaderError("strange")
                    get_array_name = lambda name: name
                    create_array = self._stream_loader.create_array
                    rename_array = lambda name, counter, formatter: (name, formatter.format(name, counter))
                    cleanup_array_names = lambda name, array: ()
            else:
                check_dimension_exists = lambda dim: True
                dimension_error_string = AmiraHeaderError("strange")
                get_array_name = lambda name: name
                create_array = self._stream_loader.create_array
                rename_array = lambda name, counter, formatter: (name, formatter.format(name, counter))
                cleanup_array_names = lambda name, array: ()
            # END CRYPTIC!!!
            _base_map = dict()
            # from this point we convert declarations into data references
            for declaration in block_data:
                # check to see whether the array declaration has the dimension else raise ValueError
                if not check_dimension_exists(declaration['array_dimension']):
                    raise ValueError(dimension_error_string.format(declaration['array_dimension']))
                # get the name of the array
                _array_name = get_array_name(declaration['array_name'])
                # get the attribute in self that is referred to
                _equalnamed = getattr(self, _array_name, None)
                # if the attribute exists
                if _equalnamed is not None:  # and not isinstance(_equalnamed,_AnyBlockProxy):
                    try:
                        # make sure the dimension in the array decl. and the attribute match else raise AmiraHeaderError
                        # np.all is because we might be comparing arrays??
                        if np.all(_equalnamed.dimension != declaration['array_dimension']):
                            raise AmiraHeaderError(
                                "either HxSpreadSheet with equal named columns of different length can't handle")
                        # check whether we have renamed it
                        _rename = self._array_data_rename.get(_array_name, None)
                        # if we haven't...
                        if _rename is None:
                            # create a CRYPTIC partial
                            self._array_data_rename[_array_name] = {
                                0: ft.partial(rename_array, formatter=(
                                    '{0:s}{1:05d}' if declaration['array_name'] == _array_name else '{0:s}')),
                            }
                        continue  # already defined if data has also equal names just renumber definitions
                    except AttributeError:
                        raise AmiraHeaderError("definition name colides with some static non block attribute")
                # _array_name = declaration['array_name']
                # create an array
                _block_obj = create_array(_array_name)  #
                self.add_attr(_array_name, _block_obj)
                _block_obj.add_attr('dimension', declaration['array_dimension'])
                self._check_siblings(_block_obj, _array_name, self)
                _base_map[_array_name] = declaration['array_name']
                _finish = _finish + cleanup_array_names(_array_name, _block_obj)
                if len(_array_name) > 0 and _array_name[0] in '_ \n\t\f\r':
                    # unhide arrays which start with '__' or '_' most likely these are arrays
                    # which encode HxSpreadSheet column arrays where each column has its own array
                    _finish = _finish + (
                        ft.partial(self.move_attr, to=_array_name.strip('_ \n\t\r\f'), name=_array_name),)
            return _finish

        def _load_definitions(self, block_data):
            if len(block_data) < 1:
                if self.filetype != "HyperSurface":
                    raise AmiraHeaderError(
                        "no data definitons found for '{}' type file '{}'".format(self.filetype, self.path))
                # load empty or debuging defintions for HyperSurface file
                block_data = _hyper_surface_base_definitions
            for data_definition in block_data:
                # deal with Field (I don't know what's special about Field though)
                if ('array_reference' in data_definition and
                        data_definition['array_reference'] == 'Field' and
                        "interpolation_method" in data_definition):
                    # Field annotation of another data definition which might not yet bee seen
                    _data_dimension = data_definition.get('data_dimension', 1)
                    _data_type = data_definition['data_type']
                    # check if the corresponding data definition has already been loaded
                    _block_index = int(data_definition['data_index']) if data_definition['data_index'] else \
                        data_definition['data_name']
                    _data_obj = self._field_data_map.get(_block_index, None)
                    if _data_obj is None:
                        # create a stub for the data definition to be completed later
                        _data_obj = self._stream_loader.create_stream("<FieldData>")
                        self._field_data_map[_block_index] = _data_obj
                        _data_obj.add_attr("type", _data_type)
                        _data_obj.add_attr("dimension", _data_dimension)
                        _data_obj.add_attr("block", _block_index)
                        _fields_list = Block("fields")
                        _data_obj.add_attr("fields", _fields_list)
                    elif _data_obj.type != _data_type or _data_obj.dimension != _data_dimension:
                        # datatype or data dimension specified for Field annotation does not match definition for underlying data
                        raise AmiraHeaderError(
                            "DataError: Field datatype '{}' and dimension={} do not match with other fields defined on same data array {}".format(
                                _data_type, _data_dimension, _data_obj.type_block_index
                            )
                        )
                    else:
                        # create list of fields defined for the specific data
                        _fields_list = getattr(_data_obj, "fields", None)
                        if _fields_list is None:
                            _fields_list = Block("fields")
                            _data_obj.add_attr("fields", _fields_list)
                    _field_obj = Block(data_definition['data_name'])
                    _fields_list.add_attr(data_definition['data_name'], _field_obj)
                    _field_obj.add_attr("interpolation", data_definition['interpolation_method'])
                    continue
                # _array_base is where we will stick the array
                _array_base = _match_sibling.match(data_definition['array_reference'][::-1])
                # print('array_reference:', data_definition['array_reference'])
                # print('_array_base:', _array_base)
                if _array_base is None:
                    _array_obj = getattr(self, data_definition['array_reference'], None)
                    # print('_array_obj:', _array_obj)
                else:
                    _array_base = data_definition['array_reference'][:-_array_base.end()]
                    _array_obj = getattr(self, _array_base, None)
                    if _array_obj is None or not isinstance(_array_obj, ListBlock):
                        _array_obj = getattr(self, data_definition['array_reference'], None)
                if _array_obj is None:
                    raise AmiraHeaderError(
                        "DataError: array_reference '{}' not found".format(data_definition['array_reference']))
                # assume data_dimension to be one if not explicitly specified and load corresponding data type
                _data_dimension = data_definition.get('data_dimension', 1)
                _data_type = data_definition['data_type']
                # check if a data definition stub has already been created by a preceeding Field definitions
                _block_index = int(data_definition['data_index']) if data_definition['data_index'] else data_definition[
                    'data_name']
                _data_obj = self._field_data_map.get(_block_index, None)
                print('_array_obj:', _array_obj)
                _relabel = self._array_data_rename.get(_array_obj.name, None)
                if _relabel is None:
                    _data_name = data_definition['data_name']
                    _data_label = _data_name
                else:
                    _counter = _relabel.get(data_definition['data_name'], -1) + 1
                    _data_name, _data_label = _relabel[0](data_definition['data_name'], _counter)
                    _relabel[data_definition['data_name']] = _counter
                # this is now where the stream is created
                if _data_obj is None:
                    print('_data_obj is None')
                    print('_array_obj:', _array_obj)
                    if _data_dimension is None:
                        _array_obj.add_attr(_data_name, None)
                        continue
                    # create the corresponding data stream object and set all corresponding attributes
                    print('a')
                    _data_obj = self._stream_loader.create_stream(_data_label, _array_obj)
                    print('b')
                    _data_obj.add_attr("type", _data_type)
                    _data_obj.add_attr("dimension", _data_dimension)
                    _data_obj.add_attr("block", _block_index)
                    self._field_data_map[_block_index] = _data_obj
                elif _data_obj.type != _data_type or _data_obj.dimension != _data_dimension:
                    # data_type or data_dimension does not match with the type or dimension specified by corresponding Field annotation
                    raise AmiraHeaderError(
                        "DataError: data definition stub ({0} [{1}]) created for block {4} by preceeding field definition not matching required datatype '{2}' and dimension={3}".format(
                            _data_type, _data_dimension, _data_obj.type, _data_obj.dimension, _block_index
                        )
                    )
                elif _data_obj.name != "<FieldData>":

                    # current definition would overwrite previous one
                    raise AmiraHeaderError(
                        "DataError: data for block {} ('{}') redefined to '{}'".format(
                            _block_index, _data_obj.name, _data_name + "({})".format(data_definition['data_name'])
                        )
                    )
                else:
                    # fill in appropriate name of data definiton
                    _data_obj.name = _data_label
                # fill the remaining attributes and link the object to its parent array
                _data_obj.add_attr("array", _array_obj, True)
                _array_obj.add_attr(_data_name, _data_obj)
                self._check_siblings(_data_obj, _data_name, _array_obj)
                if 'data_format' in data_definition:
                    _data_obj.add_attr('data_format', data_definition['data_format'])
                if 'data_length' in data_definition:
                    _data_obj.add_attr('data_length', data_definition['data_length'])

    def __repr__(self):
        if REFACTOR:
            return "AmiraHeader('{}')".format(self.filename)
        return "<AmiraHeader with {:,} bytes>".format(len(self))

    def __str__(self, prefix="", index=None):
        width = 140
        string = ''
        if REFACTOR:
            string += '*' * width + '\n'
            string += "AMIRA HEADER \n"
            string += "+-file: {}\n".format(self.filename)
            string += "+-header length: {}\n".format(len(self))
            string += "+-data streams: {}\n".format(self.data_stream_count)
            string += "+-streams loaded? {}\n".format(str(self.load_streams))
            string += "-" * width + "\n"
            string += "{}".format(self.parameters)
            string += "-" * width + "\n"
            string += super(AmiraHeader, self).__str__()
            string += "*" * width
        else:
            string += "*" * width + "\n"
            string += "AMIRA HEADER ({})\n".format(self.name)
            string += "+-path: {}\n".format(path.dirname(self._fn))
            string += "+-header size: {}\n".format(self._stream_loader.data_section_start)
            string += "-" * width + "\n"
            string += "{}".format(self.parameters) if self.parameters is not None else "+-parameters(<None>)"
            string += "-" * width + "\n"
            # string += "AmiraHeader\n"
            string += super(AmiraHeader, self).__str__()
            # string += "AmiraHeader\n"
            string += "*" * width
        return string


def main():
    try:
        fn = sys.argv[1]
    except IndexError:
        print("usage: ./{} <amira-fn>".format(__file__), file=sys.stderr)
        return 1

    h = AmiraHeader.from_file(fn, verbose=False)
    print(h)
    print(h.designation)
    if h.parameters is not None:
        print(h.parameters)
        print(h.parameters.attrs)
        if hasattr(h.parameters, "Materials"):
            print(h.parameters.Materials, type(h.parameters.Materials))
            print(h.parameters.Materials.attrs)
            print(h.parameters.Materials.Exterior)
            print(h.parameters.Materials.ids)
            print(h.parameters.Materials[1].attrs)
            for id_ in h.parameters.Materials.ids:
                print(h.parameters.Materials[id_])
                print("")

    print(h.designation)
    # pylint: disable=E1101
    print(h.data_pointers.attrs)
    # pylint: enable=E1101
    if hasattr(h, "Lattice"):
        print(h.Lattice.Data)

    return 0


if __name__ == "__main__":
    sys.exit(main())
