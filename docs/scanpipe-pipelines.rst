.. _scanpipe_pipelines:

Pipelines
=========

Pipeline Base Class
-------------------
.. autoclass:: scanpipe.pipelines.Pipeline()
    :members:

Docker Image Analysis
---------------------
.. autoclass:: scanpipe.pipelines.docker.Docker()
    :members:

Load Inventory From Scan
------------------------
.. autoclass:: scanpipe.pipelines.load_inventory.LoadInventory()
    :members:

Root Filesystem Analysis
------------------------
.. autoclass:: scanpipe.pipelines.root_filesystems.RootFS()
    :members:

Scan Codebase
-------------
.. autoclass:: scanpipe.pipelines.scan_codebase.ScanCodebase()
    :members:

Scan Package
------------
.. autoclass:: scanpipe.pipelines.scan_package.ScanPackage()
    :members:
