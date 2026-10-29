from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified
import copy
from app import models, schemas
from app.core.database import get_db
from app.core.security import get_current_user
from app.services.ai_service import AIService
from app.services.behavior_analyzer import BehaviorAnalyzer

router = APIRouter(prefix="/interviews", tags=["AI Mock Interviews"])

@router.post("/start", response_model=schemas.InterviewStartResponse)
def start_interview(
    req: schemas.InterviewStartRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    jd_text = req.job_description.strip() if req.job_description else ""
    exp_lvl = req.experience_level or "Fresher"
    domain = req.topic_domain or "AIML"
    init_diff = "Easy" if exp_lvl.lower() in ["fresher", "entry level", "student", "internship", "junior"] else "Medium"
    
    # Initialize first question tailored to Role, Fresher/Experienced, and Topic Domain
    first_question = AIService.generate_interview_question(
        role=req.target_role,
        interview_type=req.interview_type,
        history=[],
        job_description=jd_text,
        experience_level=exp_lvl,
        topic_domain=domain,
        current_difficulty=init_diff
    )
    
    transcript_init = [
        {"role": "interviewer", "text": first_question}
    ]
    
    initial_feedback = {
        "job_description": jd_text,
        "turns_evaluation": [],
        "experience_level": exp_lvl,
        "topic_domain": domain,
        "current_difficulty": init_diff
    }
    
    db_interview = models.MockInterview(
        user_id=current_user.id,
        target_role=req.target_role,
        experience_level=exp_lvl,
        interview_type=req.interview_type,
        transcript=transcript_init,
        feedback=initial_feedback,
        behavior_scores={"telemetry_log": []}
    )
    db.add(db_interview)
    db.commit()
    db.refresh(db_interview)
    
    return schemas.InterviewStartResponse(
        interview_id=db_interview.id,
        first_question=first_question,
        speech_text=first_question,
        difficulty=init_diff
    )

@router.post("/{interview_id}/answer", response_model=schemas.InterviewMessageResponse)
def submit_interview_answer(
    interview_id: int,
    req: schemas.InterviewMessageRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    db_interview = db.query(models.MockInterview)\
        .filter(models.MockInterview.id == interview_id, models.MockInterview.user_id == current_user.id)\
        .first()
        
    if not db_interview:
        raise HTTPException(status_code=404, detail="Interview session not found")
        
    # Append candidate's answer to transcript
    history = list(db_interview.transcript)
    history.append({"role": "candidate", "text": req.answer})
    
    # Save facial expressions telemetry if sent
    telemetry = list(db_interview.behavior_scores.get("telemetry_log", []))
    frame_analysis = BehaviorAnalyzer.analyze_frame_telemetry(
        attention=req.attention_metric if req.attention_metric is not None else 0.85,
        smile=req.smile_metric if req.smile_metric is not None else 0.5,
        stress=req.stress_metric if req.stress_metric is not None else 0.2,
        eye_contact=req.eye_contact_metric if req.eye_contact_metric is not None else 0.85
    )
    frame_analysis["wpm"] = req.wpm_metric or 135
    frame_analysis["filler_words"] = req.filler_words_count or 0
    telemetry.append(frame_analysis)
    
    feedback_store = dict(db_interview.feedback or {})
    jd_text = feedback_store.get("job_description", "")
    exp_lvl = db_interview.experience_level or "Fresher"
    domain = req.topic_domain or feedback_store.get("topic_domain", "AIML")
    cur_diff = req.current_difficulty or feedback_store.get("current_difficulty", "Easy")
    
    # Evaluate this specific turn (check correctness, provide immediate AI correction if wrong, and adapt difficulty)
    turn_eval = AIService.evaluate_interview_turn(
        role=db_interview.target_role,
        interview_type=db_interview.interview_type,
        history=history,
        job_description=jd_text,
        experience_level=exp_lvl,
        topic_domain=domain,
        current_difficulty=cur_diff
    )
    
    new_diff = turn_eval.get("difficulty") or cur_diff
    feedback_store["current_difficulty"] = new_diff
    
    turns_eval_list = list(feedback_store.get("turns_evaluation", []))
    turns_eval_list.append(turn_eval)
    feedback_store["turns_evaluation"] = turns_eval_list
    
    # Check interview length. Standard interview has 5 question exchanges.
    interviewer_qs = [h for h in history if h.get("role") == "interviewer"]
    
    if len(interviewer_qs) >= 5:
        # Finish the interview
        db_interview.transcript = history
        db_interview.behavior_scores = {
            "telemetry_log": telemetry,
            "aggregate": BehaviorAnalyzer.get_aggregate_behavior_report(telemetry)
        }
        
        # Trigger final AI evaluation on history
        eval_report = AIService.analyze_interview(
            role=db_interview.target_role,
            interview_type=db_interview.interview_type,
            history=history,
            job_description=jd_text
        )
        
        db_interview.technical_score = eval_report.get("technical_score", 75)
        db_interview.communication_score = eval_report.get("communication_score", 80)
        db_interview.confidence_score = eval_report.get("confidence_score", 82)
        db_interview.problem_solving_score = eval_report.get("problem_solving_score", 76)
        db_interview.leadership_score = eval_report.get("leadership_score", 72)
        db_interview.overall_score = eval_report.get("overall_score", 78)
        
        final_fb = eval_report.get("feedback", {})
        final_fb["job_description"] = jd_text
        final_fb["turns_evaluation"] = turns_eval_list
        db_interview.feedback = final_fb
        
        flag_modified(db_interview, "transcript")
        flag_modified(db_interview, "behavior_scores")
        flag_modified(db_interview, "feedback")
        
        # Award XP for interview completion
        current_user.xp += 300
        
        # Notify
        db.add(models.Notification(
            user_id=current_user.id,
            title="Mock Placement Interview Completed! (+300 XP)",
            message=f"Completed {db_interview.interview_type} mock interview for '{db_interview.target_role}'. Overall Score: {db_interview.overall_score}/100.",
            type="Interview"
        ))
        
        db.commit()
        
        closing_speech = "Thank you! That concludes our mock placement interview. Your comprehensive score report and AI analysis have been compiled."
        
        return schemas.InterviewMessageResponse(
            next_question=None,
            is_finished=True,
            ai_immediate_feedback=turn_eval.get("ai_immediate_feedback"),
            is_correct=turn_eval.get("is_correct", True),
            ai_correction=turn_eval.get("ai_correction"),
            ideal_answer=turn_eval.get("ideal_answer"),
            speech_text_to_speak=f"{turn_eval.get('speech_text_to_speak', '')} {closing_speech}".strip(),
            current_live_score=db_interview.overall_score,
            confidence_metric=db_interview.confidence_score,
            difficulty=new_diff,
            difficulty_change=turn_eval.get("difficulty_change", "same")
        )
    else:
        next_q = turn_eval.get("next_question") or AIService.generate_interview_question(
            role=db_interview.target_role,
            interview_type=db_interview.interview_type,
            history=history,
            job_description=jd_text,
            experience_level=exp_lvl,
            topic_domain=domain,
            current_difficulty=new_diff
        )
        
        history.append({"role": "interviewer", "text": next_q})
        
        db_interview.transcript = history
        db_interview.feedback = feedback_store
        db_interview.behavior_scores = {"telemetry_log": telemetry}
        flag_modified(db_interview, "transcript")
        flag_modified(db_interview, "feedback")
        flag_modified(db_interview, "behavior_scores")
        db.commit()
        
        return schemas.InterviewMessageResponse(
            next_question=next_q,
            is_finished=False,
            ai_immediate_feedback=turn_eval.get("ai_immediate_feedback"),
            is_correct=turn_eval.get("is_correct", True),
            ai_correction=turn_eval.get("ai_correction"),
            ideal_answer=turn_eval.get("ideal_answer"),
            speech_text_to_speak=turn_eval.get("speech_text_to_speak") or next_q,
            current_live_score=turn_eval.get("score_on_turn", 78),
            confidence_metric=turn_eval.get("confidence_estimate", 82),
            difficulty=new_diff,
            difficulty_change=turn_eval.get("difficulty_change", "same")
        )

@router.get("/{interview_id}/feedback", response_model=schemas.InterviewFeedbackResponse)
def get_interview_feedback(
    interview_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    interview = db.query(models.MockInterview)\
        .filter(models.MockInterview.id == interview_id, models.MockInterview.user_id == current_user.id)\
        .first()
        
    if not interview:
        raise HTTPException(status_code=404, detail="Interview session not found")
        
    if not interview.feedback:
        raise HTTPException(status_code=400, detail="Interview feedback is still generating.")
        
    return interview

@router.get("/latest", response_model=schemas.InterviewFeedbackResponse)
def get_latest_interview(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    interview = db.query(models.MockInterview)\
        .filter(models.MockInterview.user_id == current_user.id, models.MockInterview.overall_score.isnot(None))\
        .order_by(models.MockInterview.created_at.desc())\
        .first()
        
    if not interview:
        raise HTTPException(status_code=404, detail="No completed mock interview found yet")
        
    return interview

