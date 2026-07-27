# 🛡️ Noxus Policy — Versicherungsmanager mit KI-gestützter Dokumentenanalyse

<p align="center">
  <img src="https://github.com/KaelanTesseract/Noxus-Policy/blob/fcd19a9946ac18d64a184fe4778384bd5b48a888/logo.png" alt="Noxus Policy Logo" width="140" />
</p>

<p align="center">
  <b>Moderne, selbstgehostete Open-Source Plattform zur automatischen Analyse, Verwaltung und Fristen-Überwachung von Versicherungspolicen.</b><br>
  <i>100% Datenschutzkonform • Lokale KI (Qwen2.5-1.5B) • Proxmox LXC 1-Klick Installation</i>
</p>

<p align="center">
  <a href="#-proxmox-ve--linux-1-klick-installation"><img src="https://img.shields.io/badge/Proxmox_VE-Helper_Script-orange.svg?style=for-the-badge&logo=proxmox" alt="Proxmox Script"></a>
  <a href="#-tech-stack"><img src="https://img.shields.io/badge/Docker-Ready-2496ED.svg?style=for-the-badge&logo=docker" alt="Docker"></a>
  <a href="#-tech-stack"><img src="https://img.shields.io/badge/Next.js_16-v1.0.7-black.svg?style=for-the-badge&logo=next.js" alt="Next.js"></a>
  <a href="#-tech-stack"><img src="https://img.shields.io/badge/FastAPI-Python-009688.svg?style=for-the-badge&logo=fastapi" alt="FastAPI"></a>
  <a href="#-lokale-ki-engine-qwen25-15b"><img src="https://img.shields.io/badge/Local_AI-Qwen2.5_1.5B-purple.svg?style=for-the-badge" alt="Local AI"></a>
</p>

---

## 🔑 Standard Admin-Zugangsdaten (Erst-Login)

Nach der Installation ist das System mit folgenden Standard-Zugangsdaten erreichbar:

| Parameter | Standard-Wert |
| :--- | :--- |
| **Benutzername / E-Mail** | `admin` *(oder `Admin`)* |
| **Passwort** | `admin` |

> 🔒 **Sicherheitshinweis:** Beim allerersten Anmelden wirst du aus Sicherheitsgründen automatisch auf die Einrichtungsseite geleitet, um dein persönliches Administrator-Passwort festzulegen.

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

### 👥 1. Benutzer- & Rollenverwaltung
* **Erster Admin-Setup (`/admin-setup`):** Sichere Ersteinrichtung mit erzwungener Passwort-Änderung für den ersten Administrator.
* **Benutzerregistrierung & Admin-Panel:** Admins können neue Benutzer anlegen, Passwörter zurücksetzen und Systemeinstellungen verwalten.
* **Automatische Session-Abmeldung (`/session-expired`):** Läuft eine Sitzung ab (401 Unauthorized), wird der Nutzer automatisch zum Login zurückgeführt.

### 📈 2. Beitragsanpassungs-Tracker & Preis-Historie
* **Automatische KI-/OCR-Erkennung:** Liest Preisanpassungen aus Beitragsrechnungen automatisch aus.
* **Interaktives SVG-Balkendiagramm:** Visualisiert die Preisentwicklung über die Jahre mit prozentualen Trend-Badges (z. B. `📈 +12.5%` Erhöhung oder `📉 -5.0%` Senkung).

### 🚗 3. KFZ-Sondertarifklassen
* **Tarifklassen-Erkennung:** Automatische Extraktion & Anzeige von **Schadenfreiheitsklasse (SF-Klasse)**, **Regionalklasse** und **Typklasse** in der Dashboard-Übersicht und Detailansicht.

### ⏸️ 4. Ruhendstellung & Beitragsfreistellung
* **Vertragspausierung:** Verträge können ruhend bzw. beitragsfrei gestellt werden (KFZ, Kranken, BU, Leben, Unfall, Rechtsschutz).
* **0 € Berechnung:** Ruhende Verträge fließen automatisch mit 0 € in die aktiven Jahresausgaben ein und werden optisch als `⏸️ Ruhend (0 €)` markiert.

### ✍️ 5. Sonderkündigungsrechts-Assistent & Generator
* **Rechtlich fundierte Kündigungsschreiben:** Auswahl zwischen Ordentlicher Kündigung zum Vertragsende (§ 11 VVG), Sonderkündigung wegen Beitragserhöhung (§ 40 VVG), Sonderkündigung nach Schadensfall (§ 92 VVG) und Risikowegfall (§ 80 VVG).
* **Automatischer DIN A4 PDF-Druck:** Erzeugt juristisch einwandfreie Kündigungsschreiben inkl. SEPA-Widerruf, Bestätigungsanforderung und DSGVO-Löschklauseln zum Drucken oder PDF-Speichern.

### 📅 6. Live-Kalender-Abonnement (WebCal) & iCal-Export
* **Live WebCal-Sync:** Einmalig per URL in Smartphone (Apple Kalender, Google Kalender, Outlook) einbinden – Kündigungsfristen aktualisieren sich von selbst mit 14d & 7d Push-Erinnerungen.
* **Admin-Toggle & Server-Hinweise:** WebCal-Abonnement im Admin-Panel aktivierbar/deaktivierbar (inkl. Erreichbarkeitshinweisen für Nginx/Domain).
* **1-Klick .ics-Downloads:** Einzel- und Gesamt-Download aller Kündigungsfristen als `.ics`-Datei für Offline-Nutzung.

### 📑 7. Steuererklärungs- & Haushalts-PDF-Export
* **Klassifizierung nach § 10 / § 9 EStG:** Automatisches Sortieren in absetzbare Vorsorgeaufwendungen, Werbungskosten und Sachversicherungen.
* **Jahressummen-Berechnung & PDF-Druck:** 1-Klick-Generierung einer gebündelten Jahresübersicht für das Finanzamt oder den Steuerberater sowie CSV-Export (WISO / Elster / Excel).

### 📑 8. Dynamische Tab-Navigation auf der Detailseite
* **Strukturierte Vertragsansicht:** Aufteilung in 5 übersichtliche Tabs (`📋 Stammdaten & Leistungen`, `📈 Beitragsentwicklung`, `📄 Dokumente`, `💥 Schadensfälle`, `📝 Notizen & Memos`).

### 💥 9. Schadensfälle- & Melde-Historie / Notizen & Memos
* **Schadensfall-Tracker:** Erfasse Schadensfälle (Datum, Schadensnummer, Höhe in €, Status: *In Bearbeitung*, *Reguliert*, *Abgelehnt*).
* **Notizen- & Memo-Funktion:** Hinterlege Freitext-Notizen zu jedem Vertrag (z. B. Selbstbeteiligung, Hotline, Ansprechpartner).

### 🎨 10. 6 Design-Themen & monochrome Aktions-Icons
* **6 Wunderschöne Themes:** Dunkel Neon, Klassisch Business Hell, Skandinavisch Warm, Executive Slate, Mint Frisch, Cyberpunk.
* **Monochrome Icon-Buttons:** Schlanke, hochkontrastreiche Aktions-Buttons (`Eye`, `RefreshCw`, `Pencil`, `Trash2`) in der Dokumentenliste.

### 📊 11. Visuelles Kosten- & Sparten-Diagramm / Suche & Sortierung
* **Interaktives Balkendiagramm:** Ausgaben nach Kategorie (Kfz, Privathaftpflicht, Hausrat, Rechtsschutz).
* **Echtzeit-Suchleiste & Sortierung:** Suche nach Name, Gesellschaft oder Scheinnummer sowie Sortierung nach Kündigungsfrist, Kosten oder Alphabet.

### 🤖 12. Lokale KI-Engine (Qwen2.5-1.5B via Llama-cpp)
* **100% Lokal & Privat:** Kein Versenden vertraulicher Versicherungsdokumente an externe Cloud-APIs.
* **Intelligente Datensatz-Erkennung:** Extraktion von Gesellschaft, Polizzen-Nummer, Fristen, KFZ-Klassen, Beiträgen & Deckungsbausteinen.
* **Dual-Engine OCR:** Umschaltbar zwischen lokaler KI und superschneller klassischer OCR-Erkennung.

### 💾 13. Auto-Backup & Wiederherstellungs-System
* **Vorab-Sicherheitsbackup:** Automatische Datenbank-Sicherung bei jedem `update` im Ordner `/opt/versicherungsmanager/backups/`.
* **Manuelle & Geplante Sicherungen:** 1-Klick-Backups und Wiederherstellung über die Web-Oberfläche.

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
