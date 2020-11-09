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

Root Filesystem Analysis
------------------------
.. autoclass:: scanpipe.pipelines.root_filesystems.RootfsPipeline()
    :members:

Load Inventory From Scan
------------------------
.. autoclass:: scanpipe.pipelines.scan_inventory.CollectInventoryFromScanCodeScan()
    :members:
