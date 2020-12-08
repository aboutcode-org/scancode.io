.. _scanpipe_tutorial_2:

Scan Codebase (command line)
============================

Requirements
------------

- **ScanCode.io is installed**, see :ref:`installation`
- **Shell access** on the machine where ScanCode.io is installed


Before you start
----------------

Download the following package archive save this in your home directory:
`asgiref-3.3.0-py3-none-any.whl <https://files.pythonhosted.org/packages/c0/e8/578887011652048c2d273bf98839a11020891917f3aa638a0bc9ac04d653/asgiref-3.3.0-py3-none-any.whl>`_


Step-by-step
------------

- Open a shell in the ScanCode.io installation directory and activate the virtualenv::

    $ source bin/activate

- The following command will create a new project named ``asgiref``,
  add the archive as an input for the project,
  add the ``scan_codebase`` pipeline, and run its execution::

    $ scanpipe create-project asgiref \
        --input ~/asgiref-3.3.0-py3-none-any.whl \
        --pipeline scanpipe/pipelines/scan_codebase.py \
        --run

.. note::
    The content of the :guilabel:`input/` directory will be copied in the
    :guilabel:`codebase/` directory where ``extractcode`` will be run before
    running ``scancode``.
    Alternatively, the codebase content can be manually copied to the
    :guilabel:`codebase/` directory in which case the ``--input`` option can be
    omitted.

- The scan results as JSON and CSV will be available in the project
  :guilabel:`output/` directory.
