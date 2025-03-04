.. _tutorial_cli_analyze_docker_image:

Analyze Docker Image (Command Line)
===================================

In this tutorial, you will learn by example how to use ScanCode.io to analyze
a test Docker image by following the steps below and, along the way,
learn some of the ScanCode.io basic commands.

.. note::
    This tutorial assumes you have a recent version of ScanCode.io installed
    locally on your machine and **running with Docker**.
    If you do not have it installed, see our :ref:`installation` guide for instructions.

Requirements
------------

To successfully complete this tutorial, you first need to:

- Install **ScanCode.io** locally
- Have **Shell access** on the machine where ScanCode.io is installed

Instructions
------------

- Create a new directory in your home directory that will be used to put the input code
  to be scanned.

.. code-block:: console

    $ mkdir -p ~/codedrop/

- Download the following **test Docker image** and save it to the :guilabel:`~/codedrop/`
  directory: `30-alpine-nickolashkraus-staticbox-latest.tar
  <https://github.com/aboutcode-org/scancode.io-tutorial/releases/download/sample-images/30-alpine-nickolashkraus-staticbox-latest.tar>`_

.. code-block:: console

    $ curl https://github.com/aboutcode-org/scancode.io-tutorial/releases/download/sample-images/30-alpine-nickolashkraus-staticbox-latest.tar --output ~/codedrop/30-alpine-nickolashkraus-staticbox-latest.tar

- Create an alias to the ``scanpipe`` command executed through the
  ``docker compose`` command line interface with:

.. code-block:: console

    $ alias scanpipe="docker compose -f ${PWD}/docker-compose.yml run --volume ~/codedrop/:/codedrop:ro web scanpipe"

- Create a new project named ``staticbox``:

.. code-block:: console

    $ scanpipe create-project staticbox

.. code-block:: console

    >> Project staticbox created with work directory /var/scancodeio/workspace/projects/staticbox-d4ed9405

.. note::
    New projects work directory are created inside the location defined in
    :ref:`scancodeio_settings_workspace_location` setting.
    Default to the :guilabel:`/var/scancodeio/workspace/` directory.

- Add the test Docker image tarball to the project workspace's :guilabel:`input/`
  directory:

.. code-block:: bash

    $ scanpipe add-input --project staticbox \
        --input-file /codedrop/30-alpine-nickolashkraus-staticbox-latest.tar

.. code-block:: console

    >> File copied to the project inputs directory:
       - 30-alpine-nickolashkraus-staticbox-latest.tar

.. note::
    The command output will let you know that the Docker image file was
    copied to the project's :guilabel:`input/` directory.
    Alternatively, you can copy files manually to the :guilabel:`input/`
    directory to include entire directories.

- Add the ``analyze_docker_image`` pipeline to your project:

.. code-block:: console

    $ scanpipe add-pipeline --project staticbox analyze_docker_image

.. code-block:: console

    >> Pipeline analyze_docker_image added to the project

- Check the status of the pipeline added to your project:

.. code-block:: console

    $ scanpipe show-pipeline --project staticbox

.. code-block:: console

    >> [NOT_STARTED] analyze_docker_image

.. note::
    The ``scanpipe show-pipeline`` command lists all the pipelines added to the
    project and their execution status.
    You can use this to get a quick overview of the pipelines that have been
    already running, pipelines with **"SUCCESS"** or **"FAILURE"** status, and those
    will be running next, pipelines with **"NOT_STARTED"** status as shown below.

- Run the ``analyze_docker_image`` pipeline on this project. In the output, you will be
  shown the pipeline's execution progress:

.. code-block:: console

    $ scanpipe execute --project staticbox

.. code-block:: console

    >> Pipeline analyze_docker_image run in progress...
       Pipeline [analyze_docker_image] starting
       Step [extract_images] starting
       Step [extract_images] completed in 0.18 seconds
       Step [extract_layers] starting
       [...]
       Pipeline completed
       analyze_docker_image successfully executed on project staticbox

- Executing the ``show-pipeline`` command again will also confirm the success
  of the pipeline execution - **"[SUCCESS] analyze_docker_image"** status:

.. code-block:: console

    $ scanpipe show-pipeline --project staticbox

.. code-block:: console

    >> [SUCCESS] analyze_docker_image

- Get the results of the pipeline execution as a JSON file using the ``output`` command:

.. code-block:: console

    $ scanpipe output --project staticbox --format json --print > staticbox_results.json

- Finally, open the ``staticbox_results.json`` file in your preferred text
  editor/file viewer.

.. note::
    To understand the output of the pipeline execution, see our :ref:`output_files`
    section for details.

.. tip::
    The ``inputs`` and ``pipelines`` can be provided directly at once when
    calling the ``create-project`` command.
    The ``--execute`` option is also available to start the pipeline execution right
    after the project creation.
    For example, the following command will create a project named ``staticbox2``,
    download the test Docker image to the project's :guilabel:`input/`
    directory, add the ``analyze_docker_image`` pipeline, and execute the pipeline in
    one operation:

    .. code-block:: bash

        $ scanpipe create-project staticbox2 \
            --input-url https://github.com/aboutcode-org/scancode.io-tutorial/releases/download/sample-images/30-alpine-nickolashkraus-staticbox-latest.tar \
            --pipeline analyze_docker_image \
            --execute
