.. _scanpipe_pipelines:

Pipelines
=========

Pipeline Base Class
-------------------
.. autoclass:: scanpipe.pipelines.Pipeline()
    :members:

Docker Image Analysis
---------------------
.. autoclass:: scanpipe.pipelines.docker.DockerPipeline()
    :members:

Load Inventory From Scan
------------------------
.. autoclass:: scanpipe.pipelines.load_inventory.LoadInventoryFromScanCodeScan()
    :members:

Root Filesystem Analysis
------------------------
.. autoclass:: scanpipe.pipelines.root_filesystems.RootfsPipeline()
    :members:

Scan Codebase
-------------
.. autoclass:: scanpipe.pipelines.scan_codebase.ScanCodebase()
    :members:
