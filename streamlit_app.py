# # streamlit_app.py
# import streamlit as st
# import requests
# import time
# import os
# from dotenv import load_dotenv
# from datetime import datetime
# from typing import Dict, List
# from streamlit_autorefresh import st_autorefresh  # ✅ Added import

# # Load environment variables
# load_dotenv()
# API_BASE = st.secrets.get("API_BASE", os.getenv("API_BASE", "http://localhost:8000"))

# # Page config
# st.set_page_config(
#     page_title="Job Pipeline Dashboard",
#     page_icon="📊",
#     layout="wide",
#     initial_sidebar_state="collapsed",
# )

# # ✅ Auto-refresh every 10 seconds
# st_autorefresh(interval=10000, key="job_auto_refresh")

# # Custom CSS for better styling
# st.markdown(
#     """
# <style>
#     .main-header {
#         font-size: 2.5rem;
#         font-weight: 700;
#         margin-bottom: 1rem;
#     }
#     .metric-card {
#         background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
#         padding: 1rem;
#         border-radius: 0.5rem;
#         color: white;
#     }
#     .job-card {
#         border: 1px solid #e0e0e0;
#         border-radius: 0.5rem;
#         padding: 1rem;
#         margin-bottom: 1rem;
#         background: white;
#     }
#     .stage-indicator {
#         display: inline-block;
#         font-size: 1.5rem;
#         margin: 0 0.2rem;
#     }
#     .stProgress > div > div > div > div {
#         background-color: #667eea;
#     }
# </style>
# """,
#     unsafe_allow_html=True,
# )

# # Initialize session state
# if "jobs" not in st.session_state:
#     st.session_state.jobs = {}
# if "auto_refresh" not in st.session_state:
#     st.session_state.auto_refresh = True
# if "last_poll" not in st.session_state:
#     st.session_state.last_poll = time.time()

# # Stage configuration (unchanged)
# STAGE_CONFIG = {
#     "duplicate_check": {"emoji": "🔍", "label": "Check", "order": 0},
#     "extracting": {"emoji": "🕷️", "label": "Extract", "order": 1},
#     "evaluating": {"emoji": "🧠", "label": "Evaluate", "order": 2},
#     "tailoring_resume": {"emoji": "📄", "label": "Resume", "order": 3},
#     "compiling_resume_pdf": {"emoji": "📄", "label": "Resume", "order": 3},
#     "tailoring_cover_letter": {"emoji": "✉️", "label": "Cover", "order": 4},
#     "compiling_cover_letter_pdf": {"emoji": "✉️", "label": "Cover", "order": 4},
#     "saving_to_notion": {"emoji": "💾", "label": "Save", "order": 5},
#     "complete": {"emoji": "✅", "label": "Done", "order": 6},
#     "queued": {"emoji": "⏳", "label": "Queued", "order": -1},
#     "starting": {"emoji": "🚀", "label": "Starting", "order": 0},
# }

# ALL_STAGES = [
#     "🔍 Check",
#     "🕷️ Extract",
#     "🧠 Evaluate",
#     "📄 Resume",
#     "✉️ Cover",
#     "💾 Save",
#     "✅ Done",
# ]


# def get_stage_visual_for_job(job: Dict) -> str:
#     """
#     Generate visual pipeline with stage indicators using job dict.
#     Accepts job dict (so we can consult result_status etc).
#     """

#     current_stage = job.get("stage", "queued")
#     status = job.get("status", "unknown")
#     progress = job.get("progress", 0)
#     result_status = job.get("result_status")

#     # Define all stages with readable labels
#     STAGE_LABELS = [
#         ("fetch_job", "Fetch Job"),
#         ("parse_content", "Parse Content"),
#         ("extract_details", "Extract Details"),
#         ("evaluate_match", "Evaluate Match"),
#         ("compile_docs", "Compile Docs"),
#         ("notion_upload", "Upload to Notion"),
#     ]

#     # queued/pending shortcut
#     if status in ("queued", "pending"):
#         return "⏳ " + " → ".join([f"⚪ {label}" for _, label in STAGE_LABELS])

#     if status == "failed":
#         stage_order = STAGE_CONFIG.get(current_stage, {}).get("order", 0)
#         stages = []
#         for i, (_, label) in enumerate(STAGE_LABELS):
#             if i < stage_order:
#                 stages.append(f"✅ {label}")
#             elif i == stage_order:
#                 stages.append(f"❌ {label}")
#             else:
#                 stages.append(f"⚪ {label}")
#         return " → ".join(stages)

#     if status == "completed":
#         # Show special cases based on result_status
#         if result_status in ["duplicate", "unavailable", "visa_restricted"]:
#             return " " + " → ".join(
#                 [
#                     f"✅ {label}" if i < 2 else f"⚠️ {label}"
#                     for i, (_, label) in enumerate(STAGE_LABELS)
#                 ]
#             )
#         return " → ".join([f"✅ {label}" for _, label in STAGE_LABELS])

#     # processing state: highlight current stage
#     stage_order = STAGE_CONFIG.get(current_stage, {}).get("order", 0)
#     stages = []
#     for i, (_, label) in enumerate(STAGE_LABELS):
#         if i < stage_order:
#             stages.append(f"✅ {label}")
#         elif i == stage_order:
#             stages.append(f"🔵 {label}")
#         else:
#             stages.append(f"⚪ {label}")

#     return " → ".join(stages)


# def poll_job_status(job_id: str) -> Dict:
#     """Poll API for job status"""
#     try:
#         response = requests.get(f"{API_BASE}/jobs/{job_id}/status", timeout=5)
#         if response.status_code == 200:
#             return response.json()
#     except Exception as e:
#         return {"status": "error", "stage": f"Error: {str(e)}", "progress": 0}
#     return {"status": "unknown", "stage": "unknown", "progress": 0}


# def queue_job(url: str, force_playwright: bool = False) -> Dict:
#     """Queue a new job"""
#     try:
#         response = requests.post(
#             f"{API_BASE}/jobs/add",
#             json={"url": url, "force_playwright": force_playwright},
#             timeout=10,
#         )
#         if response.status_code == 200:
#             return response.json()
#     except Exception as e:
#         return {"error": str(e)}
#     return {"error": "Unknown error"}


# def queue_job_batch(urls: List[str], force_playwright: bool = False) -> Dict:
#     """Queue multiple jobs at once"""
#     try:
#         response = requests.post(
#             f"{API_BASE}/jobs/batch",
#             json={"urls": urls, "force_playwright": force_playwright},
#             timeout=30,
#         )
#         if response.status_code == 200:
#             return response.json()
#         else:
#             return {"error": f"HTTP {response.status_code}: {response.text}"}
#     except Exception as e:
#         return {"error": str(e)}


# def retry_job(url: str, force_playwright: bool = False) -> Dict:
#     """Retry a failed job by re-queueing it"""
#     return queue_job(url, force_playwright)


# # ============================================================================
# # HEADER
# # ============================================================================
# st.markdown(
#     '<div class="main-header">📊 Job Pipeline Dashboard</div>', unsafe_allow_html=True
# )

# # ============================================================================
# # METRICS ROW
# # ============================================================================
# total_jobs = len(st.session_state.jobs)
# queued = sum(
#     1 for j in st.session_state.jobs.values() if j["status"] in ("queued", "pending")
# )
# processing = sum(
#     1 for j in st.session_state.jobs.values() if j["status"] == "processing"
# )
# completed = sum(1 for j in st.session_state.jobs.values() if j["status"] == "completed")
# failed = sum(1 for j in st.session_state.jobs.values() if j["status"] == "failed")

# col1, col2, col3, col4, col5 = st.columns(5)
# with col1:
#     st.metric("📊 Total", total_jobs)
# with col2:
#     st.metric("⏳ Queued", queued)
# with col3:
#     st.metric("🔄 Running", processing)
# with col4:
#     st.metric("✅ Done", completed)
# with col5:
#     st.metric("❌ Failed", failed)

# st.divider()

# # ============================================================================
# # INPUT SECTION
# # ============================================================================
# st.subheader("📝 Add Job URLs")

# col_input, col_options = st.columns([3, 1])

# with col_input:
#     if "url_text" not in st.session_state:
#         st.session_state.url_text = ""
#     urls_input = st.text_area(
#         "Paste job URLs (one per line)",
#         placeholder="https://jobs.lever.co/company/job-id-1\nhttps://greenhouse.io/company/job-id-2\nhttps://workday.com/company/job-id-3",
#         height=120,
#         value=st.session_state.url_text,
#         key="url_input",
#     )

# with col_options:
#     st.write("")  # Spacing
#     st.write("")  # Spacing
#     force_playwright = st.checkbox("🔧 Force Playwright", help="Skip Crawl4AI")
#     auto_clear = st.checkbox(
#         "🧹 Auto-clear input", value=True, help="Clear input after queueing"
#     )

# # Parse URLs
# urls = [
#     url.strip()
#     for url in urls_input.split("\n")
#     if url.strip() and url.strip().startswith("http")
# ]

# if urls:
#     st.info(f"📋 Found **{len(urls)}** valid URL(s) ready to queue")

# # Buttons
# col_btn1, col_btn2, col_btn3, col_btn4 = st.columns([2, 2, 2, 4])

# with col_btn1:
#     queue_btn = st.button(
#         "🚀 Queue Jobs", type="primary", disabled=not urls, use_container_width=True
#     )

# with col_btn2:
#     if st.button("🗑️ Clear All Jobs", type="secondary", use_container_width=True):
#         st.session_state.jobs = {}
#         st.rerun()

# with col_btn3:
#     refresh_btn = st.button("🔄 Refresh Now", use_container_width=True)

# with col_btn4:
#     auto_refresh_toggle = st.checkbox(
#         "⏸️ Pause auto-refresh",
#         value=not st.session_state.auto_refresh,
#         help="Stop automatic polling",
#     )
#     st.session_state.auto_refresh = not auto_refresh_toggle

# # Queue jobs
# # if queue_btn and urls:
# #     with st.spinner(f"Queueing {len(urls)} jobs..."):
# #         success_count = 0
# #         for url in urls:
# #             result = queue_job(url, force_playwright)

# #             if "job_id" in result:
# #                 job_id = result["job_id"]
# #                 st.session_state.jobs[job_id] = {
# #                     "job_id": job_id,
# #                     "url": url,
# #                     "status": "queued",
# #                     "stage": "queued",
# #                     "progress": 0,
# #                     "result": None,
# #                     "result_status": None,
# #                     "added_at": datetime.now().strftime("%H:%M:%S"),
# #                     "force_playwright": force_playwright,
# #                 }
# #                 success_count += 1
# #             else:
# #                 st.error(f"Failed to queue: {url} -> {result.get('error', 'unknown')}")

# #         if success_count > 0:
# #             st.success(f"✅ Queued {success_count} job(s)!")
# #             if auto_clear:
# #                 st.session_state.url_text = ""
# #             # force immediate poll on rerun
# #             st.session_state.last_poll = 0
# #             time.sleep(0.3)
# #             st.rerun()

# if queue_btn and urls:
#     with st.spinner(f"Queueing {len(urls)} jobs..."):
#         result = queue_job_batch(urls, force_playwright)

#         if "jobs" in result:
#             queued_jobs = [j for j in result["jobs"] if "job_id" in j]
#             failed_jobs = [j for j in result["jobs"] if "error" in j]

#             for job in queued_jobs:
#                 job_id = job["job_id"]
#                 url = job["url"]
#                 st.session_state.jobs[job_id] = {
#                     "job_id": job_id,
#                     "url": url,
#                     "status": "queued",
#                     "stage": "queued",
#                     "progress": 0,
#                     "result": None,
#                     "result_status": None,
#                     "added_at": datetime.now().strftime("%H:%M:%S"),
#                     "force_playwright": force_playwright,
#                 }

#             if queued_jobs:
#                 st.success(f"✅ Queued {len(queued_jobs)} job(s) successfully!")
#             if failed_jobs:
#                 st.warning(f"⚠️ Failed to queue {len(failed_jobs)} job(s). Check logs.")

#             if auto_clear:
#                 st.session_state.url_text = ""
#             st.session_state.last_poll = 0
#             time.sleep(0.3)
#             st.rerun()
#         else:
#             st.error(f"Error queueing jobs: {result.get('error', 'unknown error')}")


# st.divider()

# # ============================================================================
# # LIVE PIPELINE STATUS (no background colours)
# # ============================================================================
# st.subheader("📋 Live Pipeline Status")

# if not st.session_state.jobs:
#     st.info("👋 No jobs yet. Paste some URLs above to get started!")
# else:
#     # Auto-refresh logic
#     active_jobs = [
#         job_id
#         for job_id, job in st.session_state.jobs.items()
#         if job["status"] in ["queued", "pending", "processing"]
#     ]

#     should_refresh = (
#         st.session_state.auto_refresh
#         and active_jobs
#         and (time.time() - st.session_state.last_poll) > 2
#     )

#     if should_refresh or refresh_btn:
#         with st.spinner("Polling active jobs..."):

#             # --- NEW: Use batch status endpoint ---
#             try:
#                 response = requests.post(
#                     f"{API_BASE}/jobs/batch/status",
#                     json=active_jobs,  # list of job IDs
#                     timeout=15,
#                 )
#                 if response.status_code == 200:
#                     batch_status = response.json()
#                     status_map = {
#                         j["job_id"]: j["status"] for j in batch_status.get("jobs", [])
#                     }
#                 else:
#                     st.warning(f"Batch status request failed ({response.status_code})")
#                     status_map = {}
#             except Exception as e:
#                 st.warning(f"Batch status check failed: {e}")
#                 status_map = {}

#             # --- Update each job in session state ---
#             for job_id in active_jobs:
#                 raw_status = str(status_map.get(job_id, "unknown")).lower()

#                 if raw_status in ("pending", "waiting"):
#                     normalized_status = "queued"
#                 elif raw_status in ("processing", "process", "started"):
#                     normalized_status = "processing"
#                 elif raw_status in ("success", "completed", "finished"):
#                     normalized_status = "completed"
#                 elif raw_status in ("failure", "failed", "error"):
#                     normalized_status = "failed"
#                 else:
#                     normalized_status = raw_status or "unknown"

#                 job = st.session_state.jobs[job_id]
#                 job["status"] = normalized_status
#                 job["stage"] = job.get("stage", normalized_status)

#                 if normalized_status == "completed":
#                     job["completed_at"] = datetime.now().strftime("%H:%M:%S")

#             st.session_state.last_poll = time.time()
#         st.rerun()

#     # if should_refresh or refresh_btn:
#     #     with st.spinner("Polling active jobs..."):
#     #         for job_id in active_jobs:
#     #             status_data = poll_job_status(job_id)
#     #             raw_status = str(status_data.get("status", "")).lower()

#     #             if raw_status in ("pending", "waiting"):
#     #                 normalized_status = "queued"
#     #             elif raw_status in ("processing", "process", "started"):
#     #                 normalized_status = "processing"
#     #             elif raw_status in ("success", "completed", "finished"):
#     #                 normalized_status = "completed"
#     #             elif raw_status in ("failure", "failed", "error"):
#     #                 normalized_status = "failed"
#     #             else:
#     #                 normalized_status = raw_status or "unknown"

#     #             # Update job state
#     #             job = st.session_state.jobs[job_id]
#     #             job["status"] = normalized_status
#     #             job["stage"] = status_data.get(
#     #                 "stage", job.get("stage", normalized_status)
#     #             )
#     #             job["progress"] = status_data.get("progress", job.get("progress", 0))

#     #             if "result" in status_data and status_data.get("result") is not None:
#     #                 job["result"] = status_data["result"]
#     #                 if isinstance(status_data["result"], dict):
#     #                     job["result_status"] = status_data["result"].get("status")

#     #             if normalized_status == "completed":
#     #                 job["completed_at"] = datetime.now().strftime("%H:%M:%S")

#     #         st.session_state.last_poll = time.time()
#     #     st.rerun()

#     # Display jobs (no colored background boxes)
#     for i, (job_id, job) in enumerate(st.session_state.jobs.items(), start=1):
#         status = job["status"]
#         stage = job.get("stage", "")
#         progress = job.get("progress", 0)
#         url = job["url"]

#         with st.container():
#             # ✅ NEW: Add job heading
#             st.markdown(f"#### Job Link #{i}")

#             # Header row
#             col_header, col_status = st.columns([3, 1])

#             with col_header:
#                 display_url = url if len(url) <= 60 else url[:57] + "..."
#                 st.markdown(f"[{display_url}]({url})")

#             with col_status:
#                 status_emoji = {
#                     "queued": "⏳",
#                     "processing": "🔄",
#                     "completed": "✅",
#                     "failed": "❌",
#                     "unknown": "❓",
#                 }.get(status, "❓")
#                 st.markdown(f"**{status_emoji} {status.title()}**")

#             # Pipeline visualization
#             stage_visual = get_stage_visual_for_job(job)
#             st.markdown(f"##### {stage_visual}")

#             # Progress bar
#             if status in ["processing", "queued", "pending"] and progress > 0:
#                 try:
#                     st.progress(
#                         min(max(progress / 100.0, 0.0), 1.0),
#                         text=f"{progress}% - {str(stage).replace('_', ' ').title()}",
#                     )
#                 except Exception:
#                     st.progress(min(max(progress / 100.0, 0.0), 1.0))

#             # Details expander
#             with st.expander("📄 Details"):
#                 col1, col2, col3 = st.columns(3)

#                 with col1:
#                     st.write(f"**Job ID:** `{job_id[:12]}...`")
#                     st.write(f"**Added:** {job.get('added_at', 'N/A')}")
#                     st.write(f"**Stage:** {str(stage).replace('_', ' ').title()}")
#                     if job.get("completed_at"):
#                         st.write(f"**Completed:** {job.get('completed_at')}")

#                 with col2:
#                     st.write(f"**Status:** {status.title()}")
#                     st.write(f"**Progress:** {progress}%")
#                     if job.get("force_playwright"):
#                         st.write("**Mode:** Playwright (forced)")

#                 with col3:
#                     if status == "failed":
#                         if st.button(f"🔄 Retry", key=f"retry_{job_id}"):
#                             with st.spinner("Re-queueing job..."):
#                                 result = retry_job(
#                                     url, job.get("force_playwright", False)
#                                 )
#                                 if "job_id" in result:
#                                     new_job_id = result["job_id"]
#                                     st.session_state.jobs[new_job_id] = {
#                                         "job_id": new_job_id,
#                                         "url": url,
#                                         "status": "queued",
#                                         "stage": "queued",
#                                         "progress": 0,
#                                         "result": None,
#                                         "result_status": None,
#                                         "added_at": datetime.now().strftime("%H:%M:%S"),
#                                         "force_playwright": job.get(
#                                             "force_playwright", False
#                                         ),
#                                     }
#                                     st.success("✅ Job re-queued!")
#                                     st.session_state.last_poll = 0
#                                     time.sleep(0.2)
#                                     st.rerun()

#                 # Completed job results
#                 if status == "completed" and job.get("result"):
#                     result = job["result"]
#                     result_status = result.get("status")
#                     st.divider()

#                     if result_status == "success":
#                         st.success("✅ Job processed successfully!")
#                     elif result_status == "duplicate":
#                         st.warning("🔄 Duplicate job detected")
#                     elif result_status == "unavailable":
#                         st.warning("🚫 Job posting unavailable")
#                     elif result_status == "visa_restricted":
#                         st.warning("🛂 Visa sponsorship not available")

#     # Auto-refresh caption
#     if st.session_state.auto_refresh and active_jobs:
#         st.caption(
#             f"🔄 Auto-refreshing every 2–3 seconds | {len(active_jobs)} active job(s)"
#         )


# st.divider()
# st.caption(
#     "💡 **Pro Tip:** Queue up to 100 jobs at once! They process in parallel. Come back anytime to check progress."
# )


# streamlit_app.py
import streamlit as st
import requests
import time
import os
from dotenv import load_dotenv
from datetime import datetime
from typing import Dict, List
from streamlit_autorefresh import st_autorefresh

# Load environment variables
load_dotenv()
# API_BASE = st.secrets.get("API_BASE", os.getenv("API_BASE", "http://localhost:8000"))


# Safe secret getter (avoid touching st.secrets if it's missing)
def get_secret_or_env(key: str, default: str = None):
    try:
        if "API_BASE" in st.secrets:
            return st.secrets[key]
    except Exception:
        # Happens when no secrets.toml exists locally
        pass
    return os.getenv(key, default)


API_BASE = get_secret_or_env("API_BASE", "http://localhost:8000")


# Page config
st.set_page_config(
    page_title="Job Pipeline Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Auto-refresh every 3 seconds
st_autorefresh(interval=3000, key="job_auto_refresh")

# Custom CSS
st.markdown(
    """
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: 700;
        margin-bottom: 1rem;
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

# Stage Configuration - matches backend exactly
STAGE_CONFIG = {
    "starting": {"emoji": "🚀", "label": "Starting", "order": 0, "progress": 5},
    "duplicate_check": {
        "emoji": "🔍",
        "label": "Duplicate Check",
        "order": 1,
        "progress": 10,
    },
    "extracting": {
        "emoji": "🕷️",
        "label": "Extracting Data",
        "order": 2,
        "progress": 20,
    },
    "evaluating": {
        "emoji": "🧠",
        "label": "Evaluating Match",
        "order": 3,
        "progress": 35,
    },
    "tailoring_resume": {
        "emoji": "📄",
        "label": "Tailoring Resume",
        "order": 4,
        "progress": 45,
    },
    "compiling_resume_pdf": {
        "emoji": "📑",
        "label": "Compiling Resume PDF",
        "order": 5,
        "progress": 55,
    },
    "tailoring_cover_letter": {
        "emoji": "✉️",
        "label": "Tailoring Cover Letter",
        "order": 6,
        "progress": 65,
    },
    "compiling_cover_letter_pdf": {
        "emoji": "📨",
        "label": "Compiling CL PDF",
        "order": 7,
        "progress": 75,
    },
    "saving_to_notion": {
        "emoji": "💾",
        "label": "Saving to Notion",
        "order": 8,
        "progress": 85,
    },
    "complete": {"emoji": "✅", "label": "Complete", "order": 9, "progress": 100},
    "queued": {"emoji": "⏳", "label": "Queued", "order": -1, "progress": 0},
    "pending": {"emoji": "⏳", "label": "Pending", "order": -1, "progress": 0},
    "failed": {"emoji": "❌", "label": "Failed", "order": -1, "progress": 0},
}

PIPELINE_STAGES = [
    "duplicate_check",
    "extracting",
    "evaluating",
    "tailoring_resume",
    "compiling_resume_pdf",
    "tailoring_cover_letter",
    "compiling_cover_letter_pdf",
    "saving_to_notion",
    "complete",
]


def get_stage_visual_for_job(job: Dict) -> str:
    """Generate visual pipeline based on current job state"""
    current_stage = job.get("stage", "queued")
    status = job.get("status", "unknown")
    result_status = job.get("result_status")

    current_order = STAGE_CONFIG.get(current_stage, {}).get("order", -1)

    # Queued/Pending - all grey
    if status in ("queued", "pending"):
        return " → ".join([f"⚪ {STAGE_CONFIG[s]['label']}" for s in PIPELINE_STAGES])

    # Failed - show where it failed
    if status == "failed":
        stages = []
        for stage_key in PIPELINE_STAGES:
            stage_order = STAGE_CONFIG[stage_key]["order"]
            if stage_order < current_order:
                stages.append(f"✅ {STAGE_CONFIG[stage_key]['label']}")
            elif stage_order == current_order:
                stages.append(f"❌ {STAGE_CONFIG[stage_key]['label']}")
            else:
                stages.append(f"⚪ {STAGE_CONFIG[stage_key]['label']}")
        return " → ".join(stages)

    # Completed - check result_status for early exits
    if status == "completed":
        if result_status == "duplicate":
            # Only duplicate_check done, rest skipped
            stages = [f"✅ {STAGE_CONFIG['duplicate_check']['label']}"]
            for stage_key in PIPELINE_STAGES[1:]:
                stages.append(f"⏭️ {STAGE_CONFIG[stage_key]['label']}")
            return " → ".join(stages)

        elif result_status in ["unavailable", "visa_restricted"]:
            # duplicate_check + extracting done, rest skipped
            stages = [
                f"✅ {STAGE_CONFIG['duplicate_check']['label']}",
                f"✅ {STAGE_CONFIG['extracting']['label']}",
            ]
            for stage_key in PIPELINE_STAGES[2:]:
                stages.append(f"⏭️ {STAGE_CONFIG[stage_key]['label']}")
            return " → ".join(stages)

        # Normal success - all done
        return " → ".join([f"✅ {STAGE_CONFIG[s]['label']}" for s in PIPELINE_STAGES])

    # Processing - show current progress
    stages = []
    for stage_key in PIPELINE_STAGES:
        stage_order = STAGE_CONFIG[stage_key]["order"]
        if stage_order < current_order:
            stages.append(f"✅ {STAGE_CONFIG[stage_key]['label']}")
        elif stage_order == current_order:
            stages.append(f"🔵 {STAGE_CONFIG[stage_key]['label']}")
        else:
            stages.append(f"⚪ {STAGE_CONFIG[stage_key]['label']}")
    return " → ".join(stages)


def poll_job_status(job_id: str) -> Dict:
    """Get detailed status for a single job"""
    try:
        response = requests.get(f"{API_BASE}/jobs/{job_id}/status", timeout=5)
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        return {"status": "error", "stage": "error", "progress": 0, "message": str(e)}
    return {"status": "unknown", "stage": "unknown", "progress": 0}


def queue_job_batch(urls: List[str], force_playwright: bool = False) -> Dict:
    """Queue multiple jobs"""
    try:
        response = requests.post(
            f"{API_BASE}/jobs/batch",
            json={"urls": urls, "force_playwright": force_playwright},
            timeout=30,
        )
        if response.status_code == 200:
            return response.json()
        else:
            return {"error": f"HTTP {response.status_code}: {response.text}"}
    except Exception as e:
        return {"error": str(e)}


def retry_job(url: str, force_playwright: bool = False) -> Dict:
    """Retry a failed job"""
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


def normalize_status(raw_status: str) -> str:
    """Normalize status strings"""
    status_lower = str(raw_status).lower()
    if status_lower in ("pending", "waiting"):
        return "queued"
    elif status_lower in ("processing", "process", "started"):
        return "processing"
    elif status_lower in ("success", "completed", "finished"):
        return "completed"
    elif status_lower in ("failure", "failed", "error"):
        return "failed"
    return status_lower or "unknown"


# ============================================================================
# HEADER
# ============================================================================
st.markdown(
    '<div class="main-header">📊 Job Pipeline Dashboard</div>', unsafe_allow_html=True
)

# ============================================================================
# METRICS
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
col1.metric("📊 Total", total_jobs)
col2.metric("⏳ Queued", queued)
col3.metric("🔄 Running", processing)
col4.metric("✅ Done", completed)
col5.metric("❌ Failed", failed)

st.divider()

# ============================================================================
# INPUT SECTION
# ============================================================================
st.subheader("🔗 Add Job URLs")

col_input, col_options = st.columns([3, 1])

with col_input:
    if "url_text" not in st.session_state:
        st.session_state.url_text = ""
    urls_input = st.text_area(
        "Paste job URLs (one per line)",
        placeholder="https://jobs.lever.co/company/job-id-1\nhttps://greenhouse.io/company/job-id-2",
        height=120,
        value=st.session_state.url_text,
        key="url_input",
    )

with col_options:
    st.write("")
    st.write("")
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
        result = queue_job_batch(urls, force_playwright)

        if "jobs" in result:
            queued_jobs = [j for j in result["jobs"] if "job_id" in j]
            failed_jobs = [j for j in result["jobs"] if "error" in j]

            for job in queued_jobs:
                job_id = job["job_id"]
                url = job["url"]
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

            if queued_jobs:
                st.success(f"✅ Queued {len(queued_jobs)} job(s)!")
            if failed_jobs:
                st.warning(f"⚠️ Failed to queue {len(failed_jobs)} job(s)")

            if auto_clear:
                st.session_state.url_text = ""
            st.session_state.last_poll = 0
            time.sleep(0.3)
            st.rerun()
        else:
            st.error(f"Error: {result.get('error', 'unknown error')}")

st.divider()

# ============================================================================
# LIVE PIPELINE STATUS
# ============================================================================
st.subheader("📋 Live Pipeline Status")

if not st.session_state.jobs:
    st.info("👋 No jobs yet. Paste some URLs above to get started!")
else:
    # Get active jobs
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

    # Poll for updates - CRITICAL FIX: Always get detailed status
    if should_refresh or refresh_btn:
        with st.spinner(f"Polling {len(active_jobs)} active job(s)..."):
            for job_id in active_jobs:
                # Get detailed status for EACH active job
                status_data = poll_job_status(job_id)

                if job_id not in st.session_state.jobs:
                    continue

                job = st.session_state.jobs[job_id]

                # Update with detailed info
                raw_status = status_data.get("status", "unknown")
                job["status"] = normalize_status(raw_status)
                job["stage"] = status_data.get("stage", job.get("stage", "queued"))
                job["progress"] = status_data.get("progress", job.get("progress", 0))

                # Handle completion
                if "result" in status_data and status_data.get("result") is not None:
                    job["result"] = status_data["result"]
                    if isinstance(status_data["result"], dict):
                        job["result_status"] = status_data["result"].get("status")

                # Update result_status from API
                if "result_status" in status_data:
                    job["result_status"] = status_data["result_status"]

                if job["status"] == "completed" and "completed_at" not in job:
                    job["completed_at"] = datetime.now().strftime("%H:%M:%S")

            st.session_state.last_poll = time.time()
        st.rerun()

    # Display jobs
    for i, (job_id, job) in enumerate(st.session_state.jobs.items(), start=1):
        status = job["status"]
        stage = job.get("stage", "")
        progress = job.get("progress", 0)
        url = job["url"]
        result_status = job.get("result_status")

        with st.container():
            st.markdown(f"#### Job #{i}")

            # Header
            col_header, col_status = st.columns([3, 1])

            with col_header:
                display_url = url if len(url) <= 60 else url[:57] + "..."
                st.markdown(f"[{display_url}]({url})")

            with col_status:
                # Status display with result context
                if status == "completed":
                    if result_status == "success":
                        st.markdown("**✅ Success**")
                    elif result_status == "duplicate":
                        st.markdown("**🔄 Duplicate**")
                    elif result_status == "unavailable":
                        st.markdown("**🚫 Unavailable**")
                    elif result_status == "visa_restricted":
                        st.markdown("**🛂 Visa Issue**")
                    else:
                        st.markdown("**✅ Completed**")
                elif status == "failed":
                    st.markdown("**❌ Failed**")
                elif status == "processing":
                    st.markdown("**🔄 Processing**")
                else:
                    st.markdown("**⏳ Queued**")

            # Pipeline visual
            stage_visual = get_stage_visual_for_job(job)
            st.markdown(stage_visual)

            # Progress bar
            if status in ["processing", "queued", "pending"]:
                display_progress = progress
                if stage in STAGE_CONFIG:
                    display_progress = max(progress, STAGE_CONFIG[stage]["progress"])

                if display_progress > 0:
                    progress_fraction = min(max(display_progress / 100.0, 0.0), 1.0)
                    stage_label = STAGE_CONFIG.get(stage, {}).get(
                        "label", str(stage).replace("_", " ").title()
                    )
                    st.progress(
                        progress_fraction, text=f"{display_progress}% - {stage_label}"
                    )

            # Details expander
            with st.expander("📄 Details"):
                col1, col2, col3 = st.columns(3)

                with col1:
                    st.write(f"**Job ID:** `{job_id[:12]}...`")
                    st.write(f"**Added:** {job.get('added_at', 'N/A')}")
                    stage_label = STAGE_CONFIG.get(stage, {}).get(
                        "label", str(stage).replace("_", " ").title()
                    )
                    st.write(f"**Stage:** {stage_label}")
                    if job.get("completed_at"):
                        st.write(f"**Completed:** {job.get('completed_at')}")

                with col2:
                    st.write(f"**Status:** {status.title()}")
                    st.write(f"**Progress:** {progress}%")
                    mode = "Playwright" if job.get("force_playwright") else "Crawl4AI"
                    st.write(f"**Mode:** {mode}")

                with col3:
                    if status == "failed":
                        if st.button(f"🔄 Retry", key=f"retry_{job_id}"):
                            with st.spinner("Re-queueing..."):
                                result = retry_job(
                                    url, job.get("force_playwright", False)
                                )
                                if "job_id" in result:
                                    new_job_id = result["job_id"]
                                    del st.session_state.jobs[job_id]
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
                                    st.success("✅ Re-queued!")
                                    st.session_state.last_poll = 0
                                    time.sleep(0.2)
                                    st.rerun()

                # Results for completed jobs
                if status == "completed" and job.get("result"):
                    result = job["result"]
                    st.divider()

                    if result_status == "success":
                        st.success("✅ Successfully processed!")

                        if "job_info" in result:
                            info = result["job_info"]
                            st.write(f"**Title:** {info.get('title', 'N/A')}")
                            st.write(f"**Company:** {info.get('company', 'N/A')}")
                            st.write(f"**Location:** {info.get('location', 'N/A')}")

                        if "evaluation" in result:
                            match = result["evaluation"].get("match_score", 0)
                            st.write(f"**Match Score:** {match}%")

                        if result.get("resume_tailored") and result.get(
                            "resume_pdf_url"
                        ):
                            st.markdown(f"[📄 Resume PDF]({result['resume_pdf_url']})")

                        if result.get("cover_letter_tailored") and result.get(
                            "cover_letter_pdf_url"
                        ):
                            st.markdown(
                                f"[✉️ Cover Letter PDF]({result['cover_letter_pdf_url']})"
                            )

                        if "notion" in result and result["notion"].get("url"):
                            st.markdown(
                                f"[📝 View in Notion]({result['notion']['url']})"
                            )

                    elif result_status == "duplicate":
                        st.warning("🔄 Already processed")
                        if result.get("notion_url"):
                            st.markdown(f"[📝 View entry]({result['notion_url']})")

                    elif result_status == "unavailable":
                        st.warning("🚫 Job no longer available")
                        if result.get("reason"):
                            st.write(f"**Reason:** {result['reason']}")

                    elif result_status == "visa_restricted":
                        st.warning("🛂 Visa sponsorship unavailable")
                        if result.get("reason"):
                            st.write(f"**Details:** {result['reason']}")

                elif status == "failed":
                    st.error("❌ Processing failed")
                    if job.get("error"):
                        st.write(f"**Error:** {job['error']}")

            st.divider()

    # Status indicator
    if st.session_state.auto_refresh and active_jobs:
        last_poll_time = datetime.fromtimestamp(st.session_state.last_poll).strftime(
            "%H:%M:%S"
        )
        st.caption(
            f"🔄 Auto-refresh: 3s | {len(active_jobs)} active | Last: {last_poll_time}"
        )
    elif not active_jobs and total_jobs > 0:
        st.caption("✅ All jobs completed!")

st.divider()
st.caption(
    "💡 Queue up to 100 jobs at once! Processing runs in parallel. Auto-refresh every 3 seconds."
)
