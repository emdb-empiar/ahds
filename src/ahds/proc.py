# -*- coding: utf-8 -*-
# amira_grammar_parser.py
"""
Dispatch processor used to verify the tokens identified according to
the grammar defined in gramma.py and to assemble the parsed data structure.
"""

import re
import sys

import numpy as np
import warnings

# simpleparse
from simpleparse.dispatchprocessor import DispatchProcessor, getString, dispatchList, singleMap
#from .core import _dict_iter_items

# List of literals found in older files and the constans they should
# be mapped to ensuring consistency between different versions of
# AmiraMesh and HyperSurface files
_compatibilitymap = {
    'TetrahedronData': "Tetrahedra",
    'TetrahedraData': "Tetrahedra",
    'TriangleData': "Triangles",
    'NodeData': "Nodes",
    'EdgeData': "Edges",
    'LatticeData': "Lattice",
    'FieldData': "Field"
}

# removes leading and trailing whitespace and " characters from
# the strings defining string type parameters values such as names of
# materials
_strip_material_name = re.compile(r'^\s*"\s*|\s*",*$')

# checks if contenttype parameter is specified. The latter details the type
# of data stored in AmirMesh files eg: LandMarks, SpreadSheet, etc. 
# currently content type is duplicated to designation, later on it might be 
# also used to postfilter array declarations and restructure them using
# meta declarations for example to collect columns of SpreadSheet as items
# of a single ListBlock. More complex documents are likely to represent
# their structure
_sub_content_type = re.compile(r'^\s*contenttype\s*$',re.I)


class AmiraDispatchProcessor(DispatchProcessor):
    """Class defining methods to handle each token specified in the grammar"""
    _array_declarations_processors = dict(
    )

    @classmethod
    def set_content_type_filter(cls,content_type,filter):
        """
        register a filter function which allows to inspect, process and
        inject a met array_declaration block for the specified content_type.
        The filter is called during parsing array_declarations with the following
        parameters:

            meta_decl ..... the meta array declaration as currently defined
                            for the specified content type

            array_decl .... the parsed declaration to be inspected by the filter

            type .......... the ahdes file ContentType this filter is sensitive toy

            base_type ..... the file content type either HyperSuface or AmirMesh


        It shall return None if the parsed array declaration does not yield a
        positive result. In case filter is successful it has to return the

            meta_name ..... the name of the meta array declaration the array
                            declaration shall be included witin, the
            
            array_index ... the index the inspected array_declaration within the
                            meta_declaration
            
            array_block ... the Block type class to be used for creating the
                            the appropriate Block object corresponding to the 
                            meta_declaration

            other_meta .... dict to be passed to data_stream.select_array_block
                            as part of the meta array_declaratoin.

            other_decl .... dict to be stored as part of array_links entry
                            of inspected array_declaration.

        NOTE: Array declarations are parsed before Parameters header structure 
              which may contain the special ContentType parameter used by
              Amira to refine content type for AmiraMesh files eg. LandMarks
              for landmark files or HxSpreadSheet for Amira spread sheets.
              There fore filter shall only check for the possibilty to be 
              included within ContentType specific structure and emmit
              if at least one declaration matches the filter criteria the filter
              shall return the above information required for a valid meta
              declaration. The final decision which meta declaration wins if
              any is decided by AmiraDispatchProcessor._emmit_meta_array_declaration
              method. 

        """
        if not callable(filter):
            raise ValueError("filter must be callable function")
        if not isinstance(content_type,str) or not content_type:
            raise ValueError("conten_type must be no empty string")
        cls._array_declarations_processors[content_type] = filter

    @classmethod
    def clear_content_type_filter(cls,content_type):
        """
        clears a previously registered filter for the content_type
        """
        if not isinstance(content_type,str) or not content_type:
            raise ValueError("conten_type must be no empty string")
        cls._array_declarations_processors.pop(content_type,None)

    def __init__(self,*args,**kwargs):
        """
        AmiraDispatchProcessor constructor in addtion to arguments and
        keyword arguments recognized by the simpleparse.DispatchProcessor
        object the content_type can and shall be set to 'AmiraMesh' or 
        'HyperSuface' as provided by file designation.

        """
        self._base_contenttype = kwargs.pop('content_type',None)
        if sys.version_info[0] > 2: # pragma: cover_py3
            super(AmiraDispatchProcessor,self).__init__(*args,**kwargs)
        self._meta_array_declarations = dict()
        self._designation = []
        self._array_declarations = []

    def _filter_array_declaration(self,array_declaration):
        """
        parses the provided array declaration dict structure for inclusion witin
        an array meta declaration corresponding to a refined content type denoted
        by special ContentType parameter.
        """

        # represents all ContentType meta declarations the array declaration could 
        # be member of
        array_links = dict()
        #for _content_type,_filter in _dict_iter_items(self.__class__._array_declarations_processors):
        for _content_type,_filter in self.__class__._array_declarations_processors.items():

            # load current array meta declaration for ContentType and filter array declaration
            typed_meta_declaration = self._meta_array_declarations.get(_content_type,None)
            _result = _filter(typed_meta_declaration,array_declaration,_content_type,self._base_contenttype)
            if _result is None:
                # no match
                continue
            # crate new or update existing meta declaratoin
            if typed_meta_declaration is None:
                self._meta_array_declarations[_content_type] = typed_meta_declaration = dict()
            base_name,array_index,array_blocktype,other_meta_data,other_declarations = _result
            meta_declaration = typed_meta_declaration.get(base_name,None)
            if meta_declaration is None:
                typed_meta_declaration[base_name] = meta_declaration = dict(
                    array_name = base_name,
                    array_dimension = array_index + 1,
                    array_blocktype = array_blocktype,
                    array_content = _content_type,
                    sub_declarations = []
                )
            elif meta_declaration["array_dimension"] >= array_index:
                meta_declaration["array_dimension"] = array_index + 1
            if isinstance(other_meta_data,dict):
                meta_declaration.update(other_meta_data)
            meta_declaration['sub_declarations'].append(array_declaration)
            array_links[_content_type] = linked_content_type = dict(array_parent = base_name,array_itemid = array_index)
            if isinstance(other_declarations,dict):
                linked_content_type.update(other_declarations)
        array_declaration['array_links'] = array_links
        return array_declaration

    def _emmit_meta_array_declaration(self,content_type):
        """
        injects meta declaration corresponding to the values of the ContentType parameter
        just parsed if more than one array declaration is to be included within meta declaratoin
        structure. 
        """
        typed_meta_declaration = self._meta_array_declarations.pop(content_type,None)
        if typed_meta_declaration is None:
            return False
        #for _base_name,meta_declaration in _dict_iter_items(typed_meta_declaration):
        for _base_name,meta_declaration in typed_meta_declaration.items():
            sub_declarations = meta_declaration.pop('sub_declarations',[])
            if len(sub_declarations) < 2:
                array_links = sub_declarations[0].get('array_links',{})
                array_links.pop(content_type,None)
                continue
            self._array_declarations.insert(0,meta_declaration)
        self._meta_array_declarations.clear()
        self._base_contenttype = None
        return True
                    
    def designation(self, value, buffer_):  # @UnusedVariable
        # value = (tag, left, right, taglist)
        designation = singleMap(value[3],self,buffer_)
        self._designation = designation
        if self._base_contenttype and designation.get('content_type',None) is None:
            # fix missing content_type entry 
            designation['content_type'] = self._base_contenttype
        return {'designation': designation}

    def filetype(self, value, buffer_):
        # value = (tag, left, right, taglist)
        return getString(value, buffer_)

    def dimension(self, value, buffer_):
        # value = (tag, left, right, taglist)
        return getString(value, buffer_)

    def format(self, value, buffer_):
        # value = (tag, left, right, taglist)
        return getString(value, buffer_)

    def version(self, value, buffer_):
        # value = (tag, left, right, taglist)
        return getString(value, buffer_)

    def content_type(self, value, buffer_):
        # value = (tag, left, right, taglist)
        content_type = getString(value,buffer_).strip('\n\r \t<>')
        return content_type

    def comment(self, value, buffer_):  # @UnusedVariable
        # value = (tag, left, right, taglist)
        return {'comment': singleMap(value[3], self, buffer_)}

    def date(self, value, buffer_):
        # value = (tag, left, right, taglist)
        return getString(value, buffer_)

    def array_declarations(self, value, buffer_):  # @UnusedVariable
        # value = (tag, left, right, taglist)
        array_declarations_list = dispatchList(self, value[3], buffer_)

        self._array_declarations = array_declarations_list
        return dict(array_declarations = array_declarations_list)
        

    def array_declaration(self, value, buffer_):  # @UnusedVariable
        # value = (tag, left, right, taglist)
        declaration = singleMap(value[3], self, buffer_)
        return self._filter_array_declaration(declaration)

    def array_name(self, value, buffer_):
        # value = (tag, left, right, taglist)
        return getString(value, buffer_)

    def array_dimension(self, value, buffer_):  # @UnusedVariable
        # value = (tag, left, right, taglist)
        _av = dispatchList(self, value[3], buffer_)
        # if resulting list of sizes along all dimensions has only a single
        # entry than reduce it to a scalar size value otherwise convert to 
        # numpy.int64 array
        if len(_av) == 1:
            return int(_av[0])
        return np.array(_av, dtype=int)

    def parameters(self, value, buffer_):  # @UnusedVariable
        # value = (tag, left, right, taglist)
        _av = singleMap(value[3], self, buffer_)
        if len(_av) == 1 and isinstance(_av,dict):
            _pl = _av.get("parameter_list",value)
            if _pl is not value:
                return {'parameters': _pl}
        
        warnings.warn("parameters without parameterlist: save data as testcase") # pragma: nocover
        return {'parameters': _av} # pragma: nocover

    def materials(self, value, buffer_):  # @UnusedVariable
        # value = (tag, left, right, taglist)
        _av = dispatchList(self, value[3], buffer_)
        # currently gramma handles dedicated materials section as additional 
        # parameters section starting with Materials instead of Parameters.
        # rewrite it to materials struture to ensure they do not overwrite 
        # the preceeding parameters section
        def filter():
            _item = None
            for _item,_id in (
                (
                    _itm,
                    _index
                )
                for _itm in _av
                for _index, _val in enumerate(_itm) if _item is not _itm and _val['parameter_name'] in ['name', 'Name']
            ):
                yield _strip_material_name.sub('', _item[_id]['parameter_value']),_item[:_id] + _item[_id + 1:]
        return {
            'materials': [
                {'parameter_name':name,'parameter_value':value}
                for name,value in filter()
            ]
        }

    def parameter(self, value, buffer_):  # @UnusedVariable
        # value = (tag, left, right, taglist)
        parameter = singleMap(value[3], self, buffer_)
        parameter_name = parameter.get("parameter_name",r'')
        if _sub_content_type.match(parameter_name) is None:
            return parameter
        parameter_value = parameter.get("parameter_value",None)
        if not isinstance(parameter_value,str):
            return parameter
        content_type = self._designation.get('content_type',None)
        if content_type is None:
            self._designation['content_type'] = parameter_value
        elif isinstance(content_type,(list,tuple)):
            content_type.append(parameter_value)
        else:
            self._designation['content_type'] = [content_type,parameter_value]
        self._emmit_meta_array_declaration(parameter_value)
        return parameter

    def parameter_value(self, value, buffer_):  # @UnusedVariable
        # value = (tag, left, right, taglist)
        _av = dispatchList(self, value[3], buffer_)
        if len(_av) == 1:
            return _av[0]
        warnings.warn("list type parameter value: save data as testcase") # pragma: nocover
        return _av # pragma: nocover

    def parameter_list(self, value, buffer_):  # @UnusedVariable
        # value = (tag, left, right, taglist)
        return dispatchList(self, value[3], buffer_)

    def parameter_name(self, value, buffer_):
        # value = (tag, left, right, taglist)
        return getString(value, buffer_)

    def attribute_value(self, value, buffer_):  # @UnusedVariable
        # value = (tag, left, right, taglist)
        _av = dispatchList(self, value[3], buffer_)
        # if list of attribute values contains only one entry reduce it 
        # to scalar value. In case the list contains more than one value
        # insert the string "<!?c?!>" which will be used by the
        # AmiraHeader._load_parameters function to distinguisch between
        # a list of constant parameter values and a list of parameters
        # in case list of parameter values is empty return None
        if len(_av) == 1:
            return _av[0]
        elif len(_av) > 1: # pragma: nocover
            warnings.warn("list type attribute value: save data as testcase") # pragma: nocover
            return ["<!?c?!>"] + _av 
        warnings.warn("empty attribute value: save data as testcase") # pragma: nocover
        return None # pragma: nocover

    def inline_parameter_value(self, value, buffer_):
        # value = (tag, left, right, taglist)
        if value[3][0][0] == "qstring":
            return getString(value, buffer_).strip(' \t\n\r\f"')
        _av = dispatchList(self, value[3], buffer_)
        # if list of attribute values contains only one entry reduce it 
        # to scalar value. Otherwise # insert the string "<!?c?!>" which
        # will be used by the # AmiraHeader._load_parameters function to
        # distinguisch between a list of constant parameter values and a
        # list of sub parameters
        if len(_av) == 1:
            return _av[0]
        return ['<!?c?!>'] + _av

    def data_definitions(self, value, buffer_):
        # value = (tag, left, right, taglist)
        return {'data_definitions': dispatchList(self, value[3], buffer_)}

    def data_definition(self, value, buffer_):
        if self._meta_array_declarations:
            self._emmit_meta_array_declaration(self._base_contenttype)
                
        # value = (tag, left, right, taglist)
        return singleMap(value[3], self, buffer_)

    def interpolation_method(self, value, buffer_):
        # value = (tag, left, right, taglist)
        return getString(value, buffer_)

    def array_reference(self, value, buffer_):
        # value = (tag, left, right, taglist)
        reference = getString(value, buffer_)
        # rename older AmiraMesh array refrence specification to their
        # corresponding value found in newer files
        return _compatibilitymap.get(reference, reference)

    def data_type(self, value, buffer_):
        # value = (tag, left, right, taglist)
        return getString(value, buffer_)

    def data_dimension(self, value, buffer_):
        # value = (tag, left, right, taglist)
        return int(getString(value, buffer_))

    def data_name(self, value, buffer_):
        # value = (tag, left, right, taglist)
        return getString(value, buffer_)

    def data_index(self, value, buffer_):
        # value = (tag, left, right, taglist)
        return int(getString(value, buffer_))

    def data_format(self, value, buffer_):
        # value = (tag, left, right, taglist)
        return getString(value, buffer_)

    def data_length(self, value, buffer_):
        # value = (tag, left, right, taglist)
        return int(getString(value, buffer_))

    def hyphname(self, value, buffer_):
        warnings.warn("touched but not reported as covered") # pragma: nocover
        # value = (tag, left, right, taglist)
        return getString(value, buffer_) # pragma: nocover

    def xstring(self, value, buffer_):
        # value = (tag, left, right, taglist)
        return getString(value, buffer_)

    def qstring(self, value, buffer_):
        # value = (tag, left, right, taglist)
        warnings.warn("touched but not reported as covered") # pragma: nocover
        return getString(value, buffer_) # pragma: nocover

    def number(self, value, buffer_):
        # value = (tag, left, right, taglist)
        if value[3][0][0] == 'int':
            return int(getString(value, buffer_))
        elif value[3][0][0] == 'float':
            return float(getString(value, buffer_))
        warnings.warn("touched but not reported as covered") # pragma: nocover
        return getString(value, buffer_) # pragma: nocover

    def number_seq(self, value, buffer_):
        # value = (tag, left, right, taglist)
        warnings.warn("touched but not reported as covered") # pragma: nocover
        return dispatchList(self, value[3], buffer_) # pragma: nocover

set_content_type_filter = AmiraDispatchProcessor.set_content_type_filter
clear_content_type_filter = AmiraDispatchProcessor.clear_content_type_filter

