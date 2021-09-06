.. _rest_api:

REST API
========

To get started locally with REST API:

1. **Run the webserver** with::

    make run

2. Visit the **projects' API endpoint** at http://127.0.0.1:8001/api/projects/ or
   http://localhost/api/projects/ when running with Docker.

Authentication
--------------

When the authentication setting is enabled on a ScanCode.io instance—disabled by
default—you will have to include an authentication token ``API key`` in the
Authorization HTTP header of each request.

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
        "[...]": "[...]"
        "codebase_resources_summary": {
            "application-package": 1
        },
        "discovered_package_summary": {
            "total": 1,
            "with_missing_resources": 0,
            "with_modified_resources": 0
        }
    }

Managing Projects
-----------------

Multiple **actions** are available to manage projects:

Add pipeline
^^^^^^^^^^^^

This action adds a selected ``pipeline`` to the ``project``.
If the ``execute_now`` value is True, the pipeline execution will start immediately
during the pipeline addition.

``POST /api/projects/d4ed9405-5568-45ad-99f6-782a9b82d1d2/add_pipeline/``

Data:
    - ``pipeline``: ``docker``
    - ``execute_now``: ``true``

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

Errors
^^^^^^

This action lists all errors that were logged during any pipeline(s) execution
on a given ``project``.

``GET /api/projects/6461408c-726c-4b70-aa7a-c9cc9d1c9685/errors/``

.. code-block:: json

    [
        {
            "uuid": "d4ed9405-5568-45ad-99f6-782a9b82d1d2",
            "model": "CodebaseResource",
            "[...]": "[...]"
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
