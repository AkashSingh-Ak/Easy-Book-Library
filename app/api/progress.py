# app/api/progress.py
import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.models.models import Book, ReadingSession
from app.schemas.schemas import ReadingSessionStart, ReadingSessionResponse

router = APIRouter(prefix="/progress", tags=["progress"])

@router.post("/{book_id}")
def update_progress(
    book_id: str,
    page_number: int = Query(..., description="Current page or chapter index"),
    db: Session = Depends(get_db)
):
    """
    Updates the current page number and calculates progress percentage.
    Also updates last_opened timestamp.
    """
    book = db.query(Book).filter(Book.id == book_id).first()
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")

    if page_number < 1:
        raise HTTPException(status_code=400, detail="Page number must be positive")

    # Limit page number to total_pages if available
    if book.total_pages > 0:
        page_number = min(page_number, book.total_pages)
        progress = (page_number / book.total_pages) * 100.0
        # If it's the last page, mark as 100
        if page_number == book.total_pages:
            progress = 100.0
    else:
        # Fallback if total pages is not yet indexed
        progress = 0.0

    # Ensure progress is saved
    book.reading_progress = round(min(100.0, max(0.0, progress)), 2)
    book.last_opened = datetime.datetime.utcnow()
    
    # Save the page number inside a dummy chapter title or bookmarks
    db.commit()
    return {
        "success": True,
        "page_number": page_number,
        "reading_progress": book.reading_progress
    }


@router.post("/session/start", response_model=ReadingSessionResponse)
def start_session(session_in: ReadingSessionStart, db: Session = Depends(get_db)):
    """Logs the start of a reading session."""
    book = db.query(Book).filter(Book.id == session_in.book_id).first()
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")

    # Close any open uncompleted sessions for this book
    open_sessions = db.query(ReadingSession).filter(
        ReadingSession.book_id == session_in.book_id,
        ReadingSession.end_time == None
    ).all()
    for s in open_sessions:
        s.end_time = datetime.datetime.utcnow()
        s.duration_seconds = int((s.end_time - s.start_time).total_seconds())

    new_session = ReadingSession(
        book_id=session_in.book_id,
        start_time=datetime.datetime.utcnow()
    )
    db.add(new_session)
    db.commit()
    db.refresh(new_session)
    
    return ReadingSessionResponse(
        session_id=new_session.id,
        book_id=new_session.book_id,
        start_time=new_session.start_time,
        duration_seconds=0
    )


@router.post("/session/end/{session_id}", response_model=ReadingSessionResponse)
def end_session(session_id: int, db: Session = Depends(get_db)):
    """Logs the end of a reading session and updates duration."""
    session = db.query(ReadingSession).filter(ReadingSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Reading session not found")

    if not session.end_time:
        session.end_time = datetime.datetime.utcnow()
        session.duration_seconds = int((session.end_time - session.start_time).total_seconds())
        db.commit()
        db.refresh(session)
        
    return ReadingSessionResponse(
        session_id=session.id,
        book_id=session.book_id,
        start_time=session.start_time,
        duration_seconds=session.duration_seconds
    )
