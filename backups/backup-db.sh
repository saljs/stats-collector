#!/bin/bash

# Run mysqldump to export all databases from server
mysqldump --host=$DB_HOST --port=$DB_PORT \
    --user=$DB_USER --password=$DB_PASSWORD \
    --no-create-info vivmonitors \
    > "$OUT_PATH/vivmonitors_backup_$(date +%FT%T).sql"

# Delete all backups older than KEEP_DAYS days
find $OUT_PATH -mtime +$KEEP_DAYS -exec rm {} \;
