"""ZenStay backend API tests."""
import os
import pytest
import requests
from pymongo import MongoClient
from datetime import datetime, timezone, timedelta

BASE = os.environ.get("REACT_APP_BACKEND_URL", "https://calm-retreat-app.preview.emergentagent.com").rstrip("/")
API = f"{BASE}/api"

MONGO_URL = "mongodb://localhost:27017"
DB_NAME = "test_database"

ADMIN_TOKEN = "test_admin_session_zs"
USER_TOKEN = "test_user_session_zs"


@pytest.fixture(scope="module")
def db():
    c = MongoClient(MONGO_URL)
    return c[DB_NAME]


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


def admin_h():
    return {"Authorization": f"Bearer {ADMIN_TOKEN}"}


def user_h():
    return {"Authorization": f"Bearer {USER_TOKEN}"}


# ---------- Health ----------
def test_root():
    r = requests.get(f"{API}/")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


# ---------- Listings ----------
def test_listings_public():
    r = requests.get(f"{API}/listings")
    assert r.status_code == 200
    data = r.json()
    assert len(data) >= 6
    for d in data:
        assert "hote_email" not in d, "hote_email leaked to public"
        assert "id" in d and "titre" in d and "prix_nuit" in d and "db_nuit" in d


def test_listing_detail():
    r = requests.get(f"{API}/listings")
    lid = r.json()[0]["id"]
    r2 = requests.get(f"{API}/listings/{lid}")
    assert r2.status_code == 200
    assert "hote_email" not in r2.json()


def test_listing_not_found():
    assert requests.get(f"{API}/listings/nope").status_code == 404


# ---------- Auth ----------
def test_session_bad():
    r = requests.post(f"{API}/auth/session", json={"session_id": "invalid_xyz"})
    assert r.status_code == 401


def test_session_missing():
    r = requests.post(f"{API}/auth/session", json={})
    assert r.status_code == 400


def test_me_no_auth():
    assert requests.get(f"{API}/auth/me").status_code == 401


def test_me_bearer():
    r = requests.get(f"{API}/auth/me", headers=admin_h())
    assert r.status_code == 200
    assert r.json()["email"] == "admin@zenstay.com"
    assert r.json()["role"] == "admin"


# ---------- Reservations ----------
def test_reservation_requires_auth():
    r = requests.post(f"{API}/reservations", json={"logement_id": "x", "name": "a", "email": "a@a.com", "date_arrivee": "2026-02-01", "date_depart": "2026-02-03"})
    assert r.status_code == 401


def test_reservation_create_and_list():
    listings = requests.get(f"{API}/listings").json()
    lst = listings[0]
    payload = {
        "logement_id": lst["id"],
        "name": "Alice Test",
        "email": "alice@zenstay.com",
        "date_arrivee": "2026-03-01",
        "date_depart": "2026-03-04",
        "voyageurs": 2,
    }
    r = requests.post(f"{API}/reservations", json=payload, headers=user_h())
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["montant"] == round(lst["prix_nuit"] * 3, 2)
    assert data["statut"] == "pending"
    assert data["user_id"]
    rid = data["id"]
    # list own
    mine = requests.get(f"{API}/reservations/me", headers=user_h())
    assert mine.status_code == 200
    assert any(x["id"] == rid for x in mine.json())
    # admin must not see this in /reservations/me with admin token (different user)
    admin_mine = requests.get(f"{API}/reservations/me", headers=admin_h()).json()
    assert not any(x["id"] == rid for x in admin_mine)
    return rid


# ---------- Admin ----------
def test_admin_listings_auth():
    assert requests.get(f"{API}/admin/listings").status_code == 401
    assert requests.get(f"{API}/admin/listings", headers=user_h()).status_code == 403
    r = requests.get(f"{API}/admin/listings", headers=admin_h())
    assert r.status_code == 200
    assert any("hote_email" in d for d in r.json())


def test_admin_crud_listing():
    payload = {
        "titre": "TEST_Cabane",
        "ville": "Test",
        "prix_nuit": 100.0,
        "image_url": "http://x/img.jpg",
        "description": "test",
        "hote_email": "test@host.com",
        "db_nuit": 25,
    }
    # create
    r = requests.post(f"{API}/admin/listings", json=payload, headers=admin_h())
    assert r.status_code == 200, r.text
    lid = r.json()["id"]
    # update
    payload["titre"] = "TEST_Cabane_updated"
    r2 = requests.put(f"{API}/admin/listings/{lid}", json=payload, headers=admin_h())
    assert r2.status_code == 200
    assert r2.json()["titre"] == "TEST_Cabane_updated"
    # toggle
    r3 = requests.patch(f"{API}/admin/listings/{lid}/toggle", headers=admin_h())
    assert r3.status_code == 200
    assert r3.json()["disponible"] is False
    # delete
    r4 = requests.delete(f"{API}/admin/listings/{lid}", headers=admin_h())
    assert r4.status_code == 200
    assert requests.get(f"{API}/listings/{lid}").status_code == 404


def test_admin_reservations_auth():
    assert requests.get(f"{API}/admin/reservations").status_code == 401
    assert requests.get(f"{API}/admin/reservations", headers=user_h()).status_code == 403
    r = requests.get(f"{API}/admin/reservations", headers=admin_h())
    assert r.status_code == 200
    assert isinstance(r.json(), list)


# ---------- Payments ----------
def test_payment_requires_auth():
    r = requests.post(f"{API}/payments/checkout", json={"reservation_id": "x", "origin_url": BASE})
    assert r.status_code == 401


def test_payment_checkout_and_status():
    listings = requests.get(f"{API}/listings").json()
    lst = listings[0]
    res = requests.post(f"{API}/reservations", json={
        "logement_id": lst["id"], "name": "Alice", "email": "alice@zenstay.com",
        "date_arrivee": "2026-04-01", "date_depart": "2026-04-02"
    }, headers=user_h()).json()
    r = requests.post(f"{API}/payments/checkout", json={"reservation_id": res["id"], "origin_url": BASE}, headers=user_h())
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["url"].startswith("https://")
    sid = data["session_id"]
    r2 = requests.get(f"{API}/payments/status/{sid}")
    assert r2.status_code == 200
    assert "payment_status" in r2.json()


def test_payment_status_unknown():
    assert requests.get(f"{API}/payments/status/no_such").status_code == 404
