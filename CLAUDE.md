# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project overview

Noxus Policy ("Versicherungsmanager") is a self-hosted insurance policy management platform with AI/OCR-driven document analysis. German-language product; UI strings, model prompts, and domain terms (Beitragsanpassung, Kündigungsfrist, SF-Klasse, etc.) are in German — keep new user-facing strings and comments consistent with that. It is a two-service app: a Next.js frontend and a FastAPI backend, meant to run via Docker Compose.

## Commands

### Frontend (`frontend/`)
- `npm run dev` — starts Next.js dev server on `0.0.0.0` (Turbopack)
- `npm run build` — production build
- `npm run start` — run production build
- `npm run lint` — ESLint (flat config, `eslint.config.mjs`)
- No test runner is configured in this repo.

### Backend (`backend/`)
- No lockfile/venv tooling beyond `requirements.txt`; install with `pip install -r requirements.txt`.
- Run locally: `uvicorn main:app --host 0.0.0.0 --port 8000` (from `backend/`).
- No test suite, linter, or formatter is configured for the backend.

### Full stack
- `docker-compose up --build` from the repo root builds and runs both `backend` and `frontend` containers (`network_mode: host`, backend on `:8000`, frontend on `:3000`).
- `install.sh` / `proxmox-install.sh` / `update.sh` are end-user deployment scripts for Proxmox LXC / Linux hosts, not development tooling.

There is currently no automated test suite for either service — verify changes by running the app (see the `run` skill) and exercising the affected flow manually.

## Architecture

### Request flow: frontend never talks to the backend directly
The Next.js app calls its own `/api/*` routes; `frontend/src/app/api/[...path]/route.ts` is a catch-all proxy that forwards every method to the FastAPI backend. It tries a list of candidate `BACKEND_URLS` (env `BACKEND_URL`, then Docker/host fallbacks) with a retry loop, since the backend container may still be booting or downloading its AI model. `frontend/src/lib/api.ts` is the single client-side wrapper (`api.get/post/put/postForm/delete`) — it attaches the JWT bearer token from `localStorage` and redirects to `/session-expired` on 401. Always route new frontend API calls through `lib/api.ts`, not raw `fetch`.

### Backend module layout (`backend/`)
- `main.py` — FastAPI app setup, CORS, router registration, and startup hooks. On startup it: creates tables, runs `auto_migrate_sqlite()` (hand-rolled `ALTER TABLE ... ADD COLUMN` / `CREATE INDEX IF NOT EXISTS` checks — **there is no Alembic migration flow**; new SQLAlchemy model columns or indexes must also be added here as a migration step, and existing installs keep any columns removed from `models.py` as harmless orphans rather than risking a `DROP COLUMN` migration), seeds a default `admin`/`admin` user if none exists, and starts the backup-scheduler daemon thread plus a daily vendor-pattern sync.
- `database.py` — SQLAlchemy engine/session/`Base`, SQLite by default (`DATABASE_URL` env var); `resolve_sqlite_path()` is the single source of truth for turning that URL into a filesystem path (used by both `database.py` and `main.py`'s migration code — don't reintroduce a second copy).
- `models.py` — SQLAlchemy models: `User`, `Insurance`, `PremiumHistory`, `Claim`, `Document`, `Category`, `SystemSetting`. `Document` doubles as both an insurance attachment and an "Inbox" item (`is_inbox`, `status`, `ai_data` JSON string) before it's assigned to an `Insurance`. Foreign-key columns (`owner_id`, `insurance_id`) are indexed.
- `schemas.py` — Pydantic request/response models.
- `auth.py` — JWT (PyJWT, `HS256`, 7-day expiry) + bcrypt password hashing. `get_current_user`/`get_current_active_user` are the standard FastAPI dependencies for protected routes; `SECRET_KEY` comes from env (defaults to `changeme123` — must be overridden in real deployments). Every endpoint that serves a stored file or user-owned resource must depend on `get_current_active_user` and check ownership — `routers/documents.py`'s `view_document`/`download_document` previously skipped this and leaked any document to unauthenticated requests; treat that pattern as a regression class to watch for in new endpoints.
- `routers/` — FastAPI routers, each `include_router`-mounted in `main.py`: `users` (auth/admin/profile/SMTP config/password-reset-by-email/calendar-webcal), `insurances` (CRUD + premium history + claims), `documents` (upload/OCR pipeline), `inbox` (Posteingang workflow), `backup` (DB+documents backup/restore, encrypted archives). SMTP-based e-mail (password reset, test mail, daily cancellation-deadline reminders) is a real, supported feature — configured per-instance via `SystemSetting` rows (`smtp_server`, `smtp_port`, etc.) through the admin "E-Mail & SMTP Server" settings card, not env vars. There is **no** Netzlaufwerk (WebDAV) feature in this codebase (removed on purpose) — don't reintroduce `netdrive-*` endpoints/columns or a WebDAV server without being asked.
- `ocr.py` — Document understanding pipeline: extracts text via `pypdf`/`pytesseract`+`pdf2image` OCR fallback, then `extract_insurance_data()` either runs the embedded local LLM (`extract_with_mini_ai`, Qwen2.5-1.5B via `llama-cpp-python`, auto-downloaded from Hugging Face on first use) or falls back to a large hand-written German regex/keyword extractor (`extract_insurance_data_regex`) when AI is disabled or fails. Results are further corrected by dedicated fallback extractors (policy number, cost, dates, Regionalklasse) that run regardless of which path produced the initial data. The frontend's `/documents/extract` preview call and the follow-up `POST /documents` save call used to both run this full pipeline on the same file; `create_document` now accepts an optional `extracted_data` form field so the frontend can pass along the already-extracted result and skip the second OCR/LLM pass — keep that field wired up when touching the upload flow. `json.dumps(...)` calls that serialize an `extract_insurance_data()` result must pass `default=str`, since the dict contains real `datetime.date` objects that aren't natively JSON-serializable.
- `learning.py` — "Vendor pattern" learning loop: after a document is verified, `learn_from_feedback()` derives anonymized regex anchor patterns per insurer and merges them into an XOR/base64-"encrypted" (`vendor_patterns.enc`, not real cryptography) pattern store, which is later reused in `ocr.py` to bias future extraction for the same company. `sync_patterns_with_github()` does a scheduled bidirectional pull/merge/push of this file with the project's public GitHub repo — **treat this file with care: it will auto-commit and `git push origin main` from a running backend instance.** This only runs from the OCR extraction path itself (document create/reanalyze/inbox-analyze); don't re-add a secondary trigger on generic insurance-metadata updates, since that previously re-ran the encrypt/write cycle on every unrelated field edit for no benefit.
- `sanitizer.py` — Regex-based PII stripper (`sanitize_text_for_learning`) that must scrub names/addresses/IBANs/policy numbers/phone numbers/plates before any OCR text is persisted into the learned pattern store. Any change to `learning.py` that stores raw document text must go through this sanitizer first — zero-PII-leak is a hard product requirement, not a nice-to-have.
- `backup_scheduler.py` — Background thread wrapping the backup logic in `routers/backup.py` (retention by days/count, encrypted zip archives of DB + documents), plus a once-per-24h check that e-mails users an upcoming-cancellation-deadline reminder (`check_and_send_cancellation_notifications`, only sends if an admin has configured an SMTP server and the user opted in via `email_notifications_enabled`). The WebCal/iCal export in `routers/users.py` (14-/7-day calendar alarms) is a separate, SMTP-independent reminder path that always works.

### Frontend layout (`frontend/src/`)
- `app/` — Next.js App Router pages: `page.tsx` (dashboard/list), `insurance/[id]/page.tsx` (detail view with tabs: Stammdaten, Beitragsentwicklung, Dokumente, Schadensfälle, Notizen), `inbox/`, `login/`, `register/`, `admin-setup/`, `forgot-password/`, `reset-password/`, `session-expired/`, `settings/`.
- `components/` — feature components (`InsuranceDetail`, `UploadModal`, `CancellationModal`, `TaxExportModal`, `Navbar`, `ThemeProvider`, `CompanyLogo`, `Footer`) plus `components/ui/` shadcn primitives (base-nova style, see `components.json`; path aliases `@/components`, `@/lib`, `@/components/ui`).
- Auth token is stored in `localStorage` under `token`; there is no server-side session — all auth state is client-driven via the JWT and the `lib/api.ts` 401 handler.
- `ThemeProvider` implements the app's 6 named visual themes (Dunkel Neon, Klassisch Business Hell, Skandinavisch Warm, Executive Slate, Mint Frisch, Cyberpunk) — check it before adding hardcoded colors so new UI respects theme variables.

### Important cross-cutting behaviors to preserve
- **Non-destructive document uploads**: uploading a new document for an existing `Insurance` must never overwrite its display name, and must never touch `is_suspended`/`suspension_reason` — these are described in the README as guarantees ("Namensschutz & Ruhendstellungs-Garantie") and are checked for in `routers/documents.py` / `routers/insurances.py`.
- Certain `doc_type`s (Sonstiges, Verbraucherinformationen, Kundeninformationen) are archived as documents only and must not update `Insurance` contract fields.
- This version of Next.js/React (Next 16, React 19) may include breaking API/convention changes relative to older training data — the frontend's own `AGENTS.md`/`CLAUDE.md` (`frontend/AGENTS.md`) instructs checking `node_modules/next/dist/docs/` before writing Next.js code; follow that when touching `frontend/`.
