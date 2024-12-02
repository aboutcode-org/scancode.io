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

Run the ``check-compliance`` command
------------------------------------

Run the ``check-compliance`` command to get a listing of the compliance alerts detected
in the project:

.. code-block:: bash

    $ scanpipe check-compliance --project cuckoo-filter-with-policies --verbosity 2

.. code-block:: bash

    4 compliance issues detected on this project.
    [packages]
     > ERROR: 3
       pkg:pypi/cuckoo-filter@.
       pkg:pypi/cuckoo-filter@1.0.6
       pkg:pypi/cuckoo-filter@1.0.6
    [resources]
     > ERROR: 1
       cuckoo_filter-1.0.6.tar.gz-extract/cuckoo_filter-1.0.6/README.md

.. tip::
    In case of compliance alerts, the command returns a non-zero exit code which
    may be useful to trigger a failure in an automated process.
