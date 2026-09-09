# app/api/search.py
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List

from app.database.session import get_db
from app.models.models import Book
from app.schemas.schemas import SearchResultResponse
from app.services.search.search_service import SearchService

router = APIRouter(prefix="/search", tags=["search"])

@router.get("/{book_id}", response_model=List[SearchResultResponse])
def search_inside_book(
    book_id: str,
    q: str = Query(..., min_length=2, description="Search query term"),
    db: Session = Depends(get_db)
):
    """Performs full text search inside PDF/EPUB books."""
    book = db.query(Book).filter(Book.id == book_id).first()
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")

    try:
        results = SearchService.search(book.file_path, book.file_type, q)
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")
