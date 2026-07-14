"""Common Pydantic schemas"""

from pydantic import AliasChoices, BaseModel, Field, model_validator


class PaginationMeta(BaseModel):
    """Pagination metadata"""

    page: int
    page_size: int
    total: int = Field(validation_alias=AliasChoices("total", "total_items"))
    total_items: int | None = None
    total_pages: int
    has_next: bool
    has_prev: bool

    @model_validator(mode="after")
    def sync_total_items(self):
        if self.total_items is None:
            self.total_items = self.total
        return self


class ErrorResponse(BaseModel):
    """Standard error response"""

    error: str
    message: str
    timestamp: str
    details: list[dict] | None = None
