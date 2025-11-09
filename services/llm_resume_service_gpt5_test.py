import os
import json
import logging
from openai import AsyncOpenAI

logger = logging.getLogger(__name__)

client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def load_master_resume() -> str:
    try:
        with open("data/resume-content.tex", "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        raise Exception("Master resume not found at data/resume-content.tex")


def smart_json_parse(raw: str):
    """
    Hybrid parser:
    1. Try strict json.loads()
    2. If it fails, try clean-up (remove fences, strip) then parse
    """
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass

    cleaned = raw.strip()

    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        # In case it's fenced like ```json\n ... \n```
        cleaned = cleaned.replace("json", "", 1).strip()

    try:
        return json.loads(cleaned)
    except Exception:
        logger.error("❌ Could not parse JSON even after cleanup.")
        logger.error(f"----- RAW OUTPUT START -----\n{raw}\n----- RAW OUTPUT END -----")
        raise


async def tailor_resume(self, master_resume: str, evaluation: dict):
    logger = logging.getLogger(__name__)

    logger.info("🧪 [GPT5-TEST] Starting resume tailoring test...")
    logger.info(f"   • Job Title: {evaluation.get('job_title')}")
    logger.info(f"   • Company: {evaluation.get('company')}")

    logger.info(f"✅ Loaded master resume ({len(master_resume)} chars)")
    logger.info(f"📊 Match Score: {evaluation.get('match_score')}%")
    logger.info(f"   • Strengths: {len(evaluation.get('strengths', []))}")
    logger.info(f"   • Gaps: {len(evaluation.get('gaps', []))}")

    prompt = f"""
You are an expert resume optimization specialist. Return ONLY valid JSON.
(do not wrap in markdown fences)

MASTER RESUME:
{master_resume}

JOB TITLE: {evaluation['job_title']}
COMPANY: {evaluation['company']}
MATCH SCORE: {evaluation['match_score']}

STRENGTHS:
{evaluation['strengths']}

GAPS:
{evaluation['gaps']}

Return JSON in this schema:
{{
  "tailored_resume": "string"
}}
"""

    logger.info("🚀 [GPT5-TEST] Sending request to GPT-5 (Responses API)...")

    try:
        response = await self.client.responses.create(
            model="gpt-5",
            input=prompt,
            reasoning={"effort": "low"},  # ✅ Allowed
            text={"verbosity": "medium"},  # ✅ Allowed
            max_output_tokens=1500,  # ✅ Allowed
        )

        raw_json_text = response.output[0].content[0].text
        logger.debug("----- RAW GPT-5 RESPONSE -----")
        logger.debug(raw_json_text)
        logger.debug("------------------------------")

        cleaned = self._extract_json(raw_json_text)
        parsed = json.loads(cleaned)

        if "tailored_resume" not in parsed:
            raise ValueError("Missing 'tailored_resume' in GPT-5 output")

        logger.info("✅ GPT-5 resume tailoring completed successfully")
        return parsed["tailored_resume"]

    except Exception as e:
        logger.error(f"❌ GPT-5 tailoring test failed: {e}", exc_info=True)
        raise
