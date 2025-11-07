# notion_test_httpx_async.py
import os, json, asyncio, httpx
from dotenv import load_dotenv

load_dotenv()

NOTION_API_KEY = os.getenv("NOTION_API_KEY")
DATABASE_ID = os.getenv("NOTION_DATABASE_ID")


async def test_query():
    async with httpx.AsyncClient(timeout=10.0) as client:
        url = f"https://api.notion.com/v1/databases/{DATABASE_ID}/query"
        payload = {
            "filter": {
                "property": "Job Posting",
                "url": {
                    "equals": "https://phf.tbe.taleo.net/phf01/ats/careers/v2/viewRequisition?org=HKTDC&cws=45&rid=3419"
                },
            },
            "page_size": 1,
        }
        headers = {
            "Authorization": f"Bearer {NOTION_API_KEY}",
            "Content-Type": "application/json",
            "Notion-Version": "2022-06-28",
        }
        resp = await client.post(url, headers=headers, json=payload)
        print("status:", resp.status_code)
        print("resp:", resp.text)


asyncio.run(test_query())
