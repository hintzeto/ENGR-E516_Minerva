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
docker compose exec ui python db_demo.py
docker compose exec db psql -U minerva -c "SELECT * FROM users;"
```
App: http://localhost:8501

Reset everything (deletes data): `docker compose down -v`

## Notes
- `EMBEDDING_DIM` in `models.py` is 3 for the demo. Set it to your embedding model's size
  (e.g. 1536) before storing real embeddings.
- Dev password `minerva` is in `docker-compose.yml`; change it for any shared deployment.
- With many chunks, add an HNSW index to keep search fast.
