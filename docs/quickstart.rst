.. _quickstart:

QuickStart
==========

Run a Local Directory Scan (no installation required!)
------------------------------------------------------

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

Run a Remote Package Scan
-------------------------

Let's look at another example — this time scanning a **remote package archive** by
providing its **download URL**:

.. code-block:: bash

    docker run --rm \
      ghcr.io/aboutcode-org/scancode.io:latest \
      run scan_single_package https://github.com/aboutcode-org/python-inspector/archive/refs/tags/v0.14.4.zip \
      > results.json

Let's break down what's happening here:

- ``docker run --rm``
  Runs a temporary container that is automatically removed after the scan completes.

- ``ghcr.io/aboutcode-org/scancode.io:latest``
  Uses the latest ScanCode.io image from GitHub Container Registry.

- ``run scan_single_package <URL>``
  Executes the ``scan_single_package`` pipeline, automatically fetching and analyzing
  the package archive from the provided URL.

- ``> results.json``
  Writes the scan results to a local ``results.json`` file.

Notice that the ``-v "$(pwd)":/codedrop`` option is **not required** in this case
because the input is downloaded directly from the provided URL, rather than coming
from your local filesystem.

The result? A **complete scan of a remote package archive — no setup, one command!**

Use PostgreSQL for Better Performance
-------------------------------------

By default, ScanCode.io uses a **temporary SQLite database** for simplicity.
While this works well for quick scans, it has a few limitations — such as
**no multiprocessing** and slower performance on large codebases.

For improved speed and scalability, you can run your pipelines using a
**PostgreSQL database** instead.

Start a PostgreSQL Database Service
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

First, start a PostgreSQL container in the background:

.. code-block:: bash

    docker run -d \
      --name scancodeio-run-db \
      -e POSTGRES_DB=scancodeio \
      -e POSTGRES_USER=scancodeio \
      -e POSTGRES_PASSWORD=scancodeio \
      -e POSTGRES_INITDB_ARGS="--encoding=UTF-8 --lc-collate=en_US.UTF-8 --lc-ctype=en_US.UTF-8" \
      -v scancodeio_pgdata:/var/lib/postgresql/data \
      -p 5432:5432 \
      postgres:17

This command starts a new PostgreSQL service named ``scancodeio-run-db`` and stores its
data in a named Docker volume called ``scancodeio_pgdata``.

.. note::
    You can stop and remove the PostgreSQL service once you are done using:

    .. code-block:: bash

        docker rm -f scancodeio-run-db

.. tip::
    The named volume ``scancodeio_pgdata`` ensures that your database data
    **persists across runs**.
    You can remove it later with ``docker volume rm scancodeio_pgdata`` if needed.

Run a Docker Image Analysis Using PostgreSQL
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Once PostgreSQL is running, you can start a ScanCode.io pipeline
using the same Docker image, connecting it to the PostgreSQL database container:

.. code-block:: bash

    docker run --rm \
      --network host \
      -e SCANCODEIO_NO_AUTO_DB=1 \
      ghcr.io/aboutcode-org/scancode.io:latest \
      run analyze_docker_image docker://alpine:3.22.1 \
      > results.json

Here’s what’s happening:

- ``--network host``
  Ensures the container can connect to the PostgreSQL service running on your host.

- ``-e SCANCODEIO_NO_AUTO_DB=1``
  Tells ScanCode.io **not** to create a temporary SQLite database, and instead use
  the configured PostgreSQL connection defined in its default settings.

- ``ghcr.io/aboutcode-org/scancode.io:latest``
  Uses the latest ScanCode.io image from GitHub Container Registry.

- ``run analyze_docker_image docker://alpine:3.22.1``
  Runs the ``analyze_docker_image`` pipeline, scanning the given Docker image.

- ``> results.json``
  Saves the scan results to a local ``results.json`` file.

The result? A **faster, multiprocessing-enabled scan** backed by PostgreSQL — ideal
for large or complex analyses.

Next Step: Installation
-----------------------

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

ScanCode.io integrates seamlessly into CI/CD pipelines, enabling automated scans on
commits, pull requests, releases, and scheduled events.

**Supported platforms:**

- **GitHub Actions** - Official action with built-in compliance checks
- **GitLab** - Docker-based pipeline integration
- **Jenkins** - Jenkinsfile integration with artifact archiving
- **Azure Pipelines** - Azure DevOps pipeline support
- **Any CI/CD system** - Direct Docker command integration

GitHub Actions
^^^^^^^^^^^^^^

Use the official `scancode-action <https://github.com/aboutcode-org/scancode-action>`_
to integrate ScanCode.io into your GitHub workflows.

**Features:**

- Run pipelines automatically on repository events
- Check for compliance issues and policy violations
- Detect security vulnerabilities
- Generate SBOMs in multiple formats (SPDX, CycloneDX)

**Example usage:**

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

**Learn more:** https://github.com/aboutcode-org/scancode-action

Other CI/CD Platforms
^^^^^^^^^^^^^^^^^^^^^

For setup instructions and examples for other platforms, see the :ref:`automation`
section.
