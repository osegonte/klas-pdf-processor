import re
from typing import List, Dict, Optional, Tuple

class ChapterDetector:
    """Pure Python hierarchical chapter detection."""
    
    def __init__(self):
        self.numbering_patterns = [
            r'^(\d+)\.',  # "1."
            r'^(\d+\.\d+)',  # "1.1"
            r'^(\d+\.\d+\.\d+)',  # "1.1.1"
            r'^([A-Z])\.',  # "A."
            r'^([ivxlcdm]+)\.',  # "i.", "ii.", "iii."
        ]
    
    def _clean_title(self, title: str) -> str:
        """Clean and sanitize title."""
        title = title.encode('utf-8', errors='ignore').decode('utf-8', errors='ignore')
        title = ' '.join(title.split())
        title = re.sub(r'^(?:chapter|unit|section|part|module)\s+\d+\s*:?\s*', '', title, flags=re.IGNORECASE)
        
        if len(title) > 100:
            title = title[:97] + "..."
        
        return title.strip()
    
    def _get_level_from_numbering(self, title: str) -> Tuple[int, str]:
        """Detect hierarchy level from numbering (1.1.1 = level 3)."""
        for pattern in self.numbering_patterns:
            match = re.match(pattern, title.strip())
            if match:
                number = match.group(1)
                # Count dots to determine level
                level = number.count('.') + 1
                return level, number
        return 1, None
    
    def detect_from_builtin_toc(self, toc_data: List, total_pages: int) -> Optional[List[Dict]]:
        """Use PDF's built-in ToC with hierarchy."""
        if not toc_data or len(toc_data) == 0:
            return None
        
        boxes = []
        parent_stack = [None]  # Stack to track parents
        
        for item in toc_data:
            level, title, page_num = item[0], item[1], item[2]
            
            if page_num > total_pages or page_num < 1:
                continue
            
            cleaned_title = self._clean_title(title)
            if not cleaned_title:
                continue
            
            # Generate box ID based on position
            box_id = f"box_{len(boxes) + 1}"
            
            # Determine parent based on level
            while len(parent_stack) > level:
                parent_stack.pop()
            
            parent_id = parent_stack[-1] if len(parent_stack) > 1 else None
            
            box = {
                'box_id': box_id,
                'title': cleaned_title,
                'level': level,
                'parent_id': parent_id,
                'start_page': page_num,
                'end_page': None  # Will fill later
            }
            
            boxes.append(box)
            
            # Update parent stack
            if len(parent_stack) <= level:
                parent_stack.extend([None] * (level - len(parent_stack) + 1))
            parent_stack[level] = box_id
        
        # Fill end pages
        for i, box in enumerate(boxes):
            # Find next sibling or parent's next sibling
            next_page = total_pages
            
            for j in range(i + 1, len(boxes)):
                if boxes[j]['level'] <= box['level']:
                    next_page = boxes[j]['start_page'] - 1
                    break
            
            box['end_page'] = next_page
        
        return boxes if len(boxes) >= 2 else None
    
    def detect_from_toc_text(self, toc_text: str, total_pages: int) -> Optional[List[Dict]]:
        """Parse ToC text for hierarchy."""
        if not toc_text:
            return None
        
        boxes = []
        lines = toc_text.split('\n')
        
        for line in lines:
            original_line = line
            line = line.strip()
            
            if not line or len(line) < 5:
                continue
            
            # Find page number
            page_match = re.search(r'\.{2,}\s*(\d+)\s*$', line)
            if not page_match:
                page_match = re.search(r'\s+(\d+)\s*$', line)
            
            if not page_match:
                continue
            
            page_num = int(page_match.group(1))
            if page_num > total_pages or page_num < 1:
                continue
            
            # Extract title
            title = re.sub(r'\.{2,}\s*\d+\s*$', '', line)
            title = re.sub(r'\s+\d+\s*$', '', title)
            
            # Detect level from indentation or numbering
            indent = len(original_line) - len(original_line.lstrip())
            level_from_indent = (indent // 4) + 1  # 4 spaces = 1 level
            
            level_from_number, number = self._get_level_from_numbering(title)
            
            level = max(level_from_indent, level_from_number)
            
            cleaned_title = self._clean_title(title)
            
            if cleaned_title:
                boxes.append({
                    'box_id': f"box_{len(boxes) + 1}",
                    'title': cleaned_title,
                    'level': level,
                    'start_page': page_num,
                    'number': number
                })
        
        # Assign parents and end pages
        if boxes:
            parent_stack = [None]
            
            for box in boxes:
                level = box['level']
                
                while len(parent_stack) > level:
                    parent_stack.pop()
                
                box['parent_id'] = parent_stack[-1] if len(parent_stack) > 1 else None
                
                if len(parent_stack) <= level:
                    parent_stack.extend([None] * (level - len(parent_stack) + 1))
                parent_stack[level] = box['box_id']
            
            # End pages
            for i, box in enumerate(boxes):
                next_page = total_pages
                for j in range(i + 1, len(boxes)):
                    if boxes[j]['level'] <= box['level']:
                        next_page = boxes[j]['start_page'] - 1
                        break
                box['end_page'] = next_page
        
        return boxes if len(boxes) >= 2 else None
    
    def create_fallback_boxes(self, num_pages: int, pages_per_box: int = 15) -> List[Dict]:
        """Flat boxes when nothing else works."""
        boxes = []
        
        for i in range(0, num_pages, pages_per_box):
            start = i + 1
            end = min(i + pages_per_box, num_pages)
            
            boxes.append({
                'box_id': f"box_{len(boxes) + 1}",
                'title': f"Section {len(boxes) + 1} (Pages {start}-{end})",
                'level': 1,
                'parent_id': None,
                'start_page': start,
                'end_page': end
            })
        
        return boxes
    
    def detect(self, extracted_data: Dict) -> List[Dict]:
        """Main detection with hierarchy support."""
        pages = extracted_data['pages']
        total_pages = extracted_data['num_pages']
        builtin_toc = extracted_data.get('builtin_toc')
        
        print("   Trying built-in PDF bookmarks (hierarchical)...")
        boxes = self.detect_from_builtin_toc(builtin_toc, total_pages)
        if boxes:
            print(f"   ✅ Found {len(boxes)} hierarchical boxes from PDF bookmarks")
            return boxes
        
        print("   Trying ToC text parsing (hierarchical)...")
        from src.extractors.pdf_extractor import PDFExtractor
        extractor = PDFExtractor()
        toc_pages = extractor.extract_toc_pages(pages)
        
        if toc_pages:
            for toc_text in toc_pages:
                boxes = self.detect_from_toc_text(toc_text, total_pages)
                if boxes:
                    print(f"   ✅ Found {len(boxes)} hierarchical boxes from ToC")
                    return boxes
        
        print("   ⚠️  No hierarchical structure detected, creating flat boxes")
        return self.create_fallback_boxes(total_pages)
