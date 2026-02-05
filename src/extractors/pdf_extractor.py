import fitz  # PyMuPDF
from typing import Dict, List, Optional
from pathlib import Path
import re

class PDFExtractor:
    def __init__(self, max_size_mb: int = 100):  # Increased to 100MB
        self.max_size_mb = max_size_mb
    
    def _clean_text(self, text: str) -> str:
        """Remove invalid unicode and clean text."""
        text = text.encode('utf-8', errors='ignore').decode('utf-8', errors='ignore')
        text = text.replace('\x00', '')
        text = re.sub(r'\s+', ' ', text)
        text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)
        return text.strip()
    
    def extract(self, pdf_path: str) -> Dict:
        """Extract text + attempt ToC extraction."""
        doc = fitz.open(pdf_path)
        
        if len(doc) == 0:
            raise ValueError("PDF has no pages")
        
        # Get file size
        file_size_mb = Path(pdf_path).stat().st_size / (1024 * 1024)
        if file_size_mb > self.max_size_mb:
            raise ValueError(f"PDF too large: {file_size_mb:.1f}MB (max: {self.max_size_mb}MB)")
        
        # Extract all pages
        pages = []
        for page_num in range(len(doc)):
            page = doc[page_num]
            raw_text = page.get_text("text")
            clean_text = self._clean_text(raw_text)
            
            try:
                blocks = page.get_text("dict")["blocks"]
            except:
                blocks = []
            
            pages.append({
                "page_num": page_num + 1,  # Physical position
                "text": clean_text,
                "blocks": blocks,
                "char_count": len(clean_text)
            })
        
        # Try to extract built-in ToC
        toc = doc.get_toc()
        
        # Clean ToC titles if present
        if toc:
            cleaned_toc = []
            for item in toc:
                level, title, page = item
                cleaned_title = self._clean_text(title)
                cleaned_toc.append([level, cleaned_title, page])
            toc = cleaned_toc
        
        doc.close()
        
        return {
            "num_pages": len(pages),
            "pages": pages,
            "filename": Path(pdf_path).name,
            "builtin_toc": toc if toc else None
        }
    
    def extract_toc_pages(self, pages: List[Dict]) -> Optional[List[str]]:
        """Extract potential ToC text from first 5 and last 3 pages."""
        toc_candidates = []
        
        # Check first 5 pages
        for page in pages[:5]:
            text = page['text'].lower()
            if any(keyword in text for keyword in [
                'table of contents', 'contents', 'index',
                'table des matières', 'índice', 'содержание'
            ]):
                toc_candidates.append(page['text'])
        
        # Check last 3 pages
        for page in pages[-3:]:
            text = page['text'].lower()
            if any(keyword in text for keyword in ['table of contents', 'contents', 'index']):
                toc_candidates.append(page['text'])
        
        return toc_candidates if toc_candidates else None
