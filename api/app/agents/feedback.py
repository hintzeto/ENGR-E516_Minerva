import json
import re
from typing import TypedDict

from langgraph.graph import END, START, StateGraph

from ..llm import get_llm

FORMAT = ('Reply with only a JSON object with these keys: "summary" (string), '
          '"strengths", "improvements", "suggestions" (each a list of strings).')


class FeedbackState(TypedDict):
    user_id: str
    filename: str
    submission: str
    rubric: str
    result: dict


def _parse(text: str) -> dict:
    match = re.search(r"\{.*\}", text, re.DOTALL)
    data = json.loads(match.group(0)) if match else {}

    def as_list(value):
        return [str(v) for v in value] if isinstance(value, list) else []

    return {"summary": str(data.get("summary", "")),
            "strengths": as_list(data.get("strengths")),
            "improvements": as_list(data.get("improvements")),
            "suggestions": as_list(data.get("suggestions")),
            "sources": []}


async def review(state: FeedbackState) -> dict:
    content = (f"Give feedback on this student submission. {FORMAT}\n\n"
               f"Assignment prompt / rubric:\n{state['rubric'] or '(none provided)'}\n\n"
               f"Submission ({state['filename']}):\n{state['submission']}")
    answer = await get_llm().ainvoke([{"role": "user", "content": content}])
    return {"result": _parse(answer.content)}


def build_graph():
    graph = StateGraph(FeedbackState)
    graph.add_node("review", review)
    graph.add_edge(START, "review")
    graph.add_edge("review", END)
    return graph.compile()


feedback_graph = build_graph()