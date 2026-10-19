"""
config.py - Central settings for the Minerva frontend.

Teammates: to switch from the fake (mock) backend to a real one, change
USE_MOCK_BACKEND to False and set BACKEND_API_URL. Nothing else in the UI
needs to change, because every page only talks to backend.py.

You can also override any value with an environment variable, e.g.:
    USE_MOCK_BACKEND=false BACKEND_API_URL=http://10.0.0.5:8000 streamlit run app.py
"""
import os


def _env_bool(name: str, default: bool) -> bool:
    """Read a True/False value from an environment variable."""
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in ("1", "true", "yes", "on")


# ---- The one-line switch ---------------------------------------------------
# True  -> backend.py returns realistic fake data (fully demoable, no servers)
# False -> backend.py sends HTTP requests to BACKEND_API_URL
USE_MOCK_BACKEND = _env_bool("USE_MOCK_BACKEND", True)

# ---- Real backend settings (only used when USE_MOCK_BACKEND is False) ------
BACKEND_API_URL = os.getenv("BACKEND_API_URL", "http://localhost:8000")
REQUEST_TIMEOUT_SECONDS = int(os.getenv("REQUEST_TIMEOUT_SECONDS", "60"))

# ---- UI settings ------------------------------------------------------------
APP_NAME = "Minerva"
APP_TAGLINE = "Your AI study partner for graduate school"

# Demo course list. TODO: replace with a backend call once courses are real.
COURSES = [
    "ENGR-E516: Cloud Computing",
    "ENGR-E599: Applied Machine Learning",
    "ENGR-E511: Data Structures & Algorithms",
]

# Files the uploaders accept (without the dot)
FEEDBACK_FILE_TYPES = ["pdf", "docx", "txt", "md", "py", "java", "c", "cpp", "js", "ipynb"]
MATERIAL_FILE_TYPES = ["pdf", "docx", "txt", "md", "pptx"]

# Delay between streamed words in mock mode (seconds). Lower = faster typing.
MOCK_STREAM_DELAY = 0.03
