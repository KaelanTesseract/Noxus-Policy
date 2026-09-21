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
  <a href="#-tech-stack"><img src="https://img.shields.io/badge/Next.js_16-v0.2.5--beta-black.svg?style=for-the-badge&logo=next.js" alt="Next.js"></a>
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
- [🔒 Sicherheit & HTTPS (Reverse Proxy)](#-sicherheit--https-reverse-proxy)
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

Es gibt bewusst **kein festes Standard-Passwort** mehr: Beim ersten Start legt das Backend das Konto `Admin` mit einem zufälligen Einmal-Passwort an und gibt es im Log aus. Das Installations-Skript zeigt es dir am Ende direkt an. Später findest du es so:

```bash
cd /opt/versicherungsmanager && docker compose logs backend | grep INITIAL_ADMIN_PASSWORD
```

| Parameter | Wert |
| :--- | :--- |
| **Benutzername** | `Admin` |
| **Passwort** | zufälliges Einmal-Passwort aus dem Log (siehe oben) |

> 🔒 **Sicherheitshinweis:** Beim allerersten Anmelden wirst du automatisch auf die Einrichtungsseite geleitet, um deine eigene E-Mail und dein persönliches Administrator-Passwort festzulegen.
>
> **Passwort vergessen / Log nicht mehr auffindbar?** Auf dem Server ein neues Einmal-Passwort erzeugen (funktioniert nur mit Zugriff auf den Container, es gibt keinen Netzwerk-Zugang dafür):
> ```bash
> cd /opt/versicherungsmanager && docker compose exec backend python reset_admin.py
> ```

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

## 🔒 Sicherheit & HTTPS (Reverse Proxy)

Noxus Policy verarbeitet sensible personenbezogene Daten (Versicherungsverträge, Beiträge, Dokumente). Ein paar Punkte solltest du bei jeder Installation beachten:

### HTTPS ist Pflicht, sobald der Server erreichbar ist

`docker-compose.yml` liefert die App standardmäßig nur über **reines HTTP** aus. Nach außen ist ausschließlich das Frontend auf **Port 3000** erreichbar; das Backend (Port 8000) hört nur auf `127.0.0.1` und wird vom Frontend intern angesprochen. Das ist für einen Test auf `localhost` unproblematisch, aber sobald der Server im LAN oder gar aus dem Internet erreichbar ist, gehen Login-Zugangsdaten und das Sitzungs-Token bei jeder Anfrage unverschlüsselt über die Leitung – für jeden mitlesbar, der Zugriff auf den Netzwerkpfad hat.

**Richte deshalb immer einen Reverse Proxy mit echtem TLS-Zertifikat vor die App**, z. B. mit Nginx + [Certbot](https://certbot.eff.org/) (Let's Encrypt):

```nginx
# /etc/nginx/sites-available/noxus-policy
server {
    listen 443 ssl http2;
    server_name deine-domain.de;

    ssl_certificate     /etc/letsencrypt/live/deine-domain.de/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/deine-domain.de/privkey.pem;

    location / {
        proxy_pass http://127.0.0.1:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}

server {
    listen 80;
    server_name deine-domain.de;
    return 301 https://$host$request_uri;
}
```

Zertifikat besorgen (einmalig) und automatische Erneuerung einrichten:

```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d deine-domain.de
```

Der Frontend-Container selbst muss dafür nicht verändert werden – Nginx läuft als eigener Dienst auf dem Host (oder in einem eigenen Container) und leitet Anfragen intern an `127.0.0.1:3000` weiter. Alternativen mit ähnlich wenig Aufwand: [Caddy](https://caddyserver.com/) (holt Let's-Encrypt-Zertifikate automatisch, ganz ohne Certbot) oder ein [Cloudflare Tunnel](https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/), falls der Server keine öffentliche IP hat.

### Reverse Proxy und Anmelde-Begrenzung (`TRUSTED_PROXY_HOPS`)

Das Backend begrenzt fehlgeschlagene Anmeldungen pro Konto und pro Client-IP. Steht ein Reverse Proxy davor, sieht das Backend sonst nur dessen Adresse. Trage deshalb in der `.env`-Datei neben `docker-compose.yml` ein, wie viele Proxys vor der App laufen (ein Nginx Proxy Manager = `1`) und starte neu:

```bash
echo "TRUSTED_PROXY_HOPS=1" >> .env && docker compose up -d
```

Ohne Proxy (direkter Zugriff auf Port 3000) den Wert bei `0` lassen. Ein falscher Wert schwächt nur das IP-Limit ab, das Limit pro Konto bleibt in jedem Fall aktiv.

### Registrierung abschalten

Ist die Instanz aus dem Internet erreichbar, kann sich zunächst jeder registrieren. Als Administrator kannst du die Selbstregistrierung unter *Einstellungen → Systemeinstellungen* ausschalten. Bestehende Konten bleiben unberührt; für weitere Konten schaltest du sie kurz wieder ein.

### SECRET_KEY

Jedes Login-Token wird mit dem Wert der Umgebungsvariable `SECRET_KEY` signiert. `install.sh`, `proxmox-install.sh` und `update.sh` erzeugen dafür automatisch einen zufälligen, 64-stelligen Schlüssel in einer lokalen `.env`-Datei neben `docker-compose.yml` (diese Datei ist in `.gitignore` und wird nie ins Repository übernommen). Startest du den Stack manuell per `docker compose up` ohne eines dieser Skripte, musst du diese `.env`-Datei selbst anlegen:

```bash
echo "SECRET_KEY=$(openssl rand -hex 32)" > .env
```

Das Backend verweigert absichtlich den Start, wenn `SECRET_KEY` fehlt oder einer der bekannten unsicheren Standardwerte ist.

**Sichere die `.env`-Datei getrennt von den Backups.** Aus dem `SECRET_KEY` wird auch der Schlüssel abgeleitet, mit dem gespeicherte Passwörter (SMTP, automatisches Backup, GitHub-Token) in der Datenbank verschlüsselt sind. Geht der Schlüssel verloren oder ändert er sich, sind diese Passwörter nicht mehr lesbar (das Backend meldet das beim Start im Log und beim Wiederherstellen eines Backups einer anderen Instanz) und müssen neu eingegeben werden; außerdem müssen sich alle Benutzer neu anmelden. Die Dokumente und Verträge selbst sind davon nicht betroffen.

### Sitzungsdauer

Eine Anmeldung gilt `ACCESS_TOKEN_EXPIRE_MINUTES` Minuten (Standard **15**) ab der letzten Aktivität und verlängert sich automatisch, solange du die Seite benutzt. Nach spätestens `SESSION_MAX_HOURS` Stunden (Standard **12**) seit der Anmeldung musst du dich unabhängig davon neu anmelden. Beide Werte lassen sich in der `.env`-Datei ändern.

### Uploads, Nginx und Größenlimits

Ein Dokument darf höchstens 15 MB groß sein, Backup-Dateien beim Wiederherstellen höchstens 512 MB (entpackt höchstens 2 GB), alle anderen Anfragen höchstens 2 MB. Größere Anfragen werden schon vor der Verarbeitung abgewiesen. Steht ein Nginx davor, muss er Uploads dieser Größe durchlassen – bei Fehler 413 beim Hochladen trage im Nginx (bzw. im Nginx Proxy Manager unter *Advanced*) `client_max_body_size 600m;` ein.

### Weitere Empfehlungen

- **Automatische Backups verschlüsseln**: Lege unter *Einstellungen → Systemeinstellungen → Automatische Backups* ein eigenes Passwort fest, statt das beim ersten Lauf automatisch generierte zu verwenden – notiere es dir an einem sicheren Ort, ohne dieses Passwort ist ein Backup nicht wiederherstellbar.
- **API-Dokumentation (`/docs`, `/redoc`) bleibt standardmäßig deaktiviert.** Nur falls du sie lokal zur Entwicklung brauchst, aktiviere sie gezielt über `ENABLE_API_DOCS=true` in der `.env`-Datei – nicht auf einem von außen erreichbaren Server.
- **2-Faktor-Authentifizierung einschalten**: Unter *Einstellungen → 2-Faktor-Authentifizierung* kann jeder Benutzer einen Authenticator-App-Code (TOTP, z. B. Aegis, 2FAS, Google Authenticator) als zweiten Faktor verlangen. Besonders für Administratoren empfohlen: Ein gestohlenes Passwort reicht dann nicht mehr. Die Wiederherstellungscodes werden nur einmal angezeigt – bewahre sie getrennt auf. Hat jemand Handy *und* Codes verloren, kann ein Administrator die 2FA in der Benutzerverwaltung zurücksetzen; für den Admin-Zugang selbst setzt `reset_admin.py` (siehe oben) auch die 2FA zurück.
- **Sicherheitsprotokoll prüfen**: Administratoren sehen unter *Systemeinstellungen → Sicherheitsprotokoll* Anmeldungen, Fehlversuche (samt Adresse) und Änderungen an Konten/Einstellungen der letzten 12 Monate. Viele Fehlversuche von einer Adresse deuten auf einen Angriff hin.
- **Starke Passwörter verwenden**: Das System verlangt mindestens 8 (höchstens 72 Bytes) Zeichen und weist bekannte Allerwelts-Passwörter („Passwort123“, „qwertz“ …) sowie Passwörter aus der eigenen E-Mail-Adresse ab. Backup-Passwörter brauchen mindestens 12 Zeichen. Echte Sicherheit hängt weiterhin von der Qualität des gewählten Passworts ab.
- **Festplatte verschlüsseln**: Verträge und Dokumente liegen unverschlüsselt im Dateisystem des Servers (nur Backups und gespeicherte Passwörter sind verschlüsselt). Wer physischen Zugriff auf den Server, den Proxmox-Host oder dessen Snapshots hat, kommt an alles heran – setze deshalb auf Datenträgerverschlüsselung (LUKS/ZFS-Verschlüsselung) und schütze Proxmox-Backups.
- **Kalender-Abo-Link vertraulich behandeln**: Die WebCal-Adresse enthält ein geheimes Token (Kalender-Apps können keine Anmeldung senden). Wer den Link kennt, sieht deine Kündigungsfristen. Bei Verdacht erneuerst du ihn unter *Einstellungen → Kalender* (der alte Link wird ungültig).
- **Versicherer-Logos**: Die Logos lädt der Server (nicht dein Browser) über den Google-Favicon-Dienst; Google erfährt dabei nur die Domain des Versicherers und die Adresse des Servers, nie die Adresse der Benutzer. Wer keinerlei externe Anfrage möchte, setzt `DISABLE_LOGO_LOOKUP=true` im Frontend-Container – es erscheinen dann Initialen.
- **Löschen von Konten**: Benutzer können ihr Konto unter *Einstellungen → Konto löschen* selbst entfernen (Administratoren löscht ein anderer Administrator). Dabei werden Verträge, Schadensfälle, Dokumente und Posteingang samt Dateien gelöscht. Bereits erstellte Server-Backups enthalten die Daten weiterhin, bis sie gelöscht werden.
- **Container laufen ohne Root-Rechte.** Das Frontend läuft als Benutzer `node`. Das Backend startet kurz als Root, übergibt die Datenordner (`backend/data`, `backend/documents`, `backend/models`) an den Benutzer `app` und läuft danach unprivilegiert; alle unnötigen Linux-Capabilities sind entzogen. Sollte das auf einem ungewöhnlichen Speicher-Setup Probleme machen, fällt der Start mit einer Warnung im Log auf Root zurück; erzwingen lässt sich das mit `RUN_AS_ROOT=1` in der `environment`-Liste des Backends.
- **Die KI-Modelldatei wird geprüft.** Das Sprachmodell wird von einem festen Hugging-Face-Stand geladen und gegen eine SHA-256-Prüfsumme verglichen; eine abweichende Datei wird verworfen und die KI fällt auf die klassische Erkennung zurück.

---

## ✨ Hauptfunktionen

### 🔐 Sicherheit, Benutzer- & Zugriffsverwaltung
* **Sicherer Erst-Login (`/admin-setup`):** Erzwungene Passwort-Änderung für den ersten Administrator, danach reguläre JWT-Authentifizierung im httpOnly-Cookie (15 Minuten Inaktivitäts-Timeout mit gleitender Verlängerung, bcrypt-Passwort-Hashing).
* **2-Faktor-Authentifizierung (TOTP) & Sicherheitsprotokoll:** Optionaler zweiter Faktor mit Wiederherstellungscodes; ein Protokoll für Anmeldungen, Fehlversuche und Admin-Aktionen; Konto-Selbstlöschung inkl. aller Dateien.
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
