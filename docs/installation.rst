Installation
============

Pre-requisite
-------------

 * Debian-like distro or macOS
 * Latest version of Python 3.6: https://www.python.org/downloads/
 * PostgreSQL 10 or later: https://www.postgresql.org/ (or https://postgresapp.com/ on macOS)
 * Recent version of git: https://git-scm.com/

Development setup
-----------------

Clone the git ScanCode.io repo, install dependencies, and prepare the database::

    git clone git@github.com:nexB/scancode.io.git && cd scancode.io
    make dev
    make envfile
    make cleandb

Tests
-----

Validate the installation by running the tests suite::

    make test

Next Step
---------

- Getting started with Docker image analysis from the command line `scanpipe-tutorial-1.rst`.
