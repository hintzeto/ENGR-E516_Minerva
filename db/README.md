# Database (PostgreSQL + pgvector)


## How it works
1. `docker compose up` starts Postgres, waits until it is healthy, then starts the UI.
2. The UI reads `DATABASE_URI` and connects to the `db` service.
3. On start, `Base.metadata.create_all()` creates any missing tables.
4. **Login:** passwords are never stored, only a salted hash (`generate_password_hash`).
   Login hashes what you typed and compares.
5. **pgvector:** an embedding is a list of numbers that represents the meaning of a text.
   Similar meanings → close vectors. `ORDER BY embedding <=> question LIMIT k` returns the
   k closest chunks. That is the "retrieval" step of RAG.

## Run
```bash
docker compose up -d --build
docker compose exec db psql -U minerva -c "SELECT * FROM users;"
```
App: http://localhost:8501

Reset everything (deletes data): `docker compose down -v`

## Notes
- `EMBEDDING_DIM` in `models.py` (384) must match the embedding model. Changing the model
  means dropping `course_chunks` and re-uploading.
- Dev password `minerva` is in `docker-compose.yml`; change it for any shared deployment.
- With many chunks, add an HNSW index to keep search fast.

## Course material retrieval (the demo)
Open **Course Materials** in the app, upload PDFs, then ask questions.

| Step | Code | What happens |
|------|------|--------------|
| Read | `rag.extract_pages` | pypdf pulls the text of each page (one slide = one chunk) |
| Split | `rag.split_text` | pages longer than 1200 characters are cut into pieces |
| Embed | `rag.embed` | local model `bge-small` turns each chunk into 384 numbers |
| Store | `rag.ingest_pdf` | chunk + file + page + vector go into `course_chunks` |
| Search | `rag.search` | the question is embedded, Postgres returns the nearest chunks |

Below `MIN_SIMILARITY` (config.py) the page answers "no good match" instead of guessing.
Good demo questions: grading (syllabus), containers vs VMs (VirtualMachine.pdf),
the reduce step (map-reduce.pdf), Spark ML libraries (Spark slides), and an off-topic one.
