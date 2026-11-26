#!/bin/bash
set -Eeuo pipefail

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
ARCH=$(uname -m)
case "$ARCH" in
  x86_64|amd64) ARCH=x86_64 ;;
  *) echo "Unsupported architecture: $ARCH" >&2; exit 1 ;;
esac

APPIMAGE="$SCRIPT_DIR/dist/ScanCodeIO-$ARCH.AppImage"
if [[ ! -x "$APPIMAGE" ]]; then
  echo "No built AppImage found at $APPIMAGE" >&2
  echo "Run $SCRIPT_DIR/build-appimage.sh first." >&2
  exit 1
fi
exec "$APPIMAGE" "$@"
build-appimage.sh