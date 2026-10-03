# OIDC-Anmeldung (Pocket ID) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Anmeldung per OpenID Connect (Pocket ID) zusätzlich zum Passwort-Login.

**Architecture:** Backend-Modul `oidc.py` (Discovery, PKCE/State, Code-Tausch, ID-Token-Prüfung) plus Router `routers/oidc.py` (login/callback, Benutzerauflösung). Das Sitzungs-Token wird im Header `X-Refreshed-Token` an den bestehenden Next-Proxy übergeben, der daraus den httpOnly-Cookie macht. Einstellungen liegen in `SystemSetting` (Secret verschlüsselt).

**Tech Stack:** FastAPI, PyJWT (JWKS), httpx, SQLAlchemy/SQLite, Next.js 16, pytest. Keine neue Abhängigkeit.

**Spec:** `docs/superpowers/specs/2026-10-03-oidc-pocket-id-design.md`

## Global Constraints

- Keine neue Python- oder npm-Abhängigkeit.
- Rückkehr-Adresse = `APP_URL + "/api/auth/oidc/callback"`, nie aus Request-Headern.
- Client-Secret verschlüsselt (`secrets_crypto`), von keinem GET-Endpunkt zurückgegeben (nur `oidc_client_secret_set`).
- Verknüpfen/Anlegen nur mit `email_verified == true`; neue SSO-Konten sind `is_admin = False`; bestehende Rechte bleiben unverändert.
- Fehlermeldungen an den Browser sind allgemein (keine Provider-Details); Gründe nur im Sicherheitsprotokoll.
- Neue Spalten brauchen einen Migrationsschritt in `main.py:auto_migrate_sqlite()`.
- UI-Texte deutsch, keine Emojis (lucide-Icons), Farben nur über die Design-Tokens.

---

### Task 1: `oidc.py` – Kern mit künstlichem Provider

**Files:**
- Create: `backend/oidc.py`, `backend/tests/oidc_fake.py`, `backend/tests/test_oidc_core.py`

**Interfaces:**
- Produces:
  - `class OidcError(Exception)` (Meldung nur für das Protokoll)
  - `@dataclass OidcConfig(issuer: str, client_id: str, client_secret: str, redirect_uri: str)`
  - `new_flow() -> Flow` mit `Flow(state: str, nonce: str, verifier: str)`; `pack_flow(flow) -> str` / `unpack_flow(value: str) -> Flow` (signiert mit `auth.SECRET_KEY`, 10 Minuten gültig, sonst `OidcError`)
  - `get_discovery(cfg, client=None) -> dict` (prüft `issuer`-Gleichheit, cacht 10 Min)
  - `authorization_url(cfg, discovery, flow) -> str` (S256-Challenge, Scopes `openid email profile`)
  - `exchange_and_verify(cfg, discovery, code: str, flow: Flow, client=None) -> dict` (Claims; prüft Signatur via JWKS, `iss`, `aud`, `exp`, `nonce`)
- Test-Hilfe `tests/oidc_fake.py`: `FakeProvider` (RSA-Schlüssel, `issuer`, `transport()` für `httpx.MockTransport`, `make_id_token(**claims)`).

- [ ] Tests zuerst: Erfolgsfall, falscher `nonce`, falscher `iss`, falsches `aud`, abgelaufen, falsche Signatur, abweichender Discovery-`issuer`, manipuliertes/abgelaufenes Flow-Cookie.
- [ ] Implementieren, bis alle grün sind; `python -m pytest backend/tests/test_oidc_core.py -q`.
- [ ] Commit `feat: OIDC core (discovery, PKCE, ID token validation)`.

### Task 2: Datenmodell, Einstellungen, Passwort-Login-Schalter

**Files:**
- Modify: `backend/models.py` (User: `oidc_issuer`, `oidc_sub`), `backend/main.py` (Migration + Index), `backend/routers/users.py`, `backend/schemas.py`, `backend/audit.py` (Labels), `backend/reset_admin.py`
- Create: `backend/oidc_settings.py`, `backend/tests/test_oidc_settings.py`

**Interfaces:**
- Produces (`oidc_settings.py`): `load_config(db) -> OidcConfig | None` (None wenn aus/unvollständig), `get_setting(db, key, default)`, `set_setting(db, key, value)`, `password_login_enabled(db) -> bool`, `auto_create_enabled(db) -> bool`.
- Endpunkte: `GET /api/users/auth-config` (öffentlich: `oidc_enabled`, `oidc_label`, `password_login_enabled`), `GET/PUT /api/users/oidc-config` (Admin; Secret nur als `oidc_client_secret_set`; `password_login_enabled=false` nur, wenn das eigene Konto verknüpft ist, sonst 400).
- `POST /api/users/login` und `/register` antworten 403, wenn Passwort-Login aus ist.

- [ ] Tests zuerst: auth-config öffentlich, Secret nie im GET, leeres Secret behält das alte, Admin-Pflicht, Aussperr-Schutz, Login/Register bei abgeschaltetem Passwort-Login, Audit-Eintrag.
- [ ] Implementieren; `reset_admin.py --enable-password-login`.
- [ ] Alle Tests laufen lassen; Commit.

### Task 3: Endpunkte `login`/`callback` und Benutzerauflösung

**Files:**
- Create: `backend/routers/oidc.py`, `backend/tests/test_oidc_flow.py`
- Modify: `backend/main.py` (Router einbinden), `backend/audit.py`, `frontend/src/app/api/[...path]/route.ts`

**Interfaces:**
- Consumes: Task 1 und 2.
- Produces: `GET /api/auth/oidc/login` (302 + Cookie `noxus_oidc`), `GET /api/auth/oidc/callback` (liest Flow aus Header `X-OIDC-Flow`; 302 `/sso-done` mit `X-Refreshed-Token`, Fehler 302 `/login?error=sso`); `resolve_user(db, claims, cfg) -> (User | None, event: str)`.

- [ ] Tests zuerst (vollständiger Ablauf gegen `FakeProvider` mit `TestClient`): neuer Benutzer ohne Admin, Verknüpfung bestehender Admin bleibt Admin, `sub`-Wiedererkennung nach E-Mail-Wechsel, unbestätigte E-Mail, Auto-Anlegen aus, falscher `state`, fehlender Flow-Header, Audit-Ereignisse `sso_login/sso_linked/sso_created/sso_denied`.
- [ ] Implementieren; Proxy gibt `noxus_oidc` als `X-OIDC-Flow` an den Callback weiter.
- [ ] Alle Tests; Commit.

### Task 4: Oberfläche

**Files:**
- Modify: `frontend/src/app/login/page.tsx`, `frontend/src/app/settings/page.tsx`
- Create: `frontend/src/app/sso-done/page.tsx`, `frontend/src/components/settings/OidcCard.tsx`

- [ ] Login-Seite lädt `auth-config`, zeigt den SSO-Knopf, blendet das Passwort-Formular bei abgeschaltetem Passwort-Login aus, zeigt `?error=sso` allgemein.
- [ ] `/sso-done`: `markSignedIn()`, `/api/users/me` in den Cache, weiter zu `/`.
- [ ] Einstellungs-Karte „Single Sign-On“ (Felder laut Spec, Secret maskiert, Rückkehr-Adresse zum Kopieren).
- [ ] `npx tsc --noEmit`, im Browser prüfen, Commit.

### Task 5: Dokumentation und Abschluss

**Files:** `README.md`, `CLAUDE.md`, `Sicherheit.md`

- [ ] README-Abschnitt „Anmeldung mit Pocket ID“; CLAUDE.md-Modulliste; `Sicherheit.md`-Punkte (Praxistest gegen echtes Pocket ID, Back-Channel-Logout offen).
- [ ] Volle Backend-Tests, Produktions-Build, Commit. Kein Push ohne Freigabe.
