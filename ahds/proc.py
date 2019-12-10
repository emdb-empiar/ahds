# -*- coding: utf-8 -*-
"""
proc
====

The `simpleparse` library requires applications to define `dispatch processors` that are called for each token in the
grammar. This module defines the `dispatch processor`.

"""

import re

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

# simpleparse
from simpleparse.dispatchprocessor import DispatchProcessor, getString, dispatchList, singleMap


class AmiraDispatchProcessor(DispatchProcessor):
    """Class defining methods to handle each token specified in the grammar"""

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
        return {'array_declarations': dispatchList(self, value[3], buffer_)}

    def array_declaration(self, value, buffer_):  # @UnusedVariable
        # value = (tag, left, right, taglist)
        return singleMap(value[3], self, buffer_)

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
