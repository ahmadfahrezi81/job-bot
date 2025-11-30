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
    Check detailed status of a queued/processing job
    Returns stage, progress, and result information
    """
    try:
        task_result = AsyncResult(job_id)

        if task_result.state == "PENDING":
            return {
                "job_id": job_id,
                "status": "pending",
                "stage": "queued",
                "message": "Job is waiting in queue",
                "progress": 0,
            }

        elif task_result.state in ["STARTED", "PROCESSING"]:
            # Get custom metadata from task
            info = task_result.info or {}
            stage = info.get("stage", "unknown")
            progress = info.get("progress", 0)

            return {
                "job_id": job_id,
                "status": "processing",
                "stage": stage,
                "progress": progress,
                "message": f"Currently: {stage.replace('_', ' ').title()}",
                "meta": info,  # Include full metadata for debugging
            }

        elif task_result.state == "SUCCESS":
            result = task_result.result

            # Determine result_status from result dict
            result_status = None
            if isinstance(result, dict):
                result_status = result.get("status")

            return {
                "job_id": job_id,
                "status": "completed",
                "stage": "complete",
                "progress": 100,
                "result": result,
                "result_status": result_status,
                "message": "Job completed successfully",
            }

        elif task_result.state == "FAILURE":
            error_info = str(task_result.info)
            return {
                "job_id": job_id,
                "status": "failed",
                "stage": "failed",
                "error": error_info,
                "message": "Job processing failed",
                "progress": 0,
            }

        else:
            # Handle any other Celery states (RETRY, REVOKED, etc.)
            return {
                "job_id": job_id,
                "status": task_result.state.lower(),
                "stage": task_result.state.lower(),
                "message": f"Job is {task_result.state}",
                "progress": 0,
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
    job_results = []
    success_count = 0

    logger.info(f"Queueing batch of {len(batch_input.urls)} jobs")

    for url in batch_input.urls:
        try:
            task = process_job_task.apply_async(
                args=[str(url), batch_input.force_playwright]
            )
            job_results.append(
                {
                    "job_id": task.id,
                    "url": str(url),
                    "status": "queued",
                    "status_url": f"/jobs/{task.id}/status",
                }
            )
            success_count += 1
            logger.info(f"Queued job {task.id} for {url}")

        except Exception as e:
            logger.error(f"Failed to queue {url}: {e}")
            job_results.append(
                {"url": str(url), "error": str(e), "status": "failed_to_queue"}
            )

    return {
        "status": "batch_queued",
        "total_submitted": len(batch_input.urls),
        "total_queued": success_count,
        "total_failed": len(batch_input.urls) - success_count,
        "jobs": job_results,
        "message": f"Successfully queued {success_count}/{len(batch_input.urls)} jobs",
    }


@router.post("/jobs/batch/status")
async def get_batch_status(job_ids: List[str]):
    """
    Check status of multiple jobs at once
    Returns summary stats and basic status for each job

    For detailed status (stage, progress), use individual /jobs/{job_id}/status endpoint
    """
    results = []

    for job_id in job_ids:
        try:
            task_result = AsyncResult(job_id)

            # Get basic state
            state = task_result.state

            # Normalize state to standard status
            if state == "PENDING":
                status = "pending"
            elif state in ["STARTED", "PROCESSING"]:
                status = "processing"
            elif state == "SUCCESS":
                status = "success"
            elif state == "FAILURE":
                status = "failure"
            else:
                status = state.lower()

            results.append(
                {
                    "job_id": job_id,
                    "status": status,
                    "state": state,  # Include original Celery state
                }
            )

        except Exception as e:
            logger.error(f"Error checking status for job {job_id}: {e}")
            results.append(
                {
                    "job_id": job_id,
                    "status": "error",
                    "error": str(e),
                }
            )

    # Calculate summary statistics
    status_counts = {
        "completed": len([r for r in results if r["status"] == "success"]),
        "failed": len([r for r in results if r["status"] == "failure"]),
        "processing": len([r for r in results if r["status"] == "processing"]),
        "pending": len([r for r in results if r["status"] == "pending"]),
        "error": len([r for r in results if r["status"] == "error"]),
    }

    return {
        "total": len(job_ids),
        "summary": status_counts,
        "completed": status_counts["completed"],
        "failed": status_counts["failed"],
        "processing": status_counts["processing"],
        "pending": status_counts["pending"],
        "jobs": results,
        "message": f"Status retrieved for {len(results)}/{len(job_ids)} jobs",
    }


@router.post("/jobs/{job_id}/retry")
async def retry_job(job_id: str):
    """
    Retry a failed job

    Note: Due to Celery architecture, we can't automatically retry with original args.
    Client should re-submit via /jobs/add endpoint with the original URL.
    """
    try:
        task_result = AsyncResult(job_id)

        if task_result.state != "FAILURE":
            raise HTTPException(
                status_code=400,
                detail=f"Job is {task_result.state}, not failed. Only failed jobs can be retried.",
            )

        # Celery doesn't store original task args by default
        # Client must resubmit via /jobs/add
        return {
            "status": "retry_not_supported",
            "message": "Please resubmit the job URL via POST /jobs/add endpoint",
            "job_id": job_id,
            "current_state": task_result.state,
            "suggestion": "Use the original URL and POST to /jobs/add to queue a new job",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrying job: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/jobs/{job_id}")
async def cancel_job(job_id: str):
    """
    Cancel a pending or running job
    """
    try:
        task_result = AsyncResult(job_id)

        if task_result.state in ["PENDING", "STARTED", "PROCESSING"]:
            # Revoke the task
            task_result.revoke(terminate=True)

            return {
                "status": "cancelled",
                "job_id": job_id,
                "message": f"Job cancelled (was {task_result.state})",
            }
        else:
            return {
                "status": "cannot_cancel",
                "job_id": job_id,
                "current_state": task_result.state,
                "message": f"Job is {task_result.state} and cannot be cancelled",
            }

    except Exception as e:
        logger.error(f"Error cancelling job: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def health_check():
    """
    Health check endpoint with system information
    """
    return {
        "status": "healthy",
        "timestamp": time.time(),
        "mode": "async",
        "components": {
            "task_queue": "celery+redis",
            "extractors": ["crawl4ai", "playwright+llm"],
            "duplicate_check": "enabled",
            "smart_filters": ["job_unavailable", "visa_restricted"],
            "resume_tailoring": "enabled (match_score >= 70)",
            "cover_letter_tailoring": "enabled (match_score >= 70)",
            "pdf_compilation": "enabled",
            "storage": "supabase",
            "notion_integration": "enabled",
        },
        "endpoints": {
            "queue_single": "POST /jobs/add",
            "queue_batch": "POST /jobs/batch",
            "check_status": "GET /jobs/{job_id}/status",
            "batch_status": "POST /jobs/batch/status",
            "cancel_job": "DELETE /jobs/{job_id}",
        },
    }


@router.get("/stats")
async def get_system_stats():
    """
    Get overall system statistics (requires Celery inspect)
    """
    try:
        from app.celery_app import celery_app

        # Get Celery inspector
        inspect = celery_app.control.inspect()

        # Get active tasks
        active_tasks = inspect.active()
        scheduled_tasks = inspect.scheduled()
        reserved_tasks = inspect.reserved()

        active_count = sum(len(tasks) for tasks in (active_tasks or {}).values())
        scheduled_count = sum(len(tasks) for tasks in (scheduled_tasks or {}).values())
        reserved_count = sum(len(tasks) for tasks in (reserved_tasks or {}).values())

        return {
            "status": "ok",
            "workers": {
                "active_tasks": active_count,
                "scheduled_tasks": scheduled_count,
                "reserved_tasks": reserved_count,
                "total_queued": active_count + scheduled_count + reserved_count,
            },
            "message": "System statistics retrieved successfully",
        }

    except Exception as e:
        logger.warning(f"Could not retrieve stats: {e}")
        return {
            "status": "unavailable",
            "message": "Statistics unavailable (workers may be offline)",
            "error": str(e),
        }
