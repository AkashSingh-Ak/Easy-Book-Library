import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "Easy Book Library"
    
    # Paths relative to the root BOOK_READER dir
    BASE_DIR: str = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    # SQLite Database URI (inside app/database/reader.db)
    DATABASE_URL: str = f"sqlite:///{os.path.join(BASE_DIR, 'app', 'database', 'reader.db')}"
    
    # Upload Directories
    UPLOAD_DIR: str = os.path.join(BASE_DIR, "app", "static", "books")
    COVER_DIR: str = os.path.join(BASE_DIR, "app", "static", "covers")
    
    # Secret Key for potential future expansions
    SECRET_KEY: str = "supersecret_default_key_change_me_in_prod"

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()

# Ensure required directories exist
os.makedirs(os.path.join(settings.BASE_DIR, "app", "database"), exist_ok=True)
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
os.makedirs(settings.COVER_DIR, exist_ok=True)
