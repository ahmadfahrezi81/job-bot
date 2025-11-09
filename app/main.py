# app/main.py
from fastapi import FastAPI
import logging
import os

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# # Set up logging
# logging.basicConfig(
#     level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
# )

# Set up logging level from environment
log_level = os.getenv("LOG_LEVEL", "INFO").upper()

# Defensive map (avoids invalid strings breaking logging)
LOG_LEVELS = {
    "CRITICAL": logging.CRITICAL,
    "ERROR": logging.ERROR,
    "WARNING": logging.WARNING,
    "INFO": logging.INFO,
    "DEBUG": logging.DEBUG,
}

logging.basicConfig(
    level=LOG_LEVELS.get(log_level, logging.INFO),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

print(f"🔧 Logging level set to: {log_level}")


app = FastAPI(title="Job Bot API")

from app.routes import router

app.include_router(router)


@app.get("/ping")
def ping():
    return {"message": "pong 👋"}
