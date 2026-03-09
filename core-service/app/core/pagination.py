"""Pagination utility for list endpoints"""

from math import ceil
from typing import Any, TypeVar

from pydantic import BaseModel, Field
from sqlalchemy.orm import Query

from app.schemas.common import PaginationMeta

T = TypeVar("T")


class PaginationParams(BaseModel):
    """Pagination and sorting parameters"""

    page: int = Field(default=1, ge=1, description="Page number (1-indexed)")
    page_size: int = Field(
        default=20, ge=1, le=100, description="Number of items per page"
    )
    sort_by: str | None = Field(default=None, description="Field name to sort by")
    sort_order: str = Field(
        default="desc",
        pattern="^(asc|desc)$",
        description="Sort order: asc or desc",
    )


class PaginatedResponse(BaseModel):
    """Generic paginated response"""

    items: list[Any]
    pagination: PaginationMeta


def apply_pagination(
    query: Query,
    model_class: type,
    page: int = 1,
    page_size: int = 20,
    sort_by: str | None = None,
    sort_order: str = "desc",
) -> tuple[list[Any], int]:
    """
    Apply pagination and sorting to a SQLAlchemy query.

    Args:
        query: SQLAlchemy query object
        model_class: SQLAlchemy model class for sorting
        page: Page number (1-indexed)
        page_size: Number of items per page
        sort_by: Field name to sort by (defaults to created_at)
        sort_order: Sort order ('asc' or 'desc')

    Returns:
        Tuple of (items, total_count)
    """
    # Get total count before pagination
    total = query.count()

    # Apply sorting
    if sort_by:
        # Get the column from the model
        col = getattr(model_class, sort_by, None)
        if col is not None:
            query = query.order_by(col.desc() if sort_order == "desc" else col.asc())
        else:
            # Fallback to created_at if sort_by field doesn't exist
            default_col = getattr(model_class, "created_at", None)
            if default_col is not None:
                query = query.order_by(
                    default_col.desc() if sort_order == "desc" else default_col.asc()
                )
    else:
        # Default to created_at
        default_col = getattr(model_class, "created_at", None)
        if default_col is not None:
            query = query.order_by(
                default_col.desc() if sort_order == "desc" else default_col.asc()
            )

    # Apply pagination
    offset = (page - 1) * page_size
    items = query.offset(offset).limit(page_size).all()

    return items, total


def create_pagination_meta(
    page: int, page_size: int, total_count: int
) -> PaginationMeta:
    """
    Create pagination metadata.

    Args:
        page: Current page number (1-indexed)
        page_size: Number of items per page
        total_count: Total number of items

    Returns:
        PaginationMeta object with pagination metadata
    """
    total_pages = ceil(total_count / page_size) if page_size > 0 else 0
    has_next = page < total_pages
    has_prev = page > 1

    return PaginationMeta(
        page=page,
        page_size=page_size,
        total_items=total_count,
        total_pages=total_pages,
        has_next=has_next,
        has_prev=has_prev,
    )
