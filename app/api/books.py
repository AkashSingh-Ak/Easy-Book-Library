# app/api/books.py
import os
import shutil
import uuid
from fastapi import APIRouter, Depends, UploadFile, File, BackgroundTasks, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime

from app.core.config import settings
from app.database.session import get_db
from app.models.models import Book, Chapter
from app.schemas.schemas import BookResponse, ChapterResponse
from app.services.library.library_service import LibraryService
from app.services.reader.pdf_reader import PDFReaderService

router = APIRouter(prefix="/books", tags=["books"])

@router.post("/upload", response_model=BookResponse)
def upload_book(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """Uploads a PDF or EPUB book and queues background indexing."""
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in [".pdf", ".epub"]:
        raise HTTPException(status_code=400, detail="Only PDF and EPUB files are supported.")

    # Stage the upload under a random name (never trust the client-supplied
    # filename directly in a filesystem path) so it can be inspected before
    # it is accepted into the permanent library storage.
    temp_dir = os.path.join(settings.BASE_DIR, "app", "static", "temp")
    os.makedirs(temp_dir, exist_ok=True)
    temp_file_path = os.path.join(temp_dir, f"{uuid.uuid4().hex}{ext}")

    try:
        with open(temp_file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        if not LibraryService.is_readable_book(temp_file_path):
            raise HTTPException(status_code=400, detail="This file could not be opened. It may be corrupted or not a valid PDF/EPUB.")

        book = LibraryService.import_book(file.filename, temp_file_path, db)
        background_tasks.add_task(LibraryService.index_book, book.id, db)
        return book
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to upload book: {str(e)}")
    finally:
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)


@router.get("", response_model=List[BookResponse])
def list_books(
    search: Optional[str] = Query(None, description="Search by title, author, or filename"),
    filter_type: Optional[str] = Query(None, description="Filter by file type: pdf, epub"),
    filter_status: Optional[str] = Query(None, description="Filter by progress status: unread, in_progress, finished"),
    sort_by: str = Query("added_date_desc", description="Sorting: added_date_desc, added_date_asc, title_asc, title_desc, author_asc, progress_desc, last_opened_desc"),
    db: Session = Depends(get_db)
):
    """Retrieve book collection with search, filters, and sort configurations."""
    query = db.query(Book)

    # 1. Searching
    if search:
        search_val = f"%{search}%"
        query = query.filter(
            Book.title.like(search_val) | 
            Book.author.like(search_val) | 
            Book.file_path.like(search_val)
        )

    # 2. Filtering
    if filter_type:
        query = query.filter(Book.file_type == filter_type.lower())

    if filter_status:
        if filter_status == "unread":
            query = query.filter(Book.reading_progress == 0.0)
        elif filter_status == "in_progress":
            query = query.filter((Book.reading_progress > 0.0) & (Book.reading_progress < 100.0))
        elif filter_status == "finished":
            query = query.filter(Book.reading_progress >= 100.0)

    # 3. Sorting
    if sort_by == "added_date_desc":
        query = query.order_by(Book.added_date.desc())
    elif sort_by == "added_date_asc":
        query = query.order_by(Book.added_date.asc())
    elif sort_by == "title_asc":
        query = query.order_by(Book.title.asc())
    elif sort_by == "title_desc":
        query = query.order_by(Book.title.desc())
    elif sort_by == "author_asc":
        query = query.order_by(Book.author.asc())
    elif sort_by == "progress_desc":
        query = query.order_by(Book.reading_progress.desc())
    elif sort_by == "last_opened_desc":
        query = query.order_by(Book.last_opened.desc())

    return query.all()


@router.get("/{book_id}", response_model=BookResponse)
def get_book(book_id: str, db: Session = Depends(get_db)):
    """Retrieve detailed book record."""
    book = db.query(Book).filter(Book.id == book_id).first()
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    return book


@router.delete("/{book_id}")
def delete_book(book_id: str, db: Session = Depends(get_db)):
    """Delete a book, its files, and all associated tables (cascade)."""
    book = db.query(Book).filter(Book.id == book_id).first()
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")

    try:
        # Delete files from disk
        if os.path.exists(book.file_path):
            os.remove(book.file_path)
            
        # Delete cover
        if book.cover_path and "default_cover" not in book.cover_path:
            cover_path = os.path.join(settings.BASE_DIR, "app", book.cover_path.lstrip("/"))
            if os.path.exists(cover_path):
                os.remove(cover_path)
                
        # Delete from DB (chapters, bookmarks, highlights, reading_sessions cascade automatically)
        db.delete(book)
        db.commit()
        return {"success": True, "message": "Book deleted successfully"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to delete book: {str(e)}")


@router.get("/{book_id}/toc", response_model=List[ChapterResponse])
def get_book_toc(book_id: str, db: Session = Depends(get_db)):
    """Retrieve Table of Contents (chapters) for a book."""
    chapters = db.query(Chapter).filter(Chapter.book_id == book_id).order_by(Chapter.index_number.asc()).all()
    return chapters


@router.get("/{book_id}/page/{page_num}")
def get_book_page(book_id: str, page_num: int, db: Session = Depends(get_db)):
    """
    Renders and retrieves a page (for PDF) or a chapter (for EPUB).
    Updates last_opened timestamp.
    """
    book = db.query(Book).filter(Book.id == book_id).first()
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")

    # Update last opened timestamp
    book.last_opened = datetime.utcnow()
    db.commit()

    try:
        return PDFReaderService.render_page(book.file_path, page_num)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error rendering content: {str(e)}")
