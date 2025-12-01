.. _inputs:

Inputs
======

ScanCode.io supports multiple input types for projects, providing flexibility in how
you provide data for analysis. This section covers all supported input methods.

.. _inputs_file_upload:

File Upload
-----------

You can **upload files directly** to a project through the Web UI or REST API.
Supported file types include archives (e.g., ``.tar``, ``.zip``, ``.tar.gz``),
individual source files, pre-built packages, and **SBOMs** (SPDX or CycloneDX in
JSON format).

When uploading through the Web UI, navigate to your project and use the upload
interface in the "Inputs" panel.

For REST API uploads, refer to the :ref:`rest_api` documentation for endpoint details.

.. _inputs_download_url:

Download URL
------------

Instead of uploading files directly, you can provide a **URL pointing to a remote file**.
ScanCode.io will fetch the file and add it to your project inputs.

**HTTP and HTTPS URLs** are supported::

    https://example.com/path/to/archive.tar.gz

The fetcher handles HTTP redirects and extracts the filename from either the
``Content-Disposition`` header or the URL path.

.. tip::
    For files behind authentication, see :ref:`inputs_authentication`.

.. _inputs_package_url:

Package URL (PURL)
------------------

ScanCode.io integrates with most package repositories using the
`Package URL (PURL) specification <https://github.com/package-url/purl-spec>`_.

A **PURL** is a URL string used to identify and locate a software package in a
mostly universal and uniform way across package managers and ecosystems.

The **general PURL syntax** is::

    pkg:<type>/<namespace>/<name>@<version>?<qualifiers>#<subpath>

Cargo (Rust)
^^^^^^^^^^^^

Fetches packages from `crates.io <https://crates.io/>`_::

    pkg:cargo/rand@0.7.2

Resolves to: ``https://crates.io/api/v1/crates/rand/0.7.2/download``

RubyGems
^^^^^^^^

Fetches packages from `rubygems.org <https://rubygems.org/>`_::

    pkg:gem/bundler@2.3.23

Resolves to: ``https://rubygems.org/downloads/bundler-2.3.23.gem``

npm
^^^

Fetches packages from the `npm registry <https://www.npmjs.com/>`_::

    pkg:npm/is-npm@1.0.0

Resolves to: ``https://registry.npmjs.org/is-npm/-/is-npm-1.0.0.tgz``

PyPI (Python)
^^^^^^^^^^^^^

Fetches packages from `PyPI <https://pypi.org/>`_::

    pkg:pypi/django@5.0

Resolves to: ``https://files.pythonhosted.org/packages/.../Django-5.0.tar.gz``

.. note::
    When multiple distributions are available, the **sdist** (source distribution) is
    used as the preferred choice.

If no version is provided, the **latest available release** will be fetched::

    pkg:pypi/django

Resolves to: ``https://files.pythonhosted.org/packages/.../django-5.2.8.tar.gz``

Hackage (Haskell)
^^^^^^^^^^^^^^^^^

Fetches packages from `Hackage <https://hackage.haskell.org/>`_::

    pkg:hackage/cli-extras@0.2.0.0

Resolves to: ``https://hackage.haskell.org/package/cli-extras-0.2.0.0/cli-extras-0.2.0.0.tar.gz``

NuGet (.NET)
^^^^^^^^^^^^

Fetches packages from `nuget.org <https://www.nuget.org/>`_::

    pkg:nuget/System.Text.Json@6.0.6

Resolves to: ``https://www.nuget.org/api/v2/package/System.Text.Json/6.0.6``

GitHub
^^^^^^

Fetches release archives from `GitHub <https://github.com/>`_ repositories::

    pkg:github/aboutcode-org/scancode-toolkit@3.1.1?version_prefix=v

Resolves to: ``https://github.com/aboutcode-org/scancode-toolkit/archive/v3.1.1.tar.gz``

The ``version_prefix`` qualifier is used when the repository tags include a prefix
(commonly ``v``) before the version number.

Bitbucket
^^^^^^^^^

Fetches archives from `Bitbucket <https://bitbucket.org/>`_ repositories::

    pkg:bitbucket/robeden/trove@3.0.3

Resolves to: ``https://bitbucket.org/robeden/trove/get/3.0.3.tar.gz``

GitLab
^^^^^^

Fetches archives from `GitLab <https://gitlab.com/>`_ repositories::

    pkg:gitlab/tg1999/firebase@1a122122

Resolves to: ``https://gitlab.com/tg1999/firebase/-/archive/1a122122/firebase-1a122122.tar.gz``

Maven (Java)
^^^^^^^^^^^^

Fetches artifacts from Maven repositories. The default repository is Maven Central::

    pkg:maven/org.apache.commons/commons-io@1.3.2

Resolves to: ``https://repo.maven.apache.org/maven2/org/apache/commons/commons-io/1.3.2/commons-io-1.3.2.jar``

You can specify an alternative repository using the ``repository_url`` qualifier::

    pkg:maven/org.apache.commons/commons-io@1.3.2?repository_url=https://repo1.maven.org/maven2

You can also fetch POM files or source JARs using the ``type`` and ``classifier``
qualifiers::

    pkg:maven/org.apache.commons/commons-io@1.3.2?type=pom
    pkg:maven/org.apache.commons/commons-math3@3.6.1?classifier=sources

.. _inputs_docker_reference:

Docker Reference
----------------

ScanCode.io can **fetch Docker images directly** from container registries using the
``docker://`` reference syntax.

Examples::

    docker://nginx:latest
    docker://alpine:3.22.1
    docker://ghcr.io/perfai-inc/perfai-engine:main
    docker://osadl/alpine-docker-base-image:v3.22-latest

The Docker image fetcher uses `Skopeo <https://github.com/containers/skopeo>`_ under
the hood. When fetching multi-platform images, ScanCode.io automatically selects the
first available platform.

For private registries requiring authentication, see the following settings:

- :ref:`SCANCODEIO_SKOPEO_CREDENTIALS <scancodeio_settings_skopeo_credentials>`
- :ref:`SCANCODEIO_SKOPEO_AUTHFILE_LOCATION <scancodeio_settings_skopeo_authfile_location>`

.. _inputs_git_repository:

Git Repository
--------------

You can provide a **Git repository URL** as project input. The repository will be cloned
(with only the latest commit history) at the start of pipeline execution.

Example::

    https://github.com/aboutcode-org/scancode.io.git

.. note::
    SSH URLs (``git@github.com:...``) are not supported. Use HTTPS URLs instead.

.. _inputs_authentication:

Authentication
--------------

For files hosted on private servers or behind authentication, several settings are
available to configure credentials. See :ref:`scancodeio_settings_fetch_authentication`
for details on:

- :ref:`Basic authentication <scancodeio_settings_fetch_basic_auth>`
- :ref:`Digest authentication <scancodeio_settings_fetch_digest_auth>`
- :ref:`HTTP request headers <scancodeio_settings_fetch_headers>` (e.g., for GitHub tokens)
- :ref:`.netrc file <scancodeio_settings_netrc_location>`
- :ref:`Docker private registries <scancodeio_settings_skopeo_credentials>`

.. _inputs_artifactory:

JFrog Artifactory
-----------------

ScanCode.io can fetch artifacts from **JFrog Artifactory** repositories using
standard download URLs.

The URL format follows Artifactory's REST API pattern::

    https://<artifactory-host>/artifactory/<repo-key>/<artifact-path>

Example::

    https://mycompany.jfrog.io/artifactory/libs-release/org/apache/commons/commons-lang3/3.12.0/commons-lang3-3.12.0.jar

For **authentication**, configure credentials in your ``.env`` file using one of
these methods:

Using Basic Authentication::

    SCANCODEIO_FETCH_BASIC_AUTH="mycompany.jfrog.io=username,password"

Using API Key (via headers)::

    SCANCODEIO_FETCH_HEADERS="mycompany.jfrog.io=X-JFrog-Art-Api=<YOUR_API_KEY>"

Using Access Token::

    SCANCODEIO_FETCH_HEADERS="mycompany.jfrog.io=Authorization=Bearer <YOUR_TOKEN>"

.. tip::
    You can also use a :ref:`.netrc file <scancodeio_settings_netrc_location>` for
    authentication if your organization already maintains one.

.. _inputs_nexus:

Sonatype Nexus
--------------

ScanCode.io can fetch artifacts from **Sonatype Nexus Repository** (versions 2 and 3)
using standard download URLs.

For **Nexus 3**, the URL format follows the repository path pattern::

    https://<nexus-host>/repository/<repo-name>/<path-to-artifact>

Example for a Maven artifact::

    https://nexus.mycompany.com/repository/maven-central/ch/qos/logback/logback-core/1.4.0/logback-core-1.4.0.jar

Example for a PyPI package::

    https://nexus.mycompany.com/repository/pypi-proxy/packages/urllib3/1.26.7/urllib3-1.26.7-py2.py3-none-any.whl

Example for an npm package::

    https://nexus.mycompany.com/repository/npm-proxy/redis/-/redis-2.8.0.tgz

For **authentication**, configure credentials in your ``.env`` file:

Using Basic Authentication::

    SCANCODEIO_FETCH_BASIC_AUTH="nexus.mycompany.com=username,password"

Using a Bearer Token::

    SCANCODEIO_FETCH_HEADERS="nexus.mycompany.com=Authorization=Bearer <YOUR_TOKEN>"

.. tip::
    You can also use a :ref:`.netrc file <scancodeio_settings_netrc_location>` for
    authentication if your organization already maintains one.
