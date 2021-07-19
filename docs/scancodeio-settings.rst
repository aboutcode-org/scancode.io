.. _scancodeio_settings:

Application Settings
====================

The ``.env`` file is created at the root of the ScanCode.io codebase during its
installation.
You can configure your preferences using the following settings in the ``.env`` file.

DATABASE
--------

The database can be configured using the following settings::

    SCANCODEIO_DB_HOST
    SCANCODEIO_DB_NAME
    SCANCODEIO_DB_USER
    SCANCODEIO_DB_PASSWORD

TIME_ZONE
---------

A string representing the time zone for this ScanCode.io installation.
Default to ``UTC``::

    TIME_ZONE=Europe/Paris

`See the list of time zones <https://en.wikipedia.org/wiki/List_of_tz_database_time_zones>`_

.. _scancodeio_settings_workspace_location:

SCANCODEIO_WORKSPACE_LOCATION
-----------------------------

Define the workspace location.
The workspace is the directory where **all the project files are stored**: input,
codebase, and output files::

    SCANCODEIO_WORKSPACE_LOCATION=/var/scancodeio/workspace/

Default to a :guilabel:`var/` directory in the local ScanCode.io codebase.

See :ref:`Project workspace` for details.

SCANCODEIO_PROCESSES
--------------------

By default, multiprocessing is enabled and setup to use the number of available CPUs on
the machine, minus 1.

You can control the number of parallel processes available to ScanCode.io using the
SCANCODE_PROCESSES setting::

    SCANCODE_PROCESSES=4

Multiprocessing can be disable entirely using "0"::

    SCANCODE_PROCESSES=0

To disable multiprocessing and threading use "-1"::

    SCANCODE_PROCESSES=-1

SCANCODE_DEFAULT_OPTIONS
------------------------

Use this settings to provide default options for running the scancode-toolkit.

Refer to `ScanCode-toolkit Available Options <https://scancode-toolkit.readthedocs.io/en/latest/cli-reference/list-options.html>`_
for the full options list.

The following example explicitly define a value for timeout and set the number
of parallel processes to 4::

    SCANCODE_DEFAULT_OPTIONS=--processes 4,--timeout 120

SCANCODEIO_PIPELINES_DIRS
-------------------------

This setting defines the additional locations ScanCode.io will search for pipelines.
This should be set to a list of comma-separated strings that contain full paths to your additional
pipelines directories::

    SCANCODEIO_PIPELINES_DIRS=/var/scancodeio/pipelines/,/home/user/pipelines/

SCANCODEIO_POLICIES_FILE
------------------------

Location of the policies file. Default: ``policies.yml``.
A valid policies file is required to enable the compliance related features.

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

Licenses are referenced by ``license_key``. The policy is defined with a ``label`` and
a ``compliance_alert``.
The ``compliance_alert`` accepts 3 values: "" (empty string), warning, and error.

When the policy feature is enabled, the ``compliance_alert`` values are displayed in
the UI and returned in all the downloadable results.
