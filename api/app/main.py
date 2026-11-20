import json
import logging
from typing import AsyncIterator

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from . import config, store 
from .agents.feedback import feedback_answer
from .agents.planner import plan_answer
from .agents.tutor import tutor_answer
from .llm import custom_error

log = logging.getLogger("minerva.api")
app = FastAPI(title="Minerva API")


class Message(BaseModel):
    role: str
    content: str


class TutorRequest(BaseModel):
    user_id: str
    course: str
    messages: list[Message]

class Task(BaseModel):
    title: str
    course: str
    due: str
    hours: float


class PlanRequest(BaseModel):
    user_id: str
    tasks: list[Task] = []
    message: str
    
def _line(event: dict) -> str:
    return json.dumps(event) + "\n"


async def _stream_answer(chunks: AsyncIterator[str],
                         sources: list[dict] | None = None) -> AsyncIterator[str]:
    """Turn an agent's answer into the NDJSON events the UI reads."""
    if sources is not None:
        yield _line({"type": "sources", "sources": sources})
    try:
        async for text in chunks:
            yield _line({"type": "token", "text": text})
        yield _line({"type": "done"})
    except Exception as err:
        log.exception("Agent failed")
        yield _line({"type": "error", "message": custom_error(err)})


def _ndjson(lines: AsyncIterator[str]) -> StreamingResponse:
    return StreamingResponse(lines, media_type="application/x-ndjson")


@app.get("/health")
def health():
    return {"status": "ok", "model": config.OPENAI_MODEL}


@app.post("/tutor/chat")
async def tutor_chat(req: TutorRequest):
    if not req.messages or req.messages[-1].role != "user":
        raise HTTPException(400, "The last message must be the student's question.")
    sources, chunks = tutor_answer(req.user_id, req.course,
                                   [m.model_dump() for m in req.messages])
    return _ndjson(_stream_answer(chunks, sources))

@app.post("/resources/plan")
async def resources_plan(req: PlanRequest):
    chunks = plan_answer([t.model_dump() for t in req.tasks], req.message)
    return _ndjson(_stream_answer(chunks))


async def _read_upload(file: UploadFile) -> bytes:
    data = await file.read()
    if len(data) > config.MAX_UPLOAD_MB * 1024 * 1024:
        raise HTTPException(413, f"Files must be under {config.MAX_UPLOAD_MB} MB.")
    return data


@app.post("/feedback")
async def feedback(user_id: str = Form(...), prompt: str = Form(""), file: UploadFile = File(...)):
    data = await _read_upload(file)
    try:
        text = store.extract_text(file.filename, data)
    except store.UnreadableFile as err:
        raise HTTPException(422, str(err))
    if not text:
        raise HTTPException(422, f"{file.filename} doesn't contain any readable text.")
    try:
        return await feedback_answer(file.filename, text, prompt)
    except json.JSONDecodeError:
        raise HTTPException(502, "The AI model returned feedback in an unexpected format. Try again.")
    except Exception as err:
        log.exception("Feedback agent failed")
        raise HTTPException(502, custom_error(err))


@app.post("/materials")
async def upload_material(user_id: str = Form(...), course: str = Form(""),
                          file: UploadFile = File(...)):
    data = await _read_upload(file)
    try:
        return store.add_material(user_id, file.filename, data, course or None)
    except store.UnreadableFile as err:
        raise HTTPException(422, str(err))


@app.get("/materials")
def list_materials(user_id: str):
    return store.list_materials(user_id)


@app.delete("/materials/{material_id}")
def delete_material(material_id: str, user_id: str):
    return {"deleted": store.delete_material(user_id, material_id)}