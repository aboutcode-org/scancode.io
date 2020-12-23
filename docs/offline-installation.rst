.. _offline_installation:

Offline packaging and installation
==================================

Offline Installation
--------------------

Create the installable archive::

   make package

Grab the installable archive in ``dist/scancodeio-1.0.6.tar.gz``
and move that file to you offline install server.

On the offline install server:

 1. extract the ScanCode.io code
 2. install dependencies
 3. prepare the database

::

   tar -xf scancodeio-1.0.6.tar.gz && cd scancode.io
   make install
   make envfile
   make postgres

Offline Upgrade
---------------

Upgrade your local checkout of the ScanCode.io repo::

    cd scancode.io && git pull

Create the latest installable archive::

   make package

Grab the installable archive in ``dist/scancodeio-1.0.6.tar.gz``
and move that to you offline install server.

On the offline install server:

 1. backup the previous ScanCode.io code
 2. extract the new ScanCode.io code
 3. install dependencies
 4. migrate the database

::

    mv scancode.io scancode.io-$(date +"%Y-%m-%d_%H%M")
    tar -xf scancodeio-1.0.6.tar.gz && cd scancode.io
    make install
    make migrate
