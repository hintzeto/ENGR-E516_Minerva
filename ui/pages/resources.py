"""
Resource Management page.

Left side : planner (add tasks, weekly view, sorted task list, "Generate study plan").
Right side: chat with the resource-management assistant.

All data is kept in st.session_state (per user session). The AI parts go
through backend.plan_resources().
"""
from datetime import date, timedelta

import streamlit as st

import backend
import config
import state

user = state.require_login()

st.title("🗓️ Resource Management")
st.caption("Plan your work, pace your deadlines, and make the most of your time and compute.")

st.session_state.setdefault("week_offset", 0)  # 0 = this week, 1 = next week, ...


def run_assistant(message: str) -> None:
    """Send `message` to the backend, stream the reply, and save both to history."""
    history = st.session_state["resource_messages"]
    history.append({"role": "user", "content": message})
    with st.chat_message("user"):
        st.markdown(message)
    with st.chat_message("assistant"):
        try:
            with st.spinner("Thinking..."):
                stream = backend.plan_resources(user, st.session_state["tasks"], message)
            reply = st.write_stream(stream)  # shows text as it arrives
        except backend.BackendError as err:
            reply = f"Sorry, I couldn't do that: {err}"
            st.error(reply)
        except Exception:
            reply = "Something unexpected went wrong. Please try again."
            st.error(reply)
    history.append({"role": "assistant", "content": reply})


left, right = st.columns([1, 1], gap="large")

# =============================================================================
# LEFT: planner
# =============================================================================
with left:
    st.subheader("Planner")

    # ---- Add a task (st.form groups inputs so the page only reruns on submit) ----
    with st.form("add_task_form", clear_on_submit=True):
        title = st.text_input("Task / deadline", placeholder="e.g. Project proposal")
        course = st.selectbox("Course", config.COURSES + ["Other"])
        c1, c2 = st.columns(2)
        due = c1.date_input("Due date", value=date.today() + timedelta(days=7))
        hours = c2.number_input("Estimated hours", min_value=0.5, max_value=200.0,
                                value=2.0, step=0.5)
        added = st.form_submit_button("➕ Add task", width="stretch")

    if added:
        if not title.strip():
            st.error("Please give the task a title.")
        else:
            st.session_state["tasks"].append({
                "title": title.strip(),
                "course": course,
                "due": due.isoformat(),
                "hours": float(hours),
            })
            st.success(f"Added “{title.strip()}”.")

    tasks = sorted(st.session_state["tasks"], key=lambda t: t["due"])

    # ---- Weekly view -----------------------------------------------------------
    st.markdown("#### Weekly view")
    nav1, nav2, nav3 = st.columns([1, 2, 1])
    if nav1.button("◀ Prev", width="stretch"):
        st.session_state["week_offset"] -= 1
    if nav3.button("Next ▶", width="stretch"):
        st.session_state["week_offset"] += 1

    today = date.today()
    week_start = today - timedelta(days=today.weekday()) + timedelta(weeks=st.session_state["week_offset"])
    nav2.markdown(f"<div style='text-align:center'>Week of <b>{week_start:%b %d}</b></div>",
                  unsafe_allow_html=True)

    day_cols = st.columns(7)
    for i, col in enumerate(day_cols):
        day = week_start + timedelta(days=i)
        with col:
            st.markdown(f"**{day:%a}**  \n{day:%d}")
            todays = [t for t in tasks if t["due"] == day.isoformat()]
            if not todays:
                st.caption("-")
            for t in todays:
                st.caption(f"📌 {t['title']} ({t['hours']:g}h)")

    # ---- Sorted task list ----------------------------------------------------------
    st.markdown("#### All tasks")
    if not tasks:
        st.info("No tasks yet. Add your first assignment or deadline above.")
    else:
        st.dataframe(
            [{"Due": t["due"], "Task": t["title"], "Course": t["course"], "Hours": t["hours"]}
             for t in tasks],
            width="stretch",
            hide_index=True,
        )
        total = sum(t["hours"] for t in tasks)
        st.caption(f"{len(tasks)} task(s), about {total:g} hours of work in total.")

        # Remove a task
        labels = [f"{t['due']} - {t['title']}" for t in tasks]
        to_remove = st.selectbox("Remove a task", ["(choose one)"] + labels)
        if st.button("🗑️ Remove selected") and to_remove != "(choose one)":
            idx = labels.index(to_remove)
            st.session_state["tasks"].remove(tasks[idx])
            st.rerun()

    # ---- Generate study plan button ----------------------------------------------
    generate = st.button("✨ Generate study plan", type="primary", width="stretch")

# =============================================================================
# RIGHT: assistant chat
# =============================================================================
with right:
    st.subheader("Assistant")

    # Show previous messages (this runs on every rerun to redraw the conversation).
    if not st.session_state["resource_messages"]:
        st.info("Ask me how to pace your work, or click “Generate study plan”.")
    for msg in st.session_state["resource_messages"]:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # Button pressed on the left -> run it here so the answer appears in the chat.
    if generate:
        run_assistant("Generate a study plan for my upcoming tasks.")

    prompt = st.chat_input("Ask about scheduling, pacing, or resources...")
    if prompt:
        run_assistant(prompt)
