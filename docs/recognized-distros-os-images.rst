.. _recognized-distros-os-images:

Recognized Distros, OS, and Images
==================================

TODO:

1. a high level summary of recognized technology combinations some of which may be only
for some pipelines.
This should cover not only OS but also later the set of programming languages and
application package managers that we support

2. at a lower level, we need to get more detailed information about the specifics of
how a technology is recognized: for instance, for Debian, we collect installed packages,
and for each package we collect installed files; we detect licenses in .., etc.

Recognized Operating Systems
----------------------------

- Debian-based Linux distros: Debian, Ubuntu and Debian-derivative
- Alpine
- RPM-based Linux distros RHEL, Fedora, openSUSE/SUSE
- Distroless (Docker images only): partial support, work in progress.
  System packages do not have installed files details.
- Windows: work in progress for Docker images only.
- Yocto, OpenWRT: work in progress
- There is work in progress to improve the quality of license detection for Debian.

For each recognized OS we collect in general this information:

- OS and image details
- Installed system packages and their files
- Installed application packages and their files
- Details for files not part of a package
