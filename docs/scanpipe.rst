ScanPipe
========

Project
-------

A project encapsulate all analysis processing on one or multiple source of data.
Multiple analysis pipelines can be run on a single project.

Create a project from the `/api/projects/` API endpoint.
An `Input file` can be provided as data source along a `Pipeline` that
would start on project creation.

Project workspace
-----------------

When adding a project, the following workspace structure is created:

 - `input/` contains all the uploaded files used as data source for the project.
 - `codebase/` contains the resources created as CodebaseResource in the database.
 - `output/` contains all output files: reports, scan results, etc...
 - `tmp/` stores the temporary files generated during the pipeline analysis, its content is removed
   at the end of a successful pipeline.

Pipelines
---------

A pipeline is an ordered series of steps run to perform data analysis.
It usually starts from uploaded input files and generates CodebaseResource in
the database accordingly.
Those resources can then be analyzed, scanned, matched, ...
Results and reports are then extracted from this resources analysis.

All pipelines are located in the `pipelines` module and consist of a python
file including one subclass of the Pipeline class.

One or more pipelines can be assigned to a project. If the currently run pipeline
complete successfully, the next in queue is run automatically until all pipelines
are executed.

Run from the command line
-------------------------

Once a project is created, a pipeline can be run or resume directly from the
command line.
This can be useful for debugging purposes as you can visualize the progress of
the run, and resume a failed run following some code modifications:

Start a new pipeline::

    $ python scanpipe/pipelines/docker.py run --project [PROJECT_UUID]

Resume a failed run::

    $ python scanpipe/pipelines/docker.py resume
