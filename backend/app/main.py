from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.database import Base, engine, get_db
from app.routers import auth, users, resumes, roadmaps, coding, interviews, mentor, admin
from app import models
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create Database tables on startup
Base.metadata.create_all(bind=engine)

app = FastAPI(title=settings.PROJECT_NAME, version=settings.VERSION)

# Enable CORS for Next.js frontend calls
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In production, restrict to your frontend domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Routers
app.include_router(auth.router, prefix=settings.API_V1_STR)
app.include_router(users.router, prefix=settings.API_V1_STR)
app.include_router(resumes.router, prefix=settings.API_V1_STR)
app.include_router(roadmaps.router, prefix=settings.API_V1_STR)
app.include_router(coding.router, prefix=settings.API_V1_STR)
app.include_router(interviews.router, prefix=settings.API_V1_STR)
app.include_router(mentor.router, prefix=settings.API_V1_STR)
app.include_router(admin.router, prefix=settings.API_V1_STR)

from app.services.problem_data import PROBLEMS_DATA

# Database seed function for coding questions (30 rich LeetCode-style problems)
def seed_problems(db: Session):
    try:
        existing_problems = {p.title: p for p in db.query(models.CodingProblem).all()}
    except Exception as e:
        logger.warning(f"Database schema mismatch detected ({e}). Recreating tables...")
        db.rollback()
        Base.metadata.drop_all(bind=engine)
        Base.metadata.create_all(bind=engine)
        existing_problems = {}
        
    logger.info("Synchronizing comprehensive 30 LeetCode-style coding problems...")
    
    for d in PROBLEMS_DATA:
        title = d["title"]
        if title in existing_problems:
            p = existing_problems[title]
            p.difficulty = d.get("difficulty", p.difficulty)
            p.category = d.get("category", p.category)
            p.company_tags = d.get("company_tags", p.company_tags)
            p.problem_statement = d.get("problem_statement", p.problem_statement)
            p.constraints = d.get("constraints", p.constraints)
            p.input_format = d.get("input_format", p.input_format)
            p.output_format = d.get("output_format", p.output_format)
            p.example_input = d.get("example_input", p.example_input)
            p.example_output = d.get("example_output", p.example_output)
            p.explanation = d.get("explanation", p.explanation)
            p.expected_time_complexity = d.get("expected_time_complexity", p.expected_time_complexity)
            p.expected_space_complexity = d.get("expected_space_complexity", p.expected_space_complexity)
            p.starter_code_python = d.get("starter_code_python", p.starter_code_python)
            p.starter_code_java = d.get("starter_code_java", p.starter_code_java)
            p.starter_code_cpp = d.get("starter_code_cpp", p.starter_code_cpp)
            p.starter_code_js = d.get("starter_code_js", p.starter_code_js)
            p.hints = d.get("hints", p.hints)
            p.test_cases = d.get("test_cases", p.test_cases)
            p.editorial = d.get("editorial", p.editorial)
        else:
            db.add(models.CodingProblem(
                title=d["title"],
                difficulty=d.get("difficulty", "Medium"),
                category=d.get("category", "Algorithms"),
                company_tags=d.get("company_tags", ["Top Tech"]),
                problem_statement=d.get("problem_statement", ""),
                constraints=d.get("constraints", ""),
                input_format=d.get("input_format", ""),
                output_format=d.get("output_format", ""),
                example_input=d.get("example_input", ""),
                example_output=d.get("example_output", ""),
                explanation=d.get("explanation", ""),
                expected_time_complexity=d.get("expected_time_complexity", "O(N)"),
                expected_space_complexity=d.get("expected_space_complexity", "O(1)"),
                starter_code_python=d.get("starter_code_python", ""),
                starter_code_java=d.get("starter_code_java", ""),
                starter_code_cpp=d.get("starter_code_cpp", ""),
                starter_code_js=d.get("starter_code_js", ""),
                hints=d.get("hints", []),
                test_cases=d.get("test_cases", []),
                editorial=d.get("editorial", "")
            ))
            
    db.commit()
    logger.info("Successfully synchronized coding problem database!")

@app.on_event("startup")
def startup_event():
    # Run seed function using local session maker
    from app.core.database import SessionLocal
    db = SessionLocal()
    try:
        seed_problems(db)
    finally:
        db.close()

@app.get("/")
def read_root():
    return {"message": "Welcome to GapX AI Placement Preparation API. Check /docs for swagger specs!"}
