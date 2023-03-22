.. _installation:

Installation
============

Welcome to **ScanCode.io** installation guide! This guide describes how to install
ScanCode.io on various platforms.
Please read and follow the instructions carefully to ensure your installation is
functional and smooth.

The **preferred ScanCode.io installation** is to :ref:`run_with_docker` as this is
the simplest to setup and get started.
Running ScanCode.io with Docker **guarantee the availability of all features** with the
**minimum configuration** required.
This installation **works across all Operating Systems**.

Alternatively, you can install ScanCode.io locally as a development server with some
limitations and caveats. Refer to the :ref:`local_development_installation` section.

.. _run_with_docker:

Run with Docker
---------------

Get Docker
^^^^^^^^^^

The first step is to download and **install Docker on your platform**.
Refer to Docker documentation and choose the best installation
path for your system: `Get Docker <https://docs.docker.com/get-docker/>`_.

Build the Image
^^^^^^^^^^^^^^^

ScanCode.io is distributed with ``Dockerfile`` and ``docker-compose.yml`` files
required for the creation of the Docker image.

.. warning:: On **Windows**, ensure that git ``autocrlf`` configuration is set to
   ``false`` before cloning the repository::

    git config --global core.autocrlf false

**Clone the git** `ScanCode.io repo <https://github.com/nexB/scancode.io>`_,
create an **environment file**, and **build the Docker image**::

    git clone https://github.com/nexB/scancode.io.git && cd scancode.io
    make envfile
    docker compose build

.. warning::
    As the ``docker-compose`` v1 command is officially deprecated by Docker, you will
    only find references to the ``docker compose`` v2 command in this documentation.

.. note::
    You need to rebuild the image whenever ScanCode.io's source code has been
    modified or updated::

        docker compose build

Run the App
^^^^^^^^^^^

**Run your image** as a container::

    docker compose up

At this point, the ScanCode.io app should be running at port 80 on your Docker host.
Go to http://localhost/ on a web browser to **access the web UI**.

An overview of the web application usage is available at :ref:`user_interface`.

.. note::
    Congratulations, you are now ready to use ScanCode.io, and you can move onto the
    **Tutorials** section starting with the :ref:`tutorial_web_ui_analyze_docker_image`
    tutorial.

.. tip::
    ScanCode.io will take advantage of all the CPUs made available by your Docker
    configuration for faster processing.

    **Make sure to allow enough memory to support each CPU processes**.

    A good rule of thumb is to allow **1 GB of memory per CPU**.
    For example, if Docker is configured for 8 CPUs, a minimum of 8 GB of memory is
    required.

.. warning::
    To access a dockerized ScanCode.io app from a remote location, the ``ALLOWED_HOSTS``
    and ``CSRF_TRUSTED_ORIGINS`` settings need to be provided in your ``.env`` file,
    for example::

        ALLOWED_HOSTS=.your-domain.com,localhost,127.0.0.1
        CSRF_TRUSTED_ORIGINS=https://*.your-domain.com,http://127.0.0.1:8001

    Refer to `ALLOWED_HOSTS settings <https://docs.djangoproject.com/
    en/dev/ref/settings/#allowed-hosts>`_ and `CSRF_TRUSTED_ORIGINS settings
    <https://docs.djangoproject.com/en/dev/ref/settings/
    #std-setting-CSRF_TRUSTED_ORIGINS>`_ for more details.

.. tip::
    If you run ScanCode.io on desktop or laptop, it may come handy to pause/unpause
    or suspend your local ScanCode.io system. For this, use these commands::

        docker compose pause  # to pause/suspend
        docker compose unpause  # to unpause/resume

Execute a Command
^^^^^^^^^^^^^^^^^

.. note::
    Refer to the :ref:`command_line_interface` section for the full list of commands.

A ``scanpipe`` command can be executed through the ``docker compose`` command line
interface with::

    docker compose exec -it web scanpipe COMMAND

.. _offline_installation:

Offline installation with Docker
--------------------------------

It is possible to install and run ScanCode.io on a server which is not connected to
internet.

The Docker images are build on a machine with internet access and copied to the server.

.. note::
    The ``docker`` command is required on both the local machine and the server.

Build the Images
^^^^^^^^^^^^^^^^

Build and save the docker images on your local machine::

    make docker-images

A compressed tarball ``scancodeio-images-VERSION.tar.gz`` containing all the docker
images will be created in the :guilabel:`dist/` directory.

Copy Images and docker-compose files
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Copy the compressed tarball and the local ``docker-compose.yml`` file to the server.

.. warning::
    The ``docker-compose.yml`` file is required to run the application.

Load the Images
^^^^^^^^^^^^^^^

Copy the tarball to the server and load the images::

    docker load --input scancodeio-images-VERSION.tar.gz

Run the App
^^^^^^^^^^^

Start the ScanCode.io services::

    docker compose --file docker-compose.yml up

.. note::
    The nginx service (webserver) requires the port 80 to be available on the host.
    In case the port 80 is already in used, you will encounter the following error::

        ERROR: for build_nginx_1 Cannot start service nginx: driver failed programming ...

    You can attempt to stop potential running services blocking the port 80 with the
    following commands on the host before starting ScanCode.io services::

         sudo systemctl stop nginx
         sudo systemctl stop apache2

.. _local_development_installation:

Local development installation
------------------------------

Supported Platforms
^^^^^^^^^^^^^^^^^^^

**ScanCode.io** has been tested and is supported on the following operating systems:

    #. **Debian-based** Linux distributions
    #. **macOS** 10.14 and up

.. warning::
     On **Windows** ScanCode.io can **only** be :ref:`run_with_docker`.

Pre-installation Checklist
^^^^^^^^^^^^^^^^^^^^^^^^^^

Before you install ScanCode.io, make sure you have the following prerequisites:

 * **Python: versions 3.8 to 3.11** found at https://www.python.org/downloads/
 * **Git**: most recent release available at https://git-scm.com/
 * **PostgreSQL**: release 11 or later found at https://www.postgresql.org/ or
   https://postgresapp.com/ on macOS

.. _system_dependencies:

System Dependencies
^^^^^^^^^^^^^^^^^^^

In addition to the above pre-installation checklist, there might be some OS-specific
system packages that need to be installed before installing ScanCode.io.

On **Linux**, several **system packages are required** by the ScanCode toolkit.
Make sure those are installed before attempting the ScanCode.io installation::

    sudo apt-get install \
        build-essential python3-dev libssl-dev libpq-dev \
        bzip2 xz-utils zlib1g libxml2-dev libxslt1-dev libpopt0 \
        libgpgme11 libdevmapper1.02.1 libguestfs-tools

See also `ScanCode-toolkit Prerequisites <https://scancode-toolkit.readthedocs.io/en/
latest/getting-started/install.html#prerequisites>`_ for more details.

Clone and Configure
^^^^^^^^^^^^^^^^^^^

 * Clone the `ScanCode.io GitHub repository <https://github.com/nexB/scancode.io>`_::

    git clone https://github.com/nexB/scancode.io.git && cd scancode.io

 * Inside the :guilabel:`scancode.io/` directory, install the required dependencies::

    make dev

 .. note::
    You can specify the Python version during the ``make dev`` step using the following
    command::

        make dev PYTHON_EXE=python3.11

    When ``PYTHON_EXE`` is not specified, by default, the ``python3`` executable is
    used.

 * Create an environment file::

    make envfile

Database
^^^^^^^^

**PostgreSQL** is the preferred database backend and should always be used on
production servers.

* Create the PostgreSQL user, database, and table with::

    make postgresdb

.. warning::
    The ``make postgres`` command is assuming that your PostgreSQL database template is
    using the ``en_US.UTF-8`` collation.
    If you encounter database creation errors while running this command, it is
    generally related to an incompatible database template.

    You can either `update your template <https://stackoverflow.com/a/60396581/8254946>`_
    to fit the ScanCode.io default, or provide custom values collation using the
    ``POSTGRES_INITDB_ARGS`` variable such as::

        make postgresdb POSTGRES_INITDB_ARGS=\
            --encoding=UTF-8 --lc-collate=en_US.UTF-8 --lc-ctype=en_US.UTF-8

.. note::
    You can also use a **SQLite** database for local development as a single user
    with::

        make sqlitedb

.. warning::
    Choosing SQLite over PostgreSQL has some caveats. Check this `link
    <https://docs.djangoproject.com/en/dev/ref/databases/#sqlite-notes>`_
    for more details.

Tests
^^^^^

You can validate your ScanCode.io installation by running the tests suite::

    make test

Web Application
^^^^^^^^^^^^^^^

A web application is available to create and manage your projects from a browser;
you can start the local webserver and access the app with::

    make run

Then open your web browser and visit: http://localhost:8001/ to access the web
application.

.. warning::
    ``make run`` is provided as a simplified way to run the application with one
    **major caveat**: pipeline runs will be **executed synchronously** on HTTP requests
    and will leave your browser connection or API calls opened during the pipeline
    execution. See also the :ref:`scancodeio_settings_async` setting.

.. warning::
    This setup is **not suitable for deployments** and **only supported for local
    development**.
    It is highly recommended to use the :ref:`run_with_docker` setup to ensure the
    availability of all the features and the benefits from asynchronous workers
    for pipeline executions.

An overview of the web application usage is available at :ref:`user_interface`.

Upgrading
^^^^^^^^^

If you already have the ScanCode.io repo cloned, you can upgrade to the latest version
with::

    cd scancode.io
    git pull
    make dev
    make migrate

Helm Chart [Beta]
-----------------

.. warning::
    The Helm Chart support for ScanCode.io is a community contribution effort.
    It is only tested on a few configurations and still under development.
    We welcome improvement suggestions and issue reports at
    `ScanCode.io GitHub repo <https://github.com/nexB/scancode.io/issues>`_.

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
    # postgresql      11.x.x  https://charts.bitnami.com/bitnami      ok
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
    The Gitpod support for ScanCode.io is a community contribution effort.
    We welcome improvement suggestions and issue reports at
    `ScanCode.io GitHub repo <https://github.com/nexB/scancode.io/issues>`_.

Installation
^^^^^^^^^^^^

* Create a new Workspace and open it in VSCode Browser or your preferred IDE.
  Provide the ScanCode.io GitHub repo URL: https://github.com/nexB/scancode.io

* Open the "TERMINAL" window and create the ``.env`` file with::

    make envfile

* Open the generated ``.env`` file and add the following settings::

    ALLOWED_HOSTS=.gitpod.io
    CSRF_TRUSTED_ORIGINS=https://*.gitpod.io

Run the App
^^^^^^^^^^^

* Build and run the app container::

    docker compose build
    docker compose up

At this stage, the ScanCode.io app is up and running.
To access the app, open the "PORTS" window and open the address for port 80 in your
browser.
