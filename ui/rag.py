"""
rag.py - The retrieval part of RAG, in four small steps.

  1. extract_pages: read the text of each PDF page          (pypdf)
  2. split_text:    cut long pages into smaller chunks
  3. embed:         turn text into a list of 384 numbers    (fastembed, local model)
  4. search:        embed the question, ask Postgres for the closest chunks (pgvector)

For slides, one page = one slide, so a chunk keeps its page number and the UI
can say "this came from slide 12 of VirtualMachine.pdf".
"""
import io
import logging

import streamlit as st
from pypdf import PdfReader
from sqlalchemy import delete, select

import config
from models import CourseChunk

logging.getLogger("pypdf").setLevel(logging.ERROR)   # quiet harmless PDF warnings


@st.cache_resource(show_spinner="Loading embedding model...")
def _model():
    """Load the embedding model once per server process."""
    from fastembed import TextEmbedding
    return TextEmbedding(config.EMBEDDING_MODEL, cache_dir=config.EMBEDDING_CACHE_DIR)


def embed(texts: list[str]) -> list[list[float]]:
    """Text in -> one 384-number vector per text out."""
    return [v.tolist() for v in _model().embed(texts)]


def extract_pages(pdf_bytes: bytes) -> list[tuple[int, str]]:
    """Return [(page_number, text)] for every page that has real text."""
    reader = PdfReader(io.BytesIO(pdf_bytes))
    pages = []
    for number, page in enumerate(reader.pages, start=1):
        text = " ".join((page.extract_text() or "").split())  # collapse whitespace
        if len(text) > 30:  # skip blank / image-only pages
            pages.append((number, text))
    return pages


def split_text(text: str, limit: int) -> list[str]:
    """Cut text into pieces of at most `limit` characters, breaking on spaces."""
    pieces = []
    while len(text) > limit:
        cut = text.rfind(" ", 0, limit)
        cut = cut if cut > 0 else limit
        pieces.append(text[:cut])
        text = text[cut:].strip()
    pieces.append(text)
    return pieces


def ingest_pdf(session, user_id: int, course: str, filename: str, pdf_bytes: bytes) -> int:
    """Read a PDF, embed its chunks and store them. Returns the number of chunks."""
    # Re-uploading the same file replaces it instead of creating duplicates.
    session.execute(delete(CourseChunk).where(
        CourseChunk.user_id == user_id, CourseChunk.filename == filename))

    chunks = [(page, piece)
              for page, text in extract_pages(pdf_bytes)
              for piece in split_text(text, config.MAX_CHUNK_CHARS)]
    if chunks:
        vectors = embed([piece for _, piece in chunks])
        session.add_all([
            CourseChunk(user_id=user_id, course=course, filename=filename,
                        page=page, content=piece, embedding=vec)
            for (page, piece), vec in zip(chunks, vectors)
        ])
    session.commit()
    return len(chunks)


def search(session, user_id: int, question: str, k: int = 5, course: str | None = None):
    """Return [(chunk, distance)] for the k chunks closest in meaning to the question."""
    q = embed([question])[0]
    distance = CourseChunk.embedding.cosine_distance(q)   # SQL: embedding <=> q
    stmt = (select(CourseChunk, distance)
            .where(CourseChunk.user_id == user_id)
            .order_by(distance)
            .limit(k))
    if course:
        stmt = stmt.where(CourseChunk.course == course)
    return session.execute(stmt).all()
