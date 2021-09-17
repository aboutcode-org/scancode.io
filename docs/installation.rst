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

**Clone the git** `ScanCode.io repo <https://github.com/nexB/scancode.io>`_,
create an **environment file**, and **build the Docker image**::

    git clone https://github.com/nexB/scancode.io.git && cd scancode.io
    make envfile
    docker-compose build

.. note::
    You need to rebuild the image whenever ScanCode.io's source code has been
    modified or updated.

Run the Image
^^^^^^^^^^^^^

**Run your image** as a container::

    docker-compose up

At this point, the ScanCode.io app should be running at port 80 on your Docker host.
Go to http://localhost/ on a web browser to **access the web UI**.

An overview of the web application usage is available at :ref:`user_interface`.

.. note::
    Congratulations, you are now ready to use ScanCode.io, and you can move onto the
    **Tutorials** section starting with the :ref:`tutorial_web_ui_analyze_docker_image`
    tutorial.

.. warning::

    To access a dockerized ScanCode.io app from a remote location, the ``ALLOWED_HOSTS``
    setting needs to be provided in your ``.env`` file::

        ALLOWED_HOSTS=.domain.com,127.0.0.1

    Refer to `Django ALLOWED_HOSTS settings <https://docs.djangoproject.com/
    en/dev/ref/settings/#allowed-hosts>`_ for more details.

Execute a Command
^^^^^^^^^^^^^^^^^

You can execute a one of ``scanpipe`` commands through the Docker command line
interface, for example::

    docker-compose run web ./manage.py create-project project_name

.. note::
    Refer to the :ref:`command_line_interface` section for the full list of commands.

Alternatively, you can connect to the Docker container ``bash`` and run commands
from there::

    docker-compose run web bash
    ./manage.py create-project project_name


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

 * **Python: versions 3.6 to 3.9** found at https://www.python.org/downloads/
 * **Git**: most recent release available at https://git-scm.com/
 * **PostgreSQL**: release 10 or later found at https://www.postgresql.org/ or
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

         make dev PYTHON_EXE=python3.6

    When ``PYTHON_EXE`` is not specified, by default, the ``python3`` executable is
    used.

 * Create an environment file::

    make envfile

Database
^^^^^^^^

**PostgreSQL** is the preferred database backend and should always be used on
production servers.

* Create the PostgreSQL user, database, and table with::

    make postgres

.. note::
    You can also use a **SQLite** database for local development as a single user
    with::

        make sqlite

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

Then open your web browser and visit: http://127.0.0.1:8001/ to access the web
application.

.. warning::
    ``make run`` is provided as a simplified way to run the application with one
    **major caveat**: pipeline runs will be **executed synchronously** on HTTP requests
    and will leave your browser connection or API calls opened during the pipeline
    execution.

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
