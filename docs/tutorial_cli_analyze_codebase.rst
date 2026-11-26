.. _tutorial_cli_analyze_codebase:

Analyze Codebase (Command Line)
===============================

The focus of this tutorial is to guide you through scanning a codebase package
using ScanCode.io.

.. note::
    This tutorial assumes you have a recent version of ScanCode.io installed
    locally on your machine and **running with Docker**.
    If you do not have it installed, see our :ref:`installation` guide for instructions.

.. tip::
    To run a single pipeline without installing ScanCode.io, see :ref:`quickstart`.

Requirements
------------

Before you follow the instructions in this tutorial, you need to:

- Install **ScanCode.io** locally
- Have **Shell access** on the machine where ScanCode.io is installed

Instructions
------------

- Create a new directory in your home directory that will be used to put the input code
  to be scanned.

.. code-block:: console

    $ mkdir -p ~/codedrop/

- Download the following **package archive** and save it to the :guilabel:`~/codedrop/`
  directory: `asgiref-3.3.0-py3-none-any.whl <https://files.pythonhosted.org/packages/c0/e8/578887011652048c2d273bf98839a11020891917f3aa638a0bc9ac04d653/asgiref-3.3.0-py3-none-any.whl>`_

.. code-block:: console

    $ curl --location https://files.pythonhosted.org/packages/c0/e8/578887011652048c2d273bf98839a11020891917f3aa638a0bc9ac04d653/asgiref-3.3.0-py3-none-any.whl --output ~/codedrop/asgiref-3.3.0-py3-none-any.whl

- From the directory where ScanCode.io is installed, start the ``web`` service and
  wait until it is ready to accept commands:

.. code-block:: console

    $ docker compose up --detach --wait web

- From the same directory, create an alias to the ``scanpipe`` command executed
  through the ``docker compose`` command line interface with:

.. code-block:: console

    $ alias scanpipe="docker compose -f ${PWD}/docker-compose.yml run --rm --volume ~/codedrop/:/codedrop:ro web scanpipe"

- Create a new project named ``asgiref``:

.. code-block:: console

    $ scanpipe create-project asgiref

.. code-block:: console

    >> Project asgiref created with work directory /var/scancodeio/workspace/projects/asgiref-35519104

- Add the package archive to the project workspace's :guilabel:`input/`
  directory:

.. code-block:: bash

    $ scanpipe add-input --project asgiref --input-file /codedrop/asgiref-3.3.0-py3-none-any.whl

.. code-block:: console

    >> File copied to the project inputs directory:
      - asgiref-3.3.0-py3-none-any.whl

- Add the ``scan_codebase`` pipeline to your project:

.. code-block:: console

    $ scanpipe add-pipeline --project asgiref scan_codebase

.. code-block:: console

    >> Pipeline scan_codebase added to the project

.. note::
    The content of the :guilabel:`input/` directory will be copied in the
    :guilabel:`codebase/` directory where ``extractcode`` will be executed before
    running ``scancode``.
    Alternatively, the codebase content can be manually copied to the
    :guilabel:`codebase/` directory in which case the ``add-input`` step can be
    skipped.

- Run the ``scan_codebase`` pipeline on your project. The pipeline execution
  progress is shown within the following command's output:

.. code-block:: bash

    $ scanpipe execute --project asgiref

.. code-block:: console

    >> Start the scan_codebase pipeline execution...
       INFO Scan 18 codebase resources with scan_for_package_data
       [...]
       scan_codebase successfully executed on project asgiref

- Finally, export the scan results as JSON format:

.. code-block:: console

    $ scanpipe output --project asgiref --format json --print > asgiref-3.3.0_results.json

.. tip::
    The ``inputs`` and ``pipelines`` can be provided at the same time when
    calling the ``create-project`` command. For instance, the following command
    will create a new project named ``asgiref2``, add the package archive as the
    project input, add the ``scan_codebase`` pipeline to the project, and
    execute it:

    .. code-block:: bash

        $ scanpipe create-project asgiref2 \
            --input-file /codedrop/asgiref-3.3.0-py3-none-any.whl \
            --pipeline scan_codebase \
            --execute

    .. code-block:: console

        >> Project asgiref2 created with work directory /var/scancodeio/workspace/projects/asgiref2-bea7a5e9
           File copied to the project inputs directory:
           - asgiref-3.3.0-py3-none-any.whl
           Start the scan_codebase pipeline execution...
           [...]
           scan_codebase successfully executed on project asgiref2
