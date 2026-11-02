"""
backend.py - EVERY call from the UI to the "brain" of Minerva lives in this file.

The pages never talk to LangGraph, the vector DB, or the LLM directly. They only
call the functions below. That means:

  * BACKEND_MODE=mock (default): the functions return realistic FAKE data
    so the whole UI can be demoed without any servers.
  * BACKEND_MODE=openai: the functions call an OpenAI-compatible model directly
    (OpenAI now; SGLang / llama.cpp on JetStream2 later via OPENAI_BASE_URL).
  * Later, teammates replace the bodies (or just flip USE_MOCK_BACKEND to False
    and implement the matching HTTP endpoints) and the UI keeps working unchanged.

Function contract (keep these signatures stable so the UI doesn't break):
    chat_with_tutor(user_id, course, messages)  -> (sources, token_stream)

A "token_stream" is just a Python generator that yields small pieces of text.
The UI feeds it to st.write_stream(), which prints it like ChatGPT typing.

All functions raise BackendError with a FRIENDLY message if something goes wrong;
the pages catch it and show the message instead of crashing.
"""
import time
from typing import Iterator
import config


class BackendError(Exception):
    """Raised for any backend problem. The message is safe to show to students."""



def _stream_text(text: str) -> Iterator[str]:
    """Yield `text` a few words at a time with a small delay (fake LLM streaming)."""
    for word in text.split(" "):
        time.sleep(config.MOCK_STREAM_DELAY)
        yield word + " "


def _check_user(user_id: str) -> None:
    """Basic validation shared by all functions."""
    if not user_id:
        raise BackendError("You need to be logged in to do that.")


# =============================================================================
# OPENAI HELPERS (used only when BACKEND_MODE=openai)
# =============================================================================
# This mode talks to any OpenAI-compatible chat API. Today that's OpenAI itself;
# later the same code reaches SGLang / llama.cpp on JetStream2 by changing
# OPENAI_BASE_URL. There's no vector DB yet, so "RAG" here is a stand-in: the
# text of the student's uploaded materials is pasted into the prompt.

_MAX_CHARS_PER_FILE = 20_000   # text kept per uploaded file
_MAX_CONTEXT_CHARS = 40_000    # total course-material text sent per question
_openai_client = None

def _client():
    """Create the OpenAI client once per server process and reuse it."""
    global _openai_client
    if _openai_client is None:
        if not config.OPENAI_API_KEY:
            raise BackendError("The AI model isn't configured (OPENAI_API_KEY is missing).")
        from openai import OpenAI  # imported here so other modes don't need it

        _openai_client = OpenAI(
            api_key=config.OPENAI_API_KEY,
            base_url=config.OPENAI_BASE_URL,
            timeout=config.REQUEST_TIMEOUT_SECONDS,
        )
    return _openai_client


def _openai_error(err: Exception) -> BackendError:
    """Turn an OpenAI SDK exception into a message that's safe to show students."""
    import openai

    if isinstance(err, openai.AuthenticationError):
        return BackendError("The AI model rejected our API key. Check OPENAI_API_KEY.")
    if isinstance(err, openai.RateLimitError):
        return BackendError("The AI model is busy or out of quota. Please try again shortly.")
    if isinstance(err, (openai.APIConnectionError, openai.APITimeoutError)):
        return BackendError("Can't reach the AI model right now. Please try again shortly.")
    if isinstance(err, openai.APIStatusError):
        return BackendError(f"The AI model returned an error ({err.status_code}).")
    return BackendError("The AI model failed unexpectedly. Please try again.")


def _openai_stream(messages: list[dict]) -> Iterator[str]:
    """
    Start a streaming chat completion and return a generator of text pieces.

    The request is sent BEFORE returning, so connection/auth errors raise
    BackendError here, where the pages already catch it.
    """
    import openai

    try:
        stream = _client().chat.completions.create(
            model=config.OPENAI_MODEL, messages=messages, stream=True,
        )
    except openai.OpenAIError as err:
        raise _openai_error(err) from err

    def _gen() -> Iterator[str]:
        try:
            for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        except openai.OpenAIError:
            yield "\n\n_(The answer was cut off by a connection problem. Please try again.)_"

    return _gen()


# =============================================================================
# REAL BACKEND HELPERS (used only when BACKEND_MODE=api)
# =============================================================================
def _http_post(path: str, **kwargs):
    """POST to the real backend and turn network problems into BackendError."""
    import requests  # imported here so mock mode doesn't need it

    try:
        resp = requests.post(
            f"{config.BACKEND_API_URL}{path}",
            timeout=config.REQUEST_TIMEOUT_SECONDS,
            **kwargs,
        )
        resp.raise_for_status()
        return resp
    except requests.exceptions.ConnectionError:
        raise BackendError("Can't reach the Minerva server right now. Please try again shortly.")
    except requests.exceptions.Timeout:
        raise BackendError("The Minerva server took too long to respond. Please try again.")
    except requests.exceptions.HTTPError as err:
        raise BackendError(f"The server returned an error ({err.response.status_code}).")



# =============================================================================
# 1) TUTOR  (RAG over course materials + guardrailed LLM)
# =============================================================================
def chat_with_tutor(user_id: str, course: str, messages: list[dict]):
    """
    Ask the tutor a question.

    Args:
        user_id:  who is asking (use it to find THEIR uploaded materials).
        course:   the course selected in the dropdown.
        messages: full chat history, a list like
                  [{"role": "user" | "assistant", "content": "..."}].
                  The last item is the newest user question.

    Returns:
        (sources, token_stream)
        sources      - list of dicts: {"file": str, "page": int, "snippet": str}
        token_stream - generator yielding pieces of the answer text.

    Why a tuple? In RAG, retrieval happens BEFORE generation, so the sources are
    known immediately and the answer streams afterwards.
    """
    _check_user(user_id)
    if not messages or messages[-1]["role"] != "user":
        raise BackendError("Please type a question for the tutor.")

    if config.USE_MOCK_BACKEND:
        question = messages[-1]["content"]
        sources = []

        answer = (
            "This is a sample for the MOCK_BACKEND"
        )
        return sources, _stream_text(answer)

    if config.USE_OPENAI:
        return [], _openai_stream(messages)

    # ---- REAL BACKEND -------------------------------------------------------
    # TODO (tutor agent teammate): POST to your LangGraph tutoring agent.
    #   The agent should: (1) retrieve top-k chunks for `course` from the vector
    #   store, (2) apply tutoring guardrails (guide, don't just give answers),
    #   (3) stream tokens from llama.cpp / SGLang on JetStream2.
    #   Expected response: JSON {"sources": [...]} on the first line, then
    #   streamed text. Adjust this parsing to whatever your API actually does.
    resp = _http_post(
        "/tutor/chat",
        json={"user_id": user_id, "course": course, "messages": messages},
        stream=True,
    )
    import json

    lines = resp.iter_lines(decode_unicode=True)
    first = next(lines, "{}")
    sources = json.loads(first).get("sources", [])

    def _stream() -> Iterator[str]:
        for line in lines:
            if line:
                yield line + "\n"

    return sources, _stream()
