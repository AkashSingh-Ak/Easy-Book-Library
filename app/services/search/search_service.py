# app/services/search/search_service.py
import fitz
import nltk
from ebooklib import epub
from lxml import html
from typing import List, Dict, Any
from app.schemas.schemas import SearchResultResponse

class SearchService:
    @staticmethod
    def search_in_pdf(file_path: str, query: str) -> List[Dict[str, Any]]:
        """Search query inside PDF file."""
        results = []
        doc = fitz.open(file_path)
        query_lower = query.lower()
        
        # Table of contents for mapping page to chapter titles
        toc = doc.get_toc() # [[lvl, title, page], ...]
        
        def get_chapter_for_page(page_num: int) -> str:
            curr_chapter = "Main Text"
            for item in toc:
                if item[2] <= page_num:
                    curr_chapter = item[1]
                else:
                    break
            return curr_chapter

        for page_idx in range(doc.page_count):
            page = doc[page_idx]
            text = page.get_text("text")
            if query_lower in text.lower():
                sentences = nltk.sent_tokenize(text)
                for sentence in sentences:
                    if query_lower in sentence.lower():
                        # Extract a small context window
                        idx = text.lower().find(sentence.lower())
                        start = max(0, idx - 40)
                        end = min(len(text), idx + len(sentence) + 40)
                        context = text[start:end].replace("\n", " ").strip()
                        
                        results.append({
                            "page_number": page_idx + 1,
                            "chapter_title": get_chapter_for_page(page_idx + 1),
                            "sentence": sentence.strip().replace("\n", " "),
                            "context": f"... {context} ..."
                        })
                        if len(results) >= 50:
                            doc.close()
                            return results
        doc.close()
        return results

    @staticmethod
    def search_in_epub(file_path: str, query: str) -> List[Dict[str, Any]]:
        """Search query inside EPUB file."""
        results = []
        book = epub.read_epub(file_path)
        query_lower = query.lower()
        
        # Load spine chapters
        chapters_items = []
        for item_ref in book.spine:
            item_id = item_ref[0] if isinstance(item_ref, tuple) else item_ref
            item = book.get_item_with_id(item_id)
            if item and item.get_type() == epub.ebooklib.ITEM_DOCUMENT:
                chapters_items.append(item)

        for chapter_idx, item in enumerate(chapters_items):
            try:
                html_content = item.get_content().decode("utf-8", errors="ignore")
                tree = html.fromstring(html_content)
                text = tree.text_content()
                
                if query_lower in text.lower():
                    sentences = nltk.sent_tokenize(text)
                    for sentence in sentences:
                        if query_lower in sentence.lower():
                            idx = text.lower().find(sentence.lower())
                            start = max(0, idx - 40)
                            end = min(len(text), idx + len(sentence) + 40)
                            context = text[start:end].replace("\n", " ").strip()
                            
                            results.append({
                                "page_number": chapter_idx + 1,
                                "chapter_title": item.get_name(),
                                "sentence": sentence.strip().replace("\n", " "),
                                "context": f"... {context} ..."
                            })
                            if len(results) >= 50:
                                return results
            except Exception as e:
                print(f"Error searching EPUB chapter {item.get_name()}: {e}")
                
        return results

    @classmethod
    def search(cls, file_path: str, file_type: str, query: str) -> List[SearchResultResponse]:
        """Dispatches search based on book file type."""
        raw_results = []
        if file_type.lower() == "pdf":
            raw_results = cls.search_in_pdf(file_path, query)
        elif file_type.lower() == "epub":
            raw_results = cls.search_in_epub(file_path, query)
            
        return [SearchResultResponse(**r) for r in raw_results]
