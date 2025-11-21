.. _automation:

Automation
==========

**Automate ScanCode.io scans** by integrating them into your CI/CD pipelines or
scheduling them to run on specific events such as commits, pull requests, or releases.

CI/CD Integrations
------------------

Seamlessly integrate ScanCode.io into your development workflow to automatically scan
code for licenses, vulnerabilities, and compliance issues.

GitHub Actions
^^^^^^^^^^^^^^

Use the official `scancode-action <https://github.com/aboutcode-org/scancode-action>`_
to integrate ScanCode.io into your GitHub workflows.

**Features:**

- Run ScanCode.io pipelines automatically
- Check for compliance issues and policy violations
- Detect security vulnerabilities
- Generate SBOMs in multiple formats (SPDX, CycloneDX)
- Export results in JSON and XLSX formats

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


**Documentation:**
https://github.com/aboutcode-org/scancode-action

Jenkins
^^^^^^^

Integrate ScanCode.io into your Jenkins pipelines with a simple Jenkinsfile.

**Quick example:**

.. code-block:: groovy

    pipeline {
        agent any

        stages {
            stage('Scan') {
                steps {
                    sh '''
                        docker run --rm \
                          -v "${WORKSPACE}":/codedrop \
                          ghcr.io/aboutcode-org/scancode.io:latest \
                          run scan_codebase /codedrop \
                          > scancode_results.json
                    '''
                    archiveArtifacts 'scancode_results.json'
                }
            }
        }
    }

**Full documentation:**
https://github.com/aboutcode-org/scancode-action/blob/main/jenkins/README.md

GitLab
^^^^^^

Run ScanCode.io scans in your GitLab pipelines.

**Full documentation:**
https://github.com/aboutcode-org/scancode-action/blob/main/gitlab/README.md

Azure Pipelines
^^^^^^^^^^^^^^^

Run ScanCode.io scans in Azure DevOps pipelines.

**Full documentation:**
https://github.com/aboutcode-org/scancode-action/blob/main/azure-pipelines/README.md

Other CI/CD Systems
^^^^^^^^^^^^^^^^^^^

ScanCode.io can be integrated into **any CI/CD system** that supports Docker using the
:ref:`RUN command <cli_run>`.

**Requirements:**

- Docker must be installed and available in your CI/CD environment
- Sufficient disk space for Docker images and scan results

**Basic command:**

.. code-block:: bash

    docker run --rm \
      -v "$(pwd)":/codedrop \
      ghcr.io/aboutcode-org/scancode.io:latest \
      run [PIPELINE] [INPUTS] \
      > scancode_results.json

Replace ``[PIPELINE]`` with your desired pipeline (e.g., ``scan_codebase``,
``scan_single_package``) and ``[INPUTS]`` with the path to scan.

See :ref:`available pipelines <built_in_pipelines>` for more options.

**Example with specific pipeline:**

.. code-block:: bash

    docker run --rm \
      -v "$(pwd)":/codedrop \
      ghcr.io/aboutcode-org/scancode.io:latest \
      run scan_codebase /codedrop \
      > scancode_results.json

2. Utilize an external ScanCode.io server (REST API)
----------------------------------------------------

If you have access to an external ScanCode.io server, you can interact with it
programmatically through the :ref:`rest_api` to **trigger scans automatically**.

You can use the following Python script as a base and execute it from various
automation methods such as a cron job or a git hook::

    from datetime import datetime
    from os import getenv

    import requests

    # Configure the following variables to your needs
    PROJECT_NAME = f"scan-{datetime.now().isoformat()}"
    INPUT_URLS = [
        "https://github.com/aboutcode-org/scancode.io/archive/refs/tags/v32.4.0.zip",
    ]
    PIPELINES = [
        "inspect_packages",
        "find_vulnerabilities",
    ]
    EXECUTE_NOW = True


    def create_project():
        session = requests.Session()

        # ScanCode.io server location
        SCANCODEIO_URL = getenv("SCANCODEIO_URL", default="").rstrip("/")
        if not SCANCODEIO_URL:
            raise ValueError("SCANCODEIO_URL value missing from the env")

        # Optional authentication
        SCANCODEIO_API_KEY = getenv("SCANCODEIO_API_KEY")
        if SCANCODEIO_API_KEY:
            session.headers.update({"Authorization": f"Token {SCANCODEIO_API_KEY}"})

        projects_api_url = f"{SCANCODEIO_URL}/api/projects/"
        project_data = {
            "name": PROJECT_NAME,
            "input_urls": INPUT_URLS,
            "pipeline": PIPELINES,
            "execute_now": EXECUTE_NOW,
        }

        response = session.post(projects_api_url, data=project_data)
        print(response.json())


    if __name__ == "__main__":
        create_project()


.. note::
    Before running this script, ensure that the environment variables ``SCANCODEIO_URL``
    and ``SCANCODEIO_API_KEY`` (when authentication is enabled) are set correctly.
    You can set the environment variables within the script command itself using the
    following format::

        SCANCODEIO_URL="https://..." SCANCODEIO_API_KEY="apikey..." python script.py

    By providing the required environment variables in this manner, you can execute the
    script with the appropriate configurations and credentials.

3. Run a Local ScanCode.io app on your machine (management commands)
--------------------------------------------------------------------

To automate scans within your local environment, you can run the ScanCode.io app
directly on your machine and leverage the :ref:`command_line_interface`.

For instance, you can create a project and trigger it using the following command in a
crontab::

    docker compose exec -it web scanpipe create-project scan-$(date +"%Y-%m-%dT%H:%M:%S") \
      --pipeline scan_single_package \
      --input-url https://github.com/package-url/packageurl-python/archive/refs/heads/main.zip \
      --execute

By executing this command, you initiate the project creation process, and the scan
will be triggered automatically based on the specified pipeline and input URL.
