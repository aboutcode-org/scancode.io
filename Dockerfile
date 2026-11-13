# SPDX-License-Identifier: Apache-2.0
#
# http://nexb.com and https://github.com/aboutcode-org/scancode.io
# The ScanCode.io software is licensed under the Apache License version 2.0.
# Data generated with ScanCode.io is provided as-is without warranties.
# ScanCode is a trademark of nexB Inc.
#
# You may not use this software except in compliance with the License.
# You may obtain a copy of the License at: http://apache.org/licenses/LICENSE-2.0
# Unless required by applicable law or agreed to in writing, software distributed
# under the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR
# CONDITIONS OF ANY KIND, either express or implied. See the License for the
# specific language governing permissions and limitations under the License.
#
# Data Generated with ScanCode.io is provided on an "AS IS" BASIS, WITHOUT WARRANTIES
# OR CONDITIONS OF ANY KIND, either express or implied. No content created from
# ScanCode.io should be considered or used as legal advice. Consult an Attorney
# for any legal advice.
#
# ScanCode.io is a free software code scanning tool from nexB Inc. and others.
# Visit https://github.com/aboutcode-org/scancode.io for support and download.

# ======================================================================================
# Stage app-core: app code and Python dependencies
# ======================================================================================

FROM ghcr.io/astral-sh/uv:0.13.7-python3.14-trixie-slim AS app-core

# Compile bytecode for faster startup
ENV UV_COMPILE_BYTECODE=1
# Copy files instead of linking (cache and target are on different filesystems)
ENV UV_LINK_MODE=copy
# Skip dev dependencies
ENV UV_NO_DEV=1
# Use the system Python, don't download one
ENV UV_PYTHON_DOWNLOADS=0
# Set uv cache directory for BuildKit cache mounts
ENV UV_CACHE_DIR=/root/.cache/uv

ENV APP_NAME=scancodeio
ENV APP_DIR=/opt/$APP_NAME
WORKDIR $APP_DIR

# Only re-runs when uv.lock changes
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --frozen --no-install-project

# Only re-runs when local code changes
COPY . $APP_DIR
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen

# ======================================================================================
# Stage app-full: app-core with the android_analysis extra
# ======================================================================================

FROM app-core AS app-full

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --extra android_analysis

# ======================================================================================
# Stage jadx: jadx, independent of the app code to stay cached
# ======================================================================================

FROM python:3.14-slim-trixie AS jadx

ARG JADX_VERSION=1.5.6
ARG JADX_SHA256=545ea2be9c242511bc145755cf4bda2485ade42966e096f8b4d3da2a230e8974
ADD --checksum=sha256:${JADX_SHA256} \
    https://github.com/skylot/jadx/releases/download/v${JADX_VERSION}/jadx-${JADX_VERSION}.zip \
    /tmp/jadx.zip
# zipfile does not keep the executable permission
RUN python3 -m zipfile --extract /tmp/jadx.zip /opt/jadx \
 && chmod +x /opt/jadx/bin/jadx

# ======================================================================================
# Stage base: runtime system packages and app user, shared by core and full
# ======================================================================================

FROM python:3.14-slim-trixie AS base

LABEL org.opencontainers.image.source="https://github.com/aboutcode-org/scancode.io"
LABEL org.opencontainers.image.description="ScanCode.io"
LABEL org.opencontainers.image.licenses="Apache-2.0"

# Set default values for APP_UID and APP_GID at build-time
ARG APP_UID=1000
ARG APP_GID=1000

ENV APP_NAME=scancodeio
ENV APP_USER=app
ENV APP_DIR=/opt/$APP_NAME

# Force Python unbuffered stdout and stderr (they are flushed to terminal immediately)
ENV PYTHONUNBUFFERED=1
# Do not write Python .pyc files
ENV PYTHONDONTWRITEBYTECODE=1
# Add the app dir in the Python path for entry points availability
ENV PYTHONPATH=$APP_DIR
# Use the libmagic bundled with typecode: two libmagic providers are installed, and
# the one used otherwise depends on the order the packages are discovered in.
ENV TYPECODE_LIBMAGIC_PATH=$APP_DIR/.venv/lib/python3.14/site-packages/typecode_libmagic/lib/libmagic.so
ENV TYPECODE_LIBMAGIC_DB_PATH=$APP_DIR/.venv/lib/python3.14/site-packages/typecode_libmagic/data/magic.mgc

# OS requirements as per
# https://scancode-toolkit.readthedocs.io/en/stable/getting-started/installation/index.html#installation-prerequisites
# Also install universal-ctags and xgettext for symbol and string collection.
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
       bzip2 \
       xz-utils \
       zlib1g \
       libxml2 \
       libxslt1.1 \
       libgomp1 \
       libsqlite3-0 \
       libgcrypt20 \
       libpopt0 \
       libzstd1 \
       libgpgme11t64 \
       libdevmapper1.02.1 \
       libmagic1t64 \
       git \
       wait-for-it \
       universal-ctags \
       gettext \
 && apt-get clean \
 && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# Create the APP_USER group, user, and directory with specific UID and GID
RUN groupadd --gid $APP_GID --system $APP_USER \
 && useradd --uid $APP_UID --gid $APP_GID --home-dir $APP_DIR --system --create-home $APP_USER \
 && chown $APP_USER:$APP_USER $APP_DIR \
 && mkdir -p /var/$APP_NAME \
 && chown $APP_USER:$APP_USER /var/$APP_NAME

# Place executables in the environment at the front of the path
ENV PATH="$APP_DIR/.venv/bin:$PATH"

# Setup the $APP_DIR as work directory and the user as APP_USER for the remaining stages
WORKDIR $APP_DIR
USER $APP_USER

# Create static/ and workspace/ directories
RUN mkdir -p /var/$APP_NAME/static/ /var/$APP_NAME/workspace/

# ======================================================================================
# Stage core: runtime image
# ======================================================================================

FROM base AS core

# Copy the application from app-core
COPY --from=app-core --chown=$APP_USER:$APP_USER $APP_DIR $APP_DIR

# ======================================================================================
# Stage full: core with VM inspection, Nix, and Android analysis tools
# ======================================================================================

FROM base AS full

USER root
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
       libguestfs-tools \
       linux-image-amd64 \
       openjdk-21-jre-headless \
       nix-bin \
       zstd \
 && apt-get clean \
 && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# Single-user Nix for the "scan_nix_package" pipeline: the store is owned by the
# app user, and the build sandbox is not available in an unprivileged container.
RUN mkdir --parents /nix/store /nix/var/nix /etc/nix \
 && chown --recursive $APP_USER:$APP_USER /nix \
 && printf 'sandbox = false\nbuild-users-group =\n' > /etc/nix/nix.conf

# jadx (runs on the OpenJDK above) decompiles the Android .dex files into Java
# sources for the "android_d2d" pipeline provided by android-inspector.
COPY --from=jadx /opt/jadx/ /usr/

USER $APP_USER

# Copied last, so a code change does not invalidate the system packages layers above.
# Starting from base instead of core keeps a single copy of the application.
COPY --from=app-full --chown=$APP_USER:$APP_USER $APP_DIR $APP_DIR
