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

# ===================================================================
# Stage 1: Build stage
# ===================================================================

FROM ghcr.io/astral-sh/uv:0.13.0-python3.14-trixie-slim AS builder

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

# ===================================================================
# Stage 1.5: Build stage for full image
# ===================================================================

FROM builder AS builder-full

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --extra android_analysis

# ===================================================================
# Stage 2: Production stage (core)
# ===================================================================

FROM python:3.14-slim-trixie AS core

LABEL org.opencontainers.image.source="https://github.com/aboutcode-org/scancode.io"
LABEL org.opencontainers.image.description="ScanCode.io"
LABEL org.opencontainers.image.licenses="Apache-2.0"

# Set default values for APP_UID and APP_GID at build-time
ARG APP_UID=1000
ARG APP_GID=1000

# Docker CLI version installed client-only
# When updating DOCKER_CLI_VERSION, recompute both SHA256 values from
# https://download.docker.com/linux/static/stable/<arch>/docker-<version>.tgz
ARG DOCKER_CLI_VERSION=29.8.1
ARG DOCKER_CLI_SHA256_AMD64=d8db66739d2e28d4933786d73e918d9be643a67fbd835db1bf740d650a259e70
ARG DOCKER_CLI_SHA256_ARM64=667395fbffab52901b80181dfbb39ea76da2fbd7642c4fbddd24e42146b07b48

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
#
# NOTE: we do NOT install docker.io for Docker-in-Docker. It would pull the full Docker engine
# (dockerd, containerd, runc) into every ScanCode.io image, while only the
# CLI is used here.
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

# Install the Docker CLI (client-only) from the official static binaries.
# The version and per-architecture checksums are pinned. Update them
# together to upgrade.
RUN set -eux; \
    arch="$(dpkg --print-architecture)"; \
    case "$arch" in \
        amd64) docker_arch="x86_64"; expected_sha256="${DOCKER_CLI_SHA256_AMD64}" ;; \
        arm64) docker_arch="aarch64"; expected_sha256="${DOCKER_CLI_SHA256_ARM64}" ;; \
        *) echo "Unsupported architecture: $arch" >&2; exit 1 ;; \
    esac; \
    python3 -c "import urllib.request; \
        urllib.request.urlretrieve( \
            'https://download.docker.com/linux/static/stable/${docker_arch}/docker-${DOCKER_CLI_VERSION}.tgz', \
            '/tmp/docker.tgz')"; \
    echo "${expected_sha256}  /tmp/docker.tgz" | sha256sum -c -; \
    tar -xzf /tmp/docker.tgz \
        --strip-components=1 \
        -C /usr/local/bin \
        docker/docker; \
    rm /tmp/docker.tgz; \
    docker --version

# Create the APP_USER group, user, and directory with specific UID and GID
RUN groupadd --gid $APP_GID --system $APP_USER \
 && useradd --uid $APP_UID --gid $APP_GID --home-dir $APP_DIR --system --create-home $APP_USER \
 && chown $APP_USER:$APP_USER $APP_DIR \
 && mkdir -p /var/$APP_NAME \
 && chown $APP_USER:$APP_USER /var/$APP_NAME

# Copy the application from the builder
COPY --from=builder --chown=$APP_USER:$APP_USER $APP_DIR $APP_DIR

# Place executables in the environment at the front of the path
ENV PATH="$APP_DIR/.venv/bin:$PATH"

# Setup the $APP_DIR as work directory and the user as APP_USER for the remaining stages
WORKDIR $APP_DIR
USER $APP_USER

# Create static/ and workspace/ directories
RUN mkdir -p /var/$APP_NAME/static/ /var/$APP_NAME/workspace/

# ===================================================================
# Stage 3: Full image (with VM inspection and Android inspector)
# ===================================================================

FROM core AS full

COPY --from=builder-full --chown=$APP_USER:$APP_USER $APP_DIR $APP_DIR

USER root
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
       libguestfs-tools \
       linux-image-amd64 \
       openjdk-21-jre-headless \
 && apt-get clean \
 && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# jadx (runs on the OpenJDK above) decompiles the Android .dex files into Java
# sources for the "android_d2d" pipeline provided by android-inspector.
ARG JADX_VERSION=1.5.6
ARG JADX_SHA256=545ea2be9c242511bc145755cf4bda2485ade42966e096f8b4d3da2a230e8974
RUN python3 -c "import hashlib, io, sys, urllib.request, zipfile; \
    archive = urllib.request.urlopen( \
    'https://github.com/skylot/jadx/releases/download/v${JADX_VERSION}/jadx-${JADX_VERSION}.zip' \
    ).read(); \
    hashlib.sha256(archive).hexdigest() == '${JADX_SHA256}' or sys.exit('jadx checksum mismatch'); \
    zipfile.ZipFile(io.BytesIO(archive)).extractall('/usr/')" \
 && chmod +x /usr/bin/jadx

USER $APP_USER
