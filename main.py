#!/usr/bin/env python3
import sys
import json
import re
from pathlib import Path
from datetime import datetime
import fitz  # PyMuPDF
from src.extractors.pdf_extractor import PDFExtractor
from src.processors.chapter_detector import ChapterDetector
from src.models.contracts import (
    PDFParserOutput, DocumentMetadata, ContentBox,
    BoxMetadata, ExerciseMetadata
)

class PDFProcessingError(Exception):
    """Custom exception for PDF processing errors."""
    pass

def extract_text_preview(pdf_chunk_path: str, max_chars: int = 500) -> str:
    """Extract first 200-500 chars from PDF chunk for preview."""
    try:
        doc = fitz.open(pdf_chunk_path)
        text = ""
        
        if len(doc) > 0:
            text = doc[0].get_text("text")
            text = ' '.join(text.split())
            if len(text) > max_chars:
                text = text[:max_chars] + "..."
        
        doc.close()
        return text if text else "No preview available"
        
    except Exception as e:
        return f"Preview extraction failed: {str(e)}"

def calculate_metadata(pdf_chunk_path: str) -> BoxMetadata:
    """Calculate metadata from PDF chunk."""
    try:
        doc = fitz.open(pdf_chunk_path)
        
        full_text = ""
        has_images = False
        
        for page in doc:
            full_text += page.get_text("text")
            
            image_list = page.get_images()
            if image_list:
                has_images = True
        
        doc.close()
        
        word_count = len(full_text.split())
        reading_minutes = max(1, word_count // 200)
        
        has_code = bool(re.search(r'(def |class |import |function\s|var\s|const\s)', full_text))
        has_equations = bool(re.search(r'[\+\-\*/=]\s*\d+|\d+\s*[\+\-\*/=]|\\frac|\\sum|\\int', full_text))
        
        return BoxMetadata(
            word_count=word_count,
            estimated_reading_minutes=reading_minutes,
            has_images=has_images,
            has_code=has_code,
            has_equations=has_equations
        )
        
    except Exception as e:
        return BoxMetadata(
            word_count=0,
            estimated_reading_minutes=1,
            has_images=False,
            has_code=False,
            has_equations=False
        )

def detect_exercise(title: str) -> tuple[bool, str, ExerciseMetadata]:
    """Detect if box is an exercise and determine type."""
    title_lower = title.lower()
    
    exercise_keywords = ['exercise', 'problem', 'question', 'quiz', 'test', 'practice']
    is_exercise = any(keyword in title_lower for keyword in exercise_keywords)
    
    if not is_exercise:
        return False, None, None
    
    # Map to valid exercise_type values
    # Valid: 'multiple_choice', 'short_answer', 'coding', 'true_false', 'fill_blank', 'essay', 'problem_solving'
    exercise_type = 'problem_solving'  # Default
    
    if 'quiz' in title_lower or 'test' in title_lower or 'multiple' in title_lower:
        exercise_type = 'multiple_choice'
    elif 'code' in title_lower or 'program' in title_lower:
        exercise_type = 'coding'
    elif 'short' in title_lower or 'brief' in title_lower:
        exercise_type = 'short_answer'
    elif 'essay' in title_lower or 'discuss' in title_lower:
        exercise_type = 'essay'
    elif 'true' in title_lower or 'false' in title_lower:
        exercise_type = 'true_false'
    elif 'fill' in title_lower or 'blank' in title_lower:
        exercise_type = 'fill_blank'
    
    exercise_num_match = re.search(r'(\d+\.?\d*)', title)
    exercise_number = exercise_num_match.group(1) if exercise_num_match else None
    
    metadata = ExerciseMetadata(
        difficulty='medium',
        estimated_minutes=15,
        has_solution=False,
        exercise_number=exercise_number
    )
    
    return True, exercise_type, metadata

def map_box_type(level: int, title: str) -> str:
    """Map hierarchy level and title to box_type."""
    title_lower = title.lower()
    
    # Check for special types first
    if any(word in title_lower for word in ['exercise', 'problem', 'question']):
        return 'exercise'
    if any(word in title_lower for word in ['quiz', 'test', 'assessment']):
        return 'quiz'
    if any(word in title_lower for word in ['summary', 'conclusion', 'recap']):
        return 'summary'
    if any(word in title_lower for word in ['example', 'illustration']):
        return 'example'
    if any(word in title_lower for word in ['definition', 'term']):
        return 'definition'
    if any(word in title_lower for word in ['note', 'remark', 'important']):
        return 'note'
    
    # Default based on level
    if level == 1:
        return 'chapter'
    elif level == 2:
        return 'section'
    elif level == 3:
        return 'subsection'
    else:
        return 'paragraph'

def split_pdf_into_chunks(pdf_path: str, boxes: list, output_dir: Path, total_pages: int) -> list:
    """Split PDF into chunks and save as separate PDF files."""
    chunks_dir = output_dir / "chunks"
    chunks_dir.mkdir(parents=True, exist_ok=True)
    
    source_doc = fitz.open(pdf_path)
    
    for box in boxes:
        # Validate page range
        start = box['page_start']
        end = box['page_end']
        
        # Fix invalid ranges
        if start < 1:
            start = 1
        if end > total_pages:
            end = total_pages
        if start > end:
            # Skip boxes with invalid ranges
            continue
        
        # Create new PDF with just these pages
        chunk_doc = fitz.open()
        
        # Copy pages (0-indexed, so subtract 1)
        pages_copied = 0
        for page_num in range(start - 1, end):
            if 0 <= page_num < len(source_doc):
                chunk_doc.insert_pdf(source_doc, from_page=page_num, to_page=page_num)
                pages_copied += 1
        
        # Only save if we have pages
        if pages_copied == 0:
            chunk_doc.close()
            continue
        
        # Save chunk
        chunk_filename = f"{box['box_id']}.pdf"
        chunk_path = chunks_dir / chunk_filename
        chunk_doc.save(chunk_path)
        chunk_doc.close()
        
        # Update box with chunk info
        box['pdf_chunk_file'] = f"chunks/{chunk_filename}"
        box['chunk_size_mb'] = round(chunk_path.stat().st_size / (1024 * 1024), 2)
        
        # Extract preview
        box['content_preview'] = extract_text_preview(str(chunk_path))
        
        # Calculate metadata
        box['metadata'] = calculate_metadata(str(chunk_path))
        
        # Detect exercises
        is_ex, ex_type, ex_meta = detect_exercise(box['title'])
        box['is_exercise'] = is_ex
        box['exercise_type'] = ex_type
        box['exercise_metadata'] = ex_meta
    
    source_doc.close()
    
    # Filter out boxes that couldn't be created
    valid_boxes = [b for b in boxes if 'pdf_chunk_file' in b]
    skipped = len(boxes) - len(valid_boxes)
    print(f"   ✅ Created {len(valid_boxes)} PDF chunks ({skipped} skipped)")
    
    return valid_boxes

def create_boxes(pdf_path: str, material_id: str = None, output_dir: str = "data/output"):
    """Process PDF and create boxes in Team Sego format."""
    
    print(f"📦 Processing: {pdf_path}")
    
    pdf_file = Path(pdf_path)
    if not pdf_file.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")
    
    if not pdf_file.suffix.lower() == '.pdf':
        raise ValueError(f"Not a PDF file: {pdf_path}")
    
    if not material_id:
        import uuid
        material_id = str(uuid.uuid4())
    
    try:
        # Step 1: Extract PDF structure
        print("1️⃣  Extracting PDF structure...")
        extractor = PDFExtractor()
        extracted = extractor.extract(pdf_path)
        total_pages = extracted['num_pages']
        print(f"   ✅ Extracted {total_pages} pages")
        
        # Step 2: Detect hierarchical structure
        print("2️⃣  Detecting hierarchical structure...")
        detector = ChapterDetector()
        box_metadata = detector.detect(extracted)
        
        if not box_metadata:
            print("   ⚠️  No structure detected, using fallback")
            box_metadata = detector.create_fallback_boxes(total_pages)
        
        # Step 3: Convert to Team Sego format
        print("3️⃣  Converting to Team Sego format...")
        boxes_raw = []
        
        for idx, box_meta in enumerate(box_metadata):
            # Find parent temp_id
            parent_temp_id = None
            if box_meta.get('parent_id'):
                for i, b in enumerate(box_metadata):
                    if b['box_id'] == box_meta['parent_id']:
                        parent_temp_id = f"box-{i + 1}"
                        break
            
            boxes_raw.append({
                'box_id': box_meta['box_id'],
                'temp_id': f"box-{idx + 1}",
                'parent_temp_id': parent_temp_id,
                'title': box_meta['title'],
                'box_type': map_box_type(box_meta['level'], box_meta['title']),
                'order_index': idx,
                'page_start': box_meta['start_page'],
                'page_end': box_meta['end_page'],
            })
        
        print(f"   ✅ Created {len(boxes_raw)} box definitions")
        
        # Step 4: Split PDF into chunks
        print("4️⃣  Splitting PDF into chunks...")
        output_path = Path(output_dir) / pdf_file.stem
        output_path.mkdir(parents=True, exist_ok=True)
        
        boxes_with_chunks = split_pdf_into_chunks(pdf_path, boxes_raw, output_path, total_pages)
        
        # Step 5: Create final output
        print("5️⃣  Generating final output...")
        
        file_size = pdf_file.stat().st_size
        doc_metadata = DocumentMetadata(
            total_pages=total_pages,
            title=pdf_file.stem.replace('_', ' ').title(),
            file_size_bytes=file_size,
            parsing_timestamp=datetime.now().isoformat(),
            parser_version="1.0.0"
        )
        
        content_boxes = []
        for box in boxes_with_chunks:
            content_boxes.append(ContentBox(
                temp_id=box['temp_id'],
                parent_temp_id=box['parent_temp_id'],
                title=box['title'],
                box_type=box['box_type'],
                content_preview=box['content_preview'],
                order_index=box['order_index'],
                page_start=box['page_start'],
                page_end=box['page_end'],
                metadata=box['metadata'],
                is_exercise=box['is_exercise'],
                exercise_type=box['exercise_type'],
                exercise_metadata=box['exercise_metadata'],
                pdf_chunk_file=box['pdf_chunk_file'],
                chunk_size_mb=box['chunk_size_mb']
            ))
        
        output = PDFParserOutput(
            material_id=material_id,
            metadata=doc_metadata,
            boxes=content_boxes
        )
        
        output_json = output_path / "boxes.json"
        with open(output_json, 'w', encoding='utf-8') as f:
            json.dump(output.model_dump(), f, indent=2, ensure_ascii=False)
        
        print(f"\n✅ COMPLETE!")
        print(f"📦 Output directory: {output_path}")
        print(f"📄 Boxes JSON: {output_json}")
        print(f"📁 PDF chunks: {output_path / 'chunks'}")
        
        level_counts = {}
        for box in content_boxes:
            box_type = box.box_type
            level_counts[box_type] = level_counts.get(box_type, 0) + 1
        
        print(f"📊 Box types: {dict(sorted(level_counts.items()))}")
        
        return output_json, output_path / "chunks"
        
    except Exception as e:
        print(f"   ❌ Error: {e}")
        raise PDFProcessingError(f"Failed to process PDF: {e}")

def main():
    """CLI entry point."""
    if len(sys.argv) < 2:
        print("Usage: python main.py <path_to_pdf> [material_id]")
        print("\nExample:")
        print("  python main.py data/input/textbook.pdf")
        print("  python main.py data/input/textbook.pdf abc-123-uuid")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    material_id = sys.argv[2] if len(sys.argv) > 2 else None
    
    try:
        create_boxes(pdf_path, material_id)
        sys.exit(0)
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
