from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session
from app import schemas, models
from app.core.database import get_db
from app.services.ai_service import AIService
from typing import Optional

router = APIRouter(prefix="/mentor", tags=["AI Career Mentor"])

@router.post("/chat", response_model=schemas.MentorMessageResponse)
def mentor_chat(
    req: schemas.MentorMessageRequest,
    request: Request,
    db: Session = Depends(get_db)
):
    # Retrieve AI response (resilient to guest, demo, local or authenticated users)
    res = AIService.get_career_advice(req.message, req.history)
    
    return schemas.MentorMessageResponse(
        response=res.get("response", "How can I help you today?"),
        suggestions=res.get("suggestions", ["How to raise my ATS score?", "Help me with coding prep"])
    )
