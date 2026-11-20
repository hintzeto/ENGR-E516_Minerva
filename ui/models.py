"""
models.py - Database tables, defined as Python classes (SQLAlchemy ORM).

Base.metadata.create_all() in app.py creates any table that doesn't exist yet.
Passwords are never stored: only a salted hash, which check_password() compares against.
"""
from time import time

from sqlalchemy import BigInteger, Integer, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from werkzeug.security import check_password_hash, generate_password_hash


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(256), nullable=False)
    # Unix time. The lambda makes the default evaluate per row, not once at import.
    created_at: Mapped[int] = mapped_column(BigInteger, default=lambda: int(time()), nullable=False)

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    def __repr__(self) -> str:
        return f"<User {self.username}>"
