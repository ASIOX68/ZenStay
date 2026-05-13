# ZenStay — PRD

## Problem Statement
Booking platform for peaceful stays (< 35 dB at night) in nature or near the sea. End-to-end: browse → login → reserve → pay → confirmation.

## Architecture
- Backend: FastAPI + MongoDB (motor), routes prefixed `/api`
- Frontend: React + react-router + Tailwind + shadcn/ui
- Auth: Emergent-managed Google OAuth (session_token cookies + Bearer)
- Payments: Stripe Checkout + SDK fallback
- Automation: Make.com webhook (bookings + host contacts)
- Email: Resend (booking flow + invoice)
- Object Storage: Emergent (listing image uploads)

## User personas
- Traveler: browse → book → pay → invoice email + web invoice
- Host (auto-detected: email == listing.hote_email): private portal with stats, listings CRUD, reservations
- Admin: full CRUD + host contacts

## Implemented (Feb 2026)

### Iter 1 — MVP
Auth, listings CRUD, reservations + Make webhook, Stripe checkout + polling. 16/16 tests.

### Iter 2 — Stripe fix
Patched `/api/payments/status` for emergentintegrations metadata bug (Stripe SDK fallback).

### Iter 3 — Polish & growth
Date range picker (shadcn Calendar), filters on /listings, host contact page, Resend confirmation, object storage upload. 27/27 tests.

### Iter 4 — Emails
Host notification on new + paid, client invoice email with invoice_number `ZS-YYYYMM-XXXXXX`, idempotent finalize helper with `matched_count` race gate. 39/39 tests.

### Iter 5 — Invoice & Host portal
- **Public invoice** `/invoices/:invoice_number` — print-friendly (`@media print` CSS), invoice number as unguessable secret, hote_email stripped
- **Host portal** `/host-portal` — auto-detected via email match, tabs (Listings / Reservations / Revenue), full edit (hote_email locked server-side), toggle availability, revenue stats
- Navbar conditional "Espace hôte" link when `is_host=true`
- Dashboard exposes invoice link per paid booking
- Email invoice now embeds "Voir & imprimer la facture" CTA via `app_origin` stored on payment_transactions
- 60/60 backend tests (39 regression + 21 iter5)

## Backlog
- P1: ErrorBoundary at AppRouter root
- P1: ESLint pre-commit (no-undef, no-unreachable)
- P2: PDF download of invoice (instead of print)
- P2: Multi-currency
- P2: Host can adjust dates/cancel reservations on their listings
- P3: Refer-a-host program

## Next tasks
- Visual e2e verification via real Google sign-in (Playwright cookie injection limited)
