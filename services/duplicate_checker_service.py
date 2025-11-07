import os
import httpx
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

NOTION_API_KEY = os.getenv("NOTION_API_KEY")
NOTION_DATABASE_ID = os.getenv("NOTION_DATABASE_ID")

NOTION_URL = f"https://api.notion.com/v1/databases/{NOTION_DATABASE_ID}/query"
NOTION_VERSION = "2022-06-28"


async def check_if_job_exists(job_url: str):
    """
    Check if a given job URL already exists in the Notion database.
    Uses direct async HTTP calls instead of the Notion SDK for reliability.
    """
    headers = {
        "Authorization": f"Bearer {NOTION_API_KEY}",
        "Content-Type": "application/json",
        "Notion-Version": NOTION_VERSION,
    }

    payload = {
        "filter": {"property": "Job Posting", "url": {"equals": job_url}},
        "page_size": 1,
    }

    logger.info(f"🔍 Checking if job exists: {job_url}")

    if not NOTION_API_KEY or not NOTION_DATABASE_ID:
        error_msg = (
            "❌ Missing NOTION_API_KEY or NOTION_DATABASE_ID environment variable."
        )
        logger.error(error_msg)
        return {"exists": False, "error": error_msg}

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(NOTION_URL, headers=headers, json=payload)
            logger.info(f"📡 Notion responded with status {response.status_code}")

            if response.status_code == 200:
                data = response.json()
                results = data.get("results", [])
                exists = len(results) > 0

                if exists:
                    # Extract info from the existing page
                    page = results[0]
                    properties = page.get("properties", {})

                    # Extract job title
                    position_prop = properties.get("Position", {})
                    job_title = "Unknown Position"
                    if position_prop.get("type") == "title":
                        title_content = position_prop.get("title", [])
                        if title_content and len(title_content) > 0:
                            job_title = (
                                title_content[0]
                                .get("text", {})
                                .get("content", "Unknown Position")
                            )

                    # Extract company name
                    company_prop = properties.get("Company", {})
                    company_name = ""
                    if company_prop.get("type") == "rich_text":
                        company_content = company_prop.get("rich_text", [])
                        if company_content and len(company_content) > 0:
                            company_name = (
                                company_content[0].get("text", {}).get("content", "")
                            )

                    full_title = (
                        f"{job_title} @ {company_name}" if company_name else job_title
                    )

                    logger.info(f"✅ Job exists in Notion: {full_title}")

                    return {
                        "exists": True,
                        "message": f"Job already exists: {full_title}",
                        "notion_url": page.get("url"),
                        "notion_page_id": page.get("id"),
                        "job_title": full_title,
                    }
                else:
                    logger.info("✅ Job does not exist in Notion.")
                    return {"exists": False, "message": "Job URL is new"}
            else:
                logger.error(f"❌ Notion API error: {response.text}")
                return {"exists": False, "error": response.text}

    except httpx.RequestError as e:
        logger.error(f"❌ Request error when checking Notion: {e}")
        return {"exists": False, "error": str(e)}

    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}")
        return {"exists": False, "error": str(e)}
