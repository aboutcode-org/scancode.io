.. _automation:

Automation
==========

To **automate ScanCode.io scans and schedule** them for regular execution or in
response to **specific events**, such as commits or releases, you can explore
various available options:

1. Utilize an external ScanCode.io server (REST API)
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
        "https://github.com/nexB/scancode.io/archive/refs/tags/v32.4.0.zip",
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

2. Integrating ScanCode.io with GitHub Workflows
------------------------------------------------

Seamlessly integrate ScanCode.io into your GitHub Workflows to enable automated scans
as an integral part of your development process.

Visit the `scancode-action repository <https://github.com/nexB/scancode-action>`_ to
explore and learn more about the GitHub Action for ScanCode.io.
The repository provides detailed information, usage instructions,
and configuration options to help you incorporate code scanning effortlessly into your
workflows.

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
