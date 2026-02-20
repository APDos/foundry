-- AI Template Marketplace schema

CREATE TABLE users (
    id          SERIAL PRIMARY KEY,
    email       TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    is_buyer    BOOLEAN NOT NULL DEFAULT TRUE,
    is_seller   BOOLEAN NOT NULL DEFAULT FALSE,
    stripe_account_id TEXT,          -- Stripe Connect account for sellers
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE sessions (
    id          TEXT PRIMARY KEY,    -- random token stored in cookie
    user_id     INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at  TIMESTAMPTZ NOT NULL DEFAULT NOW() + INTERVAL '30 days'
);

CREATE TYPE listing_status AS ENUM ('draft', 'active', 'archived');

CREATE TABLE listings (
    id          SERIAL PRIMARY KEY,
    seller_id   INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title       TEXT NOT NULL,
    description TEXT NOT NULL,
    price       INTEGER NOT NULL,    -- in cents
    category    TEXT NOT NULL,
    saas_tool   TEXT NOT NULL,       -- e.g. "Retool", "Tableau"
    preview     TEXT NOT NULL,       -- teaser shown to non-buyers
    content     JSONB NOT NULL,      -- full template, gated behind purchase
    status      listing_status NOT NULL DEFAULT 'draft',
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE purchases (
    id          SERIAL PRIMARY KEY,
    buyer_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    listing_id  INTEGER NOT NULL REFERENCES listings(id) ON DELETE CASCADE,
    amount_paid INTEGER NOT NULL,    -- in cents, price at time of purchase
    stripe_payment_intent_id TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (buyer_id, listing_id)    -- prevent duplicate purchases
);

CREATE TABLE reviews (
    id          SERIAL PRIMARY KEY,
    purchase_id INTEGER NOT NULL REFERENCES purchases(id) ON DELETE CASCADE,
    buyer_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    listing_id  INTEGER NOT NULL REFERENCES listings(id) ON DELETE CASCADE,
    rating      SMALLINT NOT NULL CHECK (rating BETWEEN 1 AND 5),
    body        TEXT NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (purchase_id)             -- one review per purchase
);

CREATE TABLE payouts (
    id                  SERIAL PRIMARY KEY,
    seller_id           INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    listing_id          INTEGER NOT NULL REFERENCES listings(id) ON DELETE CASCADE,
    purchase_id         INTEGER NOT NULL REFERENCES purchases(id) ON DELETE CASCADE,
    amount              INTEGER NOT NULL,   -- in cents (seller's share)
    stripe_transfer_id  TEXT,
    status              TEXT NOT NULL DEFAULT 'pending', -- pending, paid, failed
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indexes for common lookups
CREATE INDEX idx_listings_seller     ON listings(seller_id);
CREATE INDEX idx_listings_status     ON listings(status);
CREATE INDEX idx_purchases_buyer     ON purchases(buyer_id);
CREATE INDEX idx_purchases_listing   ON purchases(listing_id);
CREATE INDEX idx_reviews_listing     ON reviews(listing_id);
CREATE INDEX idx_sessions_user       ON sessions(user_id);
CREATE INDEX idx_payouts_seller      ON payouts(seller_id);
