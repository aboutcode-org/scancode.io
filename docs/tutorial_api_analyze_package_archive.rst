.. _tutorial_api_analyze_package_archive:

Analyse Package Archive (REST API)
==================================

This tutorial complements the :ref:`rest_api` section, and the aim here is to
show the API features while analyzing a package archive.

.. tip::
    As a pre-requisite, check our :ref:`rest_api` chapter for more details on REST
    API and how to get started.

Instructions:

- First, let's create a new project called ``boolean.py-3.8``.
- We'll be using this `package <https://github.com/bastikr/boolean.py/archive/refs/tags/v3.8.zip>`_
  as the project input.
- We can add and execute the scan_single_package pipeline on our new project.

.. note::
    Whether you follow this tutorial and previous instructions using cURL or
    Python script, the final results should be the same.

Using cURL
----------

- In your terminal, insert the following:

.. code-block:: bash

    api_url="http://localhost/api/projects/"
    content_type="Content-Type: application/json"
    data='{
        "name": "boolean.py-3.8",
        "input_urls": "https://github.com/bastikr/boolean.py/archive/refs/tags/v3.8.zip",
        "pipeline": "scan_single_package",
        "execute_now": true
    }'

    curl -X POST "$api_url" -H "$content_type" -d "$data"

.. note::
    You have to set the api_url to http://localhost:8001/api/projects/ if you run on a
    local development setup.

.. tip::
    You can provide the data using a json file with the text below, which will be
    passed in the -d parameter of the curl request:

    .. code-block:: json

        {
            "name": "boolean.py-3.8",
            "input_urls": "https://github.com/bastikr/boolean.py/archive/refs/tags/v3.8.zip",
            "pipeline": "scan_single_package",
            "execute_now": true
        }

    While in the same directory as your JSON file, here called
    ``boolean.py-3.8_cURL.json``, create your new project with the following
    curl request:

    .. code-block:: bash

        curl -X POST "http://localhost/api/projects/" -H "Content-Type: application/json" -d @boolean.py-3.8_cURL.json

If the new project has been successfully created, the response should include
the project's details URL value among the returned data.

.. code-block:: json

    {
        "name": "boolean.py-3.8",
        "url": "http://localhost/api/projects/11de938f-fb86-4178-870c-99f4952b8881/",
        "[...]": "[...]"
    }

If you click on the project url, you'll be directed to the new project's
instance page that allows you to perform extra actions on the project including
deleting it.

.. note::
    Refer to our :ref:`rest_api` section for more information about these extra actions.

Using Python script
-------------------

.. tip::
    To interact with REST APIs, we will be turning to the requests library.

- To follow the above instructions and create a new project, start up the Python
  interpreter by typing ``python`` in your terminal.
- If you are seeing the prompt ``>>>``, you can execute the following commands:

.. code-block:: python

    import requests

    api_url = "http://localhost/api/projects/"
    data = {
        "name": "boolean.py-3.8",
        "input_urls": "https://github.com/bastikr/boolean.py/archive/refs/tags/v3.8.zip",
        "pipeline": "scan_single_package",
        "execute_now": True,
    }
    response = requests.post(api_url, data=data)
    response.json()

The JSON response includes a generated UUID for the new project.

.. code-block:: python

    # print(response.json())
    {
        "name": "boolean.py-3.8",
        "url": "http://localhost/api/projects/11de938f-fb86-4178-870c-99f4952b8881/",
        "[...]": "[...]",
    }

.. note::
    Alternatively, you can create a Python script with the above commands/text.
    Then, navigate to the same directory as your Python file and run the script
    to create your new project. However, no response will be shown on the
    terminal, and to access a given project details, you need to visit the
    projects' API endpoint.

.. tip::
    You can check the :ref:`rest_api` section for more details on how to view
    and download your scan results.
