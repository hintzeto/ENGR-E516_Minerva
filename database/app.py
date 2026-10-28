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

import config
import state
import auth_db

# set_page_config must be the first Streamlit call and only be called once here.
st.set_page_config(
    page_title=config.APP_NAME,
    page_icon="🦉",
    layout="wide",
)


def show_login() -> None:
    st.title(f"🦉 {config.APP_NAME}")
    st.caption(config.APP_TAGLINE)

    _, middle, _ = st.columns([1, 2, 1])
    with middle:
        login_tab, signup_tab = st.tabs(["Log in", "Sign up"])

        with login_tab:
            with st.form("login_form"):
                username = st.text_input("Username")
                password = st.text_input("Password", type="password")
                submitted = st.form_submit_button("Log in", width="stretch")
            if submitted:
                try:
                    ok = auth_db.verify_user(username.strip().lower(), password)
                except Exception:
                    st.error("Can't reach the user database right now. Please try again.")
                else:
                    if ok:
                        state.login(username.strip().lower())
                        st.rerun()
                    else:
                        st.error("Invalid username or password.")

        with signup_tab:
            with st.form("signup_form"):
                new_user = st.text_input("Choose a username")
                new_pass = st.text_input("Choose a password", type="password")
                confirm = st.text_input("Confirm password", type="password")
                created = st.form_submit_button("Create account", width="stretch")
            if created:
                if not new_user.strip().lower() or len(new_pass) < 8:
                    st.error("Enter a username and a password of at least 8 characters.")
                elif new_pass != confirm:
                    st.error("Passwords don't match.")
                else:
                    try:
                        if auth_db.register_user(new_user.strip().lower(), new_pass):
                            st.success("Account created. Switch to the Log in tab.")
                        else:
                            st.error("That username is already taken.")
                    except Exception:
                        st.error("Can't reach the user database right now. Please try again.")


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
    st.Page("pages/resources.py", title="Resource Management", icon="🗓️"),
    st.Page("pages/tutor.py", title="Tutor", icon="🎓"),
    st.Page("pages/feedback.py", title="Feedback", icon="📝"),
    st.Page("pages/materials.py", title="Course Materials", icon="📚"),
]
selected_page = st.navigation(pages)
selected_page.run()
