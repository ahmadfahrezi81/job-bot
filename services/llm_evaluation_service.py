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
You are an expert hiring manager, recruiter, and resume optimization specialist.
Evaluate this candidate's master resume against the job description with professional, data-driven judgment.

CANDIDATE CONTEXT:
- Indonesian citizen, graduated from University of Malaya (Malaysia)
- This is their MASTER resume (not yet tailored).

MASTER RESUME:
{resume_content}

JOB DESCRIPTION:
{job_text}

Return ONLY valid JSON in this exact structure (no markdown):

{{
    "match_score": (integer between 0–100 — do not default to 75; choose a value that truly represents the overall fit based on evidence),
    "summary": "Brief 1–2 sentence honest assessment of fit and readiness",
    "strengths": [
        "Specific strength #1 with example from resume",
        "Specific strength #2",
        "Specific strength #3",
        "Specific strength #4"
    ],
    "gaps": [
        "Specific gap #1 or missing requirement",
        "Specific gap #2",
        "Specific gap #3",
        "Specific gap #4"
    ],
    "story_assessment": "Weak/Moderate/Strong — Brief explanation of how logically their background leads to this role"
}}

SCORING GUIDELINES:
- 90–100 → Excellent fit (ready with minimal tailoring)
- 80–89 → Strong fit (competitive once optimized)
- 60–79 → Moderate fit (addressable gaps)
- 40–59 → Weak fit (major experience or skill gaps)
- 0–39 → Poor fit (fundamental misalignment)

CALIBRATION EXAMPLES:
- A resume 100% tailored to this job → 95–100.
- A strong but slightly generic resume → 80–90.
- A partially relevant resume → 60–79.
- A clearly mismatched background → below 50.

IMPORTANT INSTRUCTIONS:
- Use the full 0–100 range; DO NOT default to 75 or 70.
- Score must vary meaningfully depending on fit.
- Be decisive and evidence-based: justify the score through the summary and listed strengths/gaps.
"""

    try:
        logger.info("🚀 Sending request to OpenAI API...")
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": "You are a balanced but brutally honest hiring manager. Always return valid JSON.",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.5,
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
