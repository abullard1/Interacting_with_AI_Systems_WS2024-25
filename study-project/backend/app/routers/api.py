from fastapi import APIRouter, HTTPException, Request, Body
from fastapi.responses import JSONResponse
from typing import Dict, Any, Optional
import logging
from datetime import datetime, timezone
import requests
from pydantic import BaseModel, Field
from app.core.config import get_settings
from app.core.firebase import store_study_data, release_user_locks
import json

settings = get_settings()
router = APIRouter()
logger = logging.getLogger(__name__)

class BugReport(BaseModel):
    description: str = Field(..., description="Description of the bug")
    page: str = Field(..., description="Page where the bug was encountered")
    studyToken: Optional[str] = Field(None, description="User's study token")
    userAgent: Optional[str] = Field(None, description="User agent string")

@router.post("/submit-study")
async def submit_study(request: Request):
    user_token = request.cookies.get("study_token")
    if not user_token:
        logger.error("[DEBUG] Missing study token in request cookies")
        raise HTTPException(status_code=403, detail="Missing study token")

    logger.info(f"[DEBUG] Processing study submission for user token: {user_token}")
    
    data = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "study_token": user_token
    }

    try:
        logger.info(f"[DEBUG] Calling store_study_data for user {user_token}")
        await store_study_data(data)
        logger.info(f"[DEBUG] Successfully completed store_study_data for user {user_token}")
        return {"status": "success", "message": "Study data submitted successfully"}
    except ValueError as ve:
        logger.error(f"[Submit Study] Value Error: {str(ve)}")
        
        try:
            logger.info(f"[DEBUG] Attempting direct lock release after store_study_data failure")
            await release_user_locks(user_token)
            logger.info(f"[Submit Study] Released locks for user {user_token} despite data storage error")
            
            if "feedback directory" in str(ve).lower():
                logger.info(f"[Submit Study] Ignoring feedback directory error and continuing")
                return {"status": "partial_success", "message": "Study completed but feedback data not stored"}
        except Exception as lock_error:
            logger.error(f"[Submit Study] Error releasing locks: {str(lock_error)}")
            
        raise HTTPException(status_code=500, detail=f"Error processing feedback data: {str(ve)}")
    except json.JSONDecodeError as je:
        # Handle JSON parsing errors specifically
        logger.error(f"[Submit Study] JSON Decode Error: {str(je)}")
        
        # Try to release locks even if JSON parsing fails
        try:
            logger.info(f"[DEBUG] Attempting lock release after JSON parsing failure")
            await release_user_locks(user_token)
            logger.info(f"[Submit Study] Released locks for user {user_token} despite JSON parsing error")
            return {"status": "partial_success", "message": "Study completed, but some feedback data could not be processed"}
        except Exception as lock_error:
            logger.error(f"[Submit Study] Error releasing locks: {str(lock_error)}")
            
        raise HTTPException(status_code=500, detail=f"Error parsing feedback data: {str(je)}")
    except Exception as e:
        logger.error(f"[Submit Study] Error: {str(e)}")
        
        # Even if storing data fails, try to release the locks
        locks_released = False
        try:
            logger.info(f"[DEBUG] Attempting direct lock release after store_study_data failure")
            await release_user_locks(user_token)
            logger.info(f"[Submit Study] Released locks for user {user_token} despite data storage error")
            locks_released = True
        except Exception as lock_error:
            logger.error(f"[Submit Study] Error releasing locks: {str(lock_error)}")
            
        error_detail = "Internal server error while storing study data"
        if locks_released:
            error_detail += " (locks were successfully released)"
        else:
            error_detail += " (locks could not be released)"
            
        raise HTTPException(status_code=500, detail=error_detail)

@router.get("/get-study-token")
async def get_study_token(request: Request):
    return {"study_token": request.cookies.get("study_token")}

@router.post("/report-bug")
async def report_bug(report: BugReport):
    try:
        email_subject = f"Bug Report from {report.page}"
        email_body = f"""
        Bug Report Details:
        -------------------
        Page: {report.page}
        Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        
        Description:
        {report.description}
        
        User Information:
        -----------------
        Study Token: {report.studyToken or 'Not provided'}
        User Agent: {report.userAgent or 'Not provided'}
        """
        
        logger.info(f"Bug report received from page: {report.page}")
        
        # Debug logging for Mailgun configuration
        logger.info(f"Mailgun API Key present: {bool(settings.MAILGUN_API_KEY)}")
        logger.info(f"Mailgun Domain present: {bool(settings.MAILGUN_DOMAIN)}")
        logger.info(f"Recipient Email present: {bool(settings.RECIPIENT_EMAIL)}")
        logger.info(f"Email config complete: {settings.email_config_complete}")
        
        if settings.email_config_complete:
            logger.info(f"Attempting to send email to {settings.RECIPIENT_EMAIL}")
            response = requests.post(
                f"https://api.mailgun.net/v3/{settings.MAILGUN_DOMAIN}/messages",
                auth=("api", settings.MAILGUN_API_KEY),
                data={
                    "from": f"Bug Reporter <mailgun@{settings.MAILGUN_DOMAIN}>",
                    "to": [settings.RECIPIENT_EMAIL],
                    "subject": email_subject,
                    "text": email_body
                }
            )
            if response.status_code != 200:
                logger.error(f"Mailgun API error: {response.status_code}, Response: {response.text}")
            else:
                logger.info("Email sent successfully")
        else:
            logger.warning("Email not sent: Missing Mailgun configuration values")
        
        return {"status": "success", "message": "Bug report submitted successfully"}
    except Exception as e:
        logger.error(f"Error processing bug report: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to process bug report")