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

.. warning::
    On Linux, several OS packages are required by ScanCode toolkit.
    Make sure those are installed before attempting the ScanCode.io installation.
    Refer to `ScanCode-toolkit Prerequisites <https://scancode-toolkit.readthedocs.io/en/latest/getting-started/install.html#prerequisites>`_

.. note::
    ScanCode.io can also be run through a Docker image,
    refer to the :ref:`docker_image` chapter for details.

Local installation
------------------

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

----

You are now ready to move onto the **Tutorials**: :ref:`scanpipe_tutorial_1`.

Upgrading
---------

If you have already a clone of the ScanCode.io repo, you can upgrade to the
latest version with::

    cd scancode.io
    git pull
    make dev
    make migrate
