#!/bin/sh
# Entrypoint script for Budgie.
# Supports PUID / PGID environment variables to match host UID/GID.
# This is important for Synology NAS and other systems where the data
# directory is owned by a specific user.
#
# Usage in docker-compose.yml:
#   environment:
#     - PUID=1026   # run: id -u
#     - PGID=100    # run: id -g

set -e

PUID=${PUID:-1000}
PGID=${PGID:-1000}

echo "[entrypoint] Starting Budgie as UID=${PUID} GID=${PGID}"

# If running as root, adjust the budgie user's UID/GID then drop privileges
if [ "$(id -u)" = "0" ]; then
    # Update GID of the budgie group
    if [ "$(id -g budgie 2>/dev/null)" != "${PGID}" ]; then
        groupmod -o -g "${PGID}" budgie 2>/dev/null || true
    fi

    # Update UID of the budgie user
    if [ "$(id -u budgie 2>/dev/null)" != "${PUID}" ]; then
        usermod -o -u "${PUID}" budgie 2>/dev/null || true
    fi

    # Ensure data directory is owned by the correct user
    chown -R budgie:budgie /app/data

    # Drop to budgie user
    exec gosu budgie "$@"
else
    # Already running as non-root (e.g., in dev without PUID/PGID)
    exec "$@"
fi
