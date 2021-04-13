.. _installation:

Installation
============

Pre-requisite
-------------

 * **Debian-like** distro or **macOS**
 * **Python 3.6 to 3.9**: https://www.python.org/downloads/
 * Recent version of **git**: https://git-scm.com/

Optional:
 * **PostgreSQL 10** or later: https://www.postgresql.org/ (or https://postgresapp.com/ on macOS)

.. note::
    ScanCode.io can also be run through **Docker**, this is the preferred approach
    **on Windows**. Refer to the :ref:`docker_image` chapter for details.


Local installation
------------------

.. warning::
    On **Linux**, several **system packages are required** by ScanCode toolkit.
    Make sure those are installed before attempting the ScanCode.io installation::

        sudo apt-get install \
            build-essential python3-dev libssl-dev libpq-dev \
            bzip2 xz-utils zlib1g libxml2-dev libxslt1-dev libpopt0

    See also to `ScanCode-toolkit Prerequisites <https://scancode-toolkit.readthedocs.io/en/latest/getting-started/install.html#prerequisites>`_

Clone the git `ScanCode.io repo <https://github.com/nexB/scancode.io>`_,
install dependencies and create an environment file::

    git clone https://github.com/nexB/scancode.io.git && cd scancode.io
    make dev
    make envfile

.. note::
    The Python version can be specified using the following command during the
    ``make dev`` step::

        make dev PYTHON_EXE=python3.6

    When ``PYTHON_EXE`` is not specified, the default ``python3`` executable is used.


Database
--------

**PostgreSQL** is the preferred database backend and should always be used on
production servers.

Create the PostgreSQL user, database, and table with::

    make postgres

Alternatively, you can also decide to use a **SQLite** database for local
development as a single user::

    make sqlite

.. warning::
    Choosing SQLite over PostgreSQL has some caveats. See
    https://docs.djangoproject.com/en/dev/ref/databases/#sqlite-notes
    for details.


Tests
-----

Validate the installation by running the tests suite::

    make test


Web Application
---------------

A web application is available to create and manage your projects from a browser.
To start the local webserver and access the app::

    make run

Then open you web browser at visit: http://127.0.0.1:8001/

------------------

.. note::
    You are now ready to move onto the **Tutorials**: :ref:`scanpipe_tutorial_1`.


Upgrading
---------

If you have already a clone of the ScanCode.io repo, you can upgrade to the
latest version with::

    cd scancode.io
    git pull
    make dev
    make migrate
