# services/llm_evaluation_service.py
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


async def evaluate_job_match(job_text: str, visa_warning: str = None) -> dict:
    """
    Performs an honest evaluation of how well the master resume fits the job description.

    Args:
        job_text: Full job description text
        visa_warning: Pre-determined visa warning from crawl4ai_service (if any)

    Returns:
        {
            "match_score": int,
            "summary": str,
            "strengths": list[str],
            "gaps": list[str],
            "story_assessment": str,
            "visa_warning": str  # Passed through from upstream
        }
    """
    logger.info("📝 Starting job match evaluation...")

    # Load resume content
    try:
        resume_content = load_master_resume()
        logger.info(
            f"✅ Loaded master resume successfully ({len(resume_content)} chars)"
        )
    except Exception:
        logger.exception("❌ Failed to load master resume")
        raise

    logger.info("📄 Evaluation context:")
    logger.info(f"   • Job text length: {len(job_text) if job_text else 0}")
    logger.info(f"   • Resume length: {len(resume_content)}")
    logger.info(f"   • Visa warning: {visa_warning or 'None'}")

    # Build the prompt
    prompt = f"""
You are an expert hiring manager and recruiter.
Evaluate this candidate's MASTER resume against the job description with professional, data-driven judgment.

CANDIDATE CONTEXT:
- Indonesian citizen, graduated from University of Malaya (Malaysia)
- This is their MASTER resume (not yet tailored).
- **CRITICAL**: Do NOT penalize the score for the resume being "generic" or "too long". Evaluate based on the **content** and whether the candidate possesses the required skills/experience.
- **VISA STATUS**: {visa_warning or "None detected (assume eligible/possible)"}

MASTER RESUME:
{resume_content}

JOB DESCRIPTION:
{job_text}

Return ONLY valid JSON in this exact structure:

{{
    "technical_skills_score": (integer 0-100),
    "experience_match_score": (integer 0-100),
    "domain_knowledge_score": (integer 0-100),
    "soft_skills_culture_score": (integer 0-100),
    "match_score": (calculated weighted average integer),
    "summary": "Brief 1–2 sentence honest assessment of fit and readiness",
    "strengths": [
        "Specific strength #1",
        "Specific strength #2",
        "Specific strength #3",
    ],
    "gaps": [
        "Specific gap #1",
        "Specific gap #2",
        "Specific gap #3",
    ],
    "story_assessment": "Weak/Moderate/Strong",
    "reasoning": "Brief explanation of why you gave this specific score"
}}

SCORING GUIDELINES (Weighted):
1. **Technical Skills (55%)**: Does the candidate have the hard skills (languages, frameworks, tools)?
2. **Experience Match (20%)**: Do they have the required years of experience and relevant role history?
3. **Domain Knowledge (10%)**: Do they understand the industry/sector (e.g., Fintech, EdTech, SaaS)?
4. **Soft Skills & Culture (15%)**: Communication, leadership, or other soft traits mentioned.

CALCULATION:
match_score = (Technical * 0.55) + (Experience * 0.20) + (Domain * 0.10) + (Soft * 0.15)

SCORE INTERPRETATION:
- **90–100**: Perfect fit. Meets ALL requirements + nice-to-haves.
- **80–89**: Strong fit. Meets ALL mandatory requirements.
- **70–79**: Good fit. Worth applying. Meets core technical needs, minor gaps in nice-to-haves.
- **60–69**: Moderate fit. Missing key requirements.
- **< 60**: Poor fit.

IMPORTANT:
- Be decisive.
- **IF VISA RESTRICTED**: If the job requires citizenship/green card/clearance that the candidate lacks, the score MUST be < 50 regardless of skills.
"""

    try:
        logger.info("🚀 Sending request to OpenAI API (o4-mini)...")
        response = await client.chat.completions.create(
            model="o4-mini",
            messages=[
                {
                    "role": "system",
                    "content": "You are a balanced but brutally honest hiring manager. Always return valid JSON.",
                },
                {"role": "user", "content": prompt},
            ],
            reasoning_effort="medium",
            response_format={"type": "json_object"},
            seed=42,
        )

        raw_content = response.choices[0].message.content
        logger.debug("----- RAW LLM RESPONSE -----")
        logger.debug(raw_content)
        logger.debug("----------------------------")

        parsed = json.loads(raw_content)

        # Add visa warning from upstream (crawl4ai_service)
        if visa_warning:
            parsed["visa_warning"] = visa_warning

        logger.info(
            f"✅ Job evaluation completed. Match score: {parsed.get('match_score', 'N/A')}"
        )

        return parsed

    except Exception as e:
        logger.exception("❌ LLM evaluation failed")
        raise Exception(f"Job evaluation failed: {str(e)}")