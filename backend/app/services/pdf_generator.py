import io
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, KeepTogether, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from typing import Dict, Any

class PDFNotesGenerator:
    
    @staticmethod
    def generate_notes_pdf(notes_data: Dict[str, Any]) -> io.BytesIO:
        """Generates an exhaustive, beautifully styled academic PDF study sheet."""
        buffer = io.BytesIO()
        
        # Setup document margins
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            rightMargin=40,
            leftMargin=40,
            topMargin=40,
            bottomMargin=40
        )
        
        styles = getSampleStyleSheet()
        
        # Define premium color palette
        primary_color = colors.HexColor("#312e81")    # Deep Indigo
        accent_color = colors.HexColor("#4f46e5")     # Vibrant Indigo
        emerald_color = colors.HexColor("#065f46")    # Emerald Green
        dark_slate = colors.HexColor("#0f172a")       # Slate 900
        muted_slate = colors.HexColor("#334155")      # Slate 700
        light_bg = colors.HexColor("#f8fafc")         # Slate 50
        border_color = colors.HexColor("#e2e8f0")     # Slate 200
        card_bg = colors.HexColor("#f1f5f9")          # Slate 100
        amber_color = colors.HexColor("#92400e")      # Amber 800
        
        # Custom typography styles
        title_style = ParagraphStyle(
            name="PDFTitle",
            parent=styles["Title"],
            fontName="Helvetica-Bold",
            fontSize=20,
            leading=24,
            textColor=primary_color,
            spaceAfter=4,
            alignment=0
        )
        
        meta_style = ParagraphStyle(
            name="PDFMeta",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=9.5,
            leading=13,
            textColor=accent_color,
            spaceAfter=10
        )
        
        h1_style = ParagraphStyle(
            name="PDFH1",
            parent=styles["Heading1"],
            fontName="Helvetica-Bold",
            fontSize=13,
            leading=17,
            textColor=primary_color,
            spaceBefore=12,
            spaceAfter=6,
            keepWithNext=True
        )
        
        h2_style = ParagraphStyle(
            name="PDFH2",
            parent=styles["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=11,
            leading=15,
            textColor=accent_color,
            spaceBefore=8,
            spaceAfter=4,
            keepWithNext=True
        )
        
        body_style = ParagraphStyle(
            name="PDFBody",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=9.5,
            leading=14,
            textColor=muted_slate,
            spaceAfter=6
        )
        
        code_style = ParagraphStyle(
            name="PDFCode",
            parent=styles["Normal"],
            fontName="Courier",
            fontSize=8.5,
            leading=11.5,
            textColor=dark_slate
        )
        
        qa_q_style = ParagraphStyle(
            name="PDFQAQ",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=10,
            leading=13,
            textColor=emerald_color,
            spaceAfter=3,
            keepWithNext=True
        )
        
        qa_a_style = ParagraphStyle(
            name="PDFQAA",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=9,
            leading=13,
            textColor=muted_slate,
            spaceAfter=8
        )
        
        table_header_style = ParagraphStyle(
            name="PDFTH",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=9,
            leading=12,
            textColor=colors.white
        )
        
        table_cell_style = ParagraphStyle(
            name="PDFTD",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=8.5,
            leading=11.5,
            textColor=muted_slate
        )
        
        story = []
        
        def safe_xml(s: Any) -> str:
            if not isinstance(s, str):
                s = str(s)
            return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

        # 1. Main Header Title & Metadata
        title_val = safe_xml(notes_data.get("title", "Comprehensive Study Notes"))
        stage_val = safe_xml(notes_data.get("stage", "Placement Preparation Track"))
        role_val = safe_xml(notes_data.get("role", "Software Engineer"))
        
        story.append(Paragraph(f"{title_val}", title_style))
        story.append(Paragraph(f"<b>Track:</b> {stage_val} &nbsp;|&nbsp; <b>Target Role:</b> {role_val} &nbsp;|&nbsp; <b>Platform:</b> GapX AI Skill Intelligence", meta_style))
        story.append(HRFlowable(width="100%", thickness=1.5, color=accent_color, spaceAfter=10))
        
        # 2. Executive Definition & Academic Overview
        story.append(Paragraph("1. Executive Definition & Conceptual Overview", h1_style))
        summary_val = notes_data.get("executive_summary") or notes_data.get("introduction") or "Foundational study material."
        story.append(Paragraph(safe_xml(summary_val), body_style))
        story.append(Spacer(1, 4))
        
        # 3. Deep Internals & Low-Level Architecture (if available)
        internals_val = notes_data.get("internals_and_architecture")
        if internals_val:
            story.append(Paragraph("2. Deep Internals, Memory Layout & Runtime Execution", h1_style))
            story.append(Paragraph(safe_xml(internals_val), body_style))
            story.append(Spacer(1, 4))
        
        # 4. Key Concepts Section
        concepts = notes_data.get("key_concepts", [])
        if concepts:
            story.append(Paragraph("3. Core Theoretical Principles & Mechanisms", h1_style))
            for concept in concepts:
                name = safe_xml(concept.get("name", "Concept"))
                explanation = safe_xml(concept.get("explanation", ""))
                story.append(Paragraph(f"<b>• {name}:</b> {explanation}", body_style))
            story.append(Spacer(1, 4))
            
        # 5. Complexity Analysis Table (if available)
        complexities = notes_data.get("complexity_analysis", [])
        if complexities:
            story.append(Paragraph("4. Formal Complexity Analysis", h1_style))
            table_data = [[
                Paragraph("<b>Operation / Phase</b>", table_header_style),
                Paragraph("<b>Time Complexity</b>", table_header_style),
                Paragraph("<b>Space Complexity</b>", table_header_style),
                Paragraph("<b>Trade-offs & Explanation</b>", table_header_style)
            ]]
            for c in complexities:
                table_data.append([
                    Paragraph(safe_xml(c.get("operation", "")), table_cell_style),
                    Paragraph(f"<b>{safe_xml(c.get('time_complexity', 'O(1)'))}</b>", table_cell_style),
                    Paragraph(f"<b>{safe_xml(c.get('space_complexity', 'O(1)'))}</b>", table_cell_style),
                    Paragraph(safe_xml(c.get("explanation", "")), table_cell_style)
                ])
                
            c_table = Table(table_data, colWidths=[130, 95, 95, 210])
            c_table.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,0), primary_color),
                ('TOPPADDING', (0,0), (-1,-1), 5),
                ('BOTTOMPADDING', (0,0), (-1,-1), 5),
                ('LEFTPADDING', (0,0), (-1,-1), 6),
                ('RIGHTPADDING', (0,0), (-1,-1), 6),
                ('GRID', (0,0), (-1,-1), 0.5, border_color),
                ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, light_bg]),
                ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ]))
            story.append(c_table)
            story.append(Spacer(1, 8))
        
        # 6. Production Code Implementation Block
        code_text = notes_data.get("code_example", "")
        if code_text:
            story.append(Paragraph("5. Placement-Ready Production Code Implementation", h1_style))
            
            # Format lines cleanly without overflow
            formatted_lines = []
            for line in code_text.split("\n"):
                if len(line) > 85:
                    line = line[:85] + "..."
                formatted_lines.append(safe_xml(line).replace(" ", "&nbsp;"))
            escaped_code = "<br/>".join(formatted_lines)
            code_p = Paragraph(escaped_code, code_style)
            
            code_table = Table([[code_p]], colWidths=[530])
            code_table.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,-1), card_bg),
                ('TOPPADDING', (0,0), (-1,-1), 8),
                ('BOTTOMPADDING', (0,0), (-1,-1), 8),
                ('LEFTPADDING', (0,0), (-1,-1), 10),
                ('RIGHTPADDING', (0,0), (-1,-1), 10),
                ('BOX', (0,0), (-1,-1), 1, border_color),
            ]))
            story.append(code_table)
            story.append(Spacer(1, 8))

        # 7. Real-World Industry Use Cases
        use_cases = notes_data.get("industry_use_cases", [])
        if use_cases:
            story.append(Paragraph("6. High-Scale Production & FAANG Industry Applications", h1_style))
            for uc in use_cases:
                comp = safe_xml(uc.get("company", "Tech Enterprise"))
                desc = safe_xml(uc.get("use_case", ""))
                impact = safe_xml(uc.get("architecture_impact", ""))
                story.append(Paragraph(f"<b>🏢 {comp}:</b> {desc} <i>(Impact: {impact})</i>", body_style))
            story.append(Spacer(1, 4))
            
        # 8. Placement Interview Questions & Answers
        questions = notes_data.get("interview_questions", [])
        if questions:
            story.append(Paragraph("7. Top Technical Screening & FAANG Placement Questions", h1_style))
            for idx, qa in enumerate(questions, 1):
                q = safe_xml(qa.get("question", ""))
                ans = safe_xml(qa.get("ideal_answer", ""))
                diff = safe_xml(qa.get("difficulty", "Medium"))
                
                story.append(Paragraph(f"<b>Q{idx} ({diff}):</b> {q}", qa_q_style))
                story.append(Paragraph(f"<b>Ideal Model Answer:</b> {ans}", qa_a_style))
            story.append(Spacer(1, 4))
            
        # 9. Traps, Pitfalls & Best Practices
        pitfalls = notes_data.get("common_pitfalls", [])
        practices = notes_data.get("best_practices", [])
        if pitfalls or practices:
            story.append(Paragraph("8. Common Traps, Antipatterns & Production Best Practices", h1_style))
            for p in pitfalls:
                story.append(Paragraph(f"<b>⚠️ Trap:</b> {safe_xml(p)}", body_style))
            for pr in practices:
                story.append(Paragraph(f"<b>✓ Best Practice:</b> {safe_xml(pr)}", body_style))
            story.append(Spacer(1, 4))
            
        # 10. Executive Summary & Revision Box
        final_summary = notes_data.get("summary", "Master fundamental definitions, space/time complexities, and production code before interviews.")
        story.append(Paragraph("9. Key Takeaways & Fast Revision Summary", h1_style))
        summary_p = Paragraph(safe_xml(final_summary), body_style)
        
        sum_table = Table([[summary_p]], colWidths=[530])
        sum_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#e0e7ff")), # Soft Indigo
            ('TOPPADDING', (0,0), (-1,-1), 8),
            ('BOTTOMPADDING', (0,0), (-1,-1), 8),
            ('LEFTPADDING', (0,0), (-1,-1), 10),
            ('RIGHTPADDING', (0,0), (-1,-1), 10),
            ('BOX', (0,0), (-1,-1), 1, colors.HexColor("#c7d2fe")),
        ]))
        story.append(sum_table)
        
        # Build document
        doc.build(story)
        buffer.seek(0)
        return buffer


class PDFResumeGenerator:
    """Generates an industry-standard, ATS-optimized single/two-page PDF resume."""

    @staticmethod
    def generate_resume_pdf(data: Dict[str, Any]) -> io.BytesIO:
        buffer = io.BytesIO()

        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            rightMargin=36,
            leftMargin=36,
            topMargin=36,
            bottomMargin=36
        )

        styles = getSampleStyleSheet()

        def safe_text(val: Any) -> str:
            if val is None:
                return ""
            return str(val).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')

        # Standard ATS Typography & Colors
        name_style = ParagraphStyle(
            name="ResumeName",
            parent=styles["Title"],
            fontName="Helvetica-Bold",
            fontSize=18,
            leading=22,
            textColor=colors.HexColor("#0f172a"),
            alignment=1, # Centered
            spaceAfter=3
        )

        headline_style = ParagraphStyle(
            name="ResumeHeadline",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=10,
            leading=13,
            textColor=colors.HexColor("#4338ca"),
            alignment=1,
            spaceAfter=4
        )

        contact_style = ParagraphStyle(
            name="ResumeContact",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=8.5,
            leading=11,
            textColor=colors.HexColor("#334155"),
            alignment=1,
            spaceAfter=8
        )

        section_heading_style = ParagraphStyle(
            name="ResumeSectionHeading",
            parent=styles["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=11,
            leading=14,
            textColor=colors.HexColor("#1e1b4b"),
            spaceBefore=8,
            spaceAfter=2,
            keepWithNext=True
        )

        item_title_style = ParagraphStyle(
            name="ResumeItemTitle",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=9.5,
            leading=12,
            textColor=colors.HexColor("#0f172a")
        )

        item_sub_style = ParagraphStyle(
            name="ResumeItemSub",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=8.5,
            leading=11,
            textColor=colors.HexColor("#475569")
        )

        date_style = ParagraphStyle(
            name="ResumeDate",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=8.5,
            leading=11,
            textColor=colors.HexColor("#334155"),
            alignment=2 # Right
        )

        bullet_style = ParagraphStyle(
            name="ResumeBullet",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=8.5,
            leading=11.5,
            textColor=colors.HexColor("#1e293b"),
            leftIndent=12,
            firstLineIndent=-8,
            spaceAfter=1.5
        )

        body_style = ParagraphStyle(
            name="ResumeBody",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=8.5,
            leading=12,
            textColor=colors.HexColor("#1e293b"),
            spaceAfter=4
        )

        story = []

        # 1. Header (Name, Headline, Contact details)
        name = data.get("name") or data.get("full_name") or "Candidate Name"
        story.append(Paragraph(safe_text(name), name_style))

        headline = data.get("headline") or data.get("target_role") or "Software Engineer"
        story.append(Paragraph(safe_text(headline), headline_style))

        contact_parts = []
        if data.get("email"):
            contact_parts.append(safe_text(data["email"]))
        if data.get("phone"):
            contact_parts.append(safe_text(data["phone"]))
        if data.get("location"):
            contact_parts.append(safe_text(data["location"]))
        if data.get("linkedin"):
            contact_parts.append(f"<b>LinkedIn:</b> {safe_text(data['linkedin'])}")
        if data.get("github"):
            contact_parts.append(f"<b>GitHub:</b> {safe_text(data['github'])}")
        if data.get("portfolio"):
            contact_parts.append(f"<b>Portfolio:</b> {safe_text(data['portfolio'])}")

        if contact_parts:
            story.append(Paragraph(" • ".join(contact_parts), contact_style))

        def add_section_header(title: str):
            story.append(Spacer(1, 4))
            story.append(Paragraph(title.upper(), section_heading_style))
            story.append(HRFlowable(width="100%", thickness=0.75, color=colors.HexColor("#cbd5e1"), spaceBefore=1, spaceAfter=4))

        # 2. Professional Summary
        summary = data.get("summary") or data.get("objective")
        if summary:
            add_section_header("Professional Summary")
            story.append(Paragraph(safe_text(summary), body_style))

        # 3. Education
        add_section_header("Education")
        education_list = data.get("education_items")
        if education_list and isinstance(education_list, list):
            for edu in education_list:
                deg = safe_text(edu.get("degree", "Bachelor of Technology in Computer Science"))
                inst = safe_text(edu.get("institution", "University"))
                dates = safe_text(edu.get("dates", "2022 - 2026"))
                cgpa = edu.get("cgpa")

                edu_row = [[Paragraph(f"<b>{deg}</b> - {inst}", item_title_style), Paragraph(dates, date_style)]]
                t = Table(edu_row, colWidths=[400, 140])
                t.setStyle(TableStyle([('VALIGN', (0,0), (-1,-1), 'TOP'), ('BOTTOMPADDING', (0,0), (-1,-1), 1), ('TOPPADDING', (0,0), (-1,-1), 1)]))
                story.append(t)
                if cgpa:
                    story.append(Paragraph(f"CGPA / Percentage: <b>{safe_text(cgpa)}</b>", item_sub_style))
                story.append(Spacer(1, 2))
        else:
            edu_str = data.get("education") or "Bachelor of Technology in Computer Science"
            sem_str = data.get("semester") or ""
            cgpa_val = data.get("cgpa")
            row = [[Paragraph(f"<b>{safe_text(edu_str)}</b>", item_title_style), Paragraph(safe_text(sem_str or "2022 - 2026"), date_style)]]
            t = Table(row, colWidths=[400, 140])
            t.setStyle(TableStyle([('VALIGN', (0,0), (-1,-1), 'TOP'), ('BOTTOMPADDING', (0,0), (-1,-1), 1), ('TOPPADDING', (0,0), (-1,-1), 1)]))
            story.append(t)
            if cgpa_val:
                story.append(Paragraph(f"Cumulative GPA: <b>{safe_text(cgpa_val)}</b>", item_sub_style))

        # 4. Technical Skills
        add_section_header("Technical Skills")
        skills = data.get("skills") or []
        languages = data.get("languages") or data.get("languages_known") or []
        tools = data.get("tools") or data.get("frameworks") or []

        if isinstance(skills, str):
            skills = [s.strip() for s in skills.split(",") if s.strip()]
        if isinstance(languages, str):
            languages = [l.strip() for l in languages.split(",") if l.strip()]
        if isinstance(tools, str):
            tools = [t.strip() for t in tools.split(",") if t.strip()]

        if languages:
            story.append(Paragraph(f"<b>Languages:</b> {safe_text(', '.join(languages))}", bullet_style))
        if skills:
            story.append(Paragraph(f"<b>Core Technologies &amp; Frameworks:</b> {safe_text(', '.join(skills))}", bullet_style))
        if tools:
            story.append(Paragraph(f"<b>Developer Tools &amp; Cloud:</b> {safe_text(', '.join(tools))}", bullet_style))
        if not (languages or skills or tools):
            story.append(Paragraph("<b>Technologies:</b> Python, JavaScript, TypeScript, React, Next.js, Node.js, PostgreSQL, Docker, Git, DSA, System Design", bullet_style))

        # 5. Experience / Internships
        exp_list = data.get("experience") or data.get("internships")
        if exp_list and isinstance(exp_list, list) and len(exp_list) > 0:
            add_section_header("Work Experience & Internships")
            for exp in exp_list:
                title = safe_text(exp.get("title") or exp.get("role") or "Software Engineering Intern")
                company = safe_text(exp.get("company") or "Tech Enterprise")
                dates = safe_text(exp.get("dates") or exp.get("duration") or "May 2024 - July 2024")
                loc = safe_text(exp.get("location") or "")

                comp_loc = f"{company}" + (f" | {loc}" if loc else "")
                row = [[Paragraph(f"<b>{title}</b> — {comp_loc}", item_title_style), Paragraph(dates, date_style)]]
                t = Table(row, colWidths=[400, 140])
                t.setStyle(TableStyle([('VALIGN', (0,0), (-1,-1), 'TOP'), ('BOTTOMPADDING', (0,0), (-1,-1), 1), ('TOPPADDING', (0,0), (-1,-1), 1)]))
                story.append(t)

                bullets = exp.get("bullets") or exp.get("description")
                if isinstance(bullets, list):
                    for b in bullets:
                        story.append(Paragraph(f"• {safe_text(b)}", bullet_style))
                elif isinstance(bullets, str) and bullets.strip():
                    story.append(Paragraph(f"• {safe_text(bullets)}", bullet_style))
                story.append(Spacer(1, 3))

        # 6. Key Projects
        projects_list = data.get("projects")
        if projects_list and isinstance(projects_list, list) and len(projects_list) > 0:
            add_section_header("Key Technical Projects")
            for proj in projects_list:
                pname = safe_text(proj.get("title") or proj.get("name") or "Project Name")
                pstack = safe_text(proj.get("stack") or proj.get("technologies") or "")
                plink = safe_text(proj.get("link") or proj.get("github") or "")

                title_part = f"<b>{pname}</b>" + (f" | <i>{pstack}</i>" if pstack else "")
                row = [[Paragraph(title_part, item_title_style), Paragraph(plink, date_style)]]
                t = Table(row, colWidths=[380, 160])
                t.setStyle(TableStyle([('VALIGN', (0,0), (-1,-1), 'TOP'), ('BOTTOMPADDING', (0,0), (-1,-1), 1), ('TOPPADDING', (0,0), (-1,-1), 1)]))
                story.append(t)

                bullets = proj.get("bullets") or proj.get("description")
                if isinstance(bullets, list):
                    for b in bullets:
                        story.append(Paragraph(f"• {safe_text(b)}", bullet_style))
                elif isinstance(bullets, str) and bullets.strip():
                    story.append(Paragraph(f"• {safe_text(bullets)}", bullet_style))
                story.append(Spacer(1, 3))

        # 7. Certifications & Achievements
        certs = data.get("certifications") or []
        achievements = data.get("achievements") or data.get("hackathons") or []
        if isinstance(certs, str):
            certs = [c.strip() for c in certs.split(",") if c.strip()]
        if isinstance(achievements, str):
            achievements = [a.strip() for a in achievements.split(",") if a.strip()]

        if certs or achievements:
            add_section_header("Certifications & Honors")
            if certs:
                for c in certs:
                    story.append(Paragraph(f"• <b>Certification:</b> {safe_text(c)}", bullet_style))
            if achievements:
                for a in achievements:
                    story.append(Paragraph(f"• <b>Honor / Award:</b> {safe_text(a)}", bullet_style))

        # Build document
        doc.build(story)
        buffer.seek(0)
        return buffer


class PDFExtractor:
    """Robust multi-engine PDF text extractor with normalization and fallback decoders."""

    @staticmethod
    def normalize_text(text: str) -> str:
        if not text:
            return ""
        import unicodedata
        import re
        # Unicode normalization (NFKC fixes combined accents and special characters)
        text = unicodedata.normalize("NFKC", text)
        # Replace common ligatures and special bullet characters
        ligatures = {
            "ﬁ": "fi", "ﬂ": "fl", "ﬀ": "ff", "ﬃ": "ffi", "ﬄ": "ffl",
            "–": "-", "—": "-", "\u2013": "-", "\u2014": "-",
            "\u2018": "'", "\u2019": "'", "\u201c": '"', "\u201d": '"',
            "\u2022": "•", "\u25cf": "•", "\u00a0": " ", "\ufeff": ""
        }
        for k, v in ligatures.items():
            text = text.replace(k, v)
        # Strip non-printable / control characters except \n, \r, \t
        text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]", "", text)
        # Replace 3+ consecutive newlines with 2
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()

    @classmethod
    def extract_text(cls, pdf_bytes: bytes) -> str:
        if not pdf_bytes or len(pdf_bytes) < 10:
            return ""

        extracted = ""
        import logging
        log = logging.getLogger(__name__)

        # Engine 1: pypdf (PdfReader)
        try:
            import pypdf
            reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
            pages_text = []
            for i, page in enumerate(reader.pages):
                try:
                    t = page.extract_text()
                    if t and t.strip():
                        pages_text.append(t.strip())
                except Exception as pe:
                    log.debug(f"pypdf page {i} warning: {pe}")
            if pages_text:
                extracted = "\n\n".join(pages_text)
        except Exception as e:
            log.debug(f"pypdf extraction failed: {e}")

        # Engine 2: pdfminer.six (if pypdf returned empty or very short text)
        if len(extracted.strip()) < 40:
            try:
                from pdfminer.high_level import extract_text as pdfminer_extract_text
                miner_text = pdfminer_extract_text(io.BytesIO(pdf_bytes))
                if miner_text and len(miner_text.strip()) > len(extracted.strip()):
                    extracted = miner_text
            except Exception as e:
                log.debug(f"pdfminer extraction failed: {e}")

        # Engine 3: Fallback regex uncompressed stream parser for raw text objects
        if len(extracted.strip()) < 40:
            try:
                import re
                text_chunks = re.findall(rb"\(([\w\s\.\,\:\;\-\_\@\/\(\)]+)\)\s*(?:Tj|\'|\")", pdf_bytes)
                if text_chunks:
                    extracted = "\n".join([chunk.decode("latin1", errors="ignore") for chunk in text_chunks if chunk])
            except Exception as e:
                log.debug(f"Stream regex extraction failed: {e}")

        return cls.normalize_text(extracted)

