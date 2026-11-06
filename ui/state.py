"""
state.py - Per-user session state helpers.

HOW STREAMLIT STATE WORKS (the non-obvious part):
- Streamlit re-runs your whole script every time the user clicks something.
- Normal Python variables are reset on each re-run.
- st.session_state is a dictionary that SURVIVES re-runs, and each browser
  tab/session gets its OWN copy. So two students using Minerva at the same
  time never see each other's data. This is what makes 10+ concurrent users safe.

We store everything for the logged-in user under keys that are created once
by init_user_state(). Anything that must be shared between sessions or survive
a server restart belongs in the real backend/database, not here.
"""
import streamlit as st


def current_user() -> str | None:
    """Return the logged-in username, or None if nobody is logged in."""
    return st.session_state.get("user_id")


def init_user_state() -> None:
    """Create empty containers for this session's data (only if missing)."""
    defaults = {
        "tutor_messages": {},        # {course_name: [message dicts]}
        "resource_messages": [],     # chat history for the resource assistant
        "tasks": [],                 # planner tasks (list of dicts)
        "study_plan": None,          # last generated study plan (text)
        "feedback_result": None,     # last feedback result (dict)
        "materials_version": 0,      # bump to force a refresh of material list
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def login(username: str) -> None:
    """
    Log a user in (PLACEHOLDER).

    TODO (auth): replace with real authentication, e.g. IU CAS/SSO via OIDC,
    streamlit-authenticator, or an API token check. Whatever you use, just make
    sure it ends by setting st.session_state["user_id"] to a stable unique ID.
    The rest of the app only relies on that one value.
    """
    st.session_state["user_id"] = username.strip()
    init_user_state()


def logout() -> None:
    """Wipe everything for this session and go back to the login screen."""
    st.session_state.clear()


def require_login() -> str:
    """
    Call at the top of every page. If nobody is logged in, show a message and
    stop the page. Returns the user_id when logged in.
    """
    user = current_user()
    if not user:
        st.warning("Please log in from the sidebar on the main page first.")
        st.stop()
    init_user_state()  # safe to call repeatedly
    return user
