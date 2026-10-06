# Copyright (c) 2026 Dennis Guse
# SPDX-License-Identifier: MIT
# See the LICENSE file in the project root.

"""Shared fixtures. The app is started once against a throw-away SQLite database
in a temporary working directory (it keeps its data/ and documents/ folders
relative to the current directory), so nothing touches a real installation."""

import os
import sys
import tempfile

import pytest

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_WORKDIR = tempfile.mkdtemp(prefix="zettelfrieden-tests-")

# These must be set before the application modules are imported.
os.environ["SECRET_KEY"] = "test-secret-key-for-the-automated-test-suite-only"
os.environ["DATABASE_URL"] = "sqlite:///" + os.path.join(_WORKDIR, "test.db").replace("\\", "/")
os.environ["TRUSTED_PROXY_HOPS"] = "0"
os.chdir(_WORKDIR)
sys.path.insert(0, BACKEND_DIR)

ADMIN_EMAIL = "admin@test.example"
ADMIN_PASSWORD = "Admin-Testpasswort-2026"
USER_PASSWORD = "Tisch-Lampe-Sturm-2026"


@pytest.fixture(scope="session")
def client():
    from fastapi.testclient import TestClient
    import auth, models
    from database import SessionLocal
    from main import app

    with TestClient(app) as test_client:
        # The first start creates "Admin" with a random one-time password and
        # forces a change; replace that with known credentials.
        db = SessionLocal()
        admin = db.query(models.User).filter(models.User.is_admin == True).first()  # noqa: E712
        admin.email = ADMIN_EMAIL
        admin.hashed_password = auth.get_password_hash(ADMIN_PASSWORD)
        admin.must_change_password = False
        db.commit()
        db.close()
        yield test_client


@pytest.fixture(scope="session", autouse=True)
def isolated_pattern_store():
    """Extraction teaches the learned-pattern store. Work on a copy so a test run never changes
    the committed ``data/vendor_patterns.enc`` (it is read as before, only writes go to the copy)."""
    import shutil
    import learning
    copy = os.path.join(_WORKDIR, "vendor_patterns.enc")
    if os.path.exists(learning.ENC_FILE):
        shutil.copyfile(learning.ENC_FILE, copy)
    original = (learning.ENC_FILE, learning.JSON_LEGACY_FILE)
    learning.ENC_FILE = copy
    learning.JSON_LEGACY_FILE = os.path.join(_WORKDIR, "vendor_patterns.json")
    yield
    learning.ENC_FILE, learning.JSON_LEGACY_FILE = original


@pytest.fixture(autouse=True)
def fresh_rate_limits():
    import rate_limit
    rate_limit._windows.clear()  # every limiter keeps its state in this one table
    yield


def login(client, username, password, otp=None):
    body = {"username": username, "password": password}
    if otp:
        body["otp"] = otp
    return client.post("/api/users/login", json=body)


def bearer(token):
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="session")
def admin_headers(client):
    return bearer(login(client, ADMIN_EMAIL, ADMIN_PASSWORD).json()["access_token"])


@pytest.fixture()
def make_user(client, admin_headers):
    """Creates a user (through the admin-independent registration endpoint's
    logic, directly in the database, to stay clear of the registration rate
    limit) and returns (email, password, headers)."""
    import auth, models
    from database import SessionLocal
    counter = {"n": 0}

    def _make(prefix="user"):
        counter["n"] += 1
        email = f"{prefix}{counter['n']}-{os.urandom(3).hex()}@test.example"
        db = SessionLocal()
        db.add(models.User(email=email, hashed_password=auth.get_password_hash(USER_PASSWORD), is_admin=False, must_change_password=False))
        db.commit()
        db.close()
        token = login(client, email, USER_PASSWORD).json()["access_token"]
        return email, USER_PASSWORD, bearer(token)

    return _make
