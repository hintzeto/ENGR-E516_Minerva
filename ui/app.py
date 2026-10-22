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

# set_page_config must be the first Streamlit call and only be called once here.
st.set_page_config(
    page_title=config.APP_NAME,
    page_icon="🦉",
    layout="wide",
)


def show_login() -> None:
    """Login placeholder: asks for a username only (no password)."""
    st.title(f"🦉 {config.APP_NAME}")
    st.caption(config.APP_TAGLINE)

    # Center the form a bit using columns.
    _, middle, _ = st.columns([1, 2, 1])
    with middle:
        with st.form("login_form"):
            st.subheader("Log in")
            username = st.text_input("Username", placeholder="e.g. thintze")
            submitted = st.form_submit_button("Continue", width="stretch")
        st.caption("Demo login: no password needed. Real authentication comes later.")

    if submitted:
        if not username.strip():
            st.error("Please enter a username.")
        else:
            state.login(username)
            st.rerun()  # re-run so the logged-in navigation appears


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
