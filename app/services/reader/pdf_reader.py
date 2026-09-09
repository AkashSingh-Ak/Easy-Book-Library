# app/services/reader/pdf_reader.py
import fitz
import nltk
from typing import Dict, List, Any, Tuple

class PDFReaderService:
    @staticmethod
    def get_metadata(file_path: str) -> Dict[str, Any]:
        """Extract metadata from PDF file."""
        doc = fitz.open(file_path)
        metadata = doc.metadata
        total_pages = doc.page_count
        
        # Try to extract title/author from metadata, fallback to filename
        title = metadata.get("title")
        author = metadata.get("author")
        publisher = metadata.get("publisher")
        
        doc.close()
        return {
            "title": title,
            "author": author,
            "publisher": publisher,
            "total_pages": total_pages,
            "isbn": None
        }

    @staticmethod
    def extract_cover(file_path: str, output_cover_path: str) -> bool:
        """Extract first page of PDF as cover image."""
        try:
            doc = fitz.open(file_path)
            if doc.page_count > 0:
                page = doc[0]
                # Render page to a pixmap (image)
                pix = page.get_pixmap(matrix=fitz.Matrix(1.5, 1.5))
                pix.save(output_cover_path)
                doc.close()
                return True
            doc.close()
            return False
        except Exception as e:
            print(f"Error extracting PDF cover: {e}")
            return False

    @staticmethod
    def get_toc(file_path: str) -> List[Dict[str, Any]]:
        """Extract Table of Contents from PDF."""
        try:
            doc = fitz.open(file_path)
            toc = doc.get_toc() # Returns a list of [lvl, title, page]
            doc.close()
            
            formatted_toc = []
            for item in toc:
                formatted_toc.append({
                    "level": item[0],
                    "title": item[1],
                    "page_number": item[2]
                })
            return formatted_toc
        except Exception as e:
            print(f"Error extracting PDF TOC: {e}")
            return []

    @staticmethod
    def render_page(file_path: str, page_number: int) -> Dict[str, Any]:
        """
        Renders a PDF page.
        Returns:
            - svg: The raw SVG string of the page
            - width: Width of the page
            - height: Height of the page
            - words: List of word coordinates for selection overlays
            - sentences: List of sentence texts mapped to word indices for TTS highlighting
        """
        doc = fitz.open(file_path)
        # 0-indexed page lookup (frontend is 1-indexed)
        idx = max(0, min(page_number - 1, doc.page_count - 1))
        page = doc[idx]
        
        # Get page as high-quality PNG image (2x scale for sharpness)
        import base64
        pix = page.get_pixmap(matrix=fitz.Matrix(2.0, 2.0))
        image_bytes = pix.tobytes("png")
        image_base64 = base64.b64encode(image_bytes).decode("utf-8")
        image_url = f"data:image/png;base64,{image_base64}"
        rect = page.rect
        width = rect.width
        height = rect.height
        
        # Get word bounding boxes: (x0, y0, x1, y1, "word", block_no, line_no, word_no)
        raw_words = page.get_text("words")
        words = []
        for i, rw in enumerate(raw_words):
            words.append({
                "text": rw[4],
                "x0": rw[0],
                "y0": rw[1],
                "x1": rw[2],
                "y1": rw[3],
                "block": rw[5],
                "line": rw[6],
                "index": i
            })
            
        # Segment sentences and map words to sentences
        sentences = []
        if words:
            # Reconstruct space-separated text representing reading order
            full_text = " ".join([w["text"] for w in words])
            sentences_text = nltk.sent_tokenize(full_text)
            
            word_cursor = 0
            for sent_text in sentences_text:
                sent_words = sent_text.split()
                sent_indices = []
                
                # Consume words in sequence matching the tokens in the sentence
                for sw in sent_words:
                    if word_cursor < len(words):
                        sent_indices.append(word_cursor)
                        word_cursor += 1
                        
                if sent_indices:
                    sentences.append({
                        "text": sent_text,
                        "word_indices": sent_indices
                    })
        
        doc.close()
        
        return {
            "image_url": image_url,
            "width": width,
            "height": height,
            "words": words,
            "sentences": sentences
        }
