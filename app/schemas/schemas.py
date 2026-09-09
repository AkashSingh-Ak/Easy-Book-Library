# app/schemas/schemas.py
from pydantic import BaseModel, Field
from typing import List, Optional, Any
from datetime import datetime

# Settings Schemas
class SettingsBase(BaseModel):
    theme: str = "dark"
    font_size: int = 16
    margins: int = 15
    line_spacing: float = 1.5
    paragraph_spacing: float = 1.0
    speech_rate: float = 1.0
    speech_pitch: float = 1.0
    speech_volume: float = 1.0
    speech_voice: Optional[str] = None

class SettingsUpdate(SettingsBase):
    pass

class SettingsResponse(SettingsBase):
    id: int

    class Config:
        from_attributes = True


# Book Schemas
class BookBase(BaseModel):
    title: str
    author: Optional[str] = None
    file_type: str
    file_size: int
    cover_path: Optional[str] = None
    total_pages: int = 0
    publisher: Optional[str] = None
    isbn: Optional[str] = None
    tags: Optional[str] = None

class BookResponse(BookBase):
    id: str
    added_date: datetime
    last_opened: Optional[datetime] = None
    reading_progress: float

    class Config:
        from_attributes = True


# Chapter Schemas
class ChapterResponse(BaseModel):
    id: int
    book_id: str
    title: str
    page_number: int
    index_number: int

    class Config:
        from_attributes = True


# Bookmark Schemas
class BookmarkCreate(BaseModel):
    book_id: str
    title: Optional[str] = None
    notes: Optional[str] = None
    page_number: int

class BookmarkResponse(BookmarkCreate):
    id: int
    timestamp: datetime

    class Config:
        from_attributes = True


# Highlight Schemas
class HighlightCreate(BaseModel):
    book_id: str
    page_number: int
    sentence_index: Optional[int] = None
    text: str
    color: Optional[str] = "yellow"
    notes: Optional[str] = None

class HighlightUpdate(BaseModel):
    color: Optional[str] = None
    notes: Optional[str] = None

class HighlightResponse(HighlightCreate):
    id: int
    timestamp: datetime

    class Config:
        from_attributes = True


# Vocabulary Schemas
class VocabularyCreate(BaseModel):
    word: str
    meaning: str
    book_id: Optional[str] = None
    chapter: Optional[str] = None
    sentence: Optional[str] = None
    context: Optional[str] = None
    page_number: Optional[int] = None
    personal_notes: Optional[str] = None
    learning_status: Optional[str] = "Learning"
    definition_json: Optional[str] = None

class VocabularyUpdate(BaseModel):
    personal_notes: Optional[str] = None
    learning_status: Optional[str] = None

class VocabularyResponse(VocabularyCreate):
    id: int
    date_added: datetime
    times_viewed: int
    times_searched: int

    class Config:
        from_attributes = True


# Word History Schemas
class WordHistoryResponse(BaseModel):
    id: int
    word: str
    context: Optional[str] = None
    action: str
    timestamp: datetime

    class Config:
        from_attributes = True


# Reading Progress Schemas
class ReadingProgressUpdate(BaseModel):
    current_page: int
    current_chapter: Optional[str] = None
    current_sentence: Optional[int] = None

class ReadingProgressResponse(BaseModel):
    book_id: str
    current_page: int
    completion_percentage: float
    estimated_remaining_minutes: int


# Search inside book schemas
class SearchInsideBookRequest(BaseModel):
    query: str

class SearchResultResponse(BaseModel):
    page_number: int
    chapter_title: Optional[str] = None
    sentence: str
    context: str

# Reading Session
class ReadingSessionStart(BaseModel):
    book_id: str

class ReadingSessionResponse(BaseModel):
    session_id: int
    book_id: str
    start_time: datetime
    duration_seconds: int

# Word details structure
class MorphologicalComponent(BaseModel):
    component: str
    meaning: str
    role: str
    meaning_hindi: Optional[str] = None
    role_hindi: Optional[str] = None

class WordAnalysisResponse(BaseModel):
    word: str
    pronunciation: Optional[str] = None
    ipa: Optional[str] = None
    part_of_speech: Optional[str] = None
    definitions: List[str] = []
    synonyms: List[str] = []
    antonyms: List[str] = []
    examples: List[str] = []
    cefr: Optional[str] = None
    frequency: Optional[float] = None
    etymology: Optional[str] = None
    etymology_tree: Optional[str] = None
    prefix_analysis: Optional[MorphologicalComponent] = None
    root_analysis: Optional[MorphologicalComponent] = None
    suffix_analysis: Optional[MorphologicalComponent] = None
    related_words: List[str] = []
    
    # Hindi translations
    word_hindi: Optional[str] = None
    part_of_speech_hindi: Optional[str] = None
    definitions_hindi: List[str] = []
    etymology_hindi: Optional[str] = None
    examples_hindi: List[str] = []
    is_saved: bool = False
