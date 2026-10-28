import bcrypt
import psycopg
import streamlit as st

@st.cache_resource
def get_conn():
    return psycopg.connect(st.secrets["DATABASE_URL"], autocommit=True)

def register_user(username: str, password: str) -> bool:
    hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    try:
        get_conn().execute(
            "INSERT INTO users (username, password_hash) VALUES (%s, %s)",
            (username, hashed),
        )
        return True
    except psycopg.errors.UniqueViolation:
        return False  # username taken

def verify_user(username: str, password: str) -> bool:
    row = get_conn().execute(
        "SELECT password_hash FROM users WHERE username = %s", (username,)
    ).fetchone()
    return bool(row) and bcrypt.checkpw(password.encode(), row[0].encode())
