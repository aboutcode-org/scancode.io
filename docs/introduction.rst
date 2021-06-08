.. _introduction:

ScanCode.io Overview
====================

**ScanCode.io** is a server to script and automate the process of
**Software Composition Analysis (SCA)** to identify any open source components
and their license compliance data in an application’s codebase. ScanCode.io can be
used for various use cases, such as Docker container and VM composition
analyses, among other applications.

Why ScanCode.io?
----------------

Modern software is built from many open source packages assembled with new code.
Knowing which free and open source code package is in use matters because:

- You're required to know the license of third-party code before using it, **and**
- You want to avoid using buggy, outdated or vulnerable components.

It's usually convenient to include and reuse new code downloaded from the
internet; however, it's often surprisingly hard to get a proper inventory of
all third-party code origins and licenses used in a software project.
There are some great tools available to scan your code and help uncover these
details. For example, when you reuse only a few FOSS components in a single
project, running one of these tools, such as the **ScanCode-toolkit**, manually
along with a spreadsheet might be enough to manage your software composition
analysis.

However, when you scale up, running automated and reproducible analysis pipelines
that are adapted to a software project's unique context and technology platform
can be difficult. This will require deploying and running multiple specialized
tools and merge their results with a consistent workflow. Moreover,
when reusing thousands of open source packages is becoming commonplace,
code scans pipelines need to be scripted as code and running on servers backed
by a shared database, not on a laptop.

For instance, when you analyze Docker container images, there could be hundreds
to thousands of system packages, such as Debian, RPM, Alpine, and application
packages, including npm, PyPI, Rubygems, Maven, installed in an image
side-by-side with your own code. Taking care of all these can be
an extremely hard task, and that's when **ScanCode.io** comes into play to help
organizing these complex code analysis as scripted pipelines and store their
results in a uniform database for automated code analysis.


What is ScanPipe?
-----------------

**ScanPipe** is a developer-friendly framework and application that helps
software analysts and engineers build and manage real-life software composition
analysis projects as scripted pipelines.

ScanPipe was originally developed using
`Django <https://www.djangoproject.com/>`_,
`ScanCode Toolkit <https://github.com/nexB/scancode-toolkit>`_,
and `Metaflow <https://metaflow.org/>`_
to help boost the productivity of code analysts who work on a wide variety of
software composition analysis projects.

**ScanPipe** provides a unified framework to the infrastructure that is
required to execute and organize these software composition analysis projects.


Should I use ScanPipe?
----------------------

If you are working on a software composition analysis project, or you
are planning to start a new one, consider the following questions:

1. **Automation**: Is the project part of a larger compliance program
   (as opposed to a one-of) and that you require automation?
2. **Complexity**: Does the project use many third-party components or technologies?
3. **Reproducibility**: Is it important that the results are reproducible, traceable, and auditable?

If you answered "yes" to any of the above, keep reading - ScanPipe can help you.
If the answer is "no" to all of the above, which is a valid scenario, e.g., when you
are doing small-scale analysis, ScanPipe may provide only limited benefit for you.

The first set of available pipelines helps automate the analysis of Docker
container images and virtual machine (VM) disk images that often harbor
comprehensive software stacks from an operating system with its kernel through
system and application packages to original and custom applications.

.. Some of this documentation is borrowed from the metaflow documentation and is also under
   Apache-2.0
.. Copyright (c) Netflix
