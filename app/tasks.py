# app/tasks.py
from app.celery_app import celery_app
from services.job_processor_service import extract_job_data
from services.llm_evaluation_service import evaluate_job_match
from services.llm_resume_service import tailor_resume
from services.llm_cover_letter_service import tailor_cover_letter
from services.notion_service import save_job_to_notion
from services.duplicate_checker_service import check_if_job_exists
from services.crawl4ai_service import JobUnavailableError, VisaRestrictedError
from services.pdf_compilation_service import (
    compile_resume_to_pdf,
    compile_cover_letter_to_pdf,
)
from services.supabase_upload_service import upload_pdf_to_supabase
import logging
import asyncio

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, name="process_job")
def process_job_task(self, url: str, force_playwright: bool = False):
    """
    Celery task wrapper - runs the async pipeline in sync context
    """
    try:
        # Update task state to show we started
        self.update_state(state="PROCESSING", meta={"stage": "starting", "progress": 0})

        # Create new event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            result = loop.run_until_complete(
                process_job_pipeline(self, url, force_playwright)
            )
            return result
        finally:
            # Gracefully shutdown async generators and tasks
            try:
                # Cancel all remaining tasks
                pending = asyncio.all_tasks(loop)
                for task in pending:
                    task.cancel()

                # Wait for cancellation to complete
                loop.run_until_complete(
                    asyncio.gather(*pending, return_exceptions=True)
                )

                # Give async cleanup (like httpx) time to finish
                loop.run_until_complete(asyncio.sleep(0.1))

                # Shutdown async generators
                loop.run_until_complete(loop.shutdown_asyncgens())
            except Exception as cleanup_error:
                logger.warning(f"Cleanup warning: {cleanup_error}")
            finally:
                loop.close()

    except Exception as e:
        logger.error(f"Task failed for {url}: {str(e)}")
        raise


async def process_job_pipeline(task, url: str, force_playwright: bool):
    """
    Your existing pipeline logic, now with progress updates
    """
    logger.info(f"Processing job: {url}")

    # Stage 1: Duplicate check
    task.update_state(
        state="PROCESSING", meta={"stage": "duplicate_check", "progress": 10}
    )
    duplicate_check = await check_if_job_exists(url)

    if duplicate_check["exists"]:
        logger.info(f"Duplicate detected: {duplicate_check['message']}")
        return {
            "status": "duplicate",
            "message": duplicate_check.get("message", "Job already exists"),
            "notion_url": duplicate_check.get("notion_url"),
            "notion_page_id": duplicate_check.get("notion_page_id"),
            "job_title": duplicate_check.get("job_title"),
        }

    # Stage 2: Extract job data
    task.update_state(state="PROCESSING", meta={"stage": "extracting", "progress": 20})
    try:
        normalized = await extract_job_data(url, force_playwright=force_playwright)
    except JobUnavailableError as e:
        logger.warning(f"Job unavailable: {str(e)}")
        return {
            "status": "unavailable",
            "message": f"Job posting is no longer available: {str(e)}",
            "url": url,
            "reason": str(e),
        }
    except VisaRestrictedError as e:
        logger.warning(f"Visa restricted: {str(e)}")
        return {
            "status": "visa_restricted",
            "message": f"Job has visa restrictions: {str(e)}",
            "url": url,
            "reason": str(e),
        }

    logger.info(
        f"Extraction method used: {normalized.get('extraction_method', 'unknown')}"
    )

    # Stage 3: Evaluate
    task.update_state(state="PROCESSING", meta={"stage": "evaluating", "progress": 35})
    visa_warning = normalized.get("visa_warning")
    evaluation = await evaluate_job_match(
        normalized["job_description"], visa_warning=visa_warning
    )

    # Stage 4: Tailor resume + cover letter if match > 70
    resume_data = None
    cover_letter_data = None
    resume_pdf_url = None
    cover_letter_pdf_url = None
    match_score = evaluation.get("match_score", 0)

    if match_score > 70:
        logger.info(f"Match score {match_score}% > 70%, tailoring documents...")

        company = normalized.get("company_name", "company")
        job_title = normalized.get("job_title", "role")

        # Resume generation
        task.update_state(
            state="PROCESSING", meta={"stage": "tailoring_resume", "progress": 45}
        )
        try:
            resume_data = await tailor_resume(
                job_description=normalized["job_description"],
                evaluation=evaluation,
                job_title=job_title,
                company_name=company,
            )
            logger.info("Resume tailoring completed")

            # Compile & upload resume PDF
            task.update_state(
                state="PROCESSING",
                meta={"stage": "compiling_resume_pdf", "progress": 55},
            )
            try:
                logger.info("Compiling resume LaTeX to PDF...")
                resume_pdf_bytes = await compile_resume_to_pdf(
                    resume_data["tailored_content"]
                )
                logger.info(f"Resume PDF compiled ({len(resume_pdf_bytes)} bytes)")

                logger.info("Uploading resume PDF to Supabase...")
                resume_upload_result = await upload_pdf_to_supabase(
                    pdf_bytes=resume_pdf_bytes,
                    position=job_title,
                    company=company,
                    document_type="resume",
                )
                resume_pdf_url = resume_upload_result["public_url"]
                logger.info(f"Resume PDF uploaded: {resume_pdf_url}")

            except Exception as pdf_error:
                logger.error(f"Resume PDF compilation/upload failed: {str(pdf_error)}")

        except Exception as e:
            logger.error(f"Resume tailoring failed: {str(e)}")

        # Cover letter generation
        task.update_state(
            state="PROCESSING", meta={"stage": "tailoring_cover_letter", "progress": 65}
        )
        try:
            logger.info("Starting cover letter tailoring...")
            cover_letter_data = await tailor_cover_letter(
                job_description=normalized["job_description"],
                evaluation=evaluation,
                job_title=job_title,
                company_name=company,
            )
            logger.info("Cover letter tailoring completed")

            # Compile & upload cover letter PDF
            task.update_state(
                state="PROCESSING",
                meta={"stage": "compiling_cover_letter_pdf", "progress": 75},
            )
            try:
                logger.info("Compiling cover letter LaTeX to PDF...")
                cl_pdf_bytes = await compile_cover_letter_to_pdf(
                    cover_letter_data["tailored_content"]
                )
                logger.info(f"Cover letter PDF compiled ({len(cl_pdf_bytes)} bytes)")

                logger.info("Uploading cover letter PDF to Supabase...")
                cl_upload_result = await upload_pdf_to_supabase(
                    pdf_bytes=cl_pdf_bytes,
                    position=job_title,
                    company=company,
                    document_type="cover_letter",
                )
                cover_letter_pdf_url = cl_upload_result["public_url"]
                logger.info(f"Cover letter PDF uploaded: {cover_letter_pdf_url}")

            except Exception as pdf_error:
                logger.error(
                    f"Cover letter PDF compilation/upload failed: {str(pdf_error)}"
                )

        except Exception as e:
            logger.error(f"Cover letter tailoring failed: {str(e)}")

    else:
        logger.info(f"Match score {match_score}% ≤ 70, skipping document generation")

    # Stage 5: Save to Notion
    task.update_state(
        state="PROCESSING", meta={"stage": "saving_to_notion", "progress": 85}
    )
    job_data = {
        "url": normalized["url"],
        "title": f"{normalized['job_title']} @ {normalized['company_name']}",
        "location": normalized.get("location"),
        "work_mode": normalized.get("work_mode"),
        "evaluation": evaluation,
    }

    notion_result = await save_job_to_notion(
        job_data,
        resume_data=resume_data,
        pdf_url=resume_pdf_url,
        cover_letter_data=cover_letter_data,
        cover_letter_pdf_url=cover_letter_pdf_url,
    )

    # Build final response
    task.update_state(state="PROCESSING", meta={"stage": "complete", "progress": 100})

    response = {
        "status": "success",
        "message": "Job extracted, evaluated and saved",
        "extraction_method": normalized.get("extraction_method"),
        "extraction_time": normalized.get("extraction_time"),
        "performance": {
            "method": normalized.get("extraction_method"),
            "total_time": normalized.get("extraction_time"),
            "scrape_time": normalized.get("scrape_time"),
            "normalize_time": normalized.get("normalize_time"),
        },
        "job_info": {
            "url": normalized["url"],
            "title": normalized["job_title"],
            "company": normalized["company_name"],
            "location": normalized.get("location"),
            "work_mode": normalized.get("work_mode"),
            "visa_feasibility": normalized.get("visa_feasibility"),
        },
        "evaluation": evaluation,
        "notion": notion_result,
    }

    # Add resume info
    if resume_data:
        response["resume_tailored"] = True
        response["resume_pdf_generated"] = resume_pdf_url is not None
        response["resume_pdf_url"] = resume_pdf_url
        response["resume_preview"] = {
            "pruning_strategy_preview": resume_data.get("pruning_strategy", {}).get(
                "summary", ""
            )[:200]
            + "...",
            "content_length": len(resume_data.get("tailored_content", "")),
        }
    else:
        response["resume_tailored"] = False
        response["resume_pdf_generated"] = False
        response["resume_reason"] = f"Match score {match_score}% ≤ 70 threshold"

    # Add cover letter info
    if cover_letter_data:
        response["cover_letter_tailored"] = True
        response["cover_letter_pdf_generated"] = cover_letter_pdf_url is not None
        response["cover_letter_pdf_url"] = cover_letter_pdf_url
        response["cover_letter_preview"] = {
            "writing_strategy_preview": cover_letter_data.get(
                "writing_strategy", {}
            ).get("summary", "")[:200]
            + "...",
            "word_count": cover_letter_data.get("change_summary", {}).get(
                "word_count", "unknown"
            ),
            "content_length": len(cover_letter_data.get("tailored_content", "")),
        }
    else:
        response["cover_letter_tailored"] = False
        response["cover_letter_pdf_generated"] = False
        response["cover_letter_reason"] = f"Match score {match_score}% ≤ 70 threshold"

    return response
