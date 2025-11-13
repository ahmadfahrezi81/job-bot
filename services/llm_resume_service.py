# services/llm_resume_service.py
from openai import AsyncOpenAI
import logging
import os
import json

logger = logging.getLogger(__name__)
client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def load_master_resume() -> str:
    """Load the master resume content from file"""
    try:
        with open("data/resume-content.tex", "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        raise Exception("Master resume not found at data/resume-content.tex")


def fix_latex_escaping(latex_content: str) -> str:
    """
    Convert LLM placeholders to proper LaTeX escapes.

    Placeholders avoid JSON escaping issues:
    - __AMP__ → \& (for text ampersands, NOT tabular separators)
    - __PCT__ → \%
    - __HASH__ → \#
    - __DOLLAR__ → \$

    This approach prevents double-escaping problems where the LLM
    generates \\& instead of \& when trying to be JSON-safe.
    """

    # First, clean up any backslashes the LLM mistakenly added before placeholders
    latex_content = latex_content.replace(r"\__PCT__", "__PCT__")
    latex_content = latex_content.replace(r"\__AMP__", "__AMP__")
    latex_content = latex_content.replace(r"\__HASH__", "__HASH__")
    latex_content = latex_content.replace(r"\__DOLLAR__", "__DOLLAR__")

    # Now convert placeholders to LaTeX escapes
    replacements = {
        "__AMP__": r" \& ",
        "__PCT__": r"\% ",
        "__HASH__": r" \#",
        "__DOLLAR__": r" \$",
    }

    total_fixes = 0
    for placeholder, latex_escape in replacements.items():
        count = latex_content.count(placeholder)
        if count > 0:
            latex_content = latex_content.replace(placeholder, latex_escape)
            logger.info(f"🔧 Converted {count} × '{placeholder}' → '{latex_escape}'")
            total_fixes += count

    if total_fixes > 0:
        logger.info(f"✅ Total placeholder conversions: {total_fixes}")

    return latex_content


async def tailor_resume(
    job_description: str,
    evaluation: dict,
    job_title: str = None,
    company_name: str = None,
) -> dict:
    """
    Tailors resume content for a specific job posting.
    Optimized for o4-mini: minimal, clear instructions; no excessive guidance.

    Args:
        job_description: Full text of the job posting
        evaluation: Dict containing match_score, strengths, gaps, etc.
        job_title: Title of the position (e.g., "Software Engineer - QA Automation")
        company_name: Name of the company (e.g., "GoTo Financial")

    Returns:
        {
            "tailored_content": "... LaTeX content ...",
            "pruning_strategy": {...},
            "tech_stack_analysis": {...},
            "change_summary": {...}
        }
    """
    logger.info("🎯 Starting resume tailoring...")
    logger.info(f"   • Job Title: {job_title or 'Not specified'}")
    logger.info(f"   • Company: {company_name or 'Not specified'}")

    # Load master resume
    try:
        master_resume = load_master_resume()
        logger.info(f"✅ Loaded master resume ({len(master_resume)} chars)")
    except Exception:
        logger.exception("❌ Failed to load master resume")
        raise

    # Extract key info from evaluation
    match_score = evaluation.get("match_score", 0)
    strengths = evaluation.get("strengths", [])
    gaps = evaluation.get("gaps", [])

    logger.info(f"📊 Tailoring for match score: {match_score}%")
    logger.info(f"   • {len(strengths)} strengths identified")
    logger.info(f"   • {len(gaps)} gaps identified")

    # Build role context string
    role_context = ""
    if job_title and company_name:
        role_context = f"Target Role: {job_title} at {company_name}"
    elif job_title:
        role_context = f"Target Role: {job_title}"
    elif company_name:
        role_context = f"Target Company: {company_name}"
    else:
        role_context = "Target Role: Not specified (infer from job description)"

    # Streamlined prompt for o4-mini reasoning
    prompt = f"""Tailor a LaTeX resume for this job, fitting on ONE PAGE. The resume uses a two-file system: main.tex (formatting—never modify) and resume-content.tex (content only—you update this).

**CONTEXT**
{role_context}
Match Score: {match_score}%
Strengths: {', '.join(strengths)}
Gaps: {', '.join(gaps)}

**ONE-PAGE CONSTRAINTS**
• Experience: Max 4 bullets/role (5-6 for most relevant role)
• Projects: 2 projects max, 4 bullets each
• Total bullets: 20-24 maximum
• Remove nested sub-bullets unless critical with metrics
• Prioritize bullets with metrics + job keyword matches

**CONTENT SCORING & PRUNING**
Score each bullet 0-10 for job relevance:
• Cut bullets <5 if they add no unique value
• Keep bullets ≥7 even if longer—quality over brevity
• Consolidate only truly redundant achievements
• Reduce less-relevant roles to 3-4 bullets
• Cut projects only if consistently <6 relevance

**OPTIMIZATION RULES**
• Aim for one line/bullet (12-18 words ideal, 20-25 OK if preserves impact)
• Front-load impact: result first, then method
• Remove filler: "responsible for", "worked on", "helped to"
• Keep ALL quantified metrics (numbers, %, time savings, user counts)
• Keep specific tools showing technical depth (Postman, RBAC, Appium)
• Keep architectural terms (SSR, serverless, multi-tenant, row-level security)
• Keep before/after impact data (32% increase, 40% faster, 95%+ coverage)

**MANDATORY SECTIONS (ALL MUST BE PRESENT IN THIS ORDER)**
1. HEADER SECTION
   • Copy exactly as-is from master resume
   • Plain & for tabular column separators (e.g., Name & Email)
   • DO NOT modify name, email, website, LinkedIn

2. TECHNICAL SKILLS SECTION
   • MAY reorder categories to emphasize relevant skills
   • MAY add technologies from job description if candidate has them
   • MAY remove rarely-used tech if space is critical
   • For ampersands in text: use __AMP__ placeholder (e.g., "Cloud __AMP__ Infrastructure")
   • For other special chars: __PCT__ __HASH__ __DOLLAR__

3. EXPERIENCE SECTION
   • MAY optimize bullets, reorder roles, reduce bullets for less-relevant roles
   • NEVER remove roles entirely—keep ≥2-3 bullets/role
   • Maintain \\resumeSubheading{{Title}}{{Date}}{{Company}}{{Location}}

4. PROJECTS SECTION
   • MAY select 2 most relevant projects
   • MAY optimize bullets, update tech stacks if defensible
   • Maintain \\resumeProjectHeading{{Name}}{{URL}}{{Tech Stack}}

5. EDUCATION SECTION
   • Copy exactly as-is including relevant coursework
   • DO NOT modify degree, university, dates, location

**SPECIAL CHARACTER HANDLING**
• In header tabular: Use plain & for columns
• In all other text: Use placeholders
  - __AMP__ for ampersands → converts to \\&
  - __PCT__ for percents → converts to \\%
  - __HASH__ for hashes → converts to \\#
  - __DOLLAR__ for dollars → converts to \\$
• Plus signs (+) work as-is: "200+" and "95%+" are fine

**LATEX STRUCTURE (DO NOT MODIFY THESE)**
• Keep all \\resumeSubHeadingListStart / \\resumeSubHeadingListEnd
• Keep all \\resumeItemListStart / \\resumeItemListEnd
• Balance all braces {{}}
• Use date format: MMM. YYYY
• Do NOT add \\documentclass or \\begin{{document}}

**MASTER RESUME**
{master_resume}

**JOB DESCRIPTION**
{job_description}

**OUTPUT FORMAT (JSON)**
{{
    "tailored_content": "complete LaTeX for resume-content.tex",
    "pruning_strategy": {{
        "summary": "pruning approach for {job_title or 'this role'} at {company_name or 'this company'}",
        "scoring_logic": "how bullets were scored 0-10 for relevance",
        "role_breakdown": "which roles/projects kept, relevance scores, bullet counts"
    }},
    "tech_stack_analysis": {{
        "table": [
            {{"tech": "name", "assessment": "relevance to {job_title or 'role'} and how to add", "risk": "Low/Medium/High"}}
        ],
        "suggested_additions": "where to add tech for {company_name or 'company'}"
    }},
    "change_summary": {{
        "what_made_cut": "experiences/projects kept (with scores), key bullets, total count",
        "what_removed": "bullets cut, projects removed, consolidations, justifications",
        "interview_prep": [
            "5 talking points about fit for {job_title or 'role'} at {company_name or 'company'}"
        ]
    }}
}}

**RULES**
• Be honest but strategic
• ONE PAGE is non-negotiable
• 20-24 bullets maximum
• Only add tech with genuine transferability
• Never invent experiences, dates, companies
• Maximize impact—conciseness is secondary
• Reference role/company throughout analysis"""

    try:
        logger.info("🚀 Sending tailoring request to OpenAI (o4-mini)...")

        response = await client.chat.completions.create(
            model="o4-mini",
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert resume optimizer. Return valid JSON with complete LaTeX content. Use __AMP__ __PCT__ __HASH__ __DOLLAR__ placeholders for special characters in text (NOT in header tabular). Plain & only for tabular column separators. Prioritize impact over brevity.",
                },
                {"role": "user", "content": prompt},
            ],
            reasoning_effort="low",
            max_completion_tokens=5000,
            response_format={"type": "json_object"},
        )

        raw_content = response.choices[0].message.content
        logger.debug("----- RAW RESUME TAILORING RESPONSE -----")
        logger.debug(raw_content[:2000])
        logger.debug("-----------------------------------------")

        parsed = json.loads(raw_content)

        # Validate required fields
        required_fields = [
            "tailored_content",
            "pruning_strategy",
            "tech_stack_analysis",
            "change_summary",
        ]
        for field in required_fields:
            if field not in parsed:
                raise ValueError(f"Missing required field: {field}")

        # Validate nested structures
        if not isinstance(parsed["pruning_strategy"], dict):
            raise ValueError("pruning_strategy must be a dict")
        if not isinstance(parsed["tech_stack_analysis"], dict):
            raise ValueError("tech_stack_analysis must be a dict")
        if not isinstance(parsed["change_summary"], dict):
            raise ValueError("change_summary must be a dict")
        if not isinstance(parsed["change_summary"].get("interview_prep", []), list):
            raise ValueError("interview_prep must be a list")

        # Convert placeholders to LaTeX escapes
        parsed["tailored_content"] = fix_latex_escaping(parsed["tailored_content"])

        # Recursively clean placeholders for user-display fields
        def clean_placeholders_for_display(obj):
            """Recursively replace placeholders with readable text in all strings"""
            if isinstance(obj, str):
                return (
                    obj.replace("__AMP__", " & ")
                    .replace("__PCT__", "% ")
                    .replace("__HASH__", " #")
                    .replace("__DOLLAR__", " $")
                )
            elif isinstance(obj, dict):
                return {k: clean_placeholders_for_display(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [clean_placeholders_for_display(item) for item in obj]
            return obj

        # Clean all analysis fields (tailored_content already done)
        parsed["pruning_strategy"] = clean_placeholders_for_display(
            parsed["pruning_strategy"]
        )
        parsed["tech_stack_analysis"] = clean_placeholders_for_display(
            parsed["tech_stack_analysis"]
        )
        parsed["change_summary"] = clean_placeholders_for_display(
            parsed["change_summary"]
        )

        logger.info("✅ Resume tailoring completed successfully")
        logger.info(
            f"   • Tailored content length: {len(parsed['tailored_content'])} chars"
        )
        logger.info(
            f"   • Interview prep points: {len(parsed['change_summary'].get('interview_prep', []))}"
        )
        logger.info(
            f"   • Optimized for: {job_title or 'role'} at {company_name or 'company'}"
        )

        return parsed

    except json.JSONDecodeError as e:
        logger.exception("❌ Failed to parse JSON response from OpenAI")
        logger.error(f"Raw response preview: {raw_content[:500]}")
        raise Exception(f"Resume tailoring failed - invalid JSON: {str(e)}")
    except Exception as e:
        logger.exception("❌ Resume tailoring failed")
        raise Exception(f"Resume tailoring failed: {str(e)}")
