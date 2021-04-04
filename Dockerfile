#
# Copyright (c) nexB Inc. and others. All rights reserved.
# ScanCode is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/nexB/scancode.io for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#

FROM python:3.9

# Requirements as per https://scancode-toolkit.readthedocs.io/en/latest/getting-started/install.html
RUN apt-get update \
 && apt-get install -y \
       bzip2 \
       xz-utils \
       zlib1g \
       libxml2-dev \
       libxslt1-dev \
       libgomp1 \
       libsqlite3-0 \
       libgcrypt20 \
       libpopt0 \
       libzstd1 \
 && apt-get clean \
 && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

ENV PYTHONUNBUFFERED 1
RUN mkdir /opt/scancodeio/
RUN mkdir -p /var/scancodeio/static/
RUN mkdir -p /var/scancodeio/workspace/
WORKDIR /opt/scancodeio/
COPY etc/requirements/base.txt /opt/scancodeio/
COPY . /opt/scancodeio/
RUN pip install -r base.txt . \
 && rm -rf /tmp/* /var/tmp/*
COPY rpm_inspector_rpm-4.16.1.3.210404-py3-none-manylinux1_x86_64.whl /opt/scancodeio/
RUN pip uninstall -y rpm_inspector_rpm \
 && pip install ./rpm_inspector_rpm-4.16.1.3.210404-py3-none-manylinux1_x86_64.whl

