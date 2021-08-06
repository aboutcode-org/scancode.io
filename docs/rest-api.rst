.. _rest_api:

REST API
========

To get started locally with the API:

1. **Run the webserver** with::

    make run

2. Visit the **projects API endpoint** at http://127.0.0.1:8001/api/projects/ or
   http://localhost/api/projects/ when running with Docker.

Authentication
--------------

When the authentication system is enabled on a ScanCode.io instance (disabled by
default) you will have to include an authentication token ``API key`` in the
Authorization HTTP header of each request.

The key should be prefixed by the string literal "Token", with whitespace separating
the two strings. For example::

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
^^^^^^^^^^^^^^^^

Using cURL:

.. code-block:: console

    curl -X POST  http://localhost/api/projects/ \
         --data '{"name": "project_name", "input_urls": "https://download.url/package.archive", "pipeline": "scan_package", "execute_now": true}'

Using Python and the requests library:

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


When creating a project the response will provide the project details URL value in
the returned data.
You can make a GET request on this URL to get all the information available about a
project, including the status of the pipeline run:

.. code-block:: json

    {
        "name":"project_name",
        "url":"/api/projects/6461408c-726c-4b70-aa7a-c9cc9d1c9685/",
        "uuid":"6461408c-726c-4b70-aa7a-c9cc9d1c9685",
        "created_date":"2021-07-21T16:06:29.132795+02:00"
    }

Project details
---------------

The project details view returns all information available about a project.

``GET /api/projects/b0c92a72-6c01-461d-993a-5360c30d7937/``

.. code-block:: json

    {
        "name": "alpine/httpie",
        "url": "/api/projects/6461408c-726c-4b70-aa7a-c9cc9d1c9685/",
        "uuid": "6461408c-726c-4b70-aa7a-c9cc9d1c9685",
        "created_date": "2021-07-27T08:43:06.058350+02:00",
        "codebase_resources_summary": {
            "application-package": 1
        },
        "discovered_package_summary": {
            "total": 1,
            "with_missing_resources": 0,
            "with_modified_resources": 0
        }
    }

Multiple **actions** are available to manage projects:

Add pipeline
^^^^^^^^^^^^

Add the selected ``pipeline`` to the ``project``.
If the ``execute_now`` value is provided, the pipeline execution will start immediately
on pipeline addition.

Errors
^^^^^^

List all the errors that were logged during Pipelines execution of this
``project``.

File content
^^^^^^^^^^^^

Display the content of a ``project`` file resource provided using the
``?path=<resource_path>`` argument.

Packages
^^^^^^^^

List all the ``packages`` of this ``project``.

Resources
^^^^^^^^^

List all the ``resources`` of this ``project``.

Results
^^^^^^^

Display the results as JSON content compatible with ScanCode data format.

Results (download)
^^^^^^^^^^^^^^^^^^

Download the JSON results as an attachment.
