import asyncio
from pathlib import Path
from services.pdf_compilation_service import compile_resume_to_pdf
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


async def main():
    # Load your debug resume content
    debug_file = Path("data/debug-tailored.tex")
    if not debug_file.exists():
        raise FileNotFoundError("debug-tailored.tex not found")

    tailored_content = debug_file.read_text(encoding="utf-8")

    try:
        pdf_bytes = await compile_resume_to_pdf(tailored_content)
        # Save locally so you can inspect
        out_path = Path("data/debug-output.pdf")
        out_path.write_bytes(pdf_bytes)
        logger.info(f"✅ PDF successfully compiled and saved to {out_path.resolve()}")
    except Exception as e:
        logger.exception(f"❌ PDF compilation failed: {e}")


if __name__ == "__main__":
    asyncio.run(main())
