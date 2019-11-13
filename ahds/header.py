# -*- coding: utf-8 -*-
# header.py
"""
Module to convert parsed data from an Amira (R) header into a set of nested objects. The key class is :py:class:`ahds.header.AmiraHeader`.

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


NOTE!!!
NEW DESCRIPTION OF THE FILE FORMAT:
https://assets.thermofisher.com/TFS-Assets/MSD/Product-Guides/user-guide-amira-software.pdf

"""
from __future__ import print_function

import sys

from .core import Block, deprecated, ListBlock
from .data_stream import set_data_stream
from .grammar import get_parsed_data


class AmiraHeader(Block):
    """Class to encapsulate Amira metadata and accessors to amria data streams"""

    # __slots__ field is used to separate internal attributes from the dynamic attributes
    # representing the metadata and the accessors to the content of the data streams
    # which will be stored inside the __dict__ attribute of the Block base class
    __slots__ = (
        '_fn', '_parsed_data', '_header_length', '_file_format', '_parameters', '_load_streams',
        '_data_stream_count')

    def __init__(self, fn, load_streams=True, *args, **kwargs):
        """Construct an AmiraHeader object from parsed data"""
        self._fn = fn
        self._literal_data, self._parsed_data, self._header_length, self._file_format = get_parsed_data(fn, *args,
                                                                                                        **kwargs)
        # load the streams
        self._load_streams = load_streams
        # data stream count
        self._data_stream_count = None
        # super(AmiraHeader, self).__init__(fn)
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

    @property
    def load_streams(self):
        return self._load_streams

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
            # if self.load_streams:
            #     for ds in data_streams_list:
            #         ds.read()
            #         ds.add_attr('data', ds.data())
        elif self.filetype == "HyperSurface":
            # data_streams_list = self._locate_hx_streams()
            self._data_streams_block_list = []
            self._data_stream_count = 1
            if self.load_streams:
                block = set_data_stream('Data', self)
                block.read()
                # self.add_attr(block)

    # @property
    # def Parameters(self):
    #     return self._parameters

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
        # _i = 0
        # for _idx, _data in _dict_iter_items(self._field_data_map):
        #     _data_pointers.add_attr("data_pointer_{}".format(_i), _data)
        #     _i += 1
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
        # self.add_attr('format', block_data.get('format', None))
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
                                    self._load_parameters(param['parameter_value'], name=param['parameter_name']))
                        else:
                            # print(param['parameter_name'], type(param['parameter_name']))
                            block.add_attr(param['parameter_name'], param['parameter_value'])
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
            block.add_attr('shape', getattr(parent, 'length', None))
            block.add_attr('format', defn.get('data_format', None))
            # insert this definition as an attribute
            # parent.add_attr(block)
            # keep track of data streams
        return data_streams

    def __repr__(self):
        return "AmiraHeader('{}')".format(self.filename)

    # def __str__(self, prefix="", index=None):
    #     width = 140
    #     string = ''
    # string += '*' * width + '\n'
    # string += "AMIRA HEADER \n"
    # string += "-" * width + "\n"
    # string += "+-file: {}\n".format(self.filename)
    # string += "+-header length: {}\n".format(len(self))
    # string += "+-data streams: {}\n".format(self.data_stream_count)
    # string += "+-streams loaded? {}\n".format(str(self.load_streams))
    # string += "-" * width + "\n"
    # string += "{}".format(self.parameters)
    # string += "-" * width + "\n"
    # string += super(AmiraHeader, self).__str__()
    # string += "*" * width
    # return string


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
