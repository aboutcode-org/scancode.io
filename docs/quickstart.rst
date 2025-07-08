.. _quickstart:

QuickStart
==========

Run a Scan (no installation required!)
--------------------------------------

The **fastest way** to get started and **scan a codebase** —
**no installation needed** — is by using the latest
**ScanCode.io Docker image**.

.. warning::
    **Docker must be installed on your system**.
    Visit the `Docker documentation <https://docs.docker.com/get-docker/>`_ to install
    it for your platform.

To run the :ref:`pipeline_scan_codebase` pipeline on a **local directory**
with a **single command**:

.. code-block:: bash

    docker run --rm \
      -v "$(pwd)":/codedrop \
      ghcr.io/aboutcode-org/scancode.io:latest \
      run scan_codebase /codedrop \
      > results.json

Let's unpack what each part of the command does:

- ``docker run --rm``
  Runs a temporary Docker container that is automatically removed after it finishes.

- ``-v "$(pwd)":/codedrop``
  Mounts your current directory into the container at ``/codedrop`` so it can be
  scanned.

- ``ghcr.io/aboutcode-org/scancode.io:latest``
  Uses the latest ScanCode.io image from GitHub Container Registry.

- ``run scan_codebase /codedrop``
  Runs the ``scan_codebase`` pipeline inside the container, using the mounted directory
  as the input source.

- ``> results.json``
  Saves the scan output to a ``results.json`` file on your machine.

The result? A **full scan of your local directory — no setup, one command!**

See the :ref:`RUN command <cli_run>` section for more details on this command.

.. note::
    Not sure which pipeline to use? Check out :ref:`faq_which_pipeline`.

Next Step: Local Installation
-----------------------------

Install ScanCode.io, to **unlock all features**:

- **User Interface:** Explore dashboards, codebase data, charts, and scan results.
  See :ref:`user_interface`.
- **Project Management:** Create, filter, and monitor projects.
- **REST API:** Automate your scans with the :ref:`rest_api`.
- **CLI:** Use the :ref:`command_line_interface` to work from the terminal.
- **Webhooks:** Get real-time updates via custom integrations. See :ref:`webhooks`.
- **Slack Notifications:** Send project updates to Slack. Follow setup in
  :ref:`webhooks_slack_notifications`.

See the :ref:`installation` chapter for the full list of installation options.

Integrate with Your Workflows
-----------------------------

ScanCode.io can be part of your CI/CD workflow.

GitHub Actions
^^^^^^^^^^^^^^

Use the official `scancode-action <https://github.com/aboutcode-org/scancode-action>`_
to integrate **ScanCode.io into your GitHub workflows** with ease.

This action lets you:

- **Run pipelines**
- **Check for compliance issues**
- **Detect vulnerabilities**
- **Generate SBOMs and scan results**

Example usage:

.. code-block:: yaml

    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          path: scancode-inputs
      - uses: aboutcode-org/scancode-action@main
        with:
          pipelines: "scan_codebase"
          output-formats: "json xlsx spdx cyclonedx"

Full details available at:
https://github.com/aboutcode-org/scancode-action

.. tip::
    Learn more about automation options in the :ref:`automation` section.
