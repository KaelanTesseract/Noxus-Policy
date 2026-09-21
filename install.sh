#!/usr/bin/env bash
# Copyright (c) 2026 Dennis Guse. All rights reserved.
# Licensed under the MIT License. See LICENSE file in project root.

# ==============================================================================
# Noxus Policy - Proxmox LXC & Linux 1-Click Auto-Installer
# ==============================================================================

set -e

# Formatting
GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${CYAN}"
echo '  _   _  _____  ___   _ ____    ____   ___  _     ___ ______   __'
echo ' | \ | |/ _ \ \/ / | | / ___|  |  _ \ / _ \| |   |_ _/ ___\ \ / /'
echo ' |  \| | | | \  /| | | \___ \  | |_) | | | | |    | | |    \ V / '
echo ' | |\  | |_| /  \| |_| |___) | |  __/| |_| | |___ | | |___  | |  '
echo ' |_| \_|\___/_/\_\\___/|____/  |_|    \___/|_____|___\____| |_|  '
echo -e "${NC}"
echo -e "${YELLOW}🚀 Starte automatische 1-Klick Installation von Noxus Policy...${NC}\n"

# 1. Check Root
if [ "$EUID" -ne 0 ]; then
  echo -e "${RED}❌ Bitte führe das Skript als root aus (z.B. im Proxmox LXC Terminal).${NC}"
  exit 1
fi

# 2. Use Google's public resolvers for this script's own network access (apt,
# Docker install, Git clone/pull), but only for the duration of this run: back
# up the existing /etc/resolv.conf and restore it on exit no matter how the
# script ends (success, failure, or being interrupted). An earlier version of
# this check overwrote /etc/resolv.conf permanently based on a single ICMP
# ping - ICMP is commonly blocked even when DNS/HTTPS work fine, and a
# permanent overwrite can clobber a working, admin-configured resolver with
# public ones that turn out to be less reliable on that particular network.
# update.sh already got this fix (see its own comment for the incident that
# prompted it); this backports the same approach here.
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
if ! getent hosts registry-1.docker.io >/dev/null 2>&1; then
  echo -e "${YELLOW}⚙️  Passe DNS-Konfiguration (/etc/resolv.conf) vorübergehend für diesen Lauf an...${NC}"
  { echo "nameserver 8.8.8.8"; echo "nameserver 8.8.4.4"; } > /etc/resolv.conf 2>/dev/null || true
fi

# 3. Update Package Manager & Install Dependencies
echo -e "${GREEN}📦 Installiere System-Abhängigkeiten (curl, wget, git, docker)...${NC}"
apt-get update -qq
apt-get install -y -qq curl wget git ca-certificates gnupg >/dev/null 2>&1

# 4. Check & Install Docker
if ! command -v docker &> /dev/null; then
  echo -e "${GREEN}🐳 Docker ist nicht installiert. Installiere Docker CE...${NC}"
  curl -fsSL https://get.docker.com | sh
  systemctl enable --now docker
fi

# 5. Check & Install Docker Compose
if ! docker compose version &> /dev/null; then
  echo -e "${GREEN}⚙️  Installiere Docker Compose Plugin...${NC}"
  apt-get install -y -qq docker-compose-plugin >/dev/null 2>&1
fi

# 6. Prepare App Directory
INSTALL_DIR="/opt/versicherungsmanager"
echo -e "${GREEN}📂 Richte Installationsverzeichnis in ${INSTALL_DIR} ein...${NC}"

if [ -d "$INSTALL_DIR/.git" ]; then
  echo -e "${YELLOW}🔄 Aktualisiere bestehende Installation...${NC}"
  cd "$INSTALL_DIR"
  # Re-point origin at the canonical public repo in case it ever drifted, and
  # never let this block on an unexpected credential prompt (repo is public).
  git remote set-url origin https://github.com/KaelanTesseract/Noxus-Policy.git >/dev/null 2>&1 || true
  GIT_TERMINAL_PROMPT=0 git -c credential.helper= pull origin main || true

  # The pull above may have just changed install.sh itself. This process keeps
  # executing the version it already had in memory, so anything newly added
  # further down would never run on the update that introduces it. Restart
  # into the freshly pulled script once so the rest of this run always uses
  # current code (see the same fix in update.sh for the incident this covers).
  if [ -z "$NOXUS_INSTALL_REEXECED" ]; then
    NOXUS_INSTALL_REEXECED=1 bash "$INSTALL_DIR/install.sh"
    exit $?
  fi
else
  mkdir -p "$INSTALL_DIR"
  cd "$INSTALL_DIR"
  if [ -f "docker-compose.yml" ]; then
    echo -e "${GREEN}✔ Lokale Projektdateien vorhanden.${NC}"
  fi
  # Download latest repository
  git clone https://github.com/KaelanTesseract/Noxus-Policy.git . 2>/dev/null || true
fi

# Make scripts executable & create system-wide 'update' command shortcut
chmod +x install.sh update.sh 2>/dev/null || true
ln -sf /opt/versicherungsmanager/update.sh /usr/local/bin/update
ln -sf /opt/versicherungsmanager/update.sh /usr/local/bin/policy-update

# 7. Generate a random SECRET_KEY on first install (never overwrite an existing
# one - that would invalidate every logged-in user's session on every re-run).
if [ ! -f "$INSTALL_DIR/.env" ] || ! grep -q '^SECRET_KEY=' "$INSTALL_DIR/.env" 2>/dev/null; then
  echo -e "${GREEN}🔑 Erzeuge zufälligen SECRET_KEY zur Token-Signierung...${NC}"
  NEW_SECRET=$(openssl rand -hex 32 2>/dev/null || head -c 48 /dev/urandom | base64 | tr -dc 'a-zA-Z0-9' | head -c 64)
  echo "SECRET_KEY=${NEW_SECRET}" >> "$INSTALL_DIR/.env"
fi

# 8. Build and Start Docker Containers
echo -e "${GREEN}🚀 Baue und starte Docker-Container (Frontend + Backend + KI-Engine)...${NC}"
docker compose down --remove-orphans || true
docker compose up -d --build

# 9. The backend prints a one-time random admin password on its very first start
# (there is no fixed default login any more). Wait for it and show it here.
INITIAL_ADMIN_PW=""
for i in $(seq 1 60); do
  INITIAL_ADMIN_PW=$(docker compose logs backend 2>/dev/null | grep -m1 -o 'INITIAL_ADMIN_PASSWORD=.*' | cut -d= -f2- | tr -d '\r' || true)
  [ -n "$INITIAL_ADMIN_PW" ] && break
  # Backend already up but no such line -> an admin exists from an earlier install.
  curl -s http://127.0.0.1:8000/api/health >/dev/null 2>&1 && break
  sleep 2
done

# 10. Get Container IP Address
IP_ADDR=$(hostname -I | awk '{print $1}')

echo -e "\n${GREEN}========================================================================${NC}"
echo -e "${CYAN}🎉 Installation erfolgreich abgeschlossen!${NC}"
echo -e "${GREEN}========================================================================${NC}"
echo -e "🌐 **Web-Interface aufrufen:**"
echo -e "   👉 ${YELLOW}http://${IP_ADDR}:3000${NC}\n"
if [ -n "$INITIAL_ADMIN_PW" ]; then
  echo -e "🔑 **Erst-Login (nur einmalig gültig):**"
  echo -e "   Benutzername: ${YELLOW}Admin${NC}   Passwort: ${YELLOW}${INITIAL_ADMIN_PW}${NC}"
  echo -e "   Beim ersten Anmelden legst du eine eigene E-Mail und ein eigenes Passwort fest.\n"
else
  echo -e "🔑 Ein Admin-Konto besteht bereits. Passwort vergessen? Auf dem Server:"
  echo -e "   ${CYAN}cd ${INSTALL_DIR} && docker compose exec backend python reset_admin.py${NC}\n"
fi
echo -e "🔄 **Updates in Zukunft durchführen:**"
echo -e "   Einfach im Terminal diesen Befehl eingeben:"
echo -e "   👉 ${CYAN}update${NC}"
echo -e "${GREEN}========================================================================${NC}\n"
