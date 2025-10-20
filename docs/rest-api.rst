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
        "pipeline": "scan_single_package",
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
             -F "pipeline=scan_single_package" \
             -F "execute_now=True" \
             -F "upload_file=@$upload_file" \
             "$api_url"

.. tip::

    To upload more than one file, you can use the :ref:`rest_api_add_input` endpoint of
    the project.

.. tip::

    To tag the ``upload_file``, you can provide the tag value using the
    ``upload_file_tag`` field.

.. tip::

    You can declare multiple pipelines to be executed at the project creation using a
    list of pipeline names:

    ``"pipeline": ["scan_single_package", "scan_for_virus"]``

.. tip::

    Use the "pipeline_name:option1,option2" syntax to select optional steps:

    ``"pipeline": "map_deploy_to_develop:Java,JavaScript"``

Using Python and the **"requests"** library:

.. code-block:: python

    import requests

    api_url = "http://localhost/api/projects/"
    data = {
        "name": "project_name",
        "input_urls": "https://download.url/package.archive",
        "pipeline": "scan_single_package",
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
            "pipeline": "scan_single_package",
            "execute_now": True,
        }
        files = {"upload_file": open("/path/to/the/archive.zip", "rb")}
        response = requests.post(api_url, data=data, files=files)
        response.json()

    You have the flexibility to explicitly set the filename, content_type, and
    headers for your uploaded files using the following code:

    .. code-block:: python

        files = {"upload_file": ("inventory.json", file_contents, "application/json")}

    For more information on this topic, refer to the following link:
    https://docs.python-requests.org/en/latest/user/quickstart/#post-a-multipart-encoded-file

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

.. _rest_api_webhooks:

Adding webhooks
^^^^^^^^^^^^^^^

When creating a project, you can also **register webhook subscriptions** that will
notify external services about pipeline execution events.

You can either provide:
 - A **single webhook URL** using the ``webhook_url`` field.
 - A **list of detailed webhook configurations** using the ``webhooks`` field.

Webhook fields:
    - ``webhook_url`` (string, optional): A single webhook URL to be notified.
    - ``webhooks`` (list, optional): A list of webhook configurations.
        - ``target_url`` (string, required): The URL to which the webhook will send a
          ``POST`` request.
        - ``trigger_on_each_run`` (boolean, optional): If ``true``, the webhook will be
          triggered after each individual pipeline run. Default is ``false``.
        - ``include_summary`` (boolean, optional): If ``true``, the webhook payload
          will include the summary data of the pipeline execution. Default is ``false``.
        - ``include_results`` (boolean, optional): If ``true``, the webhook payload
          will include the full results data of the pipeline execution.
          Default is ``false``.
        - ``is_active`` (boolean, optional): If ``true``, the webhook is active and
          will be triggered when the specified conditions are met. Default is ``true``.

Using cURL to register a webhook:

.. code-block:: console

    api_url="http://localhost/api/projects/"
    content_type="Content-Type: application/json"
    data='{
        "name": "project_name",
        "webhook_url": "https://example.com/webhook"
    }'

    curl -X POST "$api_url" -H "$content_type" -d "$data"

.. code-block:: json

    {
        "name": "project_name",
        "webhook_url": "https://example.com/webhook"
    }

Using cURL to register multiple webhooks:

.. code-block:: console

    api_url="http://localhost/api/projects/"
    content_type="Content-Type: application/json"
    data='{
        "name": "project_name",
        "webhooks": [
            {
                "target_url": "https://example.com/webhook1",
                "trigger_on_each_run": true,
                "include_summary": false,
                "include_results": true,
                "is_active": true
            },
            {
                "target_url": "https://example.com/webhook2",
                "trigger_on_each_run": false,
                "include_summary": true,
                "include_results": false,
                "is_active": true
            }
        ]
    }'

    curl -X POST "$api_url" -H "$content_type" -d "$data"

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
    - ``upload_file_tag``: An optional tag to add on the uploaded file

Using cURL to provide download URLs:

.. code-block:: console

    api_url="http://localhost/api/projects/6461408c-726c-4b70-aa7a-c9cc9d1c9685/add_input/"
    content_type="Content-Type: application/json"
    data='{
        "input_urls": [
            "https://github.com/aboutcode-org/debian-inspector/archive/refs/tags/v21.5.25.zip",
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

.. _rest_api_add_pipeline:

Add pipeline
^^^^^^^^^^^^

This action adds a selected ``pipeline`` to the ``project``.
If the ``execute_now`` value is True, the pipeline execution will start immediately
during the pipeline addition.

``POST /api/projects/d4ed9405-5568-45ad-99f6-782a9b82d1d2/add_pipeline/``

Data:
    - ``pipeline``: The pipeline name
    - ``execute_now``: ``true`` or ``false``

.. tip::
    Use the "pipeline_name:option1,option2" syntax to select optional steps:

    ``"pipeline": "map_deploy_to_develop:Java,JavaScript"``

Using cURL:

.. code-block:: console

    api_url="http://localhost/api/projects/6461408c-726c-4b70-aa7a-c9cc9d1c9685/add_pipeline/"
    content_type="Content-Type: application/json"
    data='{
        "pipeline": "analyze_docker_image",
        "execute_now": true
    }'

    curl -X POST "$api_url" -H "$content_type" -d "$data"

.. code-block:: json

    {
        "status": "Pipeline added."
    }

.. _rest_api_add_webhook:

Add webhook
^^^^^^^^^^^

This action adds a webhook subscription to the ``project``.
A webhook allows external services to receive real-time notifications about project
pipeline execution events.

``POST /api/projects/d4ed9405-5568-45ad-99f6-782a9b82d1d2/add_webhook/``

Data:
    - ``target_url`` (string, required): The URL to which the webhook will send
      a ``POST`` request when triggered.
    - ``trigger_on_each_run`` (boolean, optional): If ``true``, the webhook will be
      triggered after each individual pipeline run. Default is ``false``.
    - ``include_summary`` (boolean, optional): If ``true``, the webhook payload will
      include the summary data of the pipeline execution. Default is ``false``.
    - ``include_results`` (boolean, optional): If ``true``, the webhook payload will
      include the full results data of the pipeline execution. Default is ``false``.
    - ``is_active`` (boolean, optional): If ``true``, the webhook is active and will
      be triggered when the specified conditions are met. Default is ``true``.

Using cURL:

.. code-block:: console

    api_url="http://localhost/api/projects/6461408c-726c-4b70-aa7a-c9cc9d1c9685/add_webhook/"
    content_type="Content-Type: application/json"
    data='{
        "target_url": "https://example.com/webhook",
        "trigger_on_each_run": true,
        "include_summary": true,
        "include_results": false,
        "is_active": true
    }'

    curl -X POST "$api_url" -H "$content_type" -d "$data"

.. code-block:: json

    {
        "status": "Webhook added."
    }

.. note::
    - Webhooks will only be triggered for active subscriptions.
    - If ``trigger_on_each_run`` is set to ``false``, the webhook will only trigger
      after all pipeline runs are completed.
    - The ``include_summary`` and ``include_results`` fields allow customization of
      the webhook payload.

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

.. _rest_api_compliance:

Compliance
^^^^^^^^^^

This action returns a list of compliance alerts for a project,
filtered by severity level.
The severity level can be customized using the ``fail_level`` query parameter.
Defaults to ``ERROR`` if not provided.

``GET /api/projects/6461408c-726c-4b70-aa7a-c9cc9d1c9685/compliance/?fail_level=WARNING``

Data:
    - ``fail_level``: ``ERROR``, ``WARNING``, ``MISSING``.

.. code-block:: json

    {
        "compliance_alerts": {
            "packages": {
                "warning": [
                    "pkg:generic/package@1.0",
                    "pkg:generic/package@2.0"
                ],
                "error": [
                    "pkg:generic/package@3.0"
                ]
            }
        }
    }

.. _rest_api_license_clarity_compliance:

License Clarity Compliance
^^^^^^^^^^^^^^^^^^^^^^^^^^

This action returns the **license clarity compliance alert** for a project.

The license clarity compliance alert is a single value (``ok``, ``warning``, or ``error``)
that summarizes the project's **license clarity status**, based on the thresholds defined in
the ``policies.yml`` file.

``GET /api/projects/6461408c-726c-4b70-aa7a-c9cc9d1c9685/license_clarity_compliance/``

Data:
    - ``license_clarity_compliance_alert``: The overall license clarity compliance alert
      for the project.

      Possible values: ``ok``, ``warning``, ``error``.

.. code-block:: json

    {
        "license_clarity_compliance_alert": "warning"
    }

.. _rest_api_scorecard_compliance:

Scorecard Compliance
^^^^^^^^^^^^^^^^^^^^

This action returns the **scorecard compliance alert** for a project.

The scorecard compliance alert is a single value (``ok``, ``warning``, or ``error``)
that summarizes the project's **OpenSSF Scorecard security compliance status**,
based on the thresholds defined in the ``policies.yml`` file.

``GET /api/projects/6461408c-726c-4b70-aa7a-c9cc9d1c9685/scorecard_compliance/``

Data:
    - ``scorecard_compliance_alert``: The overall scorecard compliance alert
      for the project.

      Possible values: ``ok``, ``warning``, ``error``.

.. code-block:: json

    {
        "scorecard_compliance_alert": "warning"
    }

Reset
^^^^^

This action will delete all related database entries and all data on disks except for
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

``GET /api/projects/d4ed9405-5568-45ad-99f6-782a9b82d1d2/file_content/?path=filename.ext``

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

The list supports filtering by most fields using the ``?field_name=value`` query
parameter syntax.

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

The list supports filtering by most fields using the ``?field_name=value`` query
parameter syntax.

Dependencies
^^^^^^^^^^^^

Lists all ``dependencies`` of a given ``project``.

``GET /api/projects/d4ed9405-5568-45ad-99f6-782a9b82d1d2/dependencies/``

.. code-block:: json

    [
        {
            "purl": "pkg:pypi/appdirs@1.4.4",
            "extracted_requirement": "==1.4.4",
            "scope": "test",
            "is_runtime": true,
            "is_optional": true,
            "is_pinned": true,
            "is_direct": true,
            "dependency_uid": "pkg:pypi/appdirs@1.4.4?uuid=0033a678-2003-420d-8c83-c4071e646f4e",
            "for_package_uid": "pkg:pypi/platformdirs@4.2.1?uuid=6d90ce5b-a3f8-4110-a4bd-2da5a8930d29",
            "resolved_to_package_uid": null,
            "datafile_path": "platformdirs-4.2.1.dist-info/METADATA",
            "datasource_id": "pypi_wheel_metadata",
            "package_type": "pypi",
            "[...]": "[...]"
        },
    ]

The list supports filtering by most fields using the ``?field_name=value`` query
parameter syntax.

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

Results (Download)
^^^^^^^^^^^^^^^^^^

Finally, use this action to download the project results in the provided
``output_format`` as an attachment file.

Data:
    - ``output_format``: ``json``, ``xlsx``, ``spdx``, ``cyclonedx``, ``attribution``,
      ``all_formats``, ``all_outputs``

``GET /api/projects/d4ed9405-5568-45ad-99f6-782a9b82d1d2/results_download/?output_format=cyclonedx``

.. note::
   Use ``all_formats`` to generate a zip file containing all output formats for a
   project, while ``all_outputs`` can be used to obtain a zip file of all existing
   output files for that project.

.. tip::
  Refer to :ref:`output_files` to learn more about the available output formats.

Run details
-----------

The run details view returns all information available about a pipeline run.

``GET /api/runs/c4d09fe5-c133-4c03-8286-6894ee5ffaab/``

.. code-block:: json

    {
        "url": "http://localhost/api/runs/8d5c3962-5fca-47d7-b8c8-47a19247714e/",
        "pipeline_name": "scan_single_package",
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

XLSX Report
-----------

Generates an XLSX report for selected projects based on specified criteria. The
``model`` query parameter is required to determine the type of data to include in the
report.

Endpoint:
``GET /api/projects/report/?model=MODEL``

Parameters:

- ``model``: Defines the type of data to include in the report.
  Accepted values: ``package``, ``dependency``, ``resource``, ``relation``, ``message``,
  ``todo``.

.. note::

   You can apply any available filters to select the projects to include in the
   report. Filters can be based on project attributes, such as a substring in the
   name or specific labels.

Example Usage:

1. Generate a report for projects tagged with "d2d" and include the ``TODOS`` worksheet:

   .. code-block::

      GET /api/projects/report/?model=todo&label=d2d

2. Generate a report for projects whose names contain "audit" and include the
   ``PACKAGES`` worksheet:

   .. code-block::

      GET /api/projects/report/?model=package&name__contains=audit
