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

:ref:`getting-started`
~~~~~~~~~~~~~~~~~~~~~~

Start here if you are new to ScanCode.

- :ref:`quickstart`

 - :ref:`introduction`
 - :ref:`installation`
 - :ref:`user-interface`

- :ref:`faq`

.. rst-class:: column column2 top-right

:ref:`tutorials`
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Learn via practical step-by-step guides.

- :ref:`tutorial_web_ui_analyze_docker_image`
- :ref:`tutorial_web_ui_review_scan_result`
- :ref:`tutorial_cli_analyze_docker_image`
- :ref:`tutorial_api_analyze_package_archive`
- :ref:`tutorial_license_policies`
- :ref:`tutorial_vulnerablecode_integration`
- :ref:`tutorial_web_ui_symbol_and_string_collection`
- :ref:`tutorial_cli_end_to_end_scanning_to_dejacode`

.. rst-class:: column column2 bottom-left

:ref:`how-to-guides`
~~~~~~~~~~~~~~~~~~~~

Helps you accomplish things.

- :ref:`contributing`

.. rst-class:: column column2 bottom-right

:ref:`reference` and :ref:`explanation`
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Consult the reference to understand ScanCode.io concepts.

- :ref:`scanpipe-concepts`
- :ref:`built-in-pipelines`
- :ref:`custom-pipelines`
- :ref:`scanpipe-pipes`
- :ref:`project-configuration`
- :ref:`inputs`
- :ref:`output-files`
- :ref:`command-line-interface`
- :ref:`rest-api`
- :ref:`policies`
- :ref:`data-models`
- :ref:`automation`
- :ref:`webhooks`
- :ref:`application-settings`
- :ref:`distros-os-images`

.. rst-class:: row clearfix

Improving Documentation
~~~~~~~~~~~~~~~~~~~~~~~

.. include::  /rst-snippets/improve-docs.rst

.. toctree::
   :maxdepth: 2
   :hidden:

   getting-started/index
   tutorials/index
   how-to-guides/index
   reference/index
   explanation/index

   changelog

Indices and tables
==================

* :ref:`genindex`
* :ref:`search`
