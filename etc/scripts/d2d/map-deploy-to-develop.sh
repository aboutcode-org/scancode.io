#!/bin/bash
set -e

FROM_PATH="$1"
TO_PATH="$2"
OUTPUT_FILE="$3"

D2D_OPTIONS=""
SPIN_DB=false
DB_PORT=5432


shift 3
while [[ "$#" -gt 0 ]]; do
  case "$1" in
    --options)
      D2D_OPTIONS="$2"
      shift 2
      ;;
    --spin-db)
      SPIN_DB=true
      shift 1
      ;;
    --port)
      DB_PORT="$2"
      shift 2
      ;;
    *)
      echo "Unknown parameter: $1"
      exit 1
      ;;
  esac
done

if [ -z "$FROM_PATH" ] || [ -z "$TO_PATH" ] || [ -z "$OUTPUT_FILE" ]; then
  echo "Missing required arguments!"
  echo "Usage: $0 <from-path> <to-path> [options] <output-file> <spin-db(true|false)> [db-port]"
  exit 1
fi

if [ -z "$DB_PORT" ]; then
  DB_PORT=5432
fi

echo "Arguments:"
echo "FROM_PATH: $FROM_PATH"
echo "TO_PATH: $TO_PATH"
echo "D2D_OPTIONS: $D2D_OPTIONS"
echo "OUTPUT_FILE: $OUTPUT_FILE"
echo "SPIN_DB: $SPIN_DB"
echo "DB_PORT: $DB_PORT"

DB_STARTED=false

if [ "$SPIN_DB" = true ]; then
  echo "Starting Postgres container on port $DB_PORT..."

  docker run -d \
    --name scancodeio-run-db \
    -e POSTGRES_DB=scancodeio \
    -e POSTGRES_USER=scancodeio \
    -e POSTGRES_PASSWORD=scancodeio \
    -e POSTGRES_INITDB_ARGS="--encoding=UTF-8 --lc-collate=en_US.UTF-8 --lc-ctype=en_US.UTF-8" \
    -v scancodeio_pgdata:/var/lib/postgresql/data \
    -p "${DB_PORT}:5432" \
    postgres:17 || {
      echo "Failed to start DB container. Cleaning up…"
      docker rm -f scancodeio-run-db >/dev/null 2>&1 || true
      exit 1
    }

  DB_STARTED=true
  echo "DB container started"
fi

WORKDIR="d2d"
mkdir -p "$WORKDIR"

cp "$FROM_PATH" "$WORKDIR/"
cp "$TO_PATH" "$WORKDIR/"

FROM_FILENAME=$(basename "$FROM_PATH")
TO_FILENAME=$(basename "$TO_PATH")

echo "Running ScanCode.io mapping..."

docker run --rm \
  -v "$(pwd)/$WORKDIR":/code \
  --network host \
  -e SCANCODEIO_NO_AUTO_DB=1 \
  ghcr.io/aboutcode-org/scancode.io:latest \
  run map_deploy_to_develop:"$D2D_OPTIONS" \
  "/code/${FROM_FILENAME}:from,/code/${TO_FILENAME}:to" \
  > "$OUTPUT_FILE"

echo "Output saved to $OUTPUT_FILE"


rm -rf "$WORKDIR"
echo "Temporary directory cleaned up"

if [ "$DB_STARTED" = true ]; then
  echo "Stopping DB container..."
  docker rm -f scancodeio-run-db >/dev/null 2>&1 || true
  echo "DB container removed"
fi

echo "Done!"
