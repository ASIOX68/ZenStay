"""ZenStay iteration 3 backend tests:
 - POST /api/host-contact (public, Make webhook best-effort)
 - GET /api/admin/host-contacts (admin only)
 - POST /api/admin/upload (auth + image upload + size + type)
 - GET /api/files/{path} (serves uploaded file)
 - send_booking_confirmation helper (unit)
"""
import io
import os
import sys
import asyncio
import struct
import zlib
import pytest
import requests
from pymongo import MongoClient
from datetime import datetime, timezone, timedelta

BASE = os.environ.get("REACT_APP_BACKEND_URL", "https://calm-retreat-app.preview.emergentagent.com").rstrip("/")
API = f"{BASE}/api"
MONGO_URL = "mongodb://localhost:27017"
DB_NAME = "test_database"
ADMIN_TOKEN = "test_admin_session_zs3"
USER_TOKEN = "test_user_session_zs3"


@pytest.fixture(scope="module")
def db():
    return MongoClient(MONGO_URL)[DB_NAME]


@pytest.fixture(scope="module", autouse=True)
def seed_sessions(db):
    admin = db.users.find_one({"email": "admin@zenstay.com"})
    user = db.users.find_one({"email": "alice@zenstay.com"})
    assert admin and user, "Seed users not present"
    exp = datetime.now(timezone.utc) + timedelta(days=1)
    db.user_sessions.delete_many({"session_token": {"$in": [ADMIN_TOKEN, USER_TOKEN]}})
    db.user_sessions.insert_one({"user_id": admin["user_id"], "session_token": ADMIN_TOKEN, "expires_at": exp, "created_at": datetime.now(timezone.utc)})
    db.user_sessions.insert_one({"user_id": user["user_id"], "session_token": USER_TOKEN, "expires_at": exp, "created_at": datetime.now(timezone.utc)})
    yield
    db.user_sessions.delete_many({"session_token": {"$in": [ADMIN_TOKEN, USER_TOKEN]}})
    # Cleanup test host contacts and files
    db.host_contacts.delete_many({"email": {"$regex": "^TEST_"}})


def admin_h():
    return {"Authorization": f"Bearer {ADMIN_TOKEN}"}


def user_h():
    return {"Authorization": f"Bearer {USER_TOKEN}"}


def _png_bytes(w=2, h=2) -> bytes:
    """Minimal valid PNG (no external deps)."""
    def chunk(tag, data):
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xffffffff)
    sig = b"\x89PNG\r\n\x1a\n"
    ihdr = struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)  # 8-bit RGB
    raw = b""
    for _ in range(h):
        raw += b"\x00" + b"\xff\x00\x00" * w  # filter byte + red pixels
    idat = zlib.compress(raw)
    return sig + chunk(b"IHDR", ihdr) + chunk(b"IDAT", idat) + chunk(b"IEND", b"")


# ---------- Host contact ----------
class TestHostContact:
    def test_create_host_contact_public(self, db):
        payload = {
            "name": "Marie TEST_Host",
            "email": "TEST_marie@example.com",
            "location": "Brittany, France",
            "db_estimate": 24,
            "description": "Cabane silencieuse en forêt",
            "phone": "+33600000001",
        }
        r = requests.post(f"{API}/host-contact", json=payload, timeout=20)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["ok"] is True
        assert isinstance(data.get("id"), str) and len(data["id"]) > 0
        # Verify persistence
        rec = db.host_contacts.find_one({"id": data["id"]})
        assert rec is not None
        assert rec["email"] == payload["email"]
        assert rec["location"] == payload["location"]
        assert rec["status"] == "new"

    def test_create_host_contact_invalid_email(self):
        r = requests.post(f"{API}/host-contact", json={
            "name": "X", "email": "not-an-email", "location": "Y", "description": "Z"
        }, timeout=10)
        assert r.status_code == 422

    def test_admin_host_contacts_auth(self):
        assert requests.get(f"{API}/admin/host-contacts").status_code == 401
        assert requests.get(f"{API}/admin/host-contacts", headers=user_h()).status_code == 403
        r = requests.get(f"{API}/admin/host-contacts", headers=admin_h())
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, list)
        # at least our previously inserted one
        assert any(c.get("email", "").startswith("TEST_") for c in data) or len(data) > 0


# ---------- File upload ----------
class TestUpload:
    uploaded_path = None
    uploaded_url = None

    def test_upload_requires_auth(self):
        png = _png_bytes()
        files = {"file": ("a.png", png, "image/png")}
        r = requests.post(f"{API}/admin/upload", files=files, timeout=30)
        assert r.status_code == 401

    def test_upload_forbidden_for_user(self):
        png = _png_bytes()
        files = {"file": ("a.png", png, "image/png")}
        r = requests.post(f"{API}/admin/upload", files=files, headers=user_h(), timeout=30)
        assert r.status_code == 403

    def test_upload_rejects_non_image(self):
        files = {"file": ("a.txt", b"hello world", "text/plain")}
        r = requests.post(f"{API}/admin/upload", files=files, headers=admin_h(), timeout=30)
        assert r.status_code == 400

    def test_upload_rejects_oversize(self):
        big = b"\x00" * (8 * 1024 * 1024 + 1024)
        files = {"file": ("big.png", big, "image/png")}
        r = requests.post(f"{API}/admin/upload", files=files, headers=admin_h(), timeout=60)
        assert r.status_code == 413

    def test_upload_png_ok(self, db):
        png = _png_bytes(4, 4)
        files = {"file": ("test.png", png, "image/png")}
        r = requests.post(f"{API}/admin/upload", files=files, headers=admin_h(), timeout=60)
        assert r.status_code == 200, r.text
        data = r.json()
        assert "id" in data and "url" in data and "path" in data
        assert data["url"].endswith(data["path"])
        # persistence
        rec = db.files.find_one({"id": data["id"]})
        assert rec is not None and rec["content_type"] == "image/png"
        TestUpload.uploaded_path = data["path"]
        TestUpload.uploaded_url = data["url"]

    def test_serve_file_ok(self):
        assert TestUpload.uploaded_path, "upload test must run first"
        r = requests.get(f"{API}/files/{TestUpload.uploaded_path}", timeout=30)
        assert r.status_code == 200, r.text
        assert r.headers["content-type"].startswith("image/png")
        assert r.content[:8] == b"\x89PNG\r\n\x1a\n"

    def test_serve_file_not_found(self):
        r = requests.get(f"{API}/files/zenstay/uploads/none/missing.png", timeout=15)
        assert r.status_code == 404


# ---------- send_booking_confirmation unit ----------
class TestEmailHelper:
    def test_send_booking_confirmation_no_exception(self):
        sys.path.insert(0, "/app/backend")
        import server  # noqa: E402
        reservation = {
            "name": "Alice", "email": "noreply@zenstay.com",
            "date_arrivee": "2026-05-01", "date_depart": "2026-05-03",
            "voyageurs": 2, "montant": 200.0,
        }
        listing = {"titre": "Cabane Test", "ville": "Paimpont", "pays": "France"}
        # Should not raise even if Resend rejects
        asyncio.get_event_loop().run_until_complete(
            server.send_booking_confirmation(reservation, listing)
        )
