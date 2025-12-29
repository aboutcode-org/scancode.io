Reference Documentation Page: D2D Options and Capabilities
=========================================================

This page lists the available d2d options and highlights the capabilities present for each optional ecosystem option.

Overview
--------

d2d (deploy-to-develop) workflows are used to map deployed artifacts (such as compiled binaries and archives)
back to their most likely source code.

The current d2d helper script runs the ``map_deploy_to_develop`` mapping workflow in ScanCode.io inside a
Docker container. It can optionally spin up a temporary PostgreSQL database when needed.

Usage
-----

.. code-block:: bash

   ./map-deploy-to-develop.sh <from-path> <to-path> <output-file> [options] <spin-db> [db-port]

Arguments
---------

+-----------------+-------------------------------------------------------------+
| Argument        | Description                                                 |
+=================+=============================================================+
| ``from-path``   | Path to the base deployment/scan file                       |
+-----------------+-------------------------------------------------------------+
| ``to-path``     | Path to the target deployment/scan file                     |
+-----------------+-------------------------------------------------------------+
| ``options``     | D2D pipeline parameters (can be empty ``""``)               |
+-----------------+-------------------------------------------------------------+
| ``output-file`` | File where ScanCode.io output will be written               |
+-----------------+-------------------------------------------------------------+
| ``spin-db``     | ``true`` = spin temp DB container, ``false`` = skip         |
+-----------------+-------------------------------------------------------------+
| ``db-port``     | Port to bind Postgres (default: ``5432``)                   |
+-----------------+-------------------------------------------------------------+

Capabilities matrix
-------------------

The helper script executes the ``map_deploy_to_develop`` mapping workflow. The exact capabilities depend on the
D2D pipeline parameters passed through the ``options`` argument.

+------------------------------------------+------------------------------+------------------------------+---------------------------+-----------------------+--------------------------+
| d2d option / parameter                   | compiled file -> source file | archive -> source directory  | binary/source symbols     | archives -> purlDB     | source files -> purlDB   |
+==========================================+==============================+==============================+===========================+=======================+==========================+
| Base mapping workflow (default)          | ✅                            | ✅                            | depends on parameters     | depends on parameters  | depends on parameters     |
+------------------------------------------+------------------------------+------------------------------+---------------------------+-----------------------+--------------------------+
| ``options`` (pipeline parameters)        | ✅                            | ✅                            | ✅/❌                       | ✅/❌                   | ✅/❌                      |
+------------------------------------------+------------------------------+------------------------------+---------------------------+-----------------------+--------------------------+
| ``spin-db=true`` (temporary DB enabled)  | ✅                            | ✅                            | depends on parameters     | depends on parameters  | depends on parameters     |
+------------------------------------------+------------------------------+------------------------------+---------------------------+-----------------------+--------------------------+
| ``spin-db=false`` (no DB container)      | ✅                            | ✅                            | depends on parameters     | depends on parameters  | depends on parameters     |
+------------------------------------------+------------------------------+------------------------------+---------------------------+-----------------------+--------------------------+
| ``db-port=<port>``                       | ✅                            | ✅                            | depends on parameters     | depends on parameters  | depends on parameters     |
+------------------------------------------+------------------------------+------------------------------+---------------------------+-----------------------+--------------------------+

Examples
--------

Run mapping without database:

.. code-block:: bash

   ./map-deploy-to-develop.sh ./from.tar.gz ./to.whl results.json "" false

Run mapping with database on a custom port:

.. code-block:: bash

   ./map-deploy-to-develop.sh ./from.tar.gz ./to.whl output.json "Python,Java" true 5433

Script actions (high-level)
---------------------------

1. Validates required arguments
2. Starts PostgreSQL in Docker (if ``spin-db=true``)
3. Creates a temporary working directory: ``./d2d``
4. Copies input files into working directory
5. Runs ScanCode.io mapping step
6. Writes mapping output into ``output-file``
7. Cleans up temp directory
8. Stops DB container if it was started

Related files
-------------

- Script: ``etc/scripts/d2d/map-deploy-to-develop.sh``
- README: ``etc/scripts/d2d/README.rst``
- Reference docs index: :doc:`index`
