#!/bin/sh
# Copyright (c) 2026 Dennis Guse. All rights reserved.
# Licensed under the MIT License. See LICENSE file in project root.
#
# Starts the backend as the unprivileged user "app" instead of root.
#
# The data folders are bind mounts that exist on the host before the container
# ever runs, so they are owned by root (or by whoever installed the app). The
# container therefore starts as root just long enough to hand those folders to
# "app", then drops privileges for good. If anything about that fails - or if
# RUN_AS_ROOT=1 is set - it keeps running as root exactly like before rather
# than crash-looping, and says so in the log.

set -e

DIRS="/app/data /app/documents /app/models_data"

if [ "$(id -u)" != "0" ]; then
  exec "$@"
fi

if [ "${RUN_AS_ROOT:-0}" = "1" ]; then
  echo "[entrypoint] RUN_AS_ROOT=1 - not dropping privileges."
  exec "$@"
fi

if ! command -v setpriv >/dev/null 2>&1; then
  echo "[entrypoint] WARNING: setpriv not found, running as root."
  exec "$@"
fi

APP_UID="$(id -u app)"

for dir in $DIRS; do
  mkdir -p "$dir"
  # Re-own only when needed: walking a large documents folder on every start is wasteful.
  if [ "$(stat -c %u "$dir")" != "$APP_UID" ]; then
    echo "[entrypoint] Handing $dir to user app..."
    chown -R app:app "$dir" 2>/dev/null || true
  fi
done

for dir in $DIRS; do
  if ! setpriv --reuid=app --regid=app --init-groups test -w "$dir"; then
    echo "[entrypoint] WARNING: user app cannot write to $dir, running as root."
    exec "$@"
  fi
done

exec setpriv --reuid=app --regid=app --init-groups "$@"
