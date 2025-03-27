from typing import Annotated
from sqlalchemy import create_engine, String
from sqlalchemy.orm import DeclarativeBase

import config

# Подключение к базе данных
engine = create_engine(
    url=config.DATABASE_URL,
    echo=True,
)

str_256 = Annotated[str, 256]


class Base(DeclarativeBase):
    """Базовая модель."""

    type_annotation_map = {
        str_256: String(256)
    }
