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

# ============================================
# Stage 1: Build stage
# ============================================

FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim AS builder

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

# ============================================
# Stage 2: Production stage
# ============================================

FROM python:3.13-slim-bookworm

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

# OS requirements as per
# https://scancode-toolkit.readthedocs.io/en/latest/getting-started/install.html
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
       libgpgme11 \
       libdevmapper1.02.1 \
       libguestfs-tools \
       linux-image-amd64 \
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

# Copy the application from the builder
COPY --from=builder --chown=$APP_USER:$APP_USER $APP_DIR $APP_DIR

# Place executables in the environment at the front of the path
ENV PATH="$APP_DIR/.venv/bin:$PATH"

# Setup the $APP_DIR as work directory and the user as APP_USER for the remaining stages
WORKDIR $APP_DIR
USER $APP_USER

# Create static/ and workspace/ directories
RUN mkdir -p /var/$APP_NAME/static/ /var/$APP_NAME/workspace/
