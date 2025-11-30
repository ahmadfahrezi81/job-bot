# services/llm_cover_letter_service.py
from openai import AsyncOpenAI
import logging
import os
import json

logger = logging.getLogger(__name__)
client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def load_master_resume() -> str:
    """Load the master resume content from file (same source as resume tailoring)"""
    try:
        with open("data/resume-content.tex", "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        raise Exception("Master resume not found at data/resume-content.tex")


def fix_latex_escaping(latex_content: str) -> str:
    """
    Convert LLM placeholders to proper LaTeX escapes and sanitize common special characters.

    Placeholders avoid JSON escaping issues:
    - __APOS__ → ' (proper apostrophe/single quote)
    - __AMP__ → \&
    - __PCT__ → \%
    - __HASH__ → \#
    - __DOLLAR__ → \$
    """
    # 1. Active Sanitization: Replace "smart" characters that break LaTeX
    smart_replacements = {
        "’": "'",   # Smart apostrophe
        "‘": "'",   # Smart opening quote
        "“": '"',   # Smart double quote
        "”": '"',   # Smart closing quote
        "–": "--",  # En-dash
        "—": "---", # Em-dash
        "…": "...", # Ellipsis
    }
    
    for char, replacement in smart_replacements.items():
        if char in latex_content:
            latex_content = latex_content.replace(char, replacement)

    # 2. Clean up any backslashes before placeholders
    latex_content = latex_content.replace(r"\__APOS__", "__APOS__")
    latex_content = latex_content.replace(r"\__PCT__", "__PCT__")
    latex_content = latex_content.replace(r"\__AMP__", "__AMP__")
    latex_content = latex_content.replace(r"\__HASH__", "__HASH__")
    latex_content = latex_content.replace(r"\__DOLLAR__", "__DOLLAR__")

    # 3. Convert placeholders to proper characters
    replacements = {
        "__APOS__": "'",
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
            logger.info(f"🔧 Converted {count} × '{placeholder}' → proper character")
            total_fixes += count

    if total_fixes > 0:
        logger.info(f"✅ Total placeholder conversions: {total_fixes}")

    return latex_content


async def tailor_cover_letter(
    job_description: str,
    evaluation: dict,
    job_title: str = None,
    company_name: str = None,
) -> dict:
    """
    Generates a tailored cover letter from master resume + job description.

    Key improvements over master CL approach:
    - Selects most relevant projects from full resume
    - Reframes experiences based on role requirements
    - Extracts company-specific hooks from JD
    - Ensures 150-175 words, human tone, no AI clichés

    Args:
        job_description: Full text of the job posting
        evaluation: Dict containing job evaluation data (unused)
        job_title: Title of the position (e.g., "Associate Data Engineer")
        company_name: Name of the company (e.g., "NTT DATA")

    Returns:
        {
            "tailored_content": "... LaTeX content ...",
            "selected_projects": ["Project 1", "Project 2"],
            "word_count": 165,
            "quality_flags": {
                "has_metrics": true,
                "no_cliches": true,
                "proper_length": true
            }
        }
    """
    logger.info("✍️ Starting cover letter generation from resume...")
    logger.info(f"   • Job Title: {job_title or 'Not specified'}")
    logger.info(f"   • Company: {company_name or 'Not specified'}")

    # Load master resume (not master cover letter)
    try:
        master_resume = load_master_resume()
        logger.info(f"✅ Loaded master resume ({len(master_resume)} chars)")
    except Exception:
        logger.exception("❌ Failed to load master resume")
        raise

    logger.info(f"📊 Generating cover letter...")

    # Build role context string
    role_context = ""
    if job_title and company_name:
        role_context = f"{job_title} at {company_name}"
    elif job_title:
        role_context = job_title
    elif company_name:
        role_context = f"position at {company_name}"
    else:
        role_context = "this position"

    prompt = f"""Write a creative and human-sounding cover letter for {role_context}.

# Task
Generate body paragraphs only (no header/signature). Use the candidate's resume to select the most relevant experiences and weave them into a compelling narrative for this role.

# Requirements
- Length: Approximately 150-200 words.
- Tone: Natural, engaging, and professional. Avoid stiff corporate jargon or robotic AI phrases. Write as if you are a real person genuinely interested in the role.
- Content: Focus on telling a story about the candidate's experience that connects with the job requirements.
- Use LaTeX escapes: __APOS__ for apostrophes, __PCT__ for percents, __AMP__ for ampersands.
- Separate paragraphs with double newlines.

# Resume Content
{master_resume}

# Job Description
{job_description[:10000]}

# Instructions
1. Analyze the job description to understand what the company values.
2. Select 1-2 key projects or experiences from the resume that best demonstrate the candidate's fit.
3. Frame your past experience not just as history, but as proof of what you will achieve for this company in the future.
4. Start directly with a "hook"—either a strong alignment with the company's mission or a specific challenge from the JD that excites you. Do NOT start with "I am writing to apply..." or similar generic phrases.
5. Write a cover letter that flows naturally. Do not just list achievements; explain *why* they matter for this specific role.

# Output Format (JSON)
{{
    "tailored_content": "body paragraphs with LaTeX escapes",
    "selected_projects": ["Project 1 name", "Project 2 name"],
    "word_count": 165,
    "quality_flags": {{
        "has_metrics": true,
        "no_cliches": true,
        "proper_length": true
    }}
}}

Job Title: {job_title or '[Job Title]'}
Company: {company_name or '[Company]'}"""

    try:
        logger.info("🚀 Sending request to OpenAI (o4-mini)...")

        response = await client.chat.completions.create(
            model="o4-mini",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a skilled career coach who writes authentic, engaging cover letters. "
                        "Focus on storytelling and genuine connection rather than just listing metrics. "
                        "Avoid robotic phrasing and clichés. "
                        "Use __APOS__ for apostrophes, __PCT__ for percents, __AMP__ for ampersands. "
                        "Return body paragraphs only (no header/footer). Return valid JSON."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            reasoning_effort="low",
            max_completion_tokens=3000,
            response_format={"type": "json_object"},
        )

        raw_content = response.choices[0].message.content

        if not raw_content or raw_content.strip() == "":
            logger.error("❌ Empty response from OpenAI")
            raise ValueError("OpenAI returned empty response")

        logger.debug("----- RAW COVER LETTER RESPONSE (first 1000 chars) -----")
        logger.debug(raw_content[:1000])
        logger.debug("--------------------------------------------------------")

        parsed = json.loads(raw_content)

        # Validate required fields
        required_fields = [
            "tailored_content",
            "selected_projects",
            "word_count",
            "quality_flags",
        ]
        for field in required_fields:
            if field not in parsed:
                raise ValueError(f"Missing required field: {field}")

        # Validate types
        if not isinstance(parsed["selected_projects"], list):
            raise ValueError("selected_projects must be a list")
        if not isinstance(parsed["quality_flags"], dict):
            raise ValueError("quality_flags must be a dict")

        # Convert placeholders to LaTeX escapes in content
        parsed["tailored_content"] = fix_latex_escaping(parsed["tailored_content"])

        # Clean placeholders in project names for display
        parsed["selected_projects"] = [
            p.replace("__APOS__", "'")
            .replace("__AMP__", " & ")
            .replace("__PCT__", "% ")
            for p in parsed["selected_projects"]
        ]

        # Log quality metrics
        quality = parsed.get("quality_flags", {})

        logger.info("✅ Cover letter generation completed")
        logger.info(f"   • Word count: {parsed.get('word_count', 'unknown')}")
        logger.info(f"   • Selected projects: {', '.join(parsed['selected_projects'])}")
        logger.info(f"   • Quality checks:")
        logger.info(f"     - Has metrics: {quality.get('has_metrics', 'N/A')}")
        logger.info(f"     - No clichés: {quality.get('no_cliches', 'N/A')}")
        logger.info(f"     - Proper length: {quality.get('proper_length', 'N/A')}")

        return parsed

    except json.JSONDecodeError as e:
        logger.exception("❌ Failed to parse JSON response from OpenAI")
        logger.error(f"Response length: {len(raw_content) if raw_content else 0}")
        logger.error(
            f"First 500 chars: {raw_content[:500] if raw_content else 'EMPTY'}"
        )
        raise Exception(f"Invalid JSON from OpenAI: {str(e)}")
    except Exception as e:
        logger.exception("❌ Cover letter generation failed")
        raise Exception(f"Cover letter generation failed: {str(e)}")
