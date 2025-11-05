# app/main.py
import subprocess
import os

# ✅ Ensure Playwright Chromium is installed at runtime (Render fix)
try:
    if not os.path.exists("/opt/render/.cache/ms-playwright/chromium-1187"):
        print("Installing Playwright Chromium browser...")
        subprocess.run(["playwright", "install", "chromium", "--with-deps"], check=True)
    else:
        print("Playwright Chromium already installed.")
except Exception as e:
    print(f"⚠️ Playwright install check failed: {e}")

from fastapi import FastAPI
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

app = FastAPI(title="Job Bot API")

from app.routes import router

app.include_router(router)


@app.get("/ping")
def ping():
    return {"message": "pong 👋"}
