#!/usr/bin/env bash
# ==============================================================================
# Noxus Policy - Proxmox VE Host LXC 1-Click Creator & Installer
# (Runs directly in Proxmox VE Host Shell - pve node)
# ==============================================================================

set -e

GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${CYAN}"
echo '  _  _  ___  _  _ _  _ ___   ___  ___  _    ___ _____   __'
echo ' | \| |/ _ \| |/ / || / __| | _ \/ _ \| |  |_ _/ __\ \ / /'
echo ' | .` | (_) | '\'' <| || \__ \ |  _/ (_) | |__ | | (__ \ V / '
echo ' |_|\_|\___/|_|\_\\_,_|___/ |_|  \___/|____|___\___| |_|  '
echo -e "${NC}"
echo -e "${YELLOW}🚀 Proxmox VE LXC 1-Klick Container-Erstellung für Noxus Policy${NC}\n"

# 1. Ensure running on Proxmox VE Host
if ! command -v pveversion &> /dev/null; then
  echo -e "${RED}❌ Dieses Skript ist für die Proxmox VE Host Shell gedacht (Proxmox Server).${NC}"
  echo -e "Wenn du das Skript bereits innerhalb eines LXC Containers ausführst, verwende bitte install.sh!"
  exit 1
fi

# 2. Get Next Available CT ID
NEXTID=$(pvesh get /cluster/nextid)
read -p "Container ID wählen [$NEXTID]: " CTID
CTID=${CTID:-$NEXTID}

read -p "Hostname wählen [noxus-policy]: " HOSTNAME
HOSTNAME=${HOSTNAME:-noxus-policy}

read -p "RAM in MB wählen (empfohlen 4096 MB) [4096]: " RAM
RAM=${RAM:-4096}

read -p "CPU Kerne wählen (empfohlen 4 Kerne) [4]: " CORES
CORES=${CORES:-4}

read -p "Diskspeicher in GB wählen [16]: " DISK
DISK=${DISK:-16}

# Detect Storage Pool
STORAGE=$(pvesm status -content rootdir | awk 'NR==2 {print $1}')
read -p "Proxmox Storage wählen [$STORAGE]: " SELECTED_STORAGE
STORAGE=${SELECTED_STORAGE:-$STORAGE}

BRIDGE="vmbr0"

echo -e "\n${GREEN}📦 Erstelle neuen Proxmox LXC Container ID $CTID ($HOSTNAME)...${NC}"

# Download Debian 12 Template if needed
TEMPLATE_STORAGE=$(pvesm status -content vztmpl | awk 'NR==2 {print $1}')
TEMPLATE_STORAGE=${TEMPLATE_STORAGE:-local}

pveam update >/dev/null 2>&1 || true
TEMPLATE=$(pveam available -section system | grep "debian-12-standard" | head -n1 | awk '{print $2}')
if [ -z "$TEMPLATE" ]; then
  TEMPLATE="debian-12-standard_12.2-1_amd64.tar.zst"
fi

if ! pveam list $TEMPLATE_STORAGE | grep -q "$TEMPLATE"; then
  echo -e "${GREEN}📥 Lade Debian 12 CT-Template herunter...${NC}"
  pveam download $TEMPLATE_STORAGE $TEMPLATE
fi

TEMPLATE_PATH="$TEMPLATE_STORAGE:vztmpl/$TEMPLATE"

# Create Container with Docker Nesting & keyctl enabled
pct create $CTID $TEMPLATE_PATH \
  -hostname $HOSTNAME \
  -cores $CORES \
  -memory $RAM \
  -swap 512 \
  -ostype debian \
  -storage $STORAGE \
  -rootfs $STORAGE:$DISK \
  -net0 name=eth0,bridge=$BRIDGE,ip=dhcp \
  -features nesting=1,keyctl=1 \
  -unprivileged 1 \
  -onboot 1

echo -e "${GREEN}⚡ Starte neuen LXC Container CT $CTID...${NC}"
pct start $CTID

# Wait for IP address
echo -e "${GREEN}⏳ Warte auf IP-Adresse vom Router (DHCP)...${NC}"
sleep 5

# Execute Installation inside LXC
echo -e "${GREEN}🚀 Führe Anwendungs-Installation im Container aus...${NC}"
pct exec $CTID -- bash -c "
  echo 'nameserver 1.1.1.1' > /etc/resolv.conf
  apt-get update -qq && apt-get install -y -qq curl wget git ca-certificates >/dev/null 2>&1
  mkdir -p /opt/versicherungsmanager
  cd /opt/versicherungsmanager
  git clone https://github.com/KaelanTesseract/Noxus-Policy.git . 2>/dev/null || true
  curl -fsSL https://get.docker.com | sh
  apt-get install -y -qq docker-compose-plugin >/dev/null 2>&1
  chmod +x install.sh update.sh 2>/dev/null || true
  ln -sf /opt/versicherungsmanager/update.sh /usr/local/bin/update
  ln -sf /opt/versicherungsmanager/update.sh /usr/local/bin/policy-update
  docker compose up -d --build
"

CONTAINER_IP=$(pct exec $CTID -- hostname -I | awk '{print $1}')

echo -e "\n${GREEN}========================================================================${NC}"
echo -e "${CYAN}🎉 Proxmox LXC Container $CTID ($HOSTNAME) wurde erfolgreich erstellt!${NC}"
echo -e "${GREEN}========================================================================${NC}"
echo -e "🌐 **Web-Interface aufrufen:**"
echo -e "   👉 ${YELLOW}http://${CONTAINER_IP}:3000${NC}\n"
echo -e "⚙️  **Container Details:**"
echo -e "   • CT ID: ${CYAN}$CTID${NC}"
echo -e "   • RAM: ${CYAN}${RAM} MB${NC} | Cores: ${CYAN}${CORES}${NC} | Disk: ${CYAN}${DISK} GB${NC}"
echo -e "   • IP-Adresse: ${CYAN}${CONTAINER_IP}${NC}"
echo -e "🔄 **Updates in Zukunft:**"
echo -e "   Einfach im Container-Terminal den Befehl 'update' eingeben!"
echo -e "${GREEN}========================================================================${NC}\n"
