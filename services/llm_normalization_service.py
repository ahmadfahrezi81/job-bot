import os
import json
import logging
from datetime import datetime
from openai import AsyncOpenAI

logger = logging.getLogger(__name__)
client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

DEBUG_DIR = "normalize_debug"
os.makedirs(DEBUG_DIR, exist_ok=True)


def infer_visa_feasibility(normalized: dict, user_country: str = "Indonesia") -> str:
    """
    Fallback heuristic to infer visa feasibility if LLM fails to provide it.
    Same logic as crawl4ai_service for consistency.
    """
    loc = (normalized.get("location") or "").lower()
    desc = (normalized.get("job_description") or "").lower()

    # 1. Same country → eligible
    if user_country.lower() in loc:
        return "eligible"

    # 2. Restricted language
    restricted_terms = [
        "no visa sponsorship",
        "must have work authorization",
        "authorized to work",
        "locals only",
        "work permit required",
        "no relocation support",
    ]
    if any(term in desc for term in restricted_terms):
        return "restricted"

    # 3. Foreign job but no explicit restriction
    known_countries = ["singapore", "malaysia", "australia", "usa", "uk", "canada"]
    if any(country in loc for country in known_countries):
        return "possible"

    # 4. Default
    return "unknown"


async def llm_normalize_job_data(raw_scrape: dict) -> dict:
    """
    Normalize job data to match Crawl4AI output format exactly.

    Output schema (matching crawl4ai_service.py):
    {
        "url": str,
        "job_title": str,
        "company_name": str,
        "location": str | None,
        "work_mode": str | None,  # Remote | Hybrid | Onsite
        "job_description": str,    # Full cleaned description
        "source_title": str,
        "visa_feasibility": str,   # eligible | possible | restricted | unknown
    }

    Goals:
    - Keep FULL job description (not summarized)
    - Preserve original markdown + emojis and text structure
    - Remove UI junk (buttons, banners, footers)
    - Match exact field names from Crawl4AI
    """

    url = raw_scrape.get("url")
    source_title = raw_scrape.get("title")
    raw_text = raw_scrape.get("text", "")
    truncated_text = raw_text[:15000]  # safety max

    logger.info(f"[Normalization] Starting normalization for URL: {url}")

    prompt = f"""
You are a job posting normalization assistant.

You will receive a raw scraped job posting and MUST produce clean JSON that matches this EXACT schema:

{{
  "job_title": "<job title>",
  "company_name": "<company name>",
  "location": "<location or remote>",
  "work_mode": "Remote | Hybrid | Onsite",
  "job_description": "<FULL cleaned job description>",
  "visa_feasibility": "eligible | possible | restricted | unknown"
}}

### 🎯 CRITICAL INSTRUCTIONS

1. **job_description**: Keep the COMPLETE job description with ALL details
   - DO NOT summarize or shorten
   - Preserve markdown formatting, bullet points, emojis
   - Remove ONLY junk: "Apply" buttons, cookie banners, reCAPTCHA, "Powered by X" footers, navigation
   - Keep sections like: About the Role, Responsibilities, Requirements, Benefits, About Company

2. **visa_feasibility**: Infer from the perspective of an applicant based in **Indonesia**
   - "eligible" → Job is in Indonesia, or explicitly open to Indonesian candidates
   - "possible" → Job is outside Indonesia but no visa restrictions mentioned
   - "restricted" → Explicitly states "no visa sponsorship", "locals only", "must have work authorization"
   - "unknown" → Insufficient information

3. **work_mode**: Extract from job posting
   - "Remote" if fully remote
   - "Hybrid" if mix of office/remote
   - "Onsite" if office-based
   - null if not specified

4. **Output ONLY the JSON** - no preamble, no markdown backticks, no explanation

### 📄 SCRAPED CONTENT
{truncated_text}
"""

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    debug_file = f"{DEBUG_DIR}/normalize_{timestamp}.json"

    try:
        logger.info("[Normalization] Sending prompt to LLM...")

        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": "You are a job posting normalizer. You output ONLY valid JSON matching the exact schema provided. No markdown formatting, no extra fields, no explanation.",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0,
            max_tokens=4000,  # Increased to handle full job descriptions
        )

        content = response.choices[0].message.content.strip()
        logger.debug(f"[Normalization] Raw LLM response: {content[:400]}...")

        # Remove markdown code fences if present
        if content.startswith("```json"):
            content = content.replace("```json", "").replace("```", "").strip()
        elif content.startswith("```"):
            content = content.replace("```", "").strip()

        try:
            normalized = json.loads(content)

            # Ensure required fields exist
            required_fields = ["job_title", "company_name", "job_description"]
            missing_fields = [f for f in required_fields if not normalized.get(f)]

            if missing_fields:
                logger.error(
                    f"[Normalization] ❌ Missing required fields: {missing_fields}"
                )
                raise Exception(f"LLM output missing required fields: {missing_fields}")

            # Add metadata fields (same as Crawl4AI)
            normalized["url"] = url
            normalized["source_title"] = source_title

            # Ensure visa_feasibility is set (use heuristic if not provided)
            if not normalized.get("visa_feasibility"):
                normalized["visa_feasibility"] = infer_visa_feasibility(normalized)

            # Ensure optional fields exist with None default
            if "location" not in normalized:
                normalized["location"] = None
            if "work_mode" not in normalized:
                normalized["work_mode"] = None

            logger.info(
                f"[Normalization] ✅ Structured: {normalized.get('job_title')} @ {normalized.get('company_name')} "
                f"(Visa: {normalized.get('visa_feasibility')})"
            )

        except json.JSONDecodeError as e:
            logger.error(f"[Normalization] ❌ JSON parsing failed: {str(e)}")
            logger.error(f"[Normalization] Raw content: {content[:500]}")

            # Fallback: basic extraction
            normalized = {
                "url": url,
                "job_title": source_title or "Unknown Position",
                "company_name": None,
                "location": None,
                "work_mode": None,
                "job_description": raw_text,
                "source_title": source_title,
                "visa_feasibility": "unknown",
            }
            logger.warning("[Normalization] ⚠️ Using fallback normalization")

        # ✅ Save debug info
        debug_payload = {
            "url": url,
            "input_title": source_title,
            "input_text_length": len(raw_text),
            "truncated_input_text": truncated_text,
            "llm_output_raw": content,
            "normalized_output": normalized,
            "timestamp": timestamp,
        }

        with open(debug_file, "w", encoding="utf-8") as f:
            json.dump(debug_payload, f, ensure_ascii=False, indent=2)

        logger.info(f"[Normalization] Debug saved → {debug_file}")

        return normalized

    except Exception as e:
        logger.error(f"[Normalization] Fatal error: {str(e)}")

        # Emergency fallback
        fallback = {
            "url": url,
            "job_title": source_title or "Unknown Position",
            "company_name": None,
            "location": None,
            "work_mode": None,
            "job_description": raw_text or "Unable to extract job description",
            "source_title": source_title,
            "visa_feasibility": "unknown",
        }

        logger.warning("[Normalization] ⚠️ Returning emergency fallback due to error")
        return fallback
