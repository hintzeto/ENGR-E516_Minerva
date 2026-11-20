"""
llm.py - The one place the API connects to the model.

Each call is an HTTP POST to {OPENAI_BASE_URL}/chat/completions, so the same code
works with vLLM, Gemini's OpenAI-compatible endpoint, OpenAI, or SGLang.
"""
from typing import AsyncIterator

import openai
from openai import AsyncOpenAI

from . import config

# One client, shared by every request. It keeps connections open for reuse.
_client = AsyncOpenAI(
    base_url=config.OPENAI_BASE_URL,
    # Self-hosted servers often don't check keys, but the client needs a value.
    api_key=config.OPENAI_API_KEY or "not-needed",
    timeout=config.REQUEST_TIMOUT_SECONDS,
    max_retries=1,
)


async def stream(messages: list[dict]) -> AsyncIterator[str]:
    """Send the conversation and yield the answer piece by piece."""
    response = await _client.chat.completions.create(
        model=config.OPENAI_MODEL, messages=messages, stream=True)
    async for chunk in response:
        if chunk.choices and chunk.choices[0].delta.content:
            yield chunk.choices[0].delta.content


async def complete(messages: list[dict]) -> str:
    """Send the conversation and return the whole answer at once."""
    response = await _client.chat.completions.create(
        model=config.OPENAI_MODEL, messages=messages)
    return response.choices[0].message.content or ""


def custom_error(err: Exception) -> str:
    """Turn a model error into a user friendly message"""
    if isinstance(err, openai.AuthenticationError):
        return "The AI model rejected API key. Check OPENAI_API_KEY in api/.env."
    if isinstance(err, openai.RateLimitError):
        return "The AI model is busy or out of quota. Please try again shortly."
    if isinstance(err, openai.NotFoundError):
        return "The AI model wasn't found. Check OPENAI_MODEL in api/.env."
    if isinstance(err, (openai.APIConnectionError, openai.APITimeoutError)):
        return "Can't reach the AI model right now. Please try again shortly."
    if isinstance(err, openai.APIStatusError):
        if err.status_code == 503:
            return "The AI model is overloaded right now. Please try again in a minute."
        return f"The AI model returned an error ({err.status_code})."
    return "The AI model failed unexpectedly. Please try again."
