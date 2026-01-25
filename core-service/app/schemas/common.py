"""Common Pydantic schemas"""

from pydantic import BaseModel


class PaginationMeta(BaseModel):
    """Pagination metadata"""

    page: int
    page_size: int
    total_items: int
    total_pages: int
    has_next: bool
    has_prev: bool


class ErrorResponse(BaseModel):
    """Standard error response"""

    error: str
    message: str
    timestamp: str
    details: list[dict] | None = None
