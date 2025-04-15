# File: backend/app/core/config.py
from pydantic_settings import BaseSettings
from typing import List
import os
from dotenv import load_dotenv

# Construct the absolute path to the .env file located three directories up
env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), '.env')

# Load environment variables from the specified .env file
load_dotenv(dotenv_path=env_path)

class Settings(BaseSettings):
    PROJECT_NAME: str = "AI Interaction Study"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api"
    
    # Detect current environment (e.g., "development", "production")
    # We actually didn't fully implement different environments, but we kept the code for future use
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    
    # Configure Cross-Origin Resource Sharing (CORS) allowed origins
    CORS_ORIGINS: List[str] = ["*"] # Allows all origins - adjust for production
    
    # Location of static frontend files
    STATIC_FILES_DIR: str = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "frontend", "dist")
    
    # Define cookie expiration times
    COOKIE_EXPIRY: dict = {
        "session": None,  # Expires when browser closes
        "persistent": 30 * 24 * 60 * 60  # 30 days
    }
    
    # Enable secure cookies (HTTPS only) in non-development environments
    COOKIE_SECURE: bool = os.getenv("ENVIRONMENT", "development") != "development"
    
    # Path to Firebase service account credentials
    FIREBASE_CREDENTIALS_PATH: str = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "firebase-credentials.json")
    
    # Mailgun configuration for sending emails (e.g., bug reports)
    MAILGUN_API_KEY: str = os.getenv("MAILGUN_API_KEY", "")
    MAILGUN_DOMAIN: str = os.getenv("MAILGUN_DOMAIN", "")
    RECIPIENT_EMAIL: str = os.getenv("RECIPIENT_EMAIL", "")

    @property
    def email_config_complete(self) -> bool:
        """Verify if all necessary Mailgun settings are provided."""
        return bool(self.MAILGUN_API_KEY and self.MAILGUN_DOMAIN and self.RECIPIENT_EMAIL)

    class Config:
        case_sensitive = True

# Singleton pattern for settings instance
_settings = None

def get_settings() -> Settings:
    """Retrieve the application settings instance."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
