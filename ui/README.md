# Minerva - Frontend

Streamlit frontend for **Minerva**, a cloud AI assistant for graduate students
(IU ENGR-E516). It has three AI-backed features plus course-material management:

| Page | What it does |
|------|--------------|
| Home | Overview and quick links |
| Resource Management | Task planner, weekly view, "Generate study plan", assistant chat |
| Tutor | Course-aware chat with streamed answers and expandable Sources |
| Feedback | Upload a submission + rubric, get strengths / improvements / suggestions |
| Course Materials | Upload, list, and delete documents used by the tutor |

**To install and run the app, see the [root README](../README.md).** This file covers
how the frontend works.

## File structure

```
ui/
  app.py                  # entry point: login + sidebar navigation
  config.py               # BACKEND_MODE, model settings, courses, file types
  backend.py              # ALL backend calls (mock, OpenAI, or our API)
  state.py                # per-user session state + login placeholder
  pages/
    home.py  resources.py  tutor.py  feedback.py  materials.py
  config.toml             # theme + server settings (copied to .streamlit/ in Docker)
  requirements.txt
  Dockerfile  .dockerignore
  .env.example            # template for .env (the real .env is never committed)
```

## Backend modes

`BACKEND_MODE` (set in `ui/.env`) decides where answers come from:

| Mode | What happens |
|------|--------------|
| `mock` (default) | Fake but realistic data. No servers or keys needed. |
| `openai` | Calls an OpenAI-compatible model directly from the UI. |
| `api` | Sends HTTP requests to our own backend at `BACKEND_API_URL`. |

The older `USE_MOCK_BACKEND=false` still works and means `api`.

### What `openai` mode does

- **Tutor** streams real answers. A system prompt adds guardrails: hints and steps
  rather than full solutions on graded work.
- **Resource Management** sends the planner's task list and the student's message,
  and streams a study plan.
- **Course Materials** extracts text from uploads (PDF, DOCX, PPTX, text, code,
  notebooks). The tutor includes that text in its prompt for the matching course and
  lists the files under Sources. This is a stand-in for RAG until the vector DB exists;
  materials are kept in memory and reset when the app restarts.
- **Feedback** sends the submission and rubric and asks the model for JSON, which
  fills the strengths / improvements / suggestions cards.

### Model settings

| Variable | Default | Notes |
|----------|---------|-------|
| `OPENAI_API_KEY` | none | Required in `openai` mode |
| `OPENAI_MODEL` | `gpt-4o-mini` | Any chat model the endpoint serves |
| `OPENAI_BASE_URL` | `https://api.openai.com/v1` | Used when empty or unset |
| `REQUEST_TIMEOUT_SECONDS` | `60` | Per request |

### Switching to Jetstream2

SGLang serves the same OpenAI-compatible API, so moving from OpenAI
to our own GPU instance only changes `ui/.env`:

```
OPENAI_BASE_URL=http://<gpu-vm-private-ip>:30000/v1
OPENAI_MODEL=<model name the server reports>
OPENAI_API_KEY=anything-non-empty
```

The URL ends in `/v1`. SGLang's default port is `30000`; No code changes are needed.

## Login

The login is a placeholder: it asks for a username only, with no password. Any name
works, and each name gets its own chat history, tasks, and materials.

For real auth (e.g. IU login through OIDC with Streamlit's `st.login()`), replace
`state.login()` and the form in `app.py`. The rest of the app only relies on
`st.session_state["user_id"]`.

## Guide for teammates: plugging in the real backend

Every UI call goes through `backend.py`. The pages never import LangGraph, a vector
DB, or an LLM client. To go live:

1. Set `BACKEND_MODE=api` and `BACKEND_API_URL=http://<backend-host>:8000` in `ui/.env`.
2. **Either** implement HTTP endpoints matching the `# REAL BACKEND` sections in
   `backend.py` (e.g. FastAPI wrapping your LangGraph agents), **or** edit those
   sections to call your agents directly.
3. Keep the **function signatures and return shapes** the same:

| Function | Returns | Plug in |
|----------|---------|---------|
| `chat_with_tutor(user_id, course, messages)` | `(sources, token_stream)` | Tutor agent: retrieve chunks for the course, apply guardrails, stream from llama.cpp/SGLang |
| `plan_resources(user_id, tasks, message)` | `token_stream` | Resource agent: calendar/office-hours/compute tools |
| `get_feedback(user_id, file, prompt)` | dict with `summary`, `strengths`, `improvements`, `suggestions`, `sources` | Feedback agent: extract text, RAG, rubric-aware LLM; ask for JSON |
| `upload_course_material(user_id, file, course)` | record dict (`id`, `name`, `size_kb`, `course`, `uploaded`) | Chunk, embed, store in vector DB tagged by user + course |
| `list_course_materials(user_id)` | list of record dicts | Metadata store query |
| `delete_course_material(user_id, file_id)` | `bool` | Delete file AND its vectors |

Details:

- A **token stream** is any Python generator that yields strings; the UI renders it
  with `st.write_stream`. See `_openai_stream()` in `backend.py` for a working
  example against an OpenAI-compatible API.
- A **source** is `{"file": str, "page": int | str, "snippet": str}`.
- On any failure, `raise BackendError("friendly message")`. The pages catch it and
  show the message instead of crashing. For streams, raise *before* returning the
  generator, so errors land inside the pages' `try` blocks.
- `file` arguments are Streamlit `UploadedFile` objects: `.name`, `.type`,
  `.getvalue()` (bytes).
- Search the code for `TODO` to find every integration point.
- The course list in `config.COURSES` is hard-coded; replace it with a backend call
  when real courses exist.

## Concurrency

Streamlit runs each browser session in its own thread with its own
`st.session_state`, so 10+ concurrent users do not share state. The shared materials
store is keyed by `user_id` and lock-protected. The OpenAI client is created once and
shared, which is safe across threads.

## Deploying on Jetstream2

Use Docker on a CPU instance (`m3.small` is enough for the frontend):

1. Create an Ubuntu instance and note its floating IP.
2. In its Security Group, allow TCP **8501** (ideally restricted to the IU network or
   your IP) and SSH (22).
3. Install Docker, clone the repo, create `ui/.env`, and run
   `docker compose up -d --build`. The `restart: unless-stopped` setting keeps it running
   after reboots.
4. Visit `http://<floating-ip>:8501`.

This serves plain HTTP. Before real use, put it behind HTTPS (e.g. Caddy or nginx).
Behind nginx, the Streamlit location needs WebSocket support: `proxy_http_version 1.1`
and the `Upgrade` / `Connection "upgrade"` headers.

## Known limits of the prototype

- The login has no password, so anyone who can reach the page can use it. Restrict
  port 8501 in the Security Group until real auth exists.
- Chat history, tasks, and feedback live in `st.session_state`, so they reset when the
  browser tab is closed or refreshed. Persist them in the backend/DB for real use.
- Uploaded materials are stored in server memory and reset when the app restarts.
- In `openai` mode, uploads are pasted into the prompt in full (up to 40,000
  characters per question) rather than retrieved by relevance. Large materials are cut
  off, and long prompts cost more tokens.
- Could not get gpt4o-mini api key to work for free. Not sure if anyone knows of a way to get free tokens but any openai api key should       work for this. 
