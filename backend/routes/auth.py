"""Authentication routes."""
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel
from jose import jwt

from backend.settings import settings
from backend.logging_config import logger

router = APIRouter()


class LoginRequest(BaseModel):
    """Login request."""
    username: str
    password: str


class TokenResponse(BaseModel):
    """Token response."""
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class HealthResponse(BaseModel):
    """Health response."""
    status: str
    timestamp: datetime


@router.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest):
    """Authenticate user and return JWT token."""
    if not settings.AUTH_REQUIRED:
        # Dev mode: return dummy token
        token = jwt.encode(
            {
                "sub": "dev-user",
                "iat": int(datetime.now(timezone.utc).timestamp()),
                "exp": int((datetime.now(timezone.utc) + timedelta(minutes=settings.JWT_EXPIRATION_MINUTES)).timestamp()),
            },
            settings.JWT_SECRET,
            algorithm=settings.JWT_ALGORITHM,
        )
        return TokenResponse(
            access_token=token,
            expires_in=settings.JWT_EXPIRATION_MINUTES * 60,
        )
    
    # TODO: Implement real authentication with database
    logger.warning(f"Login attempt for user: {request.username}")
    raise HTTPException(status_code=401, detail="Authentication not implemented")


@router.post("/verify")
async def verify_token(authorization: Optional[str] = Header(None)):
    """Verify JWT token."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing Bearer token")
    
    try:
        token = authorization.split(" ", 1)[1].strip()
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        return {"valid": True, "user": payload.get("sub")}
    except Exception as e:
        logger.warning(f"Token verification failed: {e}")
        raise HTTPException(status_code=401, detail="Invalid token")
