import asyncio
import logging
import tempfile
from pathlib import Path
import shutil
import os

logger = logging.getLogger(__name__)


async def compile_resume_to_pdf(tailored_content: str) -> bytes:
    """
    Compiles tailored LaTeX resume content to PDF asynchronously.
    Debug version: keeps temp folder and prints full pdflatex logs for easier debugging.
    """
    logger.info("📄 Starting LaTeX → PDF compilation")

    pdflatex_path = shutil.which("pdflatex")
    if not pdflatex_path:
        raise FileNotFoundError("pdflatex not found in PATH")

    main_tex_src = Path("data/main.tex")
    if not main_tex_src.exists():
        raise FileNotFoundError("main.tex not found in data/ directory")

    # --- DEBUG: Use fixed temp folder so you can inspect ---
    tmpdir_path = Path("data/tmp_debug_pdf")
    tmpdir_path.mkdir(exist_ok=True)
    logger.info(f"🧩 Using temp folder for debugging: {tmpdir_path}")

    # Copy main.tex to temp folder
    main_tex_dest = tmpdir_path / "main.tex"
    shutil.copy(main_tex_src, main_tex_dest)
    logger.info(f"✅ Copied main.tex to {main_tex_dest}")

    # Save tailored resume content as resume-content.tex in temp folder
    resume_run_path = tmpdir_path / "resume-content.tex"
    resume_run_path.write_text(tailored_content, encoding="utf-8")
    logger.info(f"✅ Written tailored resume to {resume_run_path}")

    # Save debug copy
    debug_copy = Path("data/debug-tailored.tex")
    debug_copy.write_text(tailored_content, encoding="utf-8")
    logger.info(f"🪶 Saved debug copy at {debug_copy.resolve()}")

    # Environment (ensure fonts/packages work)
    env = os.environ.copy()
    env["TEXMFHOME"] = str(Path.home() / "Library/TinyTeX/texmf-var")

    async def run_pdflatex(pass_num: int):
        logger.info(f"▶️ Running pdflatex (pass {pass_num}/2)...")
        proc = await asyncio.create_subprocess_exec(
            pdflatex_path,
            "-interaction=nonstopmode",
            "main.tex",
            cwd=tmpdir_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env,
        )
        stdout, stderr = await proc.communicate()
        stdout_text = stdout.decode(errors="ignore")
        stderr_text = stderr.decode(errors="ignore")

        # Save full log to file if exists
        log_path = tmpdir_path / "main.log"
        if log_path.exists():
            logger.debug(
                f"📄 main.log content:\n{log_path.read_text(encoding='utf-8')}"
            )

        if proc.returncode != 0:
            logger.error(f"❌ pdflatex failed on pass {pass_num}")
            logger.debug(f"pdflatex STDOUT:\n{stdout_text}")
            logger.debug(f"pdflatex STDERR:\n{stderr_text}")
            raise Exception("LaTeX compilation failed (see logs)")

        logger.info(f"✅ pdflatex pass {pass_num} completed successfully")

    # Run pdflatex twice
    await run_pdflatex(1)
    await run_pdflatex(2)

    # Read generated PDF
    pdf_path = tmpdir_path / "main.pdf"
    if not pdf_path.exists():
        raise FileNotFoundError("main.pdf not generated after pdflatex runs")

    pdf_bytes = pdf_path.read_bytes()
    logger.info(f"✅ PDF compiled successfully ({len(pdf_bytes)} bytes)")
    logger.info(
        f"💡 Temp folder preserved at: {tmpdir_path.resolve()} for manual inspection"
    )
    return pdf_bytes
