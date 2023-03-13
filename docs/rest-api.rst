.. _rest_api:

REST API
========

To get started with the REST API, visit the **projects' API endpoint** at
http://localhost/api/projects/ or http://localhost:8001/api/projects/ if you run on a
local development setup.

.. _rest_api_authentication:

Authentication
--------------

When the authentication setting :ref:`scancodeio_settings_require_authentication`
is enabled on a ScanCode.io instance (disabled by default), you will have to include
an authentication token ``API key`` in the Authorization HTTP header of each request.

The key should be prefixed by the string literal "Token" with whitespace
separating the two strings. For example::

    Authorization: Token abcdef123456

.. warning::
    Your API key is like a password and should be treated with the same care.

Example of a cURL-style command line using an API Key for authentication:

.. code-block:: console

    curl -X GET http://localhost/api/projects/ -H "Authorization:Token abcdef123456"

Example of a Python script:

.. code-block:: python

    import requests

    api_url = "http://localhost/api/projects/"
    headers = {
        "Authorization": "Token abcdef123456",
    }
    params = {
        "page": "2",
    }
    response = requests.get(api_url, headers=headers, params=params)
    response.json()

Project list
------------

An API endpoint that provides the ability to list, get, and create projects.

``GET /api/projects/``

.. code-block:: json

    {
        "count": 1,
        "next": null,
        "previous": null,
        "results": [
            {
                "name": "alpine/httpie",
                "url": "/api/projects/6461408c-726c-4b70-aa7a-c9cc9d1c9685/",
                "uuid": "6461408c-726c-4b70-aa7a-c9cc9d1c9685",
                "created_date": "2021-07-27T08:43:06.058350+02:00",
                "next_run": null,
                "runs": []
            }
        ]
    }

The project list can be filtered by ``name``, ``uuid``, and ``is_archived`` fields.
For example:

.. code-block:: console

    api_url="http://localhost/api/projects/"
    content_type="Content-Type: application/json"
    payload="name=project_name"

    curl -X GET "$api_url?$payload" -H "$content_type"

Create a project
----------------

Using cURL:

.. code-block:: console

    api_url="http://localhost/api/projects/"
    content_type="Content-Type: application/json"
    data='{
        "name": "project_name",
        "input_urls": "https://download.url/package.archive",
        "pipeline": "scan_package",
        "execute_now": true
    }'

    curl -X POST "$api_url" -H "$content_type" -d "$data"

.. note::

    To **upload a file** as the input of the project, you have to use the cURL "form
    emulation" mode with the following syntax:

    .. code-block:: console

        api_url="http://localhost/api/projects/"
        upload_file="/path/to/the/archive.zip"

        curl -F "name=project_name" \
             -F "pipeline=scan_package" \
             -F "execute_now=True" \
             -F "upload_file=@$upload_file" \
             "$api_url"

.. tip::

    To upload more than one file, you can use the :ref:`rest_api_add_input` endpoint of
    the project.

Using Python and the **"requests"** library:

.. code-block:: python

    import requests

    api_url = "http://localhost/api/projects/"
    data = {
        "name": "project_name",
        "input_urls": "https://download.url/package.archive",
        "pipeline": "scan_package",
        "execute_now": True,
    }
    response = requests.post(api_url, data=data)
    response.json()

.. note::

    To **upload a file** as the input of the project, you have to provide the ``files``
    argument to the ``requests.post`` call:

    .. code-block:: python

        import requests

        api_url = "http://localhost/api/projects/"
        data = {
            "name": "project_name",
            "pipeline": "scan_package",
            "execute_now": True,
        }
        files = {"upload_file": open("/path/to/the/archive.zip", "rb")}
        response = requests.post(api_url, data=data, files=files)
        response.json()

When creating a project, the response will include the project's details URL
value among the returned data.
You can make a GET request to this URL, which returns all available information
about the project, including the status of any pipeline run:

.. code-block:: json

    {
        "name": "project_name",
        "url": "/api/projects/6461408c-726c-4b70-aa7a-c9cc9d1c9685/",
        "uuid": "6461408c-726c-4b70-aa7a-c9cc9d1c9685",
        "created_date": "2021-07-21T16:06:29.132795+02:00"
    }

Project details
---------------

The project details view returns all information available about a project.

``GET /api/projects/6461408c-726c-4b70-aa7a-c9cc9d1c9685/``

.. code-block:: json

    {
        "name": "alpine/httpie",
        "url": "/api/projects/6461408c-726c-4b70-aa7a-c9cc9d1c9685/",
        "uuid": "6461408c-726c-4b70-aa7a-c9cc9d1c9685",
        "created_date": "2021-07-27T08:43:06.058350+02:00",
        "[...]": "[...]",
        "codebase_resources_summary": {
            "application-package": 1
        },
        "discovered_packages_summary": {
            "total": 1,
            "with_missing_resources": 0,
            "with_modified_resources": 0
        }
    }

Managing projects
-----------------

Multiple **actions** are available to manage projects:

.. _rest_api_add_input:

Add input
^^^^^^^^^

This action adds provided ``input_urls`` or ``upload_file`` to the ``project``.

``POST /api/projects/d4ed9405-5568-45ad-99f6-782a9b82d1d2/add_input/``

Data:
    - ``input_urls``: A list of URLs to download
    - ``upload_file``: A file to upload

Using cURL to provide download URLs:

.. code-block:: console

    api_url="http://localhost/api/projects/6461408c-726c-4b70-aa7a-c9cc9d1c9685/add_input/"
    content_type="Content-Type: application/json"
    data='{
        "input_urls": [
            "https://github.com/nexB/debian-inspector/archive/refs/tags/v21.5.25.zip",
            "https://github.com/package-url/packageurl-python/archive/refs/tags/0.9.4.tar.gz"
       ]
    }'

    curl -X POST "$api_url" -H "$content_type" -d "$data"

.. code-block:: json

    {
        "status": "Input(s) added."
    }

Using cURL to upload a local file:

.. code-block:: console

    api_url="http://localhost/api/projects/6461408c-726c-4b70-aa7a-c9cc9d1c9685/add_input/"
    upload_file="/path/to/the/archive.zip"

    curl -X POST "$api_url" -F "upload_file=@$upload_file"

.. code-block:: json

    {
        "status": "Input(s) added."
    }

Add pipeline
^^^^^^^^^^^^

This action adds a selected ``pipeline`` to the ``project``.
If the ``execute_now`` value is True, the pipeline execution will start immediately
during the pipeline addition.

``POST /api/projects/d4ed9405-5568-45ad-99f6-782a9b82d1d2/add_pipeline/``

Data:
    - ``pipeline``: The pipeline name
    - ``execute_now``: ``true`` or ``false``

Using cURL:

.. code-block:: console

    api_url="http://localhost/api/projects/6461408c-726c-4b70-aa7a-c9cc9d1c9685/add_pipeline/"
    content_type="Content-Type: application/json"
    data='{
        "pipeline": "docker",
        "execute_now": true
    }'

    curl -X POST "$api_url" -H "$content_type" -d "$data"

.. code-block:: json

    {
        "status": "Pipeline added."
    }

Archive
^^^^^^^

This action archive a project and remove selected work directories.

``POST /api/projects/6461408c-726c-4b70-aa7a-c9cc9d1c9685/archive/``

Data:
    - ``remove_input``: ``true``
    - ``remove_codebase``: ``true``
    - ``remove_output``: ``false``

.. code-block:: json

    {
        "status": "The project project_name has been archived."
    }

Reset
^^^^^

This action will delete all related database entrie and all data on disks except for
the :guilabel:`input/` directory.

``POST /api/projects/6461408c-726c-4b70-aa7a-c9cc9d1c9685/reset/``

.. code-block:: json

    {
        "status": "All data, except inputs, for the project_name project have been removed."
    }

Errors
^^^^^^

This action lists all errors that were logged during any pipeline execution
on a given ``project``.

``GET /api/projects/6461408c-726c-4b70-aa7a-c9cc9d1c9685/errors/``

.. code-block:: json

    [
        {
            "uuid": "d4ed9405-5568-45ad-99f6-782a9b82d1d2",
            "model": "CodebaseResource",
            "[...]": "[...]",
            "message": "ERROR: for scanner: packages:",
            "created_date": "2021-04-27T22:38:30.762731+02:00"
        }
    ]

File content
^^^^^^^^^^^^

This displays the content of a ``project`` file resource provided using the
``?path=<resource_path>`` argument.

``GET /api/projects/d4ed9405-5568-45ad-99f6-782a9b82d1d2/file_content/?path=setup.py``

.. code-block:: json

    {
        "file_content": "#!/usr/bin/env python\n# -*- encoding: utf-8 -*-\n\n..."
    }

Packages
^^^^^^^^

Lists all ``packages`` of a given ``project``.

``GET /api/projects/d4ed9405-5568-45ad-99f6-782a9b82d1d2/packages/``

.. code-block:: json

    [
        {
            "purl": "pkg:deb/debian/libdb5.3@5.3.28%2Bdfsg1-0.5?arch=amd64",
            "type": "deb",
            "namespace": "debian",
            "name": "libdb5.3",
            "version": "5.3.28+dfsg1-0.5",
            "[...]": "[...]"
        }
    ]

Resources
^^^^^^^^^

This action lists all ``resources`` of a given ``project``.

``GET /api/projects/d4ed9405-5568-45ad-99f6-782a9b82d1d2/resources/``

.. code-block:: json

    [
        {
            "for_packages": [
                "pkg:deb/debian/bash@5.0-4?arch=amd64"
            ],
            "path": "/bin/bash",
            "size": 1168776,
            "[...]": "[...]"
        }
    ]

Results
^^^^^^^

Displays the results as JSON content compatible with ScanCode data format.

``GET /api/projects/d4ed9405-5568-45ad-99f6-782a9b82d1d2/results/``

.. code-block:: json

    {
        "headers": [
            {
                "tool_name": "scanpipe",
                "tool_version": "21.8.2",
                "[...]": "[...]"
            }
        ]
    }

Results (download)
^^^^^^^^^^^^^^^^^^

Finally, this action downloads the JSON results as an attachment.

``GET /api/projects/d4ed9405-5568-45ad-99f6-782a9b82d1d2/results_download/``

Run details
-----------

The run details view returns all information available about a pipeline run.

``GET /api/runs/c4d09fe5-c133-4c03-8286-6894ee5ffaab/``

.. code-block:: json

    {
        "url": "http://localhost/api/runs/8d5c3962-5fca-47d7-b8c8-47a19247714e/",
        "pipeline_name": "scan_package",
        "status": "success",
        "description": "A pipeline to scan a single package archive with ScanCode-toolkit.",
        "project": "http://localhost/api/projects/cd5b0459-303f-4e92-99c4-ea6d0a70193e/",
        "uuid": "8d5c3962-5fca-47d7-b8c8-47a19247714e",
        "created_date": "2021-10-01T08:44:05.174487+02:00",
        "task_exitcode": 0,
        "[...]": "[...]",
        "execution_time": 12
    }

Managing pipeline runs
----------------------

Multiple **actions** are available to manage pipeline runs:

Start pipeline
^^^^^^^^^^^^^^

This action starts (send to the task queue) a pipeline run for execution.

``POST /api/runs/8d5c3962-5fca-47d7-b8c8-47a19247714e/start_pipeline/``

.. code-block:: json

    {
        "status": "Pipeline pipeline_name started."
    }

Stop pipeline
^^^^^^^^^^^^^

This action stops a "running" pipeline.

``POST /api/runs/8d5c3962-5fca-47d7-b8c8-47a19247714e/stop_pipeline/``

.. code-block:: json

    {
        "status": "Pipeline pipeline_name stopped."
    }

Delete pipeline
^^^^^^^^^^^^^^^

This action deletes a "not started" or "queued" pipeline run.

``POST /api/runs/8d5c3962-5fca-47d7-b8c8-47a19247714e/delete_pipeline/``

.. code-block:: json

    {
        "status": "Pipeline pipeline_name deleted."
    }
