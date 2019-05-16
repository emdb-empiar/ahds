==============================================
``ahds``
==============================================

.. image:: https://readthedocs.org/projects/ahds/badge/?version=latest
    :target: https://ahds.readthedocs.io/en/latest/?badge=latest
    :alt: Documentation Status

.. contents:: Table of Contents

----------------------------------------------
Overview
----------------------------------------------
``ahds`` is a Python package to parse and handle Amira (R) files.
It was developed to facilitate reading of Amira (R) files as part of the EMDB-SFF toolkit.

.. note::

    Amira (R) is a trademark of Thermo Fisher Scientific. This package is in no way affiliated with with Thermo Fisher Scientific.

Use Cases
==============================================
*     Detect and parse Amira (R) headers and return structured data

*     Decode data (``HxRLEByte``, ``HxZip``)

*     Easy extensibility to handle previously unencountered data streams

``ahds`` was written and is maintained by Paul K. Korir.

--------------------------------------------
Installation
--------------------------------------------
Presently, ``ahds`` only works with Python 2.7 but will soon work on Python 3. Please begin by 
installing ``numpy<1.16`` using 

::

    pip install numpy<1.16

because it is needed to run ``setup.py``. Afterwards you may run

::

    pip install ahds

----------------------------------------------
License
----------------------------------------------

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

----------------------------------------------
Future Plans
----------------------------------------------
*    Write out valid Amira (R) files

----------------------------------------------
Background and Definitions
----------------------------------------------
``ahds`` presently handles two types of Amira (R) files:

*     `AmiraMesh` files, which typically but not necessarily have a ``.am`` extension, and

*     `HyperSurface` files, which have ``.surf`` and represent an older filetype.

Both file types consist of two parts: 

*     a `header`, and 

*     one or more `data streams`. 

Headers are structured in a modified VRML-like syntax and differ between AmiraMesh and HyperSurface files in some of the keywords used. 

A data stream is a sequence of encoded bytes either referred to in the header by some delimiter (usually ``@<data_stream_index>``, where ``<data_stream_index>`` is an integer) or a set of structural keywords (e.g. ``Vertices``, ``Patches``) expected in a predefined sequence.

Headers in Detail
==============================================
AmiraMesh and HyperSurface headers can be divided into four main sections:

*     **designation**

*     **definitions**

*     **parameters**, and

*     **data pointers**.

The `designation` is the first line and conveys several important details about the format and structure of the file such as:

*     filetype (either ``AmiraMesh`` or ``HyperSurface``)

*     dimensionality (``3D``)

*     format (``BINARY-LITTLE-ENDIAN``, ``BINARY`` or ``ASCII``)

*     version (a decimal number e.g. ``2.1``

*     extra format data e.g. ``<hxsurface>`` specifying that an AmiraMesh file will contain HyperSurface data

A series of `definitions` follow that refer to data found in the data pointer sections that either begin with the word ‘define’ or have ‘n’ prepended to a variable. For example:

::

    define Lattice 862 971 200

or 

::

    nVertices 85120

This is followed by grouped `parameters` enclosed in a series of braces beginning with the word ‘Parameters’. Various parameters are then enclosed each beginning with the name of that group of parameters e.g. ‘Materials’

::

    Parameters {
        # grouped parameters
        Material {
            # the names of various materials with attributes
            Exterior {
                id 0
            }
            Inside {
                id 1,
                Color 0 1 1,
                Transparency 0.5
            }
        }
        Patches {
        # patch attributes
            InnerRegion “Inside”,
            OuterRegion “Exterior”,
            BoundaryID 0,
            BranchingPoints 0
        }
        # inline parameters
        GridSize <value>,
        …
    }

The most important set of parameters are materials as these specify colours and identities of distinct segments/datasets within the file.

Finally, AmiraMesh files list a set of `data pointers` that point to data labels within the file together with additional information to decode the data. We refer to these as data streams because they consist of continuous streams of raw byte data that need to be decoded. Here is an example of data pointers that refer to the location of 3D surface primitives:

::

    Vertices { float[3] Vertices } @1
    TriangleData { int[7] Triangles } @2
    Patches-0 { int Patches-0 } @3

These refer to three raw data streams each found beginning with the delimiter ``@<number>``. Data stream one (``@1``) is called ``Vertices`` and consists of float triples, two is called ``TriangleData`` and has integer 7-tuples and three called ``Patches-`` is a single integer (the number of patches). In some cases the data pointer contains the data encoding for the corresponding data pointer.

::

    Lattice { byte Labels } @1(HxByteRLE,234575740)

which is a run-length encoded data stream of the specified length, while

::
    
    Lattice { byte Data } @1(HxZip,919215)

contains zipped data of the specified length.

Data Streams in Detail
==============================================
AmiraMesh data streams are very simple. They always have a start delimiter made of ``@`` with an index that identifies the data stream. A newline character separates the delimiter with the data stream proper which is either plain ASCII or a binary stream (raw, zipped or encoded).

HyperSurface data streams structured to have the following sections:

::

    # Header
    Vertices <nvertices>
    # vertices data stream
    
    NBranchingPoints <nbranching_points>
    NVerticesOnCurves <nvertices_on_curves>
    BoundaryCurves <nboundary_curves>
    Patches <npatches>
    {
    InnerRegion <inner_region_name>
    OuterRegion <outer_region_name>
    BoundaryID <boundary_id>
    BranchingPoints <nbranching_points>
    Triangles <ntriangles>
    # triangles data stream
    } # repeats for as <npatches> times

HyperSurface data streams can be either plain ASCII or binary.

----------------------------------------------
``ahds`` Modules
----------------------------------------------
``ahds`` has three main modules:

*    `ahds.grammar <https://ahds.readthedocs.io/en/latest/ahds.html#ahds-grammar-module>`_ specifies an EBNF grammar

*    `ahds.header <https://ahds.readthedocs.io/en/latest/ahds.html#ahds-header-module>`_ 

*    `ahds.data_stream <https://ahds.readthedocs.io/en/latest/ahds.html#ahds-data-stream-module>`_

These modules are tied into a user-level class called ``ahds.AmiraFile`` that does all the work for you.

.. code:: python

    >>> from ahds import AmiraFile
    >>> # read an AmiraMesh file
    >>> af = AmiraFile('am/test7.am')
    >>> af.header
    <AmiraHeader with 4 bytes>
    >>> # empty data streams
    >>> af.data_streams
    >>> print af.data_streams
    None
    >>> # we have to explicitly read to get the data streams
    >>> af.read()
    >>> af.data_streams
    <class 'ahds.data_stream.DataStreams'> object with 13 stream(s): 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13
    >>> for ds in af.data_streams:
    ...   print ds
    ...
    <class 'ahds.data_stream.AmiraMeshDataStream'> object of 2,608 bytes
    <class 'ahds.data_stream.AmiraMeshDataStream'> object of 2,608 bytes
    <class 'ahds.data_stream.AmiraMeshDataStream'> object of 2,608 bytes
    <class 'ahds.data_stream.AmiraMeshDataStream'> object of 2,608 bytes
    <class 'ahds.data_stream.AmiraMeshDataStream'> object of 2,608 bytes
    <class 'ahds.data_stream.AmiraMeshDataStream'> object of 2,608 bytes
    <class 'ahds.data_stream.AmiraMeshDataStream'> object of 2,608 bytes
    <class 'ahds.data_stream.AmiraMeshDataStream'> object of 2,608 bytes
    <class 'ahds.data_stream.AmiraMeshDataStream'> object of 2,608 bytes
    <class 'ahds.data_stream.AmiraMeshDataStream'> object of 2,608 bytes
    <class 'ahds.data_stream.AmiraMeshDataStream'> object of 2,608 bytes
    <class 'ahds.data_stream.AmiraMeshDataStream'> object of 2,608 bytes
    <class 'ahds.data_stream.AmiraMeshDataStream'> object of 2,608 bytes
    # we get the n-th data stream using the index/key notation
    >>> af.data_streams[1].encoded_data
    '1 \n2 \n3 \n'
    >>> af.data_streams[1].decoded_data
    [1, 2, 3]
    >>> af.data_streams[2].encoded_data
    '69 \n120 \n116 \n101 \n114 \n105 \n111 \n114 \n0 \n73 \n110 \n115 \n105 \n100 \n101 \n0 \n109 \n111 \n108 \n101 \n99 \n117 \n108 \n101 \n0 \n'
    >>> af.data_streams[2].decoded_data
    [69, 120, 116, 101, 114, 105, 111, 114, 0, 73, 110, 115, 105, 100, 101, 0, 109, 111, 108, 101, 99, 117, 108, 101, 0]


.. code:: python

    >>> # read an HyperSurface file
    >>> af = AmiraFile('surf/test4.surf')
    >>> af.read()
    >>> af.data_streams
    <class 'ahds.data_stream.DataStreams'> object with 5 stream(s): Patches, NBranchingPoints, BoundaryCurves, Vertices, NVerticesOnCurves
    # HyperSurface files have pre-set data streams
    >>> af.data_streams['Vertices'].decoded_data[:10]
    [(560.0, 243.0, 60.96875), (560.0, 242.9166717529297, 61.0), (559.5, 243.0, 61.0), (561.0, 243.0, 60.95833206176758), (561.0, 242.5, 61.0), (561.0384521484375, 243.0, 61.0), (559.0, 244.0, 60.94444274902344), (559.0, 243.5, 61.0), (558.9722290039062, 244.0, 61.0), (560.0, 244.0, 60.459999084472656)]

