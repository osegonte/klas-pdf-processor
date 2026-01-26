#!/usr/bin/env python3
import sys
import json
from pathlib import Path
from src.extractors.pdf_extractor import PDFExtractor
from src.processors.chapter_detector import ChapterDetector

def create_boxes(pdf_path: str, output_dir: str = "data/output"):
    """Extract hierarchical boxes from PDF."""
    
    print(f"📦 Processing: {pdf_path}")
    
    # Step 1: Extract PDF content
    print("1️⃣  Extracting PDF content...")
    extractor = PDFExtractor()
    extracted = extractor.extract(pdf_path)
    print(f"   ✅ Extracted {extracted['num_pages']} pages")
    
    # Step 2: Detect hierarchical structure
    print("2️⃣  Detecting hierarchical structure...")
    detector = ChapterDetector()
    box_metadata = detector.detect(extracted)
    
    # Step 3: Create boxes with text
    print("3️⃣  Creating boxes with content...")
    boxes = []
    
    for box_meta in box_metadata:
        # Get text for this box
        box_pages = [
            p for p in extracted['pages']
            if box_meta['start_page'] <= p['page_num'] <= box_meta['end_page']
        ]
        
        box_text = "\n\n".join([
            f"=== PAGE {p['page_num']} ===\n{p['text']}"
            for p in box_pages
        ])
        
        box = {
            "box_id": box_meta['box_id'],
            "title": box_meta['title'],
            "level": box_meta['level'],
            "parent_id": box_meta.get('parent_id'),
            "page_start": box_meta['start_page'],
            "page_end": box_meta['end_page'],
            "page_count": len(box_pages),
            "text": box_text,
            "char_count": len(box_text)
        }
        
        boxes.append(box)
    
    print(f"   ✅ Created {len(boxes)} boxes")
    
    # Count levels
    level_counts = {}
    for box in boxes:
        level_counts[box['level']] = level_counts.get(box['level'], 0) + 1
    
    print(f"   📊 Hierarchy: {dict(sorted(level_counts.items()))}")
    
    # Step 4: Save outputs
    filename = Path(pdf_path).name
    
    # Full output
    output = {
        "pdf_filename": filename,
        "total_pages": extracted['num_pages'],
        "total_boxes": len(boxes),
        "hierarchy_levels": max(box['level'] for box in boxes),
        "boxes": boxes
    }
    
    output_path = Path(output_dir) / f"{filename.replace('.pdf', '')}_boxes.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    
    # Index (metadata only)
    index = {
        "pdf_filename": filename,
        "total_pages": extracted['num_pages'],
        "total_boxes": len(boxes),
        "hierarchy_levels": max(box['level'] for box in boxes),
        "box_index": [
            {
                "box_id": b['box_id'],
                "title": b['title'],
                "level": b['level'],
                "parent_id": b['parent_id'],
                "page_start": b['page_start'],
                "page_end": b['page_end'],
                "page_count": b['page_count'],
                "char_count": b['char_count']
            }
            for b in boxes
        ]
    }
    
    index_path = Path(output_dir) / f"{filename.replace('.pdf', '')}_index.json"
    with open(index_path, 'w', encoding='utf-8') as f:
        json.dump(index, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ COMPLETE!")
    print(f"📦 Full boxes: {output_path}")
    print(f"📇 Index: {index_path}")
    
    return output_path, index_path

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python main.py <path_to_pdf>")
        sys.exit(1)
    
    create_boxes(sys.argv[1])
