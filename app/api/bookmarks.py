# app/api/bookmarks.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.database.session import get_db
from app.models.models import Bookmark
from app.schemas.schemas import BookmarkCreate, BookmarkResponse

router = APIRouter(prefix="/bookmarks", tags=["bookmarks"])

@router.get("/{book_id}", response_model=List[BookmarkResponse])
def list_bookmarks(book_id: str, db: Session = Depends(get_db)):
    """List bookmarks for a specific book."""
    return db.query(Bookmark).filter(Bookmark.book_id == book_id).order_by(Bookmark.page_number.asc()).all()


@router.post("", response_model=BookmarkResponse)
def create_bookmark(bookmark_in: BookmarkCreate, db: Session = Depends(get_db)):
    """Create a new bookmark."""
    bookmark = Bookmark(
        book_id=bookmark_in.book_id,
        title=bookmark_in.title,
        notes=bookmark_in.notes,
        page_number=bookmark_in.page_number
    )
    db.add(bookmark)
    db.commit()
    db.refresh(bookmark)
    return bookmark


@router.delete("/{bookmark_id}")
def delete_bookmark(bookmark_id: int, db: Session = Depends(get_db)):
    """Delete a bookmark."""
    bookmark = db.query(Bookmark).filter(Bookmark.id == bookmark_id).first()
    if not bookmark:
        raise HTTPException(status_code=404, detail="Bookmark not found")
    
    db.delete(bookmark)
    db.commit()
    return {"success": True, "message": "Bookmark removed"}
