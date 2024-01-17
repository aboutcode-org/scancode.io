.. _recognized_distros_os_images:

Recognized Distros, OS, and Images
==================================

Archives Formats
----------------

ScanCode.io recognizes and **can extract most archive formats**; however, it offers
special support for VM and container image formats:

- **Docker image tarbal** archives using a Docker image layout
- **Virtual machine images** using **QCOW** and **VHDI** image format

Operating Systems Detection
---------------------------

When scanning for Docker or virtual machine (VM) images, one of the first tasks
of a pipeline after extracting an archive is to **detect the operating system**.
For Linux, this also includes detecting the installed Linux distribution, which
checks for certain files such as ``/etc/os-release`` on Linux.
The detected OS—distro—is then used to determine **which system packages are
likely installed**, such as RPM or Debian packages.

For each recognized OS, a pipeline collects the following information:

- OS and image details
- Installed system packages metadata, license and their files
- Installed application packages metadata, license and their files
- Details for files not part of a package

Installed System Packages
-------------------------

ScanCode.io recognizes the following OS technology combinations; some of which
may be only used for certain pipelines:

- **Debian-based** Linux distros: Debian, Ubuntu and Debian-derivative
- **RPM-based** Linux distros: RHEL, Fedora, openSUSE/SUSE
- **Alpine** Linux distros

For the above three flavors, the
:ref:`analyze_docker_image <pipeline_analyze_docker_image>` and
:ref:`analyze_root_filesystem_or_vm_image <pipeline_analyze_root_filesystem>` pipelines
support comprehensive detection of installed system packages, their provenance,
their license metadata, and their installed files.

- For **Windows**, the :ref:`analyze_windows_docker_image <analyze_windows_docker_image>`
  pipeline supports Windows Docker images with extensive detection of installed Windows
  packages, programs, and the majority of installed files.

- **Distroless** Docker images system packages are detected with the
  :ref:`analyze_docker_image <pipeline_analyze_docker_image>` pipeline; package and
  license metadata are also detected.
  However, some work needs to be done to achieve comprehensive support and fix
  the issue of system packages ot tracking their installed files. Check `this
  open GitHub issue <https://github.com/GoogleContainerTools/distroless/issues/741>`_
  for more details.

- **Yocto** and **OpenWRT** Linux VM images are partially supported; adding more support
  is currently in progress.

- Other distros and OS will be scanned; however, we might not be able to detect
  system installed packages and may return a larger volume of file-level
  detections.
