#
# Copyright (c) nexB Inc. and others. All rights reserved.
# ScanCode is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See https://github.com/nexB/scancode.io for support or download.
# See https://aboutcode.org for more information about AboutCode FOSS projects.
#

FROM --platform=linux/amd64 python:3.11-slim

LABEL org.opencontainers.image.source="https://github.com/nexB/scancode.io"
LABEL org.opencontainers.image.description="ScanCode.io"
LABEL org.opencontainers.image.licenses="Apache-2.0"

ENV APP_NAME scancodeio
ENV APP_USER app
ENV APP_DIR /opt/$APP_NAME
ENV VIRTUAL_ENV /opt/$APP_NAME/venv

# Force Python unbuffered stdout and stderr (they are flushed to terminal immediately)
ENV PYTHONUNBUFFERED 1
# Do not write Python .pyc files
ENV PYTHONDONTWRITEBYTECODE 1
# Add the app dir in the Python path for entry points availability
ENV PYTHONPATH $PYTHONPATH:$APP_DIR

# OS requirements as per
# https://scancode-toolkit.readthedocs.io/en/latest/getting-started/install.html
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
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
       libgpgme11 \
       libdevmapper1.02.1 \
       libguestfs-tools \
       linux-image-amd64 \
       git \
       wait-for-it \
 && apt-get clean \
 && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# Create the APP_USER group and user
RUN addgroup --system $APP_USER \
 && adduser --system --group --home=$APP_DIR $APP_USER \
 && chown $APP_USER:$APP_USER $APP_DIR

# Create the /var/APP_NAME directory with proper permission for APP_USER
RUN mkdir -p /var/$APP_NAME \
 && chown $APP_USER:$APP_USER /var/$APP_NAME

# Setup the work directory and the user as APP_USER for the remaining stages
WORKDIR $APP_DIR
USER $APP_USER

# Create the virtualenv
RUN python -m venv $VIRTUAL_ENV
# Enable the virtualenv, similar effect as "source activate"
ENV PATH $VIRTUAL_ENV/bin:$PATH

# Create static/ and workspace/ directories
RUN mkdir -p /var/$APP_NAME/static/ \
 && mkdir -p /var/$APP_NAME/workspace/

# Install the dependencies before the codebase COPY for proper Docker layer caching
COPY --chown=$APP_USER:$APP_USER setup.cfg setup.py $APP_DIR/
RUN pip install --no-cache-dir .

# Copy the codebase and set the proper permissions for the APP_USER
COPY --chown=$APP_USER:$APP_USER . $APP_DIR
