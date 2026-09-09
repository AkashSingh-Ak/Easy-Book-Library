# app/models/models.py
import datetime
from sqlalchemy import Column, String, Integer, Float, DateTime, ForeignKey, Text, Boolean
from sqlalchemy.orm import relationship
from app.database.base import Base

class Book(Base):
    __tablename__ = "books"

    id = Column(String, primary_key=True)  # Hash of file or UUID
    title = Column(String, nullable=False, index=True)
    author = Column(String, index=True)
    file_path = Column(String, nullable=False)
    file_type = Column(String, nullable=False)  # 'pdf' or 'epub'
    file_size = Column(Integer, nullable=False)
    cover_path = Column(String)
    total_pages = Column(Integer, default=0)
    publisher = Column(String)
    isbn = Column(String)
    tags = Column(Text)  # Comma-separated or JSON array string
    added_date = Column(DateTime, default=datetime.datetime.utcnow)
    last_opened = Column(DateTime)
    reading_progress = Column(Float, default=0.0)  # Percentage 0 to 100

    # Relationships
    chapters = relationship("Chapter", back_populates="book", cascade="all, delete-orphan")
    bookmarks = relationship("Bookmark", back_populates="book", cascade="all, delete-orphan")
    highlights = relationship("Highlight", back_populates="book", cascade="all, delete-orphan")
    reading_sessions = relationship("ReadingSession", back_populates="book", cascade="all, delete-orphan")


class Chapter(Base):
    __tablename__ = "chapters"

    id = Column(Integer, primary_key=True, autoincrement=True)
    book_id = Column(String, ForeignKey("books.id", ondelete="CASCADE"), nullable=False)
    title = Column(String, nullable=False)
    page_number = Column(Integer, nullable=False)
    index_number = Column(Integer, nullable=False)

    book = relationship("Book", back_populates="chapters")


class Bookmark(Base):
    __tablename__ = "bookmarks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    book_id = Column(String, ForeignKey("books.id", ondelete="CASCADE"), nullable=False)
    title = Column(String)
    notes = Column(Text)
    page_number = Column(Integer, nullable=False)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)

    book = relationship("Book", back_populates="bookmarks")


class Highlight(Base):
    __tablename__ = "highlights"

    id = Column(Integer, primary_key=True, autoincrement=True)
    book_id = Column(String, ForeignKey("books.id", ondelete="CASCADE"), nullable=False)
    page_number = Column(Integer, nullable=False)
    sentence_index = Column(Integer)  # To map to specific sentence on page/chapter
    text = Column(Text, nullable=False)
    color = Column(String, default="yellow")
    notes = Column(Text)  # If user attaches a note to this highlight
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)

    book = relationship("Book", back_populates="highlights")


class Vocabulary(Base):
    __tablename__ = "vocabulary"

    id = Column(Integer, primary_key=True, autoincrement=True)
    word = Column(String, unique=True, nullable=False, index=True)
    meaning = Column(Text, nullable=False)
    date_added = Column(DateTime, default=datetime.datetime.utcnow)
    book_id = Column(String, ForeignKey("books.id", ondelete="SET NULL"), nullable=True)
    chapter = Column(String)
    sentence = Column(Text)
    context = Column(Text)
    page_number = Column(Integer)
    times_viewed = Column(Integer, default=1)
    times_searched = Column(Integer, default=0)
    personal_notes = Column(Text)
    learning_status = Column(String, default="Learning")  # 'Known', 'Learning', 'Review Later', 'Mastered'
    definition_json = Column(Text)  # JSON-serialized morphological details, etymology, IPA, synonyms, CEFR, etc.


class WordHistory(Base):
    __tablename__ = "word_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    word = Column(String, nullable=False, index=True)
    context = Column(Text)
    action = Column(String)  # 'viewed' or 'searched'
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)


class Settings(Base):
    __tablename__ = "settings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    theme = Column(String, default="dark")  # 'light', 'dark', 'sepia'
    font_size = Column(Integer, default=16)
    margins = Column(Integer, default=15)  # in percentage or px
    line_spacing = Column(Float, default=1.5)
    paragraph_spacing = Column(Float, default=1.0)
    speech_rate = Column(Float, default=1.0)
    speech_pitch = Column(Float, default=1.0)
    speech_volume = Column(Float, default=1.0)
    speech_voice = Column(String)  # Name of selected voice


class ReadingSession(Base):
    __tablename__ = "reading_sessions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    book_id = Column(String, ForeignKey("books.id", ondelete="CASCADE"), nullable=False)
    start_time = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    end_time = Column(DateTime)
    duration_seconds = Column(Integer, default=0)

    book = relationship("Book", back_populates="reading_sessions")
