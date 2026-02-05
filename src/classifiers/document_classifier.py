"""Classifies PDF document types."""

import re
from typing import Dict, List, Tuple


class DocumentClassifier:
    """Detects document type: textbook, past_questions, exercises, practice."""
    
    def classify(self, extracted_data: Dict) -> Tuple[str, float]:
        """
        Classify document type.
        
        Returns:
            (document_type, confidence_score)
        """
        
        pages = extracted_data['pages']
        filename = extracted_data['filename'].lower()
        
        # Check filename first
        if any(word in filename for word in ['past', 'exam', 'waec', 'neco', 'utme', 'jamb']):
            return 'past_questions', 0.9
        
        if any(word in filename for word in ['exercise', 'practice', 'drill', 'worksheet']):
            return 'exercises', 0.9
        
        # Analyze content
        sample_text = self._get_sample_text(pages, num_pages=10)
        
        # Count question indicators
        question_score = self._count_questions(sample_text)
        exercise_score = self._count_exercises(sample_text)
        chapter_score = self._count_chapters(sample_text)
        
        # Decision logic
        if question_score > 20:
            if 'past' in sample_text.lower() or 'exam' in sample_text.lower():
                return 'past_questions', 0.85
            else:
                return 'exercises', 0.8
        
        elif exercise_score > 5:
            return 'exercises', 0.75
        
        elif chapter_score > 0:
            return 'textbook', 0.8
        
        else:
            return 'textbook', 0.5
    
    def _get_sample_text(self, pages: List[Dict], num_pages: int = 10) -> str:
        """Get sample text from first N pages."""
        sample = []
        for page in pages[:num_pages]:
            sample.append(page['text'])
        return ' '.join(sample).lower()
    
    def _count_questions(self, text: str) -> int:
        """Count question indicators."""
        patterns = [
            r'\b\d+\.\s+[A-Z]',
            r'\bQuestion\s+\d+',
            r'\b[A-D]\)\s',
            r'\bchoose\b',
            r'\bselect\b',
            r'\banswer\b.*question',
        ]
        
        count = 0
        for pattern in patterns:
            count += len(re.findall(pattern, text, re.IGNORECASE))
        
        return count
    
    def _count_exercises(self, text: str) -> int:
        """Count exercise indicators."""
        patterns = [
            r'Exercise\s+\d+',
            r'Practice\s+\d+',
            r'Drill\s+\d+',
            r'Activity\s+\d+',
        ]
        
        count = 0
        for pattern in patterns:
            count += len(re.findall(pattern, text, re.IGNORECASE))
        
        return count
    
    def _count_chapters(self, text: str) -> int:
        """Count chapter indicators."""
        patterns = [
            r'Chapter\s+\d+',
            r'Unit\s+\d+',
            r'Section\s+\d+',
        ]
        
        count = 0
        for pattern in patterns:
            count += len(re.findall(pattern, text, re.IGNORECASE))
        
        return count
