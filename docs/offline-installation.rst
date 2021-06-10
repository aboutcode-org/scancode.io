.. _offline_installation:

Offline packaging and installation
==================================

Offline Installation
--------------------

Create the installable archive::

   make package

Grab the installable archive in ``dist/scancodeio-21.6.10.tar.gz``
and move that file to your offline install server.

On the offline install server:

 1. Install system dependencies, see :ref:`system_dependencies`
 2. Extract the ScanCode.io code, install app dependencies, and prepare the database

::

   mkdir scancode.io  && tar -xf scancodeio-21.6.10.tar.gz -C scancode.io --strip-components 1
   cd scancode.io
   make install
   make envfile
   make postgres

Offline Upgrade
---------------

Upgrade your local checkout of the ScanCode.io repo::

    cd scancode.io && git pull

Create the latest installable archive::

   make package

Grab the installable archive in ``dist/scancodeio-21.6.10.tar.gz``
and move that to your offline install server.

On the offline install server:

 1. Backup the previous ScanCode.io code
 2. Extract the new ScanCode.io code
 3. Install app dependencies
 4. Migrate the database

::

    mv scancode.io scancode.io-$(date +"%Y-%m-%d_%H%M")
    mkdir scancode.io  && tar -xf scancodeio-21.6.10.tar.gz -C scancode.io --strip-components 1
    cd scancode.io
    make install
    make migrate
