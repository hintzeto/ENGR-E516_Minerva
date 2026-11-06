"""
Tutor page: chat with a course-aware tutor. Each course has its own chat history.
Every answer has an expandable "Sources" section listing the materials used.
"""
import streamlit as st

import backend
import config
import state

user = state.require_login()

st.title("🎓 Tutor")

# ---- Course selector ----------------------------------------------------------
course = st.selectbox("Course", config.COURSES)

# Chat history is stored per course: {course_name: [messages]}
all_chats = st.session_state["tutor_messages"]
messages = all_chats.setdefault(course, [])


def show_sources(sources: list[dict]) -> None:
    """Draw the expandable Sources section under an answer."""
    with st.expander(f"📎 Sources ({len(sources)})"):
        if not sources:
            st.caption("No course materials were used for this answer.")
        for s in sources:
            st.markdown(f"**{s['file']}**, p. {s['page']}")
            st.caption(s["snippet"])


# ---- Show existing conversation ---------------------------------------------------
if not messages:
    st.info(f"Ask a question about **{course}**. The tutor will guide you with hints "
            "and cite the course materials it used.")
for msg in messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg["role"] == "assistant":
            show_sources(msg.get("sources", []))

if messages and st.button("Clear this chat"):
    all_chats[course] = []
    st.rerun()

# ---- New question -------------------------------------------------------------------
question = st.chat_input(f"Ask the tutor about {course.split(':')[0]}...")
if question:
    messages.append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.markdown(question)

    with st.chat_message("assistant"):
        try:
            with st.spinner("Searching your course materials..."):
                # Only role+content go to the backend (not our extra "sources" field).
                history = [{"role": m["role"], "content": m["content"]} for m in messages]
                sources, stream = backend.chat_with_tutor(user, course, history)
            answer = st.write_stream(stream)
            show_sources(sources)
            messages.append({"role": "assistant", "content": answer, "sources": sources})
        except backend.BackendError as err:
            st.error(f"Sorry, the tutor couldn't answer: {err}")
            messages.pop()  # drop the unanswered question so history stays clean
        except Exception:
            st.error("Something unexpected went wrong. Please try again.")
            messages.pop()
