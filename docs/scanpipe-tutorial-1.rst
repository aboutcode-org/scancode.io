ScanPipe Tutorial: Docker image analysis from the command line
==============================================================

Requirements
------------

- ScanCode.io is installed
- Shell access on the machine where ScanCode.io is installed


Before you start
----------------

- Download the test Docker image from:

https://github.com/nexB/scancode.io-tutorial/releases/download/sample-images/30-alpine-nickolashkraus-staticbox-latest.tar

and save this in your home directory.


Step-by-step
------------

- Open a shell in the ScanCode.io installation directory.
- Run::

    $ source bin/activate

- Create a new project named `p1`::

    $ scanpipe create-project p1

- Add the test Docker image tarball to the project workspace's input directory::

    $ scanpipe add-input --project p1 ~/30-alpine-nickolashkraus-staticbox-latest.tar

Notes: the command output will let you know where is the project workspace `input/` directory
location so you can browse this directory and check that your file was copied there correctly.
You can also copy more files manually to this `input/` directory including entire directories.

- Add the docker pipeline to your project::

    $ scanpipe add-pipeline --project p1 scanpipe/pipelines/docker.py

- Check that the docker pipeline as added to your project::

    $ scanpipe show-pipeline --project p1

Notes: Using this `scanpipe show-pipeline` command lists all the pipelines added and their planned runs.
You can use this to get a quick overview of the pipelines that have been running already 
(with their success "V" or fail status "f") and those that will be running next when you invoke the run command.

- Run the docker pipeline proper on this project::

    $ scanpipe run --project p1

Executing the show-pipeline command again will confirm the success of the pipeline run::

    $ scanpipe show-pipeline --project p1
    > "[V] scanpipe/pipelines/docker.py"

- Get the results of the pipeline run as a JSON file using the output command::

    $ scanpipe output --project p1 results.json

As a shortcut, the inputs and pipelines can be provided directly at once when
calling the `create-project` command. For example, this command will create a
project named `p2` copy our test docker image to the project's inputs and add
the docker pipeline in one operation::

    $ scanpipe create-project p2 --input ~/30-alpine-nickolashkraus-staticbox-latest.tar --pipeline scanpipe/pipelines/docker.py

Next step
---------

- Explore scanpipe command line options `scanpipe-command-line.rst`
