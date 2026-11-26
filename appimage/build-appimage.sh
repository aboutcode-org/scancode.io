#!/bin/bash
set -Eeuo pipefail

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
PYTHON=/usr/bin/python3
DISPLAY_NAME=ScanCodeIO
NAME=scancodeio
PACKAGES=(postgresql redis-server python3 python3-pip python3-dev libxml2-dev libxslt1-dev zlib1g-dev bzip2 xz-utils libgomp1 file wget curl)

if [[ $EUID -eq 0 ]]; then
  echo "Run this script as a regular user, without sudo." >&2
  exit 1
fi

ARCH=$(uname -m)
case "$ARCH" in
  x86_64|amd64) ARCH=x86_64 ;;
  *) echo "Unsupported architecture: $ARCH" >&2; exit 1 ;;
esac

VERSION=${VERSION:-$("$PYTHON" -m pip index versions scancodeio 2>/dev/null | sed -n '1s/.*(\([^)]*\)).*/\1/p')}
VERSION=${VERSION:-latest}
APPDIR="$SCRIPT_DIR/out/$NAME-$VERSION-$ARCH.AppDir"
OUTPUT="$SCRIPT_DIR/dist/$DISPLAY_NAME-$ARCH.AppImage"
PYTHON_VERSION=$("$PYTHON" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
PYTHON_DIR="/usr/lib/python$PYTHON_VERSION"

install_dependencies() {
  local missing=()
  for package in "${PACKAGES[@]}"; do
    dpkg-query -W -f='${db:Status-Status}' "$package" 2>/dev/null | grep -qx installed || missing+=("$package")
  done
  if ((${#missing[@]})); then
    sudo apt-get update
    sudo apt-get install -y "${missing[@]}"
  fi
}

copy_shared_libraries() {
  {
    find "$APPDIR/usr/bin" -maxdepth 1 -type f -executable -print
    find "$APPDIR/usr/lib/$PG_LIB_REL" -type f -name '*.so*' -print
    find "$APPDIR/usr/lib/python$PYTHON_VERSION/lib-dynload" -type f -name '*.so' -print
  } |
    while IFS= read -r binary; do
      ldd "$binary" 2>/dev/null
    done |
    awk '/=> \// {print $3} /^[[:space:]]*\// {print $1}' |
    sort -u |
    while IFS= read -r library; do
      [[ -f "$library" ]] && cp -L --preserve=mode "$library" "$APPDIR/usr/lib/"
    done

  rm -f "$APPDIR/usr/lib/libc.so."* "$APPDIR/usr/lib/libpthread.so."* "$APPDIR/usr/lib/librt.so."*
}

install_dependencies

rm -rf "$APPDIR"
mkdir -p "$APPDIR/usr/bin" "$APPDIR/usr/lib" "$APPDIR/usr/share"
cp "$PYTHON" "$APPDIR/usr/bin/python3"
cp -a "$PYTHON_DIR" "$APPDIR/usr/lib/"
cp /usr/bin/redis-server /usr/bin/redis-cli "$APPDIR/usr/bin/"

PG_BINDIR=$(pg_config --bindir)
PG_LIBDIR=$(pg_config --pkglibdir)
[[ -d "$PG_BINDIR" ]] || { echo "PostgreSQL binaries not found: $PG_BINDIR" >&2; exit 1; }
[[ -d "$PG_LIBDIR" ]] || { echo "PostgreSQL extensions not found: $PG_LIBDIR" >&2; exit 1; }
PG_LIB_REL=${PG_LIBDIR#/usr/lib/}
cp -a "$PG_BINDIR"/. "$APPDIR/usr/bin/"
mkdir -p "$APPDIR/usr/lib/$PG_LIB_REL"
cp -a "$PG_LIBDIR"/. "$APPDIR/usr/lib/$PG_LIB_REL/"
[[ ! -d /usr/share/postgresql ]] || cp -a /usr/share/postgresql "$APPDIR/usr/share/"
copy_shared_libraries

PYTHON_PACKAGES="$APPDIR/usr/lib/python-packages"
"$PYTHON" -m pip install --upgrade --ignore-installed --target "$PYTHON_PACKAGES" \
  scancodeio gunicorn psycopg2-binary redis django-rq setuptools

cp "$SCRIPT_DIR/appimage_wsgi.py" "$PYTHON_PACKAGES/scancodeio/appimage_wsgi.py"

mkdir -p "$APPDIR/usr/share/icons/hicolor/256x256/apps"
cp "$SCRIPT_DIR/logo.png" "$APPDIR/logo.png"
cp "$SCRIPT_DIR/logo.png" "$APPDIR/usr/share/icons/hicolor/256x256/apps/scancodeio.png"
cp "$SCRIPT_DIR/AppRun" "$APPDIR/AppRun"
chmod 0755 "$APPDIR/AppRun"

echo "$VERSION" > "$APPDIR/VERSION"
cat > "$APPDIR/$NAME-$VERSION-$ARCH.desktop" <<EOF
[Desktop Entry]
Name=$DISPLAY_NAME
Exec=AppRun
Icon=logo
Type=Application
Terminal=true
Categories=Development;
EOF

APPIMAGETOOL="$SCRIPT_DIR/appimagetool-$ARCH.AppImage"
if [[ ! -x "$APPIMAGETOOL" ]]; then
  curl -fL "https://github.com/AppImage/AppImageKit/releases/download/continuous/appimagetool-$ARCH.AppImage" -o "$APPIMAGETOOL"
  chmod 0755 "$APPIMAGETOOL"
fi

mkdir -p "$SCRIPT_DIR/dist"
ARCH="$ARCH" "$APPIMAGETOOL" --appimage-extract-and-run "$APPDIR" "$OUTPUT"
echo "Build complete: dist/$DISPLAY_NAME-$ARCH.AppImage"