<p align="center">
  <img src="logo.png" alt="Zettelfrieden" width="96" />
</p>

<h1 align="center">Zettelfrieden</h1>

Selbst gehostete Verwaltung für Versicherungsverträge mit lokaler Dokumentenanalyse. Zettelfrieden liest Versicherungsscheine, Beitragsrechnungen und Nachträge aus, trägt Gesellschaft, Policennummer, Beitrag und Fristen in eine Übersicht ein und erinnert rechtzeitig an Kündigungsfristen. Die Dokumente verlassen den Server nicht: Die Texterkennung läuft vollständig lokal (Poppler und Tesseract), ein Sprachmodell oder ein externer Dienst wird nicht verwendet.

Die Oberfläche ist deutsch. Zettelfrieden besteht aus einem Next.js-Frontend und einem FastAPI-Backend und läuft mit Docker Compose, zum Beispiel in einem Proxmox-LXC-Container.

> **Hinweis zur Texterkennung:** Die automatische Dokumentenanalyse wird laufend verbessert und arbeitet nicht fehlerfrei. Je nach Qualität, Layout und Auflösung eines Dokuments können Werte fehlen oder falsch erkannt werden. Prüfe Vertragsdaten, Kündigungsfristen und Beiträge deshalb immer anhand des Originals. Zu jedem ausgelesenen Wert zeigt die App, ob er im Dokument gefunden wurde (mit Seite und Textstelle), nur berechnet wurde (zum Beispiel die Kündigungsfrist) oder unsicher ist.

## Inhalt

- [Installation](#installation)
- [Erster Start](#erster-start)
- [Update](#update)
- [Sicherheit und Betrieb](#sicherheit-und-betrieb)
- [Funktionen](#funktionen)
- [Systemvoraussetzungen](#systemvoraussetzungen)
- [Technik](#technik)
- [Entwicklung](#entwicklung)
- [Lizenz](#lizenz)

## Installation

Zettelfrieden lässt sich auf einem Proxmox-VE-Server oder in jedem Linux-System (Debian, Ubuntu, LXC) installieren.

**Neuer LXC-Container auf einem Proxmox-VE-Host.** In der Shell des Proxmox-Knotens ausführen:

```bash
bash -c "$(wget -qLO - https://raw.githubusercontent.com/KaelanTesseract/Zettelfrieden/main/proxmox-install.sh)"
```

**Bestehender Linux-Server oder Container.** Im Terminal des Systems ausführen:

```bash
bash -c "$(wget -qLO - https://raw.githubusercontent.com/KaelanTesseract/Zettelfrieden/main/install.sh)"
```

Beide Skripte installieren Docker, laden den Quellcode nach `/opt/versicherungsmanager`, erzeugen den `SECRET_KEY` (siehe unten) und starten die Anwendung. Das Frontend ist danach auf Port 3000 erreichbar.

## Erster Start

Es gibt kein festes Standard-Passwort. Beim ersten Start legt das Backend das Konto `Admin` mit einem zufälligen Einmal-Passwort an und schreibt es ins Log. Das Installationsskript zeigt es am Ende an. Später findest du es so:

```bash
cd /opt/versicherungsmanager && docker compose logs backend | grep INITIAL_ADMIN_PASSWORD
```

| Angabe | Wert |
| :--- | :--- |
| Benutzername | `Admin` |
| Passwort | zufälliges Einmal-Passwort aus dem Log |

Bei der ersten Anmeldung leitet die App auf eine Einrichtungsseite, auf der du deine E-Mail-Adresse und ein eigenes Administrator-Passwort festlegst.

Passwort vergessen oder Log nicht mehr vorhanden? Auf dem Server lässt sich ein neues Einmal-Passwort erzeugen. Das geht nur mit Zugriff auf den Container, über das Netzwerk ist es nicht möglich:

```bash
cd /opt/versicherungsmanager && docker compose exec backend python reset_admin.py
```

## Update

Im Terminal des Servers genügt:

```bash
update
```

Das Skript sichert zuerst die Datenbank, baut die Anwendung neu und startet sie. Der Fortschritt wird in fünf Schritten angezeigt.

> **Hinweis:** Die Anwendung kommt ohne KI-Modell aus. Eine frühere Version konnte optional ein Sprachmodell (Qwen2.5-1.5B) laden. Gemessen brachte es gegenüber der regelbasierten Erkennung kaum etwas, kostete aber rund 1,5 GB Arbeitsspeicher, 1,1 GB Festplatte und Rechenzeit. Es wurde deshalb entfernt. Auf bestehenden Installationen ist der Ordner `backend/models` (ca. 1,1 GB) überflüssig und kann gelöscht werden.

## Sicherheit und Betrieb

Zettelfrieden verarbeitet personenbezogene Daten (Verträge, Beiträge, Dokumente). Diese Punkte gelten für jede Installation.

### HTTPS

`docker-compose.yml` liefert die App standardmäßig nur über unverschlüsseltes HTTP aus. Von außen erreichbar ist ausschließlich das Frontend auf Port 3000; das Backend (Port 8000) hört nur auf `127.0.0.1` und wird vom Frontend intern angesprochen. Auf `localhost` ist das unproblematisch. Sobald der Server im LAN oder aus dem Internet erreichbar ist, werden Zugangsdaten und Sitzungs-Token bei jeder Anfrage unverschlüsselt übertragen und sind für jeden mitlesbar, der Zugriff auf den Netzwerkpfad hat.

Betreibe die App deshalb immer hinter einem Reverse Proxy mit TLS-Zertifikat, zum Beispiel Nginx mit [Certbot](https://certbot.eff.org/) (Let's Encrypt):

```nginx
# /etc/nginx/sites-available/zettelfrieden
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

Zertifikat besorgen (einmalig, die Erneuerung richtet Certbot automatisch ein):

```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d deine-domain.de
```

Der Frontend-Container bleibt dafür unverändert. Nginx läuft als eigener Dienst auf dem Host oder in einem eigenen Container und leitet intern an `127.0.0.1:3000` weiter. Alternativen sind [Caddy](https://caddyserver.com/), das Zertifikate automatisch holt, oder ein [Cloudflare Tunnel](https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/), wenn der Server keine öffentliche IP-Adresse hat.

### Reverse Proxy und Anmelde-Begrenzung (`TRUSTED_PROXY_HOPS`)

Das Backend begrenzt fehlgeschlagene Anmeldungen pro Konto und pro Client-IP. Steht ein Reverse Proxy davor, sieht das Backend sonst nur dessen Adresse. Trage deshalb in der `.env`-Datei neben `docker-compose.yml` ein, wie viele Proxys vor der App laufen (ein Nginx Proxy Manager entspricht `1`), und starte neu:

```bash
echo "TRUSTED_PROXY_HOPS=1" >> .env && docker compose up -d
```

Ohne Proxy (direkter Zugriff auf Port 3000) bleibt der Wert bei `0`. Ein falscher Wert schwächt nur das IP-Limit ab; das Limit pro Konto bleibt immer aktiv.

### Registrierung abschalten

Ist die Instanz aus dem Internet erreichbar, kann sich zunächst jeder registrieren. Als Administrator schaltest du die Selbstregistrierung unter *Einstellungen > Systemeinstellungen* aus. Bestehende Konten bleiben unberührt; für weitere Konten schaltest du sie kurz wieder ein.

### Anmeldung mit OpenID Connect (Pocket ID)

Zusätzlich zum Passwort können sich Nutzer über einen OpenID-Connect-Anbieter anmelden. Getestet ist der Ablauf mit [Pocket ID](https://pocket-id.org) (Passkeys); er folgt dem Standard (Authorization Code mit PKCE).

**Einrichten**

1. Lege in Pocket ID einen neuen OIDC-Client an. Als Rückkehr-Adresse (Callback-URL) trägst du `https://<deine-domain>/api/auth/oidc/callback` ein; die genaue Adresse zeigt dir die App in der SSO-Karte. Notiere Client-ID und Client-Secret.
2. Trage in der App unter *Einstellungen > Systemeinstellungen > Single Sign-On* ganz oben die **Adresse dieser App** ein, so wie du sie im Browser aufrufst, also mit Domain (`https://zettelfrieden.beispiel.de`) und nicht mit der IP-Adresse. Daraus bildet die App die Rückkehr-Adresse, die in Pocket ID stehen muss (sie wird direkt darunter angezeigt). Stimmen beide nicht überein, meldet Pocket ID „redirect_uri is not registered“.
3. Trage in derselben Karte Aussteller-URL (die Adresse deines Pocket ID, z. B. `https://id.beispiel.de`), Client-ID und Client-Secret ein, schalte SSO ein und speichere. Auf der Anmeldeseite erscheint der Knopf „Mit Pocket ID anmelden“.
4. Verknüpfe dein eigenes Admin-Konto unter *Einstellungen > Single Sign-On > Konto jetzt verknüpfen*. Das funktioniert auch, wenn die E-Mail-Adresse in Pocket ID eine andere ist als in der App.

**Zuordnung der Konten**

- Wer sich wiederholt anmeldet, wird über die Identität im Anbieter erkannt, nicht über die E-Mail-Adresse. Ändert sich die Adresse im Anbieter, bleibt es dasselbe Konto.
- Bestehende Konten lassen sich gezielt verknüpfen: Jeder angemeldete Nutzer kann unter *Einstellungen > Single Sign-On > Konto jetzt verknüpfen* sein Konto mit seiner Identität im Anbieter verbinden, unabhängig von der E-Mail-Adresse. Eine Identität gehört immer zu genau einem Konto. Das ist der sichere Weg, wenn die Adressen verschieden sind oder der Anbieter die E-Mail-Adresse nicht als bestätigt meldet. Meldet sich jemand ohne verknüpftes Konto an, weist ihn die Anmeldeseite darauf hin, sein Konto zuerst zu verknüpfen.
- Bei der ersten Anmeldung wird ein bestehendes Konto mit gleicher E-Mail-Adresse verknüpft, aber nur, wenn der Anbieter die Adresse als bestätigt meldet. Ein Admin-Konto bleibt dabei Admin. Gibt es kein solches Konto, wird (sofern aktiviert) ein normales Benutzerkonto angelegt.
- Wer Administrator ist, bestimmt immer die App, nie der Anbieter.
- Bei einer SSO-Anmeldung entfällt die Zwei-Faktor-Abfrage der App, weil der Passkey beim Anbieter der starke Faktor ist.

**Passwort-Anmeldung ausschalten.** Sobald SSO läuft und dein Konto verknüpft ist, lässt sich die Anmeldung mit Passwort für alle ausschalten (nur dann, damit niemand ausgesperrt wird). Ist Pocket ID einmal nicht erreichbar, schaltet dieser Befehl auf dem Server das Passwort wieder ein und setzt zugleich ein neues Admin-Passwort:

```bash
docker compose exec backend python reset_admin.py --enable-password-login
```

### SECRET_KEY

Jedes Login-Token wird mit dem Wert der Umgebungsvariable `SECRET_KEY` signiert. `install.sh`, `proxmox-install.sh` und `update.sh` erzeugen dafür automatisch einen zufälligen, 64-stelligen Schlüssel in einer lokalen `.env`-Datei neben `docker-compose.yml`. Diese Datei steht in `.gitignore` und gelangt nie ins Repository. Startest du den Stack von Hand mit `docker compose up`, lege die Datei selbst an:

```bash
echo "SECRET_KEY=$(openssl rand -hex 32)" > .env
```

Das Backend startet absichtlich nicht, wenn `SECRET_KEY` fehlt oder ein bekannter unsicherer Standardwert ist.

**Sichere die `.env`-Datei getrennt von den Backups.** Aus dem `SECRET_KEY` wird auch der Schlüssel abgeleitet, mit dem gespeicherte Passwörter (SMTP, automatisches Backup, GitHub-Token) in der Datenbank verschlüsselt sind. Geht der Schlüssel verloren oder ändert er sich, sind diese Passwörter nicht mehr lesbar (das Backend meldet das beim Start im Log und beim Wiederherstellen eines Backups einer anderen Instanz) und müssen neu eingegeben werden. Außerdem müssen sich alle Benutzer neu anmelden. Die Dokumente und Verträge selbst sind davon nicht betroffen.

### Sitzungsdauer

Eine Anmeldung gilt `ACCESS_TOKEN_EXPIRE_MINUTES` Minuten (Standard 15) ab der letzten Aktivität und verlängert sich automatisch, solange die Seite benutzt wird. Nach spätestens `SESSION_MAX_HOURS` Stunden (Standard 12) seit der Anmeldung ist unabhängig davon eine neue Anmeldung nötig. Beide Werte lassen sich in der `.env`-Datei ändern.

### Uploads, Nginx und Größenlimits

Ein Dokument darf höchstens 15 MB groß sein, eine Backup-Datei beim Wiederherstellen höchstens 512 MB (entpackt höchstens 2 GB), alle anderen Anfragen höchstens 2 MB. Größere Anfragen werden schon vor der Verarbeitung abgewiesen. Steht ein Nginx davor, muss er Uploads dieser Größe durchlassen. Bei Fehler 413 trägst du im Nginx (im Nginx Proxy Manager unter *Advanced*) `client_max_body_size 600m;` ein.

### Weitere Empfehlungen

- **Automatische Backups verschlüsseln.** Lege unter *Einstellungen > Systemeinstellungen > Automatische Backups* ein eigenes Passwort fest, statt das beim ersten Lauf erzeugte zu behalten. Notiere es an einem sicheren Ort: Ohne dieses Passwort lässt sich ein Backup nicht wiederherstellen.
- **API-Dokumentation.** `/docs` und `/redoc` sind standardmäßig deaktiviert. Nur für die lokale Entwicklung lassen sie sich mit `ENABLE_API_DOCS=true` in der `.env`-Datei einschalten, nicht auf einem von außen erreichbaren Server.
- **Zwei-Faktor-Authentifizierung.** Unter *Einstellungen > 2-Faktor-Authentifizierung* kann jeder Benutzer einen Code aus einer Authenticator-App (TOTP, z. B. Aegis, 2FAS, Google Authenticator) als zweiten Faktor verlangen. Das ist besonders für Administratoren empfehlenswert. Die Wiederherstellungscodes werden nur einmal angezeigt und müssen getrennt aufbewahrt werden. Hat jemand Handy und Codes verloren, kann ein Administrator die 2FA in der Benutzerverwaltung zurücksetzen. Für den Admin-Zugang selbst setzt `reset_admin.py` (siehe oben) auch die 2FA zurück.
- **Sicherheitsprotokoll.** Administratoren sehen unter *Systemeinstellungen > Sicherheitsprotokoll* Anmeldungen, Fehlversuche (samt Adresse) und Änderungen an Konten und Einstellungen der letzten 12 Monate. Viele Fehlversuche von einer Adresse deuten auf einen Angriff hin.
- **Passwörter.** Das System verlangt mindestens 8 Zeichen (höchstens 72 Bytes) und weist bekannte Allerwelts-Passwörter („Passwort123“, „qwertz“ …) sowie Passwörter aus der eigenen E-Mail-Adresse ab. Backup-Passwörter brauchen mindestens 12 Zeichen. Die Sicherheit hängt weiterhin von der Qualität des gewählten Passworts ab.
- **Festplatte verschlüsseln.** Verträge und Dokumente liegen unverschlüsselt im Dateisystem des Servers (nur Backups und gespeicherte Passwörter sind verschlüsselt). Wer physischen Zugriff auf den Server, den Proxmox-Host oder dessen Snapshots hat, erreicht alle Daten. Setze deshalb auf Datenträgerverschlüsselung (LUKS oder ZFS) und schütze die Proxmox-Backups.
- **Kalender-Abo-Link.** Die WebCal-Adresse enthält ein geheimes Token, weil Kalender-Apps keine Anmeldung senden können. Wer den Link kennt, sieht deine Kündigungsfristen. Bei Verdacht erneuerst du ihn unter *Einstellungen > Kalender*; der alte Link wird ungültig.
- **Versicherer-Logos.** Die Logos lädt der Server (nicht der Browser) über den Favicon-Dienst von Google. Google erfährt dabei nur die Domain des Versicherers und die Adresse des Servers, nie die Adresse der Benutzer. Wer keine externe Anfrage möchte, setzt `DISABLE_LOGO_LOOKUP=true` in der `.env`-Datei; dann erscheinen Initialen.
- **Konten löschen.** Benutzer entfernen ihr Konto unter *Einstellungen > Konto löschen* selbst (Administratoren löscht ein anderer Administrator). Dabei werden Verträge, Schadensfälle, Dokumente und Posteingang samt Dateien gelöscht. Bereits erstellte Server-Backups enthalten die Daten weiterhin, bis sie gelöscht werden.
- **Container ohne Root-Rechte.** Das Frontend läuft als Benutzer `node`. Das Backend startet kurz als Root, übergibt die Datenordner (`backend/data`, `backend/documents`) an den Benutzer `app` und läuft danach unprivilegiert; alle nicht benötigten Linux-Capabilities sind entzogen. Macht das auf einem ungewöhnlichen Speicher-Setup Probleme, fällt der Start mit einer Warnung im Log auf Root zurück. Erzwingen lässt sich das mit `RUN_AS_ROOT=1` in der `.env`-Datei (danach `docker compose up -d`).

## Funktionen

### Dokumentenanalyse

- **Lokale Texterkennung ohne KI-Modell.** Gesellschaft, Policennummer, Fristen, Kfz-Klassen, Beiträge und Leistungen werden mit festen Regeln gelesen. PDFs mit Textebene liest Poppler (`pdftotext -layout`, Tabellen behalten ihre Spalten), Scans und Fotos liest Tesseract mit deutschem Wörterbuch. Es werden keine Modelle heruntergeladen.
- **Schräge und gedrehte Seiten.** Schräg eingescannte Seiten werden vor dem Lesen begradigt. Seiten, die um 90° oder 180° gedreht sind, erkennt die Texterkennung an ihrer geringen Sicherheit und liest sie neu.
- **Lange PDFs.** Bei PDFs mit Textebene bleiben die Seiten mit den meisten Vertragsdaten erhalten. Lange Scans werden in Schüben gelesen, das Lesen endet, sobald ein Beitrag gefunden ist. Ein Informationsschreiben mit 60 Seiten wird nicht bis zum Ende gelesen.
- **Art des Schreibens.** Versicherungsschein, Beitragsrechnung, Nachtrag, Beitragsanpassung, Grüne Karte, Bedingungen und Verbraucherinformationen werden an der Kopfzeile erkannt. Informationsschreiben ändern nie Vertragsdaten.
- **Beträge.** Guthaben und Erstattungen werden nie als Beitrag übernommen. Bei einem beendeten Vertrag gibt es weder Beitrag noch Kündigungsfrist.
- **Prüfung jedes Werts.** Der Upload-Dialog zeigt zu jedem Wert, ob er im Dokument gefunden wurde (Seite und Textstelle), nur berechnet ist oder unsicher.
- **Dokumentname.** Statt kryptischer Scan-Namen schlägt die App „Gesellschaft, Art des Schreibens, Datum“ vor, zum Beispiel *Itzehoer Kfz-Beitragsrechnung Januar 2021*, nie mit der Policennummer.
- **Doppelte Dokumente.** Wird eine Datei erneut hochgeladen, warnt die App; gespeichert werden kann sie trotzdem. Verglichen werden nur die eigenen Dokumente.
- **Vertragsdaten nur vom richtigen Schreiben.** Beginn und Ende eines bestehenden Vertrags ändern nur die Police (beides) und ein Nachtrag (nur das Ende). Rechnungen und Beitragsanpassungen übernehmen Beitrag, Zahlweise und Klassen, aber keine Laufzeit.
- **Eine Analyse pro Upload.** Dokumentvorschau und Speicherung teilen sich dasselbe Analyseergebnis.
- **Lernsystem mit Anonymisierung.** Ein Sanitizer (`sanitizer.py`) entfernt vor jedem Lernschritt Namen, Adressen, IBANs, Policennummern, Kennzeichen und Telefonnummern.
- **Musterabgleich per Pull Request.** Standardmäßig deaktiviert und pro Instanz vom Administrator aktivierbar (mit eigenem GitHub-Token in den Einstellungen). Das Backend veröffentlicht nichts automatisch, sondern öffnet oder aktualisiert einen Pull Request, sodass Muster erst nach einer Prüfung übernommen werden. Die gelernten, anonymisierten Layout-Muster werden zusätzlich obfuskiert (Base64/XOR) abgelegt.

### Verträge, Kosten und Fristen

- **Beitragsentwicklung.** Preisanpassungen werden aus Beitragsrechnungen gelesen und über die Jahre als Balkendiagramm mit prozentualer Veränderung dargestellt.
- **Kfz-Tarifklassen.** Schadenfreiheitsklasse, Regionalklasse und Typklasse werden erkannt und angezeigt.
- **Ruhendstellung.** Verträge lassen sich pausieren. Ruhende Verträge fließen mit 0 € in die Jahresausgaben ein und sind als ruhend markiert.
- **Kündigungsschreiben.** Der Assistent erzeugt druckfertige Vorlagen für die ordentliche Kündigung (§ 11 VVG), die Sonderkündigung wegen Beitragserhöhung (§ 40 VVG), nach einem Schadensfall (§ 92 VVG) und bei Wegfall des versicherten Risikos (§ 80 VVG), jeweils mit SEPA-Widerruf und Löschhinweis nach DSGVO. Die Vorlagen ersetzen keine Rechtsberatung.
- **Kalender.** Eine WebCal-Adresse bindet die Fristen in Apple-, Google- oder Outlook-Kalender ein, mit Erinnerungen 14 und 7 Tage vorher. Zusätzlich gibt es `.ics`-Downloads für die Offline-Nutzung.
- **E-Mail-Erinnerungen.** Ist ein SMTP-Server hinterlegt, verschickt das System täglich Erinnerungen an Nutzer, die das in ihrem Profil aktiviert haben. Der Kalender funktioniert auch ohne SMTP.
- **Steuerexport.** Klassifizierung nach § 10 und § 9 EStG, Jahressummen sowie CSV-Export (WISO, Elster, Excel). Der Export ersetzt keine Steuerberatung.
- **Schadensfälle und Notizen.** Schadensfälle mit Datum, Schadensnummer, Höhe und Status (in Bearbeitung, reguliert, abgelehnt) sowie freie Notizen je Vertrag.

### Übersicht und Posteingang

- **Kennzahlen.** Aktive Policen, Gesamtkosten pro Jahr, Kündigungsfristen der nächsten 90 Tage (anklickbar) und die Zahl der noch nicht zugeordneten Dokumente im Posteingang (anklickbar).
- **Posteingang.** Zentrale Ablage für hochgeladene Dokumente vor der Zuordnung zu einer Police, mit Analysevorschlägen.
- **Kostenverteilung.** Jahresausgaben nach Sparte (Kfz, Privathaftpflicht, Hausrat, Rechtsschutz und weitere).
- **Suche und Sortierung.** Nach Name, Gesellschaft, Policennummer, Kosten, Kündigungsfrist oder Alphabet.
- **Detailansicht je Police** mit den Reitern Stammdaten, Beitragsentwicklung, Dokumente, Schadensfälle und Notizen.
- **Dokumentvorschau.** PDFs und Bilder öffnen sich in einem großen, authentifiziert geladenen Vorschaufenster.

### Benutzer und Zugriff

- **Erst-Login.** Der erste Administrator muss sein Passwort ändern. Danach läuft die Sitzung über einen JWT in einem httpOnly-Cookie (bcrypt-Passwort-Hashing, 15 Minuten Inaktivitäts-Timeout mit gleitender Verlängerung).
- **Zwei-Faktor-Authentifizierung und Sicherheitsprotokoll.** Optionaler zweiter Faktor (TOTP) mit Wiederherstellungscodes. Das Protokoll hält Anmeldungen, Fehlversuche und Administrator-Aktionen fest.
- **Rollen.** Administratoren legen Benutzer an, setzen Passwörter zurück und verwalten die Systemeinstellungen.
- **Zugriffskontrolle.** Jeder Endpunkt für Dokumente und Verträge prüft die Eigentümerschaft. Fremde Unterlagen sind auch über direkt aufgerufene Links nicht erreichbar.
- **Passwort-Reset per E-Mail** über einen vom Administrator konfigurierten SMTP-Server. Alternativ löst ein Administrator die Reset-Mail aus der Benutzerverwaltung aus.
- **Single Sign-On** über OpenID Connect (siehe oben).

### Schutz bestehender Daten beim Upload

- **Namensschutz.** Ein neues Dokument überschreibt nie den Namen einer bestehenden Police.
- **Ruhendstellung bleibt erhalten.** Der Status „ruhend“ und der hinterlegte Grund bleiben bei neuen Uploads unberührt und lassen sich nur von Hand ändern.
- **Informationsdokumente.** Dokumente vom Typ Sonstiges, Verbraucherinformationen oder Kundeninformationen werden nur archiviert und ändern weder Vertragsdaten noch Beiträge.

### Darstellung

- **Drei Designs:** Dunkel (Standard), Dark Neon Glass und Apple Light, kombinierbar mit mehreren Akzentfarben. Die Oberfläche verwendet durchgehend einheitliche Linien-Symbole und respektiert die Systemeinstellung für reduzierte Bewegung.
- **Kurze Ladezeiten.** Übersicht und Detailseiten werden sofort aus einem lokalen Zwischenspeicher dargestellt und danach im Hintergrund aktualisiert.

### Betrieb

- **Verschlüsselte Backups mit Rotation.** Passwortgeschützte (Fernet/AES) Archive aus Datenbank und Dokumenten, automatisch bei jedem `update` und nach einem einstellbaren Zeitplan. Ältere Backups werden nach Anzahl oder Alter rotiert. Neue Backups tragen die Endung `.zfbackup`; ältere `.noxusbackup`-Dateien bleiben les- und wiederherstellbar.
- **Datenbankzugriffe.** Indizes auf allen Fremdschlüsseln und Eager-Loading (`selectinload`) vermeiden N+1-Abfragen.
- **Schlankes Docker-Image.** Ohne Compiler und ohne Modelldateien; alle Python-Abhängigkeiten sind fertige Pakete.

## Systemvoraussetzungen

| Komponente | Minimum | Empfohlen |
| :--- | :--- | :--- |
| Prozessor | 2 Kerne | 4 Kerne (Scans werden schneller gelesen) |
| Arbeitsspeicher | 2 GB | 4 GB |
| Festplatte | 5 GB SSD | 16 GB SSD |

## Technik

- **Frontend:** Next.js 16 (App Router, Turbopack), React 19, Tailwind CSS, Lucide.
- **Backend:** Python 3.11, FastAPI, SQLAlchemy (SQLite), pypdf, Tesseract (pytesseract), Poppler.
- **Betrieb:** Docker, Docker Compose, Installationsskripte für Proxmox VE (LXC) und Linux.

## Entwicklung

```bash
# Backend (aus backend/)
pip install -r requirements-dev.txt
pytest
uvicorn main:app --host 0.0.0.0 --port 8000

# Frontend (aus frontend/)
npm install
npm run dev
```

Die Tests des Backends laufen gegen eine temporäre SQLite-Datenbank. Sie prüfen auch, dass jede Quelldatei den Lizenzkopf trägt (`tests/test_license_headers.py`). Neue Dateien erhalten diesen Kopf:

```text
Copyright (c) 2026 Dennis Guse
SPDX-License-Identifier: MIT
See the LICENSE file in the project root.
```

## Lizenz

Copyright (c) 2026 Dennis Guse ([KaelanTesseract](https://github.com/KaelanTesseract))

Zettelfrieden steht unter der [MIT-Lizenz](LICENSE). Die Software wird ohne jede Gewährleistung bereitgestellt; die Haftung der Autoren ist im Rahmen des Lizenztextes ausgeschlossen. Die Anwendung liest Verträge automatisch aus und erzeugt Schreiben und Auswertungen. Sie ersetzt weder Rechts-, Versicherungs- noch Steuerberatung, und die ausgelesenen Werte sind vor jeder Verwendung zu prüfen.

Drittanbieter-Software, Schriften und deren Lizenzen sind in [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) aufgeführt. Das Logo gehört zum Repository und steht wie der Quellcode unter der MIT-Lizenz. Namen und Logos von Versicherern sind Eigentum der jeweiligen Unternehmen.
