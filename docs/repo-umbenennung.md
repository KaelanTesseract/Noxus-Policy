# Umbenennung des GitHub-Repositorys (Noxus-Policy zu Zettelfrieden)

Der Name der App ist umgestellt. Das Repository heißt auf GitHub noch `KaelanTesseract/Noxus-Policy`.
Damit beim Umbenennen nichts bricht, probieren die Skripte und die Mustersynchronisation **beide Namen**
(neuester zuerst) und nehmen den, der antwortet. Die Reihenfolge unten ist trotzdem wichtig.

## Reihenfolge

1. **Push und CI abwarten.** Der Docker-Job der CI baut beide Images und startet das Backend. Ist er rot,
   nicht updaten.
2. **Server aktualisieren:** im Container `update`. Der erste Durchlauf läuft noch mit dem alten Skript auf dem
   Server und holt das neue; der zweite benutzt es. Danach prüfen: Anmeldung, ein Dokument hochladen,
   Einstellungen öffnen. Der Ordner `backend/models` (altes KI-Modell, ca. 1,1 GB) ist überflüssig und kann gelöscht werden.
3. **Repository umbenennen:** GitHub, Repository, *Settings*, *General*, *Repository name*: `Zettelfrieden`
   (oder `gh repo rename Zettelfrieden`). GitHub leitet die alte Adresse weiter.
4. **Einmal `update` auf dem Server ausführen.** Das Skript findet jetzt die neue Adresse und setzt `origin` darauf.
5. **Auf dem Entwicklungs-PC:** `git remote set-url origin https://github.com/KaelanTesseract/Zettelfrieden.git`.
6. **Letzter Schritt im Code (ein kleiner Commit):** README-Installationsbefehle, `frontend/src/lib/version.ts`
   (`GITHUB_REPO`) und die Links im Footer auf den neuen Namen setzen. Bis dahin funktionieren die alten
   Adressen über die Weiterleitung. Danach kann der alte Name aus `update.sh`, `install.sh`, `proxmox-install.sh`
   und `backend/learning.py` entfernt werden (optional, er schadet nicht).

## Was beim Umbenennen funktioniert und warum

| Was | Verhalten |
|---|---|
| `update` auf bestehenden Servern | probiert zuerst den neuen, dann den alten Namen |
| Neuinstallation (`install.sh`, `proxmox-install.sh`) | wie oben |
| Mustersynchronisation (Pull Request) | `learning.github_repo()` nimmt den Namen, der mit 200 antwortet; eine Weiterleitung übersteht ein POST nicht |
| Hinweis auf neue Version im Footer | läuft über die Weiterleitung (nur Lesen) |
| GitHub Actions, Dependabot | unabhängig vom Namen |

## Nicht tun

- **Den alten Namen `Noxus-Policy` nie als neues Repository anlegen.** Dann zeigt er nicht mehr auf das
  umbenannte Repository, und alle Server, die ihn noch kennen, bekommen kein Update.
- Cookies, Backup-Endungen und Verschlüsselungs-Zeichenfolgen **nicht** umbenennen (siehe `CLAUDE.md`, Abschnitt *Name*).
