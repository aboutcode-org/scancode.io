==============================================================================
Run ScanCode.io Pipelines in Docker (D2D Runner)
==============================================================================

This script helps execute **ScanCode.io** pipelines in isolated Docker containers,
using a local PostgreSQL database and a working directory named ``./d2d``.

-------------------------------------------------------------------------------
Prerequisites
-------------------------------------------------------------------------------

1. **Python 3.8+** must be installed  
2. **Docker** must be installed and accessible via ``sudo`` or user group  

-------------------------------------------------------------------------------
Environment Variables
-------------------------------------------------------------------------------

.. list-table::
   :widths: 25 75
   :header-rows: 1

   * - Variable
     - Description
   * - ``SCANCODE_DB_PASS``
     - Database password (default: ``scancode``)
   * - ``SCANCODE_DB_USER``
     - Database user (default: ``scancode``)

-------------------------------------------------------------------------------
Usage Example
-------------------------------------------------------------------------------

.. code-block:: bash

   sudo su -
   python3 etc/scripts/run_d2d_scio.py \
       --input-file ./path/from/from-intbitset.tar.gz:from \
       --input-file ./path/to/to-intbitset.whl:to \
       --option Python \
       --output res1.json

-------------------------------------------------------------------------------
Parameters
-------------------------------------------------------------------------------

.. list-table::
   :widths: 25 75
   :header-rows: 1

   * - Parameter
     - Description
   * - ``--input-file <path:tag>``
     - Required twice: one tagged ``:from``, one tagged ``:to``
   * - ``--option <name>``
     - Optional; e.g., ``Python``, ``Java``, ``Javascript``, ``Scala``, ``Kotlin``
   * - ``--output <file.json>``
     - Required; JSON output file for results

-------------------------------------------------------------------------------
Internal Steps
-------------------------------------------------------------------------------

1. Creates or uses the ``./d2d`` directory  
2. Copies ``from`` and ``to`` files into it  
3. Spins up a temporary **Postgres 13** container  
4. Waits for database readiness  
5. Runs **ScanCode.io** pipeline (``map_deploy_to_develop``)  
6. Saves pipeline output to the specified JSON file  
7. Cleans up containers automatically  

-------------------------------------------------------------------------------
Cleanup
-------------------------------------------------------------------------------

Containers are auto-removed, but you can verify active containers with:

.. code-block:: bash

   docker ps -a | grep scancode

If manual cleanup is needed:

.. code-block:: bash

   docker rm -f <container_id>
