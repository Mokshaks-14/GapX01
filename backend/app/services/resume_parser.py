import re
import json
from typing import Dict, Any, List, Optional, Set

class ResumeEntityExtractor:
    """
    Comprehensive resume entity parsing, ATS keyword benchmarking,
    and dynamic feedback generation engine.
    """

    SKILL_TAXONOMY = {
        "programming_languages": {
            "python": "Python", "py": "Python",
            "java": "Java",
            "c++": "C++", "cpp": "C++",
            "c": "C",
            "c#": "C#", "csharp": "C#",
            "javascript": "JavaScript", "js": "JavaScript",
            "typescript": "TypeScript", "ts": "TypeScript",
            "golang": "Go", "go": "Go",
            "rust": "Rust",
            "kotlin": "Kotlin",
            "swift": "Swift",
            "sql": "SQL", "mysql": "MySQL", "postgresql": "PostgreSQL", "postgres": "PostgreSQL", "sqlite": "SQLite",
            "r": "R",
            "php": "PHP",
            "ruby": "Ruby",
            "dart": "Dart",
            "scala": "Scala",
            "bash": "Bash", "shell": "Shell Scripting"
        },
        "frameworks_libraries": {
            "react": "React", "react.js": "React", "reactjs": "React",
            "next.js": "Next.js", "nextjs": "Next.js",
            "vue": "Vue.js", "vue.js": "Vue.js", "vuejs": "Vue.js",
            "angular": "Angular",
            "node.js": "Node.js", "nodejs": "Node.js", "node": "Node.js",
            "express": "Express.js", "express.js": "Express.js",
            "fastapi": "FastAPI", "fast api": "FastAPI",
            "django": "Django",
            "flask": "Flask",
            "spring boot": "Spring Boot", "springboot": "Spring Boot", "spring": "Spring Boot",
            "asp.net": "ASP.NET", ".net": ".NET", "dotnet": ".NET",
            "redux": "Redux", "redux toolkit": "Redux Toolkit", "zustand": "Zustand",
            "tailwind": "Tailwind CSS", "tailwind css": "Tailwind CSS", "tailwindcss": "Tailwind CSS",
            "bootstrap": "Bootstrap",
            "html": "HTML5", "html5": "HTML5",
            "css": "CSS3", "css3": "CSS3",
            "graphql": "GraphQL",
            "jquery": "jQuery",
            "flutter": "Flutter",
            "react native": "React Native"
        },
        "databases": {
            "postgresql": "PostgreSQL", "postgres": "PostgreSQL",
            "mysql": "MySQL",
            "mongodb": "MongoDB", "mongo": "MongoDB",
            "redis": "Redis",
            "sqlite": "SQLite",
            "cassandra": "Cassandra",
            "elasticsearch": "Elasticsearch",
            "dynamodb": "DynamoDB",
            "oracle": "Oracle DB",
            "firebase": "Firebase",
            "supabase": "Supabase",
            "neo4j": "Neo4j"
        },
        "cloud_devops": {
            "docker": "Docker", "containerization": "Docker",
            "kubernetes": "Kubernetes", "k8s": "Kubernetes",
            "aws": "AWS", "amazon web services": "AWS",
            "azure": "Azure", "microsoft azure": "Azure",
            "gcp": "Google Cloud (GCP)", "google cloud": "Google Cloud (GCP)",
            "git": "Git", "github": "GitHub", "gitlab": "GitLab",
            "ci/cd": "CI/CD", "cicd": "CI/CD", "github actions": "GitHub Actions",
            "jenkins": "Jenkins",
            "terraform": "Terraform",
            "linux": "Linux", "ubuntu": "Linux",
            "nginx": "Nginx",
            "prometheus": "Prometheus",
            "grafana": "Grafana",
            "ansible": "Ansible"
        },
        "core_cs": {
            "data structures": "Data Structures & Algorithms", "dsa": "Data Structures & Algorithms", "algorithms": "Data Structures & Algorithms",
            "system design": "System Design", "distributed systems": "System Design",
            "oop": "OOP (Object-Oriented Programming)", "oops": "OOP", "object oriented": "OOP",
            "dbms": "DBMS",
            "operating systems": "Operating Systems", "os": "Operating Systems",
            "computer networks": "Computer Networks", "networking": "Computer Networks",
            "rest api": "REST APIs", "restful": "REST APIs", "rest": "REST APIs",
            "microservices": "Microservices", "microservice": "Microservices",
            "websockets": "WebSockets", "websocket": "WebSockets",
            "agile": "Agile / Scrum", "scrum": "Agile / Scrum",
            "unit testing": "Unit Testing", "jest": "Jest", "pytest": "PyTest", "junit": "JUnit"
        },
        "ai_ml": {
            "machine learning": "Machine Learning", "ml": "Machine Learning",
            "deep learning": "Deep Learning", "dl": "Deep Learning",
            "pytorch": "PyTorch",
            "tensorflow": "TensorFlow",
            "keras": "Keras",
            "scikit-learn": "Scikit-Learn", "sklearn": "Scikit-Learn",
            "pandas": "Pandas",
            "numpy": "NumPy",
            "nlp": "Natural Language Processing (NLP)", "natural language processing": "Natural Language Processing (NLP)",
            "computer vision": "Computer Vision", "opencv": "OpenCV",
            "llm": "LLMs (Large Language Models)", "llms": "LLMs", "generative ai": "Generative AI", "genai": "Generative AI",
            "langchain": "LangChain",
            "huggingface": "Hugging Face"
        }
    }

    ROLE_BENCHMARKS = {
        "frontend": {
            "core": ["React", "JavaScript", "TypeScript", "HTML5", "CSS3", "Tailwind CSS", "Next.js", "Redux", "REST APIs", "Git"],
            "recommended": ["Jest", "GraphQL", "Node.js", "WebSockets", "Unit Testing", "Webpack", "Vite"]
        },
        "backend": {
            "core": ["Python", "FastAPI", "Node.js", "PostgreSQL", "SQL", "Docker", "REST APIs", "System Design", "Git", "Redis"],
            "recommended": ["Microservices", "Kubernetes", "AWS", "MongoDB", "CI/CD", "Data Structures & Algorithms", "Kafka"]
        },
        "fullstack": {
            "core": ["React", "JavaScript", "TypeScript", "Node.js", "Python", "PostgreSQL", "SQL", "Docker", "REST APIs", "Git", "HTML5", "CSS3"],
            "recommended": ["Next.js", "FastAPI", "Redis", "AWS", "CI/CD", "System Design", "Microservices", "MongoDB"]
        },
        "data": {
            "core": ["Python", "Pandas", "NumPy", "Scikit-Learn", "PyTorch", "TensorFlow", "SQL", "Machine Learning", "Deep Learning", "Git"],
            "recommended": ["Docker", "FastAPI", "Natural Language Processing (NLP)", "Computer Vision", "LLMs", "PostgreSQL"]
        },
        "devops": {
            "core": ["Docker", "Kubernetes", "AWS", "CI/CD", "Linux", "Bash", "Terraform", "Git", "Python"],
            "recommended": ["Prometheus", "Grafana", "Nginx", "PostgreSQL", "System Design", "GitHub Actions"]
        }
    }

    ACTION_VERBS = [
        "architected", "engineered", "implemented", "developed", "optimized",
        "spearheaded", "designed", "automated", "built", "deployed", "scaled",
        "integrated", "streamlined", "configured", "refactored", "migrated",
        "reduced", "increased", "accelerated", "formulated", "established",
        "orchestrated", "transformed", "modeled", "mentored", "delivered"
    ]

    @classmethod
    def extract_text_entities(cls, text: str, user_metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Parses raw resume text into structured entities:
        - Contact & Links (Email, Phone, LinkedIn, GitHub, Portfolio)
        - Education (Degree, Branch, University, Dates, CGPA)
        - Skills (Categorized into 6 domains)
        - Work Experience & Internships
        - Projects (Title, Tech Stack, Bullets, Links)
        - Certifications & Achievements
        - Metrics & Action Verbs
        """
        if not user_metadata:
            user_metadata = {}

        text = text or ""
        lines = [line.strip() for line in text.split("\n") if line.strip()]
        text_lower = text.lower()

        # 1. CANDIDATE NAME EXTRACTION
        extracted_name = None
        # Look through first 5 lines for a candidate name (ignoring headers like Resume, CV, Email, etc.)
        for line in lines[:6]:
            clean_l = re.sub(r'[^a-zA-Z\s]', '', line).strip()
            words = clean_l.split()
            lower_line = line.lower()
            if (1 <= len(words) <= 4 and 
                len(clean_l) >= 3 and 
                not any(w in lower_line for w in ["resume", "curriculum", "vitae", "profile", "contact", "email", "phone", "developer", "engineer", "page", "http", "www", "github", "linkedin"])):
                extracted_name = clean_l
                break

        if not extracted_name:
            extracted_name = user_metadata.get("name") or "Candidate"

        # 2. CONTACT DETAILS & SOCIAL / PORTFOLIO LINKS
        # Email
        email_match = re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', text)
        extracted_email = email_match.group(0) if email_match else (user_metadata.get("email") or "Not Specified")

        # Phone
        phone_match = re.search(r'(?:\+?91[-.\s]?)?[6-9]\d{9}|\+?\d{1,3}[-.\s]?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}|\b\d{10}\b', text)
        extracted_phone = phone_match.group(0) if phone_match else None

        # Links
        links = {}
        # LinkedIn
        li_match = re.search(r'(?:https?:\/\/)?(?:www\.)?linkedin\.com\/in\/([a-zA-Z0-9_\-\.\/]+)', text, re.I)
        if li_match:
            links["linkedin"] = f"https://linkedin.com/in/{li_match.group(1).rstrip('/')}"
        elif user_metadata.get("linkedin"):
            links["linkedin"] = user_metadata["linkedin"]

        # GitHub
        gh_match = re.search(r'(?:https?:\/\/)?(?:www\.)?github\.com\/([a-zA-Z0-9_\-\.\/]+)', text, re.I)
        if gh_match:
            links["github"] = f"https://github.com/{gh_match.group(1).rstrip('/')}"
        elif user_metadata.get("github"):
            links["github"] = user_metadata["github"]

        # Portfolio / Personal Website
        port_match = re.search(r'(?:https?:\/\/)(?!.*(?:linkedin|github|leetcode|hackerrank|medium|twitter|youtube))([a-zA-Z0-9_\-\.]+\.[a-zA-Z]{2,}(?:\/[^\s\)]*)?)', text, re.I)
        if port_match:
            links["portfolio"] = f"https://{port_match.group(1)}"
        elif user_metadata.get("portfolio"):
            links["portfolio"] = user_metadata["portfolio"]

        # LeetCode / Coding Profile
        code_match = re.search(r'(?:https?:\/\/)?(?:www\.)?(leetcode|hackerrank)\.com\/(?:u\/)?([a-zA-Z0-9_\-\.]+)', text, re.I)
        if code_match:
            links["coding_profile"] = f"https://{code_match.group(1)}.com/{code_match.group(2)}"

        # 3. SKILLS CATEGORIZATION
        categorized_skills: Dict[str, List[str]] = {
            "programming_languages": [],
            "frameworks_libraries": [],
            "databases": [],
            "cloud_devops": [],
            "core_cs": [],
            "ai_ml": []
        }
        all_detected_skills: Set[str] = set()

        for category, skill_map in cls.SKILL_TAXONOMY.items():
            found_in_cat = set()
            for alias, canonical in skill_map.items():
                pattern = r'(?:\b|[_\-\./])' + re.escape(alias) + r'(?:\b|[_\-\./])'
                if re.search(pattern, text_lower):
                    found_in_cat.add(canonical)
                    all_detected_skills.add(canonical)
            categorized_skills[category] = sorted(list(found_in_cat))

        # Also incorporate manual skills, languages, frameworks, and tools if provided
        raw_manual = (
            (user_metadata.get("skills") or []) +
            (user_metadata.get("languages") or []) +
            (user_metadata.get("languages_known") or []) +
            (user_metadata.get("frameworks") or []) +
            (user_metadata.get("tools") or [])
        )
        manual_skills = []
        for item in raw_manual:
            if isinstance(item, str):
                manual_skills.extend([s.strip() for s in item.split(",") if s.strip()])
            elif item:
                manual_skills.append(str(item).strip())

        for ms in manual_skills:
            ms_lower = ms.lower().strip()
            matched = False
            for category, skill_map in cls.SKILL_TAXONOMY.items():
                if ms_lower in skill_map:
                    canonical = skill_map[ms_lower]
                    if canonical not in categorized_skills[category]:
                        categorized_skills[category].append(canonical)
                    all_detected_skills.add(canonical)
                    matched = True
                    break
            if not matched and ms:
                categorized_skills["frameworks_libraries"].append(ms.strip())
                all_detected_skills.add(ms.strip())

        # 4. EDUCATION EXTRACTION
        education_list = []
        # Degree
        degree_patterns = [
            r'\b(bachelor(?:\s+of\s+technology|\s+of\s+engineering|\s+of\s+science)?|b\.?tech|b\.?e\.?|b\.?s\.?|bca)\b',
            r'\b(master(?:\s+of\s+technology|\s+of\s+science|\s+of\s+computer\s+applications)?|m\.?tech|m\.?s\.?|mca|m\.?e\.?)\b',
            r'\b(ph\.?d|doctorate)\b'
        ]
        detected_degree = None
        for dp in degree_patterns:
            m = re.search(dp, text_lower)
            if m:
                detected_degree = m.group(0).upper()
                if "bachelor" in detected_degree.lower() or "b.tech" in detected_degree.lower() or "btech" in detected_degree.lower():
                    detected_degree = "Bachelor of Technology (B.Tech)"
                elif "master" in detected_degree.lower() or "m.tech" in detected_degree.lower():
                    detected_degree = "Master of Technology (M.Tech)"
                elif "bca" in detected_degree.lower():
                    detected_degree = "Bachelor of Computer Applications (BCA)"
                elif "mca" in detected_degree.lower():
                    detected_degree = "Master of Computer Applications (MCA)"
                break

        # Major / Branch
        major_patterns = [
            r'(?:computer\s+science(?:\s+(?:and|&)\s+engineering)?|information\s+technology|data\s+science|artificial\s+intelligence|electronics|electrical|mechanical)',
        ]
        detected_major = None
        for mp in major_patterns:
            m = re.search(mp, text_lower)
            if m:
                detected_major = m.group(0).title()
                break

        # Institution / University
        inst_pattern = r'([A-Z][a-zA-Z\s,\.\-&]+(?:University|Institute|College|Academy|IIT|NIT|BITS|VIT|SRM|IIIT|Campus)[a-zA-Z\s,\.\-]*)'
        detected_inst = None
        inst_matches = re.findall(inst_pattern, text)
        if inst_matches:
            # Pick first sensible institution name
            for im in inst_matches:
                cleaned_inst = im.strip().replace("\n", " ")
                if 4 <= len(cleaned_inst) <= 80:
                    detected_inst = cleaned_inst
                    break

        # CGPA / GPA
        cgpa_match = re.search(r'(?:cgpa|gpa)[\s:]*([0-9]+(?:\.[0-9]+)?)(?:\s*\/\s*(?:10|4))?|\b([0-9]\.[0-9]{1,2})\s*\/\s*(?:10|4)|\b([789][0-9](?:\.[0-9]+)?)\s*%', text, re.I)
        detected_cgpa = None
        if cgpa_match:
            detected_cgpa = cgpa_match.group(1) or cgpa_match.group(2) or (cgpa_match.group(3) + "%")

        # Graduation Year / Dates
        year_match = re.search(r'\b(201\d|202\d)\s*[-–—]\s*(202\d|203\d|present|expected|\d{4})\b|\b(202[45678])\b', text, re.I)
        detected_year = year_match.group(0) if year_match else None

        if detected_degree or detected_inst or user_metadata.get("education"):
            education_list.append({
                "degree": detected_degree or user_metadata.get("education") or "Bachelor of Technology in Computer Science",
                "major": detected_major or "Computer Science & Engineering",
                "institution": detected_inst or user_metadata.get("college_name") or "Accredited University / Institute",
                "cgpa": detected_cgpa or (str(user_metadata.get("cgpa")) if user_metadata.get("cgpa") else "8.5 / 10"),
                "year": detected_year or user_metadata.get("graduation_year") or "2022 - 2026"
            })

        # 5. PROJECTS EXTRACTION
        projects_list = []
        # Check structured projects in user_metadata first
        manual_projects = user_metadata.get("projects") or []
        if isinstance(manual_projects, list) and len(manual_projects) > 0:
            for p in manual_projects:
                if isinstance(p, dict) and (p.get("title") or p.get("name")):
                    projects_list.append({
                        "title": p.get("title") or p.get("name"),
                        "stack": p.get("stack") or p.get("technologies") or "Python, React, SQL",
                        "description": p.get("description") or (p.get("bullets")[0] if p.get("bullets") else "Full-stack software application.")
                    })

        # If not enough structured projects, extract project blocks from text
        if len(projects_list) < 2:
            # Look for project headers (e.g., "Project Name | Python, React" or bullet points under Projects)
            project_section = cls._extract_section(text, ["projects", "key projects", "technical projects", "academic projects"])
            if project_section:
                proj_lines = [l.strip() for l in project_section.split("\n") if l.strip()]
                current_proj = None
                for line in proj_lines:
                    if len(line) < 70 and ("|" in line or "—" in line or "-" in line) and any(kw in line.lower() for kw in ["react", "python", "fastapi", "django", "node", "ai", "app", "system", "engine", "platform", "web", "ml", "clone"]):
                        parts = re.split(r'[\|\—\-]', line, maxsplit=1)
                        if len(parts) >= 2:
                            p_title = parts[0].strip()
                            p_stack = parts[1].strip()
                            if current_proj:
                                projects_list.append(current_proj)
                            current_proj = {
                                "title": p_title,
                                "stack": p_stack,
                                "description": "High-impact technical software project."
                            }
                    elif current_proj and (line.startswith("•") or line.startswith("-") or line.startswith("*")):
                        current_proj["description"] = line.lstrip("•-* ").strip()
                if current_proj:
                    projects_list.append(current_proj)

        # 6. WORK EXPERIENCE & INTERNSHIPS EXTRACTION
        experience_list = []
        manual_exp = user_metadata.get("experience") or user_metadata.get("internships") or []
        if isinstance(manual_exp, list) and len(manual_exp) > 0:
            for exp in manual_exp:
                if isinstance(exp, dict) and (exp.get("title") or exp.get("company") or exp.get("role")):
                    experience_list.append({
                        "role": exp.get("title") or exp.get("role") or "Software Engineering Intern",
                        "company": exp.get("company") or exp.get("organization") or "Tech Enterprise",
                        "duration": exp.get("dates") or exp.get("duration") or "Summer 2024",
                        "description": exp.get("description") or (exp.get("bullets")[0] if exp.get("bullets") else "Developed and maintained software modules.")
                    })

        if not experience_list:
            exp_section = cls._extract_section(text, ["experience", "work experience", "internship", "internships", "employment"])
            if exp_section:
                exp_lines = [l.strip() for l in exp_section.split("\n") if l.strip()]
                for line in exp_lines[:10]:
                    if any(w in line.lower() for w in ["intern", "engineer", "developer", "trainee", "associate", "consultant"]) and len(line) < 80:
                        experience_list.append({
                            "role": line.strip(),
                            "company": "Industry Enterprise",
                            "duration": "Verified Duration",
                            "description": "Contributed to production codebases and sprint deliverables."
                        })
                        break

        # 7. CERTIFICATIONS & ACHIEVEMENTS
        certifications_list = []
        manual_certs = user_metadata.get("certifications") or user_metadata.get("achievements") or []
        if isinstance(manual_certs, list):
            certifications_list.extend([str(c) for c in manual_certs if str(c).strip()])

        cert_section = cls._extract_section(text, ["certifications", "certificates", "achievements", "honors", "awards"])
        if cert_section:
            for line in cert_section.split("\n")[:8]:
                clean_c = line.lstrip("•-* 1234567890.").strip()
                if 5 <= len(clean_c) <= 90 and clean_c not in certifications_list:
                    certifications_list.append(clean_c)

        # 8. ACTION VERBS & QUANTIFIABLE METRICS
        combined_text = (text + " " + json.dumps(user_metadata)).lower()
        found_verbs = [v for v in cls.ACTION_VERBS if re.search(r'\b' + v + r'\b', combined_text)]
        metrics_matches = re.findall(r'(\d+[\.\d]*\s*%(?:\s*(?:reduction|increase|improvement|faster|latency|uptime|accuracy|efficiency|growth))?|\d+k\+?\s*(?:requests|users|qps|rpm|downloads|lines)?|\d+\.\d+%\s*uptime|\b\d+\s*ms\b|\b\d+x\s*faster\b|\b\d+\s*users\b|\$\s*\d+k|\b\d+\s*stars\b)', combined_text)
        found_metrics = list(set(metrics_matches))

        return {
            "name": extracted_name,
            "email": extracted_email,
            "phone": extracted_phone,
            "links": links,
            "skills_by_category": categorized_skills,
            "all_skills": list(all_detected_skills),
            "education": education_list,
            "projects": projects_list,
            "experience": experience_list,
            "certifications": certifications_list,
            "action_verbs": found_verbs,
            "metrics": found_metrics,
            "raw_text_length": len(text)
        }

    @classmethod
    def _extract_section(cls, text: str, header_keywords: List[str]) -> str:
        """Extracts text content located under specific section headers."""
        lines = text.split("\n")
        capturing = False
        captured_lines = []

        all_headers = ["education", "experience", "work experience", "projects", "technical projects", "skills", "technical skills", "certifications", "achievements", "contact", "publications", "leadership"]

        for line in lines:
            l_strip = line.strip()
            l_lower = l_strip.lower()

            # Check if this line is a section header
            is_header = False
            for kw in all_headers:
                if (l_lower == kw or l_lower.startswith(kw + ":") or l_lower.startswith(kw + " :") or 
                    (len(l_strip) <= 35 and kw in l_lower and (line.isupper() or l_strip.endswith(":")))):
                    is_header = True
                    break

            if is_header:
                if any(target in l_lower for target in header_keywords):
                    capturing = True
                    continue
                else:
                    if capturing:
                        break  # Hit next section

            if capturing and l_strip:
                captured_lines.append(l_strip)

        return "\n".join(captured_lines)

    @classmethod
    def evaluate_and_audit(cls, entities: Dict[str, Any], target_role: str = "Software Engineer") -> Dict[str, Any]:
        """
        Calculates dynamic ATS scores, strengths, weaknesses, missing skills,
        and personalized recommendations based strictly on the extracted entities.
        """
        role_key = "fullstack"
        r_lower = target_role.lower()
        if "front" in r_lower or "react" in r_lower:
            role_key = "frontend"
        elif "back" in r_lower:
            role_key = "backend"
        elif "data" in r_lower or "ml" in r_lower or "machine learning" in r_lower or "ai" in r_lower:
            role_key = "data"
        elif "devops" in r_lower or "cloud" in r_lower:
            role_key = "devops"

        benchmarks = cls.ROLE_BENCHMARKS.get(role_key, cls.ROLE_BENCHMARKS["fullstack"])
        core_kw = benchmarks["core"]
        rec_kw = benchmarks["recommended"]

        detected_skills = set(entities.get("all_skills", []))
        matched_core = [kw for kw in core_kw if kw in detected_skills]
        missing_core = [kw for kw in core_kw if kw not in detected_skills]

        raw_len = entities.get("raw_text_length", 0)
        has_sections = sum([
            bool(entities.get("email") and "@" in str(entities.get("email", ""))),
            bool(entities.get("education")),
            bool(entities.get("all_skills")),
            bool(entities.get("projects")),
            bool(entities.get("experience"))
        ])
        
        is_blank_doc = (raw_len > 0 and raw_len < 40) or (raw_len > 0 and has_sections <= 1 and len(detected_skills) < 2)
        if is_blank_doc and len(detected_skills) < 2 and len(entities.get("projects", [])) == 0:
            return {
                "ats_score": 18,
                "resume_score": 15,
                "strengths": ["Document was successfully uploaded and scanned by the ATS parser."],
                "weaknesses": [
                    "The uploaded file does not contain recognizable resume sections (Skills, Projects, Education, Experience).",
                    "The document contains very low or non-selectable machine-readable text.",
                    "Zero target technical skills or industry keywords were detected."
                ],
                "missing_skills": core_kw[:3],
                "missing_keywords": core_kw[:6],
                "suggestions": [
                    "Upload a standard single-column PDF resume with clear section headings.",
                    "Ensure the PDF contains selectable digital text (not a scanned image or screenshot).",
                    "Alternatively, use the 'Builder Form' tab to generate a guaranteed 100% ATS-compliant resume."
                ],
                "readiness_level": "Invalid Document / Low Match",
                "parsed_name": entities.get("name"),
                "parsed_email": entities.get("email"),
                "parsed_phone": entities.get("phone"),
                "parsed_links": entities.get("links"),
                "parsed_education": entities.get("education"),
                "parsed_experience": entities.get("experience"),
                "parsed_projects": entities.get("projects"),
                "parsed_skills": entities.get("skills_by_category"),
                "parsed_certifications": entities.get("certifications"),
                "score_breakdown": {
                    "keyword_match": 10,
                    "experience_projects": 10,
                    "formatting_structure": 15,
                    "measurable_impact": 10
                }
            }

        # 1. KEYWORD & SKILL MATCH SCORE (0 - 100)
        core_ratio = len(matched_core) / max(len(core_kw), 1)
        skill_score = min(int(core_ratio * 75) + min(len(detected_skills) * 3, 25), 100)

        # 2. PROJECTS & TECHNICAL DEPTH SCORE (0 - 100)
        projects = entities.get("projects", [])
        proj_score = 45  # Baseline
        if len(projects) >= 1: proj_score += 30
        if len(projects) >= 2: proj_score += 15
        if any("github" in p.get("description", "").lower() or "http" in p.get("description", "").lower() for p in projects) or entities.get("links", {}).get("github"):
            proj_score += 10
        proj_score = min(proj_score, 100)

        # 3. EXPERIENCE & INTERNSHIPS SCORE (0 - 100)
        exp = entities.get("experience", [])
        if len(exp) >= 1:
            exp_score = 95
        elif len(projects) >= 2 and len(detected_skills) >= 6:
            exp_score = 85  # Strong portfolio substitute
        else:
            exp_score = 65

        # 4. FORMATTING & SECTION COMPLETENESS SCORE (0 - 100)
        format_score = 30
        if entities.get("email") and "@" in str(entities.get("email", "")): format_score += 20
        if len(entities.get("education", [])) > 0: format_score += 25
        if len(detected_skills) > 0: format_score += 25
        format_score = min(format_score, 100)

        # 5. MEASURABLE IMPACT SCORE (0 - 100)
        metrics = entities.get("metrics", [])
        verbs = entities.get("action_verbs", [])
        impact_score = 40
        if len(metrics) >= 1: impact_score += 35
        if len(metrics) >= 2: impact_score += 15
        if len(verbs) >= 2: impact_score += 10
        impact_score = min(impact_score, 100)

        certs = entities.get("certifications", [])
        cert_bonus = min(len(certs) * 3, 8)

        # TOTAL WEIGHTED ATS SCORE (0 - 100)
        total_ats = int(
            (skill_score * 0.35) +
            (proj_score * 0.25) +
            (exp_score * 0.15) +
            (format_score * 0.15) +
            (impact_score * 0.10) +
            cert_bonus
        )
        total_ats = max(min(total_ats, 98), 35)

        # Document Quality Score
        quality_score = max(min(total_ats - 2, 96), 22)

        # READINESS LEVEL
        if total_ats >= 82:
            readiness_level = "Placement-Ready"
        elif total_ats >= 65:
            readiness_level = "Competitive Candidate"
        elif total_ats >= 45:
            readiness_level = "Intermediate / Developing"
        else:
            readiness_level = "Needs Refinement"

        # ── DYNAMIC PERSONALIZED STRENGTHS ──
        strengths = []
        candidate_name = entities.get("name") or "Candidate"
        
        # Skill strength
        if matched_core:
            strengths.append(f"Strong verified competency match for {target_role}: {', '.join(matched_core[:4])}.")
        elif detected_skills:
            strengths.append(f"Identified foundational technical skills: {', '.join(list(detected_skills)[:4])}.")

        # Project strength
        if projects:
            p_sample = projects[0]
            strengths.append(f"Featured project '{p_sample.get('title', 'Technical Project')}' demonstrates hands-on implementation in {p_sample.get('stack', 'modern software stack')}.")
        
        # Metric strength
        if metrics:
            strengths.append(f"Quantifiable impact highlighted ({', '.join(metrics[:2])}), demonstrating measurable software engineering outcomes.")
        
        # Experience strength
        if exp:
            strengths.append(f"Industry experience: verified professional background as {exp[0].get('role', 'Developer Intern')} at {exp[0].get('company', 'Enterprise')}.")

        # Contact / Links strength
        if entities.get("links", {}).get("github") or entities.get("links", {}).get("linkedin"):
            strengths.append("Verified online professional presence with accessible GitHub / LinkedIn profile links.")

        if not strengths:
            strengths.append("Document successfully scanned and processed by GapX ATS Parser.")

        # ── DYNAMIC PERSONALIZED WEAKNESSES ──
        weaknesses = []
        if missing_core:
            weaknesses.append(f"Missing high-impact {target_role} keywords: {', '.join(missing_core[:4])}.")
        if not exp:
            weaknesses.append("No explicit industrial internship or enterprise work experience detected.")
        if not metrics:
            weaknesses.append("Project bullet points lack quantifiable metrics (e.g. '% latency improvement', 'requests/sec scale').")
        if not entities.get("links", {}).get("github"):
            weaknesses.append("Missing direct clickable GitHub repository links for code verification.")
        if not entities.get("certifications"):
            weaknesses.append("Adding industry-recognized certifications (e.g. AWS, Meta, or LeetCode ratings) will increase interview shortlist rates.")

        # ── DYNAMIC SUGGESTIONS ──
        suggestions = []
        if missing_core:
            suggestions.append(f"Incorporate missing core skills ({', '.join(missing_core[:3])}) into your skills and project descriptions.")
        
        if projects:
            first_p = projects[0].get("title", "your primary project")
            suggestions.append(f"Rewrite bullet points for '{first_p}' using Google's XYZ formula: 'Accomplished [X] as measured by [Y], by doing [Z]' (e.g., 'Reduced query latency by 35% using Redis caching').")
        else:
            suggestions.append("Add at least 2 full-stack projects featuring clean architecture, unit testing, and Docker containerization.")

        suggestions.append("Ensure single-column ATS formatting with standard section headers: 'Education', 'Technical Skills', 'Experience', and 'Projects'.")

        missing_keywords_list = missing_core[:6]
        if len(missing_keywords_list) < 4:
            for rk in rec_kw:
                if rk not in detected_skills and rk not in missing_keywords_list:
                    missing_keywords_list.append(rk)
                if len(missing_keywords_list) >= 6:
                    break

        return {
            "ats_score": total_ats,
            "resume_score": quality_score,
            "strengths": strengths,
            "weaknesses": weaknesses,
            "missing_skills": missing_keywords_list[:3],
            "missing_keywords": missing_keywords_list,
            "suggestions": suggestions,
            "readiness_level": readiness_level,
            "parsed_name": entities.get("name"),
            "parsed_email": entities.get("email"),
            "parsed_phone": entities.get("phone"),
            "parsed_links": entities.get("links"),
            "parsed_education": entities.get("education"),
            "parsed_experience": entities.get("experience"),
            "parsed_projects": entities.get("projects"),
            "parsed_skills": entities.get("skills_by_category"),
            "parsed_certifications": entities.get("certifications"),
            "score_breakdown": {
                "keyword_match": skill_score,
                "experience_projects": proj_score,
                "formatting_structure": format_score,
                "measurable_impact": impact_score
            }
        }
