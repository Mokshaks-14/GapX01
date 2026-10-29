from fastapi import APIRouter, Depends, HTTPException, Response, Query, status
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified
from typing import Optional, Dict, Any
from jose import jwt, JWTError
import copy
from app import models, schemas
from app.core.database import get_db
from app.core.security import get_current_user
from app.core.config import settings
from app.services.ai_service import AIService
from app.services.pdf_generator import PDFNotesGenerator
from datetime import datetime, timedelta

router = APIRouter(prefix="/roadmaps", tags=["AI Roadmap Module"])

@router.post("/generate", response_model=schemas.RoadmapResponse)
def generate_roadmap(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    if not current_user.target_roles:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Please select target job roles first."
        )
        
    primary_role = current_user.target_roles[0]
    
    # Generate roadmap stages using AI service
    stages = AIService.generate_roadmap(
        role=primary_role,
        current_skills=current_user.skills or [],
        experience=current_user.experience_level or "Beginner"
    )
    
    # Ensure structured IDs and checkbox states (is_completed = False)
    for s_idx, stage in enumerate(stages, 1):
        if not stage.get("id"):
            stage["id"] = s_idx
        for t_idx, topic in enumerate(stage.get("topics", []), 1):
            if not topic.get("id"):
                topic["id"] = stage["id"] * 100 + t_idx
            topic["is_completed"] = False
            
    # Calculate estimated completion date (e.g. 2 months from now)
    est_date = (datetime.now() + timedelta(days=60)).strftime("%d %B, %Y")
    
    # Save/Overwrite user's roadmap for this role
    db_roadmap = db.query(models.Roadmap)\
        .filter(models.Roadmap.user_id == current_user.id, models.Roadmap.target_role == primary_role)\
        .first()
        
    if db_roadmap:
        db_roadmap.stages_data = copy.deepcopy(stages)
        db_roadmap.progress_percentage = 0.0
        db_roadmap.estimated_completion_date = est_date
        flag_modified(db_roadmap, "stages_data")
    else:
        db_roadmap = models.Roadmap(
            user_id=current_user.id,
            target_role=primary_role,
            stages_data=copy.deepcopy(stages),
            progress_percentage=0.0,
            estimated_completion_date=est_date
        )
        db.add(db_roadmap)
        
    # Award XP
    current_user.xp += 100
    current_user.level = max(1, (current_user.xp // 500) + 1)
    notif = models.Notification(
        user_id=current_user.id,
        title="Custom AI Roadmap Generated! (+100 XP)",
        message=f"We designed a personalized 8-Stage preparation path targeting the '{primary_role}' job role. Let's start learning!",
        type="Roadmap"
    )
    db.add(notif)
    
    db.commit()
    db.refresh(db_roadmap)
    return db_roadmap

@router.get("/current", response_model=schemas.RoadmapResponse)
def get_current_roadmap(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    roadmap = db.query(models.Roadmap)\
        .filter(models.Roadmap.user_id == current_user.id)\
        .order_by(models.Roadmap.created_at.desc())\
        .first()
        
    if not roadmap:
        if current_user.target_roles:
            return generate_roadmap(db, current_user)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No roadmap generated yet. Complete onboarding first."
        )
    return roadmap

@router.post("/toggle-topic", response_model=schemas.RoadmapResponse)
def toggle_topic(
    request: schemas.ToggleTopicRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    roadmap = db.query(models.Roadmap)\
        .filter(models.Roadmap.user_id == current_user.id)\
        .order_by(models.Roadmap.created_at.desc())\
        .first()
        
    if not roadmap:
        raise HTTPException(status_code=404, detail="Roadmap not found")
        
    stages = copy.deepcopy(roadmap.stages_data)
    topic_found = False
    
    req_stage_str = str(request.stage_id).strip()
    req_topic_str = str(request.topic_id).strip()
    target_state = bool(request.is_completed)
    
    # 1. First pass: try matching both stage ID and topic ID
    for stage in stages:
        if str(stage.get("id")).strip() == req_stage_str:
            for topic in stage.get("topics", []):
                if str(topic.get("id")).strip() == req_topic_str:
                    topic["is_completed"] = target_state
                    topic_found = True
                    break
            if topic_found:
                break
                
    # 2. Fallback pass: match topic ID across any stage
    if not topic_found:
        for stage in stages:
            for topic in stage.get("topics", []):
                if str(topic.get("id")).strip() == req_topic_str:
                    topic["is_completed"] = target_state
                    topic_found = True
                    break
            if topic_found:
                break

    # Recalculate progress percentage
    total_topics = 0
    completed_topics = 0
    for s in stages:
        for t in s.get("topics", []):
            total_topics += 1
            if t.get("is_completed", False):
                completed_topics += 1
                
    if target_state:
        current_user.xp += 50
        new_level = (current_user.xp // 500) + 1
        if new_level > current_user.level:
            current_user.level = new_level
            lvl_notif = models.Notification(
                user_id=current_user.id,
                title=f"LEVELED UP! Level {new_level}",
                message=f"Congratulations! You reached Level {new_level} with {current_user.xp} XP. Keep coding!",
                type="Achievement"
            )
            db.add(lvl_notif)
    else:
        current_user.xp = max(0, current_user.xp - 50)
        current_user.level = max(1, (current_user.xp // 500) + 1)
        
    roadmap.stages_data = stages
    roadmap.progress_percentage = round((completed_topics / max(1, total_topics)) * 100, 1) if total_topics > 0 else 0.0
    flag_modified(roadmap, "stages_data")
    
    db.commit()
    db.refresh(roadmap)
    return roadmap

@router.get("/notes/{stage_id}/{topic_id}")
def get_topic_notes(
    stage_id: str,
    topic_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Returns structured JSON study notes for in-app reading."""
    roadmap = db.query(models.Roadmap)\
        .filter(models.Roadmap.user_id == current_user.id)\
        .order_by(models.Roadmap.created_at.desc())\
        .first()
        
    stage_title = f"Stage {stage_id}"
    topic_title = f"Topic {topic_id}"
    target_role = roadmap.target_role if roadmap else (current_user.target_roles[0] if current_user.target_roles else "Software Engineer")
    
    if roadmap and roadmap.stages_data:
        for s in roadmap.stages_data:
            if str(s.get("id")).strip() == str(stage_id).strip():
                stage_title = s.get("title", stage_title)
                for t in s.get("topics", []):
                    if str(t.get("id")).strip() == str(topic_id).strip():
                        topic_title = t.get("title", topic_title)
                        break
            # Also check across all topics if stage didn't match
            for t in s.get("topics", []):
                if str(t.get("id")).strip() == str(topic_id).strip():
                    topic_title = t.get("title", topic_title)
                    stage_title = s.get("title", stage_title)
                    break
                        
    notes = AIService.generate_topic_notes(
        topic_title=topic_title,
        stage_title=stage_title,
        role=target_role
    )
    return notes

@router.get("/notes-pdf/{stage_id}/{topic_id}")
def download_topic_notes(
    stage_id: str,
    topic_id: str,
    token: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """Compiles and streams a formatted academic ReportLab PDF of the topic study notes."""
    user = None
    if token:
        try:
            payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.ALGORITHM])
            user_id = payload.get("sub")
            if user_id:
                user = db.query(models.User).filter(models.User.id == int(user_id)).first()
        except Exception:
            pass
            
    if not user:
        user = db.query(models.User).first()
        
    if not user:
        raise HTTPException(status_code=401, detail="User authentication required")

    roadmap = db.query(models.Roadmap)\
        .filter(models.Roadmap.user_id == user.id)\
        .order_by(models.Roadmap.created_at.desc())\
        .first()
        
    stage_title = f"Stage {stage_id}"
    topic_title = f"Topic {topic_id}"
    target_role = roadmap.target_role if roadmap else (user.target_roles[0] if user.target_roles else "Software Engineer")
    
    if roadmap and roadmap.stages_data:
        for s in roadmap.stages_data:
            if str(s.get("id")).strip() == str(stage_id).strip():
                stage_title = s.get("title", stage_title)
                for t in s.get("topics", []):
                    if str(t.get("id")).strip() == str(topic_id).strip():
                        topic_title = t.get("title", topic_title)
                        break
            for t in s.get("topics", []):
                if str(t.get("id")).strip() == str(topic_id).strip():
                    topic_title = t.get("title", topic_title)
                    stage_title = s.get("title", stage_title)
                    break
                        
    notes = AIService.generate_topic_notes(
        topic_title=topic_title,
        stage_title=stage_title,
        role=target_role
    )
    
    pdf_buffer = PDFNotesGenerator.generate_notes_pdf(notes)
    
    clean_filename = "".join([c if c.isalnum() else "_" for c in topic_title])
    filename = f"GapX_AI_Notes_{clean_filename}.pdf"
    
    return Response(
        content=pdf_buffer.getvalue(),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename={filename}"
        }
    )
