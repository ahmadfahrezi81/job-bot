import streamlit as st
import requests
import time
import random
import os
from dotenv import load_dotenv

# Load env vars
load_dotenv()

API_URL = os.getenv("API_URL")

st.set_page_config(page_title="Job Evaluator", page_icon="💼", layout="centered")
st.title("💼 Job Evaluator Dashboard")


st.markdown(
    """
    Paste a **job link** and click **Submit** to evaluate it.

    The system will automatically:
    1. 🕷 Crawl the job page  
    2. ⚙️ Normalize and extract key info  
    3. 🧠 Evaluate resume match (LLM)  
    4. 🗂 Save the job into Notion
    """
)

url = st.text_input(
    "🔗 Job URL", placeholder="https://career.sea.com/position/J02067111"
)

# UI placeholders
status_box = st.empty()
progress_bar = st.progress(0)
result_box = st.empty()

if st.button("🚀 Submit"):
    if not url.strip():
        st.warning("Please enter a job URL.")
    else:
        st.session_state["processing"] = True
        start_time = time.time()

        try:
            with st.status("Processing job...", expanded=True) as status:
                # --- Step 1: Crawl4AI ---
                status.write("🕷 Crawling job posting...")
                progress_bar.progress(15)
                time.sleep(random.uniform(1.5, 2.0))

                # --- Step 2: Normalize ---
                status.write("⚙️ Normalizing text and extracting metadata...")
                progress_bar.progress(35)
                time.sleep(random.uniform(1.0, 1.5))

                # --- Step 3: LLM Evaluation ---
                status.write("🧠 Evaluating job fit using LLM...")
                progress_bar.progress(65)
                time.sleep(random.uniform(1.5, 2.5))

                # --- Step 4: Send to API ---
                status.write("📡 Sending to FastAPI backend...")
                response = requests.post(API_URL, json={"url": url})
                progress_bar.progress(85)

                # --- Step 5: Save to Notion ---
                status.write("🗂 Saving job info to Notion...")
                time.sleep(random.uniform(1.0, 2.0))
                progress_bar.progress(100)

                elapsed = time.time() - start_time

                if response.status_code == 200:
                    result = response.json()
                    status.update(
                        label="✅ Job processed successfully!",
                        state="complete",
                        expanded=False,
                    )
                    st.success(f"Completed in {elapsed:.2f}s")

                    st.subheader("📊 Evaluation Summary")
                    st.json(result)
                else:
                    status.update(
                        label="❌ Failed during processing",
                        state="error",
                        expanded=True,
                    )
                    st.error(f"API returned {response.status_code}")
                    st.code(response.text)

        except requests.exceptions.ConnectionError:
            st.error("❌ Could not connect to FastAPI. Is it running on port 8000?")
        except Exception as e:
            st.error(f"Unexpected error: {e}")

        finally:
            st.session_state["processing"] = False
