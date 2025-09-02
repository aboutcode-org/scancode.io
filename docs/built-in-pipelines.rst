.. _built_in_pipelines:

Built-in Pipelines
==================

Pipelines in ScanCode.io are Python scripts that facilitate code analysis by
executing a sequence of steps. The platform provides the following built-in pipelines:

.. note::
    Some pipelines have optional steps which are enabled only when they are
    selected explicitly.

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
.. autoclass:: scanpipe.pipelines.analyze_docker.Docker()
    :members:
    :member-order: bysource

.. _pipeline_analyze_root_filesystem:

Analyze Root Filesystem or VM Image
-----------------------------------
.. autoclass:: scanpipe.pipelines.analyze_root_filesystem.RootFS()
    :members:
    :member-order: bysource

.. _analyze_windows_docker_image:

Analyse Docker Windows Image
----------------------------
.. autoclass:: scanpipe.pipelines.analyze_docker_windows.DockerWindows()
    :members:
    :member-order: bysource

.. _pipeline_benchmark_purls:

Benchmark PURLs (addon)
-----------------------

To check an **SBOM against a list of expected Package URLs (PURLs)**:

1. **Create a new project** and provide two inputs:

   * The SBOM file you want to check.
   * A list of expected PURLs in a ``*-purls.txt`` file with one PURL per line.

     .. tip:: You may also flag any filename using the ``purls`` input tag.

2. **Run the pipelines**:

   * Select and run the ``load_sbom`` pipeline to load the SBOM.
   * Run the ``benchmark_purls`` pipeline to validate against the expected PURLs.

3. **Download the results** from the "output" section of the project.

The output file contains only the differences between the discovered PURLs and
the expected PURLs:

* Lines starting with ``-`` are missing from the project.
* Lines starting with ``+`` are unexpected in the project.

.. note::
  The ``load_sbom`` pipeline is provided as an example to benchmark external
  tools using SBOMs as inputs. You can also run ``benchmark_purls`` directly
  after any ScanCode.io pipeline to validate the discovered PURLs.

.. tip::
  You can provide multiple expected PURLs files.


.. autoclass:: scanpipe.pipelines.benchmark_purls.BenchmarkPurls()
    :members:
    :member-order: bysource


.. _pipeline_collect_strings_gettext:

Collect string with Xgettext (addon)
------------------------------------
.. autoclass:: scanpipe.pipelines.collect_strings_gettext.CollectStringsGettext()
    :members:
    :member-order: bysource

.. _pipeline_collect_symbols_ctags:

Collect symbols with Ctags (addon)
----------------------------------
.. autoclass:: scanpipe.pipelines.collect_symbols_ctags.CollectSymbolsCtags()
    :members:
    :member-order: bysource

.. _pipeline_collect_symbols_pygments:

Collect symbols, string and comments with Pygments (addon)
----------------------------------------------------------
.. autoclass:: scanpipe.pipelines.collect_symbols_pygments.CollectSymbolsPygments()
    :members:
    :member-order: bysource

.. _pipeline_collect_symbols_tree_sitter:

Collect symbols and string with Tree-Sitter (addon)
---------------------------------------------------
.. autoclass:: scanpipe.pipelines.collect_symbols_tree_sitter.CollectSymbolsTreeSitter()
    :members:
    :member-order: bysource

.. _pipeline_enrich_with_purldb:

Enrich With PurlDB (addon)
--------------------------
.. warning::
    This pipeline requires access to a PurlDB service.
    Refer to :ref:`scancodeio_settings_purldb` to configure access to PurlDB in your
    ScanCode.io instance.

.. autoclass:: scanpipe.pipelines.enrich_with_purldb.EnrichWithPurlDB()
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

.. _pipeline_match_to_matchcode:

Match to MatchCode (addon)
--------------------------
.. warning::
    This pipeline requires access to a MatchCode.io service.
    Refer to :ref:`scancodeio_settings_matchcodeio` to configure access to
    MatchCode.io in your ScanCode.io instance.

.. autoclass:: scanpipe.pipelines.match_to_matchcode.MatchToMatchCode()
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

.. _pipeline_publish_to_federatedcode:

Publish To FederatedCode (addon)
--------------------------------
.. warning::
    This pipeline requires access to a FederatedCode service.
    Refer to :ref:`scancodeio_settings_federatedcode` to configure access to
    FederatedCode in your ScanCode.io instance.

.. autoclass:: scanpipe.pipelines.publish_to_federatedcode.PublishToFederatedCode()
    :members:
    :member-order: bysource

.. _pipeline_scan_codebase:

Scan Codebase
-------------
.. autoclass:: scanpipe.pipelines.scan_codebase.ScanCodebase()
    :members:
    :member-order: bysource

.. _pipeline_scan_for_virus:

Scan For Virus
--------------
.. autoclass:: scanpipe.pipelines.scan_for_virus.ScanForVirus()
    :members:
    :member-order: bysource

.. _pipeline_scan_single_package:

Scan Single Package
-------------------
.. autoclass:: scanpipe.pipelines.scan_single_package.ScanSinglePackage()
    :members:
    :member-order: bysource

Fetch Scores (addon)
--------------------
.. warning::
    This pipeline is preconfigured to access the "OpenSSF Scorecard API"
    available at https://api.securityscorecards.dev/

.. autoclass:: scanpipe.pipelines.fetch_scores.FetchScores()
    :members:
    :member-order: bysource
