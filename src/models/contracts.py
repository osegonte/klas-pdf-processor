from pydantic import BaseModel
from typing import Optional

class Box(BaseModel):
    """Single box in the hierarchical structure."""
    box_id: str
    title: str
    level: int
    parent_id: Optional[str]
    page_start: int
    page_end: int
    page_count: int
    char_count: int
    text: str

class BoxIndex(BaseModel):
    """Metadata-only version for quick lookups."""
    box_id: str
    title: str
    level: int
    parent_id: Optional[str]
    page_start: int
    page_end: int
    page_count: int
    char_count: int
