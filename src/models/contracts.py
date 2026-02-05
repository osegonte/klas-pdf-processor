from pydantic import BaseModel, Field
from typing import Optional, List, Literal
from datetime import datetime

class BoxMetadata(BaseModel):
    """Metadata for content analysis."""
    word_count: int
    estimated_reading_minutes: int
    difficulty: Optional[Literal['beginner', 'intermediate', 'advanced']] = None
    has_images: bool = False
    has_code: bool = False
    has_equations: bool = False

class ExerciseMetadata(BaseModel):
    """Metadata for exercises."""
    difficulty: Optional[Literal['easy', 'medium', 'hard']] = None
    estimated_minutes: Optional[int] = None
    has_solution: bool = False
    exercise_number: Optional[str] = None

class ContentBox(BaseModel):
    """Single box in hierarchical structure - matches Team Sego spec."""
    # Identification
    temp_id: str
    parent_temp_id: Optional[str] = None
    
    # Box Details
    title: str
    box_type: Literal[
        'chapter', 'section', 'subsection', 'paragraph',
        'exercise', 'summary', 'example', 'definition',
        'note', 'quiz'
    ]
    content_preview: str  # First 200-500 chars
    
    # Position
    order_index: int
    page_start: int
    page_end: int
    
    # Content Analysis
    metadata: BoxMetadata
    
    # AI-Enhanced (Optional)
    ai_summary: Optional[str] = None
    key_concepts: List[str] = Field(default_factory=list)
    
    # Exercise Detection
    is_exercise: bool = False
    exercise_type: Optional[Literal[
        'multiple_choice', 'short_answer', 'coding',
        'true_false', 'fill_blank', 'essay', 'problem_solving'
    ]] = None
    exercise_metadata: Optional[ExerciseMetadata] = None
    
    # PDF Chunk Reference
    pdf_chunk_file: str  # Relative path to PDF chunk
    chunk_size_mb: float

class DocumentMetadata(BaseModel):
    """Top-level metadata."""
    total_pages: int
    title: str
    author: Optional[str] = None
    created_date: Optional[str] = None
    file_size_bytes: int
    parsing_timestamp: str
    parser_version: str = "1.0.0"

class PDFParserOutput(BaseModel):
    """Complete output matching Team Sego spec."""
    material_id: str  # UUID from KLAS
    metadata: DocumentMetadata
    boxes: List[ContentBox]
