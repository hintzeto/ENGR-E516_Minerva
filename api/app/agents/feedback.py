"""feedback.py - Personalized Feedback agent, as a plain function. Returns one JSON result."""
import json
import re

from .. import llm

FORMAT = ('Reply with only a JSON object with these keys: "summary" (string), '
          '"strengths", "improvements", "suggestions" (each a list of strings).')


def _parse(text: str) -> dict:
    """Pull the JSON object out of the reply, even if it's wrapped in ```json fences."""
    match = re.search(r"\{.*\}", text, re.DOTALL)
    data = json.loads(match.group(0)) if match else {}

    def as_list(value):
        return [str(v) for v in value] if isinstance(value, list) else []

    return {"summary": str(data.get("summary", "")),
            "strengths": as_list(data.get("strengths")),
            "improvements": as_list(data.get("improvements")),
            "suggestions": as_list(data.get("suggestions")),
            "sources": []}


async def feedback_answer(filename: str, submission: str, rubric: str) -> dict:
    content = (f"Give feedback on this student submission. {FORMAT}\n\n"
               f"Assignment prompt / rubric:\n{rubric or '(none provided)'}\n\n"
               f"Submission ({filename}):\n{submission}")
    return _parse(await llm.complete([{"role": "user", "content": content}]))
