ScanCode.io Documentation
=========================

ScanCode.io provides a Web UI and API to run and review complex scans in rich scripted
pipelines, on different kinds of containers, docker images, package archives, manifests
etc, to get information on licenses, copyrights, sources, and vulnerabilities.

ScanCode.io provides an easy-to-use front-end to ScanCode Toolkit and other AboutCode
projects.The flexible pipeline technology supports advanced scanning tasks such as
container scanning and deploy-to-develop analysis. You can run ScanCode.io in a Docker
container or install it on a Linux server. It provides full support for generating and
consuming CycloneDX and SPDX SBOMs.

Documentation overview
~~~~~~~~~~~~~~~~~~~~~~

The overview below outlines how the documentation is structured
to help you know where to look for certain things.

.. rst-class:: clearfix row

.. rst-class:: column column2 top-left

Getting started
~~~~~~~~~~~~~~~~~~~~~~

Start here if you are new to ScanCode.

- :ref:`quickstart`
- :ref:`introduction`
- :ref:`installation`
- :ref:`contributing`
- :ref:`user_interface`

.. rst-class:: column column2 top-right

Tutorials
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Learn via practical step-by-step guides.

- :ref:`tutorial_web_ui_analyze_docker_image`
- :ref:`tutorial_web_ui_review_scan_results`
- :ref:`tutorial_cli_analyze_docker_image`
- :ref:`tutorial_api_analyze_package_archive`
- :ref:`tutorial_license_policies`
- :ref:`tutorial_vulnerablecode_integration`
- :ref:`tutorial_web_ui_symbol_and_string_collection`
- :ref:`tutorial_cli_end_to_end_scanning_to_dejacode`

.. rst-class:: column column2 bottom-left

Reference Docs
~~~~~~~~~~~~~~~~~~

Reference documentation for scancode features and customizations.

- :ref:`built_in_pipelines`
- :ref:`custom_pipelines`
- :ref:`project_configuration`
- :ref:`inputs`
- :ref:`output_files`
- :ref:`command_line_interface`
- :ref:`rest_api`
- :ref:`policies`
- :ref:`data_model`
- :ref:`automation`
- :ref:`webhooks`
- :ref:`scancodeio_settings`
- :ref:`recognized_distros_os_images`

.. rst-class:: column column2 bottom-right

Explanations
~~~~~~~~~~~~~~~~~~

Consult the reference to understand ScanCode.io concepts.

- :ref:`scanpipe_concepts`
- :ref:`scanpipe_pipes`

.. rst-class:: row clearfix

Misc
~~~~~~~~~~~~~~~

- :ref:`faq`
- :ref:`changelog`

.. include:: improve-docs.rst


Indices and tables
==================

* :ref:`genindex`
* :ref:`search`

.. toctree::
    :maxdepth: 2
    :hidden:

    quickstart
    introduction
    installation
    user-interface
    faq
    contributing
    changelog
    tutorial_web_ui_analyze_docker_image
    tutorial_web_ui_review_scan_results
    tutorial_cli_analyze_docker_image
    tutorial_cli_analyze_codebase
    tutorial_api_analyze_package_archive
    tutorial_license_policies
    tutorial_vulnerablecode_integration
    tutorial_web_ui_symbol_and_string_collection
    tutorial_cli_end_to_end_scanning_to_dejacode
    scanpipe-concepts
    built-in-pipelines
    custom-pipelines
    scanpipe-pipes
    project-configuration
    inputs
    output-files
    command-line-interface
    rest-api
    policies
    data-models
    automation
    webhooks
    application-settings
    distros-os-images
