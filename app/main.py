# app/main.py
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
