.. _installation:

Installation
============

Pre-requisite
-------------

 * **Debian-like** distro or **macOS**
 * Latest version of **Python 3.6**: https://www.python.org/downloads/
 * **PostgreSQL** 10 or later: https://www.postgresql.org/ (or https://postgresapp.com/ on macOS)
 * Recent version of **git**: https://git-scm.com/

Local installation
------------------

Clone the git `ScanCode.io repo <https://github.com/nexB/scancode.io>`_,
install dependencies, and prepare the database::

    git clone git@github.com:nexB/scancode.io.git && cd scancode.io
    make dev
    make envfile
    make cleandb

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
