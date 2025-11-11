# services/crawl4ai_service.py
"""
Fast path: Crawl4AI with LLM extraction
Extracts normalized job data in one pass
"""
import os
import json
import logging
from datetime import datetime
from crawl4ai import (
    AsyncWebCrawler,
    BrowserConfig,
    CrawlerRunConfig,
    CacheMode,
    LLMConfig,
)
from crawl4ai.extraction_strategy import LLMExtractionStrategy
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

DEBUG_DIR = "crawl4ai_debug"
os.makedirs(DEBUG_DIR, exist_ok=True)


# Define the schema we want extracted
class NormalizedJob(BaseModel):
    job_title: str = Field(description="Job title")
    company_name: str = Field(description="Company name")
    location: str | None = Field(description="Location or Remote", default=None)
    work_mode: str | None = Field(
        description="Work arrangement: Remote, Hybrid, or Onsite", default=None
    )
    job_description: str = Field(
        description="Full cleaned job description with markdown formatting"
    )
    visa_feasibility: str | None = Field(
        description=(
            "Visa feasibility from the perspective of an applicant based in Indonesia. "
            "One of: eligible, possible, restricted, unknown."
        ),
        default=None,
    )
    job_available: bool = Field(
        description="Whether the job posting is still active/available (not filled or closed)",
        default=True,
    )
    unavailable_reason: str | None = Field(
        description="Reason if job is not available (e.g., 'Position filled', 'Posting expired', 'Page not found')",
        default=None,
    )


def infer_visa_feasibility(normalized: dict, user_country: str = "Indonesia") -> str:
    """Fallback heuristic to infer visa feasibility if LLM fails to provide it."""
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


def detect_job_unavailable(markdown: str, url: str) -> tuple[bool, str | None]:
    """
    Detect if a job posting is no longer available.

    Returns: (is_unavailable, reason)
    """
    if not markdown or len(markdown.strip()) < 100:
        return True, "Page content too short or empty"

    markdown_lower = markdown.lower()

    # Common patterns for unavailable jobs
    unavailable_patterns = [
        ("position has been filled", "Position already filled"),
        ("this job is no longer available", "Job posting closed"),
        ("posting has expired", "Posting expired"),
        ("job posting is no longer active", "Job no longer active"),
        ("position is no longer open", "Position closed"),
        ("this position has been closed", "Position closed"),
        ("404", "Page not found (404)"),
        ("page not found", "Page not found"),
        (
            "sorry, this job is no longer accepting applications",
            "No longer accepting applications",
        ),
        ("this opportunity is no longer available", "Opportunity closed"),
    ]

    for pattern, reason in unavailable_patterns:
        if pattern in markdown_lower:
            logger.warning(f"[Crawl4AI] 🚫 Detected unavailable job: {reason}")
            return True, reason

    # Check if content looks like actual job posting
    job_indicators = [
        "responsibilities",
        "requirements",
        "qualifications",
        "about the role",
        "what you'll do",
        "job description",
        "apply now",
    ]

    has_job_content = any(indicator in markdown_lower for indicator in job_indicators)

    if not has_job_content and len(markdown) < 500:
        return True, "No job description found - possibly removed or expired"

    return False, None


async def crawl4ai_extract(url: str) -> dict:
    """
    Extract normalized job data using Crawl4AI + LLM strategy.

    Returns normalized job dict or raises exception on failure.
    Special exceptions:
    - JobUnavailableError: Job posting no longer available
    - VisaRestrictedError: Job has visa restrictions
    """
    logger.info(f"[Crawl4AI] Starting extraction: {url}")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    try:
        # More specific extraction instructions
        extraction_prompt = """
        You are extracting job posting data from a webpage.

        CRITICAL: First, determine if this job posting is still available:
        - Look for messages like "position filled", "no longer available", "expired", etc.
        - If you see such messages, set job_available=false and provide unavailable_reason
        
        If the job IS available, extract:
        - Job title (e.g., "Software Engineer", "Product Manager")
        - Company name
        - Location information (city, country, or "Remote")
        - Full job description including responsibilities, requirements, benefits

        Additionally, infer "visa_feasibility" from the perspective of an applicant based in **Indonesia**.
        Possible values:
        - "eligible" → Job is in Indonesia, or explicitly open to Indonesian candidates.
        - "possible" → Job is outside Indonesia but does not mention visa restrictions.
        - "restricted" → Job explicitly states "no visa sponsorship", "locals only", "must have work authorization", or similar.
        - "unknown" → Insufficient information to determine.

        Clean up the description by removing:
        - Navigation menus, headers, footers
        - "Apply now" buttons
        - Cookie banners
        - reCAPTCHA notices
        - "Powered by Workday" or similar footers

        Keep the complete job description with all details intact.
        Preserve any markdown formatting, bullet points, and emojis.

        Return the data as a single JSON object (not an array).
        """

        # ✅ Use LLMConfig as per docs
        llm_config = LLMConfig(
            provider="openai/gpt-4o-mini", api_token=os.getenv("OPENAI_API_KEY")
        )

        extraction_strategy = LLMExtractionStrategy(
            llm_config=llm_config,
            schema=NormalizedJob.model_json_schema(),
            extraction_type="schema",
            instruction=extraction_prompt,
            chunk_token_threshold=4000,
            apply_chunking=True,
            input_format="markdown",
            extra_args={"temperature": 0, "max_tokens": 2000},
        )

        # ✅ Use CrawlerRunConfig as per docs
        crawl_config = CrawlerRunConfig(
            extraction_strategy=extraction_strategy,
            cache_mode=CacheMode.BYPASS,
            word_count_threshold=10,
            wait_for="body",
            delay_before_return_html=2.0,
        )

        browser_config = BrowserConfig(headless=True, verbose=True, text_mode=True)

        async with AsyncWebCrawler(config=browser_config, verbose=True) as crawler:
            result = await crawler.arun(url=url, config=crawl_config)

            if not result.success:
                raise Exception(f"Crawl failed: {result.error_message}")

            # Debug: Save raw markdown
            # markdown_debug = f"{DEBUG_DIR}/markdown_{timestamp}.md"
            # with open(markdown_debug, "w", encoding="utf-8") as f:
            #     f.write(result.markdown or "NO MARKDOWN")
            # logger.info(f"[Crawl4AI] Saved markdown → {markdown_debug}")

            # Debug: Save raw markdown (force flush to disk)
            markdown_debug = f"{DEBUG_DIR}/markdown_{timestamp}.md"
            with open(markdown_debug, "w", encoding="utf-8") as f:
                f.write(result.markdown or "NO MARKDOWN")
                f.flush()
                os.fsync(f.fileno())
            logger.info(f"[Crawl4AI] ✅ Markdown file flushed: {markdown_debug}")

            # ✅ Check if job is unavailable (before LLM parsing)
            is_unavailable, unavailable_reason = detect_job_unavailable(
                result.markdown, url
            )

            if is_unavailable:
                logger.warning(f"[Crawl4AI] 🚫 Job unavailable: {unavailable_reason}")
                raise JobUnavailableError(unavailable_reason)

            extracted = result.extracted_content
            if not extracted:
                raise Exception("No content extracted")

            if isinstance(extracted, str):
                parsed = json.loads(extracted)
            else:
                parsed = extracted

            if isinstance(parsed, list):
                if not parsed:
                    raise Exception("LLM returned empty array.")
                normalized = parsed[0]
                logger.warning("[Crawl4AI] LLM returned array, using first item")
            elif isinstance(parsed, dict):
                normalized = parsed
            else:
                raise Exception(f"Unexpected parsed type: {type(parsed)}")

            if not isinstance(normalized, dict):
                raise Exception(f"Normalized is not a dict: {type(normalized)}")

            # ✅ Check if LLM detected job as unavailable
            if not normalized.get("job_available", True):
                reason = normalized.get(
                    "unavailable_reason", "Job posting no longer available"
                )
                logger.warning(f"[Crawl4AI] 🚫 LLM detected unavailable job: {reason}")
                raise JobUnavailableError(reason)

            # Ensure required fields exist
            if not normalized.get("job_title") or not normalized.get("job_description"):
                raise Exception(
                    f"Missing required fields. Got: {list(normalized.keys())}"
                )

            # Add metadata
            normalized["url"] = url
            normalized["source_title"] = result.metadata.get("title", "")

            # Ensure visa_feasibility always set
            if not normalized.get("visa_feasibility"):
                normalized["visa_feasibility"] = infer_visa_feasibility(normalized)

            # ✅ Check if visa is restricted - raise special exception
            if normalized.get("visa_feasibility") == "restricted":
                logger.warning(f"[Crawl4AI] 🚫 Visa restricted for this position")
                raise VisaRestrictedError(
                    "Job requires work authorization/visa sponsorship not available"
                )

            logger.info(
                f"[Crawl4AI] ✅ Extracted: {normalized.get('job_title')} @ {normalized.get('company_name')} "
                f"(Visa: {normalized.get('visa_feasibility')})"
            )

            # Save debug info
            debug_file = f"{DEBUG_DIR}/crawl4ai_{timestamp}.json"
            debug_payload = {
                "url": url,
                "success": result.success,
                "extracted_content": normalized,
                "markdown_length": len(result.markdown) if result.markdown else 0,
                "timestamp": timestamp,
            }
            with open(debug_file, "w", encoding="utf-8") as f:
                json.dump(debug_payload, f, ensure_ascii=False, indent=2)

            logger.info(f"[Crawl4AI] Debug saved → {debug_file}")

            extraction_strategy.show_usage()
            return normalized

    except (JobUnavailableError, VisaRestrictedError):
        # Re-raise these special exceptions so routes.py can handle them
        raise

    except Exception as e:
        logger.error(f"[Crawl4AI] ❌ Failed: {str(e)}")

        debug_file = f"{DEBUG_DIR}/crawl4ai_fail_{timestamp}.json"
        debug_payload = {
            "url": url,
            "error": str(e),
            "error_type": type(e).__name__,
            "timestamp": timestamp,
        }

        try:
            if "result" in locals() and result:
                debug_payload["result_success"] = result.success
                debug_payload["extracted_content_type"] = str(
                    type(result.extracted_content)
                )
                debug_payload["extracted_content_preview"] = str(
                    result.extracted_content
                )[:500]
        except Exception:
            pass

        with open(debug_file, "w", encoding="utf-8") as f:
            json.dump(debug_payload, f, ensure_ascii=False, indent=2)

        logger.info(f"[Crawl4AI] Debug saved → {debug_file}")
        raise Exception(f"Crawl4AI extraction failed: {str(e)}")


# Custom exceptions for better error handling
class JobUnavailableError(Exception):
    """Raised when job posting is no longer available"""

    pass


class VisaRestrictedError(Exception):
    """Raised when job has visa restrictions"""

    pass
