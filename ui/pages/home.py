"""Home page: short description of Minerva and quick links to the features."""
import streamlit as st

import config
import state

user = state.require_login()

st.title(f"Welcome back, {user} 👋")
st.write(
    f"**{config.APP_NAME}** is an AI assistant built for graduate students. "
    "It helps you manage your time, learn from your own course materials, "
    "and get feedback on your work before you submit it."
)

# Three feature cards side by side. st.page_link makes a clickable link to a page.
with st.container(border=True):
    st.subheader("🎓 Tutor")
    st.write("Ask questions and get guided, course-specific help with "
                 "sources from your materials.")
    st.page_link("pages/tutor.py", label="Start tutoring")


st.divider()
st.subheader("Getting started")
st.markdown(
    "1. Upload your syllabus and lecture notes in **Course Materials**.\n"
    "2. Add your deadlines in **Resource Management**.\n"
    "3. Ask the **Tutor** questions as you study.\n"
    "4. Submit drafts to **Feedback** before the deadline."
)

if config.USE_MOCK_BACKEND:
    st.info("Demo mode: Minerva is running with a mock backend, so answers are sample data.")
