#!/bin/sh

# Run mysqldump to export all databases from server
mysqldump --host=$DB_HOST --port=$DB_PORT \
    --user=$DB_USER --password=$DB_PASSWORD \
    --all-databases > "${OUT_PATH}/backup_$(date +%FT%T).sql"

# Delete all backups older than KEEP_DAYS days
find $OUT_PATH -mtime +$KEEP_DAYS -exec rm {} \;
