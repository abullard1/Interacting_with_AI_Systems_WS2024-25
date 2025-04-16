# File: backend/app/core/cookies.py
from fastapi.responses import Response
import logging
from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

def set_cookie(response: Response, key: str, value: str, persistent: bool = False):
    max_age = settings.COOKIE_EXPIRY["persistent"] if persistent else settings.COOKIE_EXPIRY["session"]
    
    secure_flag = settings.COOKIE_SECURE
    
    samesite = "Lax"
    
    logger.info(f"Setting cookie '{key}' (persistent: {persistent}, secure: {secure_flag}, samesite: {samesite})")
    
    response.set_cookie(
        key=key,
        value=value,
        httponly=False, 
        secure=secure_flag,
        samesite=samesite,
        max_age=max_age
    )
    
    return response