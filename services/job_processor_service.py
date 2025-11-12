# # services/job_processor_service.py
# """
# Main orchestrator for job data extraction.
# Tries fast Crawl4AI path first, falls back to Playwright + normalization.
# """
# import logging
# import time
# from services.crawl4ai_service import (
#     crawl4ai_extract,
#     JobUnavailableError,
#     VisaRestrictedError,
# )
# from services.playwright_scraper_service import playwright_scrape_job
# from services.llm_normalization_service import llm_normalize_job_data

# logger = logging.getLogger(__name__)


# async def extract_job_data(url: str, force_playwright: bool = False) -> dict:
#     """
#     Extract and normalize job data with automatic fallback.

#     Strategy:
#     1. Try Crawl4AI (fast, ~5-10s)
#     2. On failure, use Playwright + LLM normalization (robust, ~30s)

#     Special exceptions that prevent fallback:
#     - JobUnavailableError: Job posting no longer exists
#     - VisaRestrictedError: Job has visa restrictions

#     Args:
#         url: Job posting URL
#         force_playwright: Skip Crawl4AI and use Playwright directly

#     Returns:
#         Normalized job dict with keys:
#         - url, job_title, company_name, location, work_mode,
#           job_description, source_title

#     Raises:
#         JobUnavailableError: When job posting is closed/filled
#         VisaRestrictedError: When job has visa restrictions
#     """

#     # Optional: Force Playwright for testing or known problematic sites
#     if force_playwright:
#         logger.info(f"[JobProcessor] 🔧 Forced Playwright mode for {url}")
#         return await _playwright_path(url)

#     # Try fast path first
#     start_time = time.time()
#     try:
#         logger.info(f"[JobProcessor] ⚡ Attempting Crawl4AI fast path...")
#         normalized = await crawl4ai_extract(url)

#         # Validate we got meaningful data
#         if not normalized.get("job_title") or not normalized.get("job_description"):
#             raise Exception("Incomplete extraction - missing critical fields")

#         elapsed = time.time() - start_time
#         logger.info(
#             f"[JobProcessor] ✅ Crawl4AI succeeded in {elapsed:.2f}s "
#             f"({len(normalized.get('job_description', ''))} chars)"
#         )
#         normalized["extraction_method"] = "crawl4ai"
#         normalized["extraction_time"] = round(elapsed, 2)
#         return normalized

#     except (JobUnavailableError, VisaRestrictedError) as e:
#         # ✅ DO NOT FALLBACK - these are intentional stops
#         elapsed = time.time() - start_time
#         logger.warning(
#             f"[JobProcessor] 🚫 Stopping processing after {elapsed:.2f}s: {str(e)}"
#         )
#         logger.info(f"[JobProcessor] ⛔ No fallback - job should not be processed")
#         # Re-raise to bubble up to routes.py
#         raise

#     except Exception as e:
#         # ✅ Only fallback for technical failures, not business logic stops
#         elapsed = time.time() - start_time
#         logger.warning(f"[JobProcessor] Crawl4AI failed after {elapsed:.2f}s: {str(e)}")
#         logger.info(f"[JobProcessor] 🔄 Falling back to Playwright path...")

#         return await _playwright_path(url)


# async def _playwright_path(url: str) -> dict:
#     """Robust fallback: Playwright scraping + LLM normalization"""
#     start_time = time.time()

#     try:
#         # Step 1: Scrape with Playwright
#         scrape_start = time.time()
#         raw_scraped = await playwright_scrape_job(url)
#         scrape_time = time.time() - scrape_start

#         # Step 2: Normalize with LLM
#         normalize_start = time.time()
#         normalized = await llm_normalize_job_data(raw_scraped)
#         normalize_time = time.time() - normalize_start

#         total_time = time.time() - start_time

#         logger.info(
#             f"[JobProcessor] ✅ Playwright path succeeded in {total_time:.2f}s "
#             f"(scrape: {scrape_time:.2f}s, normalize: {normalize_time:.2f}s) - "
#             f"{normalized.get('job_title')} @ {normalized.get('company_name')}"
#         )

#         normalized["extraction_method"] = "playwright+llm"
#         normalized["extraction_time"] = round(total_time, 2)
#         normalized["scrape_time"] = round(scrape_time, 2)
#         normalized["normalize_time"] = round(normalize_time, 2)
#         return normalized

#     except Exception as e:
#         logger.error(f"[JobProcessor] ❌ Both paths failed for {url}")
#         raise Exception(f"Job extraction failed on all paths: {str(e)}")


# services/job_processor_service.py
"""
Main orchestrator for job data extraction.
Tries fast Crawl4AI path first, falls back to Playwright + normalization.

Improvements:
- Smarter fallback logic (only for technical failures)
- Better error classification
- Playwright now also detects unavailable jobs early
"""
import logging
import time
from services.crawl4ai_service import (
    crawl4ai_extract,
    JobUnavailableError,
    VisaRestrictedError,
)
from services.playwright_scraper_service import (
    playwright_scrape_job,
    JobUnavailableError as PlaywrightJobUnavailableError,
)
from services.llm_normalization_service import llm_normalize_job_data

logger = logging.getLogger(__name__)


async def extract_job_data(url: str, force_playwright: bool = False) -> dict:
    """
    Extract and normalize job data with intelligent fallback.

    Strategy:
    1. Try Crawl4AI (fast, ~5-10s) with smart detection
    2. On technical failure (not business logic), fallback to Playwright + LLM (~30-40s)
    3. Playwright also validates job availability before LLM normalization

    Business logic stops (no fallback):
    - JobUnavailableError: Job posting closed/filled/404
    - VisaRestrictedError: Job has visa sponsorship restrictions

    Technical failures (triggers fallback):
    - Timeout errors
    - Network errors
    - Parsing failures
    - Missing content errors

    Args:
        url: Job posting URL
        force_playwright: Skip Crawl4AI and use Playwright directly

    Returns:
        Normalized job dict with keys:
        - url, job_title, company_name, location, work_mode,
          job_description, extraction_method, extraction_time

    Raises:
        JobUnavailableError: When job posting is closed/filled
        VisaRestrictedError: When job has visa restrictions
        Exception: When all extraction methods fail
    """

    # Optional: Force Playwright for testing or known problematic sites
    if force_playwright:
        logger.info(f"[JobProcessor] 🔧 Forced Playwright mode for {url}")
        return await _playwright_path(url)

    # Try fast path first
    start_time = time.time()
    try:
        logger.info(f"[JobProcessor] ⚡ Attempting Crawl4AI fast path...")
        normalized = await crawl4ai_extract(url)

        # Validate we got meaningful data
        if not normalized.get("job_title") or not normalized.get("job_description"):
            raise Exception("Incomplete extraction - missing critical fields")

        elapsed = time.time() - start_time
        logger.info(
            f"[JobProcessor] ✅ Crawl4AI succeeded in {elapsed:.2f}s "
            f"({len(normalized.get('job_description', ''))} chars)"
        )
        normalized["extraction_method"] = "crawl4ai"
        normalized["extraction_time"] = round(elapsed, 2)
        return normalized

    except (JobUnavailableError, VisaRestrictedError) as e:
        # ✅ DO NOT FALLBACK - these are business logic stops, not technical failures
        elapsed = time.time() - start_time
        logger.warning(
            f"[JobProcessor] 🚫 Stopping processing after {elapsed:.2f}s: {str(e)}"
        )
        logger.info(f"[JobProcessor] ⛔ No fallback - job should not be processed")
        # Re-raise to bubble up to tasks.py
        raise

    except Exception as e:
        # ✅ Technical failure - attempt fallback
        elapsed = time.time() - start_time
        error_type = type(e).__name__

        # Log detailed failure info
        logger.warning(
            f"[JobProcessor] Crawl4AI failed after {elapsed:.2f}s "
            f"({error_type}: {str(e)[:100]})"
        )

        # Determine if we should fallback based on error type
        should_fallback = _should_attempt_fallback(e)

        if should_fallback:
            logger.info(f"[JobProcessor] 🔄 Falling back to Playwright path...")
            return await _playwright_path(url)
        else:
            logger.error(f"[JobProcessor] ❌ Non-recoverable error, not falling back")
            raise


def _should_attempt_fallback(error: Exception) -> bool:
    """
    Determine if we should fallback to Playwright based on error type.

    Fallback for:
    - Timeout errors
    - Network/connection errors
    - Parsing/extraction errors
    - Content validation failures

    Don't fallback for:
    - Explicit business logic errors (already handled above)
    - Resource exhaustion errors
    - Configuration errors
    """
    error_str = str(error).lower()
    error_type = type(error).__name__

    # Patterns that suggest a fallback might help
    fallback_patterns = [
        "timeout",
        "timed out",
        "connection",
        "network",
        "incomplete extraction",
        "missing required fields",
        "no content extracted",
        "empty",
        "failed on navigating",
    ]

    # Check if error message contains any fallback-worthy patterns
    if any(pattern in error_str for pattern in fallback_patterns):
        return True

    # Check error types that are worth retrying
    retriable_errors = [
        "TimeoutError",
        "NetworkError",
        "ConnectionError",
        "RuntimeError",  # Crawl4AI often wraps navigation errors in RuntimeError
    ]

    if error_type in retriable_errors:
        return True

    # Default: don't fallback for unknown errors (fail fast)
    logger.warning(
        f"[JobProcessor] Unknown error type '{error_type}' - not falling back"
    )
    return False


async def _playwright_path(url: str) -> dict:
    """
    Robust fallback: Playwright scraping + LLM normalization.

    Now includes early job availability detection before normalization.
    """
    start_time = time.time()

    try:
        # Step 1: Scrape with Playwright (now includes unavailable detection)
        scrape_start = time.time()
        try:
            raw_scraped = await playwright_scrape_job(url)
        except PlaywrightJobUnavailableError as e:
            # Playwright detected unavailable job - convert to our exception type
            logger.warning(
                f"[JobProcessor] 🚫 Playwright detected unavailable: {str(e)}"
            )
            raise JobUnavailableError(str(e))

        scrape_time = time.time() - scrape_start

        # Step 2: Normalize with LLM
        normalize_start = time.time()
        normalized = await llm_normalize_job_data(raw_scraped)
        normalize_time = time.time() - normalize_start

        total_time = time.time() - start_time

        logger.info(
            f"[JobProcessor] ✅ Playwright path succeeded in {total_time:.2f}s "
            f"(scrape: {scrape_time:.2f}s, normalize: {normalize_time:.2f}s) - "
            f"{normalized.get('job_title')} @ {normalized.get('company_name')}"
        )

        normalized["extraction_method"] = "playwright+llm"
        normalized["extraction_time"] = round(total_time, 2)
        normalized["scrape_time"] = round(scrape_time, 2)
        normalized["normalize_time"] = round(normalize_time, 2)
        return normalized

    except JobUnavailableError:
        # Re-raise without wrapping
        raise

    except Exception as e:
        logger.error(f"[JobProcessor] ❌ Playwright path failed for {url}")
        raise Exception(f"Playwright extraction failed: {str(e)}")
