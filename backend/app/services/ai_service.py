import json
import re
import logging
from typing import Dict, Any, List, Optional
from app.core.config import settings
from app.services.career_knowledge import CareerKnowledgeEngine
from app.services.resume_parser import ResumeEntityExtractor

logger = logging.getLogger(__name__)

# Try to initialize Gemini API
gemini_available = False
if settings.GEMINI_API_KEY:
    try:
        import google.generativeai as genai
        genai.configure(api_key=settings.GEMINI_API_KEY)
        gemini_available = True
        logger.info("Google Gemini initialized successfully.")
    except Exception as e:
        logger.warning(f"Failed to initialize Google Gemini: {e}")

# Try to initialize OpenAI API
openai_available = False
if settings.OPENAI_API_KEY:
    try:
        import openai
        openai.api_key = settings.OPENAI_API_KEY
        openai_available = True
        logger.info("OpenAI API initialized successfully.")
    except Exception as e:
        logger.warning(f"Failed to initialize OpenAI API: {e}")

class AIService:
    
    @staticmethod
    def _clean_and_parse_json(raw_text: str) -> Any:
        """Strips markdown code blocks and safely decodes JSON from AI outputs."""
        if not raw_text:
            return {}
        text = raw_text.strip()
        if text.startswith("```json"):
            text = text[7:]
        elif text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        return json.loads(text.strip())

    @staticmethod
    def generate_roadmap(role: str, current_skills: List[str], experience: str) -> List[Dict[str, Any]]:
        """Generates a complete roadmap from basic to advanced."""
        prompt = f"""
        Generate a structured 8-stage learning roadmap for a user training to be a {role}.
        Their current skills: {', '.join(current_skills) if current_skills else 'None'}.
        Experience level: {experience}.
        
        Provide the response STRICTLY as a JSON array of stages. Each stage must contain:
        - id: (integer, 1-8)
        - title: (string)
        - description: (string)
        - topics: List of topics, each containing:
            - id: (integer)
            - title: (string)
            - description: (string)
            - estimated_hours: (integer)
            - difficulty: (string: Easy, Medium, Hard)
            - resources: List of resources, each containing:
                - type: (string: Documentation, YouTube, GitHub, Article)
                - title: (string)
                - url: (string)
        """
        
        if gemini_available:
            try:
                model = genai.GenerativeModel('gemini-1.5-flash', generation_config={"response_mime_type": "application/json"})
                response = model.generate_content(prompt)
                parsed = AIService._clean_and_parse_json(response.text)
                if isinstance(parsed, list) and len(parsed) >= 6:
                    return parsed
                if isinstance(parsed, dict) and "stages" in parsed and isinstance(parsed["stages"], list) and len(parsed["stages"]) >= 6:
                    return parsed["stages"]
            except Exception as e:
                logger.error(f"Gemini roadmap gen error: {e}. Using local generator.")
        
        # Local Rule-based Generator (contextual and high-quality mock data with all 8 complete stages)
        return AIService._mock_roadmap_generator(role, current_skills)

    @staticmethod
    def analyze_resume(resume_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyzes structured or manual resume data against preferred roles and skills."""
        if not resume_data:
            resume_data = {}

        raw_text = str(resume_data.get("extracted_text") or "")
        target_roles = resume_data.get("target_roles") or []
        if isinstance(target_roles, list) and len(target_roles) > 0 and target_roles[0]:
            primary_role = str(target_roles[0])
        else:
            primary_role = str(resume_data.get("headline") or "Software Engineer")

        # Extract structured entities from raw text & metadata
        entities = ResumeEntityExtractor.extract_text_entities(raw_text, resume_data)
        
        # Calculate dynamic ATS scores and personalized audit feedback
        audit_result = ResumeEntityExtractor.evaluate_and_audit(entities, primary_role)

        # Augment with Gemini if available
        if gemini_available:
            try:
                prompt = f"""
                You are an expert ATS screening system and Technical Recruiter for {primary_role} positions.
                Candidate Profile:
                - Name: {entities.get('name')}
                - Target Role: {primary_role}
                - Extracted Skills: {json.dumps(entities.get('skills_by_category'))}
                - Projects: {json.dumps(entities.get('projects'))}
                - Experience: {json.dumps(entities.get('experience'))}
                - Education: {json.dumps(entities.get('education'))}
                - Document Text: {raw_text[:2000]}

                Return a STRICT JSON response:
                {{
                    "ats_score": Integer (0-100),
                    "resume_score": Integer (0-100),
                    "strengths": list of 3-5 specific strengths referencing their actual projects and skills,
                    "weaknesses": list of 3-5 specific weaknesses/gaps for {primary_role},
                    "missing_skills": list of 3-5 critical missing skills,
                    "missing_keywords": list of 6-8 industry keywords to add,
                    "suggestions": list of 3-4 specific actionable recommendations,
                    "readiness_level": string ('Placement-Ready', 'Competitive Candidate', 'Intermediate / Developing', 'Needs Refinement')
                }}
                """
                for model_name in ['gemini-1.5-flash', 'gemini-2.0-flash', 'gemini-1.5-pro', 'gemini-pro']:
                    try:
                        model = genai.GenerativeModel(model_name, generation_config={"response_mime_type": "application/json"})
                        response = model.generate_content(prompt)
                        parsed = AIService._clean_and_parse_json(response.text)
                        if isinstance(parsed, dict) and "ats_score" in parsed:
                            audit_result["ats_score"] = int(min(max(parsed.get("ats_score", audit_result["ats_score"]), 0), 100))
                            audit_result["resume_score"] = int(min(max(parsed.get("resume_score", audit_result["resume_score"]), 0), 100))
                            if parsed.get("strengths"): audit_result["strengths"] = list(parsed["strengths"])
                            if parsed.get("weaknesses"): audit_result["weaknesses"] = list(parsed["weaknesses"])
                            if parsed.get("missing_skills"): audit_result["missing_skills"] = list(parsed["missing_skills"])
                            if parsed.get("missing_keywords"): audit_result["missing_keywords"] = list(parsed["missing_keywords"])
                            if parsed.get("suggestions"): audit_result["suggestions"] = list(parsed["suggestions"])
                            if parsed.get("readiness_level"): audit_result["readiness_level"] = str(parsed["readiness_level"])
                            break
                    except Exception as me:
                        logger.debug(f"Gemini resume model {model_name} failed: {me}")
            except Exception as e:
                logger.error(f"Gemini resume analysis error: {e}. Using local analyzer.")

        return audit_result

    @staticmethod
    def generate_topic_notes(topic_title: str, stage_title: str, role: str) -> Dict[str, Any]:
        """Generates exhaustive, placement-level academic study notes for a specific roadmap topic."""
        prompt = f"""
        You are a distinguished Computer Science Professor and Principal Staff Engineer at a Tier-1 Tech Company.
        Generate comprehensive, exhaustive, placement-level academic study notes for the topic '{topic_title}' in the context of learning '{stage_title}' for a '{role}' position.
        
        The notes must be in-depth from the basic fundamental definition to advanced architecture and production code implementation.
        
        Provide the response STRICTLY as a JSON object with this exact structure:
        {{
            "title": "{topic_title}",
            "stage": "{stage_title}",
            "role": "{role}",
            "executive_summary": "Thorough, academic definition explaining what this concept is, why it was created, and its core foundational importance in computer science and software systems.",
            "internals_and_architecture": "Deep low-level technical explanation covering memory layout (stack/heap), pointer mechanics, runtime execution flow, algorithmic principles, and system interactions.",
            "key_concepts": [
                {{"name": "Concept Name 1", "explanation": "Detailed explanation with theory, mechanisms, and rules."}},
                {{"name": "Concept Name 2", "explanation": "Detailed explanation with theory, mechanisms, and rules."}},
                {{"name": "Concept Name 3", "explanation": "Detailed explanation with theory, mechanisms, and rules."}},
                {{"name": "Concept Name 4", "explanation": "Detailed explanation with theory, mechanisms, and rules."}}
            ],
            "complexity_analysis": [
                {{"operation": "Primary Operation 1 (e.g. Access / Insert / Query)", "time_complexity": "O(...)", "space_complexity": "O(...)", "explanation": "Why this complexity occurs and trade-offs."}},
                {{"operation": "Primary Operation 2 (e.g. Search / Update / Traversal)", "time_complexity": "O(...)", "space_complexity": "O(...)", "explanation": "Why this complexity occurs and trade-offs."}},
                {{"operation": "Worst Case / Edge Scenario", "time_complexity": "O(...)", "space_complexity": "O(...)", "explanation": "Worst case conditions and mitigations."}}
            ],
            "code_example": "# Complete, production-ready, thoroughly documented code example in Python, JavaScript, C++, or Java illustrating the concept with realistic data structures, error handling, and complexity comments.",
            "industry_use_cases": [
                {{"company": "Google / Meta / Netflix / Amazon", "use_case": "Specific real-world system use case.", "architecture_impact": "How this solves latency, scalability, or consistency."}},
                {{"company": "High-Throughput Distributed System", "use_case": "Specific real-world system use case.", "architecture_impact": "How this solves latency, scalability, or consistency."}}
            ],
            "common_pitfalls": [
                "Detailed pitfall 1: Subtle bug, memory leak, or off-by-one error and how to avoid it.",
                "Detailed pitfall 2: Concurrency or scale issue and how to resolve it.",
                "Detailed pitfall 3: Antipattern in production code."
            ],
            "interview_questions": [
                {{"question": "Deep technical interview question 1?", "ideal_answer": "Complete, structured model answer demonstrating mastery.", "difficulty": "Medium"}},
                {{"question": "Deep technical interview question 2?", "ideal_answer": "Complete, structured model answer demonstrating mastery.", "difficulty": "Hard"}},
                {{"question": "System design / trade-off question 3?", "ideal_answer": "Complete, structured model answer demonstrating mastery.", "difficulty": "Medium"}},
                {{"question": "Low-level implementation question 4?", "ideal_answer": "Complete, structured model answer demonstrating mastery.", "difficulty": "Hard"}},
                {{"question": "Edge case / optimization question 5?", "ideal_answer": "Complete, structured model answer demonstrating mastery.", "difficulty": "Medium"}}
            ],
            "best_practices": [
                "Actionable production engineering rule 1",
                "Actionable production engineering rule 2",
                "Actionable production engineering rule 3",
                "Actionable production engineering rule 4"
            ],
            "summary": "Concise, punchy executive summary and revision checklist for the student before technical interviews."
        }}
        """
        
        if gemini_available:
            try:
                model = genai.GenerativeModel('gemini-1.5-flash', generation_config={"response_mime_type": "application/json"})
                response = model.generate_content(prompt)
                data = AIService._clean_and_parse_json(response.text)
                # Ensure all fields are normalized
                if "introduction" in data and "executive_summary" not in data:
                    data["executive_summary"] = data["introduction"]
                return data
            except Exception as e:
                logger.error(f"Gemini notes generation error: {e}. Using local generator.")
                
        return AIService._mock_topic_notes(topic_title, stage_title, role)

    @staticmethod
    def generate_interview_question(
        role: str,
        interview_type: str,
        history: List[Dict[str, str]],
        job_description: Optional[str] = None,
        experience_level: Optional[str] = "Fresher",
        topic_domain: Optional[str] = "AIML",
        current_difficulty: Optional[str] = "Easy"
    ) -> str:
        """Generates the interview question dynamically based on role, experience (Freshers vs Experienced), AI/ML & technical domain, and adaptive difficulty."""
        history_str = ""
        for h in (history or [])[-8:]:
            history_str += f"{h['role'].capitalize()}: {h['text']}\n"
            
        jd_context = f"\nTarget Job Description / Tech Stack Requirements:\n{job_description}\n" if job_description else ""
        is_fresher = (experience_level or "Fresher").lower() in ["fresher", "entry level", "student", "internship", "junior"]
        
        prompt = f"""
        You are Dr. Alex Vance, a Principal Engineer conducting a live video placement interview.
        Candidate Role: {role}
        Interview Format: {interview_type}
        Experience Profile: {"Fresher / College Graduate" if is_fresher else "Experienced Software Engineer"}
        Topic Focus: {topic_domain or "AIML (Artificial Intelligence & Machine Learning)"}
        Current Difficulty Level: {current_difficulty or "Easy"}
        {jd_context}
        Previous Conversation Transcript:
        {history_str if history_str else "(Interview just starting - Turn 1)"}

        Task: Generate the next single spoken interview question for the candidate.
        CRITICAL RULES:
        1. FRESHER-FRIENDLY & TOPIC RELEVANCE:
           - If candidate is a Fresher/Student, DO NOT assume past corporate job experience. Focus on college/academic projects, CS core concepts, and modern AI/ML topics (Generative AI, LLMs, prompt engineering, supervised vs unsupervised learning, overfitting, neural networks, or foundational DSA).
        2. DYNAMIC ACTIVE LISTENING:
           - If this is a follow-up turn, directly reference and quote what they said in their previous answer.
        3. ADAPTIVE DIFFICULTY:
           - Difficulty is currently set to: {current_difficulty}.
           - If Easy: ask foundational concepts, intuitive mechanics, and basic definitions.
           - If Medium: ask about practical implementation, loss functions, RAG, embeddings, trade-offs, and algorithm flow.
           - If Hard: ask deep mathematical formulations, vanishing gradients, PEFT/LoRA, or high-concurrency failure recovery.
        4. NATURAL CONVERSATION: Respond ONLY with the text of the single question to be spoken aloud (2-3 sentences max).
        """
        
        if gemini_available:
            try:
                for model_name in ['gemini-1.5-flash', 'gemini-2.0-flash', 'gemini-1.5-pro']:
                    try:
                        model = genai.GenerativeModel(model_name)
                        response = model.generate_content(prompt)
                        if response.text and response.text.strip():
                            return response.text.strip()
                    except Exception:
                        pass
            except Exception as e:
                logger.error(f"Gemini interview question error: {e}")
                
        return AIService._mock_next_interview_question(
            role, interview_type, history, job_description,
            experience_level=experience_level, topic_domain=topic_domain,
            current_difficulty=current_difficulty, last_turn_correct=True
        )

    @staticmethod
    def evaluate_interview_turn(
        role: str,
        interview_type: str,
        history: List[Dict[str, str]],
        job_description: Optional[str] = None,
        experience_level: Optional[str] = "Fresher",
        topic_domain: Optional[str] = "AIML",
        current_difficulty: Optional[str] = "Easy"
    ) -> Dict[str, Any]:
        """Evaluates candidate's last answer in real-time, determines correctness, adapts difficulty up or down, and produces immediate AI correction, ideal answer, and spoken next question."""
        candidate_answers = [h for h in history if h.get("role") == "candidate"]
        interviewer_qs = [h for h in history if h.get("role") == "interviewer"]
        
        last_answer = candidate_answers[-1].get("text", "") if candidate_answers else ""
        last_question = interviewer_qs[-1].get("text", "") if interviewer_qs else "Walk me through your engineering experience."
        is_fresher = (experience_level or "Fresher").lower() in ["fresher", "entry level", "student", "internship", "junior"]
        
        jd_context = f"\nJob Description / Requirements:\n{job_description}\n" if job_description else ""
        
        prompt = f"""
        You are Dr. Alex Vance, a Principal Engineer conducting a live online placement interview.
        Target Role: {role} ({interview_type})
        Experience Profile: {"Fresher / College Graduate" if is_fresher else "Experienced Software Engineer"}
        Topic Domain: {topic_domain or "AIML"}
        Current Difficulty Level: {current_difficulty or "Easy"}
        {jd_context}
        Question asked: {last_question}
        Candidate Answer: {last_answer}
        
        ADAPTIVE DIFFICULTY INSTRUCTIONS:
        - If the candidate's answer is flawed, wrong, or 'not even close to right':
          Set "is_correct": false, and REDUCE difficulty: "Hard" -> "Medium", "Medium" -> "Easy", "Easy" -> "Easy".
          DO NOT ask a harder question. Instead, ask a simpler, foundational question at the same or lower level.
        - If the candidate's answer is strong and technically accurate:
          Set "is_correct": true, and ELEVATE difficulty: "Easy" -> "Medium", "Medium" -> "Hard", "Hard" -> "Hard".
        - If candidate is a Fresher: questions should focus on academic projects, fundamentals, and AI/ML (supervised learning, overfitting, LLMs, prompt engineering, RAG, etc.).

        Evaluate strictly and return JSON:
        {{
            "is_correct": true/false,
            "assessment": "Strong Answer" / "Partially Correct" / "Needs Correction",
            "score_on_turn": 0-100,
            "confidence_estimate": 0-100,
            "difficulty": "Easy" / "Medium" / "Hard",
            "difficulty_change": "decreased" / "same" / "increased",
            "ai_immediate_feedback": "1-2 sentence immediate reaction praising good points or highlighting omissions",
            "ai_correction": "If answer was wrong, explain clearly what was incorrect and what the right concept is.",
            "ideal_answer": "Crisp, gold-standard model answer in 2-3 sentences.",
            "next_question": "Adaptive follow-up question matched to the new difficulty level.",
            "speech_text_to_speak": "Natural spoken voice script that the interviewer says aloud to the candidate."
        }}
        """
        
        if gemini_available:
            try:
                for model_name in ['gemini-1.5-flash', 'gemini-2.0-flash']:
                    try:
                        model = genai.GenerativeModel(model_name, generation_config={"response_mime_type": "application/json"})
                        response = model.generate_content(prompt)
                        parsed = AIService._clean_and_parse_json(response.text)
                        if isinstance(parsed, dict) and "next_question" in parsed:
                            return parsed
                    except Exception:
                        pass
            except Exception as e:
                logger.error(f"Gemini turn evaluation error: {e}")
                
        return AIService._mock_evaluate_turn(
            role, interview_type, last_question, last_answer, history, job_description,
            experience_level=experience_level, topic_domain=topic_domain,
            current_difficulty=current_difficulty
        )

    @staticmethod
    def analyze_interview(role: str, interview_type: str, history: List[Dict[str, str]], job_description: Optional[str] = None) -> Dict[str, Any]:
        """Analyzes the full interview transcripts and returns comprehensive evaluation reports."""
        jd_context = f"\nJob Description Target:\n{job_description}\n" if job_description else ""
        prompt = f"""
        Analyze this complete job interview for the role of {role} ({interview_type}).
        {jd_context}
        Transcript:
        {json.dumps(history)}
        
        Return a JSON response with:
        - technical_score: Integer (0-100)
        - communication_score: Integer (0-100)
        - confidence_score: Integer (0-100)
        - problem_solving_score: Integer (0-100)
        - leadership_score: Integer (0-100)
        - overall_score: Integer (0-100)
        - feedback:
            - strengths: list of strings
            - weaknesses: list of strings
            - mistakes: list of strings (concrete things they answered incorrectly)
            - ideal_answers: list of dicts with 'question' and 'ideal_answer'
            - suggestions: list of strings
            - practice_plan: list of strings
        """
        
        if gemini_available:
            try:
                for model_name in ['gemini-1.5-flash', 'gemini-1.5-pro']:
                    try:
                        model = genai.GenerativeModel(model_name, generation_config={"response_mime_type": "application/json"})
                        response = model.generate_content(prompt)
                        return AIService._clean_and_parse_json(response.text)
                    except Exception:
                        pass
            except Exception as e:
                logger.error(f"Gemini interview analysis error: {e}")
                
        return AIService._mock_interview_analyzer(role, interview_type, history, job_description)

    @staticmethod
    def get_career_advice(query: str, history: List[Dict[str, str]] = None) -> Dict[str, Any]:
        """Interactive AI Career Mentor and Coding Coach chat response."""
        if not history:
            history = []

        # Strict Topic Guardrail Check: Only technical, interview, and communication topics
        if not CareerKnowledgeEngine.is_in_scope(query):
            return {
                "response": CareerKnowledgeEngine.OUT_OF_SCOPE_MESSAGE,
                "suggestions": [
                    "How to prepare for technical interviews?",
                    "Solve Two Sum in Python",
                    "Tips to improve communication skills for interviews"
                ]
            }

        if gemini_available:
            try:
                system_prompt = """You are GapX AI Mentor, an empathetic, top-tier career coach, senior principal engineer, and computer science & engineering mentor.
You are designed to answer questions related to interviews, coding, Data Structures & Algorithms (like HashMaps, Graphs, Trees, Arrays, DP), Computer Science, and ALL engineering topics and subjects (including electronics, electrical, mechanical, civil, mathematics, and systems) as well as communication skills.

STRICT GUARDRAIL:
If the user asks an unrelated question (such as cooking recipes, food ingredients, movies, entertainment, sports scores, weather forecasts, health/medical advice, or dating tips), you MUST politely decline and respond EXACTLY stating:
"I am designed only to answer questions related to interview, technical or communication skills only, so sorry I will not be able to answer this question."

Provide actionable, precise, and authoritative guidance:
- If the user asks about Data Structures & Algorithms (e.g. HashMaps, Hash Tables, Trees, Graphs): Provide deep technical explanations, internal workings (hash functions, collision resolution, load factor, bucket arrays), complexity analysis O(...), and complete code implementations.
- If the user asks about ANY engineering topic or subject: Explain the fundamental physical or theoretical principles, governing equations, real-world engineering applications, and technical interview relevance.
- If the user asks for code/algorithms: Provide complete, working code in the requested language (or Python/C/C++/Java), with clean comments, step-by-step logic, and Time/Space complexity O(...).
- If the user asks about career/interviews: Provide actionable frameworks (STAR method, XYZ formula), sample scripts, and preparation roadmaps.
- Format with markdown, bolding, and bullet points.

Return a STRICT JSON response:
{
    "response": "Markdown formatted answer",
    "suggestions": ["Follow-up question 1", "Follow-up question 2", "Follow-up question 3"]
}"""
                prompt = f"{system_prompt}\n\nChat History: {json.dumps(history[-6:])}\nUser: {query}"
                for model_name in ['gemini-1.5-flash', 'gemini-2.0-flash', 'gemini-1.5-pro', 'gemini-pro']:
                    try:
                        model = genai.GenerativeModel(model_name, generation_config={"response_mime_type": "application/json"})
                        response = model.generate_content(prompt)
                        parsed = AIService._clean_and_parse_json(response.text)
                        if isinstance(parsed, dict) and "response" in parsed and parsed["response"]:
                            return {
                                "response": str(parsed["response"]),
                                "suggestions": list(parsed.get("suggestions", []))[:3]
                            }
                    except Exception as me:
                        logger.debug(f"Gemini career advice model {model_name} error: {me}")
            except Exception as e:
                logger.error(f"Gemini Career Mentor error: {e}")

        # Comprehensive Dynamic Local Engine
        return CareerKnowledgeEngine.get_response(query, history)

    @staticmethod
    def get_coding_hint(problem_title: str, problem_statement: str, code: str, language: str) -> Dict[str, str]:
        """Provides AI suggestions/hints for code debugging without revealing the exact solution."""
        prompt = f"""
        A student is trying to solve the problem '{problem_title}' in {language}.
        Problem Statement:
        {problem_statement}
        
        Their current code submission:
        ```{language}
        {code}
        ```
        
        Act as a LeetCode tutor. Give a hint, point out bugs/inefficiencies, and explain the approach WITHOUT directly giving the corrected code.
        
        Return a JSON with:
        - hint: An encouraging hint pointing to the error or next step.
        - approach: Explanation of the logic or algorithm needed.
        """
        
        if gemini_available:
            try:
                model = genai.GenerativeModel('gemini-1.5-flash', generation_config={"response_mime_type": "application/json"})
                response = model.generate_content(prompt)
                return AIService._clean_and_parse_json(response.text)
            except Exception as e:
                logger.error(f"Gemini coding hint error: {e}")
                
        return {
            "hint": "Ensure you are correctly handling edge cases, such as when the array is empty or contains negative values. Consider using a hash map to look up items in O(1) time.",
            "approach": "To solve this in O(N) time complexity, you should track traversed elements using a Set or HashMap. For each element x, compute target - x and check if it exists in the tracking structure."
        }

    # --- MOCK GENERATION FALLBACKS ---
    @staticmethod
    def _mock_roadmap_generator(role: str, skills: List[str]) -> List[Dict[str, Any]]:
        role_lower = role.lower()
        
        # Role-specific stage 5 & 6 customization
        if "frontend" in role_lower or "react" in role_lower or "web" in role_lower:
            spec_title = "Modern Frontend Architecture"
            spec_desc = "Master React, Next.js, State Management, CSS Architecture, and Web Vitals."
            topic_51 = {"id": 501, "title": "React Core & Hooks Deep Dive", "description": "Virtual DOM, useEffect, useMemo, custom hooks, and component lifecycle.", "estimated_hours": 8, "difficulty": "Medium", "resources": [{"type": "Documentation", "title": "React Docs", "url": "https://react.dev"}]}
            topic_52 = {"id": 502, "title": "State Management & Next.js SSR/SSG", "description": "Redux Toolkit, Zustand, Server Components, and App Router architecture.", "estimated_hours": 10, "difficulty": "Hard", "resources": [{"type": "Documentation", "title": "Next.js Docs", "url": "https://nextjs.org"}]}
            sys_title = "Frontend System Design & Optimization"
            topic_61 = {"id": 601, "title": "Web Vitals & Performance Tuning", "description": "LCP, FID, CLS, code splitting, lazy loading, and asset optimization.", "estimated_hours": 8, "difficulty": "Medium", "resources": []}
            topic_62 = {"id": 602, "title": "Micro-Frontends & Design Systems", "description": "Module Federation, Tailwind CSS design tokens, and accessibility (a11y).", "estimated_hours": 10, "difficulty": "Hard", "resources": []}
        elif "data" in role_lower or "machine learning" in role_lower or "ai" in role_lower:
            spec_title = "Data Engineering & Machine Learning Pipelines"
            spec_desc = "Build scalable data pipelines, ML models, feature engineering, and neural networks."
            topic_51 = {"id": 501, "title": "Pandas, NumPy & Exploratory Data Analysis", "description": "Data wrangling, matrix manipulation, feature scaling, and statistical distributions.", "estimated_hours": 8, "difficulty": "Medium", "resources": [{"type": "Documentation", "title": "Pandas Docs", "url": "https://pandas.pydata.org"}]}
            topic_52 = {"id": 502, "title": "Supervised & Unsupervised ML Algorithms", "description": "Regression, Decision Trees, Random Forests, XGBoost, Clustering, and PCA.", "estimated_hours": 12, "difficulty": "Hard", "resources": []}
            sys_title = "MLOps & Big Data Systems"
            topic_61 = {"id": 601, "title": "PySpark & Big Data Processing", "description": "Distributed dataframes, RDDs, Hadoop ecosystem, and stream processing.", "estimated_hours": 10, "difficulty": "Hard", "resources": []}
            topic_62 = {"id": 602, "title": "Model Deployment & MLOps Pipelines", "description": "FastAPI ML serving, MLflow tracking, Docker containerization, and monitoring drift.", "estimated_hours": 10, "difficulty": "Hard", "resources": []}
        elif "devops" in role_lower or "cloud" in role_lower:
            spec_title = "Cloud Infrastructure & Orchestration"
            spec_desc = "Master AWS/GCP, Kubernetes, Terraform Infrastructure as Code, and CI/CD automation."
            topic_51 = {"id": 501, "title": "Terraform & Infrastructure as Code (IaC)", "description": "HCL syntax, state management, modules, and multi-environment cloud provisioning.", "estimated_hours": 10, "difficulty": "Medium", "resources": []}
            topic_52 = {"id": 502, "title": "Kubernetes Cluster Management & Helm", "description": "Pods, Deployments, Services, Ingress controllers, Helm charts, and Secrets.", "estimated_hours": 12, "difficulty": "Hard", "resources": []}
            sys_title = "Reliability Engineering & Monitoring"
            topic_61 = {"id": 601, "title": "Prometheus, Grafana & Log Aggregation", "description": "Metrics scraping, alertmanager rules, ELK stack log processing, and tracing.", "estimated_hours": 8, "difficulty": "Medium", "resources": []}
            topic_62 = {"id": 602, "title": "Zero Downtime Deployments & Service Mesh", "description": "Canary releases, Blue/Green strategies, Istio service mesh, and mTLS security.", "estimated_hours": 10, "difficulty": "Hard", "resources": []}
        else: # Software Engineer / Backend / Full Stack / Generic
            spec_title = f"Core Backend & API Architecture ({role})"
            spec_desc = f"Deep dive into production runtime engines, REST/gRPC APIs, microservices, and database ORMs for {role}."
            topic_51 = {"id": 501, "title": "RESTful API & gRPC Microservice Specs", "description": "HTTP/2, protocol buffers, OpenAPI, middleware, authentication, and rate limiting.", "estimated_hours": 8, "difficulty": "Medium", "resources": []}
            topic_52 = {"id": 502, "title": "Async Workers, Celery & Message Queues", "description": "RabbitMQ, Kafka event streams, Redis pub/sub, background workers, and idempotency.", "estimated_hours": 10, "difficulty": "Hard", "resources": []}
            sys_title = "Distributed Systems & System Design"
            topic_61 = {"id": 601, "title": "Database Sharding, Replication & Caching", "description": "Master-slave replication, consistent hashing, Redis LRU, and read/write splitting.", "estimated_hours": 10, "difficulty": "Hard", "resources": []}
            topic_62 = {"id": 602, "title": "High Availability & Fault Tolerant Systems", "description": "Circuit breakers, rate limiters, consensus protocols (Raft/Paxos), and CDN edge caching.", "estimated_hours": 12, "difficulty": "Hard", "resources": []}

        stages = [
            {
                "id": 1,
                "title": f"Programming Foundations for {role}",
                "description": f"Master fundamental language syntax, object-oriented concepts, and memory structures essential for {role}.",
                "topics": [
                    {"id": 101, "title": "Data Types, Scoping & Control Flow", "description": "Variables, memory pointers, loops, conditional logic, and recursion fundamentals.", "estimated_hours": 4, "difficulty": "Easy", "resources": [{"type": "Documentation", "title": "Language Spec", "url": "https://docs.python.org"}]},
                    {"id": 102, "title": "Object-Oriented & Functional Design", "description": "Classes, Inheritance, Interfaces, Immutability, Lambda expressions, and Clean Code principles.", "estimated_hours": 6, "difficulty": "Medium", "resources": [{"type": "YouTube", "title": "OOP Architecture", "url": "https://youtube.com"}]}
                ]
            },
            {
                "id": 2,
                "title": "Core Data Structures & Memory Layouts",
                "description": "Building blocks of memory allocation, indexing, search trees, and dynamic arrays.",
                "topics": [
                    {"id": 201, "title": "Arrays, Strings & Hash Tables", "description": "Contiguous memory, string manipulation, hash collisions, and constant-time lookups.", "estimated_hours": 8, "difficulty": "Medium", "resources": []},
                    {"id": 202, "title": "Linked Lists, Stacks & Queues", "description": "Pointers, node traversal, double-ended queues, stack call frames, and queue buffers.", "estimated_hours": 8, "difficulty": "Medium", "resources": []}
                ]
            },
            {
                "id": 3,
                "title": "Advanced Algorithmic Paradigms",
                "description": "Formulate optimal time/space complexity solutions using standard algorithmic patterns.",
                "topics": [
                    {"id": 301, "title": "Binary Search, Two Pointers & Sliding Window", "description": "Logarithmic search spaces, subarray window tracking, and optimal pointer increments.", "estimated_hours": 8, "difficulty": "Medium", "resources": []},
                    {"id": 302, "title": "Dynamic Programming & Greedy Algorithms", "description": "Subproblem overlap, memoization tables, bottom-up tabulation, and optimal choices.", "estimated_hours": 12, "difficulty": "Hard", "resources": []}
                ]
            },
            {
                "id": 4,
                "title": "Database Systems & Data Persistence",
                "description": "Structure relational schemas, write optimized SQL queries, and configure NoSQL databases.",
                "topics": [
                    {"id": 401, "title": "SQL Deep Dive, Indexing & Transactions", "description": "B-Tree indexing, JOIN optimization, ACID guarantees, and database normalization.", "estimated_hours": 6, "difficulty": "Medium", "resources": []},
                    {"id": 402, "title": "NoSQL Key-Value Stores & Document DBs", "description": "MongoDB, Redis caching strategies, TTL expiration policies, and document modeling.", "estimated_hours": 6, "difficulty": "Medium", "resources": []}
                ]
            },
            {
                "id": 5,
                "title": spec_title,
                "description": spec_desc,
                "topics": [topic_51, topic_52]
            },
            {
                "id": 6,
                "title": sys_title,
                "description": f"Architect scalability, high throughput, and system reliability for {role} software environments.",
                "topics": [topic_61, topic_62]
            },
            {
                "id": 7,
                "title": "DevOps Pipeline & Capstone Placement Project",
                "description": "Build, containerize, and deploy a complete production-grade application for your resume portfolio.",
                "topics": [
                    {"id": 701, "title": "Docker Containerization & Multi-Stage Builds", "description": "Writing Dockerfiles, environment variables, docker-compose, and microservice networking.", "estimated_hours": 6, "difficulty": "Medium", "resources": []},
                    {"id": 702, "title": "CI/CD & Cloud Deployment Capstone Project", "description": "GitHub Actions pipelines, automated testing, production hosting, and live portfolio demo.", "estimated_hours": 12, "difficulty": "Medium", "resources": []}
                ]
            },
            {
                "id": 8,
                "title": "LeetCode Mastery & FAANG Mock Interviews",
                "description": "Consolidate your technical skills, practice algorithmic interviews, and refine behavioral responses.",
                "topics": [
                    {"id": 801, "title": "Top FAANG Coding Interview Patterns", "description": "Graph BFS/DFS, Tree LCA, Heap Top-K, Dynamic Programming, and Interval Merging.", "estimated_hours": 15, "difficulty": "Hard", "resources": []},
                    {"id": 802, "title": "Mock Interviews, STAR Technique & Soft Skills", "description": "Behavioral STAR framework, handling interviewer hints, and articulating trade-offs under time pressure.", "estimated_hours": 10, "difficulty": "Medium", "resources": []}
                ]
            }
        ]
        return stages

    @staticmethod
    def _mock_next_interview_question(role: str, interview_type: str, history: List[Dict[str, str]]) -> str:
        candidate_answers = [h for h in history if h.get("role") == "candidate"]
        last_answer = candidate_answers[-1].get("text", "") if candidate_answers else ""
        last_answer_lower = last_answer.lower()
        role_lower = role.lower()

        questions_count = len([h for h in history if h.get("role") == "interviewer"])

        # Check for brief or incomplete answer
        if last_answer and len(last_answer.split()) < 8:
            return f"That was quite brief. Could you elaborate further with technical details on how your approach handles edge cases in a production {role} environment?"

        # Dynamic follow-up based on candidate's specific terms
        if "hash" in last_answer_lower or "map" in last_answer_lower:
            return f"Good point on hash maps! How does collision resolution work internally (e.g. chaining vs open addressing), and how do you prevent worst-case O(N) lookup degradation in hash tables?"
        elif "sql" in last_answer_lower or "database" in last_answer_lower or "index" in last_answer_lower:
            return f"You brought up databases. How do you analyze slow query execution plans in production, and when would you choose a B-Tree index over a Hash index?"
        elif "docker" in last_answer_lower or "kubernetes" in last_answer_lower or "container" in last_answer_lower:
            return f"Nice containerization reference. How do you optimize Docker multi-stage builds to minimize image footprint and secure container runtime permissions?"
        elif "model" in last_answer_lower or "pytorch" in last_answer_lower or "tensor" in last_answer_lower:
            return f"Great ML context. How do you address data drift and model latency when serving predictions to thousands of active users?"
        elif "react" in last_answer_lower or "next" in last_answer_lower or "state" in last_answer_lower:
            return f"Solid frontend insight! How does React Virtual DOM diffing (reconciliation algorithm) operate, and how do you prevent unnecessary component re-renders?"

        # Role-tailored Interview Question Banks
        if interview_type in ["HR", "Behavioral"]:
            hr_pool = [
                f"Welcome to your HR & Behavioral assessment for the {role} position! To start, describe a major conflict you faced with a team member and how you resolved it using the STAR framework.",
                "Tell me about a time when a project deadline was suddenly moved forward. How did you prioritize feature trade-offs and communicate with stakeholders?",
                "Describe a situation where a code deployment broke in production. What went wrong, how did you recover, and what post-mortem steps were taken?",
                "How do you keep yourself updated with rapidly evolving technology stacks while managing day-to-day project deliverables?",
                "What are your long-term career aspirations for this role over the next 3 to 5 years?"
            ]
            index = min(questions_count, len(hr_pool) - 1)
            return hr_pool[index]

        # Technical / Mixed Question Banks tailored by Role
        if "frontend" in role_lower or "react" in role_lower or "web" in role_lower:
            pool = [
                f"Welcome to your Technical interview for the {role} role! Could you walk me through your web development experience and your favorite frontend project?",
                "How do you approach state management in a large-scale React app? Compare Redux Toolkit vs Zustand vs React Context in terms of performance.",
                "Explain Next.js App Router: What are Server Components vs Client Components, and how do you optimize Core Web Vitals (LCP, CLS, FID)?",
                "How do you design a resilient Frontend System Design for a real-time collaborative dashboard with WebSockets and offline caching?",
                "Excellent technical depth! Do you have any questions for me regarding our engineering team, design system, or stack expectations?"
            ]
        elif "data" in role_lower or "machine learning" in role_lower or "ai" in role_lower:
            pool = [
                f"Welcome to your Technical screening for {role}! Walk me through your data science background and a machine learning model you built end-to-end.",
                "How do you handle imbalanced datasets during training, and how do you choose between Precision, Recall, F1-Score, and ROC-AUC metrics?",
                "Explain the architecture of Transformer models (Self-Attention mechanism) and how Positional Encoding enables sequence processing without RNNs.",
                "How do you architect an MLOps pipeline using Docker and FastAPI to serve real-time predictions with sub-50ms latency?",
                "Fantastic performance! What questions do you have for our AI engineering team about model infrastructure or data scale?"
            ]
        elif "devops" in role_lower or "cloud" in role_lower:
            pool = [
                f"Welcome to your Technical interview for {role}! Walk me through your experience managing cloud infrastructure and CI/CD pipelines.",
                "Explain Docker multi-stage builds and container orchestration in Kubernetes: How do Pods, Deployments, Services, and Ingress controllers interact?",
                "How do you configure Terraform Infrastructure as Code for multi-environment deployments, and how do you manage remote state locks securely?",
                "How do you design an automated observability stack using Prometheus, Grafana, and Alertmanager to maintain 99.99% system uptime?",
                "Great work! What questions do you have for our Cloud Operations team regarding site reliability and security standards?"
            ]
        else: # Software Engineer / Backend / Fullstack
            pool = [
                f"Welcome to your Technical screening for the {role} position! To start, walk me through your software engineering background and your flagship project.",
                f"How would you design a distributed API Rate Limiter handling 50,000 requests per second for a {role} platform? Which algorithms and caching layers would you use?",
                "Suppose we have a continuous high-volume data stream and need to find the Top K most frequent items under strict memory bounds. How would you solve this efficiently?",
                "Let's cover System Architecture: How do you architect database sharding, connection pooling, and read-replicas to handle traffic spikes gracefully?",
                "Outstanding job today! What questions do you have for me regarding our engineering culture, tech stack, or career growth opportunities?"
            ]

        index = min(questions_count, len(pool) - 1)
        return pool[index]

    @staticmethod
    def _mock_resume_analyzer(resume_data: Dict[str, Any]) -> Dict[str, Any]:
        if not resume_data:
            resume_data = {}

        raw_text = str(resume_data.get("extracted_text") or "")
        target_roles = resume_data.get("target_roles") or []
        if isinstance(target_roles, list) and len(target_roles) > 0 and target_roles[0]:
            primary_role = str(target_roles[0])
        else:
            primary_role = str(resume_data.get("headline") or "Software Engineer")

        entities = ResumeEntityExtractor.extract_text_entities(raw_text, resume_data)
        return ResumeEntityExtractor.evaluate_and_audit(entities, primary_role)

    @staticmethod
    def _mock_topic_notes(topic_title: str, stage_title: str, role: str) -> Dict[str, Any]:
        """Generates comprehensive, placement-level academic study notes with deep architectural theory, production code, complexity analysis, and FAANG interview questions."""
        title_lower = topic_title.lower()
        
        # 1. Topic: Data Types, Scoping & Control Flow
        if "data type" in title_lower or "scoping" in title_lower or "control flow" in title_lower or "foundation" in title_lower:
            return {
                "title": topic_title,
                "stage": stage_title,
                "role": role,
                "executive_summary": "Data Types, Variable Scoping, and Control Flow form the fundamental bedrock of computation in modern programming systems. A data type defines the mathematical domain of values, the internal bitwise memory representation, and the permissible operations that can be performed without violating memory safety. Variable scoping dictates the lexical visibility and runtime lifetime of identifier bindings in the execution environment, distinguishing between stack-allocated activation records and heap-allocated dynamic objects.",
                "internals_and_architecture": "At the hardware and runtime virtual machine level, primitive data types (integers, floats, booleans) map directly to CPU registers and byte-aligned stack offsets. When a function executes, a stack frame (activation record) is pushed containing local variables, return addresses, and saved frame pointers. Lexical scoping is resolved at compile time through symbol tables, while dynamic or closure scoping retains references in the heap via environment chains. Control flow constructs (if/else, loops) translate into conditional jump instructions (such as JMP, JZ, JNZ in x86-64 assembly) where branch predictors in the CPU execute speculative instruction pipelines.",
                "key_concepts": [
                    {"name": "Primitive vs Reference Types", "explanation": "Primitives store raw scalar values directly inside fixed-width CPU stack allocations (e.g., 32-bit int, 64-bit float). Reference types store 64-bit pointers pointing to dynamically allocated memory chunks on the heap managed by runtime garbage collectors or manual deallocation."},
                    {"name": "Lexical Scope & Closure Chains", "explanation": "Lexical scoping ensures variable resolution is determined strictly by physical textual position in source code. When inner functions enclose variables from outer scopes, a closure environment record is preserved in memory even after the outer function's call frame is popped off the stack."},
                    {"name": "Pass-by-Value vs Pass-by-Reference", "explanation": "Languages like Python, Java, and JavaScript operate on 'pass-by-object-reference' or 'pass-by-value-of-pointer', where function arguments receive a copied memory address pointing to the same underlying heap object rather than a mutated stack address."},
                    {"name": "Control Flow Branch Prediction & Recursion Call Stacks", "explanation": "Deep recursion consumes linear stack memory proportional to recursion depth (O(N) stack frames), which risks a StackOverflowError if base cases fail. Iterative loops with branch prediction utilize CPU instruction cache locality without stack growth."}
                ],
                "complexity_analysis": [
                    {"operation": "Primitive Stack Allocation & Read", "time_complexity": "O(1)", "space_complexity": "O(1)", "explanation": "Direct offset addition to stack pointer register ($rsp)."},
                    {"operation": "Heap Allocation & Pointer Dereference", "time_complexity": "O(1) amortized", "space_complexity": "O(N)", "explanation": "Requires memory allocator lookup and potential garbage collection sweep."},
                    {"operation": "Recursive Call Sequence (Depth N)", "time_complexity": "O(N)", "space_complexity": "O(N) Stack", "explanation": "Allocates N activation record frames on the call stack."}
                ],
                "code_example": """# ==============================================================================
# Production Demonstration: Scoping, Recursion vs Iteration, and Bitwise Logic
# ==============================================================================
from typing import List, Optional

def demonstrate_closure_scoping(initial_counter: int = 0):
    \"\"\"
    Demonstrates closure scoping where 'counter' is captured in an enclosed 
    heap lexical environment that persists across invocations.
    \"\"\"
    counter = initial_counter  # Local variable bound in outer activation frame

    def increment(step: int = 1) -> int:
        nonlocal counter       # Mutates enclosed lexical binding
        counter += step
        return counter

    def get_current_value() -> int:
        return counter

    return increment, get_current_value


def factorial_optimized(n: int) -> int:
    \"\"\"
    Computes factorial iteratively to guarantee O(1) auxiliary space 
    and avoid stack overflow issues inherent in naive recursion.
    Time Complexity: O(N) | Space Complexity: O(1)
    \"\"\"
    if n < 0:
        raise ValueError("Factorial is undefined for negative integers.")
    result = 1
    for i in range(2, n + 1):
        result *= i
    return result


if __name__ == "__main__":
    # Test Closure Scoping
    inc, get_val = demonstrate_closure_scoping(100)
    inc(5)
    print(f"Current Counter Value: {get_val()}")  # Output: 105
    print(f"Factorial of 6: {factorial_optimized(6)}")  # Output: 720
""",
                "industry_use_cases": [
                    {"company": "Google", "use_case": "V8 JavaScript Engine optimization using hidden classes and inline caching based on predictable primitive memory layouts.", "architecture_impact": "Reduces variable property lookup time from O(N) hash searches down to single-cycle O(1) CPU machine instructions."},
                    {"company": "High-Frequency Trading (HFT) Systems", "use_case": "Replacing dynamic heap objects with fixed-size stack primitives and cache-aligned memory buffers.", "architecture_impact": "Eliminates GC pauses and brings sub-microsecond deterministic execution latency."}
                ],
                "common_pitfalls": [
                    "Modifying mutable default function arguments (e.g. `def append_item(val, items=[])`) which creates shared mutable state across all function calls.",
                    "Unbounded recursion causing StackOverflowError due to exhausted thread stack memory (typically 1MB-8MB limit).",
                    "Misunderstanding scope hoisting or closure loop variable binding in asynchronous closures."
                ],
                "interview_questions": [
                    {"question": "What is the precise difference between Stack and Heap memory allocation?", "ideal_answer": "Stack memory is statically managed by the CPU architecture via the stack pointer register; allocations and deallocations occur in strict LIFO order with zero fragmentation and sub-nanosecond speed. Heap memory is a large, dynamically managed pool where objects of arbitrary lifetimes are allocated at runtime via memory managers (e.g. malloc/jemalloc) and cleared via garbage collection or manual free calls.", "difficulty": "Medium"},
                    {"question": "How does tail-call optimization (TCO) prevent call stack exhaustion in recursive functions?", "ideal_answer": "Tail-call optimization occurs when the recursive call is the very final expression evaluated in a subroutine. The compiler reuses the current stack frame rather than pushing a new frame, transforming recursion into a constant-space O(1) iterative loop at the machine code level.", "difficulty": "Hard"},
                    {"question": "Explain pass-by-value vs pass-by-reference in Python and Java.", "ideal_answer": "Both Python and Java use 'pass-by-value of the object reference'. When an object is passed into a method, the pointer address is copied by value onto the new stack frame. Reassigning the parameter variable inside the function only changes the local pointer, but mutating properties of that referenced object directly alters the original object in the heap.", "difficulty": "Medium"},
                    {"question": "What are closures and how are they represented in memory?", "ideal_answer": "A closure is a function bundled together with references to its surrounding lexical state (lexical environment). In memory, the runtime creates a closure object containing a pointer to the function bytecode and a pointer to an environment record allocated on the heap containing the captured variables.", "difficulty": "Hard"},
                    {"question": "How do CPU branch predictors optimize conditional control flow statements?", "ideal_answer": "CPUs maintain Branch History Tables (BHT) and Branch Target Buffers (BTB). When encountering an 'if' statement, the processor speculatively executes instructions along the statistically most likely branch. If predicted correctly, execution continues without pipeline stall; if mispredicted, the speculative pipeline is flushed, causing a 10-20 cycle penalty.", "difficulty": "Hard"}
                ],
                "best_practices": [
                    "Prefer immutable data structures where possible to avoid unintended side-effect mutations across shared scopes.",
                    "Always define explicit base cases for recursive routines and consider iterative rewrites for deep trees.",
                    "Avoid global mutable variables; encapsulate state in scoped classes or pure functions.",
                    "Use static type checking (e.g. MyPy, TypeScript) to catch type mismatches before runtime."
                ],
                "summary": "Mastering scoping rules, stack vs heap allocation, and control flow guarantees deterministic execution, prevents memory leaks, and prepares you for low-level language design questions in top tech interviews."
            }

        # 2. Topic: Arrays, Strings & Hash Tables
        elif "array" in title_lower or "hash" in title_lower or "string" in title_lower:
            return {
                "title": topic_title,
                "stage": stage_title,
                "role": role,
                "executive_summary": "Arrays and Hash Tables represent the foundational linear and associative data structures in computer science. Arrays provide contiguous, indexed memory storage offering O(1) random access by computing direct memory byte offsets. Hash Tables (Hash Maps) map arbitrary keys to values in O(1) average time by passing keys through a deterministic hash function to generate array bucket indices, resolving collisions through chaining or open addressing.",
                "internals_and_architecture": "An array allocates a contiguous chunk of physical memory addresses: Address(A[i]) = BaseAddress + (i * ElementSizeInBytes). Dynamic arrays (like Python list, Java ArrayList, C++ std::vector) automatically resize with a geometric growth factor (usually 1.5x or 2x) when capacity is reached, achieving O(1) amortized insertion. Hash tables compute `index = hash(key) % capacity`. When two keys produce identical bucket indices (a collision), Hash Maps resolve it using Separate Chaining (linked lists or self-balancing Red-Black trees if chain length >= 8, as in Java 8 HashMap) or Open Addressing with Linear/Quadratic Probing. The load factor (α = N / Capacity) triggers rehashing when it exceeds a threshold (typically 0.75).",
                "key_concepts": [
                    {"name": "Contiguous Memory & CPU Cache Locality", "explanation": "Because array elements sit adjacent in physical RAM, iterating through an array triggers hardware CPU prefetching, loading entire 64-byte Cache Lines into L1/L2 caches, resulting in massive performance gains over pointer-chasing structures like linked lists."},
                    {"name": "Hash Functions & Uniform Distribution", "explanation": "A cryptographic or fast non-cryptographic hash function (like MurmurHash3, SipHash) must distribute keys uniformly across all buckets to minimize clustering and prevent O(N) degradation."},
                    {"name": "Collision Resolution Mechanics", "explanation": "Separate chaining stores collisions in linked buckets (or trees). Open addressing searches for next available open slot in the primary array using probing sequences (Linear: i+1, Quadratic: i+k^2, Double Hashing: hash1(k) + i*hash2(k))."},
                    {"name": "String Immutability & StringBuilder", "explanation": "In Python, Java, and JS, strings are immutable byte/character arrays. Repeated concatenation in a loop creates O(N^2) memory allocations; using dynamic string builders (e.g., list append + ''.join()) achieves O(N) linear time."}
                ],
                "complexity_analysis": [
                    {"operation": "Array Index Access (A[i])", "time_complexity": "O(1)", "space_complexity": "O(1)", "explanation": "Immediate arithmetic calculation of byte address."},
                    {"operation": "Dynamic Array Amortized Append", "time_complexity": "O(1) amortized", "space_complexity": "O(1)", "explanation": "Doubles capacity only every N operations; cost of resizing is spread across all insertions."},
                    {"operation": "Hash Map Search / Insert (Average)", "time_complexity": "O(1)", "space_complexity": "O(N)", "explanation": "Uniform distribution ensures near-zero chain length."},
                    {"operation": "Hash Map Search / Insert (Worst Case)", "time_complexity": "O(N) or O(log N)", "space_complexity": "O(N)", "explanation": "Occurs when all keys collide into a single bucket (O(log N) if bucket transforms into a Red-Black tree)."}
                ],
                "code_example": """# ==============================================================================
# Production Implementation: Custom Thread-Safe Hash Map with Separate Chaining
# ==============================================================================
from typing import Any, Optional, List

class HashNode:
    def __init__(self, key: Any, value: Any):
        self.key = key
        self.value = value
        self.next: Optional['HashNode'] = None

class CustomHashMap:
    \"\"\"
    A robust Hash Map implementation with Separate Chaining and dynamic Rehashing.
    Average Search/Insert: O(1) | Space: O(N)
    \"\"\"
    def __init__(self, initial_capacity: int = 16, load_factor: float = 0.75):
        self.capacity = initial_capacity
        self.load_factor = load_factor
        self.size = 0
        self.buckets: List[Optional[HashNode]] = [None] * self.capacity

    def _hash(self, key: Any) -> int:
        \"\"\"Generates a bounded bucket index using Python's built-in hash.\"\"\"
        return abs(hash(key)) % self.capacity

    def put(self, key: Any, value: Any) -> None:
        \"\"\"Inserts or updates a key-value pair. Triggers rehash if load factor exceeded.\"\"\"
        index = self._hash(key)
        head = self.buckets[index]

        # Traverse chain to check if key already exists
        curr = head
        while curr:
            if curr.key == key:
                curr.value = value
                return
            curr = curr.next

        # Key not found; insert new node at head of chain (O(1))
        new_node = HashNode(key, value)
        new_node.next = self.buckets[index]
        self.buckets[index] = new_node
        self.size += 1

        # Check load factor threshold
        if (self.size / self.capacity) > self.load_factor:
            self._rehash()

    def get(self, key: Any) -> Optional[Any]:
        \"\"\"Retrieves value by key in O(1) average time.\"\"\"
        index = self._hash(key)
        curr = self.buckets[index]
        while curr:
            if curr.key == key:
                return curr.value
            curr = curr.next
        return None

    def _rehash(self) -> None:
        \"\"\"Doubles capacity and redistributes all existing nodes.\"\"\"
        old_buckets = self.buckets
        self.capacity *= 2
        self.buckets = [None] * self.capacity
        self.size = 0

        for head in old_buckets:
            curr = head
            while curr:
                self.put(curr.key, curr.value)
                curr = curr.next
""",
                "industry_use_cases": [
                    {"company": "Redis", "use_case": "In-memory key-value database using incremental progressive rehashing over an internal dict table to avoid latency spikes during table growth.", "architecture_impact": "Maintains sub-millisecond response times even while resizing databases containing millions of keys."},
                    {"company": "Amazon DynamoDB", "use_case": "Consistent hashing ring over distributed nodes using partition keys to route queries to physical storage partitions.", "architecture_impact": "Achieves infinite horizontal scaling with single-digit millisecond latency at any scale."}
                ],
                "common_pitfalls": [
                    "Using mutable objects (e.g. lists, dicts) as Hash Map keys, causing hash value mutation and undetectable lost keys.",
                    "Failing to pre-allocate capacity in high-throughput systems, resulting in repeated expensive rehashing allocations.",
                    "Quadratic string concatenation (`s += char`) in loops instead of list join patterns."
                ],
                "interview_questions": [
                    {"question": "How does Java 8 HashMap optimize worst-case collision performance?", "ideal_answer": "In Java 8, when the number of elements in a single bucket chain reaches 8 (TREEIFY_THRESHOLD) and the total table capacity is at least 64, the linked list is converted into a balanced Red-Black Tree. This reduces worst-case search time from O(N) to O(log N). If the tree shrinks to 6 elements, it reverts to a linked list.", "difficulty": "Hard"},
                    {"question": "What is the difference between Separate Chaining and Open Addressing?", "ideal_answer": "Separate chaining stores collided elements outside the main array in linked lists or trees, handling load factors > 1.0 gracefully. Open addressing keeps all elements within the primary array, searching for alternative empty slots via linear/quadratic probing, which maximizes CPU cache locality but degrades drastically when load factor exceeds 0.7-0.8.", "difficulty": "Medium"},
                    {"question": "Why is resizing a dynamic array amortized O(1) instead of O(N)?", "ideal_answer": "While copying N elements during a resize takes O(N) work, a 2x expansion occurs only after N insertions. The aggregate cost of N insertions is N + (1 + 2 + 4 + ... + N) <= 3N. Dividing total cost by N operations yields a constant average amortized cost of O(1) per insertion.", "difficulty": "Medium"},
                    {"question": "What is Hash DoS (Denial of Service) and how do modern languages prevent it?", "ideal_answer": "Hash DoS occurs when an attacker crafts thousands of malicious keys that produce identical hash values, causing a web server's parameter map to collapse into an O(N^2) linked list, locking CPU cores at 100%. Modern runtimes mitigate this using randomized seed hashing (e.g. SipHash) so hash outputs cannot be predicted by external attackers.", "difficulty": "Hard"},
                    {"question": "How would you design a Two Sum algorithm in O(N) time?", "ideal_answer": "Iterate through the array once while maintaining a hash map of {value: index}. For each element x, calculate target - x. If the complement exists in the map, return the pair of indices in O(1) lookup time. Total time complexity is O(N) with O(N) space complexity.", "difficulty": "Easy"}
                ],
                "best_practices": [
                    "Always ensure custom classes override both `hash()` (or `hashCode`) and `equals()` consistently.",
                    "Set an appropriate initial capacity for hash collections when the expected size is known in advance.",
                    "Use contiguous array buffers for numeric and high-throughput streaming pipelines."
                ],
                "summary": "Arrays and Hash Tables are the most tested data structures in technical interviews. Master pointer manipulation, amortized time analysis, and collision strategies to excel in screening rounds."
            }

        # 3. Topic: Dynamic Programming & Algorithms
        elif "dynamic programming" in title_lower or "algorithm" in title_lower or "dp" in title_lower:
            return {
                "title": topic_title,
                "stage": stage_title,
                "role": role,
                "executive_summary": "Dynamic Programming (DP) is a powerful algorithmic paradigm that solves complex optimization problems by breaking them down into overlapping subproblems and leveraging optimal substructure. Rather than recomputing recurring subproblems repeatedly (which leads to exponential O(2^N) time), Dynamic Programming computes each subproblem exactly once, caching results via Top-Down Memoization or computing them iteratively via Bottom-Up Tabulation in polynomial time.",
                "internals_and_architecture": "The two core prerequisites for Dynamic Programming are: 1) Overlapping Subproblems (the problem space contains identical subproblems called multiple times), and 2) Optimal Substructure (an optimal solution to the global problem can be constructed from optimal solutions of its subproblems). In Top-Down DP, the call stack executes depth-first while a hash map or array caches returned values. In Bottom-Up DP, a 1D or 2D state table is filled sequentially from base cases up to the target state. Space optimization techniques often reduce 2D tables to two rows or single variables when transitions depend only on previous state steps.",
                "key_concepts": [
                    {"name": "Top-Down (Memoization) vs Bottom-Up (Tabulation)", "explanation": "Top-down uses recursion and lazily evaluates states on-demand, storing results in a cache. Bottom-up evaluates all states iteratively in topological dependency order, eliminating recursion call stack overhead."},
                    {"name": "State Representation & Recurrence Relation", "explanation": "The core intellectual step of DP is defining the state variables (e.g., dp[i][w] = maximum profit using first i items with weight capacity w) and deriving the exact mathematical recurrence equation."},
                    {"name": "Space Optimization (Rolling Array Technique)", "explanation": "If state dp[i] depends only on dp[i-1] and dp[i-2] (like Fibonacci or Climbing Stairs), the entire O(N) table can be compressed into two O(1) variables."},
                    {"name": "Classic DP Archetypes", "explanation": "1. 0/1 Knapsack & Unbounded Knapsack, 2. Longest Common Subsequence (LCS) / Edit Distance, 3. Longest Increasing Subsequence (LIS), 4. Matrix Chain Multiplication / Interval DP, 5. Bitmask DP."}
                ],
                "complexity_analysis": [
                    {"operation": "Naive Recursive Fibonacci", "time_complexity": "O(2^N)", "space_complexity": "O(N) Stack", "explanation": "Exponential branching tree of redundant calculations."},
                    {"operation": "Memoized Top-Down DP", "time_complexity": "O(N)", "space_complexity": "O(N) Table + Stack", "explanation": "Every state computed exactly once."},
                    {"operation": "Space-Optimized Bottom-Up Tabulation", "time_complexity": "O(N)", "space_complexity": "O(1)", "explanation": "Iterative loop tracking only the last two state variables."}
                ],
                "code_example": """# ==============================================================================
# Production Demonstration: 0/1 Knapsack with Space Optimization & Reconstruction
# ==============================================================================
from typing import List, Tuple

def knapsack_01_space_optimized(weights: List[int], values: List[int], capacity: int) -> int:
    \"\"\"
    Computes maximum value obtainable without exceeding weight capacity.
    Time Complexity: O(N * W) | Space Complexity: O(W)
    \"\"\"
    n = len(weights)
    # dp[w] stores the max value achievable with capacity w
    dp = [0] * (capacity + 1)

    for i in range(n):
        wt, val = weights[i], values[i]
        # Traverse backward to ensure each item is used at most once
        for w in range(capacity, wt - 1, -1):
            dp[w] = max(dp[w], dp[w - wt] + val)

    return dp[capacity]


def longest_common_subsequence(text1: str, text2: str) -> int:
    \"\"\"
    Finds length of longest common subsequence between two strings.
    Time Complexity: O(M * N) | Space Complexity: O(min(M, N))
    \"\"\"
    m, n = len(text1), len(text2)
    # Ensure text2 is the shorter string to optimize space
    if m < n:
        text1, text2 = text2, text1
        m, n = n, m

    prev = [0] * (n + 1)
    curr = [0] * (n + 1)

    for i in range(1, m + 1):
        for j in range(1, n + 1):
            if text1[i - 1] == text2[j - 1]:
                curr[j] = 1 + prev[j - 1]
            else:
                curr[j] = max(prev[j], curr[j - 1])
        prev = curr[:]

    return prev[n]
""",
                "industry_use_cases": [
                    {"company": "Google Maps & Routing Engines", "use_case": "Shortest path and multi-stop delivery route optimization algorithms (Bellman-Ford, Floyd-Warshall DP).", "architecture_impact": "Computes optimal navigation paths across road networks with millions of vertices."},
                    {"company": "Git & Diff Utilities", "use_case": "Myers Diff Algorithm and Edit Distance DP to compute minimal unified diffs and merge conflicts between codebase revisions.", "architecture_impact": "Enables instant version control delta compression and line-by-line file comparisons."}
                ],
                "common_pitfalls": [
                    "Looping forward instead of backward in 1D 0/1 Knapsack, accidentally turning it into Unbounded Knapsack (reusing same item multiple times).",
                    "Failing to identify overlapping subproblems and attempting DP on non-deterministic or non-optimal-substructure problems (like longest simple path in general graphs).",
                    "Off-by-one errors in table dimensions and boundary base-case initialization."
                ],
                "interview_questions": [
                    {"question": "How do you identify if a problem should be solved with Dynamic Programming?", "ideal_answer": "Look for two telltale signals: 1) The problem asks for an optimum (maximum/minimum), counting total ways, or feasibility, and 2) Choices made at current step affect future choices through overlapping subproblems where greedy choice fails.", "difficulty": "Medium"},
                    {"question": "What is the difference between 0/1 Knapsack and Fractional Knapsack?", "ideal_answer": "In 0/1 Knapsack, items are indivisible (you either take an item wholly or leave it); it requires O(N*W) Dynamic Programming. In Fractional Knapsack, items can be broken down; it can be solved greedily in O(N log N) time by sorting items by value-to-weight ratio.", "difficulty": "Medium"},
                    {"question": "Explain how Edit Distance (Levenshtein Distance) recurrence is derived.", "ideal_answer": "Let dp[i][j] be distance between prefix s1[0..i] and s2[0..j]. If s1[i-1] == s2[j-1], dp[i][j] = dp[i-1][j-1]. Otherwise, dp[i][j] = 1 + min(dp[i-1][j] (Delete), dp[i][j-1] (Insert), dp[i-1][j-1] (Replace)).", "difficulty": "Hard"},
                    {"question": "How can you reconstruct the actual elements chosen in a DP solution?", "ideal_answer": "Either backtrack through the 2D DP table from target state dp[N][W] comparing if dp[i][w] == dp[i-1][w] or dp[i-1][w-wt]+val, or store an explicit parent pointer matrix during state transitions.", "difficulty": "Hard"},
                    {"question": "How does Coin Change 1 (minimum coins) differ from Coin Change 2 (number of combinations)?", "ideal_answer": "Coin Change 1 computes min(dp[amount], 1 + dp[amount - coin]). Coin Change 2 counts combinations: to avoid counting permutations like [1,2] and [2,1] twice, the outer loop must iterate through coins and inner loop through amounts.", "difficulty": "Medium"}
                ],
                "best_practices": [
                    "Always write down the mathematical state definition and base cases explicitly on paper before writing code.",
                    "Start with the top-down recursive solution with memoization to verify correctness, then convert to bottom-up for speed.",
                    "Look for opportunities to compress 2D state matrices into 1D rolling arrays to save O(N) memory."
                ],
                "summary": "Dynamic Programming separates top candidates in FAANG coding interviews. Focus on mastering the 5 core patterns: Knapsack, LCS, LIS, Interval DP, and Tree DP."
            }

        # 4. Default / Dynamic Topic Generator for all other specialized topics
        else:
            return {
                "title": topic_title,
                "stage": stage_title,
                "role": role,
                "executive_summary": f"{topic_title} is a critical architectural pillar within {stage_title} for modern {role} positions. In high-scale production systems, mastering {topic_title} allows engineers to write modular, performant, and resilient software that meets strict Service Level Objectives (SLOs) and scales gracefully across enterprise infrastructures.",
                "internals_and_architecture": f"Internally, {topic_title} operates at the intersection of runtime execution models, memory management, and decoupled software components. Under production workloads, it coordinates data transformations, manages resource lifecycles (such as socket connections, memory allocations, or worker thread pools), and enforces structural boundaries between application subsystems to guarantee fault isolation, high concurrency, and low latency.",
                "key_concepts": [
                    {"name": f"Foundational Principles of {topic_title}", "explanation": f"Core mechanics, syntax specifications, protocol rules, and lifecycle management that govern {topic_title} in enterprise software stacks."},
                    {"name": "Scalability & Concurrency Model", "explanation": "How the system manages asynchronous event loops, non-blocking I/O, worker thread distribution, and memory caching layers."},
                    {"name": "Fault Tolerance & Error Recovery", "explanation": "Architectural boundaries, circuit breakers, graceful degradation, idempotency guarantees, and transactional rollbacks."},
                    {"name": "Security & Observability", "explanation": "Authentication token handshakes, data sanitization, structured logging, distributed tracing headers, and metric telemetry collection."}
                ],
                "complexity_analysis": [
                    {"operation": "Primary Processing & Lookup", "time_complexity": "O(1) to O(N)", "space_complexity": "O(1) to O(N)", "explanation": f"Optimized execution path for standard {topic_title} workflows."},
                    {"operation": "Batch Transformation & Synchronization", "time_complexity": "O(N log N)", "space_complexity": "O(N)", "explanation": "Distributed batch synchronization across worker nodes."},
                    {"operation": "Worst-Case Failover / Reconnect", "time_complexity": "O(N)", "space_complexity": "O(N)", "explanation": "Graceful exponential backoff with jitter during cluster rebalancing."}
                ],
                "code_example": f"""# ==============================================================================
# Production Reference Implementation: {topic_title}
# Designed for {role} Placement & Technical Interviews
# ==============================================================================
import logging
import time
from typing import Dict, Any, Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ProductionServiceManager:
    \"\"\"
    Production-grade enterprise pattern demonstrating {topic_title}.
    Encapsulates state management, error handling, and structured telemetry.
    \"\"\"
    def __init__(self, service_name: str = "{topic_title}"):
        self.service_name = service_name
        self.cache: Dict[str, Any] = {{}}
        self.is_healthy: bool = True
        logger.info(f"Initialized {{self.service_name}} with production safeguards.")

    def process_transaction(self, key: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        \"\"\"
        Executes business logic with O(1) cache lookups and defensive error handling.
        \"\"\"
        start_time = time.time()
        try:
            # Check cache
            if key in self.cache:
                logger.info(f"Cache hit for key: {{key}}")
                return {{"status": "SUCCESS", "source": "CACHE", "data": self.cache[key]}}

            # Process payload
            processed_data = {{
                "key": key,
                "payload": payload,
                "timestamp": int(time.time()),
                "processed_by": self.service_name
            }}
            self.cache[key] = processed_data
            
            latency_ms = (time.time() - start_time) * 1000
            return {{
                "status": "SUCCESS",
                "source": "COMPUTED",
                "latency_ms": round(latency_ms, 2),
                "data": processed_data
            }}
        except Exception as err:
            logger.error(f"Error processing {{key}} in {{self.service_name}}: {{err}}")
            return {{"status": "ERROR", "message": str(err)}}

if __name__ == "__main__":
    service = ProductionServiceManager()
    result = service.process_transaction("user_101", {{"role": "{role}", "module": "{topic_title}"}})
    print("Execution Result:", result)
""",
                "industry_use_cases": [
                    {"company": "Top Tier Tech (FAANG)", "use_case": f"Utilizing {topic_title} principles to optimize service latency, handle millions of queries per second, and reduce memory footprints.", "architecture_impact": "Maintains 99.999% high availability with zero-downtime deployments."},
                    {"company": "Enterprise Cloud Platforms", "use_case": f"Automating resource allocation and container scheduling around {topic_title}.", "architecture_impact": "Cuts infrastructure operational expenditure by 30%."}
                ],
                "common_pitfalls": [
                    f"Failing to handle network timeouts and thread deadlocks in {topic_title} pipelines.",
                    "Neglecting memory cleanup and connection pool exhaustion under high concurrency bursts.",
                    "Ignoring distributed state synchronization and eventual consistency anomalies."
                ],
                "interview_questions": [
                    {"question": f"How do you design a scalable system using {topic_title} under heavy production traffic?", "ideal_answer": f"A scalable architecture using {topic_title} employs decoupled microservices, horizontal worker auto-scaling behind an L7 load balancer, distributed caching (Redis), asynchronous message queues (Kafka/RabbitMQ) for write spikes, and database read-replicas with circuit-breaker protection.", "difficulty": "Hard"},
                    {"question": f"What are the key trade-offs between performance and maintainability when applying {topic_title}?", "ideal_answer": "Extreme performance optimizations often introduce low-level complexity, manual memory management, and tight coupling. Production engineering balances this by writing clean, modular abstractions, profiling before optimizing, and using high-level caching layers first.", "difficulty": "Medium"},
                    {"question": f"How do you debug a critical production latency spike in {topic_title}?", "ideal_answer": "First inspect P95/P99 latency metrics and APM distributed traces (OpenTelemetry/Datadog) to isolate the bottleneck (database lock, external API, CPU throttling). Check garbage collection metrics, thread pool saturation, and error rate surges.", "difficulty": "Hard"},
                    {"question": f"What are the security considerations when implementing {topic_title}?", "ideal_answer": "Enforce strict input validation, sanitize inputs against injection vulnerabilities, implement TLS in transit and AES encryption at rest, apply least-privilege IAM roles, and restrict rate limits to mitigate brute force attacks.", "difficulty": "Medium"},
                    {"question": f"Explain the testing strategy you would establish for {topic_title}.", "ideal_answer": "Implement the Testing Pyramid: 70% isolated Unit Tests with high code coverage, 20% Integration Tests with containerized test databases (Testcontainers), and 10% End-to-End and Chaos/Load Tests (using k6/Locust) to validate SLA boundaries.", "difficulty": "Medium"}
                ],
                "best_practices": [
                    f"Write self-documenting, modular code with strict interface boundaries for {topic_title}.",
                    "Instrument comprehensive telemetry (metrics, structured logs, and distributed traces).",
                    "Implement defensive programming with retries, exponential backoff, and circuit breakers.",
                    "Maintain continuous integration pipelines with automated linting and security scans."
                ],
                "summary": f"Mastering {topic_title} equips you with the exact technical rigor, system design knowledge, and coding discipline demanded by technical interviewers at leading tech firms."
            }

    @staticmethod
    def _mock_next_interview_question(
        role: str,
        interview_type: str,
        history: List[Dict[str, str]],
        job_description: Optional[str] = None,
        experience_level: Optional[str] = "Fresher",
        topic_domain: Optional[str] = "AIML",
        current_difficulty: Optional[str] = "Easy",
        last_turn_correct: bool = True
    ) -> str:
        interviewer_turns = [h for h in history if h.get("role") == "interviewer"]
        candidate_turns = [h for h in history if h.get("role") == "candidate"]
        turn_num = len(interviewer_turns)
        is_fresher = (experience_level or "Fresher").lower() in ["fresher", "entry level", "student", "internship", "junior"]
        domain = (topic_domain or "AIML").upper()
        diff = (current_difficulty or "Easy").capitalize()

        # Turn 1 Opening
        if not candidate_turns:
            if is_fresher:
                if "AI" in domain or "ML" in domain:
                    return (
                        f"Welcome! I am Dr. Alex Vance, your Technical Interviewer for the {role} position today. "
                        f"Since this interview is tailored for fresh graduates and early career engineers, let's start with your academic projects: "
                        f"Could you introduce yourself, walk me through any college or personal software projects you've built, "
                        f"and share which Machine Learning or AI concepts (such as Supervised Learning, Neural Networks, or Generative AI) you are most excited about?"
                    )
                else:
                    return (
                        f"Welcome! I am Dr. Alex Vance, your Technical Interviewer for the {role} position today. "
                        f"Since this interview is tailored for fresh graduates, let's start with your academic background: "
                        f"Could you introduce yourself, highlight your favorite academic or personal projects, "
                        f"and share what core programming languages and data structures you enjoy working with?"
                    )
            else:
                if job_description:
                    return (
                        f"Welcome to your technical screening for the {role} position! To begin our discussion, "
                        f"could you walk me through your engineering stack and describe the most technically complex project you've built?"
                    )
                return (
                    f"Welcome! I am Dr. Alex Vance, your Technical Interviewer for the {role} role today. "
                    f"To start off, please introduce yourself, walk me through your engineering journey, and describe your most challenging engineering project."
                )

        last_ans = candidate_turns[-1].get("text", "").strip()
        last_ans_lower = last_ans.lower()

        # Questions Catalog by Domain and Difficulty
        # 1. AIML Questions
        aiml_questions = {
            "Easy": [
                "Can you explain the fundamental difference between Supervised Learning, Unsupervised Learning, and Reinforcement Learning, and give a simple everyday example of each?",
                "In machine learning, what does 'overfitting' mean, and what are simple techniques (like train/test split or regularization) a developer can use to prevent it?",
                "In modern Generative AI, what is Prompt Engineering, and how does Zero-Shot prompting differ from Few-Shot prompting?",
                "Why is Accuracy alone often misleading when evaluating a model on an imbalanced dataset (like 99% non-fraud vs 1% fraud), and what metric (such as Precision or Recall) would you look at instead?",
                "What is an activation function in a neural network, and why do we need non-linear activations like ReLU rather than just linear combinations?"
            ],
            "Medium": [
                "How does Gradient Descent work to minimize the loss function during model training, and why is selecting an appropriate learning rate critical to avoid divergence or slow convergence?",
                "How does Retrieval-Augmented Generation (RAG) work with vector embeddings and vector databases to prevent Large Language Models from hallucinating on custom enterprise data?",
                "Can you explain the trade-off between Precision and Recall using a healthcare or spam detection scenario? When would you optimize for Recall over Precision?",
                "How does the Self-Attention mechanism in Transformer architectures allow models to understand the contextual relationships between all words in a sentence simultaneously?",
                "What is the difference between Model Pre-training, Fine-tuning, and In-Context prompting, and when would you choose Fine-tuning over prompting?"
            ],
            "Hard": [
                "In the Transformer attention formula Softmax((Q*K^T)/sqrt(d_k))*V, mathematically why is the dot product scaled by the square root of the key dimension d_k, and how do residual skip-connections prevent vanishing gradients?",
                "What are Parameter-Efficient Fine-Tuning (PEFT) methods like LoRA (Low-Rank Adaptation), and how do low-rank decomposition matrices drastically reduce VRAM requirements during LLM training?",
                "How do vanishing and exploding gradients occur mathematically in deep neural networks, and how do Layer Normalization and weight initialization methods (like He or Xavier) resolve them?",
                "When serving Large Language Models in production, how do KV-caching, continuous batching, and speculative decoding optimize inference throughput and reduce latency?"
            ]
        }

        # 2. DSA & CS Core Questions
        dsa_questions = {
            "Easy": [
                "Can you explain the difference between an Array and a Linked List in memory layout and time complexity for insertions and lookups?",
                "What is a Hash Map, and how does it achieve O(1) average lookup time using a hash function?",
                "Can you explain the four core principles of Object-Oriented Programming (OOP) — Encapsulation, Abstraction, Inheritance, and Polymorphism — with a simple real-world example?",
                "What is the difference between a Process and a Thread in an Operating System, and what resources do they share?",
                "In databases, what is the difference between a Primary Key and a Foreign Key, and why are indexes used on columns?"
            ],
            "Medium": [
                "In a Hash Table, how do hash collisions occur, and how do separate chaining (linked lists/trees) and open addressing (linear probing) resolve them?",
                "What is the difference between BFS (Breadth-First Search) and DFS (Depth-First Search) on a graph or tree, and what data structures (Queue vs Stack) are used to implement each?",
                "What are the ACID properties in database transactions, and why is the 'I' (Isolation) property critical when multiple users write data concurrently?",
                "How does a Binary Search Tree (BST) work, and under what conditions can search complexity degrade from O(log N) to O(N)?",
                "How does caching with Redis improve web application performance, and what is the difference between a Cache-Aside and a Write-Through strategy?"
            ],
            "Hard": [
                "How does a self-balancing tree (such as an AVL Tree or Red-Black Tree) maintain balance during insertions, and what rotations are performed?",
                "How does Deadlock occur in concurrent programming, what are the four Coffman conditions, and how does strict lock ordering eliminate deadlocks?",
                "Can you explain how Dijkstra's algorithm finds the shortest path, its time complexity using a Min-Heap, and why it fails with negative edge weights?",
                "How does Optimistic Concurrency Control (version checking) differ from Pessimistic Locking under high contention, and when would you choose one over the other?"
            ]
        }

        # Dynamic Entity Detection for specific technologies mentioned in candidate's answer
        if re.search(r'\b(ai|ml|machine\s*learning|deep\s*learning|neural|llm|transformer|rag|embedding|overfit|gradient|prompt)\b', last_ans_lower):
            pool = aiml_questions.get(diff, aiml_questions["Easy"])
            q_idx = min(len(pool) - 1, max(0, turn_num - 1))
            return pool[q_idx]
        elif re.search(r'\b(hash\s*map|hash\s*table|hashing)\b', last_ans_lower):
            if diff == "Easy":
                return "You mentioned HashMaps. What is a hash function, and why do we say a HashMap has O(1) average lookup time?"
            elif diff == "Medium":
                return "You specifically mentioned using HashMaps. How does collision resolution work internally (e.g. separate chaining vs open addressing), and how does the load factor trigger resizing?"
            else:
                return "Following up on HashMaps: in a multithreaded high-throughput service, how do you make HashMap access thread-safe without introducing severe mutex lock contention?"
        elif re.search(r'\b(redis|cache|caching)\b', last_ans_lower):
            if diff == "Easy":
                return "You mentioned caching. Can you explain what a cache is, and why storing frequently accessed data in RAM is faster than disk databases?"
            elif diff == "Medium":
                return "You mentioned Redis caching. How do you choose an eviction policy (like allkeys-lru vs volatile-ttl), and how do you protect against cache stampedes?"
            else:
                return "In a distributed Redis cluster, how do you handle cache invalidation consistency across read replicas, and how do you maintain sub-50ms P99 latency during node failovers?"
        elif re.search(r'\b(sql|database|postgres|mysql|sqlite|acid)\b', last_ans_lower):
            if diff == "Easy":
                return "You mentioned databases. What is the difference between a Primary Key and a Foreign Key in SQL tables?"
            elif diff == "Medium":
                return "You discussed relational databases. How do B-Tree indexes speed up WHERE filtering, and what is the write overhead trade-off during inserts?"
            else:
                return "When scaling relational databases across availability zones, how do you manage replication lag on read replicas, and what isolation level prevents phantom reads?"

        # Fallback to domain pool
        is_aiml_domain = "AI" in domain or "ML" in domain
        pool = aiml_questions.get(diff, aiml_questions["Easy"]) if is_aiml_domain else dsa_questions.get(diff, dsa_questions["Easy"])
        q_idx = min(len(pool) - 1, max(0, turn_num - 1))
        return pool[q_idx]

    @staticmethod
    def _mock_evaluate_turn(
        role: str,
        interview_type: str,
        question: str,
        answer: str,
        history: List[Dict[str, str]],
        job_description: Optional[str] = None,
        experience_level: Optional[str] = "Fresher",
        topic_domain: Optional[str] = "AIML",
        current_difficulty: Optional[str] = "Easy"
    ) -> Dict[str, Any]:
        ans_clean = (answer or "").strip()
        words = ans_clean.split()
        word_count = len(words)
        ans_lower = ans_clean.lower()
        cur_diff = (current_difficulty or "Easy").capitalize()

        # Detect if answer is poor, empty, "I don't know", or "not even close to right"
        is_dont_know = bool(re.search(r"\b(don't know|dont know|not sure|no idea|cannot answer|can't answer|skip|dunno)\b", ans_lower))
        is_too_brief = word_count < 6
        is_wrong = is_dont_know or is_too_brief

        # Technical concepts indicators
        tech_indicators = [
            'supervised', 'unsupervised', 'overfitting', 'underfitting', 'regularization', 'gradient',
            'learning rate', 'prompt', 'rag', 'embedding', 'transformer', 'attention', 'precision',
            'recall', 'f1', 'loss', 'neural', 'weights', 'bias', 'time complexity', 'space complexity',
            'o(1)', 'o(n)', 'hash', 'array', 'linked list', 'tree', 'database', 'sql', 'cache',
            'process', 'thread', 'encapsulation', 'inheritance', 'polymorphism'
        ]
        matched_indicators = [ind for ind in tech_indicators if ind in ans_lower]
        is_sound = not is_wrong and (len(matched_indicators) >= 1 or word_count >= 16)

        # ADAPTIVE DIFFICULTY ENGINE:
        # If answer is wrong / not even close to right -> DECREASE difficulty (or stay Easy)
        # If answer is solid -> INCREASE difficulty (or stay Hard)
        diff_order = ["Easy", "Medium", "Hard"]
        cur_idx = diff_order.index(cur_diff) if cur_diff in diff_order else 0

        if not is_sound:
            is_correct = False
            # Step down difficulty (same level if already Easy, else level lower)
            new_idx = max(0, cur_idx - 1)
            new_diff = diff_order[new_idx]
            diff_change = "decreased" if new_idx < cur_idx else "same"

            # Formulate foundational question
            next_q = AIService._mock_next_interview_question(
                role, interview_type, history, job_description,
                experience_level=experience_level, topic_domain=topic_domain,
                current_difficulty=new_diff, last_turn_correct=False
            )

            turn_score = 42 if is_dont_know else 50
            conf = 52
            ai_fb = "That answer was missing the key theoretical concepts. In technical interviews, clearly define terms, explain mechanisms, and cite examples."
            correction = "Always start with a clear definition, state the underlying mathematical or algorithmic principle, and give a concrete example."
            ideal = "A solid answer provides the core definition, explains the mechanism, and compares trade-offs."
            speech = f"That's completely okay! Let's take a step back and anchor on the foundational concept: {next_q}"

            return {
                "is_correct": False,
                "assessment": "Needs Correction (Adapted to Foundational Level)",
                "score_on_turn": turn_score,
                "confidence_estimate": conf,
                "difficulty": new_diff,
                "difficulty_change": diff_change,
                "ai_immediate_feedback": ai_fb,
                "ai_correction": correction,
                "ideal_answer": ideal,
                "next_question": next_q,
                "speech_text_to_speak": speech
            }
        else:
            is_correct = True
            # Step up difficulty if strong
            new_idx = min(len(diff_order) - 1, cur_idx + 1)
            new_diff = diff_order[new_idx]
            diff_change = "increased" if new_idx > cur_idx else "same"

            next_q = AIService._mock_next_interview_question(
                role, interview_type, history, job_description,
                experience_level=experience_level, topic_domain=topic_domain,
                current_difficulty=new_diff, last_turn_correct=True
            )

            highlight = f"regarding {matched_indicators[0]}" if matched_indicators else "in your technical breakdown"
            ai_fb = f"Excellent articulation! You accurately covered the core principles {highlight}."
            turn_score = min(96, 82 + min(word_count // 4, 14))
            conf = min(98, 85 + min(word_count // 3, 13))
            ideal = "Strong answers identify primary concepts, analyze trade-offs, and address real-world edge cases."
            speech = f"Great explanation! You covered that concept {highlight} very well. Now let's elevate the technical depth: {next_q}"

            return {
                "is_correct": True,
                "assessment": f"Strong Answer (Advanced to {new_diff} Level)" if diff_change == "increased" else "Strong Answer",
                "score_on_turn": turn_score,
                "confidence_estimate": conf,
                "difficulty": new_diff,
                "difficulty_change": diff_change,
                "ai_immediate_feedback": ai_fb,
                "ai_correction": None,
                "ideal_answer": ideal,
                "next_question": next_q,
                "speech_text_to_speak": speech
            }

    @staticmethod
    def _mock_interview_analyzer(role: str, interview_type: str, history: List[Dict[str, str]], job_description: Optional[str] = None) -> Dict[str, Any]:
        candidate_answers = [h.get("text", "") for h in history if h.get("role") == "candidate"]
        word_count = sum(len(a.split()) for a in candidate_answers)
        avg_words = word_count / max(1, len(candidate_answers))
        
        base_score = 70
        if len(candidate_answers) >= 4: base_score += 10
        if avg_words >= 25: base_score += 10
        
        technical = min(base_score + 2, 96)
        communication = min(base_score + 4, 98)
        confidence = min(base_score + 1, 95)
        problem_solving = min(base_score - 1, 94)
        leadership = min(base_score - 2, 92)
        overall = int((technical + communication + confidence + problem_solving + leadership) / 5)
        
        return {
            "technical_score": technical,
            "communication_score": communication,
            "confidence_score": confidence,
            "problem_solving_score": problem_solving,
            "leadership_score": leadership,
            "overall_score": overall,
            "feedback": {
                "strengths": [
                    "Structured communication using concise engineering terminology",
                    f"Strong conceptual understanding aligned with {role} requirements",
                    "Maintained positive tone and good problem deconstruction"
                ],
                "weaknesses": [
                    "Could explicitly state Big-O Time & Space complexity upfront before detailing architectures",
                    "Minor hesitation when explaining low-level concurrency and memory bounds",
                    "Could use the STAR format more explicitly for behavioral scenarios"
                ],
                "mistakes": [
                    "In system architecture, remember to specify Cache Invalidation strategies (Cache-Aside vs Write-Through).",
                    "When discussing rate limiters, explain why Redis Sliding Window is more accurate than Fixed Window."
                ],
                "ideal_answers": [
                    {
                        "question": "How do you architect high-throughput distributed APIs?",
                        "ideal_answer": "Use asynchronous event loops (FastAPI / Node), horizontal worker scaling behind an L7 load balancer, Redis distributed caching with TTLs, and connection pooling for the database."
                    }
                ],
                "suggestions": [
                    "Pause for 2-3 seconds after hearing the question to organize your response structure.",
                    "Always mention potential bottlenecks (CPU, I/O, Network) and how you monitor them in production.",
                    "Practice live speech dry-runs with our AI Voice interviewer to build effortless speaking fluency."
                ],
                "practice_plan": [
                    "Day 1-2: Review Top 15 System Design patterns (Rate Limiting, Sharding, Caching).",
                    "Day 3-4: Solve 5 LeetCode Medium problems focusing on Tree Traversal and Graphs.",
                    "Day 5-7: Re-take AI Mock Interview with live voice to aim for a 90%+ confidence rating."
                ]
            }
        }

    @staticmethod
    def _mock_career_chat(query: str, history: List[Dict[str, str]] = None) -> Dict[str, Any]:
        return CareerKnowledgeEngine.get_response(query, history)
