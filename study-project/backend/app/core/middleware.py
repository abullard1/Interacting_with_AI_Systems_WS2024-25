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
    """Sets Cache-Control headers based on request path patterns."""
    
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
    """Adds common security-related HTTP headers to responses."""
    
    async def dispatch(self, request, call_next):
        response = await call_next(request)

        # Prevent browser from guessing MIME types
        response.headers["X-Content-Type-Options"] = "nosniff"

        # Enable basic XSS protection in older browsers
        response.headers["X-XSS-Protection"] = "1; mode=block"

        # Allow framing only from specific origins (controlled by CSP below)
        # ALLOWALL is weak, but frame-ancestors in CSP is the primary control here.
        response.headers["X-Frame-Options"] = "ALLOWALL"

        # Define Content Security Policy, specifically controlling iframe embedding
        response.headers["Content-Security-Policy"] = (
            "frame-ancestors 'self' https://gradio.unistudy.tech https://www.gradio.unistudy.tech "
            "https://unistudy.tech http://localhost:7860 http://localhost:7861;"
        )

        # Control information sent in Referer header
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # Disallow Flash/PDF cross-domain policies
        response.headers["X-Permitted-Cross-Domain-Policies"] = "none"
        
        return response

# Middleware to track study session duration and enforce expiry
class SessionTrackingMiddleware(BaseHTTPMiddleware):
    """Tracks user session start time via cookie and redirects if session exceeds limit."""
    
    # Max session duration: 1 hour
    SESSION_EXPIRATION = 60 * 60
    
    async def dispatch(self, request: Request, call_next):
        # Ignore static assets and specific error/info pages for session tracking
        path = request.url.path
        if path.startswith(('/assets/', '/favicons/', '/images/', '/pdfs/', '/js/', '/styles/')) or \
           path in ['/token-expired', '/already-completed']:
            return await call_next(request)
        
        study_token = request.cookies.get("study_token")
        session_start = request.cookies.get("session_start")
        current_time = int(time.time())
        
        # Check for absolute session expiration based on session_start cookie
        if study_token and session_start:
            try:
                start_time = int(session_start)
                session_duration = current_time - start_time
                
                # If session exceeds the defined expiration limit, redirect
                if session_duration > self.SESSION_EXPIRATION:
                    logger.info(f"[Session] Session expired for token {study_token} - active for {session_duration} seconds ({self.SESSION_EXPIRATION // 60} min limit)")
                    
                    # Avoid redirect loop if already on expiry page or during API calls
                    if not path.startswith('/api/') and path != '/token-expired':
                        return RedirectResponse(url="/token-expired", status_code=302)
            except (ValueError, TypeError):
                # Invalid session_start format, will be reset below
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
        
        # Set the initial session_start timestamp if it doesn't exist for this user
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