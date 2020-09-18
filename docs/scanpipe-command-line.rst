ScanPipe Commands help
======================

The main entry point is the `scanpipe` command which is available directly when
you are in the activated virtualenv or directly at this path: `<scancode.io root dir/bin/scanpipe>` .


`$ scanpipe --help`
-------------------

List all the sub-commands available (including Django built-in commands).
ScanPipe's own commands are listed under the `[scanpipe]` section. 

For example::

    $ scanpipe --help
    ...
    [scanpipe]
        add-input
        add-pipeline
        create-project
        graph
        output
        run
    ...


`$ scanpipe <subcommand> --help`
--------------------------------

Display help for the provided subcommand.

For example::

    $ scanpipe create-project --help
    usage: scanpipe create-project [-h] [--pipeline PIPELINES] [--input INPUTS]
                                   [--version] [-v {0,1,2,3}]
                                   [--settings SETTINGS] [--pythonpath PYTHONPATH]
                                   [--traceback] [--no-color] [--force-color]
                                   [--skip-checks]
                                   name
    
    Create a ScanPipe project.
    
    positional arguments:
      name                  Project name.


`$ scanpipe create-project <name>`
----------------------------------

Create a ScanPipe project using <name> as a Project name. The name must
be unique.

optional arguments:

- `--pipeline PIPELINES`  Pipelines locations to add on the project. The
  pipelines are added and will be running in the order of the provided options.

- `--input INPUTS`  Input file locations to copy in the input/ workspace directory.


`$ scanpipe add-input --project PROJECT <input ...>`
----------------------------------------------------

Copy the file found at the <input> path to the project named <PROJECT> workspace 
"input" directory. You can use more than one <input> to copy multiple files at once.

For example, assuming you have created beforehand a project named foo, this will
copy `~/docker/alpine-base.tar` to the foo project input directory::

    $ scanpipe add-input --project foo ~/docker/alpine-base.tar


`$ scanpipe add-pipeline --project PROJECT <pipeline ...>`
----------------------------------------------------------

Add the <pipeline> foudn at this location to the project named <PROJECT>.
You can use more than one <pipeline> to add multiple pipelines at once.
The pipelines are added and will be running in the order of the provided options.

For example, assuming you have created beforehand a project named foo, this will
add the docker pipeline to your project::

    $ scanpipe add-pipeline --project foo scanpipe/piplines/docker.py


`$ scanpipe run --project PROJECT`
----------------------------------

Run all the pipelines of the project named <PROJECT>.


`$ scanpipe run --project PROJECT --show`
-----------------------------------------

List all the pipelines added of the project named <PROJECT>.



`$ scanpipe output --project PROJECT <output_file>`
---------------------------------------------------

Output the results of the project named <PROJECT> to the <output_file> as JSON.



`$ scanpipe graph <pipeline ...>`
---------------------------------

Generate a pipeline graph image as PNG (using Graphviz). The graphic will name
after the pipeline name with a .png extension.

optional arguments:

- `--output OUTPUT`  Alternative output directory location to use. The
  default is to create the image in the scancode.io root directory. 


Next step
---------

- Explore ScanPipe Concepts `scanpipe-concepts.rst`.



