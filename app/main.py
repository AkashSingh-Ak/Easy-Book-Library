# app/main.py
import os
from fastapi import FastAPI, Request, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.nltk_setup import ensure_nltk_data
from app.database.session import engine, get_db
from app.database.base import Base
# Import models to ensure they are registered for table creation
import app.models.models as models

# Import API Routers
from app.api import books, vocabulary, bookmarks, notes, settings as api_settings, progress, search, speech

# Download any missing NLTK language data before the app starts serving requests
ensure_nltk_data()

# Initialize Database Tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title=settings.PROJECT_NAME)

# Mount Static Files Directory
app.mount("/static", StaticFiles(directory=os.path.join(settings.BASE_DIR, "app", "static")), name="static")

# Mount Templates Directory
templates = Jinja2Templates(directory=os.path.join(settings.BASE_DIR, "app", "templates"))

# Register Routers
app.include_router(books.router, prefix="/api")
app.include_router(vocabulary.router, prefix="/api")
app.include_router(bookmarks.router, prefix="/api")
app.include_router(notes.router, prefix="/api")
app.include_router(api_settings.router, prefix="/api")
app.include_router(progress.router, prefix="/api")
app.include_router(search.router, prefix="/api")
app.include_router(speech.router, prefix="/api")


@app.get("/", response_class=HTMLResponse)
def library_view(request: Request, db: Session = Depends(get_db)):
    """Render the Library Page."""
    # Ensure settings exist
    db_settings = db.query(models.Settings).first()
    if not db_settings:
        db_settings = models.Settings()
        db.add(db_settings)
        db.commit()
        db.refresh(db_settings)
        
    return templates.TemplateResponse(request=request, name="library.html", context={"theme": db_settings.theme})


@app.get("/reader/{book_id}", response_class=HTMLResponse)
def reader_view(request: Request, book_id: str, db: Session = Depends(get_db)):
    """Render the Reading Interface Page."""
    book = db.query(models.Book).filter(models.Book.id == book_id).first()
    if not book:
        return HTMLResponse(content="<h1>Book not found</h1>", status_code=404)
        
    db_settings = db.query(models.Settings).first()
    if not db_settings:
        db_settings = models.Settings()
        db.add(db_settings)
        db.commit()
        db.refresh(db_settings)
        
    return templates.TemplateResponse(request=request, name="reader.html", context={
        "book": book,
        "theme": db_settings.theme,
        "settings": db_settings
    })


@app.get("/vocabulary", response_class=HTMLResponse)
def vocabulary_view(request: Request, db: Session = Depends(get_db)):
    """Render the Vocabulary Deck Manager Page."""
    db_settings = db.query(models.Settings).first()
    if not db_settings:
        db_settings = models.Settings()
        db.add(db_settings)
        db.commit()
        db.refresh(db_settings)
        
    return templates.TemplateResponse(request=request, name="vocabulary.html", context={"theme": db_settings.theme})
