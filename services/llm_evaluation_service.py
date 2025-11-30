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
    "match_score": (integer between 0–100),
    "summary": "Brief 1–2 sentence honest assessment of fit and readiness",
    "strengths": [
        "Specific strength #1",
        "Specific strength #2",
        "Specific strength #3"
    ],
    "gaps": [
        "Specific gap #1",
        "Specific gap #2"
    ],
    "story_assessment": "Weak/Moderate/Strong",
    "reasoning": "Brief explanation of why you gave this specific score"
}}

SCORING GUIDELINES:
- **90–100**: Candidate has ALL critical skills and experience required.
- **80–89**: Candidate has MOST critical skills; gaps are minor or learnable.
- **60–79**: Moderate fit; some key requirements missing.
- **< 60**: Major misalignment.
- **IF VISA RESTRICTED**: If the job requires citizenship/green card/clearance that the candidate lacks, the score MUST be < 50 regardless of skills.

IMPORTANT:
- Be decisive. Use the full range.
- If the candidate is a great fit skill-wise, give a high score (90+) even if the resume needs tailoring.
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