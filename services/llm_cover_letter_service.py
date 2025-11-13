# # services/llm_cover_letter_service.py
# from openai import AsyncOpenAI
# import logging
# import os
# import json

# logger = logging.getLogger(__name__)
# client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))


# def load_master_cover_letter() -> str:
#     """Load the master cover letter content from file"""
#     try:
#         with open("data/CL_content.tex", "r", encoding="utf-8") as f:
#             return f.read()
#     except FileNotFoundError:
#         raise Exception("Master cover letter not found at data/CL_content.tex")


# def fix_latex_escaping(latex_content: str) -> str:
#     """
#     Convert LLM placeholders to proper LaTeX escapes.

#     Placeholders avoid JSON escaping issues:
#     - __APOS__ → ' (proper apostrophe/single quote)
#     - __AMP__ → \&
#     - __PCT__ → \%
#     - __HASH__ → \#
#     - __DOLLAR__ → \$
#     """
#     # First, clean up any backslashes before placeholders
#     latex_content = latex_content.replace(r"\__APOS__", "__APOS__")
#     latex_content = latex_content.replace(r"\__PCT__", "__PCT__")
#     latex_content = latex_content.replace(r"\__AMP__", "__AMP__")
#     latex_content = latex_content.replace(r"\__HASH__", "__HASH__")
#     latex_content = latex_content.replace(r"\__DOLLAR__", "__DOLLAR__")

#     # Convert placeholders to proper characters
#     replacements = {
#         "__APOS__": "'",  # UTF-8 right single quotation mark (works in modern LaTeX)
#         "__AMP__": r" \& ",
#         "__PCT__": r"\% ",
#         "__HASH__": r" \#",
#         "__DOLLAR__": r" \$",
#     }

#     total_fixes = 0
#     for placeholder, latex_escape in replacements.items():
#         count = latex_content.count(placeholder)
#         if count > 0:
#             latex_content = latex_content.replace(placeholder, latex_escape)
#             logger.info(f"🔧 Converted {count} × '{placeholder}' → proper character")
#             total_fixes += count

#     if total_fixes > 0:
#         logger.info(f"✅ Total placeholder conversions: {total_fixes}")

#     return latex_content


# async def tailor_cover_letter(
#     job_description: str,
#     evaluation: dict,
#     job_title: str = None,
#     company_name: str = None,
# ) -> dict:
#     """
#     Tailors cover letter content for a specific job posting.
#     Optimized for o4-mini: natural, professional tone without AI clichés.
#     """
#     logger.info("✏️ Starting cover letter tailoring...")
#     logger.info(f"   • Job Title: {job_title or 'Not specified'}")
#     logger.info(f"   • Company: {company_name or 'Not specified'}")

#     # Load master cover letter
#     try:
#         master_cover_letter = load_master_cover_letter()
#         logger.info(f"✅ Loaded master cover letter ({len(master_cover_letter)} chars)")
#     except Exception:
#         logger.exception("❌ Failed to load master cover letter")
#         raise

#     # Extract key info from evaluation
#     match_score = evaluation.get("match_score", 0)
#     strengths = evaluation.get("strengths", [])
#     gaps = evaluation.get("gaps", [])

#     logger.info(f"📊 Tailoring for match score: {match_score}%")
#     logger.info(f"   • {len(strengths)} strengths identified")
#     logger.info(f"   • {len(gaps)} gaps identified")

#     # Build role context string
#     role_context = ""
#     if job_title and company_name:
#         role_context = f"{job_title} at {company_name}"
#     elif job_title:
#         role_context = job_title
#     elif company_name:
#         role_context = f"position at {company_name}"
#     else:
#         role_context = "this position"

#     prompt = f"""Write a professional cover letter for: {role_context}

# Match Score: {match_score}%
# Key Strengths: {', '.join(strengths[:3])}
# Gaps to Address: {', '.join(gaps[:2])}

# MASTER COVER LETTER STRUCTURE:
# {master_cover_letter}

# JOB DESCRIPTION:
# {job_description[:3000]}

# CRITICAL RULES:
# 1. ONE PAGE (320-380 words maximum)
# 2. Replace [Job Title] with: {job_title or '[Job Title]'}
# 3. Replace [Company Name] with: {company_name or '[Company Name]'}
# 4. Keep exact LaTeX structure from master (no \\documentclass or \\begin{{document}})
# 5. Use placeholders for special characters:
#    - __APOS__ for apostrophes (e.g., "I__APOS__ve" not "I've")
#    - __AMP__ for ampersands (e.g., "Q__AMP__A")
#    - __PCT__ for percents (e.g., "95__PCT__")
#    - __HASH__ for hashes, __DOLLAR__ for dollar signs
#    - DO NOT put backslashes before placeholders

# WRITING TONE:
# • Professional but genuine - sound like a real person, not an AI
# • Show you did research - mention specific company details, products, or values
# • Confident without being arrogant ("I built X" not "I'm passionate about building X")
# • Direct and concise - avoid filler like "excited to apply", "thrilled", "passionate", "eager to bring"
# • No corporate buzzwords: avoid "leverage", "synergy", "solutions-oriented", "passionate about"
# • Use active voice and strong verbs

# BANNED PHRASES (too generic/AI-like):
# ✗ "I'm excited to apply"
# ✗ "resonates deeply with my passion"
# ✗ "I admire [company]'s mission to"
# ✗ "eager to bring my skills"
# ✗ "enthusiastic about the prospect"
# ✗ "I would love the opportunity"
# ✗ "thrilled to contribute"

# STRUCTURE:
# Para 1 (3-4 sentences): Hook with specific company/product detail. Why this role matters to you (briefly). One standout qualification.

# Para 2 (4-5 sentences): Most relevant experience with concrete metrics. Show direct alignment with job requirements. No fluff.

# Para 3 (3-4 sentences): Complementary skills or project that demonstrates versatility. Keep it punchy.

# Para 4 (2-3 sentences): Brief closing. Clear call to action. Professional sign-off.

# EXAMPLES OF GOOD OPENINGS:
# ✓ "Your work on [specific product/initiative] caught my attention because [genuine reason]. I__APOS__ve spent the last two years building similar systems at Grab, and I see clear ways I could contribute to [specific team/goal]."
# ✓ "I__APOS__ve been following [company]__APOS__s [specific initiative] since [timeframe]. As someone who [relevant experience], I understand the challenges your team is solving."

# MASTER COVER LETTER REFERENCE:
# {master_cover_letter}

# Return JSON:
# {{
#     "tailored_content": "complete LaTeX content",
#     "writing_strategy": {{
#         "summary": "approach and key themes",
#         "opening_hook": "opening strategy",
#         "body_focus": "main points",
#         "gap_handling": "how gaps addressed"
#     }},
#     "change_summary": {{
#         "key_customizations": "major changes",
#         "word_count": "approximate count",
#         "tone_notes": "how natural tone achieved"
#     }}
# }}"""

#     try:
#         logger.info("🚀 Sending request to OpenAI (o4-mini)...")

#         response = await client.chat.completions.create(
#             model="o4-mini",
#             messages=[
#                 {
#                     "role": "system",
#                     "content": "You are a professional cover letter writer who writes like a real human, not an AI. Be genuine, direct, and concise. Use __APOS__ for apostrophes, __AMP__ __PCT__ __HASH__ __DOLLAR__ for other special characters. Never use backslashes before placeholders. Return valid JSON.",
#                 },
#                 {"role": "user", "content": prompt},
#             ],
#             reasoning_effort="low",
#             max_completion_tokens=4000,
#             response_format={"type": "json_object"},
#         )

#         raw_content = response.choices[0].message.content

#         if not raw_content or raw_content.strip() == "":
#             logger.error("❌ Empty response from OpenAI")
#             raise ValueError("OpenAI returned empty response")

#         logger.debug("----- RAW RESPONSE (first 1000 chars) -----")
#         logger.debug(raw_content[:1000])
#         logger.debug("--------------------------------------------")

#         parsed = json.loads(raw_content)

#         # Validate required fields
#         required_fields = ["tailored_content", "writing_strategy", "change_summary"]
#         for field in required_fields:
#             if field not in parsed:
#                 raise ValueError(f"Missing required field: {field}")

#         # Validate nested structures
#         if not isinstance(parsed["writing_strategy"], dict):
#             raise ValueError("writing_strategy must be a dict")
#         if not isinstance(parsed["change_summary"], dict):
#             raise ValueError("change_summary must be a dict")

#         # Convert placeholders to LaTeX escapes in content
#         parsed["tailored_content"] = fix_latex_escaping(parsed["tailored_content"])

#         # Clean placeholders in analysis fields for display
#         def clean_placeholders_for_display(obj):
#             """Recursively replace placeholders with readable text"""
#             if isinstance(obj, str):
#                 return (
#                     obj.replace("__APOS__", "'")
#                     .replace("__AMP__", " & ")
#                     .replace("__PCT__", "% ")
#                     .replace("__HASH__", " #")
#                     .replace("__DOLLAR__", " $")
#                 )
#             elif isinstance(obj, dict):
#                 return {k: clean_placeholders_for_display(v) for k, v in obj.items()}
#             elif isinstance(obj, list):
#                 return [clean_placeholders_for_display(item) for item in obj]
#             return obj

#         parsed["writing_strategy"] = clean_placeholders_for_display(
#             parsed["writing_strategy"]
#         )
#         parsed["change_summary"] = clean_placeholders_for_display(
#             parsed["change_summary"]
#         )

#         logger.info("✅ Cover letter tailoring completed successfully")
#         logger.info(f"   • Content length: {len(parsed['tailored_content'])} chars")
#         logger.info(
#             f"   • Word count: {parsed['change_summary'].get('word_count', 'unknown')}"
#         )

#         return parsed

#     except json.JSONDecodeError as e:
#         logger.exception("❌ Failed to parse JSON response from OpenAI")
#         logger.error(f"Response length: {len(raw_content) if raw_content else 0}")
#         logger.error(
#             f"First 500 chars: {raw_content[:500] if raw_content else 'EMPTY'}"
#         )
#         raise Exception(f"Invalid JSON from OpenAI: {str(e)}")
#     except Exception as e:
#         logger.exception("❌ Cover letter tailoring failed")
#         raise Exception(f"Cover letter tailoring failed: {str(e)}")


# services/llm_cover_letter_service.py
from openai import AsyncOpenAI
import logging
import os
import json

logger = logging.getLogger(__name__)
client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def load_master_cover_letter() -> str:
    """Load the master cover letter content from file"""
    try:
        with open("data/CL_content.tex", "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        raise Exception("Master cover letter not found at data/CL_content.tex")


def fix_latex_escaping(latex_content: str) -> str:
    """
    Convert LLM placeholders to proper LaTeX escapes.

    Placeholders avoid JSON escaping issues:
    - __APOS__ → ' (proper apostrophe/single quote)
    - __AMP__ → \&
    - __PCT__ → \%
    - __HASH__ → \#
    - __DOLLAR__ → \$
    """
    # First, clean up any backslashes before placeholders
    latex_content = latex_content.replace(r"\__APOS__", "__APOS__")
    latex_content = latex_content.replace(r"\__PCT__", "__PCT__")
    latex_content = latex_content.replace(r"\__AMP__", "__AMP__")
    latex_content = latex_content.replace(r"\__HASH__", "__HASH__")
    latex_content = latex_content.replace(r"\__DOLLAR__", "__DOLLAR__")

    # Convert placeholders to proper characters
    replacements = {
        "__APOS__": "'",  # UTF-8 right single quotation mark (works in modern LaTeX)
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
    Tailors cover letter content for a specific job posting.
    Optimized for o4-mini: SHORT (150-200 words), natural, human tone.
    """
    logger.info("✏️ Starting cover letter tailoring...")
    logger.info(f"   • Job Title: {job_title or 'Not specified'}")
    logger.info(f"   • Company: {company_name or 'Not specified'}")

    # Load master cover letter
    try:
        master_cover_letter = load_master_cover_letter()
        logger.info(f"✅ Loaded master cover letter ({len(master_cover_letter)} chars)")
    except Exception:
        logger.exception("❌ Failed to load master cover letter")
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
        role_context = f"{job_title} at {company_name}"
    elif job_title:
        role_context = job_title
    elif company_name:
        role_context = f"position at {company_name}"
    else:
        role_context = "this position"

    prompt = f"""You are a professional cover letter writer. Write a SHORT, HUMAN cover letter for: {role_context}

CRITICAL LENGTH REQUIREMENT: 150-200 words MAXIMUM (about 12-16 sentences total)

Match Score: {match_score}%
Top Strengths: {', '.join(strengths[:3])}
Key Gaps: {', '.join(gaps[:2]) if gaps else 'None'}

MASTER COVER LETTER (SELECT 1-2 MOST RELEVANT SECTIONS):
{master_cover_letter}

JOB DESCRIPTION:
{job_description[:3000]}

===== WRITING RULES =====

1. LENGTH: 150-200 words TOTAL
   - Opening: 2 sentences (30-40 words)
   - Body: Pick 1-2 paragraphs from master (80-120 words)
   - Closing: 1-2 sentences (20-30 words)

2. STRUCTURE:
   - Para 1: "I'm applying for [Job Title] at [Company]. [One standout qualification that matches their top need]"
   - Para 2: Select THE MOST RELEVANT option from master:
     * Option A (Backend/Systems) if job mentions: databases, APIs, architecture, scalability, backend
     * Option B (Full-Stack) if job mentions: frontend, React, full-stack, product development
     * Option C (QA/Automation) if job mentions: testing, QA, automation, CI/CD, quality
     * Option D (Versatility) if job is startup/generalist role
   - Para 3 (OPTIONAL - only if word count allows): Brief second skill
   - Closing: "I'd welcome the chance to discuss how I can contribute to [Company]'s [specific team/goal]. Let's connect."

3. TONE - MUST SOUND HUMAN:
   ✓ Direct and confident: "I built X that did Y"
   ✓ Specific metrics: "reduced time by 60%", "200+ users"
   ✓ Natural language: "I'd welcome the chance" not "I would be thrilled"
   
   ✗ NO AI CLICHÉS:
     - "excited/thrilled/passionate to apply"
     - "resonate with my passion"
     - "eager to bring my skills"
     - "I admire [company]'s mission"
     - "looking forward to the opportunity"
     - "leverage my experience"

4. COMPANY RESEARCH:
   - If you can find REAL, SPECIFIC details about the company from the job description (product names, tech stack, recent projects, team structure), mention them
   - If you cannot find specific details, DO NOT FABRICATE. Just focus on role requirements
   - NEVER invent case studies, blog posts, or initiatives that aren't explicitly mentioned

5. LATEX REQUIREMENTS:
   - Keep exact structure from master (\\contactline, \\vspace, \\signaturespace commands)
   - Replace [Job Title] with: {job_title or '[Job Title]'}
   - Replace [Company Name] with: {company_name or '[Company Name]'}
   - Use placeholders for special characters:
     * __APOS__ for apostrophes (e.g., "I__APOS__ve", "company__APOS__s")
     * __AMP__ for ampersands (e.g., "Q__AMP__A")
     * __PCT__ for percents (e.g., "60__PCT__")
     * __HASH__ for hashes, __DOLLAR__ for dollar signs
   - DO NOT put backslashes before placeholders

6. SELECTION LOGIC:
   Job mentions backend/databases/APIs → Use Option A (UM PTM + TeaPOS backend)
   Job mentions frontend/React/full-stack → Use Option B (CommerceOwl full-stack)
   Job mentions QA/testing/automation → Use Option C (Grab QA automation)
   Job is startup/generalist → Use Option D (Cross-functional)
   
   ONLY include 1 body paragraph unless the role explicitly requires multiple skills

7. WORD COUNT ENFORCEMENT:
   - Opening paragraph: ~30-40 words
   - Body paragraph(s): ~80-120 words (1-2 paragraphs max)
   - Closing: ~20-30 words
   - TOTAL: 150-200 words

===== OUTPUT FORMAT =====

Return JSON:
{{
    "tailored_content": "complete LaTeX content (150-200 words)",
    "writing_strategy": {{
        "selected_option": "which body paragraph(s) used (A/B/C/D)",
        "word_count": "actual word count",
        "customization_approach": "brief explanation of tailoring decisions",
        "company_details_used": "specific company details mentioned (or 'none - focused on role requirements')"
    }},
    "quality_check": {{
        "length_ok": true/false,
        "no_ai_cliches": true/false,
        "specific_metrics_included": true/false,
        "human_tone_achieved": true/false
    }}
}}"""

    try:
        logger.info("🚀 Sending request to OpenAI (o4-mini)...")

        response = await client.chat.completions.create(
            model="o4-mini",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a professional cover letter writer. Write SHORT (150-200 words), HUMAN cover letters. "
                        "Be direct and confident. Use specific metrics. NO AI clichés like 'excited to apply' or 'passionate about'. "
                        "Use __APOS__ for apostrophes, __AMP__ __PCT__ __HASH__ __DOLLAR__ for special characters. "
                        "Never use backslashes before placeholders. Return valid JSON."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            reasoning_effort="medium",  # Changed from "low" to allow better quality control
            max_completion_tokens=4000,
            response_format={"type": "json_object"},
        )

        raw_content = response.choices[0].message.content

        if not raw_content or raw_content.strip() == "":
            logger.error("❌ Empty response from OpenAI")
            raise ValueError("OpenAI returned empty response")

        logger.debug("----- RAW RESPONSE (first 1000 chars) -----")
        logger.debug(raw_content[:1000])
        logger.debug("--------------------------------------------")

        parsed = json.loads(raw_content)

        # Validate required fields
        required_fields = ["tailored_content", "writing_strategy", "quality_check"]
        for field in required_fields:
            if field not in parsed:
                raise ValueError(f"Missing required field: {field}")

        # Validate nested structures
        if not isinstance(parsed["writing_strategy"], dict):
            raise ValueError("writing_strategy must be a dict")
        if not isinstance(parsed["quality_check"], dict):
            raise ValueError("quality_check must be a dict")

        # Convert placeholders to LaTeX escapes in content
        parsed["tailored_content"] = fix_latex_escaping(parsed["tailored_content"])

        # Clean placeholders in analysis fields for display
        def clean_placeholders_for_display(obj):
            """Recursively replace placeholders with readable text"""
            if isinstance(obj, str):
                return (
                    obj.replace("__APOS__", "'")
                    .replace("__AMP__", " & ")
                    .replace("__PCT__", "% ")
                    .replace("__HASH__", " #")
                    .replace("__DOLLAR__", " $")
                )
            elif isinstance(obj, dict):
                return {k: clean_placeholders_for_display(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [clean_placeholders_for_display(item) for item in obj]
            return obj

        parsed["writing_strategy"] = clean_placeholders_for_display(
            parsed["writing_strategy"]
        )
        parsed["quality_check"] = clean_placeholders_for_display(
            parsed["quality_check"]
        )

        # Log quality metrics
        quality = parsed.get("quality_check", {})
        logger.info("✅ Cover letter tailoring completed")
        logger.info(
            f"   • Word count: {parsed['writing_strategy'].get('word_count', 'unknown')}"
        )
        logger.info(
            f"   • Selected option: {parsed['writing_strategy'].get('selected_option', 'unknown')}"
        )
        logger.info(f"   • Quality checks:")
        logger.info(f"     - Length OK: {quality.get('length_ok', 'N/A')}")
        logger.info(f"     - No AI clichés: {quality.get('no_ai_cliches', 'N/A')}")
        logger.info(f"     - Human tone: {quality.get('human_tone_achieved', 'N/A')}")

        return parsed

    except json.JSONDecodeError as e:
        logger.exception("❌ Failed to parse JSON response from OpenAI")
        logger.error(f"Response length: {len(raw_content) if raw_content else 0}")
        logger.error(
            f"First 500 chars: {raw_content[:500] if raw_content else 'EMPTY'}"
        )
        raise Exception(f"Invalid JSON from OpenAI: {str(e)}")
    except Exception as e:
        logger.exception("❌ Cover letter tailoring failed")
        raise Exception(f"Cover letter tailoring failed: {str(e)}")
