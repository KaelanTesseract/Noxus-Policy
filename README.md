<h1 align="center">Noxus Policy</h1>
<h3 align="center">Versicherungsmanager mit KI-gestützter Dokumentenanalyse</h3>

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
  <a href="#-tech-stack"><img src="https://img.shields.io/badge/Next.js_16-v0.2.4--beta-black.svg?style=for-the-badge&logo=next.js" alt="Next.js"></a>
  <a href="#-tech-stack"><img src="https://img.shields.io/badge/FastAPI-Python-009688.svg?style=for-the-badge&logo=fastapi" alt="FastAPI"></a>
  <a href="#-ki-gestützte-dokumentenanalyse--lernsystem"><img src="https://img.shields.io/badge/Local_AI-Qwen2.5_1.5B-purple.svg?style=for-the-badge" alt="Local AI"></a>
</p>

> [!WARNING]
> **Hinweis zur KI- & OCR-Texterkennung (Aktive Testphase):**
> Die automatische Texterkennung und Dokumentenanalyse befindet sich derzeit in einer **kontinuierlichen Erprobungs- & Testphase**. Je nach Qualität, Formatierung, Scan-Auflösung oder Layout der hochgeladenen PDF-Dokumente kann es vereinzelt zu Abweichungen oder Fehlern bei der Datenerkennung kommen. Bitte überprüfe ausgelesene Vertragsdaten, Kündigungsfristen und Beiträge stets sorgfältig auf ihre Richtigkeit.

---

## 📑 Inhaltsverzeichnis

- [🔑 Standard Admin-Zugangsdaten](#-standard-admin-zugangsdaten-erst-login)
- [🚀 Installation (Proxmox VE & Linux)](#-proxmox-ve--linux-1-klick-installation)
- [🔄 Auto-Update](#-1-klick-auto-update-mit-live-ladebalken--auto-backup)
- [✨ Hauptfunktionen](#-hauptfunktionen)
  - [🔐 Sicherheit, Benutzer- & Zugriffsverwaltung](#-sicherheit-benutzer---zugriffsverwaltung)
  - [🤖 KI-gestützte Dokumentenanalyse & Lernsystem](#-ki-gestützte-dokumentenanalyse--lernsystem)
  - [🛡️ Datenschutz-Garantien beim Dokumenten-Upload](#️-datenschutz-garantien-beim-dokumenten-upload)
  - [📈 Verträge, Kosten & Fristen im Blick](#-verträge-kosten--fristen-im-blick)
  - [📊 Dashboard, Posteingang & Auswertung](#-dashboard-posteingang--auswertung)
  - [🎨 Design & Nutzererlebnis](#-design--nutzererlebnis)
  - [💾 Betrieb, Backup & Performance](#-betrieb-backup--performance)
- [💻 Empfohlene Hardware-Ressourcen](#-empfohlene-hardware-ressourcen)
- [🛠️ Tech Stack](#️-tech-stack)
- [📝 Lizenz & Copyright](#-lizenz--copyright)

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

Das Skript erstellt **automatisch ein Vorab-Sicherheitsbackup** der Datenbank, führt einen sauberen Rebuild aus und zeigt dir den Fortschritt in einem **aufgeräumten Live-Fortschrittsbalken**:

```text
[██████████████████████████████] 100% | 5/5: Update erfolgreich abgeschlossen!
```

---

## ✨ Hauptfunktionen

### 🔐 Sicherheit, Benutzer- & Zugriffsverwaltung
* **Sicherer Erst-Login (`/admin-setup`):** Erzwungene Passwort-Änderung für den ersten Administrator, danach reguläre JWT-Authentifizierung (7 Tage Gültigkeit, bcrypt-Passwort-Hashing).
* **Rollen- & Benutzerverwaltung:** Admins legen Benutzer an, setzen Passwörter zurück und verwalten Systemeinstellungen zentral im Admin-Panel.
* **Konsequente Zugriffskontrolle:** Jeder Dokumenten- und Versicherungs-Endpunkt prüft die Eigentümerschaft (`owner_id`) — kein Zugriff auf fremde Unterlagen, auch nicht über direkt aufgerufene Links.
* **Automatische Session-Abmeldung (`/session-expired`):** Läuft eine Sitzung ab (401 Unauthorized), wird der Nutzer automatisch zum Login zurückgeführt.
* **Passwort-Reset per E-Mail:** Selbstständiger Passwort-Reset über einen admin-konfigurierbaren SMTP-Server; alternativ kann ein Administrator die Reset-Mail direkt aus der Benutzerverwaltung auslösen.

### 🤖 KI-gestützte Dokumentenanalyse & Lernsystem
* **Lokale KI-Engine (Qwen2.5-1.5B via llama.cpp):** 100 % lokale Extraktion von Gesellschaft, Policennummer, Fristen, KFZ-Klassen, Beiträgen & Deckungsbausteinen — vertrauliche Dokumente verlassen den Server nicht.
* **Dual-Engine OCR:** Umschaltbar zwischen lokaler KI und einer schnellen, klassischen Regex-/Keyword-Erkennung als Fallback, inklusive `pytesseract`-Bildtexterkennung für gescannte PDFs.
* **Eine Analyse statt zwei:** Dokumentenvorschau und -speicherung teilen sich dasselbe Analyseergebnis — der frühere doppelte KI-/OCR-Durchlauf pro Upload entfällt.
* **Anonymisiertes Vendor-Pattern-Lernsystem:** Ein Sanitizer (`sanitizer.py`) entfernt vor jedem Lernschritt ausnahmslos Namen, Adressen, IBANs, Policennummern, Kennzeichen und Telefonnummern (Zero-PII-Leak).
* **Community-Musterabgleich per Pull Request:** Standardmäßig **deaktiviert** und pro Instanz vom Administrator aktivierbar (inkl. eigenem GitHub-Token in den Einstellungen). Statt Änderungen automatisch zu veröffentlichen, öffnet bzw. aktualisiert das Backend einen Pull Request — Muster-Updates werden erst nach Review übernommen. Die gelernten, anonymisierten Layout-Muster werden dabei zusätzlich obfuskiert (Base64/XOR) abgelegt.

### 🛡️ Datenschutz-Garantien beim Dokumenten-Upload
* **Namensschutz:** Neue Dokumenten-Uploads überschreiben niemals den Namen einer bestehenden Police.
* **Ruhendstellungs-Garantie:** Der Ruhend-Status (`is_suspended`) und der hinterlegte Grund bleiben bei neuen Uploads unangetastet und lassen sich ausschließlich manuell ändern.
* **Intelligente Informations-Kategorien:** Dokumente vom Typ *Sonstiges*, *Verbraucherinformationen* oder *Kundeninformationen* werden ausschließlich archiviert, ohne Vertragsdaten oder Beiträge zu überschreiben.

### 📈 Verträge, Kosten & Fristen im Blick
* **Beitragsanpassungs-Tracker:** Liest Preisanpassungen automatisch aus Beitragsrechnungen aus und visualisiert die Entwicklung über die Jahre in einem Balkendiagramm mit prozentualen Trend-Badges (z. B. `📈 +12,5 %`).
* **KFZ-Sondertarifklassen:** Automatische Erkennung und Anzeige von Schadenfreiheitsklasse (SF-Klasse), Regionalklasse und Typklasse.
* **Ruhendstellung & Beitragsfreistellung:** Verträge lassen sich pausieren; ruhende Verträge fließen automatisch mit 0 € in die Jahresausgaben ein und werden als `⏸️ Ruhend (0 €)` markiert.
* **Sonderkündigungsrechts-Assistent:** Erstellt rechtlich fundierte, druckfertige Kündigungsschreiben (ordentliche Kündigung § 11 VVG, Sonderkündigung wegen Beitragserhöhung § 40 VVG, nach Schadensfall § 92 VVG oder Risikowegfall § 80 VVG) inklusive SEPA-Widerruf und DSGVO-Löschklausel.
* **Live-Kalender (WebCal) & iCal-Export:** Einmalige Einbindung in Apple-, Google- oder Outlook-Kalender mit automatischen 14- und 7-Tage-Erinnerungen; zusätzlich 1-Klick-`.ics`-Downloads für die Offline-Nutzung.
* **E-Mail-Erinnerungen vor Fristablauf:** Ist ein SMTP-Server hinterlegt, verschickt das System täglich automatisch Erinnerungsmails an Nutzer, die dies in ihrem Profil aktiviert haben — unabhängig vom WebCal-Kanal, der auch ohne SMTP-Konfiguration funktioniert.
* **Steuererklärungs- & Haushalts-PDF-Export:** Klassifizierung nach § 10 / § 9 EStG, automatische Jahressummen-Berechnung sowie CSV-Export (WISO / Elster / Excel).

### 📊 Dashboard, Posteingang & Auswertung
* **Live-Kennzahlen-Kacheln:** Aktive Policen, Gesamtkosten pro Jahr, eine anklickbare Kündigungsfristen-Kachel (zeigt Anzahl & nächste fällige Frist der kommenden 90 Tage) sowie eine anklickbare Posteingang-Kachel mit der aktuellen Zahl noch nicht zugeordneter Dokumente.
* **Posteingang (Inbox):** Zentrale Ablage für hochgeladene Dokumente vor der Zuordnung zu einer Police, inklusive KI-Analyse-Vorschlägen direkt im Posteingang.
* **Visuelles Kosten-Diagramm:** Interaktive Aufschlüsselung der Jahresausgaben nach Versicherungssparte (Kfz, Privathaftpflicht, Hausrat, Rechtsschutz, …).
* **Suche & Sortierung in Echtzeit:** Nach Name, Gesellschaft, Policennummer, Kosten, Kündigungsfrist oder Alphabet.
* **Dynamische Tab-Navigation:** Übersichtliche Detailansicht je Police in 5 Tabs (`📋 Stammdaten & Leistungen`, `📈 Beitragsentwicklung`, `📄 Dokumente`, `💥 Schadensfälle`, `📝 Notizen & Memos`).
* **Schadensfälle & Notizen:** Schadensfall-Tracker (Datum, Schadensnummer, Höhe in €, Status: *In Bearbeitung*, *Reguliert*, *Abgelehnt*) sowie freie Notizen/Memos je Vertrag.

### 🎨 Design & Nutzererlebnis
* **6 durchgestaltete Themes:** Dunkel Neon, Klassisch Business Hell, Skandinavisch Warm, Executive Slate, Mint Frisch, Cyberpunk — jedes mit einem eigens abgestimmten, dezenten Gradient-Hintergrund.
* **Monochrome Vektor-Icons:** Schlanke, hochkontrastreiche Aktions-Icons (`Eye`, `RefreshCw`, `Pencil`, `Trash2`) und KFZ-Badges (`Car`, `MapPin`, `Shield`).
* **Große, browserbreite Dokumentenvorschau:** PDF- und Bildvorschauen öffnen sich in einem großzügigen, authentifiziert geladenen Vorschaufenster.
* **Spürbar kürzere Ladezeiten:** Dashboard und Detailseiten rendern sofort aus einem lokalen Zwischenspeicher und aktualisieren die Daten anschließend im Hintergrund (Stale-while-Revalidate) — merklich schneller nach dem Login und beim Öffnen einer Police.

### 💾 Betrieb, Backup & Performance
* **Verschlüsselte Backups mit Rotation:** Passwortbasiert verschlüsselte (Fernet/AES) Archive aus Datenbank und Dokumenten, automatisch bei jedem `update` sowie nach konfigurierbarem Zeitplan; ältere Backups werden nach Anzahl/Alter automatisch rotiert.
* **Optimierte Datenbankzugriffe:** Indizes auf allen Fremdschlüsseln sowie Eager-Loading (`selectinload`) vermeiden N+1-Abfragen auf stark frequentierten Endpunkten.
* **Schlankes Docker-Image:** Mehrstufiger Docker-Build — die Build-Werkzeuge zur Kompilierung der KI-Engine landen nicht im laufenden Produktions-Image.

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
* **Deployment:** Docker (mehrstufiger Build), Docker Compose, Proxmox VE Helper Scripts (LXC).

---

## 📝 Lizenz & Copyright

Copyright (c) 2026 **Dennis Guse** ([KaelanTesseract](https://github.com/KaelanTesseract))

Dieses Projekt ist Open-Source-Software und steht unter der **[MIT Lizenz](LICENSE)**.

### 📚 Drittanbieter-Bibliotheken & Open-Source Attributierung
* **Frontend:** Next.js (MIT), React (MIT), TailwindCSS (MIT), Lucide Icons (ISC).
* **Backend:** FastAPI (MIT), Uvicorn (BSD), SQLAlchemy (MIT), PyPDF (BSD), Llama-cpp-python (MIT).
* **KI-Modell:** Qwen2.5 1.5B Instruct von Alibaba Cloud (Apache 2.0 License - Open Commercial Use).
