# Minerva - Frontend Prototype

Streamlit frontend for **Minerva**, a cloud AI assistant for graduate students
(IU ENGR-E516). It has three AI-backed features plus course-material management:

| Page | What it does |
|------|--------------|
| Home | Overview and quick links |
| Resource Management | Task planner, weekly view, "Generate study plan", assistant chat |
| Tutor | Course-aware chat with streamed answers and expandable Sources |
| Feedback | Upload a submission + rubric, get strengths / improvements / suggestions |
| Course Materials | Upload, list, and delete documents used for RAG |

The app currently runs against a **mock backend** (fake but realistic data), so the
whole UI is demoable with no servers. Teammates plug in the real agents later.

## Project structure

```
minerva/
  app.py                  # entry point: login + sidebar navigation
  config.py               # USE_MOCK_BACKEND, backend URL, courses, file types
  backend.py              # ALL backend calls (mock now, real later)
  state.py                # per-user session helpers + login placeholder
  pages/
    home.py  resources.py  tutor.py  feedback.py  materials.py
  requirements.txt
  .streamlit/config.toml  # theme + server settings
  README.md
```

## Install

Requires Python 3.10+.

```bash
cd minerva
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Run

```bash
streamlit run app.py
```

Open http://localhost:8501, enter any username, and explore. Different browser
tabs/users get separate chat history, tasks, and results.

## Deploy on a JetStream2 VM

1. **Create an instance** (Ubuntu 22.04/24.04, `m3.small` is enough for the frontend)
   in Exosphere/Horizon and note its public (floating) IP.
2. **Open the port.** In the instance's *Security Group*, add an ingress rule:
   TCP, port **8501**, source `0.0.0.0/0` (or restrict to the IU network / your IP).
   Also make sure SSH (port 22) is allowed. If the VM has `ufw` enabled:
   `sudo ufw allow 8501/tcp`.
3. **Install and copy the code:**
   ```bash
   sudo apt update && sudo apt install -y python3-venv python3-pip git
   git clone <your-repo-url> minerva && cd minerva   # or scp the folder
   python3 -m venv .venv && source .venv/bin/activate
   pip install -r requirements.txt
   ```
4. **Run it** (the config already binds to `0.0.0.0:8501`):
   ```bash
   streamlit run app.py
   ```
   Visit `http://<floating-ip>:8501`.
5. **Keep it running after you log out** - quick way:
   ```bash
   nohup streamlit run app.py > minerva.log 2>&1 &
   ```
   Better: a systemd service. Create `/etc/systemd/system/minerva.service`:
   ```ini
   [Unit]
   Description=Minerva Streamlit frontend
   After=network.target

   [Service]
   User=exouser
   WorkingDirectory=/home/exouser/minerva
   Environment=USE_MOCK_BACKEND=true
   ExecStart=/home/exouser/minerva/.venv/bin/streamlit run app.py
   Restart=always

   [Install]
   WantedBy=multi-user.target
   ```
   then `sudo systemctl daemon-reload && sudo systemctl enable --now minerva`.

**Concurrency:** Streamlit runs each browser session in its own thread with its own
`st.session_state`, so 10+ concurrent users do not share state. Anything shared
(like the mock file store) is keyed by `user_id` and lock-protected.

**Note:** this serves plain HTTP. Before real use, put it behind HTTPS (e.g., Caddy
or nginx reverse proxy) and replace the placeholder login.

## Guide for teammates: replacing the mock with the real backend

Every UI call goes through `backend.py`. The pages never import LangGraph, a vector
DB, or an LLM client. To go live:

1. **Flip the switch** in `config.py` (or via environment variables):
   ```bash
   USE_MOCK_BACKEND=false BACKEND_API_URL=http://<backend-host>:8000 streamlit run app.py
   ```
2. **Either** implement HTTP endpoints matching the `# REAL BACKEND` sections in
   `backend.py` (e.g. FastAPI wrapping your LangGraph agents), **or** edit those
   sections to call your agents directly (import them and call in-process).
3. Keep the **function signatures and return shapes** the same:

| Function | Returns | Plug in |
|----------|---------|---------|
| `chat_with_tutor(user_id, course, messages)` | `(sources, token_stream)` | Tutor agent: retrieve chunks for the course, apply guardrails, stream from llama.cpp/SGLang |
| `plan_resources(user_id, tasks, message)` | `token_stream` | Resource agent: calendar/office-hours/compute tools |
| `get_feedback(user_id, file, prompt)` | dict with `summary`, `strengths`, `improvements`, `suggestions`, `sources` | Feedback agent: extract text, RAG, rubric-aware LLM; ask the LLM for JSON |
| `upload_course_material(user_id, file, course)` | record dict (`id`, `name`, `size_kb`, `course`, `uploaded`) | Chunk, embed, store in vector DB tagged by user + course |
| `list_course_materials(user_id)` | list of record dicts | Metadata store query |
| `delete_course_material(user_id, file_id)` | `bool` | Delete file AND its vectors |

Details:
- A **token stream** is any Python generator that yields strings; the UI renders it
  with `st.write_stream`. With llama.cpp / SGLang's OpenAI-compatible API, loop over
  the streamed chunks and `yield chunk.choices[0].delta.content`.
- A **source** is `{"file": str, "page": int, "snippet": str}`.
- On any failure, `raise BackendError("friendly message")`. The pages catch it and
  show the message instead of crashing.
- `file` arguments are Streamlit `UploadedFile` objects: `.name`, `.type`,
  `.getvalue()` (bytes).
- Search the code for `TODO` to find every integration point.
- The course list in `config.COURSES` is hard-coded; replace it with a backend call
  when real courses exist.

### Replacing the login

`state.login()` just stores the username in `st.session_state["user_id"]`. Swap it for
real auth (IU CAS/SSO, OIDC, an API token) as long as it ends by setting that one key.
Everything else (per-user chat history, tasks, backend calls) already uses `user_id`.

## Known limits of the prototype

- Chat history, tasks, and feedback live in `st.session_state`, so they reset when the
  browser tab is closed or refreshed. Persist them in the backend/DB for real use.
- The mock materials store is in server memory and resets when the app restarts.
