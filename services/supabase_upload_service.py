# services/supabase_upload_service.py
import logging
import os
from datetime import datetime
from supabase import create_client, Client
import re
import uuid


logger = logging.getLogger(__name__)


def get_supabase_client() -> Client:
    """
    Initializes a Supabase client using SERVICE_ROLE_KEY (more privileged)
    or environment variables.
    """
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_KEY")  # Use service key for RLS bypass

    if not url or not key:
        raise ValueError(
            "❌ Missing SUPABASE_URL or SUPABASE_SERVICE_KEY in environment"
        )

    return create_client(url, key)


async def upload_pdf_to_supabase(
    pdf_bytes: bytes,
    position: str,
    company: str,
    filename_prefix: str = "AhmadFahrezi_Resume",
    bucket_name: str = "resumes",
) -> dict:
    """
    Uploads a compiled PDF file to Supabase Storage and returns its public URL.
    Filename: AhmadFahrezi_Resume_[Position]_[Company]_YYYYMMDD.pdf

    Args:
        pdf_bytes: PDF data as bytes
        position: Job title / position
        company: Company name
        filename_prefix: Static prefix (default: AhmadFahrezi_Resume)
        bucket_name: Supabase bucket name

    Returns:
        dict: {"status":"success", "path":..., "size":..., "public_url":...}
    """
    supabase = get_supabase_client()

    # Sanitize inputs
    def sanitize(s: str) -> str:
        s = s.strip().replace(" ", "_")
        s = re.sub(r"[^\w\-]", "", s)  # Remove anything not alphanumeric or _
        return s

    position_clean = sanitize(position or "role")
    company_clean = sanitize(company or "company")
    # Generate timestamp
    timestamp = datetime.utcnow().strftime("%Y%m%d")

    # Generate short 4-character unique ID
    unique_id = uuid.uuid4().hex[:4]

    # Build filename
    filename = f"{filename_prefix}_{position_clean}_{company_clean}_{timestamp}_{unique_id}.pdf"

    logger.info(f"📤 Uploading {filename} to Supabase bucket '{bucket_name}'...")
    logger.info(f"   • Size: {len(pdf_bytes)} bytes")

    try:
        response = supabase.storage.from_(bucket_name).upload(
            path=filename,
            file=pdf_bytes,
            file_options={"content-type": "application/pdf"},
        )

        if hasattr(response, "error") and response.error:
            raise Exception(f"Upload error: {response.error}")

        public_url = supabase.storage.from_(bucket_name).get_public_url(filename)

        logger.info(f"✅ Upload successful! Public URL: {public_url}")

        return {
            "status": "success",
            "path": filename,
            "size": len(pdf_bytes),
            "public_url": public_url,
        }

    except Exception as e:
        logger.exception("❌ Supabase upload failed")
        raise Exception(f"Supabase upload failed: {str(e)}")
