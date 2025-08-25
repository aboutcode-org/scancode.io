.. _tutorial_license_policies:

License Policies and Compliance Alerts
======================================

In this tutorial, we'll introduce ScanCode.io's **license policies** and
**compliance alerts** system and use the **results of a pipeline run** to demonstrate
an example of the license policies and compliance alerts output.

As already mentioned, ScanCode.io automates the process of
**Software Composition Analysis "SCA"** to identify existing open source components
and their license compliance data in an application's codebase.

ScanCode.io also gives users the ability to define a set of **license policies** to
have their projects checked against with a **compliance system**.

Refer to :ref:`policies` for details about the policies system.

Instructions
------------

Create a ``policies.yml`` file with the following content:

.. code-block:: yaml

    license_policies:
    -   license_key: mit
        label: Approved License
        compliance_alert: ''
    -   license_key: gpl-3.0
        label: Prohibited License
        compliance_alert: error

Run the following command to create a project and run the ``scan_codebase`` pipeline
(make sure to use the proper path for the policies.yml file):

.. code-block:: bash

    $ scanpipe create-project cuckoo-filter-with-policies \
        --input-url https://files.pythonhosted.org/packages/75/fc/f5b2e466d763dcc381d5127b73ffc265e8cdaf39ddafa422b7896e625432/cuckoo_filter-1.0.6.tar.gz \
        --input-file policies.yml \
        --pipeline scan_codebase \
        --execute

Generate results:

.. code-block:: bash

    $ scanpipe output --print --project cuckoo-filter-with-policies

The computed compliance alerts are now included in the results, available for each
detected license, and computed at the codebase resource level, for example:

.. code-block:: json

    {
      "for_packages": [],
      "compliance_alert": "error",
      "path": "cuckoo_filter-1.0.6.tar.gz-extract/cuckoo_filter-1.0.6/README.md",
      "licenses": [
        {
          "key": "mit",
          "name": "MIT License",
          "policy": {
            "label": "Recommended License",
            "compliance_alert": ""
          },
        },
        {
          "key": "gpl-3.0",
          "name": "GNU General Public License 3.0",
          "policy": {
            "label": "Prohibited License",
            "compliance_alert": "error"
          }
        }
      ],
      "license_expressions": [
        "mit OR gpl-3.0"
      ],
      "status": "scanned",
      "name": "README",
      "[...]": "[...]"
    }

License Clarity Thresholds and Compliance
-----------------------------------------

ScanCode.io also supports **license clarity thresholds**, allowing you to enforce
minimum standards for license detection quality in your codebase. This is managed
through the ``license_clarity_thresholds`` section in your ``policies.yml`` file.

Defining Clarity Thresholds
---------------------------

Add a ``license_clarity_thresholds`` section to your ``policies.yml`` file, for example:

.. code-block:: yaml

    license_clarity_thresholds:
      91: ok
      80: warning
      0: error


License Clarity Compliance in Results
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

When you run a pipeline with clarity thresholds defined in your ``policies.yml``,
the computed license clarity compliance alert is included in the project's ``extra_data`` field.

For example:

.. code-block:: json

    "extra_data": {
      "md5": "d23df4a4",
      "sha1": "3e9b61cc98c",
      "size": 3095,
      "sha256": "abacfc8bcee59067",
      "sha512": "208f6a83c83a4c770b3c0",
      "filename": "cuckoo_filter-1.0.6.tar.gz",
      "sha1_git": "3fdb0f82ad59",
      "license_clarity_compliance_alert": "error"
    }

The ``license_clarity_compliance_alert`` value (e.g., ``"error"``, ``"warning"``, or ``"ok"``)
is computed automatically based on the thresholds you configured and reflects the
overall license clarity status of the scanned codebase.

Scorecard Compliance Thresholds and Alerts
------------------------------------------

ScanCode.io also supports **OpenSSF Scorecard compliance thresholds**, allowing you to enforce
minimum security standards for open source packages in your codebase. This is managed
through the ``scorecard_score_thresholds`` section in your ``policies.yml`` file.

Defining Scorecard Thresholds
-----------------------------

Add a ``scorecard_score_thresholds`` section to your ``policies.yml`` file, for example:

.. code-block:: yaml

    scorecard_score_thresholds:
      9.0: ok
      7.0: warning
      0: error

Scorecard Compliance in Results
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

When you run a the addon pipeline fetch_scores with scorecard thresholds defined in your
``policies.yml``, the computed scorecard compliance alert is included in the project's
``extra_data`` field.

For example:

.. code-block:: json

    "extra_data": {
      "md5": "d23df4a4",
      "sha1": "3e9b61cc98c",
      "size": 3095,
      "sha256": "abacfc8bcee59067",
      "sha512": "208f6a83c83a4c770b3c0",
      "filename": "cuckoo_filter-1.0.6.tar.gz",
      "sha1_git": "3fdb0f82ad59",
      "scorecard_compliance_alert": "warning"
    }

The ``scorecard_compliance_alert`` value (e.g., ``"error"``, ``"warning"``, or ``"ok"``)
is computed automatically based on the thresholds you configured and reflects the
overall security compliance status of the OpenSSF Scorecard scores for packages in the scanned codebase.

Run the ``check-compliance`` command
------------------------------------

Run the ``check-compliance`` command to get a listing of the compliance alerts detected
in the project:

.. code-block:: bash

    $ scanpipe check-compliance --project cuckoo-filter-with-policies --verbosity 2

.. code-block:: bash

    5 compliance issues detected on this project.
    [packages]
     > ERROR: 3
       pkg:pypi/cuckoo-filter@.
       pkg:pypi/cuckoo-filter@1.0.6
       pkg:pypi/cuckoo-filter@1.0.6
    [resources]
     > ERROR: 1
       cuckoo_filter-1.0.6.tar.gz-extract/cuckoo_filter-1.0.6/README.md
    [license clarity]
     > ERROR

.. tip::
    In case of compliance alerts, the command returns a non-zero exit code which
    may be useful to trigger a failure in an automated process.
