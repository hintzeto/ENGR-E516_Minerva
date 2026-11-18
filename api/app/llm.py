from functools import lru_cache
import openai
from langchain_openai import ChatOpenAI 
from . import config 

@lru_cache 
def get_llm() -> ChatOpenAI: 
    """Create chat model client once and reuse it"""
    return ChatOpenAI(
        model = config.OPENAI_MODEL, 
        base_url = config.OPENAI_BASE_URL, 
        api_key = config.OPENAI_API_KEY, 
        timeout = config.REQUEST_TIMOUT_SECONDS, 
        max_retries = 1
    )

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