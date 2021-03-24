.. _scancodeio_settings:

ScanCode.io Settings
====================

The ``.env`` file is created at the root of the ScanCode.io codebase during its
installation.
You can configure your preferences using the following settings in the ``.env``
file.

SCANCODE_DEFAULT_OPTIONS
------------------------

Use this settings to provide default options for running the scancode-toolkit.

Refer to `ScanCode-toolkit Available Options <https://scancode-toolkit.readthedocs.io/en/latest/cli-reference/list-options.html>`_
for the full options list.

The following example explicitly define a value for timeout and set the number
of parallel processes to 4::

    SCANCODE_DEFAULT_OPTIONS=--processes 4,--timeout 60

POLICIES_FILE
-------------

Location of the policies file. Default: ``policies.yml``.
A valid policies file is required to enable the compliance related features.

.. code-block:: yaml

    license_policies:
    -   license_key: mit
        label: Approved License
        color_code: '#008000'
        compliance_alert: ''
    -   license_key: mpl-2.0
        label: Restricted License
        color_code: '#ffcc33'
        compliance_alert: warning
    -   license_key: gpl-3.0
        label: Prohibited License
        color_code: '#c83025'
        compliance_alert: error
