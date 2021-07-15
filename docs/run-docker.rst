.. _run_docker:

Run with Docker
===============

Running ScanCode.io with Docker containers is the preferred setup and ensure that all
the features are available and working properly.

Get Docker
----------

The first step is to download and install Docker on your platform.
Refer to the following Docker documentation and choose the best installation
path for you: `Get Docker <https://docs.docker.com/get-docker/>`_

Build the Image
---------------

ScanCode.io is distributed with ``Dockerfile`` and ``docker-compose.yml`` files
required for the creation of the Docker image.

Clone the git `ScanCode.io repo <https://github.com/nexB/scancode.io>`_,
create an environment file, and build the Docker image::

    git clone https://github.com/nexB/scancode.io.git && cd scancode.io
    make envfile
    docker-compose build

.. note::
    The image will need to be re-build when the ScanCode.io app source code if
    modified or updated.

Run the Image
-------------

Run your image as a container::

    docker-compose up

At this point, the ScanCode.io app should be running at port 80 on your Docker host.
Go to http://localhost/ on a web browser to access the web UI.

.. warning::

    To access a dockerized ScanCode.io app from a remote location, the ``ALLOWED_HOSTS``
    setting need to be provided in your ``.env`` file::

        ALLOWED_HOSTS=.domain.com,127.0.0.1

    Refer to `Django ALLOWED_HOSTS settings <https://docs.djangoproject.com/en/dev/ref/settings/#allowed-hosts>`_
    for documentation.

You can also execute a one-off ``scanpipe`` command through the Docker command line
interface, for example::

    docker-compose run web ./manage.py create-project project_name

.. note::
    Refer to :ref:`scanpipe_command_line` for the full list of commands.

Alternatively, you can connect to the Docker container ``bash`` and run commands
from there::

    docker-compose run web bash
    ./manage.py create-project project_name

