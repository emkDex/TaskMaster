"""
Generic paginated response schema.
Used by all list endpoints to provide consistent pagination metadata.
"""
from __future__ import annotations

import math
from typing import Generic, TypeVar

from pydantic import BaseModel, computed_field

T = TypeVar("T")


class PaginatedResponse(BaseModel, Generic[T]):
    """
    Generic paginated response wrapper.
    Provides items, total count, current page, page size, and total pages.
    """

    items: list[T]
    total: int
    page: int
    size: int

    @computed_field  # type: ignore[misc]
    @property
    def pages(self) -> int:
        if self.size == 0:
            return 0
        return math.ceil(self.total / self.size)

    model_config = {"from_attributes": True}
