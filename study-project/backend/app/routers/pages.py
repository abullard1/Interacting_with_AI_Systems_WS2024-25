from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse
import logging
import uuid
import re
from app.core.cookies import set_cookie
from app.core.static_handler import serve_static_file

logger = logging.getLogger(__name__)
router = APIRouter(include_in_schema=False)

def is_valid_study_token(token: str) -> bool:
    """Validate that a study token is in the correct format (UUID)."""
    if not token:
        logger.warning(f"[Token Validation] Empty token provided")
        return False
    
    # Check if token is a valid UUID
    try:
        uuid_obj = uuid.UUID(token)
        is_valid = str(uuid_obj) == token
        if not is_valid:
            logger.warning(f"[Token Validation] Invalid token format: {token}")
        return is_valid
    except (ValueError, AttributeError, TypeError) as e:
        logger.warning(f"[Token Validation] Exception validating token {token}: {str(e)}")
        return False

@router.head("/{path:path}")
@router.get("/{path:path}")
async def handle_page(path: str, request: Request):
    """Serve pages with study token validation and completion checks."""
    logger.info(f"[Pages] Request for path: {path}")
    
    # Log all cookies for debugging
    logger.info("[Pages] All cookies received:")
    for cookie_name, cookie_value in request.cookies.items():
        logger.info(f"  - {cookie_name}: {cookie_value}")
    
    # Debug flow control
    logger.info(f"[Pages] Current path: {path}, checking access rules...")
    
    # Normalize path
    path = path or "index.html"
    
    # Define route type flags
    homepage = path in ["", "index.html"]
    component_templates = path in ["navbar.html", "footer.html", "error-modal.html", "bug-report-modal.html"]
    static_paths = path.startswith(('assets/', 'favicons/', 'images/', 'pdfs/', 'js/', 'styles/'))
    error_pages = path in ["token-expired", "already-completed"]
    exempt_from_completed_redirect = path in ["finish", "finish.html", "already-completed", "already-completed.html"] or component_templates or static_paths
    
    # First, check if study is already completed, before serving any content
    # Only redirect if path is not exempt from redirection
    if request.cookies.get("study-completed") == "true" and not exempt_from_completed_redirect:
        logger.info(f"[Pages] Redirecting completed user from {path} to already-completed")
        return RedirectResponse(url="/already-completed", status_code=302)
    
    # Generate a consistent study token for a given user session
    study_token = request.cookies.get("study_token")
    
    # For component templates, serve the file without redirections
    if component_templates:
        response = serve_static_file(path)
        if response:
            # Always keep study_token consistent
            if not study_token:
                new_token = str(uuid.uuid4())
                logger.info(f"[Pages] Setting new study token for component template: {new_token}")
                set_cookie(response, "study_token", new_token)
            return response
        else:
            return RedirectResponse(url="/token-expired", status_code=302)
    
    # For homepage, serve the file and ensure study_token is set
    if homepage:
        response = serve_static_file(path)
        if response:
            # If no token exists, create one
            if not study_token:
                new_token = str(uuid.uuid4())
                logger.info(f"[Pages] Setting new study token for homepage: {new_token}")
                set_cookie(response, "study_token", new_token)
            # If token exists but is invalid, replace it
            elif not is_valid_study_token(study_token):
                new_token = str(uuid.uuid4())
                logger.info(f"[Pages] Replacing invalid study token: {study_token} with {new_token}")
                set_cookie(response, "study_token", new_token)
            return response
        else:
            return RedirectResponse(url="/token-expired", status_code=302)
    
    # For other static assets and error pages, serve without token check
    if static_paths or error_pages:
        logger.info(f"[Pages] Serving no-auth resource: {path}")
        return serve_static_file(path) or RedirectResponse(url="/token-expired", status_code=302)
        
    # All other pages require a valid study token
    if not study_token:
        logger.warning(f"[Pages] Missing study token for {path}, redirecting to token-expired")
        return RedirectResponse(url="/token-expired", status_code=302)
    
    if not is_valid_study_token(study_token):
        logger.warning(f"[Pages] Invalid study token format: {study_token} for {path}, redirecting to homepage")
        return RedirectResponse(url="/", status_code=302)  # Redirect to homepage to get new token
    
    # Section completion checks - prevent accessing pages out of order
    study_path = path.split('.')[0]  # Remove file extension if present
    
    # FORWARD PROGRESSION CHECKS (prevent skipping ahead)
    if study_path == "pre-study" and request.cookies.get("consent-given") != "true":
        logger.info(f"[Pages] Attempt to access pre-study without completing consent")
        return RedirectResponse(url="/consent", status_code=302)
    
    if study_path == "token" and request.cookies.get("pre-study-completed") != "true":
        logger.info(f"[Pages] Attempt to access token without completing pre-study")
        return RedirectResponse(url="/pre-study", status_code=302)
    
    if study_path == "study-explanation" and request.cookies.get("token-page-completed") != "true":
        logger.info(f"[Pages] Attempt to access study-explanation without completing token page")
        return RedirectResponse(url="/token", status_code=302)
    
    if study_path == "study" and request.cookies.get("study-explanation-completed") != "true":
        logger.info(f"[Pages] Attempt to access study without completing study-explanation")
        return RedirectResponse(url="/study-explanation", status_code=302)
    
    if study_path == "post-study" and request.cookies.get("gradio-main-study-completed") != "true":
        logger.info(f"[Pages] Attempt to access post-study without completing main study")
        return RedirectResponse(url="/study", status_code=302)
    
    if study_path == "finish" and request.cookies.get("post-study-completed") != "true":
        logger.info(f"[Pages] Attempt to access finish without completing post-study")
        return RedirectResponse(url="/post-study", status_code=302)
    
    # Allow access to the page
    logger.info(f"[Pages] Serving page: {path}")
    response = serve_static_file(path)
    if not response:
        logger.warning(f"[Pages] File not found: {path}")
        return RedirectResponse(url="/", status_code=302)  # Redirect to home if page not found
    
    # Ensure the token is passed through in the response
    set_cookie(response, "study_token", study_token)
    return response 