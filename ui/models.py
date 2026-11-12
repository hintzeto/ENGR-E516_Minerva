from sqlalchemy import BigInteger, Integer, String, Text, ForeignKey
from pgvector.sqlalchemy import Vector
from sqlalchemy.orm import Mapped, mapped_column, relationship, DeclarativeBase
import hashlib
from werkzeug.security import check_password_hash, generate_password_hash
from time import time


class Base(DeclarativeBase):
	pass


class User(Base):
	__tablename__ = "users"

	id: Mapped[int] = mapped_column(Integer, primary_key=True)
	username: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
	password_hash: Mapped[str] = mapped_column(String(256), nullable=False)
	created_at: Mapped[int] = mapped_column(BigInteger, default=lambda: int(time()), nullable=False)


	def set_password(self, password):
		self.password_hash = generate_password_hash(password)


	def check_password(self, password):
		return check_password_hash(self.password_hash, password)


	def __repr__(self):
		return f"<User {self.username}>"


# Number of numbers in each embedding. It MUST match the embedding model
# (BAAI/bge-small-en-v1.5 produces 384).
EMBEDDING_DIM = 384


class CourseChunk(Base):
	"""A piece of course material plus its embedding, for similarity search."""
	__tablename__ = "course_chunks"

	id: Mapped[int] = mapped_column(Integer, primary_key=True)
	user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
	course: Mapped[str] = mapped_column(String(100), nullable=False)
	filename: Mapped[str] = mapped_column(String(255), nullable=False)
	page: Mapped[int] = mapped_column(Integer, nullable=False)
	content: Mapped[str] = mapped_column(Text, nullable=False)
	embedding: Mapped[list[float]] = mapped_column(Vector(EMBEDDING_DIM), nullable=False)
