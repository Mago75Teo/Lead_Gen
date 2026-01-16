from fastapi import Header, HTTPException
from .settings import settings

async def require_bearer(authorization: str | None = Header(default=None)):
    token = settings.API_BEARER_TOKEN
    if not token:
        return
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")
    if authorization.split(" ", 1)[1].strip() != token:
        raise HTTPException(status_code=403, detail="Invalid bearer token")
