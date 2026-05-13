# ZenStay — PRD

## Problem Statement
ZenStay is a booking platform for peaceful stays (< 35 dB at night) in nature or near the sea. MVP: browse → login → reserve → pay → confirmation.

## Architecture
- Backend: FastAPI + MongoDB (motor), routes prefixed `/api`
- Frontend: React + react-router + Tailwind + shadcn/ui
- Auth: Emergent-managed Google OAuth (session_token cookies, 7-day expiry)
- Payments: Stripe Checkout via `emergentintegrations` + stripe SDK fallback
- Automation: Make.com webhook on bookings + host contacts
- Email: Resend (booking confirmation)
- Object Storage: Emergent (admin listing image uploads)

## User personas
- Traveler: browse → book → pay → receives confirmation email
- Host applicant: contact form → admin notified via Make webhook
- Admin: full CRUD listings (with image upload), view bookings, view host contacts

## Core requirements (all delivered)
- 6 seeded listings, 2 test users, 1 admin user
- `< 35 dB` badge prominent on every card
- Bilingual FR/EN, dark/light mode
- hote_email never exposed to public/user frontends
- Stripe checkout in EUR, success/cancel routes wired

## Implemented (Feb 2026)

### Iteration 1 — MVP
- Auth (Emergent OAuth + cookie+Bearer sessions)
- Listings CRUD (admin), reservations + Make webhook, Stripe checkout + status polling
- Landing, Listings, ListingDetail, PaymentSuccess, Dashboard, Admin pages
- 16/16 backend tests pass

### Iteration 2 — Bug fix
- Fixed `/api/payments/status` for Stripe SDK metadata bug

### Iteration 3 — Polish & growth
- **Date range picker** (shadcn Calendar in Popover, 2-month view, FR/EN locale)
- **Filters** on /listings (country select, price slider, dB slider)
- **Host contact page** (`/host`) with formulaire → POST `/api/host-contact` → Make webhook
- **Resend confirmation email** sent on Stripe `paid` event (HTML editorial template)
- **Object storage upload** for listing images (admin `/api/admin/upload` + public `/api/files/{path}`)
- 27/27 backend tests pass (16 regression + 11 new)

## Backlog
- P1: Host portal post-onboarding (separate from admin)
- P2: Multi-currency, EUR locale formatting per language
- P2: Email confirmation to host on new booking
- P2: Stripe webhook signature verification end-to-end test
- P2: Map view & favorites
- P3: Refer-a-host program (revenue-share)

## Next tasks
- Real Google OAuth e2e test setup (admin headless flow)
- Migrate `@app.on_event` → lifespan (deprecation)
