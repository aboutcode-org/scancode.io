.. _recognized-distros-os-images:

Recognized Distros, OS, and Images
==================================

Archives formats
~~~~~~~~~~~~~~~~~

ScanCode.io can recognize and extracts most archive formats and has special
support for VM and container image formats:

- docker image tarbal archives using a Docker image layout and 
- virtual machine images using QCOW and VHDI image format


Operating systems detection
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

When scanning for Docker or virtual machine (VM) images, one of the first step
of a pipeline after archive etxraction is to detect the operating system. 
For Linux this means also detecting the installed Linux distribution. 
This detection looks for certain files such as the /etc/os-release file on Linux.
The detected OS or distro is then used to determine which system package types
are likely installed such as RPM or Debian packages.


For each recognized OS a pipeline collects in general this information:

- OS and image details
- Installed system packages metadata, license and their files
- Installed application packages metadata, license and their files
- Details for files not part of a package


Installed system packages
~~~~~~~~~~~~~~~~~~~~~~~~~~

ScanCode.io recognizes these OS technology combinations some of which may be only
used for certain pipelines:

- Debian-based Linux distros: Debian, Ubuntu and Debian-derivative.
- RPM-based Linux distros RHEL, Fedora, openSUSE/SUSE
- Alpine linux distro

For these three flavors, the docker and root_filesystem pipelines support
comprehensive detection of installed system packages, their provenance and
license metadata and their installed files.

- Windows: the docker_windows pipeline supports Windows Dcoker images with
  extensive detection of installed Windows packages and programs and most
  installed files.

- Distroless Docker images system package are detected with the docker
  pipeline and package and license metadata are detected.
  A pending issue is in the way of comprehensive support and system packages do not
  track their installed files details.: https://github.com/GoogleContainerTools/distroless/issues/741

- Yocto and OpenWRT Linux VM images support is partial and support addition is in progress.

- Other distros and OS will be scanned nbut we may not detect system installed
  packages and may return a larger volume of file-level detections.

