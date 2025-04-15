# File: backend/app/core/cookies.py
from fastapi.responses import Response
import logging
from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

def set_cookie(response: Response, key: str, value: str, persistent: bool = False):
    """Set a cookie with appropriate security settings based on app config.
    
    Args:
        response: The FastAPI response to set the cookie on
        key: The cookie name
        value: The cookie value
        persistent: Whether the cookie should persist beyond the browser session
    
    Returns:
        The modified response with the cookie set.
    """
    # Determine cookie max_age based on whether it should be persistent or session-only
    max_age = settings.COOKIE_EXPIRY["persistent"] if persistent else settings.COOKIE_EXPIRY["session"]
    
    # Use secure flag from settings (typically True in production)
    secure_flag = settings.COOKIE_SECURE
    
    # Set SameSite=Lax for standard browser behavior and CSRF protection.
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