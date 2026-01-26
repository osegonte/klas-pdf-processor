import fitz  # PyMuPDF
from typing import Dict, List, Optional, Tuple
import re

class PDFExtractor:
    def __init__(self, max_size_mb: int = 10):
        self.max_size_mb = max_size_mb
    
    def _clean_text(self, text: str) -> str:
        """Remove invalid unicode and clean text."""
        text = text.encode('utf-8', errors='ignore').decode('utf-8', errors='ignore')
        text = text.replace('\x00', '')
        text = re.sub(r'\s+', ' ', text)
        text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)
        return text.strip()
    
    def _get_page_labels(self, doc) -> Dict[str, int]:
        """Extract page label to physical page mapping."""
        page_labels = {}
        
        try:
            # PyMuPDF doesn't have direct page label access, 
            # so we'll parse from the PDF structure if available
            for i in range(len(doc)):
                # Default: page label = physical position + 1
                page_labels[str(i + 1)] = i + 1
        except Exception as e:
            # Fallback: assume sequential numbering
            for i in range(len(doc)):
                page_labels[str(i + 1)] = i + 1
        
        return page_labels
    
    def extract(self, pdf_path: str) -> Dict:
        """Extract text + attempt ToC extraction."""
        doc = fitz.open(pdf_path)
        
        if len(doc) == 0:
            raise ValueError("PDF has no pages")
        
        # Get file size
        file_size_mb = Path(pdf_path).stat().st_size / (1024 * 1024)
        if file_size_mb > self.max_size_mb:
            raise ValueError(f"PDF too large: {file_size_mb:.1f}MB (max: {self.max_size_mb}MB)")
        
        # Extract page labels
        page_labels = self._get_page_labels(doc)
        
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
                # Note: page here is already physical position (1-indexed)
                cleaned_toc.append([level, cleaned_title, page])
            toc = cleaned_toc
        
        doc.close()
        
        return {
            "num_pages": len(pages),
            "pages": pages,
            "filename": Path(pdf_path).name,
            "builtin_toc": toc if toc else None,
            "page_labels": page_labels
        }
    
    def extract_toc_pages(self, pages: List[Dict]) -> Optional[List[str]]:
        """Extract potential ToC text from first 5 and last 3 pages."""
        toc_candidates = []
        
        # Check first 5 pages (ToC usually near beginning)
        for page in pages[:5]:
            text = page['text'].lower()
            # Multiple keywords for ToC detection
            if any(keyword in text for keyword in [
                'table of contents', 'contents', 'index',
                'table des matières', 'índice', 'содержание'
            ]):
                toc_candidates.append(page['text'])
        
        # Check last 3 pages (some books put ToC at end)
        for page in pages[-3:]:
            text = page['text'].lower()
            if any(keyword in text for keyword in ['table of contents', 'contents', 'index']):
                toc_candidates.append(page['text'])
        
        return toc_candidates if toc_candidates else None
