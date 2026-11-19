# Minerva API Stack

```
Internet ──HTTPS──▶ Caddy ──▶ Streamlit UI ──▶ FastAPI + LangGraph ──HTTP──▶ model (vLLM / Gemini)
                     :80/443      ui:8501          api:8000                      │
                                                     └──────────▶ PostgreSQL + pgvector (planned)
```

Only Caddy is public. The UI and API talk over Docker's internal network, and the API is the
only service that calls the model or the database.

## Files

```
docker-compose.yml     # caddy, ui, api
.env                   # DOMAIN for Caddy
caddy/Caddyfile        # domain → ui:8501, automatic HTTPS
api/
  .env                 # model settings (never commit)
  app/main.py          # routes: /health, /tutor/chat, /resources/plan, /feedback, /materials
  app/llm.py           # the model client: HTTP POST to {OPENAI_BASE_URL}/chat/completions
  app/store.py         # course materials (in memory; pgvector replaces this)
  app/agents/          # LangGraph agents: tutor.py (template), planner.py, feedback.py
```

## Configure

```bash
cp .env.example .env              # DOMAIN=http://localhost, or your domain on Jetstream2
cp api/.env.example api/.env      # model settings, below
```

`api/.env` (one `KEY=value` per line, no quotes):

| Model | `OPENAI_BASE_URL` | `OPENAI_API_KEY` | `OPENAI_MODEL` |
|-------|-------------------|------------------|----------------|
| vLLM on Jetstream2 | `http://<inference-vm-private-ip>:8000/v1` | `VLLM_API_KEY` | `Qwen/Qwen3-0.6B` |
| Gemini | `https://generativelanguage.googleapis.com/v1beta/openai/` | Gemini key | id from the models list |

Add `REQUEST_TIMEOUT_SECONDS=300` for the CPU vLLM, and set `REQUEST_TIMEOUT_SECONDS=320` in
`ui/.env` so the API times out first. The UI needs no model settings: compose sets
`BACKEND_MODE=api`.

## Run and test locally

```bash
docker compose up -d --build
docker compose ps                 # caddy, ui, api Up; api (healthy)
docker compose logs -f api        # watch requests arrive
```

Open http://localhost and use each page. Every action should log a request in the API
(e.g. `POST /tutor/chat ... 200`). Check the API directly from inside its container:

```bash
docker compose exec api python -c "import urllib.request; print(urllib.request.urlopen('http://localhost:8000/health').read().decode())"
```

Stop with `docker compose down` (not `down -v`, which deletes Caddy's certificates).

## Deploy and test on Jetstream2

1. **VM:** Ubuntu or Debian instance with Docker installed. Clone the repo.
2. **Domain:** `dig +short <your-domain>` must print the instance's public IP.
3. **Security Group:** allow inbound TCP 80 and 443 (UDP 443 optional). Remove any 8501 rule.
   Caddy needs port 80 to get the HTTPS certificate.
4. **Model access:** on the **inference VM's** Security Group, allow TCP 8000 from this VM's
   private IP only. Test from this VM:
   ```bash
   curl -H "Authorization: Bearer <VLLM_API_KEY>" http://<inference-vm-private-ip>:8000/v1/models
   ```
   The `id` it prints is the value for `OPENAI_MODEL`.
5. **Configure and start:**
   ```bash
   cp .env.example .env && nano .env            # DOMAIN=<your-domain>
   cp api/.env.example api/.env && nano api/.env
   docker compose up -d --build
   docker compose logs -f caddy                 # wait for "certificate obtained successfully"
   ```
6. **Test the model from the API container:**
   ```bash
   docker compose exec api python -c "from app.llm import get_llm; print(get_llm().invoke('Say hi').content)"
   ```
7. Open `https://<your-domain>` and test every page.

**Before sharing the link,** enable the `basic_auth` block in `caddy/Caddyfile`
(`docker compose exec caddy caddy hash-password`), since the app's login is a placeholder.

**For the CPU vLLM** (`VLLM_MAX_MODEL_LEN=2048`), lower `MAX_CONTEXT_CHARS` in
`api/app/config.py` to about `4_000`, or uploaded materials will overflow the model's context.

## Integrating LangGraph agents

Every agent in `app/agents/` has the same three parts. `tutor.py` is the template:

```python
class TutorState(TypedDict):                  # 1. State: data passed between nodes
    user_id: str
    course: str
    messages: Annotated[list[AnyMessage], add_messages]
    context: str
    sources: list[dict]

def retrieve(state): ...                      # 2. Nodes: return only the fields they change
async def generate(state): ...

graph = StateGraph(TutorState)                # 3. Graph: connect the nodes
graph.add_node("retrieve", retrieve)
graph.add_node("generate", generate)
graph.add_edge(START, "retrieve")
graph.add_edge("retrieve", "generate")
graph.add_edge("generate", END)
tutor_graph = graph.compile()
```

**Add a step** (e.g. a fact check that retries the answer):

```python
def fact_check(state): ...                    # return {"verdict": "ok"} or {"verdict": "retry"}

graph.add_node("fact_check", fact_check)
graph.add_edge("generate", "fact_check")      # replaces generate → END
graph.add_conditional_edges("fact_check", lambda s: s["verdict"],
                            {"ok": END, "retry": "generate"})
```

Add `verdict: str` to the State. Only the node named in `answer_node` (in `main.py`) streams to
students, so the fact check's own model calls stay hidden.

**Add an agent:**

1. Copy `planner.py` (one node) or `tutor.py` (several) into `app/agents/`.
2. Edit its State and nodes. Call the model with `await get_llm().ainvoke(messages)`.
3. Add a route in `main.py`: streamed answers use `_stream_graph(graph, inputs, answer_node=...)`;
   single results use `await graph.ainvoke(inputs)`.
4. Add the matching call in `ui/backend.py`.

**Test an agent** without the UI, from `api/` with the venv active and `.env` loaded:

```bash
python -c "from app.agents.tutor import tutor_graph; print(tutor_graph.get_graph().draw_mermaid())"
python -m uvicorn app.main:app --reload --port 8000     # then try routes at /docs
```

## Integrating PostgreSQL + pgvector

The database runs on its own VM; follow `db/postgres-deployment-guide.md` on the
`feature-database` branch to start it (`pgvector/pgvector:pg16`, with `init.sql` enabling the
`vector` extension). Then connect the API:

**1. Network:** on the database VM's Security Group, allow TCP 5432 from this VM's private IP only.

**2. `api/.env`:**

```
DATABASE_URI=postgresql+psycopg://minerva:<password>@<db-vm-private-ip>:5432/minerva
```

**3. `api/requirements.txt`:**

```
sqlalchemy>=2.0
psycopg[binary]>=3.2
pgvector>=0.3
fastembed>=0.4
```

`fastembed` runs a small embedding model (`BAAI/bge-small-en-v1.5`, 384 dimensions) on the CPU,
with no GPU or extra server needed. It downloads the model (about 70 MB) on first use, so the
API container needs outbound internet access.

**4. `api/app/db.py`:** the connection and the chunk table.

```python
import os

from pgvector.sqlalchemy import Vector
from sqlalchemy import Integer, String, Text, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

engine = create_engine(os.environ["DATABASE_URI"], pool_pre_ping=True)
Session = sessionmaker(engine)

class Base(DeclarativeBase):
    pass

class Chunk(Base):
    __tablename__ = "material_chunks"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    material_id: Mapped[str] = mapped_column(String(16), index=True)
    user_id: Mapped[str] = mapped_column(String(100), index=True)
    course: Mapped[str] = mapped_column(String(200), index=True)
    filename: Mapped[str] = mapped_column(String(255))
    page: Mapped[int] = mapped_column(Integer)
    text: Mapped[str] = mapped_column(Text)
    embedding = mapped_column(Vector(384))

Base.metadata.create_all(engine)
```

**5. Rewrite `api/app/store.py`** with the **same function names**, so routes and agents don't change:

| Function | New behavior |
|----------|--------------|
| `add_material` | Extract text per page, split into ~1,000-character chunks, embed them, insert `Chunk` rows |
| `list_materials` | One row per `material_id`: `SELECT DISTINCT` over this user's chunks |
| `delete_material` | `DELETE` this user's chunks with that `material_id` |
| `material_context` | Take the **question**, embed it, return the 5 closest chunks for this user and course |

The search is one query:

```python
from fastembed import TextEmbedding
_embedder = TextEmbedding("BAAI/bge-small-en-v1.5")

def material_context(user_id, course, question, k=5):
    qvec = next(_embedder.embed([question])).tolist()
    with Session() as s:
        rows = s.query(Chunk).filter(Chunk.user_id == user_id, Chunk.course == course) \
                .order_by(Chunk.embedding.cosine_distance(qvec)).limit(k).all()
    context = "\n\n".join(f"### {r.filename} p.{r.page}\n{r.text}" for r in rows)
    sources = [{"file": r.filename, "page": r.page, "snippet": r.text[:150]} for r in rows]
    return context, sources
```

**6. Pass the question in `tutor.py`'s `retrieve` node:**

```python
def retrieve(state):
    question = state["messages"][-1].content
    context, sources = store.material_context(state["user_id"], state["course"], question)
    return {"context": context, "sources": sources}
```

**7. Test:**

```bash
docker compose up -d --build
docker compose exec api python -c "from app.db import engine; print(engine.connect().exec_driver_sql(\"SELECT extversion FROM pg_extension WHERE extname='vector'\").scalar())"
```

It should print the pgvector version. Then upload a file with a made-up fact on the Course
Materials page, ask the Tutor about it, and confirm the answer uses it and Sources lists the page.
Restart the stack: uploads should still be there.

Only 5 chunks reach the model per question, so restore `MAX_CONTEXT_CHARS` and the small vLLM
context window stops being a problem.

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `ui` waits forever on `api` | `docker compose logs api`; the API crashed or failed its health check |
| Answers are the mock text | UI isn't in api mode: `docker compose exec ui env \| grep BACKEND` |
| "Can't reach the AI model" | Wrong `OPENAI_BASE_URL`, blocked port 8000 on the inference VM, or timeout too low |
| "AI model returned an error (400)" with vLLM | Prompt exceeds `VLLM_MAX_MODEL_LEN`; lower `MAX_CONTEXT_CHARS` |
| No HTTPS certificate | Port 80 closed, or DNS doesn't point to the instance |
| `could not connect to server` (database) | Port 5432 blocked, or `DATABASE_URI` has the wrong IP or password |