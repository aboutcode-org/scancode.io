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

# Do not depend on Python to generate the SECRET_KEY
GET_SECRET_KEY=`base64 /dev/urandom | head -c50`
# Customize with `$ make envfile ENV_FILE=/etc/scancodeio/.env`
ENV_FILE=.env
PKG2APPIMAGE_FILE=pkg2appimage.AppImage
PYTHON_LINUX_SUPPORT_DIR=Python-Linux-support
BUILT_PYTHON_ARCHIVE=Python-3.10-linux-x86_64-support.custom.tar.gz

envfile:
	@echo "-> Create the .env file and generate a secret key"
	@if test -f ${ENV_FILE}; then echo ".env file exists already"; exit 1; fi
	@mkdir -p $(shell dirname ${ENV_FILE}) && touch ${ENV_FILE}
	@echo SECRET_KEY=\"${GET_SECRET_KEY}\" > ${ENV_FILE}
	@echo SCANCODEIO_DB_ENGINE=\"django.db.backends.sqlite3\" >> ${ENV_FILE}

python:
	@echo "-> Build Python"
	@if ! test -f ${BUILT_PYTHON_ARCHIVE}; then \
		mkdir ${PYTHON_LINUX_SUPPORT_DIR} \
		&& wget https://github.com/beeware/Python-Linux-support/archive/refs/heads/main.tar.gz -O - | tar xzv --directory ${PYTHON_LINUX_SUPPORT_DIR} --strip-components=1 \
		&& cp resources/${PYTHON_LINUX_SUPPORT_DIR}/Makefile resources/${PYTHON_LINUX_SUPPORT_DIR}/exclude.list ${PYTHON_LINUX_SUPPORT_DIR} \
		&& cd ${PYTHON_LINUX_SUPPORT_DIR} && $(MAKE) && cd .. \
		&& cp ${PYTHON_LINUX_SUPPORT_DIR}/dist/${BUILT_PYTHON_ARCHIVE} . ;\
	fi

build: python
	@echo "-> Build ScanCode.io AppImage"
	@if ! test -f ${PKG2APPIMAGE_FILE}; then wget https://github.com/AppImageCommunity/pkg2appimage/releases/download/continuous/pkg2appimage-1807-x86_64.AppImage -O ${PKG2APPIMAGE_FILE}; chmod u+x ${PKG2APPIMAGE_FILE}; fi
	@./${PKG2APPIMAGE_FILE} scancodeio.yml

.PHONY: envfile python build
