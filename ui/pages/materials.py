"""Course Materials page: upload PDFs, then search them by meaning."""
import streamlit as st
from sqlalchemy import func, select

import config
import rag
import state
from models import CourseChunk

# st.connection is cached by name, so this is the same connection app.py opened.
db = st.connection("sql", type="sql", url=config.DATABASE_URI)

user = state.require_login()
user_id = st.session_state["user_id"]

st.title("📚 Course Materials")
course = st.selectbox("Course", config.COURSES)

# ---- 1) Upload ---------------------------------------------------------------
with st.expander("Upload PDFs", expanded=False):
    files = st.file_uploader("Syllabus, slides, papers...", type="pdf", accept_multiple_files=True)
    if files and st.button("Process files", type="primary"):
        with db.session as session:
            for f in files:
                with st.spinner(f"Reading and embedding {f.name}..."):
                    n = rag.ingest_pdf(session, user_id, course, f.name, f.getvalue())
                st.success(f"{f.name}: stored {n} chunks")

# ---- What is stored ----------------------------------------------------------
with db.session as session:
    rows = session.execute(
        select(CourseChunk.filename, func.count(), func.max(CourseChunk.page))
        .where(CourseChunk.user_id == user_id).group_by(CourseChunk.filename)
    ).all()
if rows:
    st.caption("Stored: " + " · ".join(f"**{name}** ({n} chunks, {p} pages)" for name, n, p in rows))
else:
    st.info("Nothing uploaded yet. Open **Upload PDFs** above.")
    st.stop()

# ---- 2) Search ---------------------------------------------------------------
question = st.text_input("Ask about your materials", placeholder="e.g. How is the final grade calculated?")
k = st.slider("Results", 1, 10, 4)

if question:
    with db.session as session:
        results = rag.search(session, user_id, question, k=k)
    # cosine distance 0 = identical, so 1 - distance reads as a similarity score
    results = [(chunk, 1 - dist) for chunk, dist in results]
    if not results or results[0][1] < config.MIN_SIMILARITY:
        st.warning("No good match in your uploaded materials for that question.")
        results = []
    for chunk, similarity in results:
        with st.container(border=True):
            st.markdown(f"**{chunk.filename}** · page {chunk.page} · match **{similarity:.0%}**")
            st.progress(max(0.0, min(1.0, similarity)))
            st.write(chunk.content)
