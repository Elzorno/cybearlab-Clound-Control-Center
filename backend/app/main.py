from fastapi import FastAPI
from sqlalchemy.orm import Session

from .config import settings
from .db import SessionLocal, init_db
from .routers import admin, audit, auth, grader, health
from .services.auth import bootstrap_admin_user

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
)

app.include_router(health.router)
app.include_router(auth.router)
app.include_router(admin.router)
app.include_router(grader.router)
app.include_router(audit.router)


@app.on_event("startup")
def startup() -> None:
    init_db()
    db: Session = SessionLocal()
    try:
        bootstrap_admin_user(db)
    finally:
        db.close()
