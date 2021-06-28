.. _scanpipe_tutorial_1:

Docker Image Analysis (command line)
====================================

In this tutorial, you will learn by example how to use ScanCode.io to analyze
a test Docker image by following the given steps and, along the way,
learn some of the ScanCode.io basic commands.


.. note::
    This tutorial assumes you have a current version of ScanCode.io installed
    locally on your machine. If you do not have it installed,
    see our :ref:`installation` guide for instructions.

Requirements
------------
To successfully complete this tutorial, you first need to:

- Install **ScanCode.io** locally
- Download the following **test Docker image** and save it to your home directory: `30-alpine-nickolashkraus-staticbox-latest.tar <https://github.com/nexB/scancode.io-tutorial/releases/download/sample-images/30-alpine-nickolashkraus-staticbox-latest.tar>`_
- Have **Shell access** on the machine where ScanCode.io is installed


Instructions
------------

- Open a shell in the ScanCode.io installation directory and activate the
  virtual environment - **virtualenv**::

    $ source bin/activate

.. image:: /images/Docker-CL-Image1.png

- Create a new project named ``staticbox``::

    $ scanpipe create-project staticbox

.. note::
    New projects are often created inside the
    :guilabel:`scancode.io/var/projects/` directory. Anyway, the output of the
    previous command will include the full path of the new project.

- Add the test Docker image tarball to the project workspace's :guilabel:`input/` directory::

    $ scanpipe add-input --project staticbox \
      --input-file ~/30-alpine-nickolashkraus-staticbox-latest.tar

.. note::
    The command output will let you know that the Docker image file was
    copied to the project's :guilabel:`input/` directory.
    You can also navigate to this directory and confirm your file is there.
    Alternatively, you can copy files manually to the :guilabel:`input/`
    directory to include entire directories.

.. image:: /images/Docker-CL-Image2.png

- Add the docker pipeline to your project::

    $ scanpipe add-pipeline --project staticbox docker

The output of the previous command will show whether the docker pipeline is added
to the staticbox project or not, as shown in the following screenshot.

.. image:: /images/Docker-CL-Image3.png

- Check whether the docker pipeline was added to your project successfully::

    $ scanpipe show-pipeline --project staticbox

.. note::
    The ``scanpipe show-pipeline`` command lists all the pipelines added to the
    project and their execution status.
    You can use this to get a quick overview of the pipelines that have been
    already running, pipelines with "SUCCESS" or "FAILURE" status, and those
    will be running next, pipelines with "NOT_STARTED" status as shown below.

.. image:: /images/Docker-CL-Image4.png

- Run the docker pipeline on this project. In the output, you will be shown
  whether this pipeline's execution is successful or not::

    $ scanpipe execute --project staticbox

.. image:: /images/Docker-CL-Image5.png

- Executing the ``show-pipeline`` command again will also confirm the success
  of the pipeline execution - **"[SUCCESS] docker"** status::

    $ scanpipe show-pipeline --project staticbox

.. image:: /images/Docker-CL-Image6.png

- Get the results of the pipeline execution as a JSON file using the ``output`` command::

    $ scanpipe output --project staticbox --format json

- Finally, open the ``output/results-<timestamp>.json`` file in your preferred
  text editor/file viewer.

.. note::
      To understand the output of the pipeline execution, see our :ref:`scancodeio_output`
      section for details.

.. tip::
    The ``inputs`` and ``pipelines`` can be provided directly at once when
    calling the ``create-project`` command.
    An ``execute`` option is also available to start the pipeline execution right
    after the project creation.
    For example, the following command will create a project named ``staticbox2``,
    download the test Docker image to the project's :guilabel:`input/`
    directory, add the docker pipeline, and execute the pipeline in one operation::

      $ scanpipe create-project staticbox2 \
        --input-url https://github.com/nexB/scancode.io-tutorial/releases/download/sample-images/30-alpine-nickolashkraus-staticbox-latest.tar \
        --pipeline docker \
        --execute
