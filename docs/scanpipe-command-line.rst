.. _scanpipe_command_line:

ScanPipe Commands Help
======================

The main entry point is the :guilabel:`scanpipe` command which is available
directly when you are in the activated virtualenv or at this path:
``<scancode.io_root_dir>/bin/scanpipe``


`$ scanpipe --help`
-------------------

List all the sub-commands available (including Django built-in commands).
ScanPipe's own commands are listed under the ``[scanpipe]`` section::

    $ scanpipe --help
    ...
    [scanpipe]
        add-input
        add-pipeline
        create-project
        graph
        output
        run
        show-pipeline


`$ scanpipe <subcommand> --help`
--------------------------------

Display help for the provided subcommand.

For example::

    $ scanpipe create-project --help
    usage: scanpipe create-project [--pipeline PIPELINES] [--input INPUTS] name

    Create a ScanPipe project.
    
    positional arguments:
      name                  Project name.


`$ scanpipe create-project <name>`
----------------------------------

Create a ScanPipe project using ``<name>`` as a Project name. The name must
be unique.

Optional arguments:

- ``--pipeline PIPELINES``  Pipelines locations to add on the project.

- ``--input INPUTS``  Input file locations to copy in the :guilabel:`input/` workspace
  directory.

- ``--run``  Start running the pipelines right after project creation.

.. warning::
    The pipelines are added and will be running in the order of the provided options.

`$ scanpipe add-input --project PROJECT <input ...>`
----------------------------------------------------

Copy the file found at the ``<input>`` path to the project named ``PROJECT`` workspace
:guilabel:`input/` directory.
You can use more than one ``<input>`` to copy multiple files at once.

For example, assuming you have created beforehand a project named "foo", this will
copy ``~/docker/alpine-base.tar`` to the foo project :guilabel:`input/` directory::

    $ scanpipe add-input --project foo ~/docker/alpine-base.tar


`$ scanpipe add-pipeline --project PROJECT <pipeline ...>`
----------------------------------------------------------

Add the ``<pipeline>`` found at this location to the project named ``PROJECT``.
You can use more than one ``<pipeline>`` to add multiple pipelines at once.

.. warning::
    The pipelines are added and will be running in the order of the provided options.

For example, assuming you have created beforehand a project named "foo", this will
add the docker pipeline to your project::

    $ scanpipe add-pipeline --project foo scanpipe/pipelines/docker.py


`$ scanpipe run --project PROJECT`
----------------------------------

Run all the pipelines of the project named ``PROJECT``.

Optional arguments:

- ``--resume`` Resume the latest failed pipeline execution.


`$ scanpipe show-pipeline --project PROJECT`
--------------------------------------------

List all the pipelines added of the project named ``PROJECT``.


`$ scanpipe status --project PROJECT`
--------------------------------------------

Display status information about the provided ``PROJECT``.


`$ scanpipe output --project PROJECT --format {json,csv,xlsx}`
--------------------------------------------------------------

Output the ``PROJECT`` results as JSON, CSV or XLSX.
The output files are created in the ``PROJECT`` :guilabel:`output/` directory.


`$ scanpipe graph [pipelines ...]`
----------------------------------

Generate one or more pipeline graph image as PNG
(using `Graphviz <https://graphviz.org/>`_).
The output files are named using the pipeline class name with a ``.png``
extension.

Optional arguments:

- ``--list`` Display a list of all available pipelines.

- ``--output OUTPUT`` Specifies directory to which the output is written.

.. note::
    By default, the output files are created in the current working directory.


`$ scanpipe delete-project --project PROJECT`
---------------------------------------------

Delete a project and its related work directory.

Optional arguments:

- ``--no-input`` Do not prompt the user for input of any kind.
