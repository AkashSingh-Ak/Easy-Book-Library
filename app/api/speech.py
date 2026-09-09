# app/api/speech.py
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List, Dict, Any

from app.database.session import get_db
from app.models.models import Settings

router = APIRouter(prefix="/speech", tags=["speech"])

@router.get("/voices")
def list_supported_languages() -> Dict[str, Any]:
    """
    Returns standard language tags and offline TTS engine recommendations.
    (Note: The actual voices are queried directly from the browser's Web Speech API for offline, native speed).
    """
    return {
        "engine": "Speech Dispatcher / Web Speech API",
        "locales": [
            {"code": "en-US", "name": "English (United States)"},
            {"code": "en-GB", "name": "English (United Kingdom)"},
            {"code": "es-ES", "name": "Spanish (Spain)"},
            {"code": "fr-FR", "name": "French (France)"},
            {"code": "de-DE", "name": "German (Germany)"},
            {"code": "zh-CN", "name": "Chinese (China)"},
            {"code": "yue-HK", "name": "Cantonese (Hong Kong)"}
        ],
        "notes": "Query window.speechSynthesis.getVoices() on the client for the full set of local voices."
    }
