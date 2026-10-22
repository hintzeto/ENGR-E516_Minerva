"""
Course Materials page: upload, view, and delete the documents used for RAG.
"""
import streamlit as st

import backend
import config
import state

user = state.require_login()

st.title("📚 Course Materials")
st.caption("Documents you upload here are used by the Tutor and Feedback features.")

# ---- Upload ---------------------------------------------------------------------------
with st.form("upload_form", clear_on_submit=True):
    files = st.file_uploader(
        "Upload documents",
        type=config.MATERIAL_FILE_TYPES,
        accept_multiple_files=True,
    )
    course = st.selectbox("Course", config.COURSES + ["Other"])
    submitted = st.form_submit_button("Upload", type="primary")

if submitted:
    if not files:
        st.error("Please choose at least one file.")
    else:
        for f in files:
            try:
                with st.spinner(f"Processing {f.name}..."):
                    backend.upload_course_material(user, f, course)
                st.success(f"Uploaded {f.name}")
            except backend.BackendError as err:
                st.error(f"Couldn't upload {f.name}: {err}")
            except Exception:
                st.error(f"Something went wrong uploading {f.name}.")

# ---- List ----------------------------------------------------------------------------
st.subheader("Your documents")
try:
    materials = backend.list_course_materials(user)
except backend.BackendError as err:
    st.error(f"Couldn't load your documents: {err}")
    materials = []

if not materials:
    st.info("No documents yet. Upload your syllabus or lecture notes to get started.")
else:
    for m in materials:
        with st.container(border=True):
            c1, c2, c3 = st.columns([5, 3, 1])
            c1.markdown(f"**{m['name']}**  \n{m['course']}")
            c2.caption(f"{m['size_kb']} KB · uploaded {m['uploaded']}")
            if c3.button("🗑️", key=f"del_{m['id']}", help="Delete this document"):
                try:
                    backend.delete_course_material(user, m["id"])
                    st.rerun()
                except backend.BackendError as err:
                    st.error(f"Couldn't delete: {err}")
