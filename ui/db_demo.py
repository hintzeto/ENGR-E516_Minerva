"""
db_demo.py - Tiny demo of pgvector similarity search.

Run it (with the stack up):   docker compose exec ui python db_demo.py

Real embeddings come from an embedding model and have hundreds of numbers.
Here we use 3 made-up numbers so you can see the idea: texts with SIMILAR
meaning get vectors that point in a similar direction, and the database can
find the closest ones to a question.
"""
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

import config
from models import Base, CourseChunk, User

engine = create_engine(config.DATABASE_URI)
Base.metadata.create_all(engine)

with Session(engine) as session:
    # Demo rows need an owner, so make a throwaway user if it isn't there yet.
    user = session.scalars(select(User).where(User.username == "demo")).first()
    if not user:
        user = User(username="demo")
        user.set_password("demo-password")
        session.add(user)
        session.commit()

    # Start clean so re-running the demo doesn't pile up duplicates.
    session.query(CourseChunk).filter_by(user_id=user.id).delete()

    chunks = [
        ("A pod is the smallest deployable unit in Kubernetes.", [0.9, 0.1, 0.0]),
        ("Docker images are built from a Dockerfile.",            [0.7, 0.3, 0.1]),
        ("Gradient descent minimizes a loss function.",           [0.0, 0.2, 0.9]),
    ]
    for text, vec in chunks:
        session.add(CourseChunk(user_id=user.id, course="demo", content=text, embedding=vec))
    session.commit()

    # Pretend this is the embedded question "What is a pod?"
    question_vec = [0.85, 0.15, 0.05]

    # cosine_distance -> SQL "ORDER BY embedding <=> question". Smaller = more similar.
    nearest = session.scalars(
        select(CourseChunk)
        .order_by(CourseChunk.embedding.cosine_distance(question_vec))
        .limit(2)
    ).all()

    print("Closest chunks to the question:")
    for c in nearest:
        print(" -", c.content)
