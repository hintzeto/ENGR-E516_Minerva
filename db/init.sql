-- Runs once, when the database is first created.
-- Enables pgvector so tables can use the vector column type.
-- Tables are created by the application.
CREATE EXTENSION IF NOT EXISTS vector;
