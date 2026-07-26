# 🛡️ Noxus Policy — KI-gestützte Dokumentenanalyse & Versicherungsmanager

<p align="center">
  <img src="frontend/public/logo.png" alt="Noxus Policy Logo" width="120" />
</p>

<p align="center">
  <b>Moderne, selbsgehostete Open-Source Plattform zur automatischen Analyse, Verwaltung und Fristen-Überwachung von Versicherungspolicen.</b><br>
  <i>100% Datenschutzkonform • Lokale KI (Qwen2.5-1.5B) • Proxmox LXC 1-Klick Installation</i>
</p>

<p align="center">
  <a href="#-proxmox-ve--linux-1-klick-installation"><img src="https://img.shields.io/badge/Proxmox_VE-Helper_Script-orange.svg?style=for-the-badge&logo=proxmox" alt="Proxmox Script"></a>
  <a href="#-tech-stack"><img src="https://img.shields.io/badge/Docker-Ready-2496ED.svg?style=for-the-badge&logo=docker" alt="Docker"></a>
  <a href="#-tech-stack"><img src="https://img.shields.io/badge/Next.js_16-Turbopack-black.svg?style=for-the-badge&logo=next.js" alt="Next.js"></a>
  <a href="#-tech-stack"><img src="https://img.shields.io/badge/FastAPI-Python-009688.svg?style=for-the-badge&logo=fastapi" alt="FastAPI"></a>
  <a href="#-lokale-ki-engine-qwen25-15b"><img src="https://img.shields.io/badge/Local_AI-Qwen2.5_1.5B-purple.svg?style=for-the-badge" alt="Local AI"></a>
</p>

---

## 🚀 Proxmox VE & Linux 1-Klick Installation

Noxus Policy lässt sich in Sekunden auf jedem **Proxmox VE Server** oder **Linux LXC/Debian/Ubuntu** installieren.

### 🌟 Option A: Proxmox VE Host 1-Klick Erstellung (Erstellt neuen LXC Container)
Führe diesen Befehl in der **Proxmox VE Node Shell** (Host-Ebene) aus:

```bash
bash -c "$(wget -qLO - https://raw.githubusercontent.com/KaelanTesseract/Noxus-Policy/main/proxmox-install.sh)"
```

### ⚡ Option B: Installation in einem bestehenden Linux / LXC Container
Führe diesen Befehl im **Terminal deines bestehenden Containers/Servers** aus:

```bash
bash -c "$(wget -qLO - https://raw.githubusercontent.com/KaelanTesseract/Noxus-Policy/main/install.sh)"
```

---

## 🔄 1-Klick Auto-Update (mit Live-Ladebalken & Auto-Backup)

Um das System jederzeit auf den neuesten Stand zu bringen, tippe im Container-Terminal einfach folgenden Befehl ein:

```bash
update
```

Das Skript erstellt **automatisch ein Vorab-Sicherheitsbackup** der Datenbank im Ordner `/opt/versicherungsmanager/backups/`, führt einen sauberen Code-Rebuild aus und zeigt dir den Fortschritt in einem **interaktiven Ladebalken**:

```text
[█████████████████░░░░░░░░░░░░]  55% | 3/5: Lade neueste Version herunter...
```

---

## ✨ Hauptfunktionen

### 🤖 1. Lokale KI-Engine (Qwen2.5-1.5B via Llama-cpp)
* **100% Lokal & Privat:** Kein Versenden vertraulicher Versicherungsdokumente an externe Cloud-APIs (wie OpenAI oder Google). Alle Analysen laufen lokal auf deinem Server.
* **Intelligente Datensatz-Erkennung:** Automatische Extraktion von *Versicherungsgesellschaft, Polizzen-Nummer, Kündigungsfrist, Ablaufdatum, Beiträgen & Zahlungsintervallen*.
* **Semantische Leistungs-Analyse:** Auswertung komplexer Deckungsbausteine als saubere Nomen-Stichpunkte in Klammern.

### ⚡ 2. Dual-Engine (KI oder Klassisches OCR) & Neutrales Branding
* **Admin-Toggle in den Einstellungen:** Switsche beliebig zwischen KI-Analyse und superschneller klassischer OCR.
* **Dynamisches Branding:** Bei deaktivierter KI werden sämtliche `[AI]`-Badges und KI-Erwähnungen in der gesamten Oberfläche neutralisiert.

### 🏢 3. Universelle DACH-Abdeckung (70+ Versicherer)
* **Alle großen & regionalen Anbieter:** Allianz, HUK-COBURG, HUK24, AXA, ERGO, Generali, Provinzial, SV Sparkassenversicherung, Haftpflichtkasse, Barmenia, Debeka, R+V, Signal Iduna, Helvetia, Wiener Städtische u.v.m.
* **Sämtliche Versicherungssparten:** Kfz, Privathaftpflicht, Hausrat, Wohngebäude, Berufsunfähigkeit (BU), Rechtsschutz, Zahnzusatz, Krankenkasse, Tierhalter- & Reiseversicherungen.

### 🎨 4. 6 Wunderschöne Design-Themen & Akzentfarben
Jeder Benutzer kann unter **Einstellungen ➔ Design & Erscheinungsbild** sein persönliches Layout wählen:
* ☀️ **Klassisch Business (Hell):** Strahlend helle Oberfläche mit weißen Karten & klaren Kontrasten.
* 🌙 **Dark Neon Glass (Standard):** Modernes dunkles Glasmorphismus-Design mit Neoneffekten.
* 🌾 **Skandinavisch Warm (Soft):** Beruhigender Creme-Ton mit natürlicher Ästhetik.
* 🏙️ **Executive Slate (Dunkel-Blau):** Elegantes Nachtblau-Silber für ruhiges Arbeiten.
* 🍃 **Mint Frisch (Hell):** Erfrischendes helles Design mit Minz- & Teal-Nuancen.
* ⚡ **Cyberpunk Neon (Gamer):** Futuristisches tiefes Schwarz mit Violett-Bordüren.

---

## 💻 Empfohlene Hardware-Ressourcen

| Komponente | Minimum (OCR ohne KI) | Empfohlen (mit lokaler KI) |
| :--- | :--- | :--- |
| **Prozessor (CPU)** | 2 Kerne | **4 Kerne** (mit AVX2) |
| **Arbeitsspeicher (RAM)** | 2 GB RAM | **4 GB RAM** (Modell benötigt ~1,2 GB) |
| **Festplatte (Disk)** | 5 GB SSD | **16 GB SSD** |

---

## 🛠️ Tech Stack

* **Frontend:** Next.js 16 (App Router, Turbopack), React 19, TailwindCSS, Lucide Icons.
* **Backend:** Python 3.11, FastAPI, SQLAlchemy (SQLite3), PyPDF, Llama-cpp-python.
* **Deployment:** Docker, Docker Compose, Proxmox VE Helper Scripts (LXC).

---

## 📝 Lizenz & Copyright

Copyright (c) 2026 **Dennis Guse** ([KaelanTesseract](https://github.com/KaelanTesseract))

Dieses Projekt ist Open-Source-Software und steht unter der **[MIT Lizenz](LICENSE)**.

### 📚 Drittanbieter-Bibliotheken & Open-Source Attributierung
* **Frontend:** Next.js (MIT), React (MIT), TailwindCSS (MIT), Lucide Icons (ISC).
* **Backend:** FastAPI (MIT), Uvicorn (BSD), SQLAlchemy (MIT), PyPDF (BSD), Llama-cpp-python (MIT).
* **KI-Modell:** Qwen2.5 1.5B Instruct von Alibaba Cloud (Apache 2.0 License - Open Commercial Use).

