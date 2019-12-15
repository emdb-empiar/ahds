# -*- coding: utf-8 -*-
# amira_grammar_parser.py
"""
Dispatch processor used to verify the tokens identified according to
the grammar defined in gramma.py and to assemble the parsed data structure.
"""

import re
import sys

import numpy as np

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

# used to extract counter indices from the tail of array_names
# and collect them within a common meta_array_declaration of the
# common base_name. Is applied to reversed array_name string
# a counter is any trailing number which is preceeded by non numerical
# character exempt '-' and '_' if they are preceeded by at least one digit
_extract_trailing_counter = re.compile(r'^\d+(?![-_]\d)')

# simpleparse
from simpleparse.dispatchprocessor import DispatchProcessor, getString, dispatchList, singleMap


class AmiraDispatchProcessor(DispatchProcessor):
    """Class defining methods to handle each token specified in the grammar"""
    def __init__(self,*args,**kwargs):
        if sys.version_info[0] > 2:
            super(AmiraDispatchProcessor,self).__init__(*args,**kwargs)
        else:
            super(type(self),self).__init__(*args,**kwargs)
        self._meta_array_declarations = dict()

    def designation(self, value, buffer_):  # @UnusedVariable
        # value = (tag, left, right, taglist)
        return {'designation': singleMap(value[3], self, buffer_)}

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

    def extra_format(self, value, buffer_):
        # value = (tag, left, right, taglist)
        return getString(value, buffer_)

    def comment(self, value, buffer_):  # @UnusedVariable
        # value = (tag, left, right, taglist)
        return {'comment': singleMap(value[3], self, buffer_)}

    def date(self, value, buffer_):
        # value = (tag, left, right, taglist)
        return getString(value, buffer_)

    def array_declarations(self, value, buffer_):  # @UnusedVariable
        # value = (tag, left, right, taglist)
        array_declarations_list = dispatchList(self, value[3], buffer_)

        def filter_meta_declaration(declaration):
            # Confirm that meta_declaration is referred to by more than one
            # parsed array_declaration. In case only the initiating array_declaration
            # referse to this meta_declaration cleanup reset initiating array_declaratoin
            # to its inital state as parsed and reject corresponding meta_array_declaration
            if declaration["sub_declarations"] > 1:
                return True
            cleanup = declaration["initiated_by"]
            del cleanup["array_parent"]
            del cleanup["array_itemid"]
            return False
            
        return {
            'array_declarations': [
                meta_declaration
                for meta_declaration in self._meta_array_declarations.values()
                if filter_meta_declaration(meta_declaration)
            ] + array_declarations_list
        }

    def array_declaration(self, value, buffer_):  # @UnusedVariable
        # value = (tag, left, right, taglist)
        declaration = singleMap(value[3], self, buffer_)
        array_name = declaration.get('array_name',None)
        if array_name is None:
            return declaration
        has_counter = _extract_trailing_counter.match(array_name[::-1])
        if has_counter is None:
            return declaration
        base_name = array_name[:-has_counter.end()]
        array_index = int(array_name[-has_counter.end():])
        meta_declaration = self._meta_array_declarations.get(base_name,None)
        if meta_declaration is None:
            self._meta_array_declarations[base_name] = meta_declaration = dict(
                array_name = base_name,
                array_dimension = array_index + 1,
                array_blocktype = 'list',
                sub_declarations = 0,
                initiated_by = declaration
            )
        elif meta_declaration["array_dimension"] >= array_index:
            meta_declaration["array_dimension"] = array_index + 1
        meta_declaration['sub_declarations'] += 1
        declaration['array_parent'] = base_name
        declaration['array_itemid'] = array_index
        return declaration

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
        elif len(_av) > 1:
            return np.array(_av, dtype=np.int64)
        else:
            raise ValueError('definition value list is empty:', _av)

    def parameters(self, value, buffer_):  # @UnusedVariable
        # value = (tag, left, right, taglist)
        _av = singleMap(value[3], self, buffer_)
        if len(_av) == 1 and type(_av) in [dict] and "parameter_list" in _av:
            return {'parameters': _av["parameter_list"]}
        return {'parameters': _av}

    def materials(self, value, buffer_):  # @UnusedVariable
        # value = (tag, left, right, taglist)
        _av = dispatchList(self, value[3], buffer_)
        # currently gramma handles dedicated materials section as additional 
        # parameters section starting with Materials instead of Parameters.
        # rewrite it to materials struture to ensure they do not overwrite 
        # the preceeding parameters section
        return {
            'materials': [
                {
                    'parameter_name': _strip_material_name.sub('', _item[_id]['parameter_value']),
                    'parameter_value': _item[:_id] + _item[_id + 1:]
                }
                for _item, _id in (
                    (
                        _item,
                        [_index for _index, _val in enumerate(_item) if _val['parameter_name'] in ['name', 'Name']][0]
                    ) for _item in _av
                )
            ]
        }

    def parameter(self, value, buffer_):  # @UnusedVariable
        # value = (tag, left, right, taglist)
        return singleMap(value[3], self, buffer_)

    def parameter_value(self, value, buffer_):  # @UnusedVariable
        # value = (tag, left, right, taglist)
        _av = dispatchList(self, value[3], buffer_)
        if len(_av) == 1:
            return _av[0]
        return _av

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
        elif len(_av) > 1:
            return ["<!?c?!>"] + _av
        elif len(_av) == 0:
            return None
        else:
            raise ValueError('attribute value list is empty:', _av)

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
        # value = (tag, left, right, taglist)
        return getString(value, buffer_)

    def xstring(self, value, buffer_):
        # value = (tag, left, right, taglist)
        return getString(value, buffer_)

    def qstring(self, value, buffer_):
        # value = (tag, left, right, taglist)
        return getString(value, buffer_)

    def number(self, value, buffer_):
        # value = (tag, left, right, taglist)
        if value[3][0][0] == 'int':
            return int(getString(value, buffer_))
        elif value[3][0][0] == 'float':
            return float(getString(value, buffer_))
        else:
            return getString(value, buffer_)

    def number_seq(self, value, buffer_):
        # value = (tag, left, right, taglist)
        return dispatchList(self, value[3], buffer_)
