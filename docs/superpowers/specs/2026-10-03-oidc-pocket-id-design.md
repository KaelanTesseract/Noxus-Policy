# OIDC-Anmeldung (Pocket ID) – Design

Stand: 2026-10-03. Status: vom Auftraggeber im Gespräch freigegeben, Spezifikation zur Durchsicht.

## Ziel

Nutzer können sich zusätzlich zum Passwort über einen OpenID-Connect-Provider anmelden. Zielprovider ist **Pocket ID** (selbst gehostet, Passkey-Anmeldung); der Aufbau folgt dem Standard und funktioniert auch mit anderen Providern, die Discovery, PKCE und `email_verified` unterstützen.

Festgelegte Entscheidungen:

| Frage | Entscheidung |
|---|---|
| Verhältnis zum Passwort-Login | Zusätzlich. Der Admin kann den Passwort-Login später abschalten. |
| Erste SSO-Anmeldung | Bestehendes Konto mit gleicher, vom Provider **bestätigter** E-Mail verknüpfen, sonst neues Konto anlegen. |
| Admin-Rolle | Nur in der App. Per SSO angelegte Konten sind normale Benutzer. Ein bestehendes Admin-Konto bleibt nach der Verknüpfung Admin. |
| 2FA der App | Entfällt bei SSO-Anmeldungen (der Passkey beim Provider ist der starke Faktor). |
| Neue Konten per SSO | Standard an, schaltbar. Die Registrierungs-Sperre der App gilt dafür nicht. |

Nicht Teil dieser Arbeit (YAGNI): Gruppen-/Rollen-Abbildung, mehrere Provider gleichzeitig, SSO-Abmeldung beim Provider (Back-Channel/RP-initiated Logout), Entknüpfen in der Oberfläche.

## Ablauf (Authorization Code mit PKCE)

1. Login-Seite fragt `GET /api/users/auth-config` (öffentlich): `{ oidc_enabled, oidc_label, password_login_enabled }`.
2. Klick auf den SSO-Knopf navigiert den Browser zu `GET /api/auth/oidc/login`.
   Das Backend lädt (gecachte) Discovery-Daten, erzeugt `state`, `nonce`, `code_verifier`, legt sie in einem **signierten, kurzlebigen Cookie** `noxus_oidc` ab (HttpOnly, `SameSite=Lax`, Pfad `/api/auth/oidc`, 10 Minuten) und antwortet mit `302` zum Authorization-Endpoint des Providers.
3. Der Provider leitet zu `GET /api/auth/oidc/callback?code=…&state=…` zurück. Die Rückkehr-Adresse ist `APP_URL + "/api/auth/oidc/callback"` und wird nie aus Host-Headern gebildet.
4. Das Backend prüft `state` gegen das Cookie, tauscht den Code (mit `code_verifier` und Client-Secret) am Token-Endpoint und validiert das ID-Token: Signatur über JWKS, `iss`, `aud`, `exp`, `nonce`.
5. Benutzerauflösung (siehe unten), danach `auth.create_login_token(user)` und Antwort `302 /sso-done` mit dem Token im Header `X-Refreshed-Token`. Der bestehende Next-Proxy macht daraus bereits den httpOnly-Cookie `noxus_session` und entfernt den Header; es gibt keine neue Sitzungslogik.
6. Die Seite `/sso-done` setzt den „war angemeldet“-Hinweis (`markSignedIn`), lädt `/api/users/me` in den Cache und leitet zu `/`. Fehler führen zu `/login?error=sso`, mit einer allgemeinen Meldung (keine Details aus dem Provider).

Der Next-Proxy bekommt zwei kleine Erweiterungen: für `/api/auth/oidc/callback` reicht er den Wert des Cookies `noxus_oidc` als Header `X-OIDC-Flow` ans Backend weiter (Cookies werden sonst absichtlich nicht durchgereicht), und er lässt `Set-Cookie`/`Location` der Weiterleitungen durch (tut er bereits).

## Benutzerauflösung

1. Treffer über `(oidc_issuer, oidc_sub)` → anmelden.
2. Sonst, wenn `email_verified == true` und ein Konto mit dieser E-Mail existiert → `oidc_issuer`/`oidc_sub` eintragen, anmelden. Rechte (auch Admin) bleiben unverändert.
3. Sonst, wenn „Neue Konten per SSO anlegen“ an ist und `email_verified == true` → Konto mit zufälligem, unbenutzbarem Passwort-Hash anlegen, `is_admin = false`.
4. Sonst abweisen (allgemeine Fehlermeldung, Eintrag im Sicherheitsprotokoll mit dem Grund).

Eine fehlende oder unbestätigte E-Mail führt nie zu Verknüpfung oder Anlage. Alle Ergebnisse (`sso_login`, `sso_linked`, `sso_created`, `sso_denied`) gehen ins Sicherheitsprotokoll.

## Einstellungen und Sicherheit

- Neue `SystemSetting`-Schlüssel: `oidc_enabled`, `oidc_issuer`, `oidc_client_id`, `oidc_client_secret` (verschlüsselt über `secrets_crypto`, wird nie von GET-Endpunkten zurückgegeben, nur `oidc_client_secret_set`), `oidc_button_label`, `oidc_auto_create`, `password_login_enabled`.
- Admin-Karte „Single Sign-On“ in den Systemeinstellungen; Änderungen erscheinen im Sicherheitsprotokoll.
- Discovery: `issuer` im Dokument muss exakt der konfigurierten URL entsprechen; Timeouts und Größenlimit bei allen Abrufen; JWKS wird gecacht und bei unbekannter `kid` einmal neu geladen.
- **Passwort-Login abschalten:** `POST /api/users/login` und `/register` lehnen dann ab. Der Admin kann den Schalter nur setzen, wenn sein eigenes Konto verknüpft ist (Aussperr-Schutz). `reset_admin.py` bekommt `--enable-password-login`.
- Rate-Limit für `/api/auth/oidc/*` wie bei den Login-Endpunkten.
- Das ID-Token wird nie an den Browser weitergegeben; der Browser sieht nur den bestehenden Sitzungs-Cookie.

## Komponenten

| Einheit | Aufgabe | Abhängigkeiten |
|---|---|---|
| `backend/oidc.py` | Discovery, PKCE/State, Code-Tausch, ID-Token-Prüfung (nur reine Funktionen und kleine Klasse, kein FastAPI) | `httpx`, `PyJWT` (JWKS), `secrets_crypto` |
| `backend/routers/oidc.py` | Endpunkte `login`/`callback`, Benutzerauflösung, Audit | `oidc.py`, `auth`, `audit` |
| `routers/users.py` | `auth-config`, Passwort-Login-Schalter, Konfigurations-Endpunkte (Admin) | |
| `models.py`, `main.py` | Spalten `oidc_issuer`, `oidc_sub` (+ Index) und Migration | |
| Proxy `api/[...path]/route.ts` | Cookie `noxus_oidc` als Header weiterreichen | |
| Login-Seite, `sso-done`, Einstellungs-Karte | Oberfläche | |

Keine neue Abhängigkeit in `requirements.txt`.

## Tests (pytest, künstlicher Provider)

Ein Test-Provider erzeugt einen RSA-Schlüssel und beantwortet Discovery, JWKS und Token-Endpunkt über einen gemockten `httpx`-Transport. Geprüft werden:

- Erfolgsfall: neuer Benutzer ohne Adminrechte, Sitzungs-Token wird ausgestellt
- falscher `state`, falsches `nonce`, falsche Signatur, falscher `iss`/`aud`, abgelaufenes Token
- Verknüpfung per bestätigter E-Mail, Admin bleibt Admin
- unbestätigte E-Mail: keine Verknüpfung, keine Anlage
- Wiedererkennung nach E-Mail-Wechsel beim Provider (über `sub`)
- „Neue Konten anlegen“ aus → Abweisung
- Passwort-Login abgeschaltet → Login/Registrierung abgelehnt; Schalter ohne eigene Verknüpfung abgelehnt
- Client-Secret wird nie zurückgegeben
- Audit-Einträge

## Dokumentation

README-Abschnitt „Anmeldung mit Pocket ID“: Client in Pocket ID anlegen, Rückkehr-Adresse `https://<deine-domain>/api/auth/oidc/callback`, PKCE aktivieren, Scopes `openid email profile`, Werte in der App eintragen, `APP_URL` setzen. Hinweis auf den Notzugang. `CLAUDE.md` und `Sicherheit.md` werden ergänzt.

## Offene Punkte

Keine. Ein Test gegen die echte Pocket-ID-Instanz ist erst nach dem Ausrollen möglich, weil Client-ID und Secret auf dem Server eingetragen werden (ohne dass sie hier sichtbar sind).
