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
BIN_LOCATION=${INSTALL_LOCATION}/bin
ENV_FILE=${INSTALL_LOCATION}/.env
DOCKER_COMPOSE_URL="https://raw.githubusercontent.com/nexB/scancode.io/install-sh/docker-compose.latest.yml"
DOCKER_ENV_URL="https://raw.githubusercontent.com/nexB/scancode.io/install-sh/docker.env"
DOCKER_COMPOSE_FILE=${INSTALL_LOCATION}/docker-compose.yml
DOCKER_ENV_FILE=${INSTALL_LOCATION}/docker.env
DOCKER_COMPOSE="docker compose -f ${DOCKER_COMPOSE_FILE}"
DOCKER_VOLUMES="--volume ${INSTALL_LOCATION}:/var/scancodeio/workspace/"
#SCANPIPE_CMD="${DOCKER_COMPOSE} run ${DOCKER_VOLUMES} --rm web scanpipe"
# TODO: Mounting volume raise Permission denied on Ubuntu
SCANPIPE_CMD="${DOCKER_COMPOSE} run --rm web scanpipe"
SCANPIPE_BIN_FILE=${INSTALL_LOCATION}/bin/scanpipe

success() {
  printf "\033[1;32m%s\033[0m\n" "$1"
}

info() {
  printf "\033[1m-> %s\033[0m\n" "$1"
}

info "Install ScanCode.io at ${INSTALL_LOCATION}"
mkdir -p ${INSTALL_LOCATION}
mkdir -p ${BIN_LOCATION}

# Generate the environment file
if [ ! -f "${ENV_FILE}" ]; then
    info "Create the .env file and generate a secret key"
    touch ${ENV_FILE}
    echo SECRET_KEY=\"TODO\" > ${ENV_FILE}
fi

info "Fetch the docker-compose.yml and docker.env files"
curl --silent --output ${DOCKER_COMPOSE_FILE} ${DOCKER_COMPOSE_URL}
curl --silent --output ${DOCKER_ENV_FILE} ${DOCKER_ENV_URL}

if [ ! -f "${SCANPIPE_BIN_FILE}" ]; then
    echo "Create the scanpipe executable in local bin/"
    touch ${SCANPIPE_BIN_FILE}
    chmod a+x ${SCANPIPE_BIN_FILE}
    echo "#!/bin/bash" > ${SCANPIPE_BIN_FILE}
    echo "${SCANPIPE_CMD} \$@" >> ${SCANPIPE_BIN_FILE}
fi

info "Prepare the database"
${SCANPIPE_CMD} migrate

success "Installation completed."
success "You can run the scanpipe commands using: ${SCANPIPE_BIN_FILE} [COMMAND]"

# TODO (requires sudo): sudo ln -sf ${SCANPIPE_BIN_FILE} /usr/local/bin/scanpipe
# Alternatively, set the $BIN_LOCATION in $PATH with:
# echo "export PATH=\"${BIN_LOCATION}:\$PATH\""

# To stop all related services:
# docker compose -f ${HOME}/.scancodeio/docker-compose.yml stop
