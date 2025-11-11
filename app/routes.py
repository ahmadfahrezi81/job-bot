# app/routes.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, HttpUrl
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

logger = logging.getLogger(__name__)
router = APIRouter()


class JobURLInput(BaseModel):
    url: HttpUrl
    force_playwright: bool = False  # Optional: force fallback mode


@router.post("/jobs/add")
async def add_job(job_input: JobURLInput):
    """
    Complete pipeline:
    0. Check if URL already exists in Notion
    1. Extract job data (Crawl4AI → Playwright fallback)
        - Early exit if job unavailable
        - Early exit if visa restricted
    2. Evaluate match (visa_warning passed from extraction)
    3. If match_score > 70:
        a. Tailor resume
        b. Compile resume PDF and upload to Supabase
        c. Tailor cover letter
        d. Compile cover letter PDF and upload to Supabase
    4. Save to Notion (with resume + cover letter data + PDF URLs if applicable)
    """
    try:
        logger.info(f"Processing job: {job_input.url}")

        # ✅ Step 0: Check for duplicates FIRST
        duplicate_check = await check_if_job_exists(str(job_input.url))

        if duplicate_check["exists"]:
            logger.info(f"Duplicate detected: {duplicate_check['message']}")
            return {
                "status": "duplicate",
                "message": duplicate_check.get("message", "Job already exists"),
                "notion_url": duplicate_check.get("notion_url"),
                "notion_page_id": duplicate_check.get("notion_page_id"),
                "job_title": duplicate_check.get("job_title"),
            }

        # ✅ Step 1: Extract & normalize (tries Crawl4AI first)
        try:
            normalized = await extract_job_data(
                str(job_input.url), force_playwright=job_input.force_playwright
            )
        except JobUnavailableError as e:
            # Job is no longer available - stop processing
            logger.warning(f"🚫 Job unavailable: {str(e)}")
            return {
                "status": "unavailable",
                "message": f"Job posting is no longer available: {str(e)}",
                "url": str(job_input.url),
                "reason": str(e),
            }
        except VisaRestrictedError as e:
            # Visa restricted - stop processing
            logger.warning(f"🚫 Visa restricted: {str(e)}")
            return {
                "status": "visa_restricted",
                "message": f"Job has visa restrictions: {str(e)}",
                "url": str(job_input.url),
                "reason": str(e),
            }

        logger.info(
            f"Extraction method used: {normalized.get('extraction_method', 'unknown')}"
        )

        # ✅ Step 2: Evaluate using normalized description
        # Pass visa_warning from extraction if available
        visa_warning = normalized.get("visa_warning")
        evaluation = await evaluate_job_match(
            normalized["job_description"], visa_warning=visa_warning
        )

        # ✅ Step 3: Tailor resume + cover letter if match score > 70
        resume_data = None
        cover_letter_data = None
        resume_pdf_url = None
        cover_letter_pdf_url = None
        match_score = evaluation.get("match_score", 0)

        if match_score > 70:
            logger.info(
                f"🎯 Match score {match_score}% > 70%, triggering resume + cover letter tailoring..."
            )

            company = normalized.get("company_name", "company")
            job_title = normalized.get("job_title", "role")

            # --- RESUME GENERATION (Step 3a & 3b) ---
            try:
                # Tailor resume
                resume_data = await tailor_resume(
                    job_description=normalized["job_description"],
                    evaluation=evaluation,
                    job_title=job_title,
                    company_name=company,
                )
                logger.info("✅ Resume tailoring completed")

                # Compile resume PDF
                try:
                    logger.info("📄 Compiling resume LaTeX to PDF...")
                    resume_pdf_bytes = await compile_resume_to_pdf(
                        resume_data["tailored_content"]
                    )
                    logger.info(
                        f"✅ Resume PDF compiled ({len(resume_pdf_bytes)} bytes)"
                    )

                    # Upload resume to Supabase
                    logger.info("☁️ Uploading resume PDF to Supabase...")
                    resume_upload_result = await upload_pdf_to_supabase(
                        pdf_bytes=resume_pdf_bytes,
                        position=job_title,
                        company=company,
                        document_type="resume",  # Specify document type
                    )
                    resume_pdf_url = resume_upload_result["public_url"]
                    logger.info(f"✅ Resume PDF uploaded: {resume_pdf_url}")

                except Exception as pdf_error:
                    logger.error(
                        f"⚠️ Resume PDF compilation/upload failed: {str(pdf_error)}"
                    )
                    # Continue without resume PDF - don't fail the whole pipeline

            except Exception as e:
                logger.error(f"⚠️ Resume tailoring failed (continuing anyway): {str(e)}")

            # --- COVER LETTER GENERATION (Step 3c & 3d) ---
            try:
                # Tailor cover letter
                logger.info("✍️ Starting cover letter tailoring...")
                cover_letter_data = await tailor_cover_letter(
                    job_description=normalized["job_description"],
                    evaluation=evaluation,
                    job_title=job_title,
                    company_name=company,
                )
                logger.info("✅ Cover letter tailoring completed")

                # Compile cover letter PDF
                try:
                    logger.info("📄 Compiling cover letter LaTeX to PDF...")
                    cl_pdf_bytes = await compile_cover_letter_to_pdf(
                        cover_letter_data["tailored_content"]
                    )
                    logger.info(
                        f"✅ Cover letter PDF compiled ({len(cl_pdf_bytes)} bytes)"
                    )

                    # Upload cover letter to Supabase
                    logger.info("☁️ Uploading cover letter PDF to Supabase...")
                    cl_upload_result = await upload_pdf_to_supabase(
                        pdf_bytes=cl_pdf_bytes,
                        position=job_title,
                        company=company,
                        document_type="cover_letter",  # Specify document type
                    )
                    cover_letter_pdf_url = cl_upload_result["public_url"]
                    logger.info(f"✅ Cover letter PDF uploaded: {cover_letter_pdf_url}")

                except Exception as pdf_error:
                    logger.error(
                        f"⚠️ Cover letter PDF compilation/upload failed: {str(pdf_error)}"
                    )
                    # Continue without cover letter PDF

            except Exception as e:
                logger.error(
                    f"⚠️ Cover letter tailoring failed (continuing anyway): {str(e)}"
                )

        else:
            logger.info(
                f"⭐️ Match score {match_score}% ≤ 70, skipping document generation"
            )

        # ✅ Step 4: Save to Notion using normalized data + resume + cover letter data + PDF URLs
        job_data = {
            "url": normalized["url"],
            "title": f"{normalized['job_title']} @ {normalized['company_name']}",
            "location": normalized.get("location"),
            "work_mode": normalized.get("work_mode"),
            "evaluation": evaluation,
        }

        # ✅ Save to Notion with both resume and cover letter data
        notion_result = await save_job_to_notion(
            job_data,
            resume_data=resume_data,
            pdf_url=resume_pdf_url,
            cover_letter_data=cover_letter_data,
            cover_letter_pdf_url=cover_letter_pdf_url,
        )

        # Build response
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

        # Add resume info if it was generated
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

        # Add cover letter info if it was generated
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
            response["cover_letter_reason"] = (
                f"Match score {match_score}% ≤ 70 threshold"
            )

        return response

    except Exception as e:
        logger.error(f"Error processing job: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def health_check():
    """Quick health check endpoint"""
    return {
        "status": "healthy",
        "extractors": ["crawl4ai", "playwright+llm"],
        "duplicate_check": "enabled",
        "smart_filters": ["job_unavailable", "visa_restricted"],
        "resume_tailoring": "enabled (match_score > 70)",
        "cover_letter_tailoring": "enabled (match_score > 70)",
        "pdf_compilation": "enabled",
        "supabase_upload": "enabled",
    }
