# -*- coding: utf-8 -*-
# header.py
"""
Module to convert parsed data from an Amira (R) header into a set of nested objects. The key class is :py:class:`ahds.header.AmiraHeader`.

Usage:

::

    >>> from ahds.header import AmiraHeader
    >>> ah = AmiraHeader('<somfile>.am')
    >>> print ah

Each nested object is constructed from the :py:class:``Block`` class defined.

There are fife top-level attributes that every ``AmiraHeader`` will have:

 * filename
 * file_format
 * dimension
 * format
 * endian
 * version
 * content_type
 * Parameters

The blocks defining the available data structures extend the basic Block to the corresponding 
AmiraMeshDataStream and AmiraHxSurfaceDataStream blocks which allow to load and access the correspinding
data using the data property defined by theses blocks. The additional filetype, designation, definitions,
data_pointers, stream_data, encoded_data and decoded_data attributes are deprecated and thus may be disfunct
and will be removed in future versions.

The attrs attribute of all Blocks and extended Block objects including AmiraHeader it self
which allows to query the attributes added during loading is deprecated and may be removed in future version.
To query which attributes are defined on each block use the builtin dir function instead. To 
access the defined attributes just use them liḱe any other static attribute.

The following attributes are moved from the designation attribute to the basic header block or replaced
by multiple attributes of the basic header block:
        
        
        *    filetype e.g. ``AmiraMesh`` or ``HyperSurface``
        *    dimension e.g. ``3D``
        *    format e.g. ``BINARY-LITTLE-ENDIAN`` -> format e.g. ``BINARY`` + endian e.g ``LITTLE``
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
REMARK!!!
dose not contain any file format definitions just read/write api functions within xpat developer extension

"""
from __future__ import print_function

import sys
import collections
import warnings

from .core import Block, deprecated, ListBlock 
from .data_stream import set_data_stream, HEADERONLY, ONDEMMAND, IMMEDIATE, get_stream_policy,load_streams,select_array_block
from .grammar import get_header,AHDSStreamError


_NoneBlock = Block('None')

class AmiraHeader(Block):
    """Class to encapsulate Amira metadata and accessors to amria data streams"""

    # __slots__ field is used to separate internal attributes from the dynamic attributes
    # representing the metadata and the accessors to the content of the data streams
    # which will be stored inside the __dict__ attribute of the Block base class
    __slots__ = (
        READONLY('filename'), READONLY('parsed_data'), '_header_length', READONLY('file_format'), READONLY('load_streams'),
        READONLY('data_stream_count'),'_data_streams_block_list','_stream_offset', READONLY('literal_data')
    )

    def __init__(self, fn, load_streams=None, *args, **kwargs):
        if load_streams not in (None, ONDEMMAND, HEADERONLY,IMMEDIATE):
            if not isinstance(load_streams,bool):
                raise ValueError('stream policy must be one of HEADERONLY, ONDEMMAND, IMMEDIATE')
            # for compatibility with older version where load_streams could either be True or False
            # not testable as long as comparison of bool with int 0 and 1 yields true therefor no cover
            load_streams = IMMEDIATE if load_streams else HEADERONLY # pragma: nocover
        super(AmiraHeader, self).__init__('header')
        """Construct an AmiraHeader object from parsed data"""
        self._filename = fn
        # set policy for loading streams, if load_streams is None use global policy
        self._load_streams = load_streams if load_streams is not None else get_stream_policy()
        with open(fn,'rb') as fhnd:
            self._file_format,self._parsed_data, self._header_length,self._literal_data = get_header(
                fhnd, drop_data = ( self.load_streams == HEADERONLY ), **kwargs
            )
        # data stream count
        self._data_stream_count = None
        self._stream_offset = self._header_length
        # load the parse data into this object
        self._load()

    @classmethod
    @deprecated("Now you can directly create a header from the file name as AmiraHeader('file.am')")
    def from_file(cls, fn, *args, **kwargs):
        """Deprecated classmethod"""
        return cls(fn, *args, **kwargs)

    def __len__(self):
        return self._header_length

    def _load(self):
        # first flatten the dict
        #block_data = flatten_dict(self.parsed_data)
        block_data = { 
            block_key:block_data
            for block in self._parsed_data
            for block_key,block_data in block.items()#_dict_iter_items(block)
        }
        # load file designations
        self._load_designation(block_data['designation'])
        _extra_materials_spec = block_data.get('materials',None)
        # ensure that old way specifying materials separately 
        # is properly integrated within Parameters structure
        if _extra_materials_spec is not None:
            # load parameters force their existence if not defined
            _parameter_spec = block_data.get('parameters',[])
            for param in _parameter_spec:
                param_name = param.get('parameter_name',None)
                if param_name in {'Materials','materials'}:
                    _param_value = param.get('parameter_value',list)
                    if not isinstance(_param_value,list): # pragma: nocover
                        param['parameter_value'] = _param_value = [] if _param_value is list else [{'parameter_name':'<N/A>','parameter_value':_param_value}]
                    _param_value.extend(_extra_materials_spec)
                    break
            else:
                 _parameter_spec.append({'parameter_name':'Materials','parameter_value':_extra_materials_spec})
        else:
            # load parameters if present
            _parameter_spec = block_data.get('parameters',[])
        _parameters = self._load_parameters(_parameter_spec, 'Parameters', parent=self)
        # if we have a Materials block in parameters we create a convenience dictionary for
        # accessing materials e.g. for patches
        _materials = getattr(_parameters,'Materials',[])#assert(block_data.get('materials',None) is None)
        if _materials: #hasattr(_parameters, 'Materials'):
            material_dict = dict()
            for material in _materials:#_parameters.Materials:
                if material is not None:
                    material_dict[material.name] = material
            _parameters.Materials.material_dict = material_dict
        super(AmiraHeader, self).add_attr('Parameters', _parameters)
        # load array declarations
        self._load_declarations(block_data['array_declarations'])
        self._data_streams_block_list = self._load_definitions(block_data['data_definitions'])
        self._data_stream_count = len(self._data_streams_block_list) - 1
        # cleanup any temporary protected subarray_declartion these should be inserted by setattr
        # below in self.__dict__ thus filtering its keys should be faster than filtering
        # full dir(self) which also contains inherited attributes, dynamic attributes and
        # other stuff to be ignored anyway
        for sub_decl_name in ( key for key in tuple(self.__dict__) if key[:2] == '_@' ):
            #if sub_decl_name[:2] != '_@':
            #    continue
            delattr(self,sub_decl_name)
        if self.load_streams == IMMEDIATE:
            load_streams(self)

    @property
    @deprecated(" use header attributes version, dimension, fileformat, format and extra_format istead")
    def designation(self):
        """Designation of the Amira file defined in the first row
        
        Designations consist of some or all of the following data:
        
        *    filetype e.g. ``AmiraMesh`` or ``HyperSurface``
        
        *    dimensions e.g. ``3D``
        
        *    format e.g. ``BINARY-LITTLE-ENDIAN`` -> format e.g ``BINARY`` + endian e.g. ``LITTLE``
        
        *    version e.g. ``2.1``
        
        *    extra format e.g. ``<hxsurface>``

        NOTE: this property is deprecated use the corresponding attributes of the AmiraHeader
        instead to access the above informations
        """
        return self

    @property
    @deprecated(" use data array attributes instead eg. header.Vertices, header.Triangles, ...")
    def definitions(self):
        """Definitions consist of a key-value pair specified just after the 
        designation preceded by the key-word 'define'      

        NOTE: this property is deprecated access the corresponding attributes directly
        eg. ah.Nodes instead of ah.definitions.Nodes or ah.Tetrahedra instead of ah.defintions.Tetrahedra
        """
        return self

    @property
    @deprecated(" use data attributes of data arrays  instead eg. header.Vertices.Coordinates")
    def data_pointers(self):
        """The list of data pointers together with a name, data type, dimension, 
        index, format and length

        NOTE: deprecated access the data defnitions for each data array through the corresponding attributes
        eg.: ah.Nodes.Coordinates instead of ah.data_pointers.data_pointer_1 ah.Tetrahedra.Nodes instead of 
        ah.data_pointers.data_pointer_2 etc. In any case an empty Block
        """

        _data_pointers = Block("data_pointers")
        return _data_pointers

    @property
    @deprecated(" use header.file_format attribute instead")
    def filetype(self):
        """
        deprecated alias for file_format attribute
        """
        return self.file_format

    __decode_format__ = {
        'BINARY':('format','BINARY','endian','BIG'),
        'BINARY-LITTLE-ENDIAN':('format','BINARY','endian','LITTLE'),
        'ASCII':('format','ASCII','endian',None)
    }
    def _load_designation(self, block_data):
        self.add_attr('dimension', block_data.get('dimension', None))
        try:
            format = AmiraHeader.__decode_format__[block_data.get('format')]
        except KeyError: # pragma: nocover
            raise ValueError(
                u'unsupported format {format}; kindly consider contacting the maintainer to include support. Thanks.'.format(
                    format=block_data.get('format')
                )
            )
        self.add_attr(*format[:2])#'format', format)
        self.add_attr(*format[2:])#'endian', 'BIG')
        self.add_attr('version', block_data.get('version', None))
        self.add_attr('content_type', block_data.get('content_type', None))

    def _load_parameters(self, block_data, name='Parameters', **kwargs):
        # treat materials specially (and possibly others in the future)
        if name == "Materials":
            block = ListBlock(name)
            fillin = collections.deque()
            for param in block_data:
                # a sequence of parameters
                if isinstance(param['parameter_value'], list):
                    if len(param['parameter_value']) > 0:
                        if param['parameter_value'][0] == '<!?c?!>':
                            # pragma: nocover
                            warnings.warn("Material '{}' found which is just list".format(param['parameter_name']))
                            sub_param = Block(param['parameter_name'])
                            sub_param.add_attr('Values',param['parameter_value'][1:])
                            fillin.append(sub_param)
                        else:
                            sub_param = self._load_parameters(
                                param['parameter_value'],
                                name=param['parameter_name']
                            )
                            param_id = getattr(sub_param,'Id',None)
                            if param_id is None:
                                fillin.append(sub_param)
                            else:
                                block.insert(int(param_id),sub_param)
                            block.add_attr(param['parameter_name'],sub_param)
                    else:
                        sub_param = Block(param['parameter_name'])
                        #sub_param.add_attr('Value', param['parameter_value'])
                        fillin.append(sub_param)
                # a string or number
                elif param['parameter_name'] == 'name':
                    block._name = param['parameter_name']
                else:
                    block.add_attr(param['parameter_name'], param['parameter_value'])
            fill_hole = 0
            while fillin:
                for fill_hole in range(fill_hole+1,len(block)):
                    if block[fill_hole] is None:
                        filler = block[fill_hole] = fillin.popleft()
                        block.add_attr(filler)
                        filler.add_attr('Id',fill_hole)
                        break
                else:
                    for fill_hole,filler in enumerate(fillin,len(block)):
                        block.add_attr(filler)
                        block.append(filler)
                        filler.add_attr('Id',fill_hole)
                    fillin.clear()

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
                                    param['parameter_name'], # parameter_value can contain an explicit name attribute
                                    self._load_parameters(param['parameter_value'], name=param['parameter_name'])
                                )
                        else: # pragma: nocover
                            warnings.warn("have direct value parameter {} in file {}: remove nocover".format(param['parameter_name'],self.filename))
                            block.add_attr(param['parameter_name'], param['parameter_value'])
                    elif param['parameter_name'] == 'name':
                        block._name = param['parameter_name']
                    else:
                        block.add_attr(param['parameter_name'], param['parameter_value'])
                except KeyError:
                    print(
                        u"Found odd parameter: {} = {}".format(
                            list(param.keys())[0] if param.keys() else '<<missing>>', 
                            param.get(list(param.keys())[0] if param.keys() else None,'<<missing>>')
                        ),
                        file=sys.stderr
                    )
        return block

    def _load_declarations(self, block_data):
        """Load the array definition blocks which will contain the data streams"""
        for decl in block_data:
            array_dimension = decl['array_dimension']
            if array_dimension is None:
                self.add_attr(decl['array_name'],decl.get('stream_data',''))
                continue
            block_type = decl.get("array_blocktype","block")
            block = select_array_block(decl)
            # if no array_parent use invalid attribute name to ensure self is returned
            array_links = decl.get('array_links',{})
            array_parent = self
            if array_links:# is not None:
                active_link = array_links.get((self.content_type if self.content_type is not None else self._file_format),None)
                if active_link is not None:
                    array_parent = getattr(self,active_link.get('array_parent',':<*+.=/->#'),self)
                    if array_parent is not self:
                        # add hidden shortcut to hypersurface subarray to be found by _load_definitions below
                        # but is not accessible by any other means. '_@' is not a valid attribut name and thus
                        # not accessible via . operator only getattr, setattr, delattr will be able to handle
                        setattr(self,'_@{}'.format(block.name),block)
                        if isinstance(array_parent,ListBlock):
                            item_id = active_link.get('array_itemid',None)
                            if item_id is not None and item_id >= 0:
                                array_parent[item_id] = block
            array_parent.add_attr(block)

    def _load_definitions(self, block_data):
        """We want to load data definitions to the appropriate array definition block"""
        data_streams = [_NoneBlock]
        for defn in block_data:
            # check whether the array_ref is an attribute on self
            if defn["array_reference"] == "Field":
                data_index = int(defn["data_index"])
                if data_index >= len(data_streams):
                    data_streams.extend([None] * ( data_index - len(data_streams) + 1))
                if data_streams[data_index] is None:
                    data_streams[data_index] = defn
                    continue
                field_data_block = data_streams[data_index]
                field_dimension = defn.get("data_dimension",1)
                if field_dimension != field_data_block.dimension or defn["data_type"] != field_data_block.type:
                    raise AHDSStreamError("field definition does not match data stream definition")
                field_data_block.add_attr("interpolation_method",defn.get("interpolation_method",None))
                field_data_block.add_attr("field_name",defn['data_name'])
                continue
            parent = getattr(self,defn["array_reference"],self)
            if parent is self:
                # check whether defn["array_reference"] would refer to subarray which
                # can be accessed directly by protected attribute of self
                parent = getattr(self,'_@{}'.format(defn["array_reference"]),self)
            # set the data streams
            data_dimension = defn.get('data_dimension',1)
            data_shape = defn.get('data_shape',getattr(parent,"length",None))
            if data_dimension is None and data_shape is None:
                parent.add_attr(defn['data_name'],defn.get('stream_data',''))
                continue
            block = set_data_stream(defn['data_name'], self,defn.get('stream_offset',None),defn.get('stream_data',None))
            data_index = int(defn['data_index'])
            if data_index < 0:
                data_index = len(data_streams)
            block.add_attr('data_index', data_index)
            # conditionally add the data stream if its index is unique e.g. Fields do not have unique ds
            block.add_attr('dimension', data_dimension)  # assume dimension of 1
            if block.data_index >= len(data_streams):
                data_streams.extend([None] * ( block.data_index - len(data_streams) + 1 ))
            if data_streams[block.data_index] is None:
                data_streams[block.data_index] = block
            elif isinstance(data_streams[block.data_index],dict):
                field_descriptor = data_streams[block.data_index]
                if block.dimension != field_descriptor.get("data_dimension",1) or defn["data_type"] != field_descriptor["data_type"]:
                    raise AHDSStreamError("field definition does not match data stream definition")
                block.add_attr("interpolation_method",field_descriptor.get("interpolation_method",None))
                block.add_attr("field_name",field_descriptor['data_name'])
                data_streams[block.data_index] = block
            else:
                raise AHDSStreamError("duplicate data descriptor {}".format(block.data_index))
            # keep track of the data stream indices
            block.add_attr('type', defn['data_type'])
            block.add_attr('shape', data_shape)
            block.add_attr('format', defn.get('data_format', None))
            # insert this definition as an attribute
            parent.add_attr(block)
            # keep track of data streams
        return data_streams

    def get_stream_by_index(self,data_index):
        if data_index < 1:
            raise IndexError("'AmiraDataStream' with given index not provided by '{}' file".format(self._filename))
        try:
            return self._data_streams_block_list[data_index]
        except IndexError:
            raise IndexError("'AmiraDataStream' with given index not provided by '{}' file".format(self._filename))

    def get_stream_offset(self,stream):
        stream_index = getattr(stream,"data_index",len(self._data_streams_block_list))
        try:
            if self._data_streams_block_list[stream_index] is not stream:
                if not isinstance(stream,Block):
                    raise ValueError("stream not a valid Block type object")
                raise ValueError("stream not a valid data stream or not part of this file")
        except IndexError:
            if not isinstance(stream,Block):
                raise ValueError("stream not a valid Block type object")
            raise ValueError("stream not a valid data stream or not part of this file")
        return self._stream_offset

    def set_stream_offset(self,reporter,offset):
        stream_index = getattr(reporter,"data_index",len(self._data_streams_block_list))
        try:
            if self._data_streams_block_list[stream_index] is not reporter:
                if not isinstance(reporter,Block):
                    raise ValueError("stream not a valid Block type object")
                raise ValueError("stream not a valid data stream or not part of this file")
        except IndexError:
            if not isinstance(reporter,Block):
                raise ValueError("stream not a valid Block type object")
            raise ValueError("stream not a valid data stream or not part of this file")
        self._stream_offset = offset
            

    def __repr__(self):
        return "AmiraHeader('{}')".format(self._filename)


def main(test_callback = None): # pragma: nocover
    # testing and debugging only
    try:
        fn = sys.argv[1]
    except IndexError:
        print("usage: ./{} <amira-fn>".format(__file__), file=sys.stderr)
        return 1

    h = AmiraHeader.from_file(fn, verbose=False)
    print(h)
    print(h.designation)
    if h.Parameters is not None:
        print(h.Parameters)
        try:
            print(h.Parameters.attrs)
        except AttributeError:
            pass
        if hasattr(h.Parameters, "Materials"):
            print(h.Parameters.Materials, type(h.Parameters.Materials))
            try:
                print(h.Parameters.Materials.attrs)
            except AttributeError:
                pass
            try:
                print(h.Parameters.Materials.Exterior)
            except AttributeError:
                pass
            print(h.Parameters.Materials.ids)
            try:
                print(h.Parameters.Materials[1].attrs)
            except AttributeError:
                pass
            for id_ in h.Parameters.Materials.ids:
                print(h.Parameters.Materials[id_])
                print("")
    print(h.designation)
    # pylint: disable=E1101
    try:
        print(h.data_pointers.attrs)
    except AttributeError:
        pass
    # pylint: enable=E1101
    if hasattr(h, "Lattice"):
        print(h.Lattice)

    if callable(test_callback):
        return test_callback(h)
    return 0


if __name__ == "__main__": # pragma: nocover
    sys.exit(main())
