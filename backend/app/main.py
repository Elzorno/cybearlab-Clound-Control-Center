from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from .config import settings
from .db import SessionLocal, init_db
from .routers import admin, audit, auth, cron, databases, deployment, dns, files, ftp, grader, health, security, ssl, system, updates, users
from .services.auth import bootstrap_admin_user

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(auth.router)
app.include_router(admin.router)
app.include_router(grader.router)
app.include_router(audit.router)
app.include_router(system.router)
app.include_router(users.router)
app.include_router(dns.router)
app.include_router(files.router)
app.include_router(databases.router)
app.include_router(ftp.router)
app.include_router(cron.router)
app.include_router(security.router)
app.include_router(ssl.router)
app.include_router(updates.router)
app.include_router(deployment.router)


@app.on_event("startup")
def startup() -> None:
    init_db()
    db: Session = SessionLocal()
    try:
        bootstrap_admin_user(db)
    finally:
        db.close()
