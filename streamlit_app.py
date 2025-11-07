import streamlit as st
import requests
import time
import os
from dotenv import load_dotenv
import pandas as pd
from datetime import datetime

# Load environment variables
load_dotenv()
API_URL = os.getenv("API_URL", "http://localhost:8000/jobs/add")

# Streamlit page config
st.set_page_config(page_title="Job Evaluator", page_icon="💼", layout="wide")

# Initialize session state
if "results" not in st.session_state:
    st.session_state.results = []
if "processing" not in st.session_state:
    st.session_state.processing = False

st.title("💼 Job Evaluator Dashboard")

st.markdown(
    """
    Paste **multiple job links** (one per line) and the system will automatically:
    1. 🔍 Check for duplicates in Notion
    2. 🕷️ Crawl the job page (Crawl4AI → Playwright fallback)
    3. 🚫 Filter out unavailable jobs & visa restrictions
    4. 🧠 Evaluate resume match with LLM
    5. 🗂️ Save qualified jobs to Notion
    """
)

# Sidebar stats
with st.sidebar:
    st.header("📊 Session Stats")
    if st.session_state.results:
        total = len(st.session_state.results)
        success = sum(1 for r in st.session_state.results if r["status"] == "success")
        duplicates = sum(
            1 for r in st.session_state.results if r["status"] == "duplicate"
        )
        unavailable = sum(
            1 for r in st.session_state.results if r["status"] == "unavailable"
        )
        visa_restricted = sum(
            1 for r in st.session_state.results if r["status"] == "visa_restricted"
        )
        failed = sum(1 for r in st.session_state.results if r["status"] == "error")

        col1, col2 = st.columns(2)
        with col1:
            st.metric("Total Processed", total)
            st.metric("✅ Success", success)
            st.metric("🔄 Duplicates", duplicates)
        with col2:
            st.metric("🚫 Unavailable", unavailable)
            st.metric("🛂 Visa Restricted", visa_restricted)
            st.metric("❌ Errors", failed)
    else:
        st.info("No jobs processed yet")

    if st.button("🗑️ Clear Results", type="secondary", use_container_width=True):
        st.session_state.results = []
        st.rerun()

# Main input area
st.subheader("📝 Input Job URLs")
urls_input = st.text_area(
    "Enter job URLs (one per line)",
    placeholder="https://jobs.lever.co/company/job-id-1\nhttps://greenhouse.io/company/job-id-2\nhttps://workday.com/company/job-id-3",
    height=150,
    help="Paste multiple job URLs, each on a new line. The system will process them sequentially.",
)

# Parse URLs
urls = [
    url.strip()
    for url in urls_input.split("\n")
    if url.strip() and url.strip().startswith("http")
]

# Display URL count
if urls:
    st.info(f"📋 Found {len(urls)} valid URL(s) to process")

# Submit button
col1, col2, col3 = st.columns([1, 1, 2])
with col1:
    submit_button = st.button(
        "🚀 Process Jobs",
        type="primary",
        disabled=not urls or st.session_state.processing,
        use_container_width=True,
    )
with col2:
    force_playwright = st.checkbox(
        "🔧 Force Playwright", help="Skip Crawl4AI and use Playwright directly"
    )

# Processing logic
if submit_button and urls:
    st.session_state.processing = True

    # Progress tracking
    total_jobs = len(urls)
    progress_bar = st.progress(0, text="Starting batch processing...")
    status_container = st.container()

    for idx, url in enumerate(urls):
        current_job = idx + 1
        progress_pct = idx / total_jobs

        with status_container:
            with st.status(
                f"🔄 Processing job {current_job}/{total_jobs}", expanded=True
            ) as status_box:
                try:
                    # Update progress
                    progress_bar.progress(
                        progress_pct,
                        text=f"Processing {current_job}/{total_jobs}: {url[:50]}...",
                    )

                    # Step 1: Check duplicate
                    status_box.write("🔍 Checking for duplicates...")
                    time.sleep(0.1)

                    # Step 2: Start extraction
                    status_box.write("🕷️ Extracting job data...")
                    start_time = time.time()

                    response = requests.post(
                        API_URL,
                        json={"url": url, "force_playwright": force_playwright},
                        timeout=120,  # 2 minutes max per job
                    )

                    elapsed = time.time() - start_time

                    if response.status_code == 200:
                        result = response.json()
                        result_status = result.get("status", "unknown")

                        # Different handling based on status
                        if result_status == "success":
                            status_box.write("🧠 Evaluating match...")
                            time.sleep(0.1)
                            status_box.write("🗂️ Saving to Notion...")
                            status_box.update(
                                label=f"✅ Job {current_job}/{total_jobs} completed!",
                                state="complete",
                            )

                            st.session_state.results.append(
                                {
                                    "url": url,
                                    "status": "success",
                                    "job_title": result.get("job_info", {}).get(
                                        "title", "Unknown"
                                    ),
                                    "company": result.get("job_info", {}).get(
                                        "company", "Unknown"
                                    ),
                                    "match_score": result.get("evaluation", {}).get(
                                        "match_score", 0
                                    ),
                                    "method": result.get(
                                        "extraction_method", "unknown"
                                    ),
                                    "time": f"{elapsed:.1f}s",
                                    "notion_url": result.get("notion", {}).get(
                                        "notion_url", ""
                                    ),
                                    "message": "Successfully saved to Notion",
                                    "timestamp": datetime.now().strftime("%H:%M:%S"),
                                }
                            )

                        elif result_status == "duplicate":
                            status_box.update(
                                label=f"🔄 Job {current_job}/{total_jobs} - Duplicate found",
                                state="complete",
                            )
                            st.session_state.results.append(
                                {
                                    "url": url,
                                    "status": "duplicate",
                                    "job_title": result.get("job_title", "Unknown"),
                                    "company": "",
                                    "match_score": "",
                                    "method": "duplicate_check",
                                    "time": f"{elapsed:.1f}s",
                                    "notion_url": result.get("notion_url", ""),
                                    "message": result.get(
                                        "message", "Already exists in Notion"
                                    ),
                                    "timestamp": datetime.now().strftime("%H:%M:%S"),
                                }
                            )

                        elif result_status == "unavailable":
                            status_box.update(
                                label=f"🚫 Job {current_job}/{total_jobs} - Job unavailable",
                                state="complete",
                            )
                            st.session_state.results.append(
                                {
                                    "url": url,
                                    "status": "unavailable",
                                    "job_title": "N/A",
                                    "company": "",
                                    "match_score": "",
                                    "method": "early_exit",
                                    "time": f"{elapsed:.1f}s",
                                    "notion_url": "",
                                    "message": result.get(
                                        "reason", "Job posting closed or filled"
                                    ),
                                    "timestamp": datetime.now().strftime("%H:%M:%S"),
                                }
                            )

                        elif result_status == "visa_restricted":
                            status_box.update(
                                label=f"🛂 Job {current_job}/{total_jobs} - Visa restricted",
                                state="complete",
                            )
                            st.session_state.results.append(
                                {
                                    "url": url,
                                    "status": "visa_restricted",
                                    "job_title": "N/A",
                                    "company": "",
                                    "match_score": "",
                                    "method": "early_exit",
                                    "time": f"{elapsed:.1f}s",
                                    "notion_url": "",
                                    "message": result.get(
                                        "reason", "Visa sponsorship not available"
                                    ),
                                    "timestamp": datetime.now().strftime("%H:%M:%S"),
                                }
                            )
                    else:
                        # API error
                        status_box.update(
                            label=f"❌ Job {current_job}/{total_jobs} - Error",
                            state="error",
                        )
                        st.session_state.results.append(
                            {
                                "url": url,
                                "status": "error",
                                "job_title": "Error",
                                "company": "",
                                "match_score": "",
                                "method": "failed",
                                "time": f"{elapsed:.1f}s",
                                "notion_url": "",
                                "message": f"API error: {response.status_code}",
                                "timestamp": datetime.now().strftime("%H:%M:%S"),
                            }
                        )

                except requests.exceptions.Timeout:
                    status_box.update(
                        label=f"⏱️ Job {current_job}/{total_jobs} - Timeout",
                        state="error",
                    )
                    st.session_state.results.append(
                        {
                            "url": url,
                            "status": "error",
                            "job_title": "Timeout",
                            "company": "",
                            "match_score": "",
                            "method": "failed",
                            "time": "120s+",
                            "notion_url": "",
                            "message": "Request timeout (>2 minutes)",
                            "timestamp": datetime.now().strftime("%H:%M:%S"),
                        }
                    )

                except requests.exceptions.ConnectionError:
                    status_box.update(
                        label=f"❌ Job {current_job}/{total_jobs} - Connection Error",
                        state="error",
                    )
                    st.session_state.results.append(
                        {
                            "url": url,
                            "status": "error",
                            "job_title": "Connection Error",
                            "company": "",
                            "match_score": "",
                            "method": "failed",
                            "time": "0s",
                            "notion_url": "",
                            "message": "Could not connect to API. Is it running?",
                            "timestamp": datetime.now().strftime("%H:%M:%S"),
                        }
                    )

                except Exception as e:
                    status_box.update(
                        label=f"❌ Job {current_job}/{total_jobs} - Unexpected Error",
                        state="error",
                    )
                    st.session_state.results.append(
                        {
                            "url": url,
                            "status": "error",
                            "job_title": "Error",
                            "company": "",
                            "match_score": "",
                            "method": "failed",
                            "time": "0s",
                            "notion_url": "",
                            "message": str(e),
                            "timestamp": datetime.now().strftime("%H:%M:%S"),
                        }
                    )

    # Final progress
    progress_bar.progress(1.0, text=f"✅ Completed all {total_jobs} jobs!")
    st.session_state.processing = False
    time.sleep(1)
    st.rerun()

# Results table
if st.session_state.results:
    st.subheader("📊 Processing Results")

    # Create DataFrame
    df = pd.DataFrame(st.session_state.results)

    # Add status emoji column
    status_emoji = {
        "success": "✅",
        "duplicate": "🔄",
        "unavailable": "🚫",
        "visa_restricted": "🛂",
        "error": "❌",
    }
    df["Status"] = df["status"].map(status_emoji) + " " + df["status"].str.title()

    # Reorder columns for display
    display_columns = [
        "timestamp",
        "Status",
        "job_title",
        "company",
        "match_score",
        "method",
        "time",
        "message",
    ]
    display_df = df[display_columns].copy()
    display_df.columns = [
        "Time",
        "Status",
        "Job Title",
        "Company",
        "Score",
        "Method",
        "Duration",
        "Details",
    ]

    # Style the dataframe
    def highlight_status(row):
        if "✅" in row["Status"]:
            return ["background-color: #d4edda"] * len(row)
        elif "🔄" in row["Status"]:
            return ["background-color: #d1ecf1"] * len(row)
        elif "🚫" in row["Status"] or "🛂" in row["Status"]:
            return ["background-color: #fff3cd"] * len(row)
        elif "❌" in row["Status"]:
            return ["background-color: #f8d7da"] * len(row)
        return [""] * len(row)

    styled_df = display_df.style.apply(highlight_status, axis=1)
    st.dataframe(styled_df, use_container_width=True, hide_index=True)

    # Download button
    csv = df.to_csv(index=False)
    st.download_button(
        label="📥 Download Results as CSV",
        data=csv,
        file_name=f"job_evaluation_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
        mime="text/csv",
    )

    # Detailed expandable sections for successful jobs
    st.subheader("📋 Detailed Results")
    for result in st.session_state.results:
        if result["status"] == "success":
            with st.expander(
                f"✅ {result['job_title']} - {result['match_score']}% match"
            ):
                col1, col2 = st.columns(2)
                with col1:
                    st.write(f"**Company:** {result['company']}")
                    st.write(f"**Match Score:** {result['match_score']}%")
                    st.write(f"**Extraction Method:** {result['method']}")
                with col2:
                    st.write(f"**Processing Time:** {result['time']}")
                    if result["notion_url"]:
                        st.markdown(f"[🔗 View in Notion]({result['notion_url']})")
                st.code(result["url"], language=None)

st.markdown("---")
st.caption(
    "💡 Tip: You can process up to 20 jobs at once. Each job takes ~5-30 seconds depending on the extraction method."
)
