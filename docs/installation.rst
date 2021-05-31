.. _installation:

Installation
============

Welcome to the **ScanCode.io** installation guide! This guide describes how to install ScanCode.io on various platforms.
Please read and follow the instructions carefully to ensure your installation is functional and smooth.

Supported Platforms
-------------------
**ScanCode.io** has been tested and is supported on the following operating systems:

    #. **Debian-based** Linux distributions
    #. **MacOS** 10.14 and up

In addition, ScanCode.io can also be run through **Docker**; this is the preferred approach **on Windows**. Refer to the :ref:`docker_image` chapter for details.


.. warning::
    ScanCode.io can **Only** be run on Windows through `Docker <https://www.docker.com/>`_ or `Virtual Machines <https://www.virtualbox.org/>`_. However, to avoid any installation issues, it is **Not recommended** to run ScanCode.io on Windows machines.

Pre-installation Checklist
--------------------------

Before you install ScanCode.io, make sure you have the following prerequisites:

 * **Python: versions 3.6 to 3.9** found at https://www.python.org/downloads/
 * **Git**: most recent release available at https://git-scm.com/
 * **PostgreSQL**: release 10 or later found at https://www.postgresql.org/ or https://postgresapp.com/ on macOS


Local Installation
------------------

The following installation instructions are mainly dedicated to Linux and Mac operating systems.

.. _system_dependencies:

Prerequisites
^^^^^^^^^^^^^
In addition to the above pre-installation checklist, there might be some OS-specific system packages that need to be installed before installing ScanCode.io.

* On **Linux**, several **system packages are required** by the ScanCode toolkit. Make sure those are installed before attempting the ScanCode.io installation::

        sudo apt-get install \
            build-essential python3-dev libssl-dev libpq-dev \
            bzip2 xz-utils zlib1g libxml2-dev libxslt1-dev libpopt0 \
            libgpgme11 libdevmapper1.02.1

See also `ScanCode-toolkit Prerequisites <https://scancode-toolkit.readthedocs.io/en/latest/getting-started/install.html#prerequisites>`_ for more details.

* Clone the `ScanCode.io GitHub repository <https://github.com/nexB/scancode.io>`_::

    git clone https://github.com/nexB/scancode.io.git && cd scancode.io

* Inside the scancode.io/ directory, install the required dependencies::

    make dev

.. note::
    You can specify the Python version during the
    ``make dev`` step using the following command::

        make dev PYTHON_EXE=python3.6

    When ``PYTHON_EXE`` is not specified, by default, the ``python3`` executable is used.

* Create an environment file::

    make envfile

Database
--------

**PostgreSQL** is the preferred database backend and should always be used on production servers.

* Create the PostgreSQL user, database, and table with::

    make postgres


.. note::
    You could also use a **SQLite** database for local development as a single user with::

     make sqlite

.. warning::
    Choosing SQLite over PostgreSQL has some caveats. Check this `link
    <https://docs.djangoproject.com/en/dev/ref/databases/#sqlite-notes>`_
    for more details.


Tests
-----

You can validate the ScanCode.io installation by running the tests suite::

    make test


Web Application
---------------

A web application is available to create and manage your projects from a browser; you can start the local webserver and access the app with::

    make run

Then open your web browser and visit: http://127.0.0.1:8001/ to access the web application.


.. note::
    Congratulations, you are now ready to use ScanCode.io, and you can move onto the **Tutorials** section starting with the :ref:`scanpipe_tutorial_1` tutorial.


Upgrading
---------

If you already have the ScanCode.io repo cloned, you can upgrade to the latest version with::

    cd scancode.io
    git pull
    make dev
    make migrate
