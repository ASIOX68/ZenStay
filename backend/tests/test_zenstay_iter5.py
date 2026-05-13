"""ZenStay iteration 5 — host portal + public invoice tests.

Covers:
- GET /api/invoices/{invoice_number} public-by-link (no auth)
- GET /api/host/me, /api/host/listings, /api/host/reservations, /api/host/stats
- PUT /api/host/listings/{id}, PATCH /api/host/listings/{id}/toggle (with 403/404)
- send_booking_confirmation accepts app_origin (None and set)
"""
import os
import re
import sys
import uuid
import asyncio
import pytest
import requests
from datetime import datetime, timezone, timedelta
from pymongo import MongoClient

BASE = os.environ.get("REACT_APP_BACKEND_URL", "https://calm-retreat-app.preview.emergentagent.com").rstrip("/")
API = f"{BASE}/api"
MONGO_URL = "mongodb://localhost:27017"
DB_NAME = "test_database"

HOST_TOKEN = "test_host_session_zs5"
USER_TOKEN = "test_user_session_zs5"
ADMIN_TOKEN = "test_admin_session_zs5"

HOST_EMAIL = "marie.host@zenstay.com"
NON_HOST_EMAIL = "ben@zenstay.com"
INVOICE_RE = re.compile(r"^ZS-\d{6}-[0-9A-F]{6}$")


@pytest.fixture(scope="module")
def db():
    return MongoClient(MONGO_URL)[DB_NAME]


@pytest.fixture(scope="module", autouse=True)
def seed_sessions(db):
    # Ensure host user exists (marie.host@zenstay.com)
    if not db.users.find_one({"email": HOST_EMAIL}):
        db.users.insert_one({
            "user_id": f"user_{uuid.uuid4().hex[:12]}",
            "email": HOST_EMAIL,
            "name": "Marie Host",
            "picture": None,
            "role": "user",
            "created_at": datetime.now(timezone.utc).isoformat(),
        })
    host = db.users.find_one({"email": HOST_EMAIL})
    ben = db.users.find_one({"email": NON_HOST_EMAIL})
    admin = db.users.find_one({"email": "admin@zenstay.com"})
    assert host and ben and admin, "Seed users missing"

    exp = datetime.now(timezone.utc) + timedelta(days=1)
    tokens = [HOST_TOKEN, USER_TOKEN, ADMIN_TOKEN]
    db.user_sessions.delete_many({"session_token": {"$in": tokens}})
    db.user_sessions.insert_many([
        {"user_id": host["user_id"], "session_token": HOST_TOKEN, "expires_at": exp, "created_at": datetime.now(timezone.utc)},
        {"user_id": ben["user_id"], "session_token": USER_TOKEN, "expires_at": exp, "created_at": datetime.now(timezone.utc)},
        {"user_id": admin["user_id"], "session_token": ADMIN_TOKEN, "expires_at": exp, "created_at": datetime.now(timezone.utc)},
    ])
    yield
    db.user_sessions.delete_many({"session_token": {"$in": tokens}})
    db.reservations.delete_many({"name": {"$regex": "^TEST_ZS5"}})
    db.listings.delete_many({"id": {"$regex": "^test-zs5-"}})


def H(tok): return {"Authorization": f"Bearer {tok}"}


def _import_server():
    sys.path.insert(0, "/app/backend")
    import server  # noqa
    return server


# ---------- Public Invoice ----------
class TestPublicInvoice:
    def test_404_unknown(self):
        r = requests.get(f"{API}/invoices/ZS-209901-DEADBE", timeout=15)
        assert r.status_code == 404

    def test_paid_invoice_payload(self, db):
        srv = _import_server()
        listing_id = f"test-zs5-{uuid.uuid4().hex[:8]}"
        db.listings.insert_one({
            "id": listing_id, "titre": "TEST_ZS5 Invoice Cabin",
            "ville": "Paimpont", "pays": "France", "prix_nuit": 120.0,
            "image_url": "x", "description": "x", "note": 4.8, "db_nuit": 30,
            "hote_email": HOST_EMAIL, "disponible": True,
            "created_at": datetime.now(timezone.utc).isoformat(),
        })
        ben = db.users.find_one({"email": NON_HOST_EMAIL})
        rid = str(uuid.uuid4())
        db.reservations.insert_one({
            "id": rid, "user_id": ben["user_id"], "logement_id": listing_id,
            "name": "TEST_ZS5 InvoiceUser", "email": NON_HOST_EMAIL,
            "date_arrivee": "2026-08-01", "date_depart": "2026-08-04",
            "voyageurs": 2, "montant": 360.0, "statut": "pending",
            "created_at": datetime.now(timezone.utc).isoformat(),
        })
        try:
            asyncio.get_event_loop().run_until_complete(
                srv._mark_reservation_paid_and_notify(rid)
            )
            after = db.reservations.find_one({"id": rid})
            inv = after["invoice_number"]
            assert INVOICE_RE.match(inv)

            r = requests.get(f"{API}/invoices/{inv}", timeout=15)
            assert r.status_code == 200, r.text
            data = r.json()
            for k in ["invoice_number", "name", "email", "date_arrivee",
                      "date_depart", "voyageurs", "nights", "prix_nuit",
                      "subtotal", "total", "currency", "statut", "listing"]:
                assert k in data, f"missing key {k}"
            assert data["invoice_number"] == inv
            assert data["nights"] == 3
            assert data["prix_nuit"] == 120.0
            assert data["subtotal"] == 360.0
            assert data["total"] == 360.0
            assert data["currency"] == "EUR"
            assert data["statut"] == "paid"
            # privacy: listing must NOT contain hote_email
            assert "hote_email" not in data["listing"]
        finally:
            db.reservations.delete_one({"id": rid})
            db.listings.delete_one({"id": listing_id})

    def test_no_auth_required(self):
        # explicitly send no header; just confirm 404 (not 401) for unknown id
        r = requests.get(f"{API}/invoices/ZS-000000-XXXXXX", timeout=10)
        assert r.status_code == 404


# ---------- /api/host/me ----------
class TestHostMe:
    def test_unauthenticated(self):
        r = requests.get(f"{API}/host/me", timeout=15)
        assert r.status_code == 401

    def test_non_host_returns_false(self):
        r = requests.get(f"{API}/host/me", headers=H(USER_TOKEN), timeout=15)
        assert r.status_code == 200
        data = r.json()
        assert data["is_host"] is False
        assert data["listing_count"] == 0

    def test_host_returns_true(self):
        r = requests.get(f"{API}/host/me", headers=H(HOST_TOKEN), timeout=15)
        assert r.status_code == 200
        data = r.json()
        assert data["is_host"] is True
        assert data["listing_count"] >= 1
        assert data["email"] == HOST_EMAIL


# ---------- /api/host/listings ----------
class TestHostListings:
    def test_host_sees_own(self):
        r = requests.get(f"{API}/host/listings", headers=H(HOST_TOKEN), timeout=15)
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        for l in data:
            assert l["hote_email"] == HOST_EMAIL

    def test_non_host_sees_empty(self):
        r = requests.get(f"{API}/host/listings", headers=H(USER_TOKEN), timeout=15)
        assert r.status_code == 200
        assert r.json() == []


# ---------- PUT /api/host/listings/{id} ----------
class TestHostUpdateListing:
    def test_404_unknown(self):
        payload = {
            "titre": "x", "ville": "x", "pays": "x", "prix_nuit": 1,
            "image_url": "x", "description": "x", "hote_email": HOST_EMAIL,
        }
        r = requests.put(f"{API}/host/listings/does-not-exist", json=payload,
                         headers=H(HOST_TOKEN), timeout=15)
        assert r.status_code == 404

    def test_403_not_owner(self, db):
        # User ben tries to update marie's listing
        marie_listing = db.listings.find_one({"hote_email": HOST_EMAIL})
        payload = {
            "titre": "hack", "ville": "x", "pays": "x", "prix_nuit": 1,
            "image_url": "x", "description": "x", "hote_email": NON_HOST_EMAIL,
        }
        r = requests.put(f"{API}/host/listings/{marie_listing['id']}",
                         json=payload, headers=H(USER_TOKEN), timeout=15)
        assert r.status_code == 403

    def test_host_updates_own_preserves_hote_email(self, db):
        marie_listing = db.listings.find_one({"hote_email": HOST_EMAIL})
        original_title = marie_listing["titre"]
        new_title = f"TEST_ZS5 Updated {uuid.uuid4().hex[:6]}"
        payload = {
            "titre": new_title,
            "ville": marie_listing["ville"],
            "pays": marie_listing.get("pays", "France"),
            "prix_nuit": float(marie_listing["prix_nuit"]) + 5.0,
            "image_url": marie_listing["image_url"],
            "description": marie_listing["description"],
            "hote_email": "attacker@evil.com",  # attempt reassignment
        }
        try:
            r = requests.put(f"{API}/host/listings/{marie_listing['id']}",
                             json=payload, headers=H(HOST_TOKEN), timeout=15)
            assert r.status_code == 200, r.text
            body = r.json()
            assert body["titre"] == new_title
            # hote_email MUST be preserved (server-side enforced)
            assert body["hote_email"] == HOST_EMAIL
            # verify persistence via DB
            persisted = db.listings.find_one({"id": marie_listing["id"]})
            assert persisted["hote_email"] == HOST_EMAIL
            assert persisted["titre"] == new_title
        finally:
            # restore
            db.listings.update_one(
                {"id": marie_listing["id"]},
                {"$set": {"titre": original_title,
                          "prix_nuit": float(marie_listing["prix_nuit"])}},
            )

    def test_admin_can_edit_other_host(self, db):
        marie_listing = db.listings.find_one({"hote_email": HOST_EMAIL})
        original_title = marie_listing["titre"]
        new_title = f"TEST_ZS5 AdminEdit {uuid.uuid4().hex[:6]}"
        payload = {
            "titre": new_title,
            "ville": marie_listing["ville"],
            "pays": marie_listing.get("pays", "France"),
            "prix_nuit": float(marie_listing["prix_nuit"]),
            "image_url": marie_listing["image_url"],
            "description": marie_listing["description"],
            "hote_email": "x@x.com",
        }
        try:
            r = requests.put(f"{API}/host/listings/{marie_listing['id']}",
                             json=payload, headers=H(ADMIN_TOKEN), timeout=15)
            assert r.status_code == 200
            body = r.json()
            # hote_email preserved even for admin
            assert body["hote_email"] == HOST_EMAIL
            assert body["titre"] == new_title
        finally:
            db.listings.update_one({"id": marie_listing["id"]},
                                   {"$set": {"titre": original_title}})


# ---------- PATCH /api/host/listings/{id}/toggle ----------
class TestHostToggle:
    def test_404_unknown(self):
        r = requests.patch(f"{API}/host/listings/nope/toggle",
                           headers=H(HOST_TOKEN), timeout=15)
        assert r.status_code == 404

    def test_403_not_owner(self, db):
        marie = db.listings.find_one({"hote_email": HOST_EMAIL})
        r = requests.patch(f"{API}/host/listings/{marie['id']}/toggle",
                           headers=H(USER_TOKEN), timeout=15)
        assert r.status_code == 403

    def test_host_toggles_own(self, db):
        marie = db.listings.find_one({"hote_email": HOST_EMAIL})
        original = bool(marie.get("disponible", True))
        try:
            r1 = requests.patch(f"{API}/host/listings/{marie['id']}/toggle",
                                headers=H(HOST_TOKEN), timeout=15)
            assert r1.status_code == 200
            assert r1.json()["disponible"] == (not original)
            r2 = requests.patch(f"{API}/host/listings/{marie['id']}/toggle",
                                headers=H(HOST_TOKEN), timeout=15)
            assert r2.json()["disponible"] == original
        finally:
            db.listings.update_one({"id": marie["id"]},
                                   {"$set": {"disponible": original}})


# ---------- /api/host/reservations ----------
class TestHostReservations:
    def test_empty_for_non_host(self):
        r = requests.get(f"{API}/host/reservations", headers=H(USER_TOKEN), timeout=15)
        assert r.status_code == 200
        assert r.json() == []

    def test_host_sees_reservations_on_own_listings(self, db):
        marie = db.listings.find_one({"hote_email": HOST_EMAIL})
        ben = db.users.find_one({"email": NON_HOST_EMAIL})
        rid = str(uuid.uuid4())
        db.reservations.insert_one({
            "id": rid, "user_id": ben["user_id"], "logement_id": marie["id"],
            "name": "TEST_ZS5 ResVisible", "email": NON_HOST_EMAIL,
            "date_arrivee": "2026-09-01", "date_depart": "2026-09-03",
            "voyageurs": 2, "montant": 200.0, "statut": "pending",
            "created_at": datetime.now(timezone.utc).isoformat(),
        })
        try:
            r = requests.get(f"{API}/host/reservations", headers=H(HOST_TOKEN), timeout=15)
            assert r.status_code == 200
            data = r.json()
            mine = next((x for x in data if x.get("id") == rid), None)
            assert mine is not None
            assert mine["listing_titre"] == marie["titre"]
            assert mine["listing_ville"] == marie["ville"]
        finally:
            db.reservations.delete_one({"id": rid})


# ---------- /api/host/stats ----------
class TestHostStats:
    def test_zero_for_non_host(self):
        r = requests.get(f"{API}/host/stats", headers=H(USER_TOKEN), timeout=15)
        assert r.status_code == 200
        data = r.json()
        assert data["listings"] == 0
        assert data["reservations_total"] == 0
        assert data["revenue_paid_eur"] == 0.0
        assert data["revenue_pending_eur"] == 0.0

    def test_host_stats_revenues(self, db):
        srv = _import_server()
        marie = db.listings.find_one({"hote_email": HOST_EMAIL})
        ben = db.users.find_one({"email": NON_HOST_EMAIL})
        rid_pending = str(uuid.uuid4())
        rid_paid = str(uuid.uuid4())
        db.reservations.insert_many([
            {"id": rid_pending, "user_id": ben["user_id"], "logement_id": marie["id"],
             "name": "TEST_ZS5 StatPending", "email": NON_HOST_EMAIL,
             "date_arrivee": "2026-12-01", "date_depart": "2026-12-03",
             "voyageurs": 1, "montant": 150.0, "statut": "pending",
             "created_at": datetime.now(timezone.utc).isoformat()},
            {"id": rid_paid, "user_id": ben["user_id"], "logement_id": marie["id"],
             "name": "TEST_ZS5 StatPaid", "email": NON_HOST_EMAIL,
             "date_arrivee": "2026-12-10", "date_depart": "2026-12-12",
             "voyageurs": 1, "montant": 250.0, "statut": "pending",
             "created_at": datetime.now(timezone.utc).isoformat()},
        ])
        try:
            asyncio.get_event_loop().run_until_complete(
                srv._mark_reservation_paid_and_notify(rid_paid)
            )
            r = requests.get(f"{API}/host/stats", headers=H(HOST_TOKEN), timeout=15)
            assert r.status_code == 200
            data = r.json()
            assert data["listings"] >= 1
            assert data["reservations_paid"] >= 1
            assert data["reservations_pending"] >= 1
            # revenues must include our seeded rows
            assert data["revenue_paid_eur"] >= 250.0
            assert data["revenue_pending_eur"] >= 150.0
        finally:
            db.reservations.delete_one({"id": rid_pending})
            db.reservations.delete_one({"id": rid_paid})


# ---------- send_booking_confirmation accepts app_origin ----------
class TestBookingConfirmationAppOrigin:
    def test_app_origin_none(self):
        srv = _import_server()
        reservation = {
            "name": "TEST_ZS5", "email": "noreply@zenstay.com",
            "date_arrivee": "2026-01-01", "date_depart": "2026-01-02",
            "voyageurs": 1, "montant": 100.0, "invoice_number": "ZS-202601-AAAAAA",
        }
        listing = {"titre": "x", "ville": "x", "pays": "x", "prix_nuit": 100.0,
                   "hote_email": "host@x.com"}
        asyncio.get_event_loop().run_until_complete(
            srv.send_booking_confirmation(reservation, listing, app_origin=None)
        )

    def test_app_origin_set(self):
        srv = _import_server()
        reservation = {
            "name": "TEST_ZS5", "email": "noreply@zenstay.com",
            "date_arrivee": "2026-01-01", "date_depart": "2026-01-02",
            "voyageurs": 1, "montant": 100.0, "invoice_number": "ZS-202601-BBBBBB",
        }
        listing = {"titre": "x", "ville": "x", "pays": "x", "prix_nuit": 100.0,
                   "hote_email": "host@x.com"}
        asyncio.get_event_loop().run_until_complete(
            srv.send_booking_confirmation(reservation, listing, app_origin="https://example.com/")
        )
