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

Creating Clarity Thresholds Files
---------------------------------

A valid clarity thresholds file is required to **enable license clarity compliance features**.

The clarity thresholds file, by default named ``policies.yml``, is a **YAML file** with a
structure similar to the following:

.. code-block:: yaml

    license_clarity_thresholds:
      91: ok
      80: warning
      0: error

- In the example above, the keys ``91``, ``80``, and ``0`` are integer threshold values
  representing **minimum clarity scores**.
- The values ``error``, ``warning``, and ``ok`` are the **compliance alert levels** that
  will be triggered if the project's license clarity score meets or exceeds the
  corresponding threshold.
- The thresholds must be listed in **strictly descending order**.

How it works:

- If the clarity score is **91 or above**, the alert is **``ok``**.
- If the clarity score is **80 to 90**, the alert is **``warning``**.
- If the clarity score is **below 80**, the alert is **``error``**.

You can adjust the threshold values and alert levels to match your organization's
compliance requirements.

Accepted values for the alert level:

- ``ok``
- ``warning``
- ``error``

Creating Scorecard Thresholds Files
-----------------------------------

A valid scorecard thresholds file is required to **enable OpenSSF Scorecard compliance features**.

The scorecard thresholds file, by default named ``policies.yml``, is a **YAML file** with a
structure similar to the following:

.. code-block:: yaml

    scorecard_score_thresholds:
      9.0: ok
      7.0: warning
      0: error

- In the example above, the keys ``9.0``, ``7.0``, and ``0`` are numeric threshold values
  representing **minimum scorecard scores**.
- The values ``error``, ``warning``, and ``ok`` are the **compliance alert levels** that
  will be triggered if the project's scorecard score meets or exceeds the
  corresponding threshold.
- The thresholds must be listed in **strictly descending order**.

How it works:

- If the scorecard score is **9.0 or above**, the alert is **``ok``**.
- If the scorecard score is **7.0 to 8.9**, the alert is **``warning``**.
- If the scorecard score is **below 7.0**, the alert is **``error``**.

You can adjust the threshold values and alert levels to match your organization's
security compliance requirements.

Accepted values for the alert level:

- ``ok``
- ``warning``
- ``error``

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
:ref:`rest_api_compliance` section and :ref:`rest_api_license_clarity_compliance`
section.

Command Line Interface
----------------------

A dedicated ``check-compliance`` management command is available. See the
:ref:`cli_check_compliance` section for more information.
