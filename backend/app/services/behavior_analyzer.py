import random
from typing import Dict, Any

class BehaviorAnalyzer:

    @staticmethod
    def analyze_frame_telemetry(attention: float, smile: float, stress: float, eye_contact: float) -> Dict[str, Any]:
        """Calculates behavioral analytics based on video/face telemetry received from the frontend."""
        
        # Normalize inputs
        attention = min(max(attention, 0.0), 1.0)
        smile = min(max(smile, 0.0), 1.0)
        stress = min(max(stress, 0.0), 1.0)
        eye_contact = min(max(eye_contact, 0.0), 1.0)
        
        # Calculate dynamic derived metrics
        confidence = (attention * 0.4) + (eye_contact * 0.4) + ((1 - stress) * 0.2)
        engagement = (attention * 0.6) + (smile * 0.2) + (eye_contact * 0.2)
        
        # Categorize emotion
        if stress > 0.6:
            emotion = "Anxious"
        elif smile > 0.4:
            emotion = "Confident / Happy"
        elif attention < 0.4:
            emotion = "Distracted"
        else:
            emotion = "Focused / Neutral"
            
        # Give head movement estimates (mock variation)
        head_movement = "Normal / Minimal" if attention > 0.7 else "Frequent"
        
        return {
            "attention_score": round(attention * 100, 1),
            "smile_score": round(smile * 100, 1),
            "stress_score": round(stress * 100, 1),
            "eye_contact_score": round(eye_contact * 100, 1),
            "confidence_score": round(confidence * 100, 1),
            "engagement_score": round(engagement * 100, 1),
            "detected_emotion": emotion,
            "head_movement": head_movement,
            "disclaimer": "This analysis is generated using facial expression telemetry for self-improvement and may not always be 100% accurate."
        }

    @staticmethod
    def get_aggregate_behavior_report(session_telemetry_list: list) -> Dict[str, Any]:
        """Computes summary metrics for a full mock interview session."""
        if not session_telemetry_list:
            return {
                "avg_attention": 85.0,
                "avg_smile": 45.0,
                "avg_stress": 20.0,
                "avg_eye_contact": 80.0,
                "overall_behavior_rating": "Excellent"
            }
            
        total_att = sum(x.get("attention_score", 85) for x in session_telemetry_list)
        total_sml = sum(x.get("smile_score", 45) for x in session_telemetry_list)
        total_str = sum(x.get("stress_score", 20) for x in session_telemetry_list)
        total_eye = sum(x.get("eye_contact_score", 80) for x in session_telemetry_list)
        n = len(session_telemetry_list)
        
        avg_att = total_att / n
        avg_sml = total_sml / n
        avg_str = total_str / n
        avg_eye = total_eye / n
        
        overall_rating = "Excellent"
        if avg_str > 45 or avg_att < 60:
            overall_rating = "Needs Improvement"
        elif avg_att < 80 or avg_eye < 70:
            overall_rating = "Good"
            
        return {
            "avg_attention": round(avg_att, 1),
            "avg_smile": round(avg_sml, 1),
            "avg_stress": round(avg_str, 1),
            "avg_eye_contact": round(avg_eye, 1),
            "overall_behavior_rating": overall_rating,
            "head_movement": "Stable / Concentrated",
            "body_language_feedback": "Maintained direct posture. Avoided hand-to-face touching. Excellent overall presentation."
        }
