#!/bin/bash
#
# Copyright (c) nexB Inc. and others. All rights reserved.
# DejaCode is a trademark of nexB Inc.
# SPDX-License-Identifier: AGPL-3.0-only
# See https://github.com/nexB/dejacode for support or download.
# See https://aboutcode.org for more information about AboutCode FOSS projects.
#

# Usage:
# /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/nexB/scancode.io/install-sh/etc/install.sh)"

INSTALL_LOCATION=${HOME}/.scancodeio
ENV_FILE=${INSTALL_LOCATION}/.env
DOCKER_COMPOSE_URL="https://raw.githubusercontent.com/nexB/scancode.io/install-sh/docker-compose.latest.yml"
DOCKER_ENV_URL="https://raw.githubusercontent.com/nexB/scancode.io/install-sh/docker.env"
DOCKER_COMPOSE_FILE=${INSTALL_LOCATION}/docker-compose.yml
DOCKER_ENV_FILE=${INSTALL_LOCATION}/docker.env
DOCKER_COMPOSE="docker compose -f ${DOCKER_COMPOSE_FILE}"
DOCKER_VOLUMES="--volume ${INSTALL_LOCATION}:/var/scancodeio/workspace/"
SCANPIPE_CMD="${DOCKER_COMPOSE} run ${DOCKER_VOLUMES} --rm web scanpipe"

# Create the ~/.scancodeio directory in home
mkdir -p ${INSTALL_LOCATION}

# Generate the environment file
if [ ! -f "${ENV_FILE}" ]; then
    echo "-> Create the .env file and generate a secret key"
    touch ${ENV_FILE}
    echo SECRET_KEY=\"TODO\" > ${ENV_FILE}
fi

# Fetch the docker-compose.yml and docker.env files
curl --output ${DOCKER_COMPOSE_FILE} ${DOCKER_COMPOSE_URL}
curl --output ${DOCKER_ENV_FILE} ${DOCKER_ENV_URL}

# Run a test command
${SCANPIPE_CMD} create-project test_project

#${SCANPIPE_CMD} create-project ackage-url \
#    --input-url https://github.com/package-url/packageurl-js/archive/refs/tags/v1.2.1.zip \
#    --pipeline scan_codebase \
#    --execute
#${SCANPIPE_CMD} shell

echo "Installation completed!"
