.. _installation:

Installation
============

There are three ways to run ScanCode.io:

- :ref:`run_with_docker`: **recommended**, uses the Docker images published on the
  GitHub Container Registry, with all the features available, on all operating systems.
- :ref:`offline_installation`: the same Docker setup, on a server without internet
  access.
- :ref:`local_development_installation`: Docker-based setup for contributors.

.. _run_with_docker:

Run with Docker
---------------

Get Docker
^^^^^^^^^^

The first step is to download and **install Docker on your platform**.
Refer to Docker documentation and choose the best installation
path for your system: `Get Docker <https://docs.docker.com/get-docker/>`_.

Install and Run the App
^^^^^^^^^^^^^^^^^^^^^^^

ScanCode.io is distributed as Docker images published on the GitHub Container
Registry, with a ``docker-compose.yml`` file to run all the required services.

.. note::
    On **Windows**, ensure to use the **wsl** (Windows Subsystem for Linux) for
    the installation process.

.. warning:: On **Windows**, ensure that git ``autocrlf`` configuration is set to
   ``false`` before cloning the repository::

    git config --global core.autocrlf false

**Clone the git** `ScanCode.io repo <https://github.com/aboutcode-org/scancode.io>`_,
create an **environment file**, **pull the Docker images**, and **start the services**::

    git clone https://github.com/aboutcode-org/scancode.io.git && cd scancode.io
    make envfile
    docker compose pull
    docker compose up -d

Go to http://localhost/ on a web browser to **access the web UI**.

.. note::
    ``docker-compose.yml`` uses the ``full`` image of the ScanCode.io release, which
    includes OpenJDK, jadx, and android-inspector for the Android analysis pipeline.

An overview of the web application usage is available at :ref:`user_interface`.

.. note::
    Congratulations, you are now ready to use ScanCode.io, and you can move onto the
    **Tutorials** section starting with the :ref:`tutorial_web_ui_analyze_docker_image`
    tutorial.

.. tip::
    ScanCode.io will take advantage of all the CPUs made available by your Docker
    configuration for faster processing.

    **Make sure to allow enough memory to support each CPU processes**.

    A good rule of thumb is to allow **2 GB of memory per CPU**.
    For example, if Docker is configured for 8 CPUs, a minimum of 16 GB of memory is
    required.

.. tip::
    By default, ScanCode.io starts only 1 worker, which means only 1 pipeline will be
    executed at a time. If you wish to start more workers, use the following command,
    replacing the number 2 with the desired number of workers::

        docker compose up -d --scale worker=2

.. warning::
    To access a dockerized ScanCode.io app from a remote location, the ``ALLOWED_HOSTS``
    and ``CSRF_TRUSTED_ORIGINS`` settings need to be provided in your ``.env`` file,
    for example::

        ALLOWED_HOSTS=.your-domain.com
        CSRF_TRUSTED_ORIGINS=https://*.your-domain.com

    Refer to `ALLOWED_HOSTS settings <https://docs.djangoproject.com/
    en/dev/ref/settings/#allowed-hosts>`_ and `CSRF_TRUSTED_ORIGINS settings
    <https://docs.djangoproject.com/en/dev/ref/settings/
    #std-setting-CSRF_TRUSTED_ORIGINS>`_ for more details.

.. tip::
    If you run ScanCode.io on desktop or laptop, it may come handy to pause/unpause
    or suspend your local ScanCode.io system. For this, use these commands::

        docker compose pause  # to pause/suspend
        docker compose unpause  # to unpause/resume

Upgrade the App
^^^^^^^^^^^^^^^

**Update your local** `ScanCode.io repo <https://github.com/aboutcode-org/scancode.io>`_,
**pull the Docker images** of the new release, and restart the services::

    cd scancode.io
    git pull
    docker compose pull
    docker compose up -d

The ``docker-compose.yml`` file references the image of a given ScanCode.io release:
``git pull`` updates it to the latest release.

.. warning::
    The Docker image has been updated to run as a non-root user.
    If you encounter "permissions" issues while running the ScanCode.io Docker images
    after an upgrade, you will need to update the permissions
    of the ``/var/scancodeio/`` directory of the Docker volumes using::

        docker compose run -u 0:0 web chown -R app:app /var/scancodeio/

    See also https://github.com/aboutcode-org/scancode.io/issues/399

.. note::
    If you run local code changes, see :ref:`build_image_from_source` instead.

.. _build_image_from_source:

Run local code changes
^^^^^^^^^^^^^^^^^^^^^^

By default, ``docker-compose.yml`` runs the published image. To build the ``full``
image from your local checkout and run it, add the ``docker-compose.build.yml`` file
to the command::

    docker compose -f docker-compose.yml -f docker-compose.build.yml up -d --build

Run this command again after each code change or ``git pull`` to rebuild the image.

.. tip::
    A ``docker compose up`` without the ``-f`` options switches back to the published
    image. To use ``docker-compose.build.yml`` in all your ``docker compose`` commands,
    add this line to your ``.env`` file::

        COMPOSE_FILE=docker-compose.yml:docker-compose.build.yml

    To go back to the published image, remove this line, then run
    ``docker compose pull`` and ``docker compose up -d``.

.. note::
    For development with hot reload, see :ref:`local_development_installation`.

Execute a Command
^^^^^^^^^^^^^^^^^

.. note::
    Refer to the :ref:`command_line_interface` section for the full list of commands.

A ``scanpipe`` command can be executed through the ``docker compose`` command line
interface with::

    docker compose exec -it web scanpipe COMMAND

Use alternative HTTP ports
^^^^^^^^^^^^^^^^^^^^^^^^^^

By default, the application is accessible on port 80 for HTTP and 443 for HTTPS
requests. This assumes that these ports are not already occupied by another
application. You can customize both of these ports by adjusting the following
variables in the ``.env`` file, located in the root of the application directory,
next to the ``docker-compose.yml`` file::

    NGINX_PUBLISHED_HTTP_PORT=8080
    NGINX_PUBLISHED_HTTPS_PORT=8443

.. _offline_installation:

Offline installation with Docker
--------------------------------

ScanCode.io can be installed and operated on a server that is not connected to the
internet, such as an "airgapped" or isolated server.

The published Docker images are pulled on a machine with internet access, saved in an
offline installation package, and loaded on the offline server. The package uses the
same ``docker-compose.yml`` file as the online installation: both run the same
services and image versions.

.. note::
    ``docker`` and ``docker compose`` are required on both machines.
    The package contains ``linux/amd64`` images: the offline server must be an
    ``x86_64`` machine.

Build the offline installation package
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

On the machine with internet access, from a clone of the ScanCode.io repository::

    make offline-package

This pulls the Docker images and creates the ``scancodeio-offline-package-VERSION.tar``
tarball in the :guilabel:`dist/` directory.
The tarball contains a :guilabel:`build/` directory with:

- ``scancodeio-images.tar.gz``: all the Docker images used by ``docker-compose.yml``
- ``docker-compose.yml``, ``docker.env``, and the :guilabel:`etc/` configuration directory

Install on the offline server
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Copy the tarball to the server, extract it replacing ``VERSION`` with the actual
version value, and change to the extracted :guilabel:`build/` directory::

    tar -xf scancodeio-offline-package-VERSION.tar
    cd build

Load the Docker images::

    docker load --input scancodeio-images.tar.gz

Create the ``.env`` file with a generated secret key::

    echo "SECRET_KEY=\"$(head -c50 /dev/urandom | base64 | head -c50)\"" > .env

.. warning::
    Keep this ``.env`` file when you upgrade: it holds the secret key of your
    installation.

Run on the offline server
^^^^^^^^^^^^^^^^^^^^^^^^^

Start the ScanCode.io services::

    docker compose up -d

And visit the web UI at: http://localhost/project/

The images are already loaded: ``docker compose`` does not download anything.

.. note::
    To use other ports than 80 and 443, add ``NGINX_PUBLISHED_HTTP_PORT`` and
    ``NGINX_PUBLISHED_HTTPS_PORT`` to the ``.env`` file, as described in the
    "Use alternative HTTP ports" section above.

Upgrade on the offline server
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Build a new package on the machine with internet access. On the server, extract it at
the same location, so the :guilabel:`build/` directory keeps your ``.env`` file, then load
the new images and restart the services::

    tar -xf scancodeio-offline-package-VERSION.tar
    cd build
    docker load --input scancodeio-images.tar.gz
    docker compose up -d

Your data is stored in Docker volumes and is kept across upgrades.

Features not available offline
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The features that need internet access do not work on an offline server:

- Fetching project inputs from a URL, a Git repository, or a Docker image reference.
- The integrations with external services, such as PurlDB, MatchCode.io,
  VulnerableCode, and FederatedCode.
- The :ref:`pipeline_scan_for_virus` pipeline: ClamAV cannot download its virus
  database. To not start the ``clamav`` service at all, use::

    docker compose up -d --scale clamav=0

.. _local_development_installation:

Local development
-----------------

.. note::
    This section is for contributors to ScanCode.io. The development environment
    runs entirely in Docker: no local Python or PostgreSQL installation required.
    Refer to :ref:`contributing` for instructions on submitting changes.

Clone and Configure
^^^^^^^^^^^^^^^^^^^

#. Clone the `ScanCode.io repository <https://github.com/aboutcode-org/scancode.io>`_::

    git clone https://github.com/aboutcode-org/scancode.io.git && cd scancode.io

#. Create an environment file::

    make envfile

Run the App
^^^^^^^^^^^

Build the development image and start all services::

    make run

The application is available at http://localhost:8001/.
Source code changes are reflected immediately in the web application.
Restart the worker to apply them to pipeline runs::

    make restart-worker

.. note::
    ``make run`` is a shortcut for
    ``docker compose -f docker-compose.yml -f docker-compose.dev.yml up``.
    The development image is the ``core`` image: the VM image extraction and the
    Android analysis features of the ``full`` image are not available.

Rebuild the development image after a dependency change with::

    make build

Tests
^^^^^

Run the test suite with::

    make test

.. warning::
    This setup is **not suitable for deployments** and is **only supported for local
    development**.

Helm Chart [Beta]
-----------------

.. warning::
    The Helm Chart is a **community contribution** and is **not tested** by the
    ScanCode.io maintainers. It was last tested with minikube v1.25.1 and helm v3.8.1,
    and may not work with the current ScanCode.io release.
    We welcome improvement suggestions and issue reports at
    `ScanCode.io GitHub repo <https://github.com/aboutcode-org/scancode.io/issues>`_.

Requirements
^^^^^^^^^^^^

`Helm <https://helm.sh>`_ must be installed to use the charts.
Please refer to Helm's `documentation <https://helm.sh/docs/>`_ to get started.

Requires:

* `Kubernetes <https://kubernetes.io/>`_ cluster running with appropriate permissions (depending on your cluster)
* ``kubectl`` set up to connect to the cluster
* ``helm``

Tested on:

* minikube v1.25.1::

    $ minikube version
    minikube version: v1.25.1
    commit: 3e64b11ed75e56e4898ea85f96b2e4af0301f43d

* helm v3.8.1::

    $ helm version
    version.BuildInfo{Version:"v3.8.1",
    GitCommit:"5cb9af4b1b271d11d7a97a71df3ac337dd94ad37",
    GitTreeState:"clean", GoVersion:"go1.17.5"}

Installation
^^^^^^^^^^^^

Once Helm is properly set up, add the ``scancode-kube`` repo as follows::

    # clone github repository
    git clone git@github.com:xerrni/scancode-kube.git

    # create kubernetes namespace
    kubectl create namespace scancode

    # configure values.yaml file
    vi values.yaml

    # install helm dependencies
    helm dependency update

    # check if dependencies are installed
    helm dependency list

    # sample output
    # NAME            VERSION REPOSITORY                              STATUS
    # nginx           9.x.x   https://charts.bitnami.com/bitnami      ok
    # postgresql      17.x.x  https://charts.bitnami.com/bitnami      ok
    # redis           16.x.x  https://charts.bitnami.com/bitnami      ok

    # install scancode helm charts
    helm install scancode ./ --namespace scancode

    # wait until all pods are in Running state
    # afterwards cancel this command as it will run forever
    kubectl get pods -n scancode --watch

    # sample output
    # NAME                                       READY   STATUS    RESTARTS   AGE
    # scancode-nginx-f4d79f44d-4vhlv             1/1     Running   0          5m28s
    # scancode-postgresql-0                      1/1     Running   0          5m28s
    # scancode-redis-master-0                    1/1     Running   0          5m28s
    # scancode-scancodeio-web-5786df657c-khrgb   1/1     Running   0          5m28s
    # scancode-scancodeio-worker-0               1/1     Running   1          5m28s

    # expose nginx frontend
    minikube service --url=true -n scancode scancode-nginx


Gitpod
------

.. warning::
    The Gitpod support is a **community contribution** and is **not tested** by the
    ScanCode.io maintainers. It may not work with the current Gitpod platform or
    ScanCode.io release.
    We welcome improvement suggestions and issue reports at
    `ScanCode.io GitHub repo <https://github.com/aboutcode-org/scancode.io/issues>`_.

Installation
^^^^^^^^^^^^

* Create a new Workspace and open it in VSCode Browser or your preferred IDE.
  Provide the ScanCode.io GitHub repo URL: https://github.com/aboutcode-org/scancode.io

* Open the "TERMINAL" window and create the ``.env`` file with::

    make envfile

* Open the generated ``.env`` file and add the following settings::

    ALLOWED_HOSTS=.gitpod.io
    CSRF_TRUSTED_ORIGINS=https://*.gitpod.io

Run the App
^^^^^^^^^^^

* Pull and run the app containers::

    docker compose pull
    docker compose up

At this stage, the ScanCode.io app is up and running.
To access the app, open the "PORTS" window and open the address for port 80 in your
browser.
