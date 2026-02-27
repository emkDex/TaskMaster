"""
Generic async CRUD base class.
All domain-specific CRUD classes extend CRUDBase and inherit these methods.
"""
from __future__ import annotations

import uuid
from typing import Any, Generic, TypeVar

from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import Base

ModelType = TypeVar("ModelType", bound=Base)
CreateSchemaType = TypeVar("CreateSchemaType", bound=BaseModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=BaseModel)


class CRUDBase(Generic[ModelType, CreateSchemaType, UpdateSchemaType]):
    """
    Generic CRUD operations for SQLAlchemy async ORM models.

    Type parameters:
        ModelType: The SQLAlchemy ORM model class.
        CreateSchemaType: The Pydantic schema used for creation.
        UpdateSchemaType: The Pydantic schema used for updates.
    """

    def __init__(self, model: type[ModelType]) -> None:
        self.model = model

    async def get(self, db: AsyncSession, id: uuid.UUID) -> ModelType | None:
        """Fetch a single record by primary key."""
        result = await db.execute(select(self.model).where(self.model.id == id))  # type: ignore[attr-defined]
        return result.scalar_one_or_none()

    async def get_multi(
        self,
        db: AsyncSession,
        *,
        skip: int = 0,
        limit: int = 100,
    ) -> list[ModelType]:
        """Fetch multiple records with offset pagination."""
        result = await db.execute(select(self.model).offset(skip).limit(limit))
        return list(result.scalars().all())

    async def get_count(self, db: AsyncSession) -> int:
        """Return total count of records in the table."""
        result = await db.execute(select(func.count()).select_from(self.model))
        return result.scalar_one()

    async def create(self, db: AsyncSession, *, obj_in: CreateSchemaType) -> ModelType:
        """Create a new record from a Pydantic schema."""
        obj_data = obj_in.model_dump(exclude_unset=False)
        db_obj = self.model(**obj_data)
        db.add(db_obj)
        await db.flush()
        await db.refresh(db_obj)
        return db_obj

    async def create_from_dict(
        self, db: AsyncSession, *, obj_in: dict[str, Any]
    ) -> ModelType:
        """Create a new record from a plain dictionary."""
        db_obj = self.model(**obj_in)
        db.add(db_obj)
        await db.flush()
        await db.refresh(db_obj)
        return db_obj

    async def update(
        self,
        db: AsyncSession,
        *,
        db_obj: ModelType,
        obj_in: UpdateSchemaType | dict[str, Any],
    ) -> ModelType:
        """
        Update an existing record.
        Accepts either a Pydantic schema or a plain dict.
        Only fields explicitly set in the schema are updated.
        """
        if isinstance(obj_in, dict):
            update_data = obj_in
        else:
            update_data = obj_in.model_dump(exclude_unset=True)

        for field, value in update_data.items():
            setattr(db_obj, field, value)

        db.add(db_obj)
        await db.flush()
        await db.refresh(db_obj)
        return db_obj

    async def remove(self, db: AsyncSession, *, id: uuid.UUID) -> ModelType | None:
        """Delete a record by primary key. Returns the deleted object or None."""
        db_obj = await self.get(db, id)
        if db_obj is None:
            return None
        await db.delete(db_obj)
        await db.flush()
        return db_obj

    async def exists(self, db: AsyncSession, **filters: Any) -> bool:
        """Return True if any record matches the given keyword filters."""
        query = select(func.count()).select_from(self.model)
        for attr, value in filters.items():
            query = query.where(getattr(self.model, attr) == value)
        result = await db.execute(query)
        return (result.scalar_one() or 0) > 0
