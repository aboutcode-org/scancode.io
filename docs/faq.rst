.. _faq:

FAQs
====

You can't find what you're looking for? Below you'll find answers to a few of
our frequently asked questions.

How can I run a scan?
---------------------

You simply start by creating a :ref:`new project <user_interface_create_new_project>`
and run the appropriate pipeline.

ScanCode.io offers several :ref:`built_in_pipelines` depending on your input:

- Docker image
- Codebase drop
- Package archive
- Root filesystem
- ScanCode-toolkit results

What is the difference between scan_codebase and scan_package pipelines?
------------------------------------------------------------------------

The key differences are that the ``scan_package`` pipeline treats the input
as if it were a single package, such as a package archive, and computes a
**License clarity** and a **Scan summary** to aggregate the package scan data:

.. image:: images/license-clarity-scan-summary.png

In contrast, the ``scan_codebase`` pipeline is more of a general purpose pipeline and
make no such single package assumption. It does not not compute such summary.

You can also have a look at the different steps for each pipeline from the
:ref:`built_in_pipelines` documentation:

 - :ref:`pipeline_scan_package`
 - :ref:`pipeline_scan_codebase`

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

The pipeline documentation is available at :ref:`pipeline_docker` and its source code
at `docker.py <https://github.com/nexB/scancode.io/blob/main/scanpipe/pipelines/docker.py>`_.
It is hopefully designed to be simple and readable code.

I am unable to run ScanCode.io on Windows?
------------------------------------------

Unfortunately, we never tested nor support Windows. Please refer to our
:ref:`installation` section for more details on how to install ScanCode.io
locally.

Is it possible to compare scan results?
---------------------------------------

At the moment, you can only download full reports in JSON and XLSX formats.
Please refer to our :ref:`output_files` section for more details on the output formats.

How can I trigger a pipeline scan from a CI/CD, such as Jenkins, TeamCity or Azure Devops?
------------------------------------------------------------------------------------------

You can use the :ref:`rest_api` to automate your project or pipeline management.
