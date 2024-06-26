.. _tutorial_cli_end_to_end_scanning_to_dejacode:

Analyze Codebase End to End with deplock and DejaCode (Command Line)
========================================================================

The focus of this tutorial is to guide you through scanning a codebase end to end, starting with the
dependency resolution, through the scanning proper, and finally the upload of the scan in DejaCode,
using deplock and ScanCode.io.

This is designed to run a faster, simple "inspect_packages" ScanCode.io pipeline.


.. note::
    This tutorial assumes you have Docker installed locally on your machine. and that you have
    access to a DejaCode installation with an API key. See the DejaCode installation guide to
    install DejaCode.


Requirements
------------

Before you follow the instructions in this tutorial, you need to:

- Have **Shell access** on the machine where docker is installed.
- Have the API URL and API key for your DejaCode instance.


Docker Engine installation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The ScanCode app container requires the Docker engine for running scans.
If you haven't already, install Docker on your machine by referring
to the <official Docker documentation>(https://docs.docker.com/get-docker/_ and
following the installation instructions.


.. note::
    These instructions have been tested on Linux for now.



Outline of the processing steps
----------------------------------------

The process for this tutorial is to:

1. Fetch the codebase to scan
2. Ensure that it contains a proper scancode-config.yml file with references to a DejaCode
   product and version for this codebase
3. Download and run the latest deplock for each ecosystem of this codebase
4. Run ScanCode.io and collect results
5. Upload thes scans results to DejaCode for the product of this codebase



Fetch codebase to scan
--------------------------------------


**Local Project Codebase**: Ensure you have a local checkout of your project's  codebase.

We are using this repo as a test:

TODO


Create scancode-config.yml config file
---------------------------------------

TODO do we need to create the product in DejaCode????
TODO add details


Download and run deplock
---------------------------------------

TODO

Run ScanCode Package Detection
--------------------------------------

Pull the latest ScanCode.io image::

    docker pull --quiet ghcr.io/nexb/scancode.io:latest


Execute the following command to run the ScanCode scanner on your project codebase::

    docker run --rm \
      -v "$(pwd)":/code \
      ghcr.io/nexb/scancode.io:latest \
      sh -c "run inspect_packages /code" \
      > results.json


Once completed, you will find the `results.json`
**results file in your current directory**.


Upload Scan Results in DejaCode
--------------------------------------

TODO

Trigger detailed Scan in DejaCode for all packages of the product
--------------------------------------------------------------------


Either using API or UI

