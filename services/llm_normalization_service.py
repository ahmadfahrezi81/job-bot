import os
import json
import logging
from datetime import datetime
from openai import AsyncOpenAI

logger = logging.getLogger(__name__)
client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

DEBUG_DIR = "normalize_debug"
os.makedirs(DEBUG_DIR, exist_ok=True)


async def llm_normalize_job_data(raw_scrape: dict) -> dict:
    """
    Normalize job data:
    - Keep full job description (rich text)
    - Clean UI junk (buttons, recaptcha, apply text)
    - Preserve emojis + markdown structure
    - Standardize metadata fields
    """

    url = raw_scrape.get("url")
    source_title = raw_scrape.get("title")
    raw_text = raw_scrape.get("text", "")
    truncated_text = raw_text[:15000]  # safety max

    logger.info(f"[Normalization] Starting normalization for URL: {url}")

    prompt = f"""
You are a job posting normalization assistant.

You will receive a raw scraped job posting and MUST produce clean JSON.

### 🎯 GOALS
- Extract **exact** job metadata
- Keep **full job description** (not summarized)
- Preserve original markdown + emojis and text structure
- Remove junk like:
  - "Apply" buttons
  - Cookie banners
  - reCAPTCHA footer
  - Powered by Workday/Greenhouse/Ashby/etc
  - Navigation bars
- DO NOT shorten or rewrite — only clean formatting & remove noise

### ✅ OUTPUT JSON FIELDS

{{
  "url": "{url}",
  "job_title": "<job title>",
  "company_name": "<company name>",
  "location": "<location or remote>",
  "work_mode": "Remote | Hybrid | Onsite",
  "job_description": "<FULL cleaned job description>",
  "source_title": "{source_title}"
}}

### 📝 SCRAPED CONTENT
{truncated_text}
"""

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    debug_file = f"{DEBUG_DIR}/normalize_{timestamp}.json"

    try:
        logger.info("[Normalization] Sending prompt to LLM...")

        response = await client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[
                {"role": "system", "content": "You output ONLY valid JSON."},
                {"role": "user", "content": prompt},
            ],
            temperature=0,
        )

        content = response.choices[0].message.content.strip()
        logger.debug(f"[Normalization] Raw LLM json: {content[:400]}...")

        try:
            normalized = json.loads(content)
            logger.info(
                f"[Normalization] ✅ Structured: {normalized.get('job_title')} @ {normalized.get('company_name')}"
            )
        except json.JSONDecodeError:
            logger.error("[Normalization] ❌ JSON parsing failed — fallback used.")
            normalized = {
                "url": url,
                "job_title": source_title,
                "company_name": None,
                "location": None,
                "work_mode": None,
                "job_description": raw_text,
                "source_title": source_title,
            }

        # ✅ Save debug info
        debug_payload = {
            "url": url,
            "input_title": source_title,
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
        raise Exception("Normalization failed")
