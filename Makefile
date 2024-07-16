# SPDX-License-Identifier: Apache-2.0
#
# http://nexb.com and https://github.com/nexB/scancode.io
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
# Visit https://github.com/nexB/scancode.io for support and download.

# Python version can be specified with `$ PYTHON_EXE=python3.x make conf`
PYTHON_EXE?=python3
MANAGE=bin/python manage.py
ACTIVATE?=. bin/activate;
VIRTUALENV_PYZ=etc/thirdparty/virtualenv.pyz
BLACK_ARGS=--exclude=".cache|migrations|data|lib|bin|var"
# Do not depend on Python to generate the SECRET_KEY
GET_SECRET_KEY=`head -c50 /dev/urandom | base64 | head -c50`
# Customize with `$ make envfile ENV_FILE=/etc/scancodeio/.env`
ENV_FILE=.env
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
	@${PYTHON_EXE} ${VIRTUALENV_PYZ} --never-download --no-periodic-update .

conf: virtualenv
	@echo "-> Install dependencies"
	@${ACTIVATE} pip install -e .

dev: virtualenv
	@echo "-> Configure and install development dependencies"
	@${ACTIVATE} pip install -e .[dev]

envfile:
	@echo "-> Create the .env file and generate a secret key"
	@if test -f ${ENV_FILE}; then echo ".env file exists already"; exit 1; fi
	@mkdir -p $(shell dirname ${ENV_FILE}) && touch ${ENV_FILE}
	@echo SECRET_KEY=\"${GET_SECRET_KEY}\" > ${ENV_FILE}

isort:
	@echo "-> Apply isort changes to ensure proper imports ordering"
	@${ACTIVATE} isort --profile black .

black:
	@echo "-> Apply black code formatter"
	@${ACTIVATE} black ${BLACK_ARGS} .

doc8:
	@echo "-> Run doc8 validation"
	@${ACTIVATE} doc8 --max-line-length 100 --ignore-path docs/_build/ --quiet docs/

valid: isort black doc8 check

bandit:
	@echo "-> Run source code security analyzer"
	@${ACTIVATE} bandit -r scanpipe scancodeio --quiet --exclude test_spdx.py

check: doc8 bandit
	@echo "-> Run flake8 (pycodestyle, pyflakes, mccabe) validation"
	@${ACTIVATE} flake8 .
	@echo "-> Run isort imports ordering validation"
	@${ACTIVATE} isort --profile black --check-only .
	@echo "-> Run black validation"
	@${ACTIVATE} black --check ${BLACK_ARGS} .
	@echo "-> Run docstring validation"
	@${ACTIVATE} pydocstyle scanpipe scancodeio

check-deploy:
	@echo "-> Check Django deployment settings"
	${MANAGE} check --deploy

clean:
	@echo "-> Clean the Python env"
	rm -rf bin/ lib/ lib64/ include/ build/ dist/ docs/_build/ .cache/ pip-selfcheck.json pyvenv.cfg
	find . -type f -name '*.py[co]' -delete -o -type d -name __pycache__ -delete -type d -name '*.egg-info' -delete

migrate:
	@echo "-> Apply database migrations"
	${MANAGE} migrate

upgrade:
	@echo "-> Upgrade local git checkout"
	@git pull
	@$(MAKE) migrate

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

run:
	${MANAGE} runserver 8001 --insecure

test:
	@echo "-> Run the test suite"
	${MANAGE} test --noinput

worker:
	${MANAGE} rqworker --worker-class scancodeio.worker.ScanCodeIOWorker --queue-class scancodeio.worker.ScanCodeIOQueue --verbosity 2

docs:
	rm -rf docs/_build/
	@${ACTIVATE} sphinx-build docs/ docs/_build/

bump:
	@echo "-> Bump the version"
	@${ACTIVATE} bumpver update --no-fetch --patch

docker-images:
	@echo "-> Build Docker services"
	docker compose build
	@echo "-> Pull service images"
	docker compose pull
	@echo "-> Save the service images to a tar archive in the build/ directory"
	@rm -rf build/
	@mkdir -p build/
	@docker save postgres redis scancodeio-worker scancodeio-web nginx | gzip > build/scancodeio-images.tar.gz

offline-package: docker-images
	@echo "-> Build package for offline installation in dist/"
	@cp -r etc docker-compose-offline.yml docker.env build/
	@mkdir -p dist/
	@tar -cf dist/scancodeio-offline-package-`git describe --tags`.tar build/

.PHONY: virtualenv conf dev envfile install check bandit valid isort check-deploy clean migrate upgrade postgresdb sqlitedb backupdb run test docs bump docker-images offline-package
