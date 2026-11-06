# Minerva Tutor

Minerva Frontend - Tutor feature. Just a test for reliable OpenAI streaming. Once this
is tested, we can added course materials context. 

This branch contains **only the Tutor**. The Resource Management, Feedback, and Course
Materials features live on the `claude-vibe-full-project` branch.

| Page | What it does |
|------|--------------|
| Home | Overview |
| Tutor | Course-aware chat with streamed answers. Each course keeps its own chat history. |

## How it works

```
Browser ──▶ Streamlit (ui/) ──▶ backend.py ──▶ mock text, an OpenAI-compatible model, or our API
```

The pages never call a model directly. Every request goes through one function in
`backend.py`:

```python
chat_with_tutor(user_id, course, messages) -> (sources, token_stream)
```

- `messages` is the full chat history: `[{"role": "user" | "assistant", "content": "..."}]`
- `sources` is a list of `{"file": str, "page": int | str, "snippet": str}`, shown under
  each answer. Empty for now. 
- `token_stream` is a generator of text pieces, rendered with `st.write_stream`

`BACKEND_MODE` decides where answers come from:

| Mode | Where the answer comes from | Needs |
|------|-----------------------------|-------|
| `mock` (default) | A fixed, built-in answer. Nothing is sent anywhere. | Nothing |
| `openai` | Any OpenAI-compatible chat API: OpenAI, or SGLang / llama.cpp on Jetstream2 | A base URL and model name (and a key for OpenAI) |
| `api` | Our own backend's `/tutor/chat` endpoint | `BACKEND_API_URL` |

In `openai` mode the chat history is sent to the model **as is, with no system prompt**,
and the tutor returns no sources. The model's own defaults decide how it answers, so it
will answer graded questions directly rather than giving hints.

## Files

```
ui/
  app.py              # entry point: login + navigation (Home, Tutor)
  config.py           # BACKEND_MODE, model settings, course list
  backend.py          # chat_with_tutor() and its helpers
  state.py            # per-session state and the username-only login
  pages/
    home.py
    tutor.py
  config.toml         # theme + server settings (copied to .streamlit/ in Docker)
  requirements.txt    # streamlit, requests, openai
  Dockerfile
  .dockerignore
  .env.example        # template for ui/.env
```

## Configure `ui/.env`

```bash
cp ui/.env.example ui/.env
```

`ui/.env` is git-ignored; never commit it.

| Variable | Default | Notes |
|----------|---------|-------|
| `BACKEND_MODE` | `mock` | `mock`, `openai`, or `api` |
| `OPENAI_API_KEY` | none | Required for OpenAI. For a self-hosted server that doesn't check keys, use any placeholder such as `not-needed`. |
| `OPENAI_MODEL` | `gpt-4o-mini` | For a self-hosted server, the `id` from `GET /v1/models` |
| `OPENAI_BASE_URL` | `https://api.openai.com/v1` | Leave empty for OpenAI |
| `BACKEND_API_URL` | `http://localhost:8000` | Only for `api` mode |
| `REQUEST_TIMEOUT_SECONDS` | `60` | Raise it (e.g. `180`) for slow self-hosted models |

Rules: one `KEY=value` per line, no quotes, no spaces around `=`, and no comments on the
same line as a value.

**Example: OpenAI**

```
BACKEND_MODE=openai
OPENAI_API_KEY=sk-your-key
OPENAI_MODEL=gpt-4o-mini
OPENAI_BASE_URL=
```

**Example: a model on Jetstream2**

```
BACKEND_MODE=openai
OPENAI_API_KEY=not-needed
OPENAI_MODEL=<model id from /v1/models>
OPENAI_BASE_URL=http://<gpu-vm-private-ip>:<port>/v1
```

SGLang's default port is `30000`; llama.cpp's server uses `8080`. Check the server is
reachable from the frontend VM first:

```bash
curl http://<gpu-vm-private-ip>:<port>/v1/models
```

## Run with Docker

From the repo root:

```bash
docker build -t minerva-tutor ./ui
docker run -d --name minerva-tutor -p 8501:8501 \
  --env-file ui/.env --restart unless-stopped minerva-tutor
```

Open `http://localhost:8501` (or `http://<floating-ip>:8501` on Jetstream2) and log in
with any username.

To try it without a `.env` file, replace `--env-file ui/.env` with `-e BACKEND_MODE=mock`.

**Useful commands**

```bash
docker logs -f minerva-tutor                                     # live output
docker exec minerva-tutor env | grep -E "BACKEND|OPENAI_MODEL"   # check settings
docker rm -f minerva-tutor                                       # stop and remove
```

**After changing `.env` or pulling new code**, replace the container. A running container
doesn't pick up changes on its own:

```bash
docker rm -f minerva-tutor
docker build -t minerva-tutor ./ui
docker run -d --name minerva-tutor -p 8501:8501 \
  --env-file ui/.env --restart unless-stopped minerva-tutor
```

## Run without Docker

Requires Python 3.10 or newer.

```bash
cd ui
python3 -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate
pip install -r requirements.txt
mkdir -p .streamlit && cp config.toml .streamlit/config.toml
set -a; source .env; set +a          # load ui/.env; Streamlit doesn't read it on its own
streamlit run app.py
```

If you skip the `source .env` step, the app silently falls back to `mock` mode.

## Connecting the team's backend (`api` mode)

Set `BACKEND_MODE=api` and `BACKEND_API_URL`. The frontend then sends:

```
POST {BACKEND_API_URL}/tutor/chat
Content-Type: application/json

{"user_id": "ale", "course": "ENGR-E516: Cloud Computing",
 "messages": [{"role": "user", "content": "What is a pod?"}]}
```

and expects a streamed response where:

1. The **first line** is JSON with the sources: `{"sources": [...]}` (use `{"sources": []}` if none)
2. **Every following line** is answer text, displayed as it arrives

If your backend responds differently, adjust the `# REAL BACKEND` section of
`chat_with_tutor()` in `backend.py`. Keep its return value the same, `(sources,
token_stream)`, so `pages/tutor.py` doesn't need to change.

## Troubleshooting

| Symptom | Cause and fix |
|---------|---------------|
| Every answer is the same "Great question about..." text | The app is in `mock` mode. Check `BACKEND_MODE` inside the container (see above), and that you started it with `--env-file ui/.env`. |
| "Can't reach the AI model right now" | Wrong or unreachable `OPENAI_BASE_URL`, or the request took longer than `REQUEST_TIMEOUT_SECONDS`. Test with `curl .../v1/models`. |
| "The AI model is busy or out of quota" | OpenAI account has no credits, or a rate limit was hit. |
| "The AI model rejected our API key" | Wrong or revoked `OPENAI_API_KEY`. |
| "OPENAI_API_KEY is missing" | Set a key, or a placeholder for self-hosted servers. |
| "Connection error" banner at the top of the browser | The browser lost its connection to Streamlit. Check `docker logs minerva-tutor` for restarts or errors. |
| `failed to connect to the docker API` | Docker isn't running. |

## Known limits

- **No guardrails.** There's no system prompt, so the tutor doesn't steer students away
  from asking for graded answers.
- **No course materials.** Answers aren't grounded in uploaded files, and the course
  selection isn't sent to the model in `openai` mode.
- **Placeholder login.** Any username works and there's no password. Restrict port 8501
  in the Jetstream2 Security Group to trusted IPs.
- **Chat history isn't saved.** It lives in the browser session and resets on refresh.
- The course list is hard-coded in `config.COURSES`.