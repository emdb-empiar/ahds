==============================================
``ahds``
==============================================

.. image:: https://img.shields.io/pypi/v/ahds/0.2.0.dev0
    :alt: PyPI

.. image:: https://img.shields.io/pypi/pyversions/ahds/0.2.0.dev0
    :alt: PyPI - Python Version

.. image:: https://travis-ci.org/emdb-empiar/ahds.svg?branch=master
    :target: https://travis-ci.org/emdb-empiar/ahds

.. image:: https://readthedocs.org/projects/ahds/badge/?version=latest
    :target: https://ahds.readthedocs.io/en/latest/?badge=latest
    :alt: Documentation Status

.. image:: https://coveralls.io/repos/github/emdb-empiar/ahds/badge.svg
    :target: https://coveralls.io/github/emdb-empiar/ahds

.. contents::

----------------------------------------------
Overview
----------------------------------------------
``ahds`` is a Python package to parse and handle Amira (R) files.
It was developed to facilitate reading of Amira (R) files as part of the `EMDB-SFF toolkit <https://sfftk.readthedocs.io>`_.

.. note::

    Amira (R) is a trademark of Thermo Fisher Scientific. This package is in no way affiliated with with Thermo Fisher Scientific.

----------------------------------------------
License
----------------------------------------------

``ahds`` is free software and is provided under the terms of the Apache License, Version 2.0.

::

    Copyright 2017 EMBL - European Bioinformatics Institute

    Licensed under the Apache License, Version 2.0 (the "License");
    you may not use this file except in compliance with the License.
    You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

    Unless required by applicable law or agreed to in writing,
    software distributed under the License is distributed on an
    "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
    either express or implied. See the License for the specific
    language governing permissions and limitations under the License.

----------------------------------------
Use Cases
----------------------------------------
*     Detect and parse Amira (R) headers and return structured data

*     Decode data (``HxRLEByte``, ``HxZip``)

*     Easy extensibility to handle previously unencountered data streams

``ahds`` was written and is maintained by Paul K. Korir but there is
`a list of contributors <https://github.com/emdb-empiar/ahds/blob/dev/CONTRIBUTORS.txt>`_.
Feel free to join this initiative.

--------------------------------------------
Installation
--------------------------------------------
``ahds`` works with Python 2.7, 3.5, 3.6 and 3.7. It requires ``numpy`` to build.

::

    pip install numpy

Afterwards you may run

::

    pip install ahds

.. note::

    Figure out a way to avoid the need for ``numpy`` as part of the build.

--------------------------------------------
Getting Started
--------------------------------------------

You can begin playing with ``ahds`` out of the box using the provided console command ``ahds``.


.. code:: bash

    me@home ~$ ahds ahds/data/FieldOnTetraMesh.am
    ********************************************************************************************************************************************
    AMIRA (R) HEADER AND DATA STREAMS
    --------------------------------------------------------------------------------------------------------------------------------------------
    +-ahds/data/FieldOnTetraMesh.am                                                                  AmiraFile [is_parent? True ]
    |  +-meta                                                                                            Block [is_parent? False]
    |  |  +-file: ahds/data/FieldOnTetraMesh.am
    |  |  +-header_length: 182
    |  |  +-data_streams: 1
    |  |  +-streams_loaded: False
    |  +-header                                                                                    AmiraHeader [is_parent? True ]
    |  |  +-filetype: AmiraMesh
    |  |  +-dimension: 3D
    |  |  +-format: BINARY
    |  |  +-endian: BIG
    |  |  +-version: 2.0
    |  |  +-extra_format: None
    |  |  +-Parameters                                                                                   Block [is_parent? False]
    |  |  +-Tetrahedra                                                                                   Block [is_parent? False]
    |  |  |  +-length: 23685
    |  +-data_streams                                                                                    Block [is_parent? False]
    ********************************************************************************************************************************************

The ``ahds`` command takes the following arguments

.. code:: bash

    me@home ~$ ahds -h
    usage: ahds [-h] [-s] [-d] [-l] file [file ...]

    Python tool to read and display Amira files

    positional arguments:
      file                a valid Amira file with an optional block path

    optional arguments:
      -h, --help          show this help message and exit
      -s, --load-streams  whether to load data streams or not [default: False]
      -d, --debug         display debugging information [default: False]
      -l, --literal       display the literal header [default: False]

You can specify a **dotted path** after the filename to only render that the content of that field in the header:

.. code:: bash

    me@home ~$ ahds ahds/data/FieldOnTetraMesh.am header
    ***********************************************************************************************************************************
    ahds: Displaying path 'header'
    -----------------------------------------------------------------------------------------------------------------------------------
    +-header                                                                                       AmiraHeader [is_parent? True ]
    |  +-filetype: AmiraMesh
    |  +-dimension: 3D
    |  +-format: BINARY
    |  +-endian: BIG
    |  +-version: 2.0
    |  +-extra_format: None
    |  +-Parameters                                                                                      Block [is_parent? False]
    |  +-Tetrahedra                                                                                      Block [is_parent? False]
    |  |  +-length: 23685


For debugging you can display the literal header (the exact header present in the file) using the ``-l/--literal`` flag.
Also, you can display the parsed data structure using the ``-d/--debug`` flag.

.. code:: bash

    me@home ~$ ahds --literal --debug ahds/data/FieldOnTetraMesh.am
    ***********************************************************************************************************************************
    ahds: Displaying literal header
    -----------------------------------------------------------------------------------------------------------------------------------
    # AmiraMesh 3D BINARY 2.0
    # CreationDate: Tue Nov  2 11:46:31 2004


    nTetrahedra 23685

    TetrahedronData { float[3] Data } @1
    Field { float[3] f } Constant(@1)

    # Data section follows
    ***********************************************************************************************************************************
    ahds: Displaying parsed header data
    -----------------------------------------------------------------------------------------------------------------------------------
    [{'designation': {'dimension': '3D',
                      'filetype': 'AmiraMesh',
                      'format': 'BINARY',
                      'version': '2.0'}},
     {'comment': {'date': 'Tue Nov  2 11:46:31 2004'}},
     {'array_declarations': [{'array_dimension': 23685,
                              'array_name': 'Tetrahedra'}]},
     {'data_definitions': [{'array_reference': 'Tetrahedra',
                            'data_dimension': 3,
                            'data_index': 1,
                            'data_name': 'Data',
                            'data_type': 'float'},
                           {'array_reference': 'Field',
                            'data_dimension': 3,
                            'data_index': 1,
                            'data_name': 'f',
                            'data_type': 'float',
                            'interpolation_method': 'Constant'}]}]

    ********************************************************************************************************************************************
    AMIRA (R) HEADER AND DATA STREAMS
    --------------------------------------------------------------------------------------------------------------------------------------------
    +-ahds/data/FieldOnTetraMesh.am                                                                  AmiraFile [is_parent? True ]
    |  +-meta                                                                                            Block [is_parent? False]
    |  |  +-file: ahds/data/FieldOnTetraMesh.am
    |  |  +-header_length: 182
    |  |  +-data_streams: 1
    |  |  +-streams_loaded: False
    |  +-header                                                                                    AmiraHeader [is_parent? True ]
    |  |  +-filetype: AmiraMesh
    |  |  +-dimension: 3D
    |  |  +-format: BINARY
    |  |  +-endian: BIG
    |  |  +-version: 2.0
    |  |  +-extra_format: None
    |  |  +-Parameters                                                                                   Block [is_parent? False]
    |  |  +-Tetrahedra                                                                                   Block [is_parent? False]
    |  |  |  +-length: 23685
    |  +-data_streams                                                                                    Block [is_parent? False]
    ********************************************************************************************************************************************

By default, data streams are not read --- only the header is parsed. You may obtain the data streams using the
``-s/--load-streams`` flag.

.. code:: bash

    me@home ~$ ahds --load-streams ahds/data/FieldOnTetraMesh.am
    ********************************************************************************************************************************************
    AMIRA (R) HEADER AND DATA STREAMS
    --------------------------------------------------------------------------------------------------------------------------------------------
    +-ahds/data/FieldOnTetraMesh.am                                                                  AmiraFile [is_parent? True ]
    |  +-meta                                                                                            Block [is_parent? False]
    |  |  +-file: ahds/data/FieldOnTetraMesh.am
    |  |  +-header_length: 182
    |  |  +-data_streams: 1
    |  |  +-streams_loaded: True
    |  +-header                                                                                    AmiraHeader [is_parent? True ]
    |  |  +-filetype: AmiraMesh
    |  |  +-dimension: 3D
    |  |  +-format: BINARY
    |  |  +-endian: BIG
    |  |  +-version: 2.0
    |  |  +-extra_format: None
    |  |  +-Parameters                                                                                   Block [is_parent? False]
    |  |  +-Tetrahedra                                                                                   Block [is_parent? False]
    |  |  |  +-length: 23685
    |  +-data_streams                                                                                    Block [is_parent? True ]
    |  |  +-Data                                                                           AmiraMeshDataStream [is_parent? False]
    |  |  |  +-data_index: 1
    |  |  |  +-dimension: 3
    |  |  |  +-type: float
    |  |  |  +-interpolation_method: None
    |  |  |  +-shape: 23685
    |  |  |  +-format: None
    |  |  |  +-data: [  0.8917308   0.9711809 300.       ],...,[  1.4390504   1.1243758 300.       ]
    ********************************************************************************************************************************************

----------------------------------------------
Future Plans
----------------------------------------------
*    Write out valid Amira (R) files

