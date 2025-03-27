from typing import Annotated, Optional
from sqlalchemy import Boolean
from sqlalchemy.orm import Mapped, mapped_column

from database import Base, str_256

intpk = Annotated[int, mapped_column(primary_key=True)]


class Users(Base):
    """Модель пользователя."""

    __tablename__ = "users"

    id: Mapped[intpk]
    username: Mapped[str_256]
    first_name: Mapped[Optional[str_256]]
    last_name: Mapped[Optional[str_256]]
    subscriber: Mapped[bool] = mapped_column(Boolean, default=False)


class Requests(Base):
    """Модель запроса."""

    __tablename__ = "requests"

    id: Mapped[int] = mapped_column(primary_key=True)
    content: Mapped[str_256]


class PDFfiles(Base):
    """Модель PDF-файла."""

    __tablename__ = "pdf"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str_256]
    file: Mapped[bytes]
    valid: Mapped[bool] = mapped_column(Boolean, default=False)
