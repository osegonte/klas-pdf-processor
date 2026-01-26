from pydantic import BaseModel, Field
from typing import List, Optional, Literal
from datetime import datetime

class DocumentMetadata(BaseModel):
    title: str
    filename: str
    num_pages: int
    language: str = "en"
    doc_type: Optional[Literal["notes", "textbook", "syllabus", "past_questions"]] = None
    created_at: datetime = Field(default_factory=datetime.now)
    processing_version: str = "1.0.0-ai-heavy"

class Chapter(BaseModel):
    order: int
    title: str
    start_page: int
    end_page: int

class Block(BaseModel):
    chapter_id: int
    order_in_chapter: int
    content: str
    block_type: Literal[
        "explanation", "definition", "example", "procedure", 
        "question", "summary", "formula", "misc"
    ]
    page_start: int
    page_end: int
    topics: List[str] = Field(default_factory=list, max_length=3)
    keywords: List[str] = Field(default_factory=list)

class QualityFlag(BaseModel):
    flag_type: Literal[
        "multi_column_suspected", "table_suspected", 
        "scanned_ocr_needed", "low_confidence_chapters"
    ]
    page: Optional[int] = None
    details: str

class TopicDictionary(BaseModel):
    canonical_topics: List[str]

class ProcessedDocument(BaseModel):
    metadata: DocumentMetadata
    chapters: List[Chapter]
    blocks: List[Block]
    topic_dictionary: TopicDictionary
    quality_flags: List[QualityFlag] = Field(default_factory=list)
