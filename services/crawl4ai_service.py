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


async def crawl4ai_extract(url: str) -> dict:
    """
    Extract normalized job data using Crawl4AI + LLM strategy.

    Returns normalized job dict or raises exception on failure.
    """
    logger.info(f"[Crawl4AI] Starting extraction: {url}")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    try:
        # More specific extraction instructions
        extraction_prompt = """
        You are extracting job posting data from a webpage.
        
        CRITICAL: You MUST find and extract the job information. Look for:
        - Job title (e.g., "Software Engineer", "Product Manager")
        - Company name
        - Location information (city, country, or "Remote")
        - Full job description including responsibilities, requirements, benefits
        
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
            llm_config=llm_config,  # ✅ Use llm_config parameter
            schema=NormalizedJob.model_json_schema(),
            extraction_type="schema",
            instruction=extraction_prompt,
            chunk_token_threshold=4000,  # Handle larger content
            apply_chunking=True,
            input_format="markdown",  # Use markdown for cleaner extraction
            extra_args={"temperature": 0, "max_tokens": 2000},
        )

        # ✅ Use CrawlerRunConfig as per docs
        crawl_config = CrawlerRunConfig(
            extraction_strategy=extraction_strategy,
            cache_mode=CacheMode.BYPASS,  # Always fresh for job posts
            word_count_threshold=10,
            # Add wait time for dynamic content
            wait_for="body",
            delay_before_return_html=2.0,  # Wait 2s for content to load
        )

        browser_config = BrowserConfig(headless=True, verbose=True)

        async with AsyncWebCrawler(config=browser_config, verbose=True) as crawler:
            result = await crawler.arun(url=url, config=crawl_config)

            if not result.success:
                raise Exception(f"Crawl failed: {result.error_message}")

            # Debug: Save the raw markdown to see what LLM is seeing
            markdown_debug = f"{DEBUG_DIR}/markdown_{timestamp}.md"
            with open(markdown_debug, "w", encoding="utf-8") as f:
                f.write(result.markdown or "NO MARKDOWN")
            logger.info(f"[Crawl4AI] Saved markdown → {markdown_debug}")

            # Parse extracted content
            extracted = result.extracted_content

            if not extracted:
                raise Exception("No content extracted")

            # Debug: Log what we got
            logger.debug(f"[Crawl4AI] Raw extracted type: {type(extracted)}")
            logger.debug(f"[Crawl4AI] Raw extracted preview: {str(extracted)[:200]}")

            # Parse JSON response from LLM
            if isinstance(extracted, str):
                parsed = json.loads(extracted)
            else:
                parsed = extracted  # Already parsed

            logger.debug(f"[Crawl4AI] Parsed type: {type(parsed)}")

            # Handle if LLM returns array instead of object
            if isinstance(parsed, list):
                if len(parsed) == 0:
                    # LLM returned empty - might be content issue
                    raise Exception(
                        f"LLM returned empty array. "
                        f"Markdown had {len(result.markdown or '')} chars. "
                        f"Check {markdown_debug} to see what LLM received."
                    )
                normalized = parsed[0]  # Take first item
                logger.warning("[Crawl4AI] LLM returned array, using first item")
            elif isinstance(parsed, dict):
                normalized = parsed
            else:
                raise Exception(f"Unexpected parsed type: {type(parsed)}")

            # Validate we have a dict now
            if not isinstance(normalized, dict):
                raise Exception(f"Normalized is not a dict: {type(normalized)}")

            # Ensure required fields exist
            if not normalized.get("job_title") or not normalized.get("job_description"):
                raise Exception(
                    f"Missing required fields. Got: {list(normalized.keys())}"
                )

            # Add metadata
            normalized["url"] = url
            normalized["source_title"] = result.metadata.get("title", "")

            logger.info(
                f"[Crawl4AI] ✅ Extracted: {normalized.get('job_title')} @ {normalized.get('company_name')}"
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

            # Optional: Show token usage
            extraction_strategy.show_usage()

            return normalized

    except Exception as e:
        logger.error(f"[Crawl4AI] ❌ Failed: {str(e)}")

        # Save failure debug with more context
        debug_file = f"{DEBUG_DIR}/crawl4ai_fail_{timestamp}.json"

        # Try to capture what we got before failing
        debug_payload = {
            "url": url,
            "error": str(e),
            "error_type": type(e).__name__,
            "timestamp": timestamp,
        }

        # Try to add extracted content if available
        try:
            if "result" in locals() and result:
                debug_payload["result_success"] = result.success
                debug_payload["extracted_content_type"] = str(
                    type(result.extracted_content)
                )
                debug_payload["extracted_content_preview"] = str(
                    result.extracted_content
                )[:500]
        except:
            pass

        with open(debug_file, "w", encoding="utf-8") as f:
            json.dump(debug_payload, f, ensure_ascii=False, indent=2)

        logger.info(f"[Crawl4AI] Debug saved → {debug_file}")

        raise Exception(f"Crawl4AI extraction failed: {str(e)}")
