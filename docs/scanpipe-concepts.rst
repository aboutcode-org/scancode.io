.. _scanpipe_concepts:

ScanPipe Concepts
=================

Project
-------

A **project** encapsulates the analysis of software code:

- it has a **workspace** which is a directory that contains the software code files under analysis
- it is related to one or more **code analysis pipelines** scripts to automate its analysis
- it tracks ``Codebase Resources`` e.g. its **code files and directories**
- it tracks ``Discovered Packages`` e.g. its the **system and application packages** origin and license discovered in the codebase

In the database, **a project is identified by its unique name**.

.. note::
    Multiple analysis pipelines can be run on a single project.


Project workspace
-----------------

A project workspace is the root directory where **all the project files are stored**.

The following directories exists under this workspace directory:

- :guilabel:`input/` contains all the original uploaded and input files used of the project. For instance, it could be a codebase archive.
- :guilabel:`codebase/` contains the files and directories (aka. resources) tracked as CodebaseResource records in the database.
- :guilabel:`output/` contains all output files created by the pipelines: reports, scan results, etc.
- :guilabel:`tmp/` is a scratch pad for temporary files generated during the pipelines runs.


Pipelines
---------

A pipeline is a Python script that contains a series of steps from start to end
to run in order to **perform a code analysis**.

It usually starts from the uploaded input files, and may extract these then
generates ``CodebaseResource`` records in the database accordingly.

Those resources can then be **analyzed, scanned, and matched** as needed.
Analysis results and reports are eventually posted at the end of a pipeline run.

All pipelines are located in the ``scanpipe.pipelines`` module.
Each pipeline consist of a Python script including one subclass of the ``Pipeline`` class.
Each step is a method of the ``Pipeline`` class decorated with a ``@step`` decorator.
At its end, a step states which is the next step to execute.

.. note::
    One or more pipelines can be assigned to a project as a sequence.
    If one pipeline of a sequence completes successfully, the next pipeline in
    the queue for this project is launched automatically and this until all
    the scheduled pipelines have executed.


Codebase Resources
------------------

A project ``Codebase Resources`` are records of its **code files and directories**.
``CodebaseResource`` is a database model and each record is identified by its path
under the project workspace.

Some of the ``CodebaseResource`` interesting attributes are:

- a **status** used to track the analysis status for this resource.
- a **type** (such as file, directory or symlink)
- various attributes to track detected **copyrights**, **license expressions**, **copyright holders**, and **related packages**.

.. note::
    In general the attributes and their names are the same that are used in
    `ScanCode-toolkit <https://github.com/nexB/scancode-toolkit>`_ for files.


Discovered Packages
-------------------

A project ``Discovered Packages`` are records of the **system and application packages**
discovered in its code.
``DiscoveredPackage`` is a database model and each record is identified by its ``Package URL``.
``Package URL`` is a grassroot efforts to create informative identifiers for software
packages such as Debian, RPM, npm, Maven, or PyPI packages.
See https://github.com/package-url for details.

Some of the ``DiscoveredPackage`` interesting attributes are:

- type, name, version (all Package URL attributes)
- homepage_url, download_url and other URLs
- checksums (such as SHA1, MD5)
- copyright, license_expression, declared_license

.. note::
    In general the attributes and their names are the same that are used in
    `ScanCode-toolkit <https://github.com/nexB/scancode-toolkit>`_ for packages.
