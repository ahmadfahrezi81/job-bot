# services/job_processor_service.py
"""
Main orchestrator for job data extraction.
Tries fast Crawl4AI path first, falls back to Playwright + normalization.
"""
import logging
import time
from services.crawl4ai_service import crawl4ai_extract
from services.playwright_scraper_service import playwright_scrape_job
from services.llm_normalization_service import llm_normalize_job_data

logger = logging.getLogger(__name__)


async def extract_job_data(url: str, force_playwright: bool = False) -> dict:
    """
    Extract and normalize job data with automatic fallback.

    Strategy:
    1. Try Crawl4AI (fast, ~5-10s)
    2. On failure, use Playwright + LLM normalization (robust, ~30s)

    Args:
        url: Job posting URL
        force_playwright: Skip Crawl4AI and use Playwright directly

    Returns:
        Normalized job dict with keys:
        - url, job_title, company_name, location, work_mode,
          job_description, source_title
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

    except Exception as e:
        elapsed = time.time() - start_time
        logger.warning(f"[JobProcessor] Crawl4AI failed after {elapsed:.2f}s: {str(e)}")
        logger.info(f"[JobProcessor] 🔄 Falling back to Playwright path...")

        return await _playwright_path(url)


async def _playwright_path(url: str) -> dict:
    """Robust fallback: Playwright scraping + LLM normalization"""
    start_time = time.time()

    try:
        # Step 1: Scrape with Playwright
        scrape_start = time.time()
        raw_scraped = await playwright_scrape_job(url)
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

    except Exception as e:
        logger.error(f"[JobProcessor] ❌ Both paths failed for {url}")
        raise Exception(f"Job extraction failed on all paths: {str(e)}")
