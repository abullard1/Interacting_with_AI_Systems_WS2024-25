# File: backend/app/core/middleware.py
import logging
from starlette.middleware.base import BaseHTTPMiddleware
from app.core.config import get_settings
from starlette.responses import RedirectResponse
from starlette.requests import Request
from datetime import datetime, timedelta
import time
from app.core.cookies import set_cookie

settings = get_settings()
logger = logging.getLogger(__name__)

# Middleware to set Cache-Control headers
class CacheControlMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        path = request.url.path
        
        # No caching for Vite-built assets (often have hashes in names)
        if path.startswith("/assets/"):
            response.headers["Cache-Control"] = "no-store"
        
        # Long cache for favicons
        elif path.startswith("/favicons/"):
            response.headers["Cache-Control"] = "public, max-age=31536000" # 1 year

        # Moderate cache for images
        elif path.startswith("/images/"):
            response.headers["Cache-Control"] = "public, max-age=86400" # 1 day
        
        # Moderate cache for PDFs
        elif path.startswith("/pdfs/"):
            response.headers["Cache-Control"] = "public, max-age=86400" # 1 day
            
        # No caching for HTML pages (often dynamic)
        elif path.endswith(".html"):
            response.headers["Cache-Control"] = "no-store"

        # Default: No caching for API calls and other paths
        else:
            response.headers["Cache-Control"] = "no-store"
        
        return response

# Middleware to set security headers
class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)

        # Prevent browser from guessing MIME types
        response.headers["X-Content-Type-Options"] = "nosniff"

        # Enable basic XSS protection in older browsers
        response.headers["X-XSS-Protection"] = "1; mode=block"

        response.headers["X-Frame-Options"] = "ALLOWALL"

        response.headers["Content-Security-Policy"] = (
            "frame-ancestors 'self' https://gradio.unistudy.tech https://www.gradio.unistudy.tech "
            "https://unistudy.tech http://localhost:7860 http://localhost:7861;"
        )

        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        response.headers["X-Permitted-Cross-Domain-Policies"] = "none"
        
        return response

# Middleware to track study session duration and enforce expiry
class SessionTrackingMiddleware(BaseHTTPMiddleware):
    # Max session duration: 1 hour
    SESSION_EXPIRATION = 60 * 60
    
    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        if path.startswith(('/assets/', '/favicons/', '/images/', '/pdfs/', '/js/', '/styles/')) or \
           path in ['/token-expired', '/already-completed']:
            return await call_next(request)
        
        study_token = request.cookies.get("study_token")
        session_start = request.cookies.get("session_start")
        current_time = int(time.time())
        
        if study_token and session_start:
            try:
                start_time = int(session_start)
                session_duration = current_time - start_time
                
                if session_duration > self.SESSION_EXPIRATION:
                    logger.info(f"[Session] Session expired for token {study_token} - active for {session_duration} seconds ({self.SESSION_EXPIRATION // 60} min limit)")
                    
                    if not path.startswith('/api/') and path != '/token-expired':
                        return RedirectResponse(url="/token-expired", status_code=302)
            except (ValueError, TypeError):
                logger.warning(f"[Session] Invalid session_start format: {session_start}")
        
        response = await call_next(request)
        
        # Update last activity time on every relevant request
        response.set_cookie(
            key="last_activity",
            value=str(current_time),
            httponly=False,
            secure=settings.COOKIE_SECURE,
            samesite="Lax"
        )
        
        if not session_start and study_token:
            logger.info(f"[Session] Setting initial session_start for token {study_token}")
            response.set_cookie(
                key="session_start",
                value=str(current_time),
                httponly=False,
                secure=settings.COOKIE_SECURE,
                samesite="Lax"
            )
        
        return response