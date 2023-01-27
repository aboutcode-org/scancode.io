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

FROM ubuntu:18.04

# OS requirements as per
# https://scancode-toolkit.readthedocs.io/en/latest/getting-started/install.html
RUN apt-get update \
 && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
    libexpat1 \
    gtk-update-icon-cache \
    ca-certificates \
    gcc \
    libpq-dev \
    python3-dev \
    wget \
    python3-pip \
    file \
    desktop-file-utils \
    build-essential \
    libglib2.0-bin \
 && apt-get clean \
 && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

WORKDIR /tmp
RUN wget https://github.com/AppImageCommunity/pkg2appimage/releases/download/continuous/pkg2appimage-1807-x86_64.AppImage -O pkg2appimage.AppImage && \
    sed 's|AI\x02|\x00\x00\x00|g' -i /tmp/pkg2appimage.AppImage && \
    chmod +x /tmp/pkg2appimage.AppImage && \
    cd /opt && /tmp/pkg2appimage.AppImage --appimage-extract || true && \
    mv squashfs-root pkg2appimage.AppDir && \
    ln -s /opt/pkg2appimage.AppDir/AppRun /usr/bin/pkg2appimage && \
    rm /tmp/pkg2appimage.AppImage

WORKDIR /
