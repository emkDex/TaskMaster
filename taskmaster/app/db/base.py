"""
SQLAlchemy declarative base and shared metadata.
All models must import and inherit from Base defined here.
"""
from __future__ import annotations

from sqlalchemy.orm import DeclarativeBase, MappedColumn
from sqlalchemy import MetaData

# Naming convention for Alembic autogenerate to produce deterministic constraint names
NAMING_CONVENTION: dict[str, str] = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    """Shared declarative base for all ORM models."""

    metadata = MetaData(naming_convention=NAMING_CONVENTION)
