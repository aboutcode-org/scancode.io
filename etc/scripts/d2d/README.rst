Run ScanCode.io Mapping Script
================================

This script executes the ``map_deploy_to_develop`` mapping workflow from
ScanCode.io inside a Docker container. It optionally spins up a temporary
PostgreSQL instance when needed. The script copies the specified input files to
a working directory, runs the mapping, writes the output to a file, and cleans
up afterward.

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


Example
-------

Run mapping without database:

.. code-block:: bash

   ./map-deploy-to-develop.sh ./from.tar.gz ./to.whl results.json

Run mapping with database on a custom port:

.. code-block:: bash

   ./map-deploy-to-develop.sh ./from.tar.gz ./to.whl output.json --options "Python,Java" --spin-db --port 5433

Script Actions
--------------

1. Validates required arguments
2. Starts PostgreSQL in Docker (if ``spin-db=true``)
3. Creates a temporary working directory: ``./d2d``
4. Copies input files into working directory
5. Runs ScanCode.io mapping step:

   .. code-block:: text

      run map_deploy_to_develop:<D2D_OPTIONS> \
          "/code/<from-file>:from,/code/<to-file>:to"

6. Writes mapping output into ``output-file``
7. Cleans up temp directory
8. Stops DB container if it was started

Dependencies
------------

* Bash
* Docker
* Local filesystem permissions for creating ``./d2d`` and writing output


Before running the script:
----------------------------------

Ensure the script has execute permissions:

.. code-block:: bash

      sudo su -
      chmod +x map-deploy-to-develop.sh

Then execute:

.. code-block:: bash

      ./map-deploy-to-develop.sh ...
