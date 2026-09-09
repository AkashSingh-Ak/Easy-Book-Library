# app/services/library/library_service.py
import hashlib
import os
import shutil
from sqlalchemy.orm import Session
from app.core.config import settings
from app.models.models import Book, Chapter
from app.services.reader.pdf_reader import PDFReaderService

class LibraryService:
    @staticmethod
    def is_readable_book(file_path: str) -> bool:
        """
        Confirms a file can actually be opened as a book before it is added
        to the library, so a corrupted or mislabeled upload is rejected with
        a clear error instead of sitting in the library as a broken entry.
        """
        try:
            import fitz
            doc = fitz.open(file_path)
            has_pages = doc.page_count > 0
            doc.close()
            return has_pages
        except Exception:
            return False

    @staticmethod
    def calculate_file_hash(file_path: str) -> str:
        """Calculate SHA-256 hash of a file for unique identification."""
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()

    @classmethod
    def import_book(cls, file_name: str, file_path: str, db: Session) -> Book:
        """
        Imports a book by moving it to the storage folder and creating the database record.
        Indexing metadata/cover happens in a background task.
        """
        # Calculate SHA256 hash for unique ID
        book_id = cls.calculate_file_hash(file_path)
        
        # Determine file type
        file_ext = os.path.splitext(file_name)[1].lower().replace(".", "")
        if file_ext not in ["pdf", "epub"]:
            raise ValueError("Unsupported book format. Only PDF and EPUB are supported.")

        # Resolve paths
        dest_filename = f"{book_id}.{file_ext}"
        dest_path = os.path.join(settings.UPLOAD_DIR, dest_filename)

        # Move uploaded file to static storage if not already there
        if os.path.abspath(file_path) != os.path.abspath(dest_path):
            shutil.copy2(file_path, dest_path)

        # Check if book already exists in DB
        db_book = db.query(Book).filter(Book.id == book_id).first()
        if db_book:
            return db_book

        # Create basic record
        file_size = os.path.getsize(dest_path)
        title = os.path.splitext(file_name)[0].replace("_", " ").replace("-", " ")
        
        new_book = Book(
            id=book_id,
            title=title,
            author="Unknown Author",
            file_path=dest_path,
            file_type=file_ext,
            file_size=file_size,
            reading_progress=0.0
        )
        db.add(new_book)
        db.commit()
        db.refresh(new_book)
        
        return new_book

    @classmethod
    def index_book(cls, book_id: str, db: Session):
        """
        Indexes book metadata, extracts cover art, and parses chapters/TOC.
        Intended to run as a background task.
        """
        book = db.query(Book).filter(Book.id == book_id).first()
        if not book:
            return

        file_path = book.file_path
        cover_filename = f"{book_id}.png"
        cover_path = os.path.join(settings.COVER_DIR, cover_filename)
        
        metadata = {}
        toc = []

        try:
            # 1. Parse using PyMuPDF (supports PDF and EPUB formats natively)
            metadata = PDFReaderService.get_metadata(file_path)
            PDFReaderService.extract_cover(file_path, cover_path)
            toc = PDFReaderService.get_toc(file_path)

            # 2. Update book details
            if metadata.get("title"):
                book.title = metadata["title"]
            if metadata.get("author"):
                book.author = metadata["author"]
            if metadata.get("publisher"):
                book.publisher = metadata["publisher"]
            if metadata.get("isbn"):
                book.isbn = metadata["isbn"]
            if metadata.get("total_pages"):
                book.total_pages = metadata["total_pages"]

            # Save cover path reference
            if os.path.exists(cover_path):
                # Save relative path for browser serving
                book.cover_path = f"/static/covers/{cover_filename}"
            else:
                # Use default cover fallback if cover could not be extracted
                book.cover_path = "/static/covers/default_cover.png"

            # 3. Populate Chapters/TOC in DB
            # Remove any stale chapters
            db.query(Chapter).filter(Chapter.book_id == book_id).delete()
            
            for idx, item in enumerate(toc):
                chapter = Chapter(
                    book_id=book_id,
                    title=item["title"],
                    page_number=item["page_number"],
                    index_number=idx + 1
                )
                db.add(chapter)

            db.commit()
        except Exception as e:
            db.rollback()
            print(f"Error indexing book {book_id}: {e}")
