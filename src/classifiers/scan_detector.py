"""Detects if PDF is scanned (image-based) or text-based."""

import fitz
from typing import Dict, Tuple


class ScanDetector:
    """Detects if PDF contains scanned images vs extractable text."""
    
    def detect(self, pdf_path: str) -> Tuple[bool, float, Dict]:
        """
        Detect if PDF is scanned.
        
        Returns:
            (is_scanned, confidence, details)
        """
        
        doc = fitz.open(pdf_path)
        
        total_pages = len(doc)
        sample_size = min(10, total_pages)
        
        text_pages = 0
        image_pages = 0
        text_chars = 0
        image_count = 0
        
        for page_num in range(sample_size):
            page = doc[page_num]
            
            text = page.get_text("text")
            char_count = len(text.strip())
            
            images = page.get_images()
            
            if char_count > 100:
                text_pages += 1
                text_chars += char_count
            
            if len(images) > 0:
                image_pages += 1
                image_count += len(images)
        
        doc.close()
        
        avg_chars_per_page = text_chars / sample_size if sample_size > 0 else 0
        
        is_scanned = False
        confidence = 0.0
        
        if avg_chars_per_page < 50:
            is_scanned = True
            confidence = 0.9
        elif image_pages > sample_size * 0.8 and avg_chars_per_page < 200:
            is_scanned = True
            confidence = 0.7
        else:
            is_scanned = False
            confidence = 0.8
        
        details = {
            "sample_pages": sample_size,
            "text_pages": text_pages,
            "image_pages": image_pages,
            "avg_chars_per_page": int(avg_chars_per_page),
            "total_images": image_count,
            "needs_ocr": is_scanned
        }
        
        return is_scanned, confidence, details
