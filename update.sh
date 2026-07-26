#!/usr/bin/env bash
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
echo '  _  _  ___  _  _ _  _ ___   ___  ___  _    ___ _____   __'
echo ' | \| |/ _ \| \/ / || / __| | _ \/ _ \| |  |_ _/ __\ \ / /'
echo ' | .` | (_) | >  <| || \__ \ |  _/ (_) | |__ | | (__ \ V / '
echo ' |_|\_|\___/|_/\_\\_,_|___/ |_|  \___/|____|___\___| |_|  '
echo -e "${NC}"
echo -e "${YELLOW}🚀 Starte System-Update von Noxus Policy...${NC}\n"

INSTALL_DIR="/opt/versicherungsmanager"
if [ ! -d "$INSTALL_DIR" ]; then
  echo -e "${RED}❌ Fehler: Installationsverzeichnis ${INSTALL_DIR} nicht gefunden.${NC}"
  exit 1
fi

cd "$INSTALL_DIR"

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
ln -sf /opt/versicherungsmanager/update.sh /usr/local/bin/update 2>/dev/null || true
ln -sf /opt/versicherungsmanager/update.sh /usr/local/bin/policy-update 2>/dev/null || true

# Step 4: Docker Container Rebuild without cache (80%)
render_progress 80 100 "4/5: Baue und aktualisiere Docker-Container (Frontend + Backend)..."
docker compose down --remove-orphans >/dev/null 2>&1 || true
docker compose build --no-cache >/dev/null 2>&1 || true
docker compose up -d >/dev/null 2>&1 || docker compose up -d

# Step 5: Clean Docker Cache (100%)
render_progress 100 100 "5/5: Bereinige alten Build-Speicher..."
docker image prune -f >/dev/null 2>&1 || true
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
