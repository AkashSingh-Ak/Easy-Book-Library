# main.py
import uvicorn
from app.core import constants

if __name__ == "__main__":
    print(f"Starting Easy Book Library server at http://{constants.HOST}:{constants.PORT}...")
    uvicorn.run(
        "app.main:app",
        host=constants.HOST,
        port=constants.PORT,
        reload=constants.RELOAD
    )
