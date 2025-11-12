# # # services/scraper_service.py
# # from playwright.async_api import async_playwright
# # import logging

# # logger = logging.getLogger(__name__)


# # async def scrape_job(url: str) -> dict:
# #     """
# #     Scrapes a job posting URL and returns raw HTML + text content.

# #     Returns:
# #         dict with 'url', 'html', 'text', 'title'
# #     """
# #     logger.info(f"Scraping job URL: {url}")

# #     async with async_playwright() as p:
# #         browser = await p.chromium.launch(headless=True)
# #         page = await browser.new_page()

# #         try:
# #             # Navigate to the job page
# #             await page.goto(url, wait_until="domcontentloaded", timeout=15000)

# #             # Wait a bit for dynamic content to load
# #             await page.wait_for_timeout(2000)

# #             # Extract content
# #             html = await page.content()
# #             text = await page.inner_text("body")
# #             title = await page.title()

# #             logger.info(f"Successfully scraped: {title}")

# #             return {"url": url, "html": html, "text": text, "title": title}

# #         except Exception as e:
# #             logger.error(f"Failed to scrape {url}: {str(e)}")
# #             raise Exception(f"Scraping failed: {str(e)}")

# #         finally:
# #             await browser.close()


# # services/scraper_service.py

# from playwright.async_api import async_playwright, TimeoutError
# import logging, os, time, random
# from datetime import datetime

# logger = logging.getLogger(__name__)

# DEBUG_SCRAPE_DIR = "scrape_debug"
# os.makedirs(DEBUG_SCRAPE_DIR, exist_ok=True)


# async def _expand_page(page):
#     """Clicks buttons that reveal more text on job boards."""
#     selectors = [
#         "button:has-text('Show more')",
#         "button:has-text('See more')",
#         "button:has-text('Read more')",
#         "button:has-text('More')",
#         "button:has-text('Expand')",
#         "div[role='button']:has-text('Show more')",
#     ]

#     for selector in selectors:
#         try:
#             btns = page.locator(selector)
#             if await btns.count() > 0:
#                 await btns.first().click()
#                 await page.wait_for_timeout(500)
#                 logger.info(f"[Scraper] Clicked expand button: {selector}")
#                 break
#         except Exception:
#             pass


# async def _scroll_page(page):
#     """Scroll to bottom slowly to trigger lazy loading."""
#     for _ in range(5):
#         await page.evaluate("window.scrollBy(0, document.body.scrollHeight)")
#         await page.wait_for_timeout(600)


# async def playwright_scrape_job(url: str) -> dict:
#     logger.info(f"[Scraper] Starting scrape: {url}")

#     retries = 2
#     for attempt in range(retries):
#         try:
#             async with async_playwright() as p:
#                 browser = await p.chromium.launch(
#                     headless=True,
#                     args=["--disable-blink-features=AutomationControlled"],
#                 )
#                 context = await browser.new_context(
#                     user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 13_4) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117 Safari/537.36",
#                     viewport={"width": 1280, "height": 900},
#                 )
#                 page = await context.new_page()

#                 await page.goto(url, wait_until="networkidle", timeout=20000)

#                 # Scroll + Expand content
#                 await _scroll_page(page)
#                 await _expand_page(page)
#                 await _scroll_page(page)

#                 # Extract content
#                 html = await page.content()
#                 text = await page.inner_text("body")
#                 title = await page.title()

#                 # Debug output
#                 logger.info(f"[Scraper] ✅ Loaded page: {title}")
#                 logger.info(f"[Scraper] Extracted {len(text)} characters of text")

#                 return {
#                     "url": url,
#                     "html": html,
#                     "text": text,
#                     "title": title,
#                 }

#         except TimeoutError:
#             logger.warning(f"[Scraper] Timeout, retrying ({attempt+1}/{retries})...")
#             await page.wait_for_timeout(1500)

#         except Exception as e:
#             logger.error(f"[Scraper] Error: {str(e)}")

#             # Save failure artifacts
#             ts = datetime.now().strftime("%Y%m%d_%H%M%S")
#             screenshot = f"{DEBUG_SCRAPE_DIR}/fail_{ts}.png"
#             htmlfile = f"{DEBUG_SCRAPE_DIR}/fail_{ts}.html"

#             try:
#                 await page.screenshot(path=screenshot)
#                 with open(htmlfile, "w", encoding="utf-8") as f:
#                     f.write(await page.content())

#                 logger.error(f"[Scraper] Saved debug → {screenshot}, {htmlfile}")
#             except:
#                 pass

#             if attempt == retries - 1:
#                 raise Exception(f"Scraping failed: {str(e)}")

#     raise Exception("Final scrape attempt failed.")


# services/playwright_scraper_service.py
"""
Robust fallback scraper using Playwright
Now includes unavailable job detection
"""
from playwright.async_api import async_playwright, TimeoutError
import logging
import os
from datetime import datetime

logger = logging.getLogger(__name__)

DEBUG_SCRAPE_DIR = "scrape_debug"
os.makedirs(DEBUG_SCRAPE_DIR, exist_ok=True)


class JobUnavailableError(Exception):
    """Raised when job posting is no longer available"""

    pass


async def _expand_page(page):
    """Clicks buttons that reveal more text on job boards."""
    selectors = [
        "button:has-text('Show more')",
        "button:has-text('See more')",
        "button:has-text('Read more')",
        "button:has-text('More')",
        "button:has-text('Expand')",
        "div[role='button']:has-text('Show more')",
    ]

    for selector in selectors:
        try:
            btns = page.locator(selector)
            if await btns.count() > 0:
                await btns.first.click()
                await page.wait_for_timeout(500)
                logger.info(f"[Scraper] Clicked expand button: {selector}")
                break
        except Exception:
            pass


async def _scroll_page(page):
    """Scroll to bottom slowly to trigger lazy loading."""
    for _ in range(5):
        await page.evaluate("window.scrollBy(0, document.body.scrollHeight)")
        await page.wait_for_timeout(600)


def detect_unavailable_in_text(text: str, title: str) -> tuple[bool, str | None]:
    """
    Detect if scraped content indicates job is unavailable.
    Same logic as crawl4ai_service but for plain text.

    Returns: (is_unavailable, reason)
    """
    if not text or len(text.strip()) < 100:
        return True, "Page content too short or empty"

    text_lower = text.lower()
    title_lower = title.lower()

    # Check for unavailable patterns
    unavailable_patterns = [
        ("position has been filled", "Position already filled"),
        ("this job is no longer available", "Job posting closed"),
        ("posting has expired", "Posting expired"),
        ("job posting is no longer active", "Job no longer active"),
        ("position is no longer open", "Position closed"),
        ("this position has been closed", "Position closed"),
        (
            "sorry, this job is no longer accepting applications",
            "No longer accepting applications",
        ),
        ("this opportunity is no longer available", "Opportunity closed"),
        # Specific 404 patterns
        ("error 404", "Page not found (404)"),
        ("http 404", "Page not found (404)"),
        ("404 not found", "Page not found (404)"),
        ("404 error", "Page not found (404)"),
    ]

    for pattern, reason in unavailable_patterns:
        if pattern in text_lower or pattern in title_lower:
            # Extra validation for "404" patterns - check context
            if "404" in pattern:
                # Check if it appears early in content (likely header)
                if pattern in text_lower[:500]:
                    logger.warning(f"[Scraper] 🚫 Detected unavailable: {reason}")
                    return True, reason
                # Or if total content is very short
                elif len(text) < 500:
                    logger.warning(f"[Scraper] 🚫 Detected unavailable: {reason}")
                    return True, reason
                # Otherwise skip (likely false positive)
                else:
                    continue
            else:
                # Non-404 patterns - trigger immediately
                logger.warning(f"[Scraper] 🚫 Detected unavailable: {reason}")
                return True, reason

    # Validate actual job content exists
    job_indicators = [
        "responsibilities",
        "requirements",
        "qualifications",
        "about the role",
        "what you'll do",
        "job description",
        "apply now",
        "skills",
        "experience",
    ]

    has_job_content = any(indicator in text_lower for indicator in job_indicators)

    if not has_job_content and len(text) < 800:
        return True, "No job description found - possibly removed or expired"

    return False, None


async def playwright_scrape_job(url: str) -> dict:
    """
    Robust scraping with Playwright.

    Features:
    - Multiple retries with exponential backoff
    - Longer timeouts than Crawl4AI
    - Scroll and expand content
    - Early detection of unavailable jobs

    Raises:
    - JobUnavailableError: If job is no longer available
    - Exception: For other scraping failures
    """
    logger.info(f"[Scraper] Starting scrape: {url}")

    max_retries = 3
    base_timeout = 30000  # Start with 30s

    last_error = None

    for attempt in range(max_retries):
        timeout = base_timeout + (attempt * 10000)  # Increase timeout each retry

        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(
                    headless=True,
                    args=[
                        "--disable-blink-features=AutomationControlled",
                        "--disable-dev-shm-usage",  # Better for containerized environments
                    ],
                )
                context = await browser.new_context(
                    user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 13_4) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117 Safari/537.36",
                    viewport={"width": 1280, "height": 900},
                )
                page = await context.new_page()

                # Navigate with progressive timeout
                logger.info(
                    f"[Scraper] Attempt {attempt + 1}/{max_retries} (timeout: {timeout}ms)"
                )

                try:
                    response = await page.goto(
                        url, wait_until="networkidle", timeout=timeout
                    )

                    # Check HTTP status
                    if response and response.status >= 400:
                        if response.status == 404:
                            raise JobUnavailableError("HTTP 404 - Page not found")
                        elif response.status == 410:
                            raise JobUnavailableError("HTTP 410 - Page gone")
                        else:
                            logger.warning(
                                f"[Scraper] HTTP {response.status} - may retry"
                            )
                            raise Exception(f"HTTP {response.status}")

                except TimeoutError:
                    if attempt < max_retries - 1:
                        logger.warning(f"[Scraper] Navigation timeout, retrying...")
                        await page.wait_for_timeout(2000)
                        continue
                    else:
                        raise

                # Scroll + Expand content
                await _scroll_page(page)
                await _expand_page(page)
                await _scroll_page(page)

                # Extract content
                html = await page.content()
                text = await page.inner_text("body")
                title = await page.title()

                await browser.close()

                # Early detection of unavailable jobs
                is_unavailable, reason = detect_unavailable_in_text(text, title)
                if is_unavailable:
                    logger.warning(f"[Scraper] 🚫 Job unavailable: {reason}")
                    raise JobUnavailableError(reason)

                # Success!
                logger.info(f"[Scraper] ✅ Successfully scraped: {title}")
                logger.info(f"[Scraper] Extracted {len(text)} characters of text")

                return {
                    "url": url,
                    "html": html,
                    "text": text,
                    "title": title,
                }

        except JobUnavailableError:
            # Don't retry for unavailable jobs - bubble up immediately
            raise

        except TimeoutError as e:
            last_error = e
            logger.warning(f"[Scraper] Timeout on attempt {attempt + 1}/{max_retries}")
            if attempt < max_retries - 1:
                wait_time = 2000 + (attempt * 1000)  # Progressive backoff
                logger.info(f"[Scraper] Waiting {wait_time}ms before retry...")
                # Can't use page.wait_for_timeout here as page may be closed
                import asyncio

                await asyncio.sleep(wait_time / 1000)

        except Exception as e:
            last_error = e
            logger.error(f"[Scraper] Error on attempt {attempt + 1}: {str(e)}")

            # Save failure artifacts only on final attempt
            if attempt == max_retries - 1:
                ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                screenshot = f"{DEBUG_SCRAPE_DIR}/fail_{ts}.png"
                htmlfile = f"{DEBUG_SCRAPE_DIR}/fail_{ts}.html"

                try:
                    if "page" in locals():
                        await page.screenshot(path=screenshot)
                        with open(htmlfile, "w", encoding="utf-8") as f:
                            f.write(await page.content())
                        logger.error(
                            f"[Scraper] Saved debug → {screenshot}, {htmlfile}"
                        )
                except Exception as debug_error:
                    logger.warning(
                        f"[Scraper] Could not save debug files: {debug_error}"
                    )

            if attempt < max_retries - 1:
                logger.info(f"[Scraper] Retrying after error...")

            # Clean up browser before retry
            try:
                if "browser" in locals():
                    await browser.close()
            except:
                pass

    # All retries exhausted
    error_msg = f"Scraping failed after {max_retries} attempts: {str(last_error)}"
    logger.error(f"[Scraper] ❌ {error_msg}")
    raise Exception(error_msg)
