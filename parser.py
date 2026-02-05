#!/usr/bin/env python3
"""
KLAS PDF Parser v3.0 - Efficient Storage
Stores ONE PDF + metadata with page ranges (no chunks)
"""

import sys
import json
import uuid
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Tuple
import fitz

from src.extractors.pdf_extractor import PDFExtractor
from src.extractors.question_extractor import QuestionExtractor
from src.processors.chapter_detector import ChapterDetector
from src.analyzers.content_analyzer import ContentAnalyzer
from src.classifiers.document_classifier import DocumentClassifier
from src.classifiers.scan_detector import ScanDetector


class PDFParser:
    """Efficient PDF parser - no duplicate chunks, just metadata."""
    
    def __init__(self, max_pdf_size_mb: int = 100):
        self.extractor = PDFExtractor(max_size_mb=max_pdf_size_mb)
        self.detector = ChapterDetector()
        self.analyzer = ContentAnalyzer()
        self.classifier = DocumentClassifier()
        self.scan_detector = ScanDetector()
        self.question_extractor = QuestionExtractor()
    
    def parse(self, pdf_path: str, output_dir: str = "output", keep_original: bool = True) -> Dict:
        """Parse PDF efficiently - one file + metadata."""
        
        print(f"\n{'='*60}")
        print(f"KLAS PDF Parser v3.0 - Efficient Storage")
        print(f"{'='*60}")
        print(f"📄 File: {pdf_path}\n")
        
        pdf_file = Path(pdf_path)
        if not pdf_file.exists():
            raise FileNotFoundError(f"PDF not found: {pdf_path}")
        
        # 1. Detect if scanned
        print("1️⃣  Analyzing PDF format...")
        is_scanned, scan_confidence, scan_details = self.scan_detector.detect(pdf_path)
        
        if is_scanned:
            print(f"   ⚠️  SCANNED PDF DETECTED (confidence: {scan_confidence:.0%})")
            print(f"   📊 Average: {scan_details['avg_chars_per_page']} chars/page")
            print(f"   🔧 Recommendation: Apply OCR first for better parsing")
            self._show_ocr_instructions()
        else:
            print(f"   ✅ Text-based PDF (confidence: {scan_confidence:.0%})")
        
        # 2. Extract structure
        print(f"\n2️⃣  Extracting PDF structure...")
        extracted = self.extractor.extract(pdf_path)
        total_pages = extracted['num_pages']
        print(f"   ✅ {total_pages} pages extracted")
        
        # 3. Classify document type
        print(f"\n3️⃣  Classifying document type...")
        doc_type, type_confidence = self.classifier.classify(extracted)
        print(f"   📋 Type: {doc_type.upper()} (confidence: {type_confidence:.0%})")
        
        # 4. Parse based on type
        if doc_type in ['past_questions', 'exercises']:
            return self._parse_questions(pdf_path, extracted, doc_type, is_scanned, 
                                        scan_details, output_dir, keep_original)
        else:
            return self._parse_textbook(pdf_path, extracted, doc_type, is_scanned,
                                       scan_details, output_dir, keep_original)
    
    def _show_ocr_instructions(self):
        """Show OCR recommendations for scanned PDFs."""
        print(f"\n   💡 To extract text from scanned PDFs:")
        print(f"      Option 1 (Python): pip install pytesseract")
        print(f"      Option 2 (Mac): brew install tesseract")
        print(f"      Option 3 (Online): Use Adobe Acrobat OCR")
        print(f"      Then re-run parser on OCR'd PDF")
    
    def _parse_questions(self, pdf_path: str, extracted: Dict, doc_type: str,
                        is_scanned: bool, scan_details: Dict, output_dir: str,
                        keep_original: bool) -> Dict:
        """Parse question/exercise PDFs."""
        
        if is_scanned:
            print(f"\n⚠️  Cannot extract questions from scanned PDF without OCR")
            print(f"   Falling back to page-based chunking...")
        
        print(f"\n4️⃣  Extracting questions...")
        
        all_questions = []
        if not is_scanned:
            for page in extracted['pages']:
                questions = self.question_extractor.extract(page['text'], page['page_num'])
                all_questions.extend(questions)
            
            print(f"   ✅ {len(all_questions)} questions extracted")
            
            if all_questions:
                type_counts = {}
                for q in all_questions:
                    qtype = q['type']
                    type_counts[qtype] = type_counts.get(qtype, 0) + 1
                
                print(f"   📊 Question types:")
                for qtype, count in sorted(type_counts.items()):
                    print(f"      {qtype}: {count}")
        else:
            print(f"   ⚠️  0 questions extracted (scanned PDF)")
        
        # Create output
        pdf_file = Path(pdf_path)
        output_path = Path(output_dir) / pdf_file.stem
        output_path.mkdir(parents=True, exist_ok=True)
        
        # Copy or reference original PDF
        stored_pdf_path = self._handle_pdf_storage(pdf_path, output_path, keep_original)
        
        document = {
            "id": str(uuid.uuid4()),
            "filename": pdf_file.name,
            "title": pdf_file.stem.replace('_', ' ').replace('-', ' ').title(),
            "document_type": doc_type,
            "is_scanned": is_scanned,
            "scan_details": scan_details,
            "pages": extracted['num_pages'],
            "file_size_bytes": pdf_file.stat().st_size,
            "pdf_path": stored_pdf_path,
            "processed_at": datetime.now().isoformat(),
            "parser_version": "3.0.0"
        }
        
        output_data = {
            "document": document,
            "questions": all_questions,
            "stats": {
                "total_questions": len(all_questions),
                "question_types": type_counts if all_questions else {}
            }
        }
        
        # Save
        output_json = output_path / "questions.json"
        with open(output_json, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)
        
        print(f"\n✅ PARSING COMPLETE!")
        print(f"📁 Output: {output_path}")
        print(f"📄 Questions: {output_json.name}")
        print(f"📦 Storage: 1 PDF file (no chunks)")
        print(f"\n{'='*60}\n")
        
        return {
            "document": document,
            "questions": all_questions,
            "output_paths": {
                "directory": str(output_path),
                "json": str(output_json),
                "pdf": stored_pdf_path
            }
        }
    
    def _parse_textbook(self, pdf_path: str, extracted: Dict, doc_type: str,
                       is_scanned: bool, scan_details: Dict, output_dir: str,
                       keep_original: bool) -> Dict:
        """Parse textbook PDFs - metadata only, no chunks."""
        
        print(f"\n4️⃣  Detecting document structure...")
        raw_boxes = self.detector.detect(extracted)
        print(f"   ✅ {len(raw_boxes)} boxes detected")
        
        print(f"\n5️⃣  Analyzing content types...")
        analyzed_boxes = self.analyzer.analyze_boxes(raw_boxes)
        
        type_counts = {}
        for box in analyzed_boxes:
            bt = box.get('block_type', 'unknown')
            type_counts[bt] = type_counts.get(bt, 0) + 1
        
        print(f"   📊 Content breakdown:")
        for btype, count in sorted(type_counts.items()):
            print(f"      {btype}: {count}")
        
        # Create output directory
        pdf_file = Path(pdf_path)
        output_path = Path(output_dir) / pdf_file.stem
        output_path.mkdir(parents=True, exist_ok=True)
        
        # Store PDF reference
        stored_pdf_path = self._handle_pdf_storage(pdf_path, output_path, keep_original)
        
        print(f"\n6️⃣  Creating block metadata (no chunks)...")
        blocks = self._create_block_metadata(stored_pdf_path, analyzed_boxes, extracted['num_pages'])
        print(f"   ✅ {len(blocks)} blocks with page references")
        
        # Calculate storage saved
        pdf_size_mb = pdf_file.stat().st_size / (1024 * 1024)
        saved_space = (len(blocks) - 1) * pdf_size_mb  # Rough estimate
        print(f"   💾 Storage saved: ~{saved_space:.1f}MB (no duplicate chunks!)")
        
        # Generate output
        document = {
            "id": str(uuid.uuid4()),
            "filename": pdf_file.name,
            "title": pdf_file.stem.replace('_', ' ').replace('-', ' ').title(),
            "document_type": doc_type,
            "is_scanned": is_scanned,
            "scan_details": scan_details,
            "pages": extracted['num_pages'],
            "file_size_bytes": pdf_file.stat().st_size,
            "pdf_path": stored_pdf_path,
            "processed_at": datetime.now().isoformat(),
            "parser_version": "3.0.0"
        }
        
        output_data = {
            "document": document,
            "blocks": blocks,
            "stats": {
                "total_blocks": len(blocks),
                "block_types": type_counts,
                "hierarchy_depth": max((b.get('level', 1) for b in blocks), default=1)
            }
        }
        
        # Save files
        output_json = output_path / "parsed.json"
        with open(output_json, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)
        
        blocks_json = output_path / "blocks.json"
        with open(blocks_json, 'w', encoding='utf-8') as f:
            json.dump(blocks, f, indent=2, ensure_ascii=False)
        
        summary = {
            "document_id": document['id'],
            "filename": document['filename'],
            "document_type": doc_type,
            "is_scanned": is_scanned,
            "pages": document['pages'],
            "blocks_created": len(blocks),
            "block_types": type_counts,
            "storage_model": "efficient",
            "pdf_chunks": 0,
            "storage_savings_mb": round(saved_space, 2)
        }
        
        summary_json = output_path / "summary.json"
        with open(summary_json, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)
        
        print(f"\n✅ PARSING COMPLETE!")
        print(f"📁 Output: {output_path}")
        print(f"📄 Files: {output_json.name}, {blocks_json.name}, {summary_json.name}")
        print(f"📦 Storage: 1 PDF + metadata (efficient!)")
        print(f"\n{'='*60}\n")
        
        return {
            "document": document,
            "blocks": blocks,
            "output_paths": {
                "directory": str(output_path),
                "json": str(output_json),
                "blocks": str(blocks_json),
                "summary": str(summary_json),
                "pdf": stored_pdf_path
            }
        }
    
    def _handle_pdf_storage(self, pdf_path: str, output_path: Path, keep_original: bool) -> str:
        """Handle PDF storage - copy or reference."""
        import shutil
        
        pdf_file = Path(pdf_path)
        
        if keep_original:
            # Copy to output directory
            dest_pdf = output_path / pdf_file.name
            shutil.copy2(pdf_path, dest_pdf)
            return str(dest_pdf.relative_to(output_path.parent))
        else:
            # Just reference original
            return str(pdf_file.absolute())
    
    def _create_block_metadata(self, pdf_path: str, boxes: List[Dict], 
                              total_pages: int) -> List[Dict]:
        """Create block metadata with page ranges (no PDF chunks)."""
        
        blocks = []
        
        for box in boxes:
            start = max(1, box['start_page'])
            end = min(total_pages, box['end_page'])
            
            if start > end:
                continue
            
            # Extract preview from original PDF
            preview = self._extract_preview_from_pages(pdf_path, start, end)
            metadata = self._calculate_page_metadata(pdf_path, start, end)
            
            block = {
                "id": box['id'],
                "parent_id": box.get('parent_id'),
                "title": box['title'],
                "block_type": box['block_type'],
                "level": box['level'],
                "order_index": box['order_index'],
                
                # Page references instead of PDF chunks
                "start_page": start,
                "end_page": end,
                "page_count": end - start + 1,
                "pdf_reference": f"{pdf_path}#page={start}",
                
                "content_preview": preview,
                "metadata": metadata
            }
            
            if box.get('is_exercise'):
                block['is_exercise'] = True
                block['exercise_type'] = box.get('exercise_type')
            
            blocks.append(block)
        
        return blocks
    
    def _extract_preview_from_pages(self, pdf_path: str, start_page: int, 
                                    end_page: int, max_chars: int = 400) -> str:
        """Extract preview from page range."""
        try:
            doc = fitz.open(pdf_path)
            text = ""
            
            # Get text from first page of range
            if start_page - 1 < len(doc):
                text = doc[start_page - 1].get_text("text")
                text = ' '.join(text.split())
            
            doc.close()
            return text[:max_chars] + "..." if len(text) > max_chars else text
        except:
            return ""
    
    def _calculate_page_metadata(self, pdf_path: str, start_page: int, end_page: int) -> Dict:
        """Calculate metadata from page range."""
        try:
            doc = fitz.open(pdf_path)
            
            full_text = ""
            has_images = False
            
            for page_num in range(start_page - 1, end_page):
                if page_num < len(doc):
                    page = doc[page_num]
                    full_text += page.get_text("text")
                    if page.get_images():
                        has_images = True
            
            doc.close()
            
            word_count = len(full_text.split())
            
            return {
                "word_count": word_count,
                "estimated_reading_minutes": max(1, word_count // 200),
                "has_images": has_images,
                "page_count": end_page - start_page + 1
            }
        except:
            return {
                "word_count": 0,
                "estimated_reading_minutes": 1,
                "has_images": False,
                "page_count": end_page - start_page + 1
            }


def main():
    if len(sys.argv) < 2:
        print("Usage: python parser.py <pdf_file> [output_dir]")
        print("\nExample:")
        print("  python parser.py textbook.pdf")
        print("  python parser.py textbook.pdf custom_output/")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else "output"
    
    try:
        parser = PDFParser()
        result = parser.parse(pdf_path, output_dir, keep_original=True)
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
