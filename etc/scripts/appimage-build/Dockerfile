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

FROM ubuntu:20.04

# OS requirements as per
# https://scancode-toolkit.readthedocs.io/en/latest/getting-started/install.html
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
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
 && apt-get clean \
 && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

WORKDIR /tmp
RUN wget https://github.com/AppImage/AppImageKit/releases/download/continuous/appimagetool-x86_64.AppImage && \
    sed 's|AI\x02|\x00\x00\x00|g' -i /tmp/appimagetool-x86_64.AppImage && \
    chmod +x /tmp/appimagetool-x86_64.AppImage && \
    cd /opt && /tmp/appimagetool-x86_64.AppImage --appimage-extract && \
    mv squashfs-root appimage-tool.AppDir && \
    ln -s /opt/appimage-tool.AppDir/AppRun /usr/bin/appimagetool && \
    rm /tmp/appimagetool-x86_64.AppImage

WORKDIR /tmp
RUN wget https://github.com/AppImageCrafters/appimage-builder/releases/download/Continuous/appimage-builder-1.1.1.dev32+g2709a3b-x86_64.AppImage -O appimage-builder.AppImage && \
    sed 's|AI\x02|\x00\x00\x00|g' -i /tmp/appimage-builder.AppImage && \
    chmod +x /tmp/appimage-builder.AppImage && \
    cd /opt && /tmp/appimage-builder.AppImage --appimage-extract || true && \
    mv squashfs-root appimage-builder.AppDir && \
    ln -s /opt/appimage-builder.AppDir/AppRun /usr/bin/appimage-builder && \
    rm /tmp/appimage-builder.AppImage

WORKDIR /tmp
RUN wget https://github.com/AppImageCommunity/pkg2appimage/releases/download/continuous/pkg2appimage-1807-x86_64.AppImage -O pkg2appimage.AppImage && \
    sed 's|AI\x02|\x00\x00\x00|g' -i /tmp/pkg2appimage.AppImage && \
    chmod +x /tmp/pkg2appimage.AppImage && \
    cd /opt && /tmp/pkg2appimage.AppImage --appimage-extract || true && \
    mv squashfs-root pkg2appimage.AppDir && \
    ln -s /opt/pkg2appimage.AppDir/AppRun /usr/bin/pkg2appimage && \
    sed 's|AI\x02|\x00\x00\x00|g' -i /opt/pkg2appimage.AppDir/usr/bin/appimagetool && \
    rm /tmp/pkg2appimage.AppImage

WORKDIR /
