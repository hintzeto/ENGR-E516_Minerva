"""
Feedback page: upload a submission + paste the prompt/rubric, get structured feedback.
"""
import streamlit as st

import backend
import config
import state

user = state.require_login()

st.title("📝 Feedback")
st.caption("Upload a draft and get feedback grounded in your course materials.")

MAX_MB = 20  # friendly size limit

left, right = st.columns([1, 1], gap="large")

with left:
    uploaded = st.file_uploader(
        "Your submission",
        type=config.FEEDBACK_FILE_TYPES,
        help="PDF, Word, text, or code files.",
    )
    prompt = st.text_area(
        "Assignment prompt / rubric (optional but recommended)",
        height=200,
        placeholder="Paste the assignment instructions or grading rubric here...",
    )
    go = st.button("Get feedback", type="primary", width="stretch")

    if go:
        if uploaded is None:
            st.error("Please upload a file first.")
        elif uploaded.size > MAX_MB * 1024 * 1024:
            st.error(f"That file is larger than {MAX_MB} MB. Please upload a smaller one.")
        else:
            try:
                with st.spinner("Reading your submission and course materials..."):
                    st.session_state["feedback_result"] = backend.get_feedback(user, uploaded, prompt)
            except backend.BackendError as err:
                st.error(f"Couldn't generate feedback: {err}")
            except Exception:
                st.error("Something unexpected went wrong. Please try again.")

with right:
    result = st.session_state["feedback_result"]
    if result is None:
        st.info("Your feedback will appear here.")
    else:
        st.subheader("Feedback")
        st.markdown(result.get("summary", ""))

        with st.container(border=True):
            st.markdown("#### ✅ Strengths")
            for item in result.get("strengths", []):
                st.markdown(f"- {item}")

        with st.container(border=True):
            st.markdown("#### ⚠️ Areas to improve")
            for item in result.get("improvements", []):
                st.markdown(f"- {item}")

        with st.container(border=True):
            st.markdown("#### 💡 Suggestions")
            for item in result.get("suggestions", []):
                st.markdown(f"- {item}")

        sources = result.get("sources", [])
        with st.expander(f"📎 Sources ({len(sources)})"):
            for s in sources:
                st.markdown(f"**{s['file']}**, p. {s['page']}")
                st.caption(s["snippet"])

        if st.button("Clear feedback"):
            st.session_state["feedback_result"] = None
            st.rerun()
