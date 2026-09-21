# Copyright (c) 2026 Dennis Guse. All rights reserved.
# Licensed under the MIT License. See LICENSE file in project root.

"""Notfall-Zugang: setzt das Passwort eines Administrators auf ein neues
Zufallspasswort zurück (z. B. wenn das initiale Passwort aus dem Log nicht mehr
auffindbar ist oder das Admin-Passwort vergessen wurde).

Aufruf auf dem Server:
    docker compose exec backend python reset_admin.py            # erster Admin
    docker compose exec backend python reset_admin.py "mail@x.de" # bestimmter Admin

Das Skript läuft nur mit direktem Zugriff auf den Container - es gibt keinen
Netzwerk-Endpunkt dafür. Alle bestehenden Sitzungen dieses Kontos werden beendet
und beim nächsten Login muss ein neues Passwort gewählt werden. Eine aktive
2-Faktor-Authentifizierung des Kontos wird dabei ebenfalls zurückgesetzt."""

import secrets
import sys

import audit
import auth
import models
from database import SessionLocal


def main():
    email = sys.argv[1] if len(sys.argv) > 1 else None
    db = SessionLocal()
    try:
        query = db.query(models.User).filter(models.User.is_admin == True)  # noqa: E712
        admin = auth.get_user_by_email(db, email) if email else query.order_by(models.User.id).first()
        if admin is None or not admin.is_admin:
            print("Kein passender Administrator gefunden.")
            sys.exit(1)

        new_password = secrets.token_urlsafe(12)
        admin.hashed_password = auth.get_password_hash(new_password)
        admin.must_change_password = True
        # A locked-out admin may also have lost the authenticator: whoever can run this
        # script has full control of the server anyway, so the second factor is cleared too.
        admin.totp_enabled = False
        admin.totp_secret = None
        admin.totp_last_step = 0
        admin.recovery_codes = None
        auth.revoke_tokens(admin)
        db.commit()
        audit.log_event(db, "password_reset_completed", user=admin, detail="reset_admin.py (Servertoolzugriff)")

        print(f"Benutzername: {admin.email}")
        print(f"Neues Einmal-Passwort: {new_password}")
        print("Beim nächsten Login muss ein eigenes Passwort festgelegt werden.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
