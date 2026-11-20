"""
tutor.py - The Tutor agent, as a plain function.

Two steps: find the student's course materials, then ask the model with them.
(LangGraph was removed; Langflow will take over the agent logic later.)
"""
from .. import llm, store


def tutor_answer(user_id: str, course: str, messages: list[dict]):
    """Returns (sources, token_stream)."""
    context, sources = store.material_context(user_id, course)
    prompt = list(messages)
    if context:
        prompt.insert(0, {"role": "system",
                          "content": "Course materials uploaded by the student:\n" + context})
    return sources, llm.stream(prompt)
