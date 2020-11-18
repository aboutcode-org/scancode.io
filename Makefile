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

PYTHON_EXE=python3
MANAGE=bin/python manage.py
ACTIVATE=. bin/activate;
ANSIBLE_PLAYBOOK=cd etc/ansible/ && ansible-playbook --inventory-file=hosts --verbose --ask-become-pass --user=${USER}
BLACK_ARGS=--exclude="migrations|data|docs" .
GET_SECRET_KEY=`${PYTHON_EXE} -c "from django.core.management import utils; print(utils.get_random_secret_key())"`
# Customize with `$ make envfile ENV_FILE=/etc/scancodeio/.env`
ENV_FILE=.env
# Customize with `$ make cleandb SCANCODEIO_DB_PASSWORD=YOUR_PASSWORD`
SCANCODEIO_DB_PASSWORD=scancodeio

# Use sudo for postgres, but only on Linux
UNAME := $(shell uname)
ifeq ($(UNAME), Linux)
	SUDO_POSTGRES=sudo -u postgres
else
	SUDO_POSTGRES=
endif

conf:
	@echo "-> Configure the Python venv and install dependencies"
	${PYTHON_EXE} -m venv .
	@${ACTIVATE} pip install -r etc/requirements/base.txt
	@${ACTIVATE} pip install -e .

dev: conf
	@echo "-> Configure and install development dependencies"
	# Workaround https://github.com/python/typing/issues/573#issuecomment-405986724
	@${ACTIVATE} pip uninstall --yes typing
	@${ACTIVATE} pip install -r etc/requirements/dev.txt

envfile:
	@echo "-> Create the .env file and generate a secret key"
	@if test -f ${ENV_FILE}; then echo ".env file exists already"; exit 1; fi
	mkdir -p $(shell dirname ${ENV_FILE}) && touch ${ENV_FILE}
	@${ACTIVATE} echo SECRET_KEY=\"${GET_SECRET_KEY}\" > ${ENV_FILE}

install:
	@echo "-> Install and configure the Python env with base dependencies, offline"
	${PYTHON_EXE} -m venv .
	bin/pip install --upgrade --no-index --no-cache-dir --find-links=thirdparty -e .

check:
	@echo "-> Run pycodestyle (PEP8) validation"
	@${ACTIVATE} pycodestyle --max-line-length=88 --exclude=lib,thirdparty,docs,bin,migrations,settings,data,pipelines,var .
	@echo "-> Run isort imports ordering validation"
	@${ACTIVATE} isort --recursive --check-only .
	@echo "-> Run black validation"
	@${ACTIVATE} black --check ${BLACK_ARGS}

isort:
	@echo "-> Apply isort changes to ensure proper imports ordering"
	bin/isort --recursive --apply .

black:
	@echo "-> Apply black code formatter"
	bin/black ${BLACK_ARGS}

valid: isort black

clean:
	@echo "-> Cleaning the Python env"
	rm -rf bin/ lib/ lib64/ include/ build/ dist/ pip-selfcheck.json pyvenv.cfg scancodeio.egg-info
	find . -type f -name '*.py[co]' -delete -o -type d -name __pycache__ -delete

migrate:
	@echo "-> Applying migrations"
	${MANAGE} migrate

cleandb:
	@echo "-> Create database user 'scancodeio'"
	${SUDO_POSTGRES} createuser --no-createrole --no-superuser --login --inherit --createdb scancodeio || true
	${SUDO_POSTGRES} psql -c "alter user scancodeio with encrypted password '${SCANCODEIO_DB_PASSWORD}';" || true
	@echo "-> Dropping 'scancodeio' database"
	${SUDO_POSTGRES} dropdb scancodeio || true
	@echo "-> Creating 'scancodeio' database"
	${SUDO_POSTGRES} createdb --encoding=utf-8 --owner=scancodeio scancodeio
	@$(MAKE) migrate

run:
	${MANAGE} runserver 8001

test:
	@echo "-> Running the test suite"
	${MANAGE} test --noinput

package: conf
	@echo "-> Create a scancode.io package for offline installation"
	@echo "-> Fetch dependencies in thirdparty/ for offline installation"
	rm -rf thirdparty && mkdir thirdparty
	bin/pip download -r etc/requirements/base.txt --no-cache-dir --dest thirdparty
	@echo "-> Create package in dist/ for offline installation"
	bin/python setup.py sdist

bump:
	@echo "-> Bump the version to next patch number: 'major.minor.patch'"
	bin/bumpversion patch --allow-dirty

docs:
	rm -rf docs/_build/
	sphinx-build docs/ docs/_build/

.PHONY: conf dev envfile install check valid isort clean migrate cleandb run test package bump docs
