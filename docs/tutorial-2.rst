.. _tutorial_2:

Analyze Codebase (command line)
===============================

The focus of this tutorial is to guide you through scanning a codebase package
using ScanCode.io.

.. note::
    This tutorial assumes you have a current version of ScanCode.io installed
    locally on your machine. If you do not have it installed,
    see our :ref:`installation` guide for instructions.

Requirements
------------
Before you follow the instructions in this tutorial, you need to:

- Install **ScanCode.io** locally
- Download the following **package archive** and save it to your home directory: `asgiref-3.3.0-py3-none-any.whl <https://files.pythonhosted.org/packages/c0/e8/578887011652048c2d273bf98839a11020891917f3aa638a0bc9ac04d653/asgiref-3.3.0-py3-none-any.whl>`_
- Have **Shell access** on the machine where ScanCode.io is installed

Instructions
------------

- Open a shell in the ScanCode.io installation directory and activate the
  virtual environment - **virtualenv**:

.. code-block:: console

    $ source bin/activate

.. code-block:: console

    >> (scancodeio) $

- Create a new project named ``asgiref``:

.. code-block:: console

    $ scanpipe create-project asgiref

.. code-block:: console

    >> Project asgiref created with work directory projects/asgiref-072c89db

- Add the package archive to the project workspace's :guilabel:`input/`
  directory:

.. code-block:: bash

    $ scanpipe add-input --project asgiref --input-file ~/asgiref-3.3.0-py3-none-any.whl

.. code-block:: console

    >> File(s) copied to the project inputs directory:
      - asgiref-3.3.0-py3-none-any.whl

- Add the ``scan_codebase`` pipeline to your project:

.. code-block:: console

    $ scanpipe add-pipeline --project asgiref scan_codebase

.. code-block:: console

    >> Pipeline(s) added to the project

.. note::
    The content of the :guilabel:`input/` directory will be copied in the
    :guilabel:`codebase/` directory where ``extractcode`` will be executed before
    running ``scancode``.
    Alternatively, the codebase content can be manually copied to the
    :guilabel:`codebase/` directory in which case the ``--input`` option can be
    omitted.

- Run the ``scan_codebase`` pipeline on your project. The pipeline execution
  progress is shown within the following command's output:

.. code-block:: bash

    $ scanpipe execute --project asgiref

.. code-block:: console

    >> Pipeline scan_codebase run in progress..
       2021-07-12 17:45:53.85 Pipeline [scan_codebase] starting
       2021-07-12 17:45:53.85 Step [copy_inputs_to_codebase_directory] starting
       2021-07-12 17:45:53.86 Step [copy_inputs_to_codebase_directory] completed in 0.00 seconds
       2021-07-12 17:45:53.86 Step [run_extractcode] starting
       [...]
       2021-07-12 17:46:01.61 Pipeline completed

- Finally, you can view your scan results in JSON or CSV file formats inside
  the project's :guilabel:`output/` directory.

.. tip::
    The ``inputs`` and ``pipelines`` can be provided at the same time when
    calling the ``create-project`` command. For instance, the following command
    will create a new project named ``asgiref``, add the package archive as the
    project input, add the ``scan_codebase`` pipeline to the project, and
    execute it:

.. code-block:: bash

    $ scanpipe create-project asgiref \
        --input-file ~/asgiref-3.3.0-py3-none-any.whl \
        --pipeline scan_codebase \
        --execute
