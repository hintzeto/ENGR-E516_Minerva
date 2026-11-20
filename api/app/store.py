import io 
import json 
import threading
import uuid
from datetime import datetime
from . import config 

_MATERIALS: dict[str, list[dict]] = {} 
_LOCK = threading.Lock() 

class UnreadableFile(Exception): 
    """The uploaded file's contents cannot be extracted"""

def extract_text(filename: str, data: bytes) -> str: 
    name = filename.lower()
    try: 
        if name.endswith(".pdf"): 
            from pypdf import PdfReader
            reader = PdfReader(io.BytesIO(data))
            text = "\n".join(f"[page {i}]\n{p.extract_text() or ''}" for i, p in enumerate(reader.pages, start=1))
        elif name.endswith(".docx"): 
            from docx import Document
            text = "\n".join(p.text for p in Document(io.BytesIO(data)).paragraphs)
        elif name.endswith(".pptx"):
            from pptx import Presentation
            slides = []
            for i, slide in enumerate(Presentation(io.BytesIO(data)).slides, start=1):
                parts = [s.text_frame.text for s in slide.shapes if s.has_text_frame]
                slides.append(f"[slide {i}]\n" + "\n".join(parts))
            text = "\n".join(slides)
        elif name.endswith(".ipynb"):
            cells = json.loads(data).get("cells", [])
            text = "\n\n".join("".join(c.get("source", [])) for c in cells)
        else:
            text = data.decode("utf-8", errors="replace")
    except Exception as err:
        raise UnreadableFile(f"Couldn't read the text in {filename}. Is the file valid?") from err
    return text.strip()[: config.MAX_CHARS_PER_FILE]


def add_material(user_id: str, filename: str, data: bytes, course: str | None) -> dict:
    record = {
        "id": uuid.uuid4().hex[:8],
        "name": filename,
        "size_kb": round(len(data) / 1024, 1),
        "course": course or "Unassigned",
        "uploaded": datetime.now().strftime("%Y-%m-%d %H:%M"),
    }
    stored = {**record, "text": extract_text(filename, data)}
    with _LOCK:
        _MATERIALS.setdefault(user_id, []).append(stored)
    return record


def list_materials(user_id: str) -> list[dict]:
    with _LOCK:
        return [{k: v for k, v in m.items() if k != "text"} for m in _MATERIALS.get(user_id, [])]


def delete_material(user_id: str, material_id: str) -> bool:
    with _LOCK:
        items = _MATERIALS.get(user_id, [])
        remaining = [m for m in items if m["id"] != material_id]
        _MATERIALS[user_id] = remaining
        return len(remaining) != len(items)


def material_context(user_id: str, course: str) -> tuple[str, list[dict]]:
    with _LOCK:
        mine = [m for m in _MATERIALS.get(user_id, [])
                if m["course"] in (course, "Unassigned") and m["text"]]
    blocks, sources, used = [], [], 0
    for m in mine:
        piece = m["text"][: config.MAX_CONTEXT_CHARS - used]
        if not piece:
            break
        blocks.append(f"### File: {m['name']}\n{piece}")
        sources.append({"file": m["name"], "page": "—",
                        "snippet": "Full text included as course context."})
        used += len(piece)
    return "\n\n".join(blocks), sources