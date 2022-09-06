# -*- coding: utf-8 -*-
"""
header
======

Module to convert parsed data from an Amira (R) header into a set of nested objects.
The key class is :py:class:`ahds.header.AmiraHeader`.

Usage:

::

    >>> from ahds.header import AmiraHeader
    >>> ah = AmiraHeader('<somfile>.am')
    >>> print(ah)
    +-header                                                                                       AmiraHeader [is_parent? True ]
    |  +-filetype: AmiraMesh
    |  +-dimension: None
    |  +-format: BINARY
    |  +-endian: LITTLE
    |  +-version: 2.1
    |  +-extra_format: None
    |  +-Parameters                                                                                      Block [is_parent? True ]
    |  |  +-Materials                                                                                ListBlock [is_parent? True ]
    |  |  |  +[0]-Exterior                                                                               Block [is_parent? False]
    |  |  |  |  +-Id: 1
    |  |  |  +[1]-Inside                                                                                 Block [is_parent? False]
    |  |  |  |  +-Color: [0.64, 0, 0.8]
    |  |  |  |  +-Id: 2
    |  |  |  +[2]-Mitochondria                                                                           Block [is_parent? False]
    |  |  |  |  +-Id: 3
    |  |  |  |  +-Color: [0, 1, 0]
    |  |  |  +[3]-Mitochondria_                                                                          Block [is_parent? False]
    |  |  |  |  +-Id: 4
    |  |  |  |  +-Color: [1, 1, 0]
    |  |  |  +[4]-mitochondria__                                                                         Block [is_parent? False]
    |  |  |  |  +-Id: 5
    |  |  |  |  +-Color: [0, 0.125, 1]
    |  |  |  +[5]-NE                                                                                     Block [is_parent? False]
    |  |  |  |  +-Id: 6
    |  |  |  |  +-Color: [1, 0, 0]
    |  |  +-Content: 862x971x200 byte, uniform coordinates
    |  |  +-BoundingBox: [0, 13410.7, 0, 15108.4, 1121.45, 4221.01]
    |  |  +-CoordType: uniform
    |  +-Lattice                                                                                         Block [is_parent? False]
    |  |  +-length: [862 971 200]


Each nested object is constructed from the :py:class:``Block`` class defined in the `core` module.

There are five top-level attributes that every ``AmiraHeader`` will have:

* `designation`
* `definitions`
* `Parameters`
* `Materials`
* `data_pointers`

All of them, except `Materials` and `Parameters` are marked deprecated and may be removed in
future. The `designation` and `defintions` attributes just return the reference to the `AmiraHeader`
instance which host all the attributes and data array declarations (`definitions`) found within
the `AmiraMesh` and `HyperSurface` files. The `data_pointers` attribute collects from each
attribute representing a valid array declaration the defined data definitions and returns the resulting
list. New code should directly access the Block objects describing the available data directly
from the corresponding array attribute of the `AmiraHeader` object.

The blocks defining the available data structures extend the basic `Block` to the corresponding
`AmiraMeshDataStream` and `AmiraHxSurfaceDataStream` blocks which allow to load and access the correspinding
data using the `data` property defined by theses blocks. The additional `stream_data`, `encoded_data` and
`decoded_data` attributes are deprecated and may be removed in future versions.

The `attrs` attribute of all `Block` and subclass objects including `AmiraHeader` itself
which allows to query the attributes added during loading is deprecated and may be removed in future version.
To query which attributes are defined on each block use the builtin dir function instead. To
access the defined attributes just use them liḱe any other static attribute.

The following attributes are moved from the `designation` attribute to the basic `header` block:

* `filetype` e.g. ``AmiraMesh``, ``Avizo`` or ``HyperSurface``
* `dimension` e.g. ``3D``
* `format` e.g. ``BINARY-LITTLE-ENDIAN``
* `version` e.g. ``2.1``
* `extra_format`

Data pointers are identified by the name ``data_pointer_<n>`` where <n> is the number indicated by the
block attibute in the above examples.

The above approach can also be used to load Amira HyperSurface files.

    >>> ah = AmiraHeader('<somfile>.surf')
    +-header                                                                                       AmiraHeader [is_parent? False]
    |  +-filetype: HyperSurface
    |  +-dimension: None
    |  +-format: BINARY
    |  +-endian: BIG
    |  +-version: 0.1
    |  +-extra_format: None
    |  +-Parameters                                                                                      Block [is_parent? True ]
    |  |  +-Materials                                                                                ListBlock [is_parent? True ]
    |  |  |  +[0]-Exterior                                                                               Block [is_parent? False]
    |  |  |  |  +-Id: 1
    |  |  |  +[1]-Background                                                                             Block [is_parent? False]
    |  |  |  |  +-Id: 1
    |  |  |  |  +-Color: [1, 0, 0]
    |  |  |  +[2]-host_cell_2                                                                            Block [is_parent? False]
    |  |  |  |  +-Id: 2
    |  |  |  |  +-Color: [1, 1, 0.167]
    |  |  +-BoundaryIds                                                                                  Block [is_parent? False]
    |  |  |  +-Name: BoundaryConditions
    |  |  +-GridBox: [-1, 850, -1, 932, -1, 233]
    |  |  +-GridSize: [852, 934, 235]
    |  |  +-Filename: /Users/ubanan01/Desktop/cryo_Tomo_Polara/U2OS/08.04....

NOTE!!!
NEW DESCRIPTION OF THE FILE FORMAT:
https://assets.thermofisher.com/TFS-Assets/MSD/Product-Guides/user-guide-amira-software.pdf

"""
from __future__ import print_function

import sys
import numpy
import warnings

from .core import Block, deprecated, ListBlock
from .data_stream import set_data_stream
from .grammar import get_parsed_data


class AmiraHeader(Block):
    """Class to encapsulate Amira metadata and accessors to Amira (R) data streams"""

    # __slots__ field is used to separate internal attributes from the dynamic attributes
    # representing the metadata and the accessors to the content of the data streams
    # which will be stored inside the __dict__ attribute of the Block base class
    __slots__ = (
        '_fn', '_parsed_data', '_header_length', '_file_format', '_parameters', '_load_streams',
        '_data_stream_count')

    # fixme: load_streams should be False by default
    def __init__(self, fn, load_streams=True, *args, **kwargs):
        """Construct an AmiraHeader object from parsed data"""
        self._fn = fn
        self._literal_data, self._parsed_data, self._header_length, self._file_format = get_parsed_data(fn, *args,
                                                                                                        **kwargs)
        # load the streams
        self._load_streams = load_streams
        # data stream count
        self._data_stream_count = None
        super(AmiraHeader, self).__init__('header')
        # load the parse data into this object
        self._load()

    @classmethod
    @deprecated("Now you can directly create a header from the file name as AmiraHeader('file.am')")
    def from_file(cls, fn, *args, **kwargs):
        """Deprecated classmethod"""
        return cls(fn, *args, **kwargs)

    @property
    def filename(self):
        return self._fn

    @property
    def literal_data(self):
        return self._literal_data

    @property
    def parsed_data(self):
        return self._parsed_data

    # todo: change this to streams_loaded
    @property
    def load_streams(self):
        return self._load_streams

    # todo: change this to streams_loaded
    @load_streams.setter
    def load_streams(self, value):
        try:
            assert isinstance(value, bool)
        except AssertionError:
            raise TypeError("must be a bool")
        self._load_streams = value

    @property
    def data_stream_count(self):
        return self._data_stream_count

    def load(self):
        """Public loading method"""
        self._load()

    def __len__(self):
        return self._header_length

    @staticmethod
    def flatten_dict(in_dict):
        block_data = dict()
        for block in in_dict:
            for block_keys0 in block.keys():
                block_data[block_keys0] = block[block_keys0]
                break
        return block_data

    def _load(self):
        # first flatten the dict
        block_data = self.flatten_dict(self._parsed_data)
        # load file designations
        self._load_designation(block_data['designation'])
        # load parameters
        if 'parameters' in block_data:
            _parameters = self._load_parameters(block_data['parameters'], 'Parameters', parent=self)
        else:
            # just create an empty parameters block to keep header consistent
            _parameters = Block('Parameters')
        # if we have a Materials block in parameters we create a convenience dictionary for
        # accessing materials e.g. for patches
        if hasattr(_parameters, 'Materials'):
            material_dict = dict()
            for material in _parameters.Materials:
                material_dict[material.name] = material
            _parameters.Materials.material_dict = material_dict
        super(AmiraHeader, self).add_attr('Parameters', _parameters)
        # load array declarations
        self._load_declarations(block_data['array_declarations'])
        # load data stream definitions
        if self.filetype == "AmiraMesh":
            # a list of data streams
            self._data_streams_block_list = self._load_definitions(block_data['data_definitions'])
            self._data_stream_count = len(self._data_streams_block_list)
        elif self.filetype == "HyperSurface":
            # data_streams_list = self._locate_hx_streams()
            self._data_streams_block_list = []
            self._data_stream_count = 1
            if self.load_streams:
                block = set_data_stream('Data', self)
                block.read()

    @deprecated(" use header attributes version, dimension, fileformat, format and extra_format istead")
    def designation(self):
        """Designation of the Amira file defined in the first row
        
        Designations consist of some or all of the following data:
        
        * filetype e.g. ``AmiraMesh`` or ``HyperSurface``
        * dimensions e.g. ``3D``
        * format e.g. ``BINARY-LITTLE-ENDIAN``
        * version e.g. ``2.1``
        * extra format e.g. ``<hxsurface>``

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
        return _data_pointers

    def _load_designation(self, block_data):
        self.add_attr('filetype', block_data.get('filetype', None))
        self.add_attr('dimension', block_data.get('dimension', None))
        format = block_data.get('format')
        if format == 'BINARY':
            self.add_attr('format', format)
            self.add_attr('endian', 'BIG')
        elif format == 'ASCII':
            self.add_attr('format', format)
            self.add_attr('endian', None)
        elif format == 'BINARY-LITTLE-ENDIAN':
            self.add_attr('format', 'BINARY')
            self.add_attr('endian', 'LITTLE')
        else:
            raise ValueError(
                u'unsupported format {format}; kindly consider contacting the maintainer to include support. Thanks.'.format(
                    format=format))
        self.add_attr('version', block_data.get('version', None))
        self.add_attr('extra_format', block_data.get('extra_format', None))

    def _load_parameters(self, block_data, name='Parameters', **kwargs):
        # treat materials specially (and possibly others in the future)
        if name in ["Materials"]:
            block = ListBlock(name)
            for param in block_data:
                # a sequence of parameters
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
                # a string or number
                else:
                    block.add_attr(param['parameter_name'], param['parameter_value'])
        else:
            block = Block(name)
            for param in block_data:
                try:
                    if isinstance(param['parameter_value'], list):
                        if len(param['parameter_value']) > 0:
                            if param['parameter_value'][0] == '<!?c?!>':
                                block.add_attr(param['parameter_name'], param['parameter_value'][1:])
                            else:
                                block.add_attr(
                                    self._load_parameters(param['parameter_value'], name=param['parameter_name'],parent_block=block))
                        else:
                            # print(param['parameter_name'], type(param['parameter_name']))
                            block.add_attr(param['parameter_name'], param['parameter_value'])
                    else:
                        parameter_name = param['parameter_name']
                        if parameter_name == 'name':
                            parameter_value = param['parameter_value']
                            if parameter_value != name:
                                parent_block = kwargs.get('parent_block',None)
                                if isinstance(parent_block,Block):
                                    parent_block.add_attr(parameter_value,block)
                                else: # may be removed to silently ignore alias definitions on Parameters
                                    warnings.warn("Setting alias '{}' for block '{}' failed: No parent".format(parameter_value,name))
                                block.add_attr('@alias',parameter_value)
                        else:
                            block.add_attr(param['parameter_name'], param['parameter_value'])
                except KeyError:
                    print(u"Found odd parameter: {} = {}".format(list(param.keys())[0], param[list(param.keys())[0]]),
                          file=sys.stderr)
        return block

    def _load_declarations(self, block_data):
        """Load the array definition blocks which will contain the data streams"""
        for decl in block_data:
            block = Block(decl['array_name'])
            block.add_attr('length', decl['array_dimension'])
            self.add_attr(block)

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
            _shape = getattr(parent, 'length', None)
            if isinstance(_shape, numpy.ndarray):
                block.add_attr('shape', tuple(_shape.tolist()[::-1]))
            else:
                block.add_attr('shape', _shape)
            block.add_attr('format', defn.get('data_format', None))
            # insert this definition as an attribute
            # parent.add_attr(block)
            # keep track of data streams
        return data_streams

    def __repr__(self):
        return "AmiraHeader('{}')".format(self.filename)

