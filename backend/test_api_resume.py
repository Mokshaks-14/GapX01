import io
from fastapi.testclient import TestClient
from app.main import app
from app.services.pdf_generator import PDFResumeGenerator

client = TestClient(app)

print("================ INTEGRATION TEST: FASTAPI RESUME ENDPOINTS ================")

# 1. Register test user
reg_res = client.post("/api/v1/auth/register", json={
    "email": "test_resume_user@gapx.ai",
    "password": "Password123!",
    "full_name": "Alex Developer"
})
print("Register Status:", reg_res.status_code)
if reg_res.status_code == 200:
    token = reg_res.json()["access_token"]
else:
    login_res = client.post("/api/v1/auth/login", json={
        "email": "test_resume_user@gapx.ai",
        "password": "Password123!"
    })
    token = login_res.json()["access_token"]

headers = {"Authorization": f"Bearer {token}"}

# 2. Test Onboarding user with target role
client.post("/api/v1/users/onboard", json={
    "role": "Student",
    "education": "B.Tech Computer Science",
    "semester": "Final Year",
    "skills": ["Python", "React", "PostgreSQL", "Docker"],
    "languages_known": ["English", "Hindi"],
    "experience_level": "Intermediate",
    "target_roles": ["Software Engineer"]
}, headers=headers)

# 3. Generate a sample PDF resume in memory
sample_resume_data = {
    "name": "Alex Developer",
    "email": "test_resume_user@gapx.ai",
    "headline": "Full Stack Software Engineer",
    "skills": ["Python", "FastAPI", "React", "TypeScript", "Node.js", "PostgreSQL", "Docker", "Git", "Data Structures & Algorithms", "System Design"],
    "languages": ["Python", "JavaScript", "TypeScript", "SQL"],
    "tools": ["Docker", "Git", "Postman", "AWS"],
    "education": "Bachelor of Technology in Computer Science",
    "semester": "Final Year 2026",
    "cgpa": "9.2",
    "projects": [
        {
            "title": "Cloud Scale ATS Scanner",
            "stack": "React, FastAPI, PostgreSQL, Docker",
            "bullets": [
                "Architected high-throughput microservices processing 10k documents/min with Redis caching.",
                "Optimized database query indexing improving execution speed by 40%."
            ]
        }
    ],
    "experience": [
        {
            "title": "Software Engineering Intern",
            "company": "NextGen AI Corp",
            "dates": "May 2024 - August 2024",
            "bullets": [
                "Implemented secure OAuth2 authentication and RESTful APIs serving 50k active users."
            ]
        }
    ],
    "certifications": ["AWS Certified Cloud Practitioner"]
}

pdf_buf = PDFResumeGenerator.generate_resume_pdf(sample_resume_data)
pdf_bytes = pdf_buf.getvalue()

# 4. Test POST /api/v1/resumes/upload
upload_res = client.post(
    "/api/v1/resumes/upload",
    files={"file": ("Alex_Developer_Resume.pdf", pdf_bytes, "application/pdf")},
    headers=headers
)
print("Upload Status Code:", upload_res.status_code)
upload_json = upload_res.json()
print("Upload ATS Score:", upload_json.get("ats_score"))
print("Upload Readiness:", upload_json.get("readiness_level"))
assert upload_res.status_code == 200, f"Upload failed: {upload_res.text}"
assert upload_json.get("ats_score", 0) >= 85, f"ATS score {upload_json.get('ats_score')} is too low for a valid resume!"
print("[PASS] Upload PDF Endpoint test PASSED")

# 5. Test GET /api/v1/resumes/latest
latest_res = client.get("/api/v1/resumes/latest", headers=headers)
print("Latest Status Code:", latest_res.status_code)
assert latest_res.status_code == 200
latest_json = latest_res.json()
assert latest_json.get("ats_score") == upload_json.get("ats_score")
print("[PASS] GET /resumes/latest test PASSED")

# 6. Test POST /api/v1/resumes/manual (Builder)
manual_res = client.post(
    "/api/v1/resumes/manual",
    json=sample_resume_data,
    headers=headers
)
print("Manual Builder Status Code:", manual_res.status_code)
assert manual_res.status_code == 200
manual_json = manual_res.json()
assert manual_json.get("ats_score", 0) >= 85
print("[PASS] Manual Builder Endpoint test PASSED")

# 7. Test POST /api/v1/resumes/download-pdf
download_res = client.post(
    "/api/v1/resumes/download-pdf",
    json=sample_resume_data,
    headers=headers
)
print("Download PDF Status Code:", download_res.status_code)
assert download_res.status_code == 200
assert download_res.headers.get("content-type") == "application/pdf"
assert len(download_res.content) > 1000
print("[PASS] Download PDF Endpoint test PASSED")

# 8. Test Invalid File Extension Rejection
invalid_res = client.post(
    "/api/v1/resumes/upload",
    files={"file": ("malicious.exe", b"binary content", "application/octet-stream")},
    headers=headers
)
print("Invalid file status code:", invalid_res.status_code)
assert invalid_res.status_code == 400
print("[PASS] Invalid File Rejection test PASSED")

print("\n================ ALL FASTAPI RESUME INTEGRATION TESTS PASSED! ================")
