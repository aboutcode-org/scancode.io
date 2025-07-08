#!/bin/bash

# SPDX-License-Identifier: Apache-2.0
#
# http://nexb.com and https://github.com/aboutcode-org/scancode.io
# The ScanCode.io software is licensed under the Apache License version 2.0.
# Data generated with ScanCode.io is provided as-is without warranties.
# ScanCode is a trademark of nexB Inc.

# Usage:
#   Default scan of current directory using 'scan_codebase':
#     ./run-scan.sh
#
#   Run pipelines on current directory:
#     ./run-scan.sh scan_codebase find_vulnerabilities
#
#   Run pipelines on a specific directory:
#     ./run-scan.sh scan_codebase /path/to/scan/dir
#
#   Run multiple pipelines on a specific directory (directory must come last):
#     ./run-scan.sh scan_codebase find_vulnerabilities /my/codebase
#
#   Scan a directory using default pipeline:
#     ./run-scan.sh /path/to/codebase

set -e

readonly SCIO_DOCKER_IMAGE="ghcr.io/aboutcode-org/scancode.io:latest"
readonly RESULTS_LOCATION="results.json"

# Default values
SCAN_DIR="$(pwd)"
PIPELINES=()

# Check if last argument is a directory
LAST_ARG="${!#}"
if [ -d "$LAST_ARG" ]; then
  SCAN_DIR="$LAST_ARG"
  PIPELINES=("${@:1:$#-1}")  # All args except last
else
  PIPELINES=("$@")
fi

# Default pipeline if none specified
if [ "${#PIPELINES[@]}" -eq 0 ]; then
  PIPELINES=("scan_codebase")
fi

# Run the scan
docker run --rm \
  -v "$SCAN_DIR":/codebase \
  "$SCIO_DOCKER_IMAGE" \
  run "${PIPELINES[@]}" /codebase \
  > "$RESULTS_LOCATION"

ABS_RESULTS_PATH="$(pwd)/$RESULTS_LOCATION"

echo "✅ Scan complete using pipeline(s): ${PIPELINES[*]}"
echo "💾 Results saved to: $ABS_RESULTS_PATH"
