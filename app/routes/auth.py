from fastapi import APIRouter, Form, Request, Response, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from app.db import get_conn
from app.auth import hash_password, verify_password, create_session, delete_session, get_current_user

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/register", response_class=HTMLResponse)
def register_page(request: Request, user=Depends(get_current_user)):
    return templates.TemplateResponse("auth/register.html", {"request": request, "user": user})


@router.post("/register")
def register(
    request: Request,
    response: Response,
    email: str = Form(...),
    password: str = Form(...),
    is_seller: bool = Form(default=False),
):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM users WHERE email = %s", (email,))
            if cur.fetchone():
                return templates.TemplateResponse(
                    "auth/register.html",
                    {"request": request, "error": "Email already registered", "user": None},
                    status_code=400,
                )
            cur.execute(
                "INSERT INTO users (email, password_hash, is_buyer, is_seller) VALUES (%s, %s, TRUE, %s) RETURNING id",
                (email, hash_password(password), is_seller),
            )
            user_id = cur.fetchone()["id"]
        conn.commit()

    token = create_session(user_id)
    resp = RedirectResponse("/", status_code=303)
    resp.set_cookie("session", token, httponly=True, samesite="lax", max_age=60 * 60 * 24 * 30)
    return resp


@router.get("/login", response_class=HTMLResponse)
def login_page(request: Request, user=Depends(get_current_user)):
    return templates.TemplateResponse("auth/login.html", {"request": request, "user": user})


@router.post("/login")
def login(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id, password_hash FROM users WHERE email = %s", (email,))
            row = cur.fetchone()

    if not row or not verify_password(password, row["password_hash"]):
        return templates.TemplateResponse(
            "auth/login.html",
            {"request": request, "error": "Invalid email or password", "user": None},
            status_code=400,
        )

    token = create_session(row["id"])
    resp = RedirectResponse("/", status_code=303)
    resp.set_cookie("session", token, httponly=True, samesite="lax", max_age=60 * 60 * 24 * 30)
    return resp


@router.post("/logout")
def logout(request: Request, response: Response, user=Depends(get_current_user)):
    session = request.cookies.get("session")
    if session:
        delete_session(session)
    resp = RedirectResponse("/", status_code=303)
    resp.delete_cookie("session")
    return resp
