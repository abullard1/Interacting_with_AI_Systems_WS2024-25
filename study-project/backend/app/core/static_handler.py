# File: backend/app/core/static_handler.py
import os
import logging
from fastapi.responses import FileResponse
from app.core.config import get_settings
from typing import Optional

logger = logging.getLogger(__name__)
settings = get_settings()

def serve_static_file(path: str) -> Optional[FileResponse]:
    """
    Serves a file from the configured static directory, handling missing files and setting cache headers.
    
    Attempts to find the file at the given path. If not found, it tries appending '.html'.
    
    Returns:
        FileResponse with appropriate cache headers if found, otherwise None.
    """
    # Construct full path using base directory from settings
    file_path = f"{settings.STATIC_FILES_DIR}/{path}"
    logger.debug(f"[Static File] Attempting to serve: {file_path}")
    
    # Check if the requested path directly points to a file
    if not os.path.isfile(file_path):
        # If not found, check if adding '.html' resolves to a file (common for clean URLs)
        html_path = f"{file_path}.html"
        if os.path.isfile(html_path):
            file_path = html_path # Update path to the found .html file
            logger.debug(f"[Static File] Found as HTML: {file_path}")
        else:
            # File not found at original path or with .html appended
            logger.warning(f"[Static File] Not found: {file_path} (or .html)")
            return None
        
    try:
        response = FileResponse(file_path)
        
        # Apply Cache-Control based on file extension
        if any(file_path.endswith(ext) for ext in ['.html', '.htm']):
            response.headers["Cache-Control"] = "no-store" # Never cache HTML
        elif any(file_path.endswith(ext) for ext in ['.js', '.css']):
            response.headers["Cache-Control"] = "public, max-age=3600" # Cache JS/CSS for 1 hour
        elif any(file_path.endswith(ext) for ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp']):
            response.headers["Cache-Control"] = "public, max-age=86400" # Cache images for 1 day
        else:
            # Default: no cache for other file types
            response.headers["Cache-Control"] = "no-store"
            
        logger.info(f"[Static File] Serving: {file_path} with Cache-Control: {response.headers.get('Cache-Control')}")
        return response
    except Exception as e:
        # Handle potential errors during file access or response creation
        logger.error(f"[Static File] Error serving {file_path}: {str(e)}")
        return None