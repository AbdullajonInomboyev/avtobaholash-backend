#!/bin/bash
# PostgreSQL avtomatik backup skripti
# Cron: 0 2 * * * /app/docker/backup.sh

set -e

BACKUP_DIR="/backups"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/avtobaholash_$DATE.sql.gz"
RETENTION_DAYS=30

mkdir -p "$BACKUP_DIR"

echo "[$DATE] Backup boshlanmoqda..."

# Backup olish
docker exec avtobaholash_db_1 pg_dump \
    -U postgres \
    -d avtobaholash \
    --no-owner \
    --no-acl \
    | gzip > "$BACKUP_FILE"

echo "[$DATE] Backup saqlandi: $BACKUP_FILE"

# Eski backuplarni o'chirish
find "$BACKUP_DIR" -name "*.sql.gz" -mtime +$RETENTION_DAYS -delete
echo "[$DATE] $RETENTION_DAYS kundan eski backuplar o'chirildi"

# MinIO ga yuklash (ixtiyoriy)
if [ -n "$MINIO_BACKUP_BUCKET" ]; then
    docker run --rm \
        -e MC_HOST_local="http://$MINIO_ACCESS_KEY:$MINIO_SECRET_KEY@minio:9000" \
        minio/mc cp "$BACKUP_FILE" "local/$MINIO_BACKUP_BUCKET/$(basename $BACKUP_FILE)"
    echo "[$DATE] MinIO ga yuklandi"
fi

echo "[$DATE] Backup muvaffaqiyatli yakunlandi"
