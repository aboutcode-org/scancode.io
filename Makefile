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

########################################################################################
# Docker dev commands
########################################################################################

IMAGE_NAME=scancodeio
COMPOSE=docker compose -f docker-compose.yml -f docker-compose.dev.yml
MANAGE=${COMPOSE} exec web ./manage.py
UV_DOCKER=docker run --rm \
	--user "$$(id -u):$$(id -g)" \
	--env UV_CACHE_DIR=/tmp/uv-cache \
	--volume "$(CURDIR)":/opt/scancodeio \
	--workdir /opt/scancodeio \
	ghcr.io/astral-sh/uv:0.13.4-python3.14-trixie-slim
# Do not depend on Python to generate the SECRET_KEY
GET_SECRET_KEY=`head -c50 /dev/urandom | base64 | head -c50`
# Customize with `$ make envfile ENV_FILE=/etc/scancodeio/.env`
ENV_FILE=.env

envfile:
	@echo "-> Create the .env file and generate a secret key"
	@if test -f ${ENV_FILE}; then echo ".env file exists already"; exit 1; fi
	@mkdir -p $(shell dirname ${ENV_FILE}) && touch ${ENV_FILE}
	@echo SECRET_KEY=\"${GET_SECRET_KEY}\" > ${ENV_FILE}

run:
	@echo "-> Run the Docker compose services in dev mode (hot reload on code changes)"
	${COMPOSE} up

run-dind:
	@echo "-> Run the Docker compose services with the dind profile (foreground)"
	${COMPOSE} --profile dind up

start:
	@echo "-> Start the Docker compose services in background"
	${COMPOSE} up -d

start-dind:
	@echo "-> Start the Docker compose services with the dind profile (background)"
	${COMPOSE} --profile dind up -d

stop:
	@echo "-> Stop the Docker compose services"
	${COMPOSE} stop

stop-dind:
	@echo "-> Stop the Docker compose services (dind profile)"
	${COMPOSE} --profile dind stop

bash:
	# Open a bash session in the running web container
	${COMPOSE} exec web bash

shell:
	# Open a bash session in a standalone container (no stack required)
	docker run -it $(IMAGE_NAME) bash

# make test              - full suite
# make test k=<pattern>  - filter by name, e.g. make test k=test_name
test:
	${MANAGE} test --noinput $(if $(k),-k $(k),)

fasttest:
	@echo "-> Run the test suite without the PipelinesIntegrationTest"
	${MANAGE} test --noinput --exclude-tag slow

migrations:
	@echo "-> Creates new database migrations"
	${MANAGE} makemigrations

migrate:
	@echo "-> Apply database migrations"
	${MANAGE} migrate

restart-worker:
	${COMPOSE} restart worker

build:
	# Build the dev Docker images (core, hot reload)
	${COMPOSE} build --pull

build-core:
	# Build the production core Docker image
	docker build --pull --target core -t $(IMAGE_NAME) .

build-full:
	# Build the production full Docker image
	docker build --pull --target full -t $(IMAGE_NAME):full .

regen-fixtures:
	@echo "-> Regenerate test fixtures from the running Docker stack"
	${COMPOSE} exec -e SCANCODEIO_TEST_FIXTURES_REGEN=1 web ./manage.py test

outdated:
	@echo "-> Check for outdated packages (with 3 days cooldown)"
	uv tree --outdated --exclude-newer "3 days"
	# Run `make start` first following any pyproject.toml changes
	${COMPOSE} exec web uv pip list --outdated --exclude-newer "3 days"
	@echo "-> Audit the project's dependencies for known vulnerabilities"
	uv audit

lock:
	@echo "-> Regenerate uv.lock from pyproject.toml in the uv image"
	${UV_DOCKER} uv lock

upgrade:
	@if [ -z "$(PACKAGE)" ]; then \
		echo "Usage: make upgrade PACKAGE=\"django==x.x.x idna==x.x\""; \
		exit 1; \
	fi
	@echo "-> Pin $(PACKAGE) in pyproject.toml"
	@for requirement in $(PACKAGE); do \
		NAME_PATTERN=$$(echo "$${requirement%%==*}" | sed 's/[-_.]/[-_.]/g') \
		VERSION=$${requirement##*==} \
		perl -pi -e 's/"($$ENV{NAME_PATTERN}(\[[^]]*\])?)==[^";]*/"$$1==$$ENV{VERSION}/i' pyproject.toml; \
	done
	@echo "-> Lock $(PACKAGE) in the uv image"
	${UV_DOCKER} uv lock $(addprefix --upgrade-package=,$(PACKAGE))

docker-images:
	@echo "-> Pull service images"
	DOCKER_DEFAULT_PLATFORM=linux/amd64 docker compose pull
	@echo "-> Save the service images to a tar archive in the build/ directory"
	@rm -rf build/
	@mkdir -p build/
	@docker save --platform linux/amd64 $$(docker compose config --images) | gzip > build/scancodeio-images.tar.gz

offline-package: docker-images
	@echo "-> Build package for offline installation in dist/"
	@cp -r etc docker-compose.yml docker.env build/
	@mkdir -p dist/
	@tar -cf dist/scancodeio-offline-package-`git describe --tags`.tar build/

########################################################################################
# Linters / docs
########################################################################################

doc8:
	@echo "-> Run doc8 validation"
	uvx doc8==2.0.0 --max-line-length 100 --ignore-path docs/_build/ --quiet docs/

fix:
	@echo "-> Run Ruff format"
	uvx ruff format
	@echo "-> Run Ruff linter"
	uvx ruff check --fix

valid: fix

check:
	@echo "-> Run Ruff linter validation (pycodestyle, bandit, isort, and more)"
	uvx ruff check
	@echo "-> Run Ruff format validation"
	uvx ruff format --check
	@$(MAKE) doc8
	@echo "-> Run ABOUT files validation"
	uvx --from aboutcode-toolkit --with setuptools about check --exclude .venv/ --exclude scanpipe/tests/ .

docs:
	rm -rf docs/_build/
	${COMPOSE} run --rm --no-deps --volume ./docs:/opt/scancodeio/docs \
		--volume ./CHANGELOG.rst:/opt/scancodeio/CHANGELOG.rst:ro web \
		sh -c "uv sync --frozen --extra dev --inexact && sphinx-build docs/ docs/_build/"

clean:
	@echo "-> Clean the Python env"
	rm -rf .venv/ .*cache/ *.egg-info/ build/ dist/
	find . -type f -name '*.py[co]' -delete -o -type d -name __pycache__ -delete

########################################################################################
# Local venv commands (legacy)
########################################################################################

# Python version can be specified with `$ PYTHON_EXE=python3.x make conf`
PYTHON_EXE?=python3
VENV_LOCATION=.venv
ACTIVATE?=. ${VENV_LOCATION}/bin/activate;
VENV_MANAGE=${VENV_LOCATION}/bin/python manage.py
VIRTUALENV_PYZ=etc/thirdparty/virtualenv.pyz
PIP_ARGS=--find-links=./etc/thirdparty/dummy_dist
# Customize with `$ make postgresdb SCANCODEIO_DB_PASSWORD=YOUR_PASSWORD`
SCANCODEIO_DB_NAME=scancodeio
SCANCODEIO_DB_USER=scancodeio
SCANCODEIO_DB_PASSWORD=scancodeio
POSTGRES_INITDB_ARGS=--encoding=UTF-8 --lc-collate=en_US.UTF-8 --lc-ctype=en_US.UTF-8
DATE=$(shell date +"%Y-%m-%d_%H%M")

# Use sudo for postgres, only on Linux
UNAME := $(shell uname)
ifeq ($(UNAME), Linux)
	SUDO_POSTGRES=sudo -u postgres
else
	SUDO_POSTGRES=
endif

virtualenv:
	@echo "-> Bootstrap the virtualenv with PYTHON_EXE=${PYTHON_EXE}"
	@${PYTHON_EXE} ${VIRTUALENV_PYZ} --never-download --no-periodic-update ${VENV_LOCATION}

conf: virtualenv
	@echo "-> Install dependencies"
	@${ACTIVATE} pip install ${PIP_ARGS} --editable .

dev: virtualenv
	@echo "-> Configure and install development dependencies"
	@${ACTIVATE} pip install ${PIP_ARGS} --editable .[dev]

dev-mining: virtualenv
	@echo "-> Configure and install development dependencies"
	@$(MAKE) dev
	@${ACTIVATE} pip install ${PIP_ARGS} --editable .[mining]

runserver:
	DJANGO_RUNSERVER_HIDE_WARNING=true ${VENV_MANAGE} runserver 8001 --insecure

check-deploy:
	@echo "-> Check Django deployment settings"
	${VENV_MANAGE} check --deploy

postgresdb:
	@echo "-> Configure PostgreSQL database"
	@echo "-> Create database user ${SCANCODEIO_DB_NAME}"
	@${SUDO_POSTGRES} createuser --no-createrole --no-superuser --login --inherit --createdb '${SCANCODEIO_DB_USER}' || true
	@${SUDO_POSTGRES} psql -c "alter user ${SCANCODEIO_DB_USER} with encrypted password '${SCANCODEIO_DB_PASSWORD}';" || true
	@echo "-> Drop ${SCANCODEIO_DB_NAME} database"
	@${SUDO_POSTGRES} dropdb ${SCANCODEIO_DB_NAME} || true
	@echo "-> Create ${SCANCODEIO_DB_NAME} database"
	@${SUDO_POSTGRES} createdb --owner=${SCANCODEIO_DB_USER} ${POSTGRES_INITDB_ARGS} ${SCANCODEIO_DB_NAME}
	@$(MAKE) migrate

backupdb:
	pg_dump -Fc ${SCANCODEIO_DB_NAME} > "${SCANCODEIO_DB_NAME}-db-${DATE}.dump"

sqlitedb:
	@echo "-> Configure SQLite database"
	@echo SCANCODEIO_DB_ENGINE=\"django.db.backends.sqlite3\" >> ${ENV_FILE}
	@echo SCANCODEIO_DB_NAME=\"sqlite3.db\" >> ${ENV_FILE}
	@$(MAKE) migrate

.PHONY: envfile run start stop bash shell test fasttest migrations migrate restart-worker build build-core build-full regen-fixtures outdated lock upgrade docker-images offline-package doc8 fix valid check docs virtualenv conf dev dev-mining runserver check-deploy clean postgresdb backupdb sqlitedb run-dind start-dind stop-dind
