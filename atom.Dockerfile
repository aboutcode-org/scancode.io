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

FROM ghcr.io/appthreat/atom:v3.2.0

RUN set -e; \
    JAVA_DIR="$(ls -d /opt/java/*-tem | head -n1)"; \
    MAVEN_DIR="$(ls -d /opt/maven/* | head -n1)"; \
    SBT_DIR="$(ls -d /opt/sbt/* | head -n1)"; \
    SCALA_DIR="$(ls -d /opt/scala/* | head -n1)"; \
    mkdir -p /atom-staged/opt /atom-staged/bin /atom-staged/lib/node_modules; \
    cp -a /opt/wrapper /opt/java /opt/maven /opt/sbt /opt/scala /opt/vendor /atom-staged/opt/; \
    cp /usr/bin/node-22 /atom-staged/bin/node; \
    for lib in $(ldd /usr/bin/node-22 | awk '/=>/{print $3}'); do \
      case "$lib" in */libc.so*|*/libm.so*|*/libpthread*|*/libdl.so*|*/librt*|*/ld-linux*) ;; *) cp -aL "$lib" /atom-staged/lib/ ;; esac; \
    done; \
    cp -a /usr/local/lib/node_modules/. /atom-staged/lib/node_modules/; \
    ln -sfn /atom-root/opt/wrapper/nodejs/packages/atom /atom-root/opt/wrapper/nodejs/packages/atom-jar /atom-staged/lib/node_modules/@appthreat/; \
    printf '#!/bin/sh\nexport LD_LIBRARY_PATH=/atom-root/lib\nexport JAVA_HOME=/atom-root%s\nexport PATH=/atom-root%s/bin:/atom-root%s/bin:/atom-root%s/bin:/atom-root%s/bin:/atom-root/opt/vendor/bin:$PATH\nexec /atom-root/bin/node /atom-root/opt/wrapper/nodejs/packages/atom/index.js "$@"\n' \
      "$JAVA_DIR" "$JAVA_DIR" "$MAVEN_DIR" "$SBT_DIR" "$SCALA_DIR" \
      > /atom-staged/bin/atom; \
    chmod +x /atom-staged/bin/atom

ENTRYPOINT ["/bin/sh", "-c", "set -e; find /atom-root -mindepth 1 -delete; cp -a /atom-staged/. /atom-root/"]