.. _scancodeio_settings:

Application Settings
====================

ScanCode.io is configured with environment variables stored in a ``.env`` file.

The ``.env`` file is created at the root of the ScanCode.io codebase during its
installation.
You can configure your preferences using the following settings in the ``.env``
file.

.. note::
    ScanCode.io is based on the Django web framework and its settings system.
    The list of settings available in Django is documented at
    `Django Settings <https://docs.djangoproject.com/en/dev/ref/settings/>`_.

.. tip::
    Settings specific to ScanCode.io are all prefixed with ``SCANCODEIO_``.

DATABASE
--------

The database can be configured using the following settings::

    SCANCODEIO_DB_HOST=localhost
    SCANCODEIO_DB_NAME=scancodeio
    SCANCODEIO_DB_USER=user
    SCANCODEIO_DB_PASSWORD=password
    SCANCODEIO_DB_PORT=5432

.. _scancodeio_settings_require_authentication:

SCANCODEIO_REQUIRE_AUTHENTICATION
---------------------------------

By default, the ScanCode.io Web UI and REST API are available without any
authentication.

The authentication system can be enable with this settings::

    SCANCODEIO_REQUIRE_AUTHENTICATION=True

Once enabled, all the Web UI views and REST API endpoints will force the user to login
to gain access.

A management command :ref:`cli_create_user` is available to create users and
generate their API key for authentication.

See :ref:`rest_api_authentication` for details on using the ``API key``
authentication system in the REST API.

.. _scancodeio_settings_workspace_location:

SCANCODEIO_WORKSPACE_LOCATION
-----------------------------

This setting defines the workspace location of a given project.
The **workspace** is the directory where **all of the project's files are stored**
, such as input, codebase, and output files::

    SCANCODEIO_WORKSPACE_LOCATION=/var/scancodeio/workspace/

It defaults to a :guilabel:`var/` directory in the local ScanCode.io codebase.

See :ref:`project_workspace` for more details.

SCANCODEIO_PROCESSES
--------------------

By default, multiprocessing is enabled and configured to use an optimal number of CPUs
available on the machine. You can control the number of parallel processes available
to ScanCode.io using the SCANCODEIO_PROCESSES setting::

    SCANCODEIO_PROCESSES=4

Multiprocessing can be disabled entirely using "0"::

    SCANCODEIO_PROCESSES=0

To disable both multiprocessing and threading, use "-1"::

    SCANCODEIO_PROCESSES=-1

.. note::
    Multiprocessing and threading are disabled by default on operating system
    where the multiprocessing start method is not "fork", such as on macOS.

.. _scancodeio_settings_async:

SCANCODEIO_ASYNC
----------------

When enabled, pipeline runs are **executed asynchronously**, meaning that users can
continue using the app while the pipeline are run in the background.

The ASYNC mode is **enabled by default in a "Run with Docker" configuration** but
**disabled in a "Local development" setup**.

It is possible to enable ASYNC mode in a "local development" setup with the following
setting::

    SCANCODEIO_ASYNC=True

Once enabled, pipeline runs will be sent to a task queue instead of being executed
synchronously in the web server process.

.. warning::
    The ASYNC mode required a **Redis server** and running a **tasks worker** using
    ``$ make worker``.

    On macOS, the ASYNC mode requires the following line in your environment::

        export OBJC_DISABLE_INITIALIZE_FORK_SAFETY=YES

SCANCODE_TOOLKIT_CLI_OPTIONS
----------------------------

Use this setting to provide any default options for running ScanCode-toolkit.

.. note::
    Refer to `ScanCode-toolkit Available Options <https://scancode-toolkit.readthedocs.io/en/latest/cli-reference/list-options.html>`_
    for the full list of available options.

The following example explicitly defines a timeout value of 60::

    SCANCODE_TOOLKIT_CLI_OPTIONS=--timeout 60

.. _scancodeio_settings_pipelines_dirs:

SCANCODEIO_TASK_TIMEOUT
-----------------------

Maximum time allowed for a pipeline to complete.
The pipeline run will be stopped and marked as failed if that limit is reached.

The value is a string with specify unit including hour, minute, second
(e.g. "1h", "3m", "5s")::

    SCANCODEIO_TASK_TIMEOUT=24h

Default: ``24h``

SCANCODEIO_SCAN_FILE_TIMEOUT
----------------------------

Maximum time allowed for a file to be analyzed when scanning a codebase.

The value unit is second and is defined as an integer::

    SCANCODEIO_SCAN_FILE_TIMEOUT=120

Default: ``120`` (2 minutes)

SCANCODEIO_PIPELINES_DIRS
-------------------------

This setting defines any additional locations that ScanCode.io will search in
for pipelines.
It usually includes a list of comma-separated strings containing full paths
of additional pipelines directories::

    SCANCODEIO_PIPELINES_DIRS=/var/scancodeio/pipelines/,/home/user/pipelines/

.. _scancodeio_settings_policies_file:

SCANCODEIO_POLICIES_FILE
------------------------

This setting defines the location of the policies file, or ``policies.yml``.
A valid policies file is required to enable compliance-related features.

.. code-block:: yaml

    license_policies:
    -   license_key: mit
        label: Approved License
        compliance_alert: ''
    -   license_key: mpl-2.0
        label: Restricted License
        compliance_alert: warning
    -   license_key: gpl-3.0
        label: Prohibited License
        compliance_alert: error

- Licenses are referenced by the ``license_key``.
- A Policy is defined with ``label`` and ``compliance_alert``.
- The ``compliance_alert`` accepts 3 values: '' for an empty string, warning, and error.

.. note::
    When the policy feature is enabled, the ``compliance_alert`` values are
    displayed in the UI and returned in all downloadable results.

.. tip::
    Check out the :ref:`tutorial_license_policies` tutorial for in-depth coverage of
    this feature.

SCANCODEIO_PAGINATE_BY
----------------------

The number of objects display per page for each object type can be customized with the
following setting::

    SCANCODEIO_PAGINATE_BY=project=30,error=50,resource=100,package=100,dependency=100

SCANCODEIO_REST_API_PAGE_SIZE
-----------------------------

A numeric value indicating the number of objects returned per page in the REST API::

    SCANCODEIO_REST_API_PAGE_SIZE=100

Default: ``50``

.. warning::
    Using a large page size may have an impact on performances.

SCANCODEIO_LOG_LEVEL
--------------------

By default, only a minimum of logging messages is displayed in the console, mostly
to provide some progress about pipeline run execution.

Default: ``INFO``

The ``DEBUG`` value can be provided to this setting to see all ScanCode.io debug
messages to help track down configuration issues for example.
This mode can be enabled globally through the ``.env`` file::

    SCANCODEIO_LOG_LEVEL=DEBUG

Or, in the context of running a :ref:`scanpipe command <command_line_interface>`:

.. code-block:: console

    $ SCANCODEIO_LOG_LEVEL=DEBUG bin/scanpipe [command]

The web server can be started in DEBUG mode with:

.. code-block:: console

    $ SCANCODEIO_LOG_LEVEL=DEBUG make run

TIME_ZONE
---------

A string representing the time zone for the current ScanCode.io installation. By
default the ``UTC`` time zone is used::

    TIME_ZONE=Europe/Paris

.. note::
    You can view a detailed list of time zones `here.
    <https://en.wikipedia.org/wiki/List_of_tz_database_time_zones>`_
