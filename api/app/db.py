from collections.abc import Iterator
from functools import lru_cache

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import DeclarativeBase, Session

from app.config import get_settings


class Base(DeclarativeBase):
    pass


@lru_cache(maxsize=1)
def _get_engine() -> Engine:
    return create_engine(get_settings().database_url)


def get_session() -> Iterator[Session]:
    with Session(_get_engine()) as session:
        yield session
