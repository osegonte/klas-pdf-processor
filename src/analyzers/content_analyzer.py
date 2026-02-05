"""Content type analyzer for PDF blocks."""

import re
import uuid
from typing import List, Dict


class ContentAnalyzer:
    """Analyzes and classifies PDF blocks."""
    
    def analyze_boxes(self, raw_boxes: List[Dict]) -> List[Dict]:
        """Analyze and enhance boxes with content types."""
        
        analyzed = []
        
        for idx, box in enumerate(raw_boxes):
            # Generate UUID
            box_id = str(uuid.uuid4())
            
            # Find parent
            parent_id = None
            if box.get('parent_id'):
                for prev_box in analyzed:
                    if prev_box.get('original_box_id') == box['parent_id']:
                        parent_id = prev_box['id']
                        break
            
            # Classify content type
            block_type = self._classify_type(box['title'], box['level'])
            
            # Detect exercises
            is_exercise, exercise_type = self._detect_exercise(box['title'])
            
            analyzed_box = {
                'id': box_id,
                'original_box_id': box['box_id'],
                'parent_id': parent_id,
                'title': box['title'],
                'block_type': block_type,
                'level': box['level'],
                'order_index': idx,
                'start_page': box['start_page'],
                'end_page': box['end_page']
            }
            
            if is_exercise:
                analyzed_box['is_exercise'] = True
                analyzed_box['exercise_type'] = exercise_type
            
            analyzed.append(analyzed_box)
        
        for box in analyzed:
            box.pop('original_box_id', None)
        
        return analyzed
    
    def _classify_type(self, title: str, level: int) -> str:
        """Classify block type based on title and level."""
        title_lower = title.lower()
        
        if any(word in title_lower for word in ['exercise', 'problem', 'practice']):
            return 'exercise'
        if any(word in title_lower for word in ['question', 'quiz', 'test', 'assessment']):
            return 'quiz'
        if any(word in title_lower for word in ['summary', 'conclusion', 'recap', 'review']):
            return 'summary'
        if any(word in title_lower for word in ['example', 'case study', 'illustration']):
            return 'example'
        if any(word in title_lower for word in ['definition', 'glossary', 'term', 'concept']):
            return 'definition'
        if any(word in title_lower for word in ['note', 'remark', 'important', 'remember']):
            return 'note'
        
        if level == 1:
            return 'chapter'
        elif level == 2:
            return 'section'
        elif level == 3:
            return 'subsection'
        else:
            return 'paragraph'
    
    def _detect_exercise(self, title: str) -> tuple:
        """Detect if block is an exercise and classify type."""
        title_lower = title.lower()
        
        exercise_keywords = ['exercise', 'problem', 'question', 'quiz', 'test', 'practice', 'activity']
        is_exercise = any(keyword in title_lower for keyword in exercise_keywords)
        
        if not is_exercise:
            return False, None
        
        if 'multiple choice' in title_lower or 'mcq' in title_lower:
            return True, 'multiple_choice'
        elif 'true' in title_lower or 'false' in title_lower:
            return True, 'true_false'
        elif 'short answer' in title_lower or 'brief' in title_lower:
            return True, 'short_answer'
        elif 'essay' in title_lower or 'discuss' in title_lower:
            return True, 'essay'
        elif 'fill' in title_lower or 'blank' in title_lower:
            return True, 'fill_blank'
        elif 'code' in title_lower or 'program' in title_lower:
            return True, 'coding'
        else:
            return True, 'problem_solving'
