# streamlit_app.py
import streamlit as st
import requests
import time
import os
from dotenv import load_dotenv
from datetime import datetime
from typing import Dict, List
from streamlit_autorefresh import st_autorefresh  # ✅ Added import

# Load environment variables
load_dotenv()
API_BASE = os.getenv("API_BASE", "http://localhost:8000")

# Page config
st.set_page_config(
    page_title="Job Pipeline Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ✅ Auto-refresh every 10 seconds
st_autorefresh(interval=10000, key="job_auto_refresh")

# Custom CSS for better styling
st.markdown(
    """
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: 700;
        margin-bottom: 1rem;
    }
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1rem;
        border-radius: 0.5rem;
        color: white;
    }
    .job-card {
        border: 1px solid #e0e0e0;
        border-radius: 0.5rem;
        padding: 1rem;
        margin-bottom: 1rem;
        background: white;
    }
    .stage-indicator {
        display: inline-block;
        font-size: 1.5rem;
        margin: 0 0.2rem;
    }
    .stProgress > div > div > div > div {
        background-color: #667eea;
    }
</style>
""",
    unsafe_allow_html=True,
)

# Initialize session state
if "jobs" not in st.session_state:
    st.session_state.jobs = {}
if "auto_refresh" not in st.session_state:
    st.session_state.auto_refresh = True
if "last_poll" not in st.session_state:
    st.session_state.last_poll = time.time()

# Stage configuration (unchanged)
STAGE_CONFIG = {
    "duplicate_check": {"emoji": "🔍", "label": "Check", "order": 0},
    "extracting": {"emoji": "🕷️", "label": "Extract", "order": 1},
    "evaluating": {"emoji": "🧠", "label": "Evaluate", "order": 2},
    "tailoring_resume": {"emoji": "📄", "label": "Resume", "order": 3},
    "compiling_resume_pdf": {"emoji": "📄", "label": "Resume", "order": 3},
    "tailoring_cover_letter": {"emoji": "✉️", "label": "Cover", "order": 4},
    "compiling_cover_letter_pdf": {"emoji": "✉️", "label": "Cover", "order": 4},
    "saving_to_notion": {"emoji": "💾", "label": "Save", "order": 5},
    "complete": {"emoji": "✅", "label": "Done", "order": 6},
    "queued": {"emoji": "⏳", "label": "Queued", "order": -1},
    "starting": {"emoji": "🚀", "label": "Starting", "order": 0},
}

ALL_STAGES = [
    "🔍 Check",
    "🕷️ Extract",
    "🧠 Evaluate",
    "📄 Resume",
    "✉️ Cover",
    "💾 Save",
    "✅ Done",
]


def get_stage_visual_for_job(job: Dict) -> str:
    """
    Generate visual pipeline with stage indicators using job dict.
    Accepts job dict (so we can consult result_status etc).
    """

    current_stage = job.get("stage", "queued")
    status = job.get("status", "unknown")
    progress = job.get("progress", 0)
    result_status = job.get("result_status")

    # Define all stages with readable labels
    STAGE_LABELS = [
        ("fetch_job", "Fetch Job"),
        ("parse_content", "Parse Content"),
        ("extract_details", "Extract Details"),
        ("evaluate_match", "Evaluate Match"),
        ("compile_docs", "Compile Docs"),
        ("notion_upload", "Upload to Notion"),
    ]

    # queued/pending shortcut
    if status in ("queued", "pending"):
        return "⏳ " + " → ".join([f"⚪ {label}" for _, label in STAGE_LABELS])

    if status == "failed":
        stage_order = STAGE_CONFIG.get(current_stage, {}).get("order", 0)
        stages = []
        for i, (_, label) in enumerate(STAGE_LABELS):
            if i < stage_order:
                stages.append(f"✅ {label}")
            elif i == stage_order:
                stages.append(f"❌ {label}")
            else:
                stages.append(f"⚪ {label}")
        return " → ".join(stages)

    if status == "completed":
        # Show special cases based on result_status
        if result_status in ["duplicate", "unavailable", "visa_restricted"]:
            return " " + " → ".join(
                [
                    f"✅ {label}" if i < 2 else f"⚠️ {label}"
                    for i, (_, label) in enumerate(STAGE_LABELS)
                ]
            )
        return " → ".join([f"✅ {label}" for _, label in STAGE_LABELS])

    # processing state: highlight current stage
    stage_order = STAGE_CONFIG.get(current_stage, {}).get("order", 0)
    stages = []
    for i, (_, label) in enumerate(STAGE_LABELS):
        if i < stage_order:
            stages.append(f"✅ {label}")
        elif i == stage_order:
            stages.append(f"🔵 {label}")
        else:
            stages.append(f"⚪ {label}")

    return " → ".join(stages)


def poll_job_status(job_id: str) -> Dict:
    """Poll API for job status"""
    try:
        response = requests.get(f"{API_BASE}/jobs/{job_id}/status", timeout=5)
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        return {"status": "error", "stage": f"Error: {str(e)}", "progress": 0}
    return {"status": "unknown", "stage": "unknown", "progress": 0}


def queue_job(url: str, force_playwright: bool = False) -> Dict:
    """Queue a new job"""
    try:
        response = requests.post(
            f"{API_BASE}/jobs/add",
            json={"url": url, "force_playwright": force_playwright},
            timeout=10,
        )
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        return {"error": str(e)}
    return {"error": "Unknown error"}


def retry_job(url: str, force_playwright: bool = False) -> Dict:
    """Retry a failed job by re-queueing it"""
    return queue_job(url, force_playwright)


# ============================================================================
# HEADER
# ============================================================================
st.markdown(
    '<div class="main-header">📊 Job Pipeline Dashboard</div>', unsafe_allow_html=True
)

# ============================================================================
# METRICS ROW
# ============================================================================
total_jobs = len(st.session_state.jobs)
queued = sum(
    1 for j in st.session_state.jobs.values() if j["status"] in ("queued", "pending")
)
processing = sum(
    1 for j in st.session_state.jobs.values() if j["status"] == "processing"
)
completed = sum(1 for j in st.session_state.jobs.values() if j["status"] == "completed")
failed = sum(1 for j in st.session_state.jobs.values() if j["status"] == "failed")

col1, col2, col3, col4, col5 = st.columns(5)
with col1:
    st.metric("📊 Total", total_jobs)
with col2:
    st.metric("⏳ Queued", queued)
with col3:
    st.metric("🔄 Running", processing)
with col4:
    st.metric("✅ Done", completed)
with col5:
    st.metric("❌ Failed", failed)

st.divider()

# ============================================================================
# INPUT SECTION
# ============================================================================
st.subheader("📝 Add Job URLs")

col_input, col_options = st.columns([3, 1])

with col_input:
    if "url_text" not in st.session_state:
        st.session_state.url_text = ""
    urls_input = st.text_area(
        "Paste job URLs (one per line)",
        placeholder="https://jobs.lever.co/company/job-id-1\nhttps://greenhouse.io/company/job-id-2\nhttps://workday.com/company/job-id-3",
        height=120,
        value=st.session_state.url_text,
        key="url_input",
    )

with col_options:
    st.write("")  # Spacing
    st.write("")  # Spacing
    force_playwright = st.checkbox("🔧 Force Playwright", help="Skip Crawl4AI")
    auto_clear = st.checkbox(
        "🧹 Auto-clear input", value=True, help="Clear input after queueing"
    )

# Parse URLs
urls = [
    url.strip()
    for url in urls_input.split("\n")
    if url.strip() and url.strip().startswith("http")
]

if urls:
    st.info(f"📋 Found **{len(urls)}** valid URL(s) ready to queue")

# Buttons
col_btn1, col_btn2, col_btn3, col_btn4 = st.columns([2, 2, 2, 4])

with col_btn1:
    queue_btn = st.button(
        "🚀 Queue Jobs", type="primary", disabled=not urls, use_container_width=True
    )

with col_btn2:
    if st.button("🗑️ Clear All Jobs", type="secondary", use_container_width=True):
        st.session_state.jobs = {}
        st.rerun()

with col_btn3:
    refresh_btn = st.button("🔄 Refresh Now", use_container_width=True)

with col_btn4:
    auto_refresh_toggle = st.checkbox(
        "⏸️ Pause auto-refresh",
        value=not st.session_state.auto_refresh,
        help="Stop automatic polling",
    )
    st.session_state.auto_refresh = not auto_refresh_toggle

# Queue jobs
if queue_btn and urls:
    with st.spinner(f"Queueing {len(urls)} jobs..."):
        success_count = 0
        for url in urls:
            result = queue_job(url, force_playwright)

            if "job_id" in result:
                job_id = result["job_id"]
                st.session_state.jobs[job_id] = {
                    "job_id": job_id,
                    "url": url,
                    "status": "queued",
                    "stage": "queued",
                    "progress": 0,
                    "result": None,
                    "result_status": None,
                    "added_at": datetime.now().strftime("%H:%M:%S"),
                    "force_playwright": force_playwright,
                }
                success_count += 1
            else:
                st.error(f"Failed to queue: {url} -> {result.get('error', 'unknown')}")

        if success_count > 0:
            st.success(f"✅ Queued {success_count} job(s)!")
            if auto_clear:
                st.session_state.url_text = ""
            # force immediate poll on rerun
            st.session_state.last_poll = 0
            time.sleep(0.3)
            st.rerun()

st.divider()

# ============================================================================
# LIVE PIPELINE STATUS (no background colours)
# ============================================================================
st.subheader("📋 Live Pipeline Status")

if not st.session_state.jobs:
    st.info("👋 No jobs yet. Paste some URLs above to get started!")
else:
    # Auto-refresh logic
    active_jobs = [
        job_id
        for job_id, job in st.session_state.jobs.items()
        if job["status"] in ["queued", "pending", "processing"]
    ]

    should_refresh = (
        st.session_state.auto_refresh
        and active_jobs
        and (time.time() - st.session_state.last_poll) > 2
    )

    if should_refresh or refresh_btn:
        with st.spinner("Polling active jobs..."):
            for job_id in active_jobs:
                status_data = poll_job_status(job_id)
                raw_status = str(status_data.get("status", "")).lower()

                if raw_status in ("pending", "waiting"):
                    normalized_status = "queued"
                elif raw_status in ("processing", "process", "started"):
                    normalized_status = "processing"
                elif raw_status in ("success", "completed", "finished"):
                    normalized_status = "completed"
                elif raw_status in ("failure", "failed", "error"):
                    normalized_status = "failed"
                else:
                    normalized_status = raw_status or "unknown"

                # Update job state
                job = st.session_state.jobs[job_id]
                job["status"] = normalized_status
                job["stage"] = status_data.get(
                    "stage", job.get("stage", normalized_status)
                )
                job["progress"] = status_data.get("progress", job.get("progress", 0))

                if "result" in status_data and status_data.get("result") is not None:
                    job["result"] = status_data["result"]
                    if isinstance(status_data["result"], dict):
                        job["result_status"] = status_data["result"].get("status")

                if normalized_status == "completed":
                    job["completed_at"] = datetime.now().strftime("%H:%M:%S")

            st.session_state.last_poll = time.time()
        st.rerun()

    # Display jobs (no colored background boxes)
    for i, (job_id, job) in enumerate(st.session_state.jobs.items(), start=1):
        status = job["status"]
        stage = job.get("stage", "")
        progress = job.get("progress", 0)
        url = job["url"]

        with st.container():
            # ✅ NEW: Add job heading
            st.markdown(f"#### Job Link #{i}")

            # Header row
            col_header, col_status = st.columns([3, 1])

            with col_header:
                display_url = url if len(url) <= 60 else url[:57] + "..."
                st.markdown(f"[{display_url}]({url})")

            with col_status:
                status_emoji = {
                    "queued": "⏳",
                    "processing": "🔄",
                    "completed": "✅",
                    "failed": "❌",
                    "unknown": "❓",
                }.get(status, "❓")
                st.markdown(f"**{status_emoji} {status.title()}**")

            # Pipeline visualization
            stage_visual = get_stage_visual_for_job(job)
            st.markdown(f"##### {stage_visual}")

            # Progress bar
            if status in ["processing", "queued", "pending"] and progress > 0:
                try:
                    st.progress(
                        min(max(progress / 100.0, 0.0), 1.0),
                        text=f"{progress}% - {str(stage).replace('_', ' ').title()}",
                    )
                except Exception:
                    st.progress(min(max(progress / 100.0, 0.0), 1.0))

            # Details expander
            with st.expander("📄 Details"):
                col1, col2, col3 = st.columns(3)

                with col1:
                    st.write(f"**Job ID:** `{job_id[:12]}...`")
                    st.write(f"**Added:** {job.get('added_at', 'N/A')}")
                    st.write(f"**Stage:** {str(stage).replace('_', ' ').title()}")
                    if job.get("completed_at"):
                        st.write(f"**Completed:** {job.get('completed_at')}")

                with col2:
                    st.write(f"**Status:** {status.title()}")
                    st.write(f"**Progress:** {progress}%")
                    if job.get("force_playwright"):
                        st.write("**Mode:** Playwright (forced)")

                with col3:
                    if status == "failed":
                        if st.button(f"🔄 Retry", key=f"retry_{job_id}"):
                            with st.spinner("Re-queueing job..."):
                                result = retry_job(
                                    url, job.get("force_playwright", False)
                                )
                                if "job_id" in result:
                                    new_job_id = result["job_id"]
                                    st.session_state.jobs[new_job_id] = {
                                        "job_id": new_job_id,
                                        "url": url,
                                        "status": "queued",
                                        "stage": "queued",
                                        "progress": 0,
                                        "result": None,
                                        "result_status": None,
                                        "added_at": datetime.now().strftime("%H:%M:%S"),
                                        "force_playwright": job.get(
                                            "force_playwright", False
                                        ),
                                    }
                                    st.success("✅ Job re-queued!")
                                    st.session_state.last_poll = 0
                                    time.sleep(0.2)
                                    st.rerun()

                # Completed job results
                if status == "completed" and job.get("result"):
                    result = job["result"]
                    result_status = result.get("status")
                    st.divider()

                    if result_status == "success":
                        st.success("✅ Job processed successfully!")
                    elif result_status == "duplicate":
                        st.warning("🔄 Duplicate job detected")
                    elif result_status == "unavailable":
                        st.warning("🚫 Job posting unavailable")
                    elif result_status == "visa_restricted":
                        st.warning("🛂 Visa sponsorship not available")

    # Auto-refresh caption
    if st.session_state.auto_refresh and active_jobs:
        st.caption(
            f"🔄 Auto-refreshing every 2–3 seconds | {len(active_jobs)} active job(s)"
        )


st.divider()
st.caption(
    "💡 **Pro Tip:** Queue up to 100 jobs at once! They process in parallel. Come back anytime to check progress."
)
