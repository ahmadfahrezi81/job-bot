# app/main.py
from fastapi import FastAPI
import logging
import os

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Optional: log them once (safe, only partial token)
print(f"🔑 Notion API loaded: {os.getenv('NOTION_API_KEY')[:8]}...")
print(f"🗂️ Database ID loaded: {os.getenv('NOTION_DATABASE_ID')}")


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
