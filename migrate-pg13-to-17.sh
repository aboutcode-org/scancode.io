#!/bin/bash
# =============================================================================
# PostgreSQL 13 to 17 Migration Script for ScanCode.io
# =============================================================================
#
# This script migrates the PostgreSQL database from version 13 to 17.
#
# Usage:
#   ./migrate-pg13-to-17.sh [backup_directory]
#
# Arguments:
#   backup_directory  Optional. Directory to store the backup file.
#                     Defaults to current directory.
#
# Examples:
#   ./migrate-pg13-to-17.sh
#   ./migrate-pg13-to-17.sh /path/to/backups
#
# =============================================================================

set -e
echo "=== PostgreSQL 13 to 17 Migration ==="

POSTGRES_DB="scancodeio"
POSTGRES_USER="scancodeio"
BACKUP_DIR="${1:-.}"
BACKUP_FILE="$BACKUP_DIR/backup_pg13_$(date +%Y%m%d_%H%M%S).dump"
VOLUME_NAME="scancodeio_db_data"
VOLUME_BACKUP="${VOLUME_NAME}_pg13_backup"

# Check backup directory exists
if [ ! -d "$BACKUP_DIR" ]; then
    echo "ERROR: Backup directory $BACKUP_DIR does not exist"
    exit 1
fi

# Stop all compose services first
echo "Stopping all services..."
docker compose down

# Cleanup any leftover container from previous run
docker rm -f pg13_backup 2>/dev/null || true

# Check volume exists
if ! docker volume inspect "$VOLUME_NAME" &>/dev/null; then
    echo "ERROR: Volume $VOLUME_NAME not found"
    exit 1
fi

echo "Step 1/5: Starting temporary PG13 container for backup..."
docker run -d --name pg13_backup \
    -v "$VOLUME_NAME":/var/lib/postgresql/data \
    postgres:13

echo "         Waiting for PG13 to be ready..."
until docker exec pg13_backup pg_isready 2>/dev/null; do
    sleep 2
done

echo "Step 2/5: Creating backup of $POSTGRES_DB (this may take a while)..."
docker exec pg13_backup pg_dump -U "$POSTGRES_USER" -Fc "$POSTGRES_DB" > "$BACKUP_FILE"
BACKUP_SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
echo "         Backup saved to: $BACKUP_FILE ($BACKUP_SIZE)"

if [ ! -s "$BACKUP_FILE" ]; then
    echo "ERROR: Backup file is empty"
    docker stop pg13_backup && docker rm pg13_backup
    exit 1
fi

echo "Step 3/5: Stopping temporary container and renaming old volume..."
docker stop pg13_backup && docker rm pg13_backup

docker volume create "$VOLUME_BACKUP"
docker run --rm \
    -v "$VOLUME_NAME":/from:ro \
    -v "$VOLUME_BACKUP":/to \
    alpine sh -c "cp -a /from/. /to/"
docker volume rm "$VOLUME_NAME"
echo "         Old volume preserved as: $VOLUME_BACKUP"

echo "Step 4/5: Starting fresh PG17..."
docker compose up -d db
echo "         Waiting for PG17 to be ready..."
until docker compose exec -T db pg_isready 2>/dev/null; do
    sleep 2
done

echo "Step 5/5: Restoring data (this may take a while)..."
docker cp "$BACKUP_FILE" scancodeio-db-1:/tmp/backup.dump
docker compose exec -T db pg_restore -U "$POSTGRES_USER" -d "$POSTGRES_DB" --no-owner --no-acl /tmp/backup.dump
docker compose exec -T db rm /tmp/backup.dump

echo ""
echo "=== Migration complete! ==="
echo "Backup retained at: $BACKUP_FILE"
echo "Old volume preserved as: $VOLUME_BACKUP"
echo ""
echo "Once verified, you can delete the old volume with:"
echo "  docker volume rm $VOLUME_BACKUP"
echo ""
echo "Verify with: docker compose exec db psql -U scancodeio -c 'SELECT version();'"
