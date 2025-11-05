# # services/scraper_service.py
# from playwright.async_api import async_playwright
# import logging

# logger = logging.getLogger(__name__)


# async def scrape_job(url: str) -> dict:
#     """
#     Scrapes a job posting URL and returns raw HTML + text content.

#     Returns:
#         dict with 'url', 'html', 'text', 'title'
#     """
#     logger.info(f"Scraping job URL: {url}")

#     async with async_playwright() as p:
#         browser = await p.chromium.launch(headless=True)
#         page = await browser.new_page()

#         try:
#             # Navigate to the job page
#             await page.goto(url, wait_until="domcontentloaded", timeout=15000)

#             # Wait a bit for dynamic content to load
#             await page.wait_for_timeout(2000)

#             # Extract content
#             html = await page.content()
#             text = await page.inner_text("body")
#             title = await page.title()

#             logger.info(f"Successfully scraped: {title}")

#             return {"url": url, "html": html, "text": text, "title": title}

#         except Exception as e:
#             logger.error(f"Failed to scrape {url}: {str(e)}")
#             raise Exception(f"Scraping failed: {str(e)}")

#         finally:
#             await browser.close()


# services/scraper_service.py

from playwright.async_api import async_playwright, TimeoutError
import logging, os, time, random
from datetime import datetime

logger = logging.getLogger(__name__)

DEBUG_SCRAPE_DIR = "scrape_debug"
os.makedirs(DEBUG_SCRAPE_DIR, exist_ok=True)


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
                await btns.first().click()
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


async def playwright_scrape_job(url: str) -> dict:
    logger.info(f"[Scraper] Starting scrape: {url}")

    retries = 2
    for attempt in range(retries):
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(
                    headless=True,
                    args=["--disable-blink-features=AutomationControlled"],
                )
                context = await browser.new_context(
                    user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 13_4) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117 Safari/537.36",
                    viewport={"width": 1280, "height": 900},
                )
                page = await context.new_page()

                await page.goto(url, wait_until="networkidle", timeout=20000)

                # Scroll + Expand content
                await _scroll_page(page)
                await _expand_page(page)
                await _scroll_page(page)

                # Extract content
                html = await page.content()
                text = await page.inner_text("body")
                title = await page.title()

                # Debug output
                logger.info(f"[Scraper] ✅ Loaded page: {title}")
                logger.info(f"[Scraper] Extracted {len(text)} characters of text")

                return {
                    "url": url,
                    "html": html,
                    "text": text,
                    "title": title,
                }

        except TimeoutError:
            logger.warning(f"[Scraper] Timeout, retrying ({attempt+1}/{retries})...")
            await page.wait_for_timeout(1500)

        except Exception as e:
            logger.error(f"[Scraper] Error: {str(e)}")

            # Save failure artifacts
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            screenshot = f"{DEBUG_SCRAPE_DIR}/fail_{ts}.png"
            htmlfile = f"{DEBUG_SCRAPE_DIR}/fail_{ts}.html"

            try:
                await page.screenshot(path=screenshot)
                with open(htmlfile, "w", encoding="utf-8") as f:
                    f.write(await page.content())

                logger.error(f"[Scraper] Saved debug → {screenshot}, {htmlfile}")
            except:
                pass

            if attempt == retries - 1:
                raise Exception(f"Scraping failed: {str(e)}")

    raise Exception("Final scrape attempt failed.")
