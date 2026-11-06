"""
app.py - Entry point. Run with:  streamlit run app.py

What this file does:
  1. Sets the page title/icon.
  2. Shows a simple username login if nobody is logged in.
  3. Once logged in, builds the sidebar navigation between the pages in /pages.

HOW MULTIPAGE WORKS: st.navigation() takes a list of st.Page objects (one per
file in /pages) and draws the sidebar menu. The selected page's file is then
run by pg.run(). This file runs on EVERY click, so it acts as a wrapper
around all pages.
"""
import streamlit as st

from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from models import User, Base
import traceback

import config
import state


# set_page_config must be the first Streamlit call and only be called once here.
st.set_page_config(
    page_title=config.APP_NAME,
    page_icon="🦉",
    layout="wide",
)

# database accessor
db = st.connection("sql", type="sql", url=config.DATABASE_URI)
# ensure defined tables exist - may not check schema
Base.metadata.create_all(db.engine)


# Login user function broken out for return functionality
def login(username, password) -> None:
    if not username or not password:
        st.error("Missing required field.")
        return

    username = username.strip().lower()
    password = password.strip()

    if not username or not password:
        st.info("Please enter a username and password.")
        return

    try:
        with db.session as session:
            user = session.scalars(
                select(User).where(User.username == username)
            ).first()
    except SQLAlchemyError:
        traceback.print_exc()
        st.error("Database currently unreachable. Please try again later.")
        return

    if not user or not user.check_password(password):
        st.info("Invalid username or password.")
        return

    state.login(user)
    st.rerun() # show all pages now that user is logged in


# Register user function broken out for return functionality
def register(username, password) -> None:
    if not username or not password:
        st.error("Missing required field.")
        return

    username = username.strip().lower()
    password = password.strip()

    if not username or not password:
        st.error("Please enter a username and password.")
        return

    if len(password) < 8:
        st.error("Please use a password of at least 8 characters")
        return

    try:
        with db.session as session:
            user = session.scalars(
                select(User).where(User.username == username)
            ).first()

            if user:
                st.error("User with that name already exists.")
                return

            user = User(username=username)
            user.set_password(password)

            session.add(user)
            session.commit()

            st.success("Account registered. Please login.")
    except SQLAlchemyError:
        traceback.print_exc()
        st.error("Database currently unreachable. Please try again later.")
        return


def show_login() -> None:
    st.title(f"🦉 {config.APP_NAME}")
    st.caption(config.APP_TAGLINE)

    # Center the form a bit using columns.
    _, middle, _ = st.columns([1, 2, 1])
    with middle:
        login_tab, signup_tab = st.tabs(["Log in", "Sign up"])

        with login_tab:
            with st.form("login_form"):
                st.subheader("Log in")
                username = st.text_input("Username", placeholder="e.g. adam")
                password = st.text_input("Password", type="password")
                submitted = st.form_submit_button("Sign in", width="stretch")
            #st.caption("Demo login: no password needed. Real authentication comes later.")
            if submitted:
                login(username, password)

        with signup_tab:
            with st.form("signup_form"):
                st.subheader("Register")
                username = st.text_input("Username", placeholder="e.g. adam")
                password = st.text_input("Password", type="password")
                submitted = st.form_submit_button("Register", width="stretch")
            if submitted:
                register(username, password)


# ---- Not logged in: show only the login screen -----------------------------
if not state.current_user():
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
]
selected_page = st.navigation(pages)
selected_page.run()
