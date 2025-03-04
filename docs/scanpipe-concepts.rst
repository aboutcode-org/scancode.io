.. _scanpipe_concepts:

ScanPipe Concepts
=================

Project
-------

A **project** encapsulates the analysis of software code:

- It has a :ref:`project_workspace`, which is a directory that contains the
  software code files under analysis.
- It makes use of one or more **code analysis** :ref:`pipelines_concept` scripts to
  automate the code analysis process.
- It tracks :ref:`codebase_resources`, i.e. its **code files and directories**
- It tracks :ref:`discovered_packages`, i.e. **system and application packages**
  origin and license discovered in the codebase.

In the database, **a project is identified by its unique name**.

.. note::
    Multiple analysis pipelines can be run on a single project.

.. _project_workspace:

Project workspace
-----------------

A project workspace is the root directory where **a project's files are stored**.

The following directories exist under the workspace directory:

- :guilabel:`input/` contains all uploaded files used as the input of a project,
  such as a codebase archive.
- :guilabel:`codebase/` contains files and directories - i.e. resources -
  tracked as CodebaseResource records in the database.
- :guilabel:`output/` contains any output files created by the pipelines,
  including reports, scan results, etc.
- :guilabel:`tmp/` is a scratch pad for temporary files generated during
  pipelines runs.

.. _pipelines_concept:

Pipelines
---------

A pipeline is a Python script that contains a series of steps, which are
executed sequentially to **perform a code analysis**.

It usually starts with the uploaded input files, which might need to be
extracted first. Then, it generates ``CodebaseResource`` records in the database
accordingly.

Those resources can then be **analyzed, scanned, and matched** as needed.
Analysis results and reports are eventually posted at the end of a pipeline run.

All :ref:`built_in_pipelines` are located in the ``scanpipe.pipelines`` module.
Each pipeline consists of a Python script and includes one subclass of the
``Pipeline`` class.
Each step is a method of the ``Pipeline`` class.
The execution order of the steps - or the sequence of steps execution - is
declared through the ``steps`` class attribute.

.. tip::
    Refer to :ref:`custom_pipelines` for details about adding custom pipelines
    to ScanCode.io.

.. note::
    You can assign one or more pipelines to a project as a sequence.

Pipes
-----

As mentioned above, pipelines include a group of operations—Pipes—that are
combined in a chain-like fashion and executed in orderly manner.
Pipes are simply the building blocks of a given pipeline.

For example, the following operations—Steps—are included in the RootFS pipeline, and
they are leveraging pipes to accomplish pre-defined tasks::

    from scanpipe.pipelines import Pipeline
    from scanpipe.pipes import flag
    from scanpipe.pipes import rootfs
    from scanpipe.pipes import scancode

    class RootFS(Pipeline):
        [...]

        def flag_empty_files(self):
            """
            Flags empty files.
            """
            flag.flag_empty_files(self.project)

        def scan_for_application_packages(self):
            """
            Scans unknown resources for packages information.
            """
            scancode.scan_for_application_packages(self.project)


.. note::
    All **built-in pipes** are located in the ``scanpipe.pipes`` module.
    Pipes are grouped by type in modules, e.g. ``codebase``, ``input``, ``output``,
    ``scancode``.

    Refer to our :ref:`scanpipe_pipes` section for information about available
    pipes and their usage.

.. _codebase_resources:

Codebase Resources
------------------

A project ``Codebase Resources`` are records of its **code files and directories**.
``CodebaseResource`` is a database model and each record is identified by its path
under the project workspace.

The following are some of the ``CodebaseResource`` attributes:

- A **status**, which is used to track the analysis status for this resource.
- A **type**, such as a file, a directory or a symlink
- Various attributes to track detected **copyrights**, **license expressions**,
  **copyright holders**, and **related packages**.

.. note::
    Please note that `ScanCode-toolkit <https://github.com/aboutcode-org/scancode-toolkit>`_
    use the same attributes and attribute names for files.

.. _discovered_packages:

Discovered Packages
-------------------

A project ``Discovered Packages`` are records of the **system and application packages**
discovered in the code under analysis.
``DiscoveredPackage`` is a database model and each record is identified by its ``Package URL``.
``Package URL`` is a fundamental effort to create informative identifiers for
software packages, such as Debian, RPM, npm, Maven, or PyPI packages.
See https://github.com/package-url for more details.

The following are some of the ``DiscoveredPackage`` attributes:

- A type, name, version (all Package URL attributes)
- A homepage_url, download_url, and other URLs
- Checksums, such as SHA1, MD5
- Copyright, license_expression, and declared_license

.. note::
    Please note that `ScanCode-toolkit <https://github.com/aboutcode-org/scancode-toolkit>`_
    use the same attributes and attribute names for packages.
