import os 

# Agents reach model with HTTP requests to {OPENAI_BASE_URL}/chat/completions
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL") 
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL")
# Timeout for model - 300 seconds to account for CPU model inference  
REQUEST_TIMOUT_SECONDS = float(os.getenv("REQUEST_TIMEOUT_SECONDS", "300"))

MAX_CHARS_PER_FILE = 20_000
MAX_CONTEXT_CHARS = 40_000
MAX_UPLOAD_MB = 50 