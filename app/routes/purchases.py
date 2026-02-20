import os
import stripe
from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from app.db import get_conn
from app.auth import get_current_user, require_user

stripe.api_key = os.environ.get("STRIPE_SECRET_KEY", "")
PLATFORM_FEE_PERCENT = int(os.environ.get("STRIPE_PLATFORM_FEE_PERCENT", 10))

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.post("/listings/{listing_id}/buy")
def start_checkout(listing_id: int, request: Request, user=Depends(get_current_user)):
    require_user(user)

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT l.*, u.stripe_account_id FROM listings l JOIN users u ON u.id = l.seller_id WHERE l.id = %s AND l.status = 'active'",
                (listing_id,),
            )
            listing = cur.fetchone()
            if not listing:
                return RedirectResponse("/", status_code=303)

            # Check not already purchased
            cur.execute(
                "SELECT id FROM purchases WHERE buyer_id = %s AND listing_id = %s",
                (user["id"], listing_id),
            )
            if cur.fetchone():
                return RedirectResponse(f"/listings/{listing_id}", status_code=303)

    base_url = str(request.base_url).rstrip("/")
    session = stripe.checkout.Session.create(
        payment_method_types=["card"],
        line_items=[{
            "price_data": {
                "currency": "usd",
                "product_data": {"name": listing["title"]},
                "unit_amount": listing["price"],
            },
            "quantity": 1,
        }],
        mode="payment",
        success_url=f"{base_url}/purchases/success?session_id={{CHECKOUT_SESSION_ID}}&listing_id={listing_id}",
        cancel_url=f"{base_url}/listings/{listing_id}",
        metadata={"buyer_id": user["id"], "listing_id": listing_id},
    )
    return RedirectResponse(session.url, status_code=303)


@router.get("/purchases/success", response_class=HTMLResponse)
def purchase_success(request: Request, session_id: str, listing_id: int, user=Depends(get_current_user)):
    require_user(user)

    checkout_session = stripe.checkout.Session.retrieve(session_id)
    if checkout_session.payment_status != "paid":
        return RedirectResponse(f"/listings/{listing_id}", status_code=303)

    with get_conn() as conn:
        with conn.cursor() as cur:
            # Idempotent insert
            cur.execute(
                """
                INSERT INTO purchases (buyer_id, listing_id, amount_paid, stripe_payment_intent_id)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (buyer_id, listing_id) DO NOTHING
                RETURNING id
                """,
                (user["id"], listing_id, checkout_session.amount_total, checkout_session.payment_intent),
            )
            purchase = cur.fetchone()

            if purchase:
                # Queue payout record
                cur.execute("SELECT price, seller_id FROM listings WHERE id = %s", (listing_id,))
                listing = cur.fetchone()
                seller_share = listing["price"] * (100 - PLATFORM_FEE_PERCENT) // 100
                cur.execute(
                    "INSERT INTO payouts (seller_id, listing_id, purchase_id, amount) VALUES (%s, %s, %s, %s)",
                    (listing["seller_id"], listing_id, purchase["id"], seller_share),
                )
        conn.commit()

    return RedirectResponse(f"/account/purchases", status_code=303)


@router.get("/account/purchases", response_class=HTMLResponse)
def my_purchases(request: Request, user=Depends(get_current_user)):
    require_user(user)
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT l.id, l.title, l.saas_tool, l.category, l.content, p.created_at, p.amount_paid
                FROM purchases p
                JOIN listings l ON l.id = p.listing_id
                WHERE p.buyer_id = %s
                ORDER BY p.created_at DESC
                """,
                (user["id"],),
            )
            purchases = cur.fetchall()
    return templates.TemplateResponse("purchases/my_purchases.html", {"request": request, "purchases": purchases, "user": user})
