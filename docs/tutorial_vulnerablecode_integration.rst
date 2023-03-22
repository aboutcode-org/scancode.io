.. _tutorial_vulnerablecode_integration:

Find vulnerabilities (Web UI)
=============================

This tutorial aims to show you how to integrate VulnerableCode with ScanCode.io and
how to discover vulnerable packages using the ``find_vulnerabilities`` pipeline.

.. note::
    This tutorial assumes that you have a working installation of ScanCode.io.
    If you don't, please refer to the :ref:`installation` page.

Configure VulnerableCode integration
------------------------------------

.. warning::
    The ``find_vulnerabilities`` pipeline requires access to a VulnerableCode database.

You can either run your own instance of VulnerableCode or connect to the public one.
Authentication is provided using an API key that you can obtain by registering at
https://public.vulnerablecode.io/account/request_api_key/

Set the VulnerableCode URL and API key in your local settings:
  - in the ``docker.env`` file if your run with docker
  - in the ``.env`` for a local development deployment

The resulting ``docker.env``/``.env`` file should contain the following::

    VULNERABLECODE_URL = "https://public.vulnerablecode.io/"
    VULNERABLECODE_API_KEY = "<VulnerableCode API key>"

.. note::
    Optionally contact nexB support at support@nexb.com with your API user email if
    you are doing a larger scale evaluation and need to ease API throttling limitations.

Run the ``find_vulnerabilities`` pipeline
-----------------------------------------

Open any of your existing projects containing a few detected packages.

.. note::
    If you do not have any projects available, please start with this tutorial:
    :ref:`tutorial_web_ui_analyze_docker_image`

- Click on the **"Add pipeline"** button and select the **"find_vulnerabilities"**
  pipeline from the dropdown list.
  Check the **"Execute pipeline now"** option and validate with the **"Add pipeline"**
  button.

- Once the pipeline run completes with success, you can reach the **Packages** list view
  by clicking the count number under the **"PACKAGES"** header:

.. image:: images/tutorial-find-vulnerabilities-packages-link.png

- A red bug icon is displayed next to all packages for which declared vulnerabilities
  were found:

.. image:: images/tutorial-find-vulnerabilities-icon-link.png

- Click red bug icon to reach the vulnerability details for this package:

.. image:: images/tutorial-find-vulnerabilities-extra-data.png
