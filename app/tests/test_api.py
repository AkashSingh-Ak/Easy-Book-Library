# app/tests/test_api.py
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_settings_endpoints():
    # 1. Test GET settings (initializes if missing)
    response = client.get("/api/settings")
    assert response.status_code == 200
    data = response.json()
    assert "theme" in data
    assert "font_size" in data

    # 2. Test PUT settings
    payload = {
        "theme": "sepia",
        "font_size": 20,
        "margins": 12,
        "line_spacing": 1.8,
        "paragraph_spacing": 1.2,
        "speech_rate": 1.2,
        "speech_pitch": 1.0,
        "speech_volume": 0.8,
        "speech_voice": "Google US English"
    }
    response = client.put("/api/settings", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["theme"] == "sepia"
    assert data["font_size"] == 20
    assert data["speech_rate"] == 1.2


def test_vocabulary_lookup():
    # Test dictionary decomposition, CEFR tagger, and WordNet mapping
    response = client.get("/api/vocabulary/lookup/unbelievable")
    assert response.status_code == 200
    data = response.json()
    assert data["word"] == "unbelievable"
    assert "definitions" in data
    assert len(data["definitions"]) > 0
    assert data["cefr"] is not None
    assert data["prefix_analysis"]["component"] == "un-"
    assert data["suffix_analysis"]["component"] == "-able"
    assert data["root_analysis"] is None

    # Test another word containing a Latin/Greek root: e.g. incredible
    response = client.get("/api/vocabulary/lookup/incredible")
    assert response.status_code == 200
    data = response.json()
    assert data["word"] == "incredible"
    assert data["prefix_analysis"]["component"] == "in-"
    assert data["suffix_analysis"]["component"] == "-ible"
    assert data["root_analysis"]["component"] == "cred"


def test_books_list():
    # Test book retrieval query
    response = client.get("/api/books")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_speech_voices():
    # Test supported locales info endpoint
    response = client.get("/api/speech/voices")
    assert response.status_code == 200
    data = response.json()
    assert "locales" in data
    assert len(data["locales"]) > 0


def test_book_page_rendering():
    # Fetch first book
    books_response = client.get("/api/books")
    assert books_response.status_code == 200
    books = books_response.json()
    if books:
        book_id = books[0]["id"]
        # Render first page of that book
        response = client.get(f"/api/books/{book_id}/page/1")
        assert response.status_code == 200
        data = response.json()
        assert "image_url" in data
