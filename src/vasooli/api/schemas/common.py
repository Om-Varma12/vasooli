from pydantic import BaseModel, ConfigDict
from typing import Optional, Generic, TypeVar, List
from datetime import datetime

T = TypeVar("T")

class PaginatedResponse(BaseModel, Generic[T]):
    items: List[T]
    next_cursor: Optional[str] = None
    total_count: int

    model_config = ConfigDict(from_attributes=True)

class CommonSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)
