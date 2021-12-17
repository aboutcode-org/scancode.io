.. _tutorial_cli_analyze_docker_image:

Analyze Docker Image (Command Line)
===================================

In this tutorial, you will learn by example how to use ScanCode.io to analyze
a test Docker image by following the steps below and, along the way,
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
  virtual environment - **virtualenv**:

.. code-block:: console

    $ source bin/activate

.. code-block:: console

    >> (scancodeio) $

- Create a new project named ``staticbox``:

.. code-block:: console

    $ scanpipe create-project staticbox

.. code-block:: console

    >> Project staticbox created with work directory projects/staticbox-d4ed9405

.. note::
    New projects work directory are created inside the location defined in
    :ref:`scancodeio_settings_workspace_location` setting.
    Default to a :guilabel:`var/` directory in the local ScanCode.io codebase.

- Add the test Docker image tarball to the project workspace's :guilabel:`input/`
  directory:

.. code-block:: bash

    $ scanpipe add-input --project staticbox \
      --input-file ~/30-alpine-nickolashkraus-staticbox-latest.tar

.. code-block:: console

    >> File(s) copied to the project inputs directory:
       - 30-alpine-nickolashkraus-staticbox-latest.tar

.. note::
    The command output will let you know that the Docker image file was
    copied to the project's :guilabel:`input/` directory.
    You can also navigate to this directory and confirm your file is there.
    Alternatively, you can copy files manually to the :guilabel:`input/`
    directory to include entire directories.

- Add the docker pipeline to your project:

.. code-block:: console

    $ scanpipe add-pipeline --project staticbox docker

.. code-block:: console

    >> Pipeline(s) added to the project

- Check the status of the pipeline added to your project:

.. code-block:: console

    $ scanpipe show-pipeline --project staticbox

.. code-block:: console

    >> [NOT_STARTED] docker

.. note::
    The ``scanpipe show-pipeline`` command lists all the pipelines added to the
    project and their execution status.
    You can use this to get a quick overview of the pipelines that have been
    already running, pipelines with **"SUCCESS"** or **"FAILURE"** status, and those
    will be running next, pipelines with **"NOT_STARTED"** status as shown below.

- Run the docker pipeline on this project. In the output, you will be shown
  the pipeline's execution progress:

.. code-block:: console

    $ scanpipe execute --project staticbox

.. code-block:: console

    >> Pipeline docker run in progress...
       2021-07-07 10:39:26.49 Pipeline [docker] starting
       2021-07-07 10:39:26.53 Step [extract_images] starting
       2021-07-07 10:39:26.71 Step [extract_images] completed in 0.18 seconds
       2021-07-07 10:39:26.71 Step [extract_layers] starting
       [...]
       2021-07-07 10:39:31.39 Pipeline completed

- Executing the ``show-pipeline`` command again will also confirm the success
  of the pipeline execution - **"[SUCCESS] docker"** status:

.. code-block:: console

    $ scanpipe show-pipeline --project staticbox

.. code-block:: console

    >> [SUCCESS] docker

- Get the results of the pipeline execution as a JSON file using the ``output`` command:

.. code-block:: console

    $ scanpipe output --project staticbox --format json

.. code-block:: console

    >> projects/staticbox-d4ed9405/output/results-2021-07-07-08-54-02.json

- Finally, open the ``output/results-<timestamp>.json`` file in your preferred
  text editor/file viewer.

.. note::
    To understand the output of the pipeline execution, see our :ref:`output_files`
    section for details.

.. tip::
    The ``inputs`` and ``pipelines`` can be provided directly at once when
    calling the ``create-project`` command.
    An ``execute`` option is also available to start the pipeline execution right
    after the project creation.
    For example, the following command will create a project named ``staticbox2``,
    download the test Docker image to the project's :guilabel:`input/`
    directory, add the docker pipeline, and execute the pipeline in one operation:

    .. code-block:: bash

      $ scanpipe create-project staticbox2 \
        --input-url https://github.com/nexB/scancode.io-tutorial/releases/download/sample-images/30-alpine-nickolashkraus-staticbox-latest.tar \
        --pipeline docker \
        --execute
