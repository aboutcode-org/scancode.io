.. _scancodeio_settings:

ScanCode.io Settings
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

SCANCODE_DEFAULT_OPTIONS
------------------------

Use this settings to provide default options for running the scancode-toolkit.

Refer to `ScanCode-toolkit Available Options <https://scancode-toolkit.readthedocs.io/en/latest/cli-reference/list-options.html>`_
for the full options list.

The following example explicitly define a value for timeout and set the number
of parallel processes to 4::

    SCANCODE_DEFAULT_OPTIONS=--processes 4,--timeout 60

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
