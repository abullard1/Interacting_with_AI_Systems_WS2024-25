import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import firebase_admin
from firebase_admin import credentials

from app.core.config import get_settings
from app.core.middleware import SecurityHeadersMiddleware, SessionTrackingMiddleware
from app.routers import api, pages

logging.basicConfig(level=logging.INFO)
settings = get_settings()

firebase_admin.initialize_app(credentials.Certificate(settings.FIREBASE_CREDENTIALS_PATH))

# Initialize FastAPI
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
)

# Add middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(SessionTrackingMiddleware)

# Add routers
app.include_router(api.router, prefix=settings.API_V1_STR)
app.include_router(pages.router)

# Mount static files - single mount point for all static content
app.mount("/", StaticFiles(directory=settings.STATIC_FILES_DIR, html=True), name="static") 