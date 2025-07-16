.. _policies:

License Policies and Compliance Alerts
======================================

ScanCode.io enables you to define **license policies** that check your projects
against a **compliance system**.

Creating Policies Files
-----------------------

A valid policies file is required to **enable compliance-related features**.

The policies file, by default named ``policies.yml``, is a **YAML file** with a
structure similar to the following:

.. code-block:: yaml

    license_policies:
      - license_key: mit
        label: Approved License
        compliance_alert: ''

      - license_key: mpl-2.0
        label: Restricted License
        compliance_alert: warning

      - license_key: gpl-3.0
        label: Prohibited License
        compliance_alert: error

      - license_key: OFL-1.1
        compliance_alert: warning

      - license_key: LicenseRef-scancode-public-domain
        compliance_alert: ''

      - license_key: LicenseRef-scancode-unknown-license-reference
        compliance_alert: error

- In the example above, licenses are referenced using the ``license_key`` field.
  These keys can be either **ScanCode license identifiers** (e.g., "mit", "gpl-3.0"),
  or **SPDX license identifiers** (e.g., "OFL-1.1",
  "LicenseRef-scancode-public-domain").
  These values are used to match against the licenses detected in scan results.

- Each policy entry includes a ``label`` and a ``compliance_alert`` field.
  The ``label`` is a customizable description used for display or reporting purposes.

- The ``compliance_alert`` field determines the severity level for a license and
  supports the following values:

  - ``''`` (empty string) — No action needed; the license is approved.
  - ``warning`` — Use with caution; the license may have some restrictions.
  - ``error`` — The license is prohibited or incompatible with your policy.

App Policies
------------

Policies can be enabled for the entire ScanCode.io app instance or on a per-project
basis.

By default, ScanCode.io will look for a ``policies.yml`` file in the root of its
application codebase.

Alternatively, you can specify the location of your policies file in your ``.env`` file
using the :ref:`scancodeio_settings_policies_file` setting.

If a policies file is found at this location, those policies will be applied to
all projects in the ScanCode.io instance.

.. tip::
    Refer to the :ref:`scancodeio_settings` section for a full list of settings,
    including the policies file setting.

Per-Project Policies
--------------------

Project-specific policies can be provided via a ``policies.yml`` file as one of the
project inputs or by defining the ``policies`` value in the
:ref:`project_configuration`.

Compliance Alerts Ranking
-------------------------

The compliance system uses a ``Precedence of Policies`` principle, which ensures the
highest-priority policy is applied in cases where resources or packages have complex
license expressions:

- **error > warning > missing > '' (empty string)**

This principle means that if a resource has an ``error``, ``warning``, and ``''``
in its license expression, the overall compliance alert for that resource would be
``error``.

.. warning::
    The ``missing`` compliance alert value is applied for licenses not included in the
    policies file.

Web UI
------

Compliance alerts are shown directly in the Web user interface in the following
locations:

* A summary panel in the project detail view:

  .. image:: images/tutorial-policies-compliance-alerts-panel.png

* A dedicated column in the Packages and Resources list tables:

  .. image:: images/tutorial-policies-compliance-alerts-column.png

REST API
--------

For more details on retrieving compliance data through the REST API, see the
:ref:`rest_api_compliance` section.

Command Line Interface
----------------------

A dedicated ``check-compliance`` management command is available. See the
:ref:`cli_check_compliance` section for more information.
