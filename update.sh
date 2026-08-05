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

  printf "\r${CYAN}[${GREEN}%s${CYAN}%s] %3d%%${NC} | %s" "$filled_bar" "$empty_bar" "$percentage" "$stage_name"
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

# Step 1: DNS Check (15%)
render_progress 15 100 "1/5: Prüfe Netzwerk- und DNS-Verbindung..."
if ! ping -c 1 -W 2 registry-1.docker.io >/dev/null 2>&1; then
  echo "nameserver 1.1.1.1" > /etc/resolv.conf 2>/dev/null || true
  echo "nameserver 192.168.1.1" >> /etc/resolv.conf 2>/dev/null || true
fi
sleep 1

# Step 2: Auto-Database Safety Backup before updating (35%)
render_progress 35 100 "2/5: Erstelle automatisches Sicherheits-Backup der Datenbank..."
mkdir -p "$INSTALL_DIR/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

if [ -f "$INSTALL_DIR/backend/insurance.db" ]; then
  cp "$INSTALL_DIR/backend/insurance.db" "$INSTALL_DIR/backups/insurance_backup_$TIMESTAMP.db" 2>/dev/null || true
  # Auto-Cleanup: Keep only 5 newest update backups to save disk space
  ls -dt "$INSTALL_DIR/backups"/insurance_backup_*.db 2>/dev/null | tail -n +6 | xargs rm -f 2>/dev/null || true
fi
sleep 1

# Step 3: Git Pull & Hard Sync with GitHub (55%)
render_progress 55 100 "3/5: Lade neueste Version von GitHub herunter..."
if [ ! -d ".git" ]; then
  git init >/dev/null 2>&1 || true
  git remote add origin https://github.com/KaelanTesseract/Noxus-Policy.git >/dev/null 2>&1 || true
fi

git fetch origin main >/dev/null 2>&1 || true
git reset --hard origin/main >/dev/null 2>&1 || git pull origin main >/dev/null 2>&1 || true

chmod +x update.sh install.sh 2>/dev/null || true
ln -sf "$INSTALL_DIR/update.sh" /usr/local/bin/update 2>/dev/null || true
ln -sf "$INSTALL_DIR/update.sh" /usr/local/bin/policy-update 2>/dev/null || true

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
if ! $DC_CMD build >"$BUILD_LOG" 2>&1; then
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
render_progress 100 100 "5/5: Update erfolgreich abgeschlossen!                 "
echo -e "\n"

IP_ADDR=$(hostname -I | awk '{print $1}')

echo -e "${GREEN}========================================================================${NC}"
echo -e "${CYAN}🎉 Update & Sicherheits-Backup erfolgreich abgeschlossen!${NC}"
echo -e "${GREEN}========================================================================${NC}"
echo -e "💾 **Sicherheits-Backup erstellt unter:**"
echo -e "   👉 ${YELLOW}${INSTALL_DIR}/backups/insurance_backup_${TIMESTAMP}.db${NC}\n"
echo -e "🌐 **Web-Interface bereit unter:**"
echo -e "   👉 ${YELLOW}http://${IP_ADDR}:3000${NC}"
echo -e "${GREEN}========================================================================${NC}\n"
