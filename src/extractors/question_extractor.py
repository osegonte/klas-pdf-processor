"""Extracts individual questions from exercise/exam PDFs."""

import re
from typing import List, Dict


class QuestionExtractor:
    """Extracts individual questions from text."""
    
    def extract(self, text: str, page_num: int) -> List[Dict]:
        """Extract questions from text."""
        
        questions = []
        
        # Pattern 1: Numbered questions (1. What is...)
        pattern1 = r'(\d+)\.\s+([^\n]+(?:\n(?!\d+\.)[^\n]+)*)'
        matches1 = re.finditer(pattern1, text)
        
        for match in matches1:
            question_num = match.group(1)
            question_text = match.group(2).strip()
            
            if self._is_question(question_text):
                questions.append({
                    'number': question_num,
                    'text': question_text,
                    'page': page_num,
                    'type': self._detect_question_type(question_text)
                })
        
        # Pattern 2: Question X format
        pattern2 = r'Question\s+(\d+)[:\s]+([^\n]+(?:\n(?!Question\s+\d+)[^\n]+)*)'
        matches2 = re.finditer(pattern2, text, re.IGNORECASE)
        
        for match in matches2:
            question_num = match.group(1)
            question_text = match.group(2).strip()
            
            questions.append({
                'number': question_num,
                'text': question_text,
                'page': page_num,
                'type': self._detect_question_type(question_text)
            })
        
        return questions
    
    def _is_question(self, text: str) -> bool:
        """Check if text looks like a question."""
        text_lower = text.lower()
        
        indicators = [
            '?',
            'what', 'why', 'how', 'when', 'where', 'who', 'which',
            'calculate', 'solve', 'find', 'determine', 'explain',
            'choose', 'select', 'answer'
        ]
        
        return any(indicator in text_lower for indicator in indicators)
    
    def _detect_question_type(self, text: str) -> str:
        """Detect question type."""
        text_lower = text.lower()
        
        if re.search(r'\b[A-D]\)', text):
            return 'multiple_choice'
        
        if 'true' in text_lower and 'false' in text_lower:
            return 'true_false'
        
        if any(word in text_lower for word in ['calculate', 'compute', 'solve']):
            return 'calculation'
        
        if any(word in text_lower for word in ['explain', 'discuss', 'describe', 'essay']):
            return 'essay'
        
        return 'short_answer'
