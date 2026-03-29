from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..deps import get_db
from ..models import User
from ..schemas import LoginRequest, LoginResponse
from ..services.audit import write_audit
from ..services.auth import issue_token, verify_password

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> LoginResponse:
    user = db.query(User).filter(User.username == payload.username, User.is_active.is_(True)).first()
    if not user or not verify_password(payload.password, user.password_hash):
        write_audit(
            db,
            actor_user_id=user.id if user else None,
            event_type="auth.login",
            entity_type="user",
            entity_id=user.id if user else None,
            status="denied",
            metadata={"username": payload.username},
        )
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    token, ttl = issue_token(user.id)
    write_audit(
        db,
        actor_user_id=user.id,
        event_type="auth.login",
        entity_type="user",
        entity_id=user.id,
        status="success",
        metadata={"username": user.username},
    )
    return LoginResponse(access_token=token, expires_in=ttl)
