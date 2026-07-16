#!/bin/bash

BENCH_DIR="/home/frappe/frappe-bench"
SITE="builder.localhost"

# Reuse an existing bench if one is already provisioned.
if [ -d "$BENCH_DIR/apps/frappe" ]; then
    echo "Bench already exists, skipping init"
    cd "$BENCH_DIR"
    bench start
    exit 0
fi

echo "Creating new bench..."
bench init --skip-redis-config-generation frappe-bench --version version-15
cd frappe-bench

# Point services at the compose containers instead of localhost.
bench set-mariadb-host mariadb
bench set-redis-cache-host "redis://redis:6379"
bench set-redis-queue-host "redis://redis:6379"
bench set-redis-socketio-host "redis://redis:6379"

# Remove redis/watch entries from the Procfile (handled by compose).
sed -i '/redis/d' ./Procfile
sed -i '/watch/d' ./Procfile

bench get-app builder --branch develop

bench new-site "$SITE" \
    --force \
    --mariadb-root-password 123 \
    --admin-password admin \
    --no-mariadb-socket

bench --site "$SITE" install-app builder
bench --site "$SITE" set-config developer_mode 1
bench --site "$SITE" set-config mute_emails 1
bench --site "$SITE" clear-cache
bench use "$SITE"

bench start
