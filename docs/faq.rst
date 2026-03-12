.. _faq:

FAQs
====

You can't find what you're looking for? Below you'll find answers to a few of
our frequently asked questions.

How can I run a scan?
---------------------

Once you've completed the ScanCode.io app installation,
you simply start by creating a :ref:`new project <user_interface_create_new_project>`
and run the appropriate pipeline.

ScanCode.io offers several :ref:`built_in_pipelines` depending on your input, see
the :ref:`faq_which_pipeline` below.

As an alternative, If you simply which to run a pipeline without installing ScanCode.io
you may use the Docker image to run pipelines as a single command:

.. code-block:: bash

  docker run --rm \
    -v "$(pwd)":/codedrop \
    ghcr.io/aboutcode-org/scancode.io:latest \
    run scan_codebase /codedrop \
    > results.json

Refer to the :ref:`cli_run` section for more about this approach.

.. tip::
    Prefer a one-liner? Use this to scan your current directory::

        curl -sSL https://raw.githubusercontent.com/aboutcode-org/scancode.io/main/etc/scripts/run-scan.sh | bash

.. _faq_which_pipeline:

Which pipeline should I use?
----------------------------

Selecting the right pipeline for your needs depends primarily on the type of input
data you have available.
Here are some general guidelines based on different input scenarios:

- If you have a **Docker image** as input, use the
  :ref:`analyze_docker_image <pipeline_analyze_docker_image>` pipeline.
- For a full **codebase compressed as an archive**, optionally also with
  it's **pre-resolved dependencies**, and want to detect all the packages
  present linked with their respective files, use the
  :ref:`scan_codebase <pipeline_scan_codebase>` pipeline.
- If you have a **single package archive**, and you want to get information
  on licenses, copyrights and package metadata for it, opt for the
  :ref:`scan_single_package <pipeline_scan_single_package>` pipeline.
- When dealing with a **Linux root filesystem** (rootfs), the
  :ref:`analyze_root_filesystem_or_vm_image <pipeline_analyze_root_filesystem>` pipeline
  is the appropriate choice.
- For processing the results of a **ScanCode-toolkit scan** or **ScanCode.io scan**,
  use the :ref:`load_inventory <pipeline_load_inventory>` pipeline.
- When you want to import **SPDX/CycloneDX SBOMs or ABOUT files** into a project,
  use the :ref:`load_sbom <pipeline_load_sbom>` pipeline.
- When you have **lockfiles or other package manifests** in a codebase and you want to
  resolve packages from their package requirements, use the
  :ref:`resolve_dependencies <pipeline_resolve_dependencies>` pipeline.
- When you have application **package archives/codebases** and optionally also
  their **pre-resolved dependencies** and you want to **inspect packages**
  present in the package manifests and dependency, use the
  :ref:`inspect_packages <pipeline_inspect_packages>` pipeline.
- For scenarios involving both a **development and deployment codebase**, consider using
  the :ref:`map_deploy_to_develop <pipeline_map_deploy_to_develop>` pipeline.
- For getting the DWARF debug symbol compilation unit paths when available from an elf binary.
  use the :ref:`inspect_elf_binaries <pipeline_inspect_elf>` pipeline.

These pipelines will automatically execute the necessary steps to scan and create the
packages, dependencies, and resources for your project based on the input data provided.

After executing one of the pipelines mentioned above, you have the option to
**augment your project's data** by executing additional pipelines, often referred to
as **addon** pipelines.
These additional pipelines offer further enhancements and modifications to your
existing data, allowing for more comprehensive analysis and insights.

- If you wish to **find vulnerabilities** for packages and dependencies, you can use the
  :ref:`find_vulnerabilities <pipeline_find_vulnerabilities>` pipeline.
  Note that setting up :ref:`VulnerableCode <scancodeio_settings_vulnerablecode>` is
  required for this pipeline to function properly.

- To **populate PurlDB with the packages discovered in your project**,
  use the :ref:`populate_purldb <pipeline_populate_purldb>` pipeline.
  Before executing this pipeline, make sure to set up
  :ref:`PurlDB <scancodeio_settings_purldb>`.

- To **match your project codebase resources to MatchCode.io for Package matches**,
  utilize the :ref:`match_to_matchcode <pipeline_match_to_matchcode>` pipeline.
  It's essential to set up :ref:`MatchCode.io <scancodeio_settings_matchcodeio>` before
  executing this pipeline.

What input types are supported?
-------------------------------

ScanCode.io supports **multiple input types** for your projects:

- **File Upload**: Upload archives, source files, packages, or SBOMs directly.
  See :ref:`inputs_file_upload`.

- **Download URL**: Provide an HTTP/HTTPS URL to fetch remote files.
  See :ref:`inputs_download_url`.

- **Package URL (PURL)**: Reference packages from popular registries (npm, PyPI,
  Maven, Cargo, NuGet, RubyGems, and more) using the PURL specification.
  See :ref:`inputs_package_url`.

- **Docker Reference**: Fetch Docker images directly from container registries
  using the ``docker://`` syntax.
  See :ref:`inputs_docker_reference`.

- **Git Repository**: Clone a Git repository using its HTTPS URL.
  See :ref:`inputs_git_repository`.

- **JFrog Artifactory**: Fetch artifacts from on-premise or cloud Artifactory
  repositories.
  See :ref:`inputs_artifactory`.

- **Sonatype Nexus**: Fetch artifacts from Nexus Repository Manager instances.
  See :ref:`inputs_nexus`.

For complete details on all input methods, refer to the :ref:`inputs` documentation.

What is the difference between scan_codebase and scan_single_package pipelines?
-------------------------------------------------------------------------------

The key differences are that the
:ref:`scan_single_package <pipeline_scan_single_package>` pipeline
treats the input as if it were a single package, such as a package archive, and
computes a **License clarity** and a **Scan summary** to aggregate the package scan
data:

.. image:: images/license-clarity-scan-summary.png

In contrast, the :ref:`scan_codebase <pipeline_scan_codebase>` pipeline is more of a
general purpose pipeline and makes no such single package assumption.
It does not compute such summary.

You can also have a look at the different steps for each pipeline from the
:ref:`built_in_pipelines` documentation.

How to create multiple projects at once?
-----------------------------------------

You can use the :ref:`cli_batch_create` command to create multiple projects
simultaneously.
This command processes all files in a specified input directory, creating one project
per file.
Each project is uniquely named using the file name and a timestamp by default.

For example, to create multiple projects from files in a directory named
``local-data/``::

    $ docker compose run --rm \
        --volume local-data/:/input-data:ro \
        web scanpipe batch-create /input-data

**Options**:

- **Custom Pipelines**: Use the ``--pipeline`` option to add specific pipelines to the
  projects.
- **Asynchronous Execution**: Add ``--execute`` and ``--async`` to queue pipeline
  execution for worker processing.
- **Project Notes and Labels**: Use ``--notes`` and ``--label`` to include metadata.

Each file in the input directory will result in the creation of a corresponding project,
ready for pipeline execution.

Can I run multiple pipelines in parallel?
-----------------------------------------

Yes, you can run multiple pipelines in parallel by starting your Docker containers
with the desired number of workers using the following command::

    docker compose up --scale worker=2

.. note:: You can also add extra workers by running the command while the ScanCode.io
   services are already running. For example, to add 2 extra workers to the 2
   currently running ones, use the following command::

        sudo docker compose up --scale worker=4

Can I pause/resume a running pipeline?
--------------------------------------

You can stop/terminate a running pipeline but it will not be possible to resume it.
Although, as a workaround if you run ScanCode.io on desktop or laptop,
you can pause/unpause the running Docker containers with::

    docker compose pause  # to pause/suspend
    docker compose unpause  # to unpause/resume

What tool does ScanCode.io use to analyze docker images?
--------------------------------------------------------

The following tools and libraries are used during the docker images analysis pipeline:

 - `container-inspector <https://github.com/aboutcode-org/container-inspector>`_ and
   `debian-inspector <https://github.com/aboutcode-org/debian-inspector>`_ for handling containers
   and distros.
 - `fetchcode-container <https://pypi.org/project/fetchcode-container/>`_ to download
   containers and images.
 - `scancode-toolkit <https://github.com/aboutcode-org/scancode-toolkit>`_ for application
   package scans and system package scans.
 - `extractcode <https://github.com/aboutcode-org/extractcode>`_ for universal and reliable
   archive extraction.
 - Specific handling of windows containers is done in
   `scancode-toolkit <https://github.com/aboutcode-org/scancode-toolkit>`_ to process the windows registry.
 - Secondary libraries and plugins from
   `scancode-plugins <https://github.com/aboutcode-org/scancode-plugins>`_.

The pipeline documentation is available at :ref:`pipeline_analyze_docker_image` and
its source code at
`docker.py <https://github.com/aboutcode-org/scancode.io/blob/main/scanpipe/pipelines/docker.py>`_.
It is hopefully designed to be simple and readable code.

Am I able to run ScanCode.io on Windows?
----------------------------------------

Yes, you can use the :ref:`run_with_docker` installation. However, please be sure to
carefully read the warnings, as running on Windows may have certain limitations or
challenges.

Is it possible to compare scan results?
---------------------------------------

At the moment, you can only download full reports in JSON and XLSX formats.
Please refer to our :ref:`output_files` section for more details on the output formats.

How can I trigger a pipeline scan from a CI/CD, such as Jenkins, TeamCity or Azure Devops?
------------------------------------------------------------------------------------------

You can refer to the :ref:`automation` to automate your projects management.

Also, A new GitHub action is available at
`scancode-action repository <https://github.com/aboutcode-org/scancode-action>`_
to run ScanCode.io pipelines from your GitHub Workflows.

How can I get notified about my project progression?
-----------------------------------------------------

You can monitor your project's progress in multiple ways:

- **User Interface:** The project details page provides real-time updates on pipeline
  execution.
- **REST API:** Use the API to programmatically check the status of your projects.
- **CLI Monitoring:** The ``scanpipe list-projects`` command provides an overview of
  project states.
- **Webhook Integration:** You can set up webhooks to receive updates in your preferred
  notification system. For more details, refer to the :ref:`webhooks` section.
- **Slack notifications:** Get project updates directly in Slack by configuring an
  incoming webhook. See :ref:`webhooks_slack_notifications` for setup instructions.

.. _faq_tag_input_files:

How to tag input files?
-----------------------

Certain pipelines, including the :ref:`pipeline_map_deploy_to_develop`, require input
files to be tagged. This section outlines various methods to tag input files based on
your project management context.

Using download URLs as inputs
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

You can provide tags using the "#<fragment>" section of URLs. This tagging method is
universally applicable in the User Interface, REST API, and Command Line Interface.

Example:

.. code-block::

    https://url.com/sources.zip#from
    https://url.com/binaries.zip#to

Uploading local files
^^^^^^^^^^^^^^^^^^^^^

There are multiple ways to tag input files when uploading local files:

- **User Interface:** Utilize the "Edit flag" link in the "Inputs" panel of the Project
  details view.

- **REST API:** Use the "upload_file_tag" field in addition to the "upload_file" field.

- **Command Line Interface:** Tag uploaded files using the "filename:tag" syntax.
  Example: ``--input-file path/filename:tag``.

How to fetch files from private sources and protected by credentials?
---------------------------------------------------------------------

Several :ref:`scancodeio_settings_fetch_authentication` settings are available to
define the credentials required to access your private files, depending on the
authentication type:

- :ref:`Basic authentication <scancodeio_settings_fetch_basic_auth>`
- :ref:`Digest authentication <scancodeio_settings_fetch_digest_auth>`
- :ref:`HTTP request headers <scancodeio_settings_fetch_headers>`
- :ref:`.netrc file <scancodeio_settings_netrc_location>`
- :ref:`Docker private repository <scancodeio_settings_skopeo_credentials>`

Example for GitHub private repository files::

    SCANCODEIO_FETCH_HEADERS="github.com=Authorization=token <YOUR_TOKEN>"

Example for Docker private repository::

    SCANCODEIO_SKOPEO_CREDENTIALS="registry.com=user:password"

Can I use a git repository as project input?
--------------------------------------------

Yes, as an alternative to an uploaded file, or an download URL targeting an archive,
you may directly provide the URL to a git repository.
The repository will be cloned in the project inputs, fetching only the latest commit
history, at the start of a pipeline execution.

Note that only the HTTPS type of URL is supported::

    https://<host>[:<port>]/<path-to-git-repo>.git`

A GitHub repository URL example::

    https://github.com/username/repository.git

How can I cleanup my ScanCode.io installation, removing all projects and related data?
--------------------------------------------------------------------------------------

You can use the :ref:`cli_flush_projects` command to perform bulk deletion of projects
and their associated data stored on disk::

    $ scanpipe flush-projects

**Confirmation will be required before deletion.**

To automate this process, such as running it from a cron job, you can use the
``--no-input`` option to skip confirmation prompts.

Additionally, you can retain specific projects and their data based on their
creation date using the ``--retain-days`` option.

Here's an example of a crontab entry that runs daily and flushes all projects and
data older than 7 days::

    @daily scanpipe flush-projects --retain-days 7 --no-input

.. note:: If you are using Docker for running ScanCode.io, you can run the scanpipe
  ``flush-projects`` command using::

    docker compose run --rm web scanpipe flush-projects

  See :ref:`command_line_interface` chapter for more information about the scanpipe
  command.

How can I provide my license policies?
--------------------------------------

For detailed information about the policies system, refer to :ref:`policies`.

Can you analyze Dockerfiles?
----------------------------

We have code in https://github.com/aboutcode-org/container-inspector/blob/main/src/container_inspector/dockerfile.py
for this ... but this may not be wired in other tools at the moment.
It can for instance map dockerfile instructions to actual docker image history,
https://github.com/aboutcode-org/container-inspector/blob/main/src/container_inspector/dockerfile.py#L204

Can you analyze a built image? (Build Docker Image Analysis)
------------------------------------------------------------

Yes, we do this in ScanCode.io. We have one fairly unique feature to actually account
for all files used in all layers.

Can you analyze all layers of a running container?
--------------------------------------------------

ScanCode.io scans all layers of images. We can scan all layers of a running container
if you save the running container as an image first.
We can also fetch images from registries, local files and technically also from a
running container, say in a local docker ... but this has not yet been tested so far.
We do not introspect k8s clusters to analyze the deployed and running images
there (yet) and that would be a nice future addition.
For now we can instead work on the many images there, save and analyze them.

Can you analyze Docker in Docker?
---------------------------------

The input to ScanCode is a local saved image: Docker or OCI.
Docker in Docker support will demand to have access to the saved images
(either extracted from the Docker images in Docker, or mounted in a volume or saved
from the Docker in the Docker image). Once saved we can analyze these alright.

Can I import SBOM from other SCA tools?
---------------------------------------

Yes! You can load SBOMs generated by other tools for further review and run
pipelines to enrich or validate the data directly in ScanCode.io.

While most valid SBOMs should work out of the box, SBOMs from the following tools
are actively supported and tested::

  - Anchore: https://anchore.com/sbom/
  - CycloneDX cdxgen: https://cyclonedx.github.io/cdxgen/
  - OWASP dep-scan: https://owasp.org/www-project-dep-scan/
  - OSS Review Toolkit (ORT): https://oss-review-toolkit.org/ort/
  - OSV-Scanner: https://osv.dev/
  - SBOM tool: https://github.com/microsoft/sbom-tool/
  - Trivy: https://trivy.dev/

.. note:: Imported SBOMs must follow the SPDX or CycloneDX standards, in JSON format.
   You can use the ``load_sbom`` pipeline to process and enhance these SBOMs in your
   ScanCode.io projects.
