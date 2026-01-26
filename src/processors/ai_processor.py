import json
from typing import List, Dict
from src.ai.deepseek_client import DeepSeekClient
from src.models.contracts import Chapter, Block, TopicDictionary

class AIProcessor:
    def __init__(self):
        self.ai = DeepSeekClient()
    
    def detect_chapters(self, pages: List[Dict], title: str) -> List[Chapter]:
        """Use AI to detect chapter structure."""
        
        sample_text = "\n\n".join([
            f"=== PAGE {p['page_num']} ===\n{p['text']}" 
            for p in pages[:20]
        ])
        
        system_prompt = """You are a document structure analyzer. 
Detect chapters/sections in educational PDFs.
Return ONLY a JSON array of chapters with: order, title, start_page, end_page.
If no clear chapters exist, create pseudo-chapters by page ranges (e.g., "Pages 1-10").
Return valid JSON only, no other text."""

        user_prompt = f"""Document title: {title}
Total pages: {len(pages)}

Analyze this content and detect chapters:

{sample_text[:3000]}

Return JSON array like:
[
  {{"order": 1, "title": "Introduction", "start_page": 1, "end_page": 5}},
  {{"order": 2, "title": "Main Concepts", "start_page": 6, "end_page": 15}}
]"""

        response = self.ai.process_with_schema(system_prompt, user_prompt)
        
        try:
            # Clean response - remove markdown code blocks if present
            clean_response = response.strip()
            if clean_response.startswith("```"):
                lines = clean_response.split("\n")
                clean_response = "\n".join(lines[1:-1])
            
            chapters_data = json.loads(clean_response)
            return [Chapter(**ch) for ch in chapters_data]
        except Exception as e:
            print(f"⚠️  Chapter detection failed: {e}")
            print(f"Response was: {response[:200]}")
            return self._create_fallback_chapters(len(pages))
    
    def _create_fallback_chapters(self, num_pages: int) -> List[Chapter]:
        """Create chapters by page ranges if detection fails."""
        chapters = []
        pages_per_chapter = 10
        
        for i in range(0, num_pages, pages_per_chapter):
            start = i + 1
            end = min(i + pages_per_chapter, num_pages)
            chapters.append(Chapter(
                order=len(chapters) + 1,
                title=f"Pages {start}-{end}",
                start_page=start,
                end_page=end
            ))
        
        return chapters
    
    def create_blocks(self, pages: List[Dict], chapters: List[Chapter]) -> List[Block]:
        """Use AI to split content into blocks and classify them."""
        
        blocks = []
        
        for chapter in chapters:
            chapter_pages = [
                p for p in pages 
                if chapter.start_page <= p['page_num'] <= chapter.end_page
            ]
            
            chapter_text = "\n\n".join([
                f"PAGE {p['page_num']}:\n{p['text']}" 
                for p in chapter_pages
            ])
            
            # Limit text length for API
            if len(chapter_text) > 8000:
                chapter_text = chapter_text[:8000] + "\n... [truncated]"
            
            system_prompt = """You are an educational content analyzer.
Split text into logical learning blocks and classify each.

Block types: explanation, definition, example, procedure, question, summary, formula, misc

Return ONLY valid JSON array of blocks with:
- content (clean text, 100-500 words)
- block_type
- page_start, page_end
- topics (1-3 relevant topics as array)
- keywords (optional array)

No other text, just the JSON array."""

            user_prompt = f"""Chapter: {chapter.title}
Pages: {chapter.start_page}-{chapter.end_page}

Content:
{chapter_text}

Create structured blocks from this content."""

            response = self.ai.process_with_schema(system_prompt, user_prompt)
            
            try:
                # Clean response
                clean_response = response.strip()
                if clean_response.startswith("```"):
                    lines = clean_response.split("\n")
                    clean_response = "\n".join(lines[1:-1])
                
                blocks_data = json.loads(clean_response)
                
                for idx, b in enumerate(blocks_data):
                    blocks.append(Block(
                        chapter_id=chapter.order,
                        order_in_chapter=idx + 1,
                        content=b['content'],
                        block_type=b['block_type'],
                        page_start=b.get('page_start', chapter.start_page),
                        page_end=b.get('page_end', chapter.end_page),
                        topics=b.get('topics', []),
                        keywords=b.get('keywords', [])
                    ))
                    
            except Exception as e:
                print(f"⚠️  Error processing chapter {chapter.order}: {e}")
                print(f"Response was: {response[:200]}")
        
        return blocks
    
    def extract_topic_dictionary(self, blocks: List[Block]) -> TopicDictionary:
        """Extract canonical topic list from all blocks."""
        all_topics = set()
        for block in blocks:
            all_topics.update(block.topics)
        
        return TopicDictionary(canonical_topics=sorted(list(all_topics)))
