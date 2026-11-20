"""
app.py - Entry point. Run with:  streamlit run app.py

What this file does:
  1. Sets the page title/icon.
  2. Shows a username/password login and sign-up if nobody is logged in.
  3. Once logged in, builds the sidebar navigation between the pages in /pages.

HOW MULTIPAGE WORKS: st.navigation() takes a list of st.Page objects (one per
file in /pages) and draws the sidebar menu. The selected page's file is then
run by pg.run(). This file runs on EVERY click, so it acts as a wrapper
around all pages.
"""
import streamlit as st
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

import config
import state
from models import Base, User

MIN_PASSWORD_LENGTH = 8

# set_page_config must be the first Streamlit call and only be called once here.
st.set_page_config(
    page_title=config.APP_NAME,
    page_icon="🦉",
    layout="wide",
)

if not config.DATABASE_URI:
    st.error("DATABASE_URI is not set. Add it to ui/.env (see .env.example).")
    st.stop()

# st.connection caches the database engine across reruns and sessions.
db = st.connection("sql", type="sql", url=config.DATABASE_URI)


@st.cache_resource
def init_db() -> None:
    """Create the tables on first run. Existing tables are left alone."""
    Base.metadata.create_all(db.engine)


def find_user(session, username: str) -> User | None:
    return session.scalars(select(User).where(User.username == username)).first()


def log_in(username: str, password: str) -> None:
    username = username.strip().lower()
    if not username or not password:
        st.error("Please enter a username and password.")
        return
    try:
        with db.session as session:
            user = find_user(session, username)
    except SQLAlchemyError:
        st.error("The database is unreachable. Please try again later.")
        return
    # One message for both cases, so the form doesn't reveal which usernames exist.
    if user is None or not user.check_password(password):
        st.error("Invalid username or password.")
        return
    state.login(user)
    st.rerun()  # re-run so the logged-in navigation appears


def register(username: str, password: str) -> None:
    username = username.strip().lower()
    if not username or not password:
        st.error("Please enter a username and password.")
        return
    if len(password) < MIN_PASSWORD_LENGTH:
        st.error(f"Use a password of at least {MIN_PASSWORD_LENGTH} characters.")
        return
    try:
        with db.session as session:
            if find_user(session, username):
                st.error("That username is already taken.")
                return
            user = User(username=username)
            user.set_password(password)
            session.add(user)
            session.commit()
    except SQLAlchemyError:
        st.error("The database is unreachable. Please try again later.")
        return
    st.success("Account created. Switch to the Log in tab.")


def show_login() -> None:
    st.title(f"🦉 {config.APP_NAME}")
    st.caption(config.APP_TAGLINE)

    # Center the form a bit using columns.
    _, middle, _ = st.columns([1, 2, 1])
    with middle:
        login_tab, signup_tab = st.tabs(["Log in", "Sign up"])
        with login_tab:
            with st.form("login_form"):
                username = st.text_input("Username", key="login_username")
                password = st.text_input("Password", type="password", key="login_password")
                submitted = st.form_submit_button("Log in", width="stretch")
            if submitted:
                log_in(username, password)
        with signup_tab:
            with st.form("signup_form"):
                username = st.text_input("Username", key="signup_username")
                password = st.text_input("Password", type="password", key="signup_password")
                submitted = st.form_submit_button("Create account", width="stretch")
            if submitted:
                register(username, password)


# ---- Not logged in: show only the login screen -----------------------------
if not state.current_user():
    try:
        init_db()
    except SQLAlchemyError:
        st.error("The database is unreachable. Please try again later.")
        st.stop()
    show_login()
    st.stop()

# ---- Logged in: make sure this session's data containers exist -------------
state.init_user_state()

# ---- Sidebar: who am I + logout --------------------------------------------
with st.sidebar:
    st.markdown(f"### 🦉 {config.APP_NAME}")
    st.caption(f"Signed in as **{state.current_user()}**")
    if st.button("Log out", width="stretch"):
        state.logout()
        st.rerun()

# ---- Navigation (one st.Page per file in /pages) ---------------------------
pages = [
    st.Page("pages/home.py", title="Home", icon="🏠", default=True),
    st.Page("pages/tutor.py", title="Tutor", icon="🎓"),
    st.Page("pages/materials.py", title="Course Materials", icon="📚"), 
    st.Page("pages/feedback.py", title="Feedback", icon="📝"), 
    st.Page("pages/resources.py", title="Resource Management", icon="🗓️")
    
]
selected_page = st.navigation(pages)
selected_page.run()
