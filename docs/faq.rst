.. _faq:

FAQs
====

You can't find what you're looking for? Below you'll find answers to a few of
our frequently asked questions.

How can I run a scan?
---------------------

You simply start by creating a :ref:`new project <user_interface_create_new_project>`
and run the appropriate pipeline.

ScanCode.io offers several :ref:`built_in_pipelines` depending on your input, see above.

.. _faq_which_pipeline:

Which pipeline should I use?
----------------------------

Selecting the right pipeline for your needs depends primarily on the type of input
data you have available.
Here are some general guidelines based on different input scenarios:

- If you have a **Docker image** as input, use the
  :ref:`analyze_docker_image <pipeline_analyze_docker_image>` pipeline.
- For a full **codebase compressed as an archive**, choose the
  :ref:`scan_codebase <pipeline_scan_codebase>` pipeline.
- If you have a **single package archive**, opt for the
  :ref:`scan_single_package <pipeline_scan_single_package>` pipeline.
- When dealing with a **Linux root filesystem** (rootfs), the
  :ref:`analyze_root_filesystem_or_vm_image <pipeline_analyze_root_filesystem>` pipeline
  is the appropriate choice.
- For processing the results of a **ScanCode-toolkit scan** or **ScanCode.io scan**,
  use the :ref:`load_inventory <pipeline_load_inventory>` pipeline.
- When you have **manifest files**, such as a
  **CycloneDX BOM, SPDX document, lockfile**, etc.,
  use the :ref:`inspect_packages <pipeline_inspect_packages>` pipeline.
- For scenarios involving both a **development and deployment codebase**, consider using
  the :ref:`map_deploy_to_develop <pipeline_map_deploy_to_develop>` pipeline.

These pipelines will automatically execute the necessary steps to scan and create the
packages, dependencies, and resources for your project based on the input data provided.

After executing one of the pipelines mentioned above, you have the option to
**augment your project's data** by executing additional pipelines, often referred to
as **addon** pipelines.
These additional pipelines offer further enhancements and modifications to your
existing data, allowing for more comprehensive analysis and insights.

- If you wish to **find vulnerabilities** for packages and dependencies, you can use the
  :ref:`find_vulnerabilities <pipeline_find_vulnerabilities>` pipeline.
  Note that setting up :ref:`VulnerableCode <scancodeio_settings_vulnerablecode>` is
  required for this pipeline to function properly.

- To **populate PurlDB with the packages discovered in your project**,
  use the :ref:`populate_purldb <pipeline_populate_purldb>` pipeline.
  Before executing this pipeline, make sure to set up
  :ref:`PurlDB <scancodeio_settings_purldb>`.

- To **match your project codebase resources to PurlDB for Package matches**,
  utilize the :ref:`match_to_purldb <pipeline_match_to_purldb>` pipeline.
  It's essential to set up :ref:`PurlDB <scancodeio_settings_purldb>` before executing
  this pipeline.

What is the difference between scan_codebase and scan_single_package pipelines?
-------------------------------------------------------------------------------

The key differences are that the
:ref:`scan_single_package <pipeline_scan_single_package>` pipeline
treats the input as if it were a single package, such as a package archive, and
computes a **License clarity** and a **Scan summary** to aggregate the package scan
data:

.. image:: images/license-clarity-scan-summary.png

In contrast, the :ref:`scan_codebase <pipeline_scan_codebase>` pipeline is more of a
general purpose pipeline and make no such single package assumption.
It does not not compute such summary.

You can also have a look at the different steps for each pipeline from the
:ref:`built_in_pipelines` documentation.

Can I run multiple pipelines in parallel?
-----------------------------------------

Yes, you can run multiple pipelines in parallel by starting your Docker containers
with the desired number of workers using the following command::

    docker compose up --scale worker=2

.. note:: You can also add extra workers by running the command while the ScanCode.io
   services are already running. For example, to add 2 extra workers to the 2
   currently running ones, use the following command::

        sudo docker compose up --scale worker=4

Can I pause/resume a running pipeline?
--------------------------------------

You can stop/terminate a running pipeline but it will not be possible to resume it.
Although, as a workaround if you run ScanCode.io on desktop or laptop,
you can pause/unpause the running Docker containers with::

    docker compose pause  # to pause/suspend
    docker compose unpause  # to unpause/resume

What tool does ScanCode.io use to analyze docker images?
--------------------------------------------------------

The following tools and libraries are used during the docker images analysis pipeline:

 - `container-inspector <https://github.com/nexB/container-inspector>`_ and
   `debian-inspector <https://github.com/nexB/debian-inspector>`_ for handling containers
   and distros.
 - `fetchcode-container <https://pypi.org/project/fetchcode-container/>`_ to download
   containers and images.
 - `scancode-toolkit <https://github.com/nexB/scancode-toolkit>`_ for application
   package scans and system package scans.
 - `extractcode <https://github.com/nexB/extractcode>`_ for universal and reliable
   archive extraction.
 - Specific handling of windows containers is done in
   `scancode-toolkit <https://github.com/nexB/scancode-toolkit>`_ to process the windows registry.
 - Secondary libraries and plugins from
   `scancode-plugins <https://github.com/nexB/scancode-plugins>`_.

The pipeline documentation is available at :ref:`pipeline_analyze_docker_image` and
its source code at
`docker.py <https://github.com/nexB/scancode.io/blob/main/scanpipe/pipelines/docker.py>`_.
It is hopefully designed to be simple and readable code.

Am I able to run ScanCode.io on Windows?
----------------------------------------

Yes, you can use the :ref:`run_with_docker` installation. However, please be sure to
carefully read the warnings, as running on Windows may have certain limitations or
challenges.

Is it possible to compare scan results?
---------------------------------------

At the moment, you can only download full reports in JSON and XLSX formats.
Please refer to our :ref:`output_files` section for more details on the output formats.

How can I trigger a pipeline scan from a CI/CD, such as Jenkins, TeamCity or Azure Devops?
------------------------------------------------------------------------------------------

You can refer to the :ref:`automation` to automate your projects management.

Also, A new GitHub action is available at
`scancode-action repository <https://github.com/nexB/scancode-action>`_
to run ScanCode.io pipelines from your GitHub Workflows.

.. _faq_tag_input_files:

How to tag input files?
-----------------------

Certain pipelines, including the :ref:`pipeline_map_deploy_to_develop`, require input
files to be tagged. This section outlines various methods to tag input files based on
your project management context.

Using download URLs as inputs
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

You can provide tags using the "#<fragment>" section of URLs. This tagging method is
universally applicable in the User Interface, REST API, and Command Line Interface.

Example:

.. code-block::

    https://url.com/sources.zip#from
    https://url.com/binaries.zip#to

Uploading local files
^^^^^^^^^^^^^^^^^^^^^

There are multiple ways to tag input files when uploading local files:

- **User Interface:** Utilize the "Edit flag" link in the "Inputs" panel of the Project
  details view.

- **REST API:** Use the "upload_file_tag" field in addition to the "upload_file" field.

- **Command Line Interface:** Tag uploaded files using the "filename:tag" syntax.
  Example: ``--input-file path/filename:tag``.
