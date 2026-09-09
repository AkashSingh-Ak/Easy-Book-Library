# app/api/vocabulary.py
import json
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime

from app.database.session import get_db, SessionLocal
from app.models.models import Vocabulary, WordHistory
from app.schemas.schemas import VocabularyResponse, VocabularyUpdate, WordAnalysisResponse, WordHistoryResponse
from app.services.vocabulary.vocab_service import VocabularyService

router = APIRouter(prefix="/vocabulary", tags=["vocabulary"])


def migrate_vocab_record_if_needed(vocab: Vocabulary, db: Session, service: VocabularyService) -> bool:
    """
    Checks if a vocabulary record is missing Hindi translations, and translates/updates it.
    Also keeps `meaning` as plain English - Hindi text only ever lives in
    definition_json's `definitions_hindi`, so the frontend's Hindi toggle can
    decide whether to show it instead of it being permanently baked in.
    Returns True if the record was changed, False otherwise.
    """
    details = {}
    if vocab.definition_json:
        try:
            details = json.loads(vocab.definition_json)
        except Exception:
            pass

    # Determine if it needs translation
    needs_translate = False
    if not details:
        needs_translate = True
    elif "definitions_hindi" not in details or "word_hindi" not in details:
        needs_translate = True
    else:
        # Check if definitions is present but definitions_hindi is missing/empty/mismatched/all-empty
        defs = details.get("definitions", [])
        defs_hi = details.get("definitions_hindi", [])
        if defs and (not defs_hi or len(defs_hi) != len(defs) or all(not d for d in defs_hi)):
            needs_translate = True

    if needs_translate:
        try:
            analysis = service.analyze_word(vocab.word)
            try:
                details = analysis.model_dump()
            except AttributeError:
                details = analysis.dict()

            vocab.definition_json = json.dumps(details)
        except Exception as e:
            print(f"Failed to migrate vocab record '{vocab.word}': {e}")
            return False

    updated = needs_translate

    # Self-heal older records saved before the Hindi toggle existed, where a
    # Hindi translation was appended directly onto `meaning`.
    clean_definitions = details.get("definitions") or []
    if clean_definitions and vocab.meaning != clean_definitions[0]:
        vocab.meaning = clean_definitions[0]
        updated = True

    if updated:
        db.add(vocab)
        db.commit()

    return updated


def bulk_migrate_vocab_records(db_session_factory, service: VocabularyService):
    """
    Performs a background scan of all vocabulary records to translate any that need it.
    """
    db = db_session_factory()
    try:
        records = db.query(Vocabulary).all()
        updated = False
        for vocab in records:
            if migrate_vocab_record_if_needed(vocab, db, service):
                updated = True
        if updated:
            db.commit()
    except Exception as e:
        print(f"Error in background bulk migration: {e}")
    finally:
        db.close()

@router.get("/lookup/{word}", response_model=WordAnalysisResponse)
def lookup_word(
    word: str,
    book_id: Optional[str] = Query(None),
    chapter: Optional[str] = Query(None),
    sentence: Optional[str] = Query(None),
    context: Optional[str] = Query(None),
    page_number: Optional[int] = Query(None),
    db: Session = Depends(get_db)
):
    """
    Performs etymological, grammatical, and morphological lookup.
    Automatically saves the word into the local vocabulary database if new.
    Logs the lookup action in WordHistory.
    """
    service = VocabularyService()
    cleaned = service.clean_word(word)
    
    if not cleaned:
        raise HTTPException(status_code=400, detail="Invalid word string")
        
    analysis = service.analyze_word(cleaned)
    
    # Check if word is already saved in Vocabulary
    db_vocab = db.query(Vocabulary).filter(Vocabulary.word == cleaned).first()
    
    is_saved = False
    if db_vocab:
        is_saved = True
        # Word exists, increment views
        db_vocab.times_viewed += 1
        if context:
            db_vocab.context = context
        if sentence:
            db_vocab.sentence = sentence
        if book_id:
            db_vocab.book_id = book_id
        if page_number:
            db_vocab.page_number = page_number
        if chapter:
            db_vocab.chapter = chapter
            
        # Ensure it has Hindi translations in the database
        migrate_vocab_record_if_needed(db_vocab, db, service)
        
        db.commit()
        db.refresh(db_vocab)
        
    # Log lookup in history
    history = WordHistory(
        word=cleaned,
        context=context,
        action="viewed"
    )
    db.add(history)
    db.commit()
    
    # Return response with is_saved state
    try:
        analysis_dict = analysis.model_dump()
    except AttributeError:
        analysis_dict = analysis.dict()
    analysis_dict["is_saved"] = is_saved
    return WordAnalysisResponse(**analysis_dict)


@router.post("/save", response_model=VocabularyResponse)
def save_word(
    word: str = Query(...),
    book_id: Optional[str] = Query(None),
    chapter: Optional[str] = Query(None),
    sentence: Optional[str] = Query(None),
    context: Optional[str] = Query(None),
    page_number: Optional[int] = Query(None),
    db: Session = Depends(get_db)
):
    """
    Explicitly saves a word into the local vocabulary database.
    """
    service = VocabularyService()
    cleaned = service.clean_word(word)
    if not cleaned:
        raise HTTPException(status_code=400, detail="Invalid word string")
        
    analysis = service.analyze_word(cleaned)
    
    # Check if word is already saved in Vocabulary
    db_vocab = db.query(Vocabulary).filter(Vocabulary.word == cleaned).first()
    if db_vocab:
        return db_vocab
        
    # Kept as plain English - the Hindi translation lives separately in
    # definition_json.definitions_hindi and is only shown when the
    # frontend's Hindi toggle is on.
    first_meaning = analysis.definitions[0] if analysis.definitions else "No definition found"

    try:
        analysis_dict = analysis.model_dump()
    except AttributeError:
        analysis_dict = analysis.dict()
        
    db_vocab = Vocabulary(
        word=cleaned,
        meaning=first_meaning,
        book_id=book_id,
        chapter=chapter,
        sentence=sentence,
        context=context,
        page_number=page_number,
        times_viewed=1,
        times_searched=0,
        learning_status="Learning",
        definition_json=json.dumps(analysis_dict)
    )
    db.add(db_vocab)
    db.commit()
    db.refresh(db_vocab)
    return db_vocab


@router.get("", response_model=List[VocabularyResponse])
def list_vocabulary(
    search: Optional[str] = Query(None, description="Search word or meaning"),
    book_id: Optional[str] = Query(None, description="Filter by book ID"),
    learning_status: Optional[str] = Query(None, description="Filter: Known, Learning, Review Later, Mastered"),
    sort_by: str = Query("date_desc", description="Sorting: date_desc, date_asc, alphabetical, views_desc"),
    background_tasks: BackgroundTasks = None,
    db: Session = Depends(get_db)
):
    """Retrieve saved vocabulary list with queries and filters."""
    # Queue background migration of all records
    if background_tasks:
        service = VocabularyService()
        background_tasks.add_task(bulk_migrate_vocab_records, SessionLocal, service)

    query = db.query(Vocabulary)

    if search:
        search_val = f"%{search}%"
        query = query.filter(
            Vocabulary.word.like(search_val) | 
            Vocabulary.meaning.like(search_val) |
            Vocabulary.personal_notes.like(search_val)
        )

    if book_id:
        query = query.filter(Vocabulary.book_id == book_id)

    if learning_status:
        query = query.filter(Vocabulary.learning_status == learning_status)

    if sort_by == "date_desc":
        query = query.order_by(Vocabulary.date_added.desc())
    elif sort_by == "date_asc":
        query = query.order_by(Vocabulary.date_added.asc())
    elif sort_by == "alphabetical":
        query = query.order_by(Vocabulary.word.asc())
    elif sort_by == "views_desc":
        query = query.order_by(Vocabulary.times_viewed.desc())

    return query.all()


@router.get("/word/{word}", response_model=VocabularyResponse)
def get_vocab_word(word: str, db: Session = Depends(get_db)):
    """Retrieve details of a saved vocabulary word."""
    service = VocabularyService()
    cleaned = service.clean_word(word)
    vocab = db.query(Vocabulary).filter(Vocabulary.word == cleaned).first()
    if not vocab:
        raise HTTPException(status_code=404, detail="Word not saved in vocabulary deck")
        
    # Check and migrate on-the-fly using the robust checker
    if migrate_vocab_record_if_needed(vocab, db, service):
        db.refresh(vocab)
        
    return vocab


@router.put("/word/{word}", response_model=VocabularyResponse)
def update_vocab_word(
    word: str, 
    update_data: VocabularyUpdate, 
    db: Session = Depends(get_db)
):
    """Update learning status and personal notes for a vocabulary word."""
    service = VocabularyService()
    cleaned = service.clean_word(word)
    vocab = db.query(Vocabulary).filter(Vocabulary.word == cleaned).first()
    if not vocab:
        raise HTTPException(status_code=404, detail="Word not found")

    if update_data.learning_status is not None:
        vocab.learning_status = update_data.learning_status
    if update_data.personal_notes is not None:
        vocab.personal_notes = update_data.personal_notes

    db.commit()
    db.refresh(vocab)
    return vocab


@router.delete("/word/{word}")
def delete_vocab_word(word: str, db: Session = Depends(get_db)):
    """Remove a word from the vocabulary deck."""
    service = VocabularyService()
    cleaned = service.clean_word(word)
    vocab = db.query(Vocabulary).filter(Vocabulary.word == cleaned).first()
    if not vocab:
        raise HTTPException(status_code=404, detail="Word not found")
    
    db.delete(vocab)
    db.commit()
    return {"success": True, "message": "Word removed from vocabulary"}


@router.get("/history", response_model=List[WordHistoryResponse])
def get_history(limit: int = 50, db: Session = Depends(get_db)):
    """Get lookup history list."""
    return db.query(WordHistory).order_by(WordHistory.timestamp.desc()).limit(limit).all()
