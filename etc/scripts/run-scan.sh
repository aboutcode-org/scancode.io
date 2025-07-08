#!/bin/bash

# SPDX-License-Identifier: Apache-2.0
#
# http://nexb.com and https://github.com/aboutcode-org/scancode.io
# The ScanCode.io software is licensed under the Apache License version 2.0.
# Data generated with ScanCode.io is provided as-is without warranties.
# ScanCode is a trademark of nexB Inc.

# Usage:
# Scan current directory with default pipeline 'scan_codebase':
# ./run-scan.sh
#
# Scan a specific directory with a custom pipeline:
# ./run-scan.sh /path/to/scan/dir scan_single_package
#
# Scan a specific directory with multiple pipelines:
# ./run-scan.sh /path/to/scan/dir "scan_codebase find_vulnerabilities"

set -e

# Use first argument as scan directory or default to current directory
SCAN_DIR="${1:-$(pwd)}"
# Use second argument as pipeline name or default to 'scan_codebase'
PIPELINE="${2:-scan_codebase}"
SCIO_DOCKER_IMAGE="ghcr.io/aboutcode-org/scancode.io:latest"
RESULTS_LOCATION="results.json"
ABS_RESULTS_PATH="$(pwd)/$RESULTS_LOCATION"

# Run the pipeline
docker run --rm \
  -v "$SCAN_DIR":/codebase \
  "$SCIO_DOCKER_IMAGE" \
  run $PIPELINE /codebase \
  > "$RESULTS_LOCATION"

# Check if docker run succeeded
if [ $? -eq 0 ]; then
  echo "✅ Scan complete using pipeline '$PIPELINE'. Results saved to $ABS_RESULTS_PATH"
else
  echo "❌ Scan failed. Please check the error messages above."
  exit 1
fi
