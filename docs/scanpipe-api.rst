.. _scanpipe_api:

ScanPipe REST API
=================

To get started locally with the API:

1. **Run the webserver** with::

    make run

2. Visit the **projects API endpoint** at http://127.0.0.1:8001/api/projects/

From the bottom of this page you can **create a new project**, **upload an input
file** and **add a pipeline** to this project at once.

.. note::
    If you add a pipeline, the pipeline starts immediately on project creation.

----

Multiple **views** and **actions** are available to manage projects.
From a ``Project Instance`` view:

Add pipeline
------------

Add the selected ``pipeline`` to the ``project``.

Errors
------

List all the errors that were logged during Pipelines execution of this
``project``.

File content
------------

Display the content of a ``project`` file resource provided using the
``?path=<resource_path>`` argument.

Packages
--------

List all the ``packages`` of this ``project``.

Resources
---------

List all the ``resources`` of this ``project``.

Results
-------

Display the results as JSON content compatible with ScanCode data format.

Results (download)
------------------

Download the JSON results as an attachment.
