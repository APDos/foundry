from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from app.db import get_conn
from app.auth import get_current_user, require_seller

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/", response_class=HTMLResponse)
def index(request: Request, user=Depends(get_current_user)):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT l.id, l.title, l.description, l.price, l.category, l.saas_tool, l.preview,
                       u.email AS seller_email,
                       COALESCE(AVG(r.rating), 0) AS avg_rating,
                       COUNT(r.id) AS review_count
                FROM listings l
                JOIN users u ON u.id = l.seller_id
                LEFT JOIN reviews r ON r.listing_id = l.id
                WHERE l.status = 'active'
                GROUP BY l.id, u.email
                ORDER BY l.created_at DESC
                """
            )
            listings = cur.fetchall()
    return templates.TemplateResponse("index.html", {"request": request, "listings": listings, "user": user})


@router.get("/listings/{listing_id}", response_class=HTMLResponse)
def listing_detail(listing_id: int, request: Request, user=Depends(get_current_user)):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT l.*, u.email AS seller_email,
                       COALESCE(AVG(r.rating), 0) AS avg_rating,
                       COUNT(r.id) AS review_count
                FROM listings l
                JOIN users u ON u.id = l.seller_id
                LEFT JOIN reviews r ON r.listing_id = l.id
                WHERE l.id = %s AND l.status = 'active'
                GROUP BY l.id, u.email
                """,
                (listing_id,),
            )
            listing = cur.fetchone()
            if not listing:
                return templates.TemplateResponse("404.html", {"request": request, "user": user}, status_code=404)

            purchased = False
            if user:
                cur.execute(
                    "SELECT id FROM purchases WHERE buyer_id = %s AND listing_id = %s",
                    (user["id"], listing_id),
                )
                purchased = cur.fetchone() is not None

            cur.execute(
                """
                SELECT r.rating, r.body, r.created_at, u.email AS buyer_email
                FROM reviews r
                JOIN users u ON u.id = r.buyer_id
                WHERE r.listing_id = %s
                ORDER BY r.created_at DESC
                """,
                (listing_id,),
            )
            reviews = cur.fetchall()

    return templates.TemplateResponse(
        "listings/detail.html",
        {"request": request, "listing": listing, "purchased": purchased, "reviews": reviews, "user": user},
    )


@router.get("/sell/new", response_class=HTMLResponse)
def new_listing_page(request: Request, user=Depends(get_current_user)):
    require_seller(user)
    return templates.TemplateResponse("listings/new.html", {"request": request, "user": user})


@router.post("/sell/new")
def create_listing(
    request: Request,
    user=Depends(get_current_user),
    title: str = Form(...),
    description: str = Form(...),
    price: int = Form(...),        # in cents
    category: str = Form(...),
    saas_tool: str = Form(...),
    preview: str = Form(...),
    content: str = Form(...),      # JSON string from textarea
):
    require_seller(user)
    import json
    try:
        content_json = json.loads(content)
    except json.JSONDecodeError:
        return templates.TemplateResponse(
            "listings/new.html",
            {"request": request, "user": user, "error": "Content must be valid JSON"},
            status_code=400,
        )

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO listings (seller_id, title, description, price, category, saas_tool, preview, content)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
                """,
                (user["id"], title, description, price, category, saas_tool, preview, json.dumps(content_json)),
            )
            listing_id = cur.fetchone()["id"]
        conn.commit()

    return RedirectResponse(f"/listings/{listing_id}", status_code=303)


@router.get("/account/listings", response_class=HTMLResponse)
def my_listings(request: Request, user=Depends(get_current_user)):
    require_seller(user)
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT * FROM listings WHERE seller_id = %s ORDER BY created_at DESC",
                (user["id"],),
            )
            listings = cur.fetchall()
    return templates.TemplateResponse("listings/my_listings.html", {"request": request, "listings": listings, "user": user})


@router.post("/listings/{listing_id}/publish")
def publish_listing(listing_id: int, request: Request, user=Depends(get_current_user)):
    require_seller(user)
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE listings SET status = 'active', updated_at = NOW() WHERE id = %s AND seller_id = %s",
                (listing_id, user["id"]),
            )
        conn.commit()
    return RedirectResponse(f"/listings/{listing_id}", status_code=303)
