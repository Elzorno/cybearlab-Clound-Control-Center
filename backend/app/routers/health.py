from fastapi import APIRouter
from sqlalchemy import text
from sqlalchemy.orm import Session

from ..config import settings
from ..deps import get_db
from fastapi import Depends

router = APIRouter(tags=["System"])


@router.get("/health")
def health(db: Session = Depends(get_db)) -> dict:
    db_ok = True
    try:
        db.execute(text("SELECT 1"))
    except Exception:
        db_ok = False

    return {
        "status": "ok" if db_ok else "degraded",
        "version": settings.app_version,
        "queue_depth": 0,
    }
