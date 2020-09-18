ScanPipe Concepts
=================

Project
-------

A project is the encapsulates the analysis of software code:

- it has a workspace which is a directory that contains the software code files under analysis
- it is related to one or more code analysis pipelines scripts to automate its analysis
- it tracks the project Codebase Resources e.g. its code files and directories
- it tracks the project Discovered Packages e.g. its the system and application packages origin and license discovered in the codebase

Multiple analysis pipelines can be run on a single project.

In the database, a project is identified by its unique name.


Project workspace
-----------------

A project workspace is the root directory where all the project files are stored.

The following directories exists under this directory:

- `input/` contains all the original uploaded and input files used of the project. For instance, it could be a codebase archive.
- `codebase/` contains the files and directories (aka. resources) tracked as CodebaseResource records in the database.
- `output/` contains all output files created by the pipelines: reports, scan results, etc.
- `tmp/` is a scratch pad for temporary files generated during the pipelines runs.


Pipelines
---------

A pipeline is a Python script that contains a series of steps from start to end
to run in order perform a code analysis.

It usually starts from the uploaded input files, and may extract these then
generates CodebaseResource records in the database accordingly.

Those resources can then be analyzed, scanned, matched as needed.
Analysis results and reports are evetually posted at the end of pipeline run

For now, all pipelines are located in the `scanpipe.pipelines` module.
Each pipeline consist of a Python script including one subclass of the "Pipeline" class.
Each step is a method of the Pipeline class decorated with @step decorator.
At its end, a step states which is the next step to execute.

One or more pipelines can be assigned to a project as a sequence. 
If the one pipeline of a sequence completes successfully, the next pipeline in
queue for this project is run automatically until all pipelines are executed.


Codebase Resources
------------------

A project Codebase Resources are records of its code files and directories.
CodebaseResource is a database model and each record is identified by its path
under the project workspace.

Some of the CodebaseResource interesting attributes are:

- a status used to track the analysis status for this resource.
- a type (such as file, directory or symlink)
- various attributes to track detected copyrights, license expressions, copyright holders, related packages.

In general the attributes and their names are the same that are used in ScanCode-Toolkit for files.


Discovered Packages
-------------------

A project Discovered Packages are records of the system and application packages
discovered in its code.
DiscoveredPackage is a database model and each record is identified by its Package URL.
Package URL is a grassroot efforts to create informative identifiers for software
packages such as Debian, RPM, npm, Maven PyPI packages. See https://github.com/package-url for details.


Some of the DiscoveredPackage interesting attributes are:

- type, name, version (all Package URL attributes)
- homepage_url, download_url and other URLs
- checksums (such as SHA1, MD5)
- copyright, license_expression, declared_license


In general the attributes and their names are the same that are used in ScanCode-Toolkit for packages.
