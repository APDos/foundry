import os
import secrets
from datetime import datetime, timezone
from fastapi import Cookie, HTTPException, status
from passlib.hash import bcrypt
from app.db import get_conn


def hash_password(password: str) -> str:
    return bcrypt.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.verify(password, password_hash)


def create_session(user_id: int) -> str:
    token = secrets.token_urlsafe(32)
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO sessions (id, user_id) VALUES (%s, %s)",
                (token, user_id),
            )
        conn.commit()
    return token


def delete_session(token: str) -> None:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM sessions WHERE id = %s", (token,))
        conn.commit()


def get_current_user(session: str | None = Cookie(default=None)):
    """Dependency — returns the logged-in user dict or None."""
    if not session:
        return None
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT u.id, u.email, u.is_buyer, u.is_seller, u.stripe_account_id
                FROM sessions s
                JOIN users u ON u.id = s.user_id
                WHERE s.id = %s AND s.expires_at > NOW()
                """,
                (session,),
            )
            row = cur.fetchone()
    return dict(row) if row else None


def require_user(user=None):
    """Dependency — raises 401 if not logged in."""
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    return user


def require_seller(user=None):
    """Dependency — raises 403 if user is not a seller."""
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    if not user["is_seller"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Seller account required")
    return user
