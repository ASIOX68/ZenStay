# ZenStay — PRD

## Problem Statement
ZenStay is a booking platform for peaceful stays (< 35 dB at night) located in nature or near the sea. MVP must deliver: browse → login → reserve → pay → confirmation.

## Architecture
- Backend: FastAPI + MongoDB (motor), routes prefixed `/api`
- Frontend: React + react-router + Tailwind + shadcn/ui
- Auth: Emergent-managed Google OAuth (session_token cookies, 7-day expiry)
- Payments: Stripe Checkout via `emergentintegrations` library + polling on success URL
- Automation: Make.com webhook fired on reservation creation (POST JSON with hote_email server-side)

## User personas
- Traveler: browse listings, book a stay, pay via Stripe
- Host: receive bookings via Make webhook → email (no UI for hosts in MVP)
- Admin: full CRUD on listings, view all bookings (admin@zenstay.com)

## Core requirements
- 6 seeded listings, 2 test users, 1 admin user
- < 35 dB badge prominent on every card
- Bilingual FR/EN toggle
- Dark/light mode toggle
- hote_email never exposed to public/user frontends
- Booking creates record + triggers Make webhook
- Stripe checkout in EUR, success/cancel routes wired

## Implemented (Feb 2026)
- Auth: /api/auth/{session,me,logout} with Emergent OAuth + cookie sessions
- Listings: public GET, admin CRUD + toggle availability
- Reservations: POST creates booking, triggers Make webhook, calculates total from nights
- Payments: /api/payments/checkout + /api/payments/status + webhook handler
- Frontend: Landing (hero+search, listings grid, why bento, host CTA, footer), Listings, ListingDetail with booking form, PaymentSuccess (polling), Dashboard (my bookings), Admin (full CRUD)
- Theme + Language contexts, sonner toasts, shadcn UI components

## Backlog
- P1: Date range picker (shadcn Calendar in popover) replacing native date inputs
- P1: Host portal (separate from admin)
- P2: Image upload for listings (object storage)
- P2: Stripe webhook signature verification end-to-end test
- P2: Email confirmation to traveler (e.g. Resend)
- P2: Map view, filters by country/price/dB

## Next tasks
- Verify e2e flow with testing agent
- Polish empty states, mobile menu
