# app/routes.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, HttpUrl
from services.job_processor_service import extract_job_data
from services.llm_evaluation_service import evaluate_job_match
from services.notion_service import save_job_to_notion
import logging

logger = logging.getLogger(__name__)
router = APIRouter()


class JobURLInput(BaseModel):
    url: HttpUrl
    force_playwright: bool = False  # Optional: force fallback mode


@router.post("/jobs/add")
async def add_job(job_input: JobURLInput):
    """
    Complete pipeline:
    1. Extract job data (Crawl4AI → Playwright fallback)
    2. Evaluate match (with location/work_mode for smart visa warnings)
    3. Save to Notion
    """
    try:
        logger.info(f"Processing job: {job_input.url}")

        # ✅ Step 1: Extract & normalize (tries Crawl4AI first)
        normalized = await extract_job_data(
            str(job_input.url), force_playwright=job_input.force_playwright
        )

        logger.info(
            f"Extraction method used: {normalized.get('extraction_method', 'unknown')}"
        )

        # ✅ Step 2: Evaluate using normalized description + location/work_mode
        evaluation = await evaluate_job_match(
            normalized["job_description"],
            location=normalized.get("location"),
            work_mode=normalized.get("work_mode"),
        )

        # ✅ Step 3: Save to Notion using normalized data
        job_data = {
            "url": normalized["url"],
            "title": f"{normalized['job_title']} @ {normalized['company_name']}",
            "location": normalized.get("location"),
            "work_mode": normalized.get("work_mode"),
            "evaluation": evaluation,
        }

        notion_result = await save_job_to_notion(job_data)

        return {
            "status": "success",
            "message": "Job extracted, evaluated and saved",
            "extraction_method": normalized.get("extraction_method"),
            "extraction_time": normalized.get("extraction_time"),
            "performance": {
                "method": normalized.get("extraction_method"),
                "total_time": normalized.get("extraction_time"),
                "scrape_time": normalized.get("scrape_time"),  # Only for playwright
                "normalize_time": normalized.get(
                    "normalize_time"
                ),  # Only for playwright
            },
            "job_info": {
                "url": normalized["url"],
                "title": normalized["job_title"],
                "company": normalized["company_name"],
                "location": normalized.get("location"),
                "work_mode": normalized.get("work_mode"),
            },
            "evaluation": evaluation,
            "notion": notion_result,
        }

    except Exception as e:
        logger.error(f"Error processing job: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def health_check():
    """Quick health check endpoint"""
    return {
        "status": "healthy",
        "extractors": ["crawl4ai", "playwright+llm"],
    }
