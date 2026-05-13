from fastapi import FastAPI, APIRouter, HTTPException, Request, Response, Depends, Cookie, Header, UploadFile, File
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import asyncio
import logging
import uuid
import httpx
import requests
import resend
from pathlib import Path
from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone, timedelta
from emergentintegrations.payments.stripe.checkout import (
    StripeCheckout,
    CheckoutSessionResponse,
    CheckoutStatusResponse,
    CheckoutSessionRequest,
)
import stripe as stripe_sdk

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

# ---------- DB ----------
mongo_url = os.environ["MONGO_URL"]
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ["DB_NAME"]]

# ---------- App ----------
app = FastAPI(title="ZenStay API")
api_router = APIRouter(prefix="/api")

STRIPE_API_KEY = os.environ.get("STRIPE_API_KEY", "")
MAKE_WEBHOOK_URL = os.environ.get("MAKE_WEBHOOK_URL", "")
ADMIN_EMAIL = "admin@zenstay.com"
RESEND_API_KEY = os.environ.get("RESEND_API_KEY", "")
SENDER_EMAIL = os.environ.get("SENDER_EMAIL", "onboarding@resend.dev")
EMERGENT_LLM_KEY = os.environ.get("EMERGENT_LLM_KEY", "")
APP_NAME = os.environ.get("APP_NAME", "zenstay")
STORAGE_URL = "https://integrations.emergentagent.com/objstore/api/v1/storage"

if RESEND_API_KEY:
    resend.api_key = RESEND_API_KEY

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("zenstay")

# ---------- Object storage ----------
_storage_key: Optional[str] = None

def init_storage() -> Optional[str]:
    global _storage_key
    if _storage_key:
        return _storage_key
    if not EMERGENT_LLM_KEY:
        return None
    try:
        r = requests.post(
            f"{STORAGE_URL}/init",
            json={"emergent_key": EMERGENT_LLM_KEY},
            timeout=30,
        )
        r.raise_for_status()
        _storage_key = r.json()["storage_key"]
        return _storage_key
    except Exception as e:
        logger.warning(f"Storage init failed: {e}")
        return None


def put_object(path: str, data: bytes, content_type: str) -> Dict[str, Any]:
    key = init_storage()
    if not key:
        raise HTTPException(status_code=500, detail="Storage unavailable")
    r = requests.put(
        f"{STORAGE_URL}/objects/{path}",
        headers={"X-Storage-Key": key, "Content-Type": content_type},
        data=data,
        timeout=120,
    )
    r.raise_for_status()
    return r.json()


def get_object(path: str) -> tuple:
    key = init_storage()
    if not key:
        raise HTTPException(status_code=500, detail="Storage unavailable")
    r = requests.get(
        f"{STORAGE_URL}/objects/{path}",
        headers={"X-Storage-Key": key},
        timeout=60,
    )
    r.raise_for_status()
    return r.content, r.headers.get("Content-Type", "application/octet-stream")


# ---------- Email ----------
def _format_eur(v: float) -> str:
    return f"{v:,.2f}".replace(",", " ").replace(".", ",")


def _nights_count(date_arrivee: str, date_depart: str) -> int:
    try:
        a = datetime.fromisoformat(date_arrivee)
        b = datetime.fromisoformat(date_depart)
        return max(1, (b.date() - a.date()).days)
    except Exception:
        return 1


def _generate_invoice_number() -> str:
    now = datetime.now(timezone.utc)
    return f"ZS-{now.year}{now.month:02d}-{uuid.uuid4().hex[:6].upper()}"


async def _resend_send(to_email: str, subject: str, html: str) -> None:
    if not RESEND_API_KEY:
        logger.info(f"RESEND_API_KEY missing — skip email to {to_email}")
        return
    try:
        await asyncio.to_thread(
            resend.Emails.send,
            {"from": SENDER_EMAIL, "to": [to_email], "subject": subject, "html": html},
        )
        logger.info(f"Resend → {to_email} · {subject}")
    except Exception as e:
        logger.warning(f"Resend send failed to {to_email}: {e}")


def _email_shell(title: str, intro: str, rows_html: str, footer: str) -> str:
    return f"""
    <table cellpadding="0" cellspacing="0" border="0" width="100%" style="background:#FAF9F6;font-family:Helvetica,Arial,sans-serif;color:#1A1C1A">
      <tr><td align="center" style="padding:40px 20px">
        <table width="600" cellpadding="0" cellspacing="0" border="0" style="background:#ffffff;border:1px solid #E2E0D8;border-radius:14px">
          <tr><td style="padding:32px 32px 16px 32px">
            <p style="font-size:11px;letter-spacing:0.25em;text-transform:uppercase;color:#4A7C59;margin:0 0 10px 0">ZenStay</p>
            <h1 style="font-family:Georgia,serif;font-weight:500;font-size:28px;line-height:1.15;margin:0 0 8px 0">{title}</h1>
            <p style="font-size:14px;color:#6B726B;margin:0 0 20px 0">{intro}</p>
          </td></tr>
          <tr><td style="padding:0 32px 20px 32px">
            <table width="100%" cellpadding="10" cellspacing="0" border="0" style="background:#F0EFEA;border-radius:10px;font-size:13px">
              {rows_html}
            </table>
          </td></tr>
          <tr><td style="padding:0 32px 32px 32px;font-size:12px;color:#6B726B;line-height:1.6">
            {footer}
          </td></tr>
        </table>
      </td></tr>
    </table>
    """


def _kv(label: str, value: str, *, strong: bool = False, sep: bool = False) -> str:
    border = "border-top:1px solid #E2E0D8;padding-top:10px;" if sep else ""
    weight = "font-weight:600;" if strong else ""
    return (
        f"<tr><td style='color:#6B726B;{border}'>{label}</td>"
        f"<td align='right' style='{border}{weight}'>{value}</td></tr>"
    )


async def send_booking_confirmation(reservation: Dict[str, Any], listing: Dict[str, Any]) -> None:
    """Client invoice email — sent after Stripe payment is paid."""
    total = _format_eur(float(reservation.get("montant", 0)))
    nights = _nights_count(reservation.get("date_arrivee", ""), reservation.get("date_depart", ""))
    invoice_no = reservation.get("invoice_number") or _generate_invoice_number()
    issued = datetime.now(timezone.utc).strftime("%d/%m/%Y")
    prix_nuit = float(listing.get("prix_nuit", 0))
    subject = f"ZenStay — facture {invoice_no} · {listing.get('titre', '')}"
    rows = (
        _kv("Facture n°", invoice_no, strong=True)
        + _kv("Émise le", issued)
        + _kv("Bénéficiaire", reservation.get("name", ""))
        + _kv("Email", reservation.get("email", ""))
        + _kv("Séjour", listing.get("titre", ""), sep=True)
        + _kv("Lieu", f"{listing.get('ville','')}, {listing.get('pays','')}")
        + _kv("Arrivée", reservation.get("date_arrivee", ""))
        + _kv("Départ", reservation.get("date_depart", ""))
        + _kv("Voyageurs", str(reservation.get("voyageurs", "")))
        + _kv(f"Tarif · {nights} × {_format_eur(prix_nuit)} €", f"{_format_eur(prix_nuit * nights)} €", sep=True)
        + _kv("Total payé TTC", f"{total} €", strong=True, sep=True)
    )
    footer = (
        "<p style='margin:0 0 8px 0'>Les coordonnées exactes de votre hôte vous seront transmises 24h avant l'arrivée.</p>"
        "<p style='margin:0 0 8px 0;color:#A1A6A1;font-size:11px'>"
        "Conservez ce document — il vaut facture. Aucune TVA appliquée (régime exonéré loueur particulier)."
        "</p>"
        "<p style='margin:0'>Bon repos.<br/>— L'équipe ZenStay</p>"
    )
    html = _email_shell(
        title="Paiement reçu — séjour confirmé",
        intro=f"Merci {reservation.get('name','')}. Voici votre confirmation et votre facture.",
        rows_html=rows,
        footer=footer,
    )
    await _resend_send(reservation["email"], subject, html)


async def send_host_notification(
    reservation: Dict[str, Any], listing: Dict[str, Any], event: str
) -> None:
    """Host email — event in {'new','paid'}.
    'new'  = traveler created a reservation (payment pending)
    'paid' = Stripe payment succeeded
    """
    host_email = listing.get("hote_email")
    if not host_email:
        return
    total = _format_eur(float(reservation.get("montant", 0)))
    if event == "new":
        title = "Nouvelle demande de réservation"
        intro = (
            f"{reservation.get('name','')} souhaite séjourner chez vous. "
            "Le paiement est en attente — nous vous notifierons dès qu'il est confirmé."
        )
        subject = f"ZenStay — nouvelle demande · {listing.get('titre','')}"
        status_label = "En attente de paiement"
    else:
        title = "Réservation confirmée et payée"
        intro = (
            f"Le paiement de {reservation.get('name','')} est confirmé. "
            "Préparez l'accueil — la confidentialité est notre engagement."
        )
        subject = f"ZenStay — réservation payée · {listing.get('titre','')}"
        status_label = "Payée"

    rows = (
        _kv("Voyageur", reservation.get("name", ""))
        + _kv("Email", reservation.get("email", ""))
        + _kv("Hébergement", listing.get("titre", ""), sep=True)
        + _kv("Arrivée", reservation.get("date_arrivee", ""))
        + _kv("Départ", reservation.get("date_depart", ""))
        + _kv("Voyageurs", str(reservation.get("voyageurs", "")))
        + _kv("Statut", status_label, sep=True)
        + _kv("Montant", f"{total} €", strong=True)
    )
    footer = (
        "<p style='margin:0 0 8px 0'>Vous pouvez préparer les détails d'accueil sans transmettre vos coordonnées — elles seront partagées au voyageur 24h avant l'arrivée.</p>"
        "<p style='margin:0'>— L'équipe ZenStay</p>"
    )
    html = _email_shell(title=title, intro=intro, rows_html=rows, footer=footer)
    await _resend_send(host_email, subject, html)






# ---------- Models ----------
class User(BaseModel):
    user_id: str
    email: str
    name: str
    picture: Optional[str] = None
    role: str = "user"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class Listing(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    titre: str
    titre_en: Optional[str] = None
    ville: str
    pays: Optional[str] = "France"
    prix_nuit: float
    note: float = 4.8
    db_nuit: int = 30
    image_url: str
    description: str
    description_en: Optional[str] = None
    hote_email: str
    disponible: bool = True
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ListingCreate(BaseModel):
    titre: str
    titre_en: Optional[str] = None
    ville: str
    pays: Optional[str] = "France"
    prix_nuit: float
    note: float = 4.8
    db_nuit: int = 30
    image_url: str
    description: str
    description_en: Optional[str] = None
    hote_email: str
    disponible: bool = True


class Reservation(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    logement_id: str
    name: str
    email: str
    date_arrivee: str
    date_depart: str
    voyageurs: int = 1
    montant: float
    statut: str = "pending"  # pending|paid|cancelled
    stripe_link: Optional[str] = None
    stripe_session_id: Optional[str] = None
    invoice_number: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ReservationCreate(BaseModel):
    logement_id: str
    name: str
    email: str
    date_arrivee: str
    date_depart: str
    voyageurs: int = 1


class PaymentTransaction(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str
    reservation_id: str
    user_id: Optional[str] = None
    email: Optional[str] = None
    amount: float
    currency: str = "eur"
    payment_status: str = "initiated"  # initiated|paid|failed|expired
    status: str = "open"
    metadata: Dict[str, Any] = {}
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class CheckoutRequest(BaseModel):
    reservation_id: str
    origin_url: str


# ---------- Auth helpers ----------
async def get_current_user(
    request: Request,
    session_token: Optional[str] = Cookie(default=None),
    authorization: Optional[str] = Header(default=None),
) -> Optional[Dict[str, Any]]:
    token = session_token
    if not token and authorization and authorization.startswith("Bearer "):
        token = authorization.split(" ", 1)[1].strip()
    if not token:
        return None
    sess = await db.user_sessions.find_one({"session_token": token}, {"_id": 0})
    if not sess:
        return None
    expires_at = sess.get("expires_at")
    if isinstance(expires_at, str):
        expires_at = datetime.fromisoformat(expires_at)
    if expires_at and expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at and expires_at < datetime.now(timezone.utc):
        return None
    user = await db.users.find_one({"user_id": sess["user_id"]}, {"_id": 0})
    return user


async def require_user(user=Depends(get_current_user)):
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user


async def require_admin(user=Depends(require_user)):
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    return user


# ---------- Auth Routes ----------
@api_router.post("/auth/session")
async def auth_session(request: Request, response: Response):
    body = await request.json()
    session_id = body.get("session_id")
    if not session_id:
        raise HTTPException(status_code=400, detail="session_id required")

    async with httpx.AsyncClient() as hc:
        r = await hc.get(
            "https://demobackend.emergentagent.com/auth/v1/env/oauth/session-data",
            headers={"X-Session-ID": session_id},
            timeout=15.0,
        )
    if r.status_code != 200:
        raise HTTPException(status_code=401, detail="Invalid session_id")
    data = r.json()
    email = data["email"]
    name = data.get("name", email.split("@")[0])
    picture = data.get("picture")
    session_token = data["session_token"]

    existing = await db.users.find_one({"email": email}, {"_id": 0})
    if existing:
        user_id = existing["user_id"]
        role = existing.get("role", "user")
        if email == ADMIN_EMAIL and role != "admin":
            await db.users.update_one({"user_id": user_id}, {"$set": {"role": "admin"}})
            role = "admin"
        await db.users.update_one(
            {"user_id": user_id},
            {"$set": {"name": name, "picture": picture}},
        )
    else:
        user_id = f"user_{uuid.uuid4().hex[:12]}"
        role = "admin" if email == ADMIN_EMAIL else "user"
        await db.users.insert_one(
            {
                "user_id": user_id,
                "email": email,
                "name": name,
                "picture": picture,
                "role": role,
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
        )

    expires_at = datetime.now(timezone.utc) + timedelta(days=7)
    await db.user_sessions.insert_one(
        {
            "user_id": user_id,
            "session_token": session_token,
            "expires_at": expires_at,
            "created_at": datetime.now(timezone.utc),
        }
    )

    response.set_cookie(
        key="session_token",
        value=session_token,
        max_age=7 * 24 * 60 * 60,
        httponly=True,
        secure=True,
        samesite="none",
        path="/",
    )
    return {
        "user_id": user_id,
        "email": email,
        "name": name,
        "picture": picture,
        "role": role,
    }


@api_router.get("/auth/me")
async def auth_me(user=Depends(get_current_user)):
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user


@api_router.post("/auth/logout")
async def auth_logout(
    response: Response,
    session_token: Optional[str] = Cookie(default=None),
):
    if session_token:
        await db.user_sessions.delete_many({"session_token": session_token})
    response.delete_cookie("session_token", path="/", samesite="none", secure=True)
    return {"ok": True}


# ---------- Listings ----------
def _pub_listing(doc: Dict[str, Any]) -> Dict[str, Any]:
    # Remove hote_email before exposing to public/users
    doc = {k: v for k, v in doc.items() if k != "hote_email"}
    return doc


@api_router.get("/listings")
async def list_listings():
    docs = await db.listings.find({}, {"_id": 0}).to_list(200)
    return [_pub_listing(d) for d in docs]


@api_router.get("/listings/{listing_id}")
async def get_listing(listing_id: str):
    doc = await db.listings.find_one({"id": listing_id}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Listing not found")
    return _pub_listing(doc)


@api_router.post("/admin/listings")
async def admin_create_listing(payload: ListingCreate, admin=Depends(require_admin)):
    listing = Listing(**payload.model_dump())
    doc = listing.model_dump()
    doc["created_at"] = doc["created_at"].isoformat()
    await db.listings.insert_one(doc)
    return _pub_listing({k: v for k, v in doc.items() if k != "_id"})


@api_router.get("/admin/listings")
async def admin_list_listings(admin=Depends(require_admin)):
    docs = await db.listings.find({}, {"_id": 0}).to_list(500)
    return docs  # admin can see hote_email


@api_router.put("/admin/listings/{listing_id}")
async def admin_update_listing(
    listing_id: str, payload: ListingCreate, admin=Depends(require_admin)
):
    res = await db.listings.update_one(
        {"id": listing_id}, {"$set": payload.model_dump()}
    )
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Not found")
    doc = await db.listings.find_one({"id": listing_id}, {"_id": 0})
    return doc


@api_router.delete("/admin/listings/{listing_id}")
async def admin_delete_listing(listing_id: str, admin=Depends(require_admin)):
    res = await db.listings.delete_one({"id": listing_id})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Not found")
    return {"ok": True}


@api_router.patch("/admin/listings/{listing_id}/toggle")
async def admin_toggle_listing(listing_id: str, admin=Depends(require_admin)):
    doc = await db.listings.find_one({"id": listing_id}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Not found")
    new_state = not bool(doc.get("disponible", True))
    await db.listings.update_one({"id": listing_id}, {"$set": {"disponible": new_state}})
    return {"id": listing_id, "disponible": new_state}


# ---------- Reservations ----------
def _nights(date_arrivee: str, date_depart: str) -> int:
    try:
        a = datetime.fromisoformat(date_arrivee)
        b = datetime.fromisoformat(date_depart)
        n = (b.date() - a.date()).days
        return max(1, n)
    except Exception:
        return 1


@api_router.post("/reservations")
async def create_reservation(payload: ReservationCreate, user=Depends(require_user)):
    listing = await db.listings.find_one({"id": payload.logement_id}, {"_id": 0})
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")
    if not listing.get("disponible", True):
        raise HTTPException(status_code=400, detail="Listing unavailable")

    nights = _nights(payload.date_arrivee, payload.date_depart)
    montant = round(float(listing["prix_nuit"]) * nights, 2)

    reservation = Reservation(
        user_id=user["user_id"],
        logement_id=payload.logement_id,
        name=payload.name,
        email=payload.email,
        date_arrivee=payload.date_arrivee,
        date_depart=payload.date_depart,
        voyageurs=payload.voyageurs,
        montant=montant,
        statut="pending",
    )
    doc = reservation.model_dump()
    doc["created_at"] = doc["created_at"].isoformat()
    await db.reservations.insert_one(doc)

    # Fire Make.com webhook (host email kept backend only)
    if MAKE_WEBHOOK_URL:
        try:
            async with httpx.AsyncClient() as hc:
                await hc.post(
                    MAKE_WEBHOOK_URL,
                    json={
                        "name": payload.name,
                        "email": payload.email,
                        "logement": listing["titre"],
                        "ville": listing["ville"],
                        "date_arrivee": payload.date_arrivee,
                        "date_depart": payload.date_depart,
                        "voyageurs": payload.voyageurs,
                        "montant": montant,
                        "stripe_link": "",
                        "hote_email": listing.get("hote_email", ""),
                        "reservation_id": reservation.id,
                    },
                    timeout=10.0,
                )
        except Exception as e:
            logger.warning(f"Make webhook failed: {e}")

    # Host notification email — event=new (payment pending)
    await send_host_notification(doc, listing, event="new")

    out = {k: v for k, v in doc.items() if k != "_id"}
    return out


@api_router.get("/reservations/me")
async def my_reservations(user=Depends(require_user)):
    docs = await db.reservations.find({"user_id": user["user_id"]}, {"_id": 0}).to_list(
        200
    )
    return docs


@api_router.get("/admin/reservations")
async def admin_reservations(admin=Depends(require_admin)):
    docs = await db.reservations.find({}, {"_id": 0}).to_list(500)
    return docs


# ---------- Payments ----------
async def _mark_reservation_paid_and_notify(reservation_id: str) -> None:
    """Idempotent finalize: set paid, assign invoice_number, send client invoice + host email.
    Safe to call multiple times — only fires emails the first time.
    """
    res = await db.reservations.find_one({"id": reservation_id}, {"_id": 0})
    if not res:
        return
    if res.get("statut") == "paid" and res.get("invoice_number"):
        return  # already finalized & notified
    invoice_no = res.get("invoice_number") or _generate_invoice_number()
    await db.reservations.update_one(
        {"id": reservation_id, "$or": [{"invoice_number": None}, {"invoice_number": {"$exists": False}}]},
        {"$set": {"statut": "paid", "invoice_number": invoice_no}},
    )
    # Re-fetch (may have been finalized by a concurrent caller)
    res = await db.reservations.find_one({"id": reservation_id}, {"_id": 0})
    if not res or not res.get("invoice_number"):
        return
    listing = await db.listings.find_one({"id": res["logement_id"]}, {"_id": 0})
    if not listing:
        return
    await send_booking_confirmation(res, listing)
    await send_host_notification(res, listing, event="paid")

def _get_stripe(host_url: str) -> StripeCheckout:
    webhook_url = f"{host_url.rstrip('/')}/api/webhook/stripe"
    return StripeCheckout(api_key=STRIPE_API_KEY, webhook_url=webhook_url)


@api_router.post("/payments/checkout")
async def create_checkout(
    payload: CheckoutRequest, request: Request, user=Depends(require_user)
):
    reservation = await db.reservations.find_one(
        {"id": payload.reservation_id, "user_id": user["user_id"]}, {"_id": 0}
    )
    if not reservation:
        raise HTTPException(status_code=404, detail="Reservation not found")
    if reservation.get("statut") == "paid":
        raise HTTPException(status_code=400, detail="Already paid")

    amount = float(reservation["montant"])
    origin = payload.origin_url.rstrip("/")
    success_url = f"{origin}/payment-success?session_id={{CHECKOUT_SESSION_ID}}"
    cancel_url = f"{origin}/listings/{reservation['logement_id']}?cancelled=1"

    host_url = str(request.base_url)
    stripe_checkout = _get_stripe(host_url)
    req = CheckoutSessionRequest(
        amount=amount,
        currency="eur",
        success_url=success_url,
        cancel_url=cancel_url,
        metadata={
            "reservation_id": reservation["id"],
            "user_id": user["user_id"],
            "email": user["email"],
        },
    )
    session: CheckoutSessionResponse = await stripe_checkout.create_checkout_session(req)

    pt = PaymentTransaction(
        session_id=session.session_id,
        reservation_id=reservation["id"],
        user_id=user["user_id"],
        email=user["email"],
        amount=amount,
        currency="eur",
        payment_status="initiated",
        status="open",
        metadata={"reservation_id": reservation["id"]},
    )
    doc = pt.model_dump()
    doc["created_at"] = doc["created_at"].isoformat()
    await db.payment_transactions.insert_one(doc)

    await db.reservations.update_one(
        {"id": reservation["id"]},
        {"$set": {"stripe_link": session.url, "stripe_session_id": session.session_id}},
    )

    return {"url": session.url, "session_id": session.session_id}


@api_router.get("/payments/status/{session_id}")
async def payment_status(session_id: str, request: Request):
    pt = await db.payment_transactions.find_one({"session_id": session_id}, {"_id": 0})
    if not pt:
        raise HTTPException(status_code=404, detail="Unknown session")

    host_url = str(request.base_url)
    payment_status_val = None
    session_status_val = None
    amount_total_cents = None
    currency = "eur"
    try:
        stripe_checkout = _get_stripe(host_url)
        status: CheckoutStatusResponse = await stripe_checkout.get_checkout_status(session_id)
        payment_status_val = status.payment_status
        session_status_val = status.status
        amount_total_cents = status.amount_total
        currency = status.currency
    except Exception as e:
        # Fallback: hit Stripe SDK directly (lib has a metadata-type bug)
        logger.warning(f"emergentintegrations get_checkout_status failed, falling back to stripe SDK: {e}")
        stripe_sdk.api_key = STRIPE_API_KEY
        s = stripe_sdk.checkout.Session.retrieve(session_id)
        # StripeObject supports dict-style [] access; .get() collides with __getattr__
        try:
            payment_status_val = s["payment_status"] or "unpaid"
        except KeyError:
            payment_status_val = "unpaid"
        try:
            session_status_val = s["status"] or "open"
        except KeyError:
            session_status_val = "open"
        try:
            amount_total_cents = s["amount_total"]
        except KeyError:
            amount_total_cents = None
        try:
            currency = s["currency"] or "eur"
        except KeyError:
            currency = "eur"

    # Update transaction only if not already paid
    if pt.get("payment_status") != "paid":
        await db.payment_transactions.update_one(
            {"session_id": session_id},
            {
                "$set": {
                    "payment_status": payment_status_val,
                    "status": session_status_val,
                }
            },
        )
        if payment_status_val == "paid":
            await _mark_reservation_paid_and_notify(pt["reservation_id"])

    reservation = await db.reservations.find_one(
        {"id": pt["reservation_id"]}, {"_id": 0}
    )
    return {
        "session_id": session_id,
        "payment_status": payment_status_val,
        "status": session_status_val,
        "amount": (amount_total_cents / 100.0) if amount_total_cents else pt["amount"],
        "currency": currency,
        "reservation": reservation,
    }


@api_router.post("/webhook/stripe")
async def stripe_webhook(request: Request):
    body = await request.body()
    sig = request.headers.get("Stripe-Signature", "")
    try:
        host_url = str(request.base_url)
        stripe_checkout = _get_stripe(host_url)
        evt = await stripe_checkout.handle_webhook(body, sig)
    except Exception as e:
        logger.warning(f"Webhook err: {e}")
        return {"ok": False}

    if evt.session_id:
        await db.payment_transactions.update_one(
            {"session_id": evt.session_id},
            {"$set": {"payment_status": evt.payment_status}},
        )
        if evt.payment_status == "paid":
            pt = await db.payment_transactions.find_one(
                {"session_id": evt.session_id}, {"_id": 0}
            )
            if pt:
                await _mark_reservation_paid_and_notify(pt["reservation_id"])
    return {"ok": True}


# ---------- Host contact ----------
class HostContact(BaseModel):
    name: str
    email: EmailStr
    location: str
    db_estimate: Optional[int] = None
    description: str
    phone: Optional[str] = None


@api_router.post("/host-contact")
async def create_host_contact(payload: HostContact):
    doc = {
        "id": str(uuid.uuid4()),
        "name": payload.name,
        "email": payload.email,
        "location": payload.location,
        "db_estimate": payload.db_estimate,
        "description": payload.description,
        "phone": payload.phone,
        "status": "new",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.host_contacts.insert_one(doc)

    if MAKE_WEBHOOK_URL:
        try:
            async with httpx.AsyncClient() as hc:
                await hc.post(
                    MAKE_WEBHOOK_URL,
                    json={
                        "type": "host_contact",
                        "name": payload.name,
                        "email": payload.email,
                        "location": payload.location,
                        "db_estimate": payload.db_estimate,
                        "description": payload.description,
                        "phone": payload.phone,
                        "admin_email": ADMIN_EMAIL,
                    },
                    timeout=10.0,
                )
        except Exception as e:
            logger.warning(f"Host contact webhook failed: {e}")

    return {"ok": True, "id": doc["id"]}


@api_router.get("/admin/host-contacts")
async def admin_list_host_contacts(admin=Depends(require_admin)):
    docs = await db.host_contacts.find({}, {"_id": 0}).to_list(500)
    return docs


# ---------- File upload ----------
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/jpg", "image/png", "image/webp", "image/gif"}
MAX_UPLOAD_SIZE = 8 * 1024 * 1024  # 8 MB


@api_router.post("/admin/upload")
async def admin_upload(
    request: Request,
    file: UploadFile = File(...),
    admin=Depends(require_admin),
):
    if file.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(status_code=400, detail="Unsupported file type")
    data = await file.read()
    if len(data) > MAX_UPLOAD_SIZE:
        raise HTTPException(status_code=413, detail="File too large (max 8 MB)")

    ext = (file.filename or "img").split(".")[-1].lower()
    if ext not in {"jpg", "jpeg", "png", "webp", "gif"}:
        ext = "jpg"
    path = f"{APP_NAME}/uploads/{admin['user_id']}/{uuid.uuid4().hex}.{ext}"

    try:
        result = await asyncio.to_thread(put_object, path, data, file.content_type)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Upload failed: {e}")
        raise HTTPException(status_code=500, detail="Upload failed")

    file_id = str(uuid.uuid4())
    await db.files.insert_one(
        {
            "id": file_id,
            "storage_path": result["path"],
            "original_filename": file.filename,
            "content_type": file.content_type,
            "size": result.get("size", len(data)),
            "uploaded_by": admin["user_id"],
            "is_deleted": False,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
    )

    base = str(request.base_url).rstrip("/")
    public_url = f"{base}/api/files/{result['path']}"
    return {"id": file_id, "url": public_url, "path": result["path"]}


@api_router.get("/files/{path:path}")
async def serve_file(path: str):
    record = await db.files.find_one(
        {"storage_path": path, "is_deleted": False}, {"_id": 0}
    )
    if not record:
        raise HTTPException(status_code=404, detail="File not found")
    try:
        data, content_type = await asyncio.to_thread(get_object, path)
    except Exception as e:
        logger.warning(f"Storage get failed: {e}")
        raise HTTPException(status_code=404, detail="File not found")
    return Response(
        content=data,
        media_type=record.get("content_type") or content_type,
        headers={"Cache-Control": "public, max-age=3600"},
    )


# ---------- Health ----------
@api_router.get("/")
async def root():
    return {"app": "ZenStay", "status": "ok"}


# ---------- Seed ----------
SEED_LISTINGS = [
    {
        "titre": "Cabane sylvestre — Forêt de Brocéliande",
        "titre_en": "Forest cabin — Brocéliande woods",
        "ville": "Paimpont",
        "pays": "France",
        "prix_nuit": 168.0,
        "note": 4.9,
        "db_nuit": 24,
        "image_url": "https://images.unsplash.com/photo-1775806577799-43d0d7efa67e?crop=entropy&cs=srgb&fm=jpg&ixid=M3w4NjA4Mzl8MHwxfHNlYXJjaHwyfHxjb3p5JTIwZm9yZXN0JTIwY2FiaW4lMjBleHRlcmlvcnxlbnwwfHx8fDE3Nzg2NzI4MzN8MA&ixlib=rb-4.1.0&q=85",
        "description": "Une cabane en bois nichée sous les pins, baignée d'un silence presque total. Cheminée, vue sur lac.",
        "description_en": "A wooden cabin nestled under pines, bathed in near-total silence. Fireplace, lake view.",
        "hote_email": "marie.host@zenstay.com",
    },
    {
        "titre": "Maison blanche — Île de Folegandros",
        "titre_en": "White house — Folegandros island",
        "ville": "Folegandros",
        "pays": "Grèce",
        "prix_nuit": 245.0,
        "note": 4.95,
        "db_nuit": 22,
        "image_url": "https://images.unsplash.com/photo-1767211664493-90841f9d778b?crop=entropy&cs=srgb&fm=jpg&ixid=M3w3NDQ2Mzl8MHwxfHNlYXJjaHwzfHxzZXJlbmUlMjBvY2VhbiUyMGhvdXNlJTIwYXJjaGl0ZWN0dXJlfGVufDB8fHx8MTc3ODY3MjgzM3ww&ixlib=rb-4.1.0&q=85",
        "description": "Maison de pierre face à la mer Égée. Aucune route à proximité, juste le souffle du vent.",
        "description_en": "Stone house facing the Aegean sea. No nearby road, just the breath of the wind.",
        "hote_email": "nikos.host@zenstay.com",
    },
    {
        "titre": "Refuge bois — Vallée du Queyras",
        "titre_en": "Wooden refuge — Queyras Valley",
        "ville": "Saint-Véran",
        "pays": "France",
        "prix_nuit": 132.0,
        "note": 4.85,
        "db_nuit": 28,
        "image_url": "https://images.unsplash.com/photo-1699210025833-07318c121bf0?crop=entropy&cs=srgb&fm=jpg&ixid=M3w4NjA4Mzl8MHwxfHNlYXJjaHwzfHxjb3p5JTIwZm9yZXN0JTIwY2FiaW4lMjBleHRlcmlvcnxlbnwwfHx8fDE3Nzg2NzI4MzN8MA&ixlib=rb-4.1.0&q=85",
        "description": "Refuge isolé à 2040m d'altitude. Nuits étoilées, silence minéral.",
        "description_en": "Remote refuge at 2040m altitude. Starlit nights, mineral silence.",
        "hote_email": "claire.host@zenstay.com",
    },
    {
        "titre": "Villa minérale — Côte Amalfitaine",
        "titre_en": "Mineral villa — Amalfi Coast",
        "ville": "Praiano",
        "pays": "Italie",
        "prix_nuit": 320.0,
        "note": 4.92,
        "db_nuit": 30,
        "image_url": "https://images.unsplash.com/photo-1775974861298-8fe164a40024?crop=entropy&cs=srgb&fm=jpg&ixid=M3w3NDQ2Mzl8MHwxfHNlYXJjaHw0fHxzZXJlbmUlMjBvY2VhbiUyMGhvdXNlJTIwYXJjaGl0ZWN0dXJlfGVufDB8fHx8MTc3ODY3MjgzM3ww&ixlib=rb-4.1.0&q=85",
        "description": "Villa creusée dans la falaise, terrasse suspendue au-dessus du Tyrrhénien.",
        "description_en": "Cliff-carved villa, terrace suspended above the Tyrrhenian.",
        "hote_email": "luca.host@zenstay.com",
    },
    {
        "titre": "Bothy nordique — Lofoten",
        "titre_en": "Nordic bothy — Lofoten",
        "ville": "Reine",
        "pays": "Norvège",
        "prix_nuit": 198.0,
        "note": 4.88,
        "db_nuit": 26,
        "image_url": "https://images.unsplash.com/photo-1699209148943-acacf2821f33?crop=entropy&cs=srgb&fm=jpg&ixid=M3w4NjA4Mzl8MHwxfHNlYXJjaHwxfHxjb3p5JTIwZm9yZXN0JTIwY2FiaW4lMjBleHRlcmlvcnxlbnwwfHx8fDE3Nzg2NzI4MzN8MA&ixlib=rb-4.1.0&q=85",
        "description": "Rorbu rouge sur pilotis, fjord en arrière-plan, aurores boréales en hiver.",
        "description_en": "Red stilted rorbu, fjord backdrop, northern lights in winter.",
        "hote_email": "ingrid.host@zenstay.com",
    },
    {
        "titre": "Piscine du large — Cap de Formentor",
        "titre_en": "Ocean pool — Cap de Formentor",
        "ville": "Pollença",
        "pays": "Espagne",
        "prix_nuit": 275.0,
        "note": 4.9,
        "db_nuit": 29,
        "image_url": "https://images.unsplash.com/photo-1571635685743-db0db8e31d9a?crop=entropy&cs=srgb&fm=jpg&ixid=M3w3NDQ2Mzl8MHwxfHNlYXJjaHwxfHxzZXJlbmUlMjBvY2VhbiUyMGhvdXNlJTIwYXJjaGl0ZWN0dXJlfGVufDB8fHx8MTc3ODY3MjgzM3ww&ixlib=rb-4.1.0&q=85",
        "description": "Maison contemporaine, piscine à débordement face à la Méditerranée.",
        "description_en": "Contemporary house, infinity pool facing the Mediterranean.",
        "hote_email": "alba.host@zenstay.com",
    },
]


async def seed_data():
    count = await db.listings.count_documents({})
    if count == 0:
        for l in SEED_LISTINGS:
            obj = Listing(**l).model_dump()
            obj["created_at"] = obj["created_at"].isoformat()
            await db.listings.insert_one(obj)
        logger.info("Seeded 6 listings")
    # Seed admin user (no password required because Google Auth; admin via email)
    existing_admin = await db.users.find_one({"email": ADMIN_EMAIL}, {"_id": 0})
    if not existing_admin:
        await db.users.insert_one(
            {
                "user_id": f"user_{uuid.uuid4().hex[:12]}",
                "email": ADMIN_EMAIL,
                "name": "ZenStay Admin",
                "picture": None,
                "role": "admin",
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
        )
        logger.info("Seeded admin user")
    # Seed test users
    for em, nm in [("alice@zenstay.com", "Alice"), ("ben@zenstay.com", "Ben")]:
        if not await db.users.find_one({"email": em}, {"_id": 0}):
            await db.users.insert_one(
                {
                    "user_id": f"user_{uuid.uuid4().hex[:12]}",
                    "email": em,
                    "name": nm,
                    "picture": None,
                    "role": "user",
                    "created_at": datetime.now(timezone.utc).isoformat(),
                }
            )


@app.on_event("startup")
async def on_startup():
    await seed_data()
    try:
        await asyncio.to_thread(init_storage)
        logger.info("Object storage initialized")
    except Exception as e:
        logger.warning(f"Storage init failed at startup: {e}")


# ---------- Mount & CORS ----------
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origin_regex=r"https?://.*",
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
