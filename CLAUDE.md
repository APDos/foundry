# Project: AI Template Marketplace

## What We're Building
A marketplace where sellers can list and sell AI prompt templates and instructions that help buyers replace or replicate common SaaS tools. Buyers browse listings, purchase templates, and get access to structured prompt content. Sellers upload their templates and receive payouts via Stripe Connect.

This is a side project — prioritise simplicity and getting things working over clever abstractions. Avoid over-engineering.

## Stack
- **Frontend:** HTML, CSS, HTMX (for dynamic behaviour without a JS framework)
- **Backend:** FastAPI (Python)
- **Database:** PostgreSQL
- **Payments:** Stripe Connect (marketplace payouts to sellers)
- **Auth:** Session-based auth, rolled manually with FastAPI + PostgreSQL

## Core Tables

### users
- id, email, password_hash, created_at
- role: can be buyer, seller, or both (use a flags or enum approach)

### listings
- id, seller_id (fk users), title, description, price, category
- saas_tool (the tool this template replaces e.g. "Retool", "Tableau")
- preview (text) — visible to all users before purchase
- content (jsonb) — full structured template, only accessible after purchase
- created_at, updated_at, status (draft/active/archived)

### purchases
- id, buyer_id (fk users), listing_id (fk listings), amount_paid, created_at
- This is the access control layer — a buyer can access a listing's content only if a purchase record exists

### reviews
- id, purchase_id (fk purchases), buyer_id (fk users), listing_id (fk listings)
- rating (1-5), body (text), created_at
- Only buyers with a verified purchase can leave a review

### payouts
- id, seller_id (fk users), listing_id (fk listings), purchase_id (fk purchases)
- amount, stripe_transfer_id, status, created_at

## Content Storage Decision
Template content is stored as `jsonb` in the database — not as file downloads. This keeps things simple while allowing structured multi-step templates (e.g. each step has a prompt and instructions). A plain text `preview` field on listings is shown to non-buyers as a teaser.

## Core User Flows
1. **Browse** — any visitor can see listings, titles, descriptions, categories, and previews
2. **Purchase** — authenticated buyer pays via Stripe, purchase record is created, content is unlocked
3. **Access** — buyer views full jsonb content of purchased listings in their account
4. **Sell** — authenticated seller creates a listing, fills in metadata, writes structured content, sets price, publishes
5. **Payout** — seller receives their share via Stripe Connect when a sale is made

## Conventions
- Keep routes and logic simple and readable — this is a side project, not a startup
- Use PostgreSQL directly with a lightweight library like `asyncpg` or `psycopg2`, no ORM
- HTMX for any dynamic frontend behaviour, avoid writing vanilla JS where possible
- Commit frequently — before starting any significant new feature
- Build and validate each feature end to end before moving to the next one
