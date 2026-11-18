import json
import logging
from typing import AsyncIterator

from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from . import config
from .agents.tutor import tutor_graph
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


def _line(event: dict) -> str:
    return json.dumps(event) + "\n"


async def _stream_graph(graph, inputs: dict, answer_node: str) -> AsyncIterator[str]:
    try:
        async for mode, chunk in graph.astream(inputs, stream_mode=["updates", "messages"]):
            if mode == "updates":
                for update in chunk.values():
                    if update and "sources" in update:
                        yield _line({"type": "sources", "sources": update["sources"]})
            elif mode == "messages":
                message, meta = chunk
                if meta.get("langgraph_node") == answer_node and isinstance(message.content, str) \
                        and message.content:
                    yield _line({"type": "token", "text": message.content})
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
    inputs = {"user_id": req.user_id, "course": req.course,
              "messages": [m.model_dump() for m in req.messages],
              "context": "", "sources": []}
    return _ndjson(_stream_graph(tutor_graph, inputs, answer_node="generate"))