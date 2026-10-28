"""auth_db.py - user accounts stored in PostgreSQL. Only app.py's login screen calls this."""
import bcrypt
import psycopg

import config


def _conn():
    if not config.DATABASE_URL:
        raise RuntimeError("DATABASE_URL is not set.")
    return psycopg.connect(config.DATABASE_URL)


def register_user(username: str, password: str) -> bool:
    """Create an account. Returns False if the username is already taken."""
    hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    try:
        with _conn() as conn:
            conn.execute(
                "INSERT INTO users (username, password_hash) VALUES (%s, %s)",
                (username, hashed),
            )
        return True
    except psycopg.errors.UniqueViolation:
        return False


def verify_user(username: str, password: str) -> bool:
    """True if the username exists and the password matches."""
    with _conn() as conn:
        row = conn.execute(
            "SELECT password_hash FROM users WHERE username = %s", (username,)
        ).fetchone()
    return bool(row) and bcrypt.checkpw(password.encode(), row[0].encode())
