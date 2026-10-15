"""Simple launcher script for Business Opportunity Finder."""

import uvicorn
from app.config import settings

if __name__ == "__main__":
    print(f"Starting {settings.APP_NAME}...")
    print(f"Dashboard available at: http://{settings.HOST}:{settings.PORT}")
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
    )
