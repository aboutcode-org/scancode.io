.. _tutorial_license_policies:

License Policies and Compliance Alerts
======================================

In this tutorial, we'll introduce ScanCode.io's license policies and compliance
alert system and use the results of a pipeline run to demonstrate an example
license and compliance alert output.

.. note::
    For example pipeline runs, you can view our ``Tutorial`` section.

As already mentioned, ScanCode.io automates the process of Software Composition
Analysis—SCA—to identify existing open source components and their license
compliance data in an application's codebase. ScanCode.io also gives users the
ability to define a set of policies—license policies—to have their projects
checked against with a ``ok``, ``missing``, ``warning``, and ``error`` compliance
system.

Creating Policies Files
-----------------------

A valid policies file is required to enable compliance-related features. The
policies file, by default``policies.yml``, is a YAML file with a format
similar to the following,

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

- In the above policies file, licenses are referenced by the ``license_key``,
  such as mit and gpl-3.0, which represents the ScanCode license key to match
  against detected licenses in the scan results.
- A policy is defined with ``label`` and ``compliance_alert``.
- The ``compliance_alert`` accepts 4 values: ``''`` for ``Approved License``,
  ``warning`` for ``Restricted License``, ``error`` for ``Prohibited License``,
  and ``missing`` for ``Missing License``.

Policies File Location
----------------------

During the installation of ScanCode.io, an ``.env`` file is created at the root
of ScanCode.io's codebase. You can configure the location of policies files using
the ``SCANCODEIO_POLICIES_FILE`` setting in the ``.env`` file.

.. tip::
    Check out our :ref:`scancodeio_settings` section for a comprehensive list of
    settings including policies file setting.

How Does The Compliance Alert Work?
-----------------------------------

The compliance system works by following a ``Precedence of Policies`` principal
allowing the highest precedence policy to be applied in case of resources or
packages with complex license expressions. This principal means a given resource
with ``Prohibited`` AND ``Restricted`` AND ``Approved`` license expression would
have an overall policy of ``Prohibited``.

The code block below implements the previous principal by checking alerts for a
given resource or package and having ``error`` as the highest precedence and
``ok`` as the lowest.

.. code-block:: python

    ok = self.Compliance.OK
    error = self.Compliance.ERROR
    warning = self.Compliance.WARNING
    missing = self.Compliance.MISSING

     if error in alerts:
         return error
     elif warning in alerts:
         return warning
     elif missing in alerts:
         return missing
     return ok

Example Output
--------------

We followed the :ref: `tutorial_cli_analyze_docker_image` tutorial to generate
the scan results that show ``""`` compliance alert for a given package.

.. code-block:: json

    {
      "for_packages": [
        "pkg:alpine/busybox@1.31.1-r9?arch=x86_64"
      ],
      "compliance_alert": "",
      "path": "30-alpine-nickolashkraus-staticbox-latest.tar-extract/5216338b40a7b96416b8b9858974bbe4acc3096ee60acbc4dfb1ee02aecceb10/bin/busybox",
      "size": 841288,
      "extra_data": {},
      "copyrights": [],
      "holders": [],
      "authors": [],
      "licenses": [],
      "license_expressions": [],
      "emails": [],
      "urls": [],
      "status": "system-package",
      "type": "file",
      "name": "busybox",
      "extension": "",
      "programming_language": "",
      "mime_type": "application/x-pie-executable",
      "file_type": "ELF 64-bit LSB pie executable, x86-64, version 1 (SYSV), dynamically linked, interpreter /lib/ld-musl-x86_64.so.1, stripped",
      "is_binary": true,
      "is_text": false,
      "is_archive": false,
      "is_key_file": false,
      "is_media": false
    }
