.. _built_in_pipelines:

Built-in Pipelines
==================

Pipelines in ScanCode.io are Python scripts that facilitate code analysis by
executing a sequence of steps. The platform provides the following built-in pipelines:

.. tip::
    If you are unsure which pipeline suits your requirements best, check out the
    :ref:`faq_which_pipeline` section for guidance.

.. _pipeline_base_class:

Pipeline Base Class
-------------------
.. autoclass:: scanpipe.pipelines.Pipeline()
    :members:
    :member-order: bysource

.. _pipeline_analyze_docker_image:

Analyse Docker Image
--------------------
.. autoclass:: scanpipe.pipelines.docker.Docker()
    :members:
    :member-order: bysource

.. _pipeline_analyze_root_filesystem:

Analyze Root Filesystem or VM Image
-----------------------------------
.. autoclass:: scanpipe.pipelines.root_filesystem.RootFS()
    :members:
    :member-order: bysource

.. _analyze_windows_docker_image:

Analyse Docker Windows Image
----------------------------
.. autoclass:: scanpipe.pipelines.docker_windows.DockerWindows()
    :members:
    :member-order: bysource

.. _pipeline_find_vulnerabilities:

Find Vulnerabilities (addon)
----------------------------

.. warning::
    This pipeline requires access to a VulnerableCode database.
    Refer to :ref:`scancodeio_settings_vulnerablecode` to configure access to
    VulnerableCode in your ScanCode.io instance.

.. autoclass:: scanpipe.pipelines.find_vulnerabilities.FindVulnerabilities()
    :members:
    :member-order: bysource

.. _pipeline_inspect_elf:

Inspect ELF Binaries (addon)
----------------------------
.. autoclass:: scanpipe.pipelines.inspect_elf_binaries.InspectELFBinaries()
    :members:
    :member-order: bysource

.. _pipeline_inspect_packages:

Inspect Packages
----------------
.. autoclass:: scanpipe.pipelines.inspect_packages.InspectPackages()
    :members:
    :member-order: bysource

.. _pipeline_load_inventory:

Load Inventory
--------------
.. autoclass:: scanpipe.pipelines.load_inventory.LoadInventory()
    :members:
    :member-order: bysource

.. _pipeline_load_sbom:

Load SBOM
---------
.. autoclass:: scanpipe.pipelines.load_sbom.LoadSBOM()
    :members:
    :member-order: bysource

.. _pipeline_resolve_dependencies:

Resolve Dependencies
--------------------
.. autoclass:: scanpipe.pipelines.resolve_dependencies.ResolveDependencies()
    :members:
    :member-order: bysource

.. _pipeline_map_deploy_to_develop:

Map Deploy To Develop
---------------------

.. warning::
    This pipeline requires input files to be tagged with the following:

    - "from": For files related to the source code (also known as "develop").
    - "to": For files related to the build/binaries (also known as "deploy").

    Tagging your input files varies based on whether you are using the REST API,
    UI, or CLI. Refer to the :ref:`faq_tag_input_files` section for guidance.

.. autoclass:: scanpipe.pipelines.deploy_to_develop.DeployToDevelop()
    :members:
    :member-order: bysource

.. _pipeline_match_to_purldb:

Match to PurlDB (addon)
-----------------------

.. warning::
    This pipeline requires access to a PurlDB service.
    Refer to :ref:`scancodeio_settings_purldb` to configure access to PurlDB in your
    ScanCode.io instance.

.. autoclass:: scanpipe.pipelines.match_to_purldb.MatchToPurlDB()
    :members:
    :member-order: bysource

.. _pipeline_populate_purldb:

Populate PurlDB (addon)
-----------------------

.. warning::
    This pipeline requires access to a PurlDB service.
    Refer to :ref:`scancodeio_settings_purldb` to configure access to PurlDB in your
    ScanCode.io instance.

.. autoclass:: scanpipe.pipelines.populate_purldb.PopulatePurlDB()
    :members:
    :member-order: bysource

.. _pipeline_scan_codebase:

Scan Codebase
-------------
.. autoclass:: scanpipe.pipelines.scan_codebase.ScanCodebase()
    :members:
    :member-order: bysource

.. _pipeline_scan_single_package:

Scan Single Package
-------------------
.. autoclass:: scanpipe.pipelines.scan_single_package.ScanSinglePackage()
    :members:
    :member-order: bysource
