Offline packaging and installation
==================================

Create the installable archive::

   make package

Grab the installable archive in dist/scancodeio-1.0.1.tar.gz
and move that to you offline install server.

On the offline install server:

 1. extract the ScanCode.io code,
 2. install dependencies
 3. prepare the database

::

   tar -xf scancodeio-1.0.1.tar.gz && cd scancode.io
   make install
   make envfile
   make cleandb

Finally set the workspace location in your local environment::

    export SCANCODEIO_WORKSPACE_LOCATION=/path/to/scancodeio/workspace/
    mkdir -p $SCANCODEIO_WORKSPACE_LOCATION

Offline upgrade
---------------

Upgrade your local checkout of the ScanCode.io repo::

    cd scancode.io && git checkout develop && git pull

Create the latest installable archive::

   make package

Grab the installable archive in dist/scancodeio-1.0.1.tar.gz
and move that to you offline install server.

On the offline install server:

 1. backup the previous ScanCode.io code
 2. extract the new ScanCode.io code
 3. install dependencies
 4. migrate the database

::

    mv scancode.io scancode.io-$(date +"%Y-%m-%d_%H%M")
    tar -xf scancodeio-1.0.1.tar.gz && cd scancode.io
    make install
    make migrate

Next Step
---------

- Getting started with Docker image analysis from the command line `scanpipe-tutorial-1.rst`.
