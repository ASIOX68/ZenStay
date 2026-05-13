"""ZenStay iteration 4 backend tests:
- invoice_number generator format ZS-YYYYMM-XXXXXX (6 hex)
- _mark_reservation_paid_and_notify: paid + invoice_number assignment, idempotency
- _mark_reservation_paid_and_notify: missing reservation / missing listing must NOT raise
- send_host_notification helper: event in {'new','paid'} does not raise
- POST /api/reservations fires send_host_notification(event='new') best-effort (request succeeds)
- GET /api/reservations/me + GET /api/admin/reservations expose invoice_number after finalize
"""
import os
import re
import sys
import asyncio
import uuid
import pytest
import requests
from datetime import datetime, timezone, timedelta
from pymongo import MongoClient

BASE = os.environ.get("REACT_APP_BACKEND_URL", "https://calm-retreat-app.preview.emergentagent.com").rstrip("/")
API = f"{BASE}/api"
MONGO_URL = "mongodb://localhost:27017"
DB_NAME = "test_database"

ADMIN_TOKEN = "test_admin_session_zs4"
USER_TOKEN = "test_user_session_zs4"

INVOICE_RE = re.compile(r"^ZS-\d{6}-[0-9A-F]{6}$")


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
    db.user_sessions.insert_one({
        "user_id": admin["user_id"], "session_token": ADMIN_TOKEN,
        "expires_at": exp, "created_at": datetime.now(timezone.utc),
    })
    db.user_sessions.insert_one({
        "user_id": user["user_id"], "session_token": USER_TOKEN,
        "expires_at": exp, "created_at": datetime.now(timezone.utc),
    })
    yield
    db.user_sessions.delete_many({"session_token": {"$in": [ADMIN_TOKEN, USER_TOKEN]}})
    # cleanup test fixtures
    db.reservations.delete_many({"name": {"$regex": "^TEST_ZS4"}})
    db.listings.delete_many({"id": {"$regex": "^test-zs4-"}})


def admin_h():
    return {"Authorization": f"Bearer {ADMIN_TOKEN}"}


def user_h():
    return {"Authorization": f"Bearer {USER_TOKEN}"}


def _import_server():
    sys.path.insert(0, "/app/backend")
    import server  # noqa: WPS433
    return server


# ---------- invoice_number helper ----------
class TestInvoiceNumberFormat:
    def test_format_pattern(self):
        srv = _import_server()
        inv = srv._generate_invoice_number()
        assert INVOICE_RE.match(inv), f"unexpected format: {inv}"

    def test_uniqueness_batch(self):
        srv = _import_server()
        nums = {srv._generate_invoice_number() for _ in range(50)}
        # All must match pattern
        for n in nums:
            assert INVOICE_RE.match(n)
        # 6 hex chars => collisions extremely unlikely in 50 draws
        assert len(nums) == 50

    def test_yyyymm_matches_now(self):
        srv = _import_server()
        inv = srv._generate_invoice_number()
        now = datetime.now(timezone.utc)
        expected = f"{now.year}{now.month:02d}"
        assert inv.split("-")[1] == expected


# ---------- send_host_notification unit ----------
class TestHostNotificationHelper:
    def test_event_new_no_exception(self):
        srv = _import_server()
        reservation = {
            "name": "TEST_ZS4 Host-New",
            "email": "noreply@zenstay.com",
            "date_arrivee": "2026-06-01", "date_depart": "2026-06-03",
            "voyageurs": 2, "montant": 240.0,
        }
        listing = {
            "titre": "Cabane Test", "ville": "Paimpont", "pays": "France",
            "hote_email": "host_TEST_ZS4@example.com",
        }
        asyncio.get_event_loop().run_until_complete(
            srv.send_host_notification(reservation, listing, event="new")
        )

    def test_event_paid_no_exception(self):
        srv = _import_server()
        reservation = {
            "name": "TEST_ZS4 Host-Paid",
            "email": "noreply@zenstay.com",
            "date_arrivee": "2026-07-01", "date_depart": "2026-07-04",
            "voyageurs": 3, "montant": 510.0,
        }
        listing = {
            "titre": "Cabane Test", "ville": "Paimpont", "pays": "France",
            "hote_email": "host_TEST_ZS4@example.com",
        }
        asyncio.get_event_loop().run_until_complete(
            srv.send_host_notification(reservation, listing, event="paid")
        )

    def test_no_host_email_no_op(self):
        srv = _import_server()
        reservation = {"name": "n", "email": "e", "montant": 0}
        listing = {"titre": "x"}  # no hote_email
        # Should silently return without raising
        asyncio.get_event_loop().run_until_complete(
            srv.send_host_notification(reservation, listing, event="new")
        )


# ---------- _mark_reservation_paid_and_notify ----------
class TestMarkPaid:
    @pytest.fixture
    def seeded_reservation(self, db):
        """Create a listing + pending reservation owned by alice."""
        srv = _import_server()  # noqa
        listing_id = f"test-zs4-{uuid.uuid4().hex[:8]}"
        listing_doc = {
            "id": listing_id,
            "titre": "TEST_ZS4 Cabane",
            "ville": "Paimpont",
            "pays": "France",
            "prix_nuit": 100.0,
            "hote_email": "host_TEST_ZS4@example.com",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        db.listings.insert_one(listing_doc)

        alice = db.users.find_one({"email": "alice@zenstay.com"})
        rid = str(uuid.uuid4())
        res_doc = {
            "id": rid,
            "user_id": alice["user_id"],
            "logement_id": listing_id,
            "name": "TEST_ZS4 Alice",
            "email": "alice@zenstay.com",
            "date_arrivee": "2026-08-01",
            "date_depart": "2026-08-03",
            "voyageurs": 2,
            "montant": 200.0,
            "statut": "pending",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        db.reservations.insert_one(res_doc)
        yield rid
        db.reservations.delete_one({"id": rid})
        db.listings.delete_one({"id": listing_id})

    def test_missing_reservation_no_raise(self):
        srv = _import_server()
        asyncio.get_event_loop().run_until_complete(
            srv._mark_reservation_paid_and_notify("does-not-exist-zs4")
        )

    def test_missing_listing_no_raise(self, db):
        srv = _import_server()
        alice = db.users.find_one({"email": "alice@zenstay.com"})
        rid = str(uuid.uuid4())
        db.reservations.insert_one({
            "id": rid,
            "user_id": alice["user_id"],
            "logement_id": "nonexistent-listing-zs4",
            "name": "TEST_ZS4 NoListing",
            "email": "alice@zenstay.com",
            "date_arrivee": "2026-09-01",
            "date_depart": "2026-09-02",
            "voyageurs": 1,
            "montant": 100.0,
            "statut": "pending",
            "created_at": datetime.now(timezone.utc).isoformat(),
        })
        try:
            asyncio.get_event_loop().run_until_complete(
                srv._mark_reservation_paid_and_notify(rid)
            )
        finally:
            db.reservations.delete_one({"id": rid})

    def test_marks_paid_and_assigns_invoice(self, db, seeded_reservation):
        srv = _import_server()
        rid = seeded_reservation
        # Precondition
        before = db.reservations.find_one({"id": rid})
        assert before["statut"] == "pending"
        assert "invoice_number" not in before or before.get("invoice_number") in (None,)

        asyncio.get_event_loop().run_until_complete(
            srv._mark_reservation_paid_and_notify(rid)
        )

        after = db.reservations.find_one({"id": rid})
        assert after["statut"] == "paid"
        assert INVOICE_RE.match(after["invoice_number"]), f"bad invoice: {after.get('invoice_number')}"

    def test_idempotent_same_invoice_on_second_call(self, db, seeded_reservation):
        srv = _import_server()
        rid = seeded_reservation
        loop = asyncio.get_event_loop()
        loop.run_until_complete(srv._mark_reservation_paid_and_notify(rid))
        first = db.reservations.find_one({"id": rid})["invoice_number"]
        # second call
        loop.run_until_complete(srv._mark_reservation_paid_and_notify(rid))
        second = db.reservations.find_one({"id": rid})["invoice_number"]
        assert first == second
        # third call for extra assurance
        loop.run_until_complete(srv._mark_reservation_paid_and_notify(rid))
        third = db.reservations.find_one({"id": rid})["invoice_number"]
        assert third == first


# ---------- API contract: invoice_number exposed on listing endpoints ----------
class TestInvoiceExposedOnAPI:
    def test_admin_reservations_includes_invoice_number(self, db):
        srv = _import_server()
        # Seed a paid reservation directly via helper
        alice = db.users.find_one({"email": "alice@zenstay.com"})
        listing_id = f"test-zs4-{uuid.uuid4().hex[:8]}"
        db.listings.insert_one({
            "id": listing_id, "titre": "TEST_ZS4 API", "ville": "Paimpont",
            "pays": "France", "prix_nuit": 100.0,
            "hote_email": "host_TEST_ZS4@example.com",
            "created_at": datetime.now(timezone.utc).isoformat(),
        })
        rid = str(uuid.uuid4())
        db.reservations.insert_one({
            "id": rid, "user_id": alice["user_id"], "logement_id": listing_id,
            "name": "TEST_ZS4 ApiExpose", "email": "alice@zenstay.com",
            "date_arrivee": "2026-10-01", "date_depart": "2026-10-03",
            "voyageurs": 2, "montant": 200.0, "statut": "pending",
            "created_at": datetime.now(timezone.utc).isoformat(),
        })
        try:
            asyncio.get_event_loop().run_until_complete(
                srv._mark_reservation_paid_and_notify(rid)
            )
            # admin endpoint
            r = requests.get(f"{API}/admin/reservations", headers=admin_h(), timeout=20)
            assert r.status_code == 200, r.text
            data = r.json()
            mine = next((x for x in data if x.get("id") == rid), None)
            assert mine is not None
            assert mine["statut"] == "paid"
            assert INVOICE_RE.match(mine["invoice_number"])

            # user "me" endpoint
            r2 = requests.get(f"{API}/reservations/me", headers=user_h(), timeout=20)
            assert r2.status_code == 200, r2.text
            mine2 = next((x for x in r2.json() if x.get("id") == rid), None)
            assert mine2 is not None
            assert mine2["statut"] == "paid"
            assert INVOICE_RE.match(mine2["invoice_number"])
        finally:
            db.reservations.delete_one({"id": rid})
            db.listings.delete_one({"id": listing_id})


# ---------- E2E: POST /api/reservations triggers host email best-effort ----------
class TestCreateReservationFiresHostNew:
    def test_create_reservation_succeeds_with_host_notification(self, db):
        """Posting a reservation must succeed even though send_host_notification(event='new')
        runs synchronously inside the request. Resend failures are swallowed."""
        listing_id = f"test-zs4-{uuid.uuid4().hex[:8]}"
        db.listings.insert_one({
            "id": listing_id, "titre": "TEST_ZS4 Create", "ville": "Paimpont",
            "pays": "France", "prix_nuit": 90.0,
            "hote_email": "host_TEST_ZS4@example.com",
            "created_at": datetime.now(timezone.utc).isoformat(),
        })
        try:
            payload = {
                "logement_id": listing_id,
                "name": "TEST_ZS4 Bob",
                "email": "bob_TEST_ZS4@example.com",
                "date_arrivee": "2026-11-01",
                "date_depart": "2026-11-04",
                "voyageurs": 2,
            }
            r = requests.post(f"{API}/reservations", json=payload, headers=user_h(), timeout=30)
            assert r.status_code == 200, r.text
            body = r.json()
            assert body["statut"] == "pending"
            # invoice_number must NOT be set yet (payment still pending)
            assert body.get("invoice_number") in (None,) or "invoice_number" not in body
            assert body["montant"] == 90.0 * 3
            # cleanup
            db.reservations.delete_one({"id": body["id"]})
        finally:
            db.listings.delete_one({"id": listing_id})
