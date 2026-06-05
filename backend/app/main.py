from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.advertisers import router as advertisers_router
from app.api.assistant import router as assistant_router
from app.api.auth import router as auth_router
from app.api.classifieds import router as classifieds_router
from app.api.complaints import router as complaints_router
from app.api.proposals import router as proposals_router
from app.api.subscribers import router as subscribers_router
from app.core.config import settings
from app.core.db import get_db

app = FastAPI(title="News CRM API", version="0.1.0")

app.include_router(auth_router)
app.include_router(advertisers_router)
app.include_router(classifieds_router)
app.include_router(subscribers_router)
app.include_router(complaints_router)
app.include_router(proposals_router)
app.include_router(assistant_router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/health/db")
def health_db(db: Session = Depends(get_db)) -> dict[str, str]:
    db.execute(text("SELECT 1"))
    return {"status": "ok", "db": "connected"}
