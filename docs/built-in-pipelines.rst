.. _built_in_pipelines:

Built-in Pipelines
==================

As you may already know that pipelines are Python scripts that perform code
analysis by executing a sequence of steps. ScanCode.io offers the following
built-in—available—pipelines:

.. _pipeline_base_class:

Pipeline Base Class
-------------------
.. autoclass:: scanpipe.pipelines.Pipeline()
    :members:
    :member-order: bysource

.. _pipeline_docker:

Docker Image Analysis
---------------------
.. autoclass:: scanpipe.pipelines.docker.Docker()
    :members:
    :member-order: bysource

.. _pipeline_docker_windows:

Docker Windows Image Analysis
-----------------------------
.. autoclass:: scanpipe.pipelines.docker_windows.DockerWindows()
    :members:
    :member-order: bysource

.. _pipeline_find_vulnerabilities:

Find Vulnerabilities
--------------------
.. autoclass:: scanpipe.pipelines.find_vulnerabilities.FindVulnerabilities()
    :members:
    :member-order: bysource

.. _pipeline_inspect_manifest:

Inspect Manifest
----------------
.. autoclass:: scanpipe.pipelines.inspect_manifest.InspectManifest()
    :members:
    :member-order: bysource

.. _pipeline_load_inventory:

Load Inventory From Scan
------------------------
.. autoclass:: scanpipe.pipelines.load_inventory.LoadInventory()
    :members:
    :member-order: bysource

.. _pipeline_root_filesystems:

Root Filesystem Analysis
------------------------
.. autoclass:: scanpipe.pipelines.root_filesystems.RootFS()
    :members:
    :member-order: bysource

.. _pipeline_scan_codebase:

Scan Codebase
-------------
.. autoclass:: scanpipe.pipelines.scan_codebase.ScanCodebase()
    :members:
    :member-order: bysource

.. _pipeline_scan_package:

Scan Package
------------
.. autoclass:: scanpipe.pipelines.scan_package.ScanPackage()
    :members:
    :member-order: bysource
