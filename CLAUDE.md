# Project: Foundry

## What We're Building
Foundry is a marketplace where sellers list and sell AI-powered build templates — structured prompt sequences and instructions that guide AI coding tools (like Claude Code or Cursor) to build functional SaaS-style tools, dashboards, and microservices from scratch.

The core buyer persona is a non-technical or semi-technical business owner — think a tech CEO who knows what they want to build, can interact with an AI, but can't write code or debug a broken environment. They purchase a template, follow the steps, and end up with a working piece of software without needing an engineering team.

The core seller persona is a developer who has already built something with AI assistance and wants to package up their prompt sequence, decisions, and hard-won knowledge into a repeatable, sellable template.

Foundry is not a generic prompt marketplace. It is specifically focused on building software. Templates are playbooks, not scripts — they include prompts, context, checkpoints, and guidance that make them usable by someone who isn't going to write or debug code themselves.

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
- what_it_builds (text) — plain English description e.g. "A Stripe billing dashboard"
- ai_tools (text array) — compatible tools e.g. Claude Code, Cursor
- difficulty (enum: beginner/intermediate/advanced)
- estimated_hours (int) — honest estimate for the buyer
- prerequisites (text) — plain English, no jargon e.g. "A Stripe account and a PostgreSQL database"
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

## Template Content Structure (jsonb)
The `content` field on a listing stores the full template as structured JSON. A well-formed template looks like this:

```json
{
  "context_file": "A CLAUDE.md style block the buyer pastes into their project before starting",
  "steps": [
    {
      "order": 1,
      "title": "Set up the project",
      "prompt": "The exact prompt the buyer pastes into Claude Code",
      "expected_output": "Plain English description of what should happen e.g. a src/ folder with a main.py and requirements.txt",
      "checkpoint": "How the buyer verifies this step worked, written for a non-technical person",
      "common_issues": "What can go wrong and how to fix it, in plain English"
    }
  ],
  "finishing_checklist": ["Item 1 to verify the build is complete", "Item 2..."]
}
```

Sellers are guided to write prompts, checkpoints, and common_issues in plain English — the buyer persona is a business owner, not a developer.

## Getting Started (Buyer-Facing)
Foundry includes a short onboarding guide for buyers covering:
- How to install and set up Claude Code
- How to use a Foundry template step by step
- What to do if a step doesn't produce the expected output

This reduces drop-off for non-technical buyers before they even open a template.

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
