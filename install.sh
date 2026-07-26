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

# 2. Fix DNS if needed (prevents Docker DNS timeouts in Proxmox LXC)
if ! ping -c 1 -W 2 registry-1.docker.io >/dev/null 2>&1; then
  echo -e "${YELLOW}⚙️  Passe DNS-Konfiguration (/etc/resolv.conf) für zuverlässige Docker-Downloads an...${NC}"
  echo "nameserver 1.1.1.1" > /etc/resolv.conf
  echo "nameserver 192.168.1.1" >> /etc/resolv.conf
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
  git pull origin main || true
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

# 7. Build and Start Docker Containers
echo -e "${GREEN}🚀 Baue und starte Docker-Container (Frontend + Backend + KI-Engine)...${NC}"
docker compose down --remove-orphans || true
docker compose up -d --build

# 8. Get Container IP Address
IP_ADDR=$(hostname -I | awk '{print $1}')

echo -e "\n${GREEN}========================================================================${NC}"
echo -e "${CYAN}🎉 Installation erfolgreich abgeschlossen!${NC}"
echo -e "${GREEN}========================================================================${NC}"
echo -e "🌐 **Web-Interface aufrufen:**"
echo -e "   👉 ${YELLOW}http://${IP_ADDR}:3000${NC}\n"
echo -e "🔄 **Updates in Zukunft durchführen:**"
echo -e "   Einfach im Terminal diesen Befehl eingeben:"
echo -e "   👉 ${CYAN}update${NC}"
echo -e "${GREEN}========================================================================${NC}\n"
