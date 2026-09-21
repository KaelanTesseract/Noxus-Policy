#!/usr/bin/env bash
# Copyright (c) 2026 Dennis Guse. All rights reserved.
# Licensed under the MIT License. See LICENSE file in project root.

# ==============================================================================
# Noxus Policy - Auto-Updater Script mit Auto-Backup & Ladebalken
# ==============================================================================

set -e

GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Progress Bar Generator Function
render_progress() {
  local current=$1
  local total=$2
  local stage_name=$3
  local width=30
  
  local percentage=$((current * 100 / total))
  local filled=$((current * width / total))
  local empty=$((width - filled))
  
  local filled_bar=""
  for ((i=0; i<filled; i++)); do filled_bar+="█"; done
  
  local empty_bar=""
  for ((i=0; i<empty; i++)); do empty_bar+="░"; done

  printf "\r\033[K${CYAN}[${GREEN}%s${CYAN}%s] %3d%%${NC} | %s" "$filled_bar" "$empty_bar" "$percentage" "$stage_name"
}

echo -e "${CYAN}"
echo '  _   _  _____  ___   _ ____    ____   ___  _     ___ ______   __'
echo ' | \ | |/ _ \ \/ / | | / ___|  |  _ \ / _ \| |   |_ _/ ___\ \ / /'
echo ' |  \| | | | \  /| | | \___ \  | |_) | | | | |    | | |    \ V / '
echo ' | |\  | |_| /  \| |_| |___) | |  __/| |_| | |___ | | |___  | |  '
echo ' |_| \_|\___/_/\_\\___/|____/  |_|    \___/|_____|___\____| |_|  '
echo -e "${NC}"
echo -e "${YELLOW}🚀 Starte System-Update von Noxus Policy...${NC}\n"

INSTALL_DIR="/opt/versicherungsmanager"
if [ ! -d "$INSTALL_DIR" ]; then
  INSTALL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
fi

cd "$INSTALL_DIR" || exit 1

# Use Google's public resolvers for this script's own network access (Git +
# Docker registry lookups), but only for the duration of this run: back up
# the existing /etc/resolv.conf and restore it on exit no matter how the
# script ends (success, failure, or being interrupted). A previous version
# of this script overwrote /etc/resolv.conf permanently, which on at least
# one deployment clobbered a working router-relayed resolver with public
# ones that turned out to be the less reliable choice on that network - so
# this is deliberately temporary and always reverted, never left behind.
RESOLV_BACKUP=""
if [ -f /etc/resolv.conf ]; then
  RESOLV_BACKUP="$(mktemp /tmp/noxus-resolv-backup.XXXXXX)"
  cp /etc/resolv.conf "$RESOLV_BACKUP" 2>/dev/null || RESOLV_BACKUP=""
fi
restore_resolv_conf() {
  if [ -n "$RESOLV_BACKUP" ] && [ -f "$RESOLV_BACKUP" ]; then
    cp "$RESOLV_BACKUP" /etc/resolv.conf 2>/dev/null || true
    rm -f "$RESOLV_BACKUP" 2>/dev/null || true
  fi
}
trap restore_resolv_conf EXIT
{ echo "nameserver 8.8.8.8"; echo "nameserver 8.8.4.4"; } > /etc/resolv.conf 2>/dev/null || true

# Step 1: DNS Check (15%)
render_progress 15 100 "1/5: Prüfe Netzwerk- und DNS-Verbindung..."
if ! getent hosts registry-1.docker.io >/dev/null 2>&1; then
  echo -e "\n${YELLOW}⚠ DNS-Auflösung über 8.8.8.8/8.8.4.4 scheint gerade gestört zu sein. Fahre trotzdem fort.${NC}"
fi
sleep 1

# Step 2: Auto-Database Safety Backup before updating (35%)
render_progress 35 100 "2/5: Erstelle automatisches Sicherheits-Backup der Datenbank..."
mkdir -p "$INSTALL_DIR/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# The live database sits in backend/data/ (Docker volume). This step used to look
# only at backend/insurance.db - a path from an early version that no longer
# exists - so it silently backed up nothing while still announcing a backup.
DB_BACKUP_FILE=""
for DB_CANDIDATE in "$INSTALL_DIR/backend/data/versicherungsmanager.db" "$INSTALL_DIR/backend/insurance.db"; do
  if [ -f "$DB_CANDIDATE" ]; then
    DB_BACKUP_FILE="$INSTALL_DIR/backups/insurance_backup_$TIMESTAMP.db"
    if cp "$DB_CANDIDATE" "$DB_BACKUP_FILE" 2>/dev/null; then
      chmod 600 "$DB_BACKUP_FILE" 2>/dev/null || true
    else
      DB_BACKUP_FILE=""
    fi
    break
  fi
done
# Auto-Cleanup: Keep only 5 newest update backups to save disk space
ls -dt "$INSTALL_DIR/backups"/insurance_backup_*.db 2>/dev/null | tail -n +6 | xargs rm -f 2>/dev/null || true
sleep 1

# Step 3: Git Pull & Hard Sync with GitHub (55%)
render_progress 55 100 "3/5: Lade neueste Version von GitHub herunter..."
if [ ! -d ".git" ]; then
  git init >/dev/null 2>&1 || true
  git remote add origin https://github.com/KaelanTesseract/Noxus-Policy.git >/dev/null 2>&1 || true
fi

# Always re-point origin at the canonical public repo, in case it ever drifted
# (old fork, rename, manual edit) — a stale/wrong URL is what makes Git treat
# the remote as potentially private and prompt for credentials below.
git remote set-url origin https://github.com/KaelanTesseract/Noxus-Policy.git >/dev/null 2>&1 || true

# The repo is public and read-only here, so no credentials should ever be
# needed. Disabling the terminal prompt turns a silent hang on unexpected
# auth into a fast, visible failure instead of blocking the update forever.
# A few short retries ride out transient DNS/network blips instead of
# giving up (and silently NOT updating) on the very first hiccup.
export GIT_TERMINAL_PROMPT=0
GIT_FETCH_OK=0
for attempt in 1 2 3; do
  if git -c credential.helper= fetch origin main >/dev/null 2>&1; then
    GIT_FETCH_OK=1
    break
  fi
  sleep 3
done

if [ "$GIT_FETCH_OK" = "1" ]; then
  git -c credential.helper= reset --hard origin/main >/dev/null 2>&1 || git -c credential.helper= pull origin main >/dev/null 2>&1 || true

  # This script may have just overwritten itself via the reset above. Bash
  # keeps reading the *old* file content for the rest of this run (the old
  # inode stays open even after git replaces the file on disk), so anything
  # newly added below this point in a future version would silently never
  # run on the update that introduces it - exactly what happened when the
  # SECRET_KEY requirement below shipped: this process still finished
  # against the old script and never generated it, while the freshly
  # pulled docker-compose.yml already required it, breaking that one run.
  # Restart into the just-pulled script once so the rest of this update
  # always uses current code. Restore the temporary DNS override first -
  # `exec` would skip the EXIT trap that normally does this.
  if [ -z "$NOXUS_UPDATE_REEXECED" ]; then
    restore_resolv_conf
    NOXUS_UPDATE_REEXECED=1 bash "$INSTALL_DIR/update.sh"
    exit $?
  fi
else
  echo -e "\n\n${YELLOW}⚠ Konnte GitHub nach mehreren Versuchen nicht erreichen (Netzwerk-/DNS-Problem). Fahre mit der aktuell installierten Version fort, es wird also NICHTS aktualisiert.${NC}"
fi

chmod +x update.sh install.sh 2>/dev/null || true
ln -sf "$INSTALL_DIR/update.sh" /usr/local/bin/update 2>/dev/null || true
ln -sf "$INSTALL_DIR/update.sh" /usr/local/bin/policy-update 2>/dev/null || true

# Ensure a SECRET_KEY exists (older installs predate this) without ever
# overwriting one that's already there - that would sign out every user.
if [ ! -f "$INSTALL_DIR/.env" ] || ! grep -q '^SECRET_KEY=' "$INSTALL_DIR/.env" 2>/dev/null; then
  echo -e "\n${YELLOW}🔑 Erzeuge zufälligen SECRET_KEY zur Token-Signierung (bisher nicht gesetzt)...${NC}"
  NEW_SECRET=$(openssl rand -hex 32 2>/dev/null || head -c 48 /dev/urandom | base64 | tr -dc 'a-zA-Z0-9' | head -c 64)
  echo "SECRET_KEY=${NEW_SECRET}" >> "$INSTALL_DIR/.env"
fi

# Step 4: Docker Container Rebuild without cache (80%)
render_progress 80 100 "4/5: Baue und aktualisiere Docker-Container (Frontend + Backend)..."

# Auto-install static Docker CLI on-the-fly if missing but docker.sock is present
if ! command -v docker >/dev/null 2>&1 && [ ! -x "/usr/bin/docker" ] && [ ! -x "/usr/local/bin/docker" ]; then
  if [ -S "/var/run/docker.sock" ]; then
    mkdir -p /tmp/docker_cli
    curl -fsSL https://download.docker.com/linux/static/stable/x86_64/docker-24.0.7.tgz -o /tmp/docker_cli/docker.tgz 2>/dev/null || true
    if [ -f "/tmp/docker_cli/docker.tgz" ]; then
      tar -xzf /tmp/docker_cli/docker.tgz -C /tmp/docker_cli 2>/dev/null || true
      cp /tmp/docker_cli/docker/docker /usr/local/bin/docker 2>/dev/null || cp /tmp/docker_cli/docker/docker /tmp/docker 2>/dev/null || true
      chmod +x /usr/local/bin/docker 2>/dev/null || chmod +x /tmp/docker 2>/dev/null || true
      export PATH="/tmp:/usr/local/bin:$PATH"
      rm -rf /tmp/docker_cli 2>/dev/null || true
    fi
  fi
fi

# Detect docker command syntax (test 'docker compose version' first, fallback to 'docker-compose')
DC_CMD=""

if docker compose version >/dev/null 2>&1; then
  DC_CMD="docker compose"
elif command -v docker-compose >/dev/null 2>&1; then
  DC_CMD="docker-compose"
elif [ -x "/usr/bin/docker-compose" ]; then
  DC_CMD="/usr/bin/docker-compose"
elif [ -x "/usr/local/bin/docker-compose" ]; then
  DC_CMD="/usr/local/bin/docker-compose"
elif [ -x "/tmp/docker-compose" ]; then
  DC_CMD="/tmp/docker-compose"
else
  # Auto-download standalone docker-compose binary on-the-fly if missing
  curl -fsSL "https://github.com/docker/compose/releases/download/v2.24.5/docker-compose-linux-x86_64" -o /tmp/docker-compose 2>/dev/null || true
  if [ -f "/tmp/docker-compose" ]; then
    chmod +x /tmp/docker-compose 2>/dev/null || true
    DC_CMD="/tmp/docker-compose"
  fi
fi

if [ -z "$DC_CMD" ]; then
  echo -e "\n\n${RED}❌ Fehler: Weder 'docker compose' noch 'docker-compose' wurde im Pfad gefunden.${NC}\n"
  exit 1
fi

BUILD_LOG="/tmp/noxus_build.log"
# Image pulls hit the Docker registry over the network too, so they can hit
# the same kind of transient DNS/network blip as the Git step above — retry
# a couple of times before treating it as a real failure.
BUILD_OK=0
for attempt in 1 2; do
  if $DC_CMD build --no-cache >"$BUILD_LOG" 2>&1; then
    BUILD_OK=1
    break
  fi
  sleep 5
done
if [ "$BUILD_OK" != "1" ]; then
  echo -e "\n\n${RED}❌ Fehler beim Bauen der Docker-Container:${NC}\n"
  cat "$BUILD_LOG"
  exit 1
fi

if ! $DC_CMD up -d --remove-orphans >"$BUILD_LOG" 2>&1; then
  echo -e "\n\n${RED}❌ Fehler beim Starten der Docker-Container:${NC}\n"
  cat "$BUILD_LOG"
  exit 1
fi
rm -f "$BUILD_LOG" 2>/dev/null || true

# Step 5: Wait for Backend startup & Clean Docker Cache (100%)
render_progress 95 100 "5/5: Prüfe Container-Status & Backend-Bereitschaft..."
for i in {1..15}; do
  if curl -s http://localhost:8000/ >/dev/null 2>&1 || curl -s http://127.0.0.1:8000/ >/dev/null 2>&1 || docker exec versicherungsmanager-backend-1 curl -s http://localhost:8000/ >/dev/null 2>&1; then
    break
  fi
  sleep 1
done

docker image prune -f >/dev/null 2>&1 || true
render_progress 100 100 "5/5: Update erfolgreich abgeschlossen!"
echo -e "\n"

IP_ADDR=$(hostname -I | awk '{print $1}')

echo -e "${GREEN}========================================================================${NC}"
echo -e "${CYAN}🎉 Update & Sicherheits-Backup erfolgreich abgeschlossen!${NC}"
echo -e "${GREEN}========================================================================${NC}"
if [ -n "$DB_BACKUP_FILE" ] && [ -f "$DB_BACKUP_FILE" ]; then
  echo -e "💾 **Sicherheits-Backup der Datenbank erstellt unter:**"
  echo -e "   👉 ${YELLOW}${DB_BACKUP_FILE}${NC}\n"
else
  echo -e "${YELLOW}⚠ Es wurde keine Datenbank zum Sichern gefunden (frische Installation?).${NC}\n"
fi
echo -e "🌐 **Web-Interface bereit unter:**"
echo -e "   👉 ${YELLOW}http://${IP_ADDR}:3000${NC}"
echo -e "${GREEN}========================================================================${NC}\n"
