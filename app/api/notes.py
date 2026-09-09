# app/api/notes.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.database.session import get_db
from app.models.models import Highlight
from app.schemas.schemas import HighlightCreate, HighlightUpdate, HighlightResponse

router = APIRouter(prefix="/notes", tags=["notes"])

@router.get("/{book_id}", response_model=List[HighlightResponse])
def list_highlights(book_id: str, db: Session = Depends(get_db)):
    """List highlights and notes for a specific book."""
    return db.query(Highlight).filter(Highlight.book_id == book_id).order_by(Highlight.page_number.asc(), Highlight.timestamp.asc()).all()


@router.post("", response_model=HighlightResponse)
def create_highlight(highlight_in: HighlightCreate, db: Session = Depends(get_db)):
    """Create a highlight or note."""
    highlight = Highlight(
        book_id=highlight_in.book_id,
        page_number=highlight_in.page_number,
        sentence_index=highlight_in.sentence_index,
        text=highlight_in.text,
        color=highlight_in.color or "yellow",
        notes=highlight_in.notes
    )
    db.add(highlight)
    db.commit()
    db.refresh(highlight)
    return highlight


@router.put("/{highlight_id}", response_model=HighlightResponse)
def update_highlight(
    highlight_id: int, 
    highlight_in: HighlightUpdate, 
    db: Session = Depends(get_db)
):
    """Update highlight color or note text."""
    highlight = db.query(Highlight).filter(Highlight.id == highlight_id).first()
    if not highlight:
        raise HTTPException(status_code=404, detail="Highlight not found")

    if highlight_in.color is not None:
        highlight.color = highlight_in.color
    if highlight_in.notes is not None:
        highlight.notes = highlight_in.notes

    db.commit()
    db.refresh(highlight)
    return highlight


@router.delete("/{highlight_id}")
def delete_highlight(highlight_id: int, db: Session = Depends(get_db)):
    """Delete a highlight/note."""
    highlight = db.query(Highlight).filter(Highlight.id == highlight_id).first()
    if not highlight:
        raise HTTPException(status_code=404, detail="Highlight not found")

    db.delete(highlight)
    db.commit()
    return {"success": True, "message": "Highlight/Note removed"}
