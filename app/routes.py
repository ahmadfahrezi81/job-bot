# app/routes.py
from typing import List
import time
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, HttpUrl
from app.tasks import process_job_task
from celery.result import AsyncResult
import logging

logger = logging.getLogger(__name__)
router = APIRouter()


class JobURLInput(BaseModel):
    url: HttpUrl
    force_playwright: bool = False


class JobBatchInput(BaseModel):
    urls: List[HttpUrl]
    force_playwright: bool = False


@router.post("/jobs/add")
async def add_job(job_input: JobURLInput):
    """
    Submit a job for async processing
    Returns immediately with job_id
    """
    try:
        logger.info(f"Queueing job: {job_input.url}")

        # Queue the task
        task = process_job_task.apply_async(
            args=[str(job_input.url), job_input.force_playwright]
        )

        return {
            "status": "queued",
            "job_id": task.id,
            "message": "Job queued for processing",
            "url": str(job_input.url),
            "check_status_url": f"/jobs/{task.id}/status",
        }

    except Exception as e:
        logger.error(f"Error queueing job: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/jobs/{job_id}/status")
async def get_job_status(job_id: str):
    """
    Check status of a queued/processing job
    """
    try:
        task_result = AsyncResult(job_id)

        if task_result.state == "PENDING":
            return {
                "job_id": job_id,
                "status": "pending",
                "message": "Job is waiting in queue",
                "progress": 0,
            }

        elif task_result.state == "PROCESSING":
            # Get custom metadata from task
            info = task_result.info or {}
            return {
                "job_id": job_id,
                "status": "processing",
                "stage": info.get("stage", "unknown"),
                "progress": info.get("progress", 0),
                "message": f"Currently: {info.get('stage', 'processing')}",
            }

        elif task_result.state == "SUCCESS":
            result = task_result.result
            return {
                "job_id": job_id,
                "status": "completed",
                "progress": 100,
                "result": result,
            }

        elif task_result.state == "FAILURE":
            return {
                "job_id": job_id,
                "status": "failed",
                "error": str(task_result.info),
                "message": "Job processing failed",
            }

        else:
            return {
                "job_id": job_id,
                "status": task_result.state.lower(),
                "message": f"Job is {task_result.state}",
            }

    except Exception as e:
        logger.error(f"Error checking job status: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/jobs/batch")
async def add_job_batch(batch_input: JobBatchInput):
    """
    Queue multiple jobs at once.
    Returns immediately with all job_ids for tracking.
    """
    job_ids = []

    for url in batch_input.urls:
        try:
            task = process_job_task.apply_async(
                args=[str(url), batch_input.force_playwright]
            )
            job_ids.append(
                {
                    "job_id": task.id,
                    "url": str(url),
                    "status_url": f"/jobs/{task.id}/status",
                }
            )
        except Exception as e:
            logger.error(f"Failed to queue {url}: {e}")
            job_ids.append(
                {"url": str(url), "error": str(e), "status": "failed_to_queue"}
            )

    return {
        "status": "queued",
        "total_submitted": len(batch_input.urls),
        "total_queued": len([j for j in job_ids if "job_id" in j]),
        "jobs": job_ids,
        "message": f"Queued {len(job_ids)} jobs for processing",
    }


@router.post("/jobs/batch/status")
async def get_batch_status(job_ids: List[str]):
    """
    Check status of multiple jobs at once
    """
    results = []
    for job_id in job_ids:
        task_result = AsyncResult(job_id)
        results.append(
            {
                "job_id": job_id,
                "status": task_result.state.lower(),
            }
        )

    return {
        "total": len(job_ids),
        "completed": len([r for r in results if r["status"] == "success"]),
        "failed": len([r for r in results if r["status"] == "failure"]),
        "processing": len([r for r in results if r["status"] == "processing"]),
        "pending": len([r for r in results if r["status"] == "pending"]),
        "jobs": results,
    }


@router.post("/jobs/{job_id}/retry")
async def retry_job(job_id: str):
    """
    Retry a failed job
    """
    try:
        task_result = AsyncResult(job_id)

        if task_result.state != "FAILURE":
            raise HTTPException(
                status_code=400, detail=f"Job is {task_result.state}, not failed"
            )

        # Get original args from failed task (if available)
        # Note: This requires task to be retried with same args
        # For now, return error asking user to resubmit
        return {
            "status": "error",
            "message": "Please resubmit the job URL via /jobs/add endpoint",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrying job: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def health_check():
    """Quick health check endpoint"""
    return {
        "status": "healthy",
        "mode": "async",
        "task_queue": "celery+redis",
        "extractors": ["crawl4ai", "playwright+llm"],
        "duplicate_check": "enabled",
        "smart_filters": ["job_unavailable", "visa_restricted"],
        "resume_tailoring": "enabled (match_score > 70)",
        "cover_letter_tailoring": "enabled (match_score > 70)",
        "pdf_compilation": "enabled",
        "supabase_upload": "enabled",
    }
