from sqlalchemy import BigInteger, Integer, String, ForeignKey
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
	created_at: Mapped[int] = mapped_column(BigInteger, default=time(), nullable=False)


	def set_password(self, password):
		self.password_hash = generate_password_hash(password)


	def check_password(self, password):
		return check_password_hash(self.password_hash, password)


	def __repr__(self):
		return f"<User {self.username}>"
