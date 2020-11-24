.. _docker_image:

Docker image
============

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

    git clone git@github.com:nexB/scancode.io.git && cd scancode.io
    make envfile
    docker-compose build


.. note::
    The image will need to be re-build when the ScanCode.io app source code if
    modified or updated.

Run the Image
-------------

Run your image as a container::

    docker-compose up


At this point, the ScanCode.io app should be running at port 8000 on your
Docker host.
Go to http://localhost:8000 on a web browser to access the web UI.

You can also run a one-off ``scanpipe`` command through the Docker command line
interface, for example::

    docker-compose run web scanpipe create-project project_name


.. note::
    Refer to :ref:`scanpipe_command_line` for the full list of commands.

Alternatively, you can connect to the Docker container ``bash`` and run commands
from there::

    docker-compose run web bash
    scanpipe create-project project_name
