# app/api/settings.py
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.models import Settings
from app.schemas.schemas import SettingsUpdate, SettingsResponse

router = APIRouter(prefix="/settings", tags=["settings"])

@router.get("", response_model=SettingsResponse)
def get_settings(db: Session = Depends(get_db)):
    """Retrieve settings. If none exist, initializes a default record."""
    settings = db.query(Settings).first()
    if not settings:
        settings = Settings(
            theme="dark",
            font_size=16,
            margins=15,
            line_spacing=1.5,
            paragraph_spacing=1.0,
            speech_rate=1.0,
            speech_pitch=1.0,
            speech_volume=1.0,
            speech_voice=""
        )
        db.add(settings)
        db.commit()
        db.refresh(settings)
    return settings


@router.put("", response_model=SettingsResponse)
def update_settings(settings_in: SettingsUpdate, db: Session = Depends(get_db)):
    """Update settings."""
    settings = db.query(Settings).first()
    if not settings:
        settings = Settings()
        db.add(settings)

    settings.theme = settings_in.theme
    settings.font_size = settings_in.font_size
    settings.margins = settings_in.margins
    settings.line_spacing = settings_in.line_spacing
    settings.paragraph_spacing = settings_in.paragraph_spacing
    settings.speech_rate = settings_in.speech_rate
    settings.speech_pitch = settings_in.speech_pitch
    settings.speech_volume = settings_in.speech_volume
    settings.speech_voice = settings_in.speech_voice

    db.commit()
    db.refresh(settings)
    return settings
