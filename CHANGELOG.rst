====================
Changes by release
====================

0.2.0.dev0 - 2019-09-09
============================

This release was made possible due to considerable support from Christoph Hintermüller.

Major refactoring
-------------------------

- supporty for Python3: 3.5, 3.6 and 3.7 (in addition to Python2.7)
- package is now structured into seven modules: 

    - ``ahds`` is the main entry point
    - ``core`` defines ``Block`` and ``ListBlock`` classes as well as cross-Python variables
    - ``data_stream`` defines new data stream classes
    - ``grammar`` only specifies the grammar while
    - ``proc`` defines the grammar processor
    - ``header`` specifies the ``AmiraHeader`` class
    - ``extra`` holds classes for downstream data analysis ``Image``, ``Volume`` etc.
    - ``__init__`` specifies the top-level ``AmiraFile`` class
   
- better test coverage

New example files
-------------------------

- many more example files (thanks to Christoph Hintermüller)

New print format for Amira (R) files to console
--------------------------------------------------

- data is presented as a tree
- the provided ``ahds`` command (see documentation) provides an easy way to browse Amira (R) files
- all data now read and stored as ``numpy`` arrays

Documentation
-------------------------

- described how to use the new command line utility








