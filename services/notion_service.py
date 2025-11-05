# services/notion_service.py
from notion_client import AsyncClient
import logging
import os
from datetime import datetime

logger = logging.getLogger(__name__)

notion = AsyncClient(auth=os.getenv("NOTION_API_KEY"))
DATABASE_ID = os.getenv("NOTION_DATABASE_ID")


async def save_job_to_notion(job_data: dict) -> dict:
    """
    Saves evaluated job to Notion database with new format.

    Expected job_data structure:
    {
        "url": "...",
        "title": "Job Title @ Company",
        "location": "...",
        "work_mode": "Remote/Hybrid/Onsite",
        "evaluation": {
            "match_score": 75,
            "summary": "...",
            "strengths": [...],  # 3-5 items
            "gaps": [...],  # 3-5 items
            "story_assessment": "Strong — explanation",
            "visa_warning": "✅/⚠️/🚫 message"
        }
    }
    """
    logger.info(f"Saving job to Notion: {job_data['title']}")

    try:
        # Extract company from title (basic heuristic)
        title = job_data["title"]
        company = title.split("@")[-1].strip() if "@" in title else "Unknown"
        job_name = title.split("@")[0].strip() if "@" in title else title

        eval_data = job_data["evaluation"]
        location = job_data.get("location", "Not specified")
        work_mode = job_data.get("work_mode", "Not specified")

        # Build the page content as ONE cohesive "Honest Evaluation" section
        content_blocks = [
            # Main heading
            {
                "object": "block",
                "type": "heading_2",
                "heading_2": {
                    "rich_text": [
                        {"type": "text", "text": {"content": "📊 1. Honest Evaluation"}}
                    ]
                },
            },
            # Match Score
            {
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [
                        {
                            "type": "text",
                            "text": {"content": "Match Score: "},
                            "annotations": {"bold": True},
                        },
                        {
                            "type": "text",
                            "text": {"content": f"{eval_data.get('match_score', 0)}%"},
                        },
                    ]
                },
            },
            # Summary of Fit
            {
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [
                        {
                            "type": "text",
                            "text": {"content": "Summary of Fit:\n"},
                            "annotations": {"bold": True},
                        },
                        {
                            "type": "text",
                            "text": {"content": eval_data.get("summary", "")},
                        },
                    ]
                },
            },
            # Key Strengths heading
            {
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [
                        {
                            "type": "text",
                            "text": {"content": "\nKey Strengths"},
                            "annotations": {"bold": True},
                        }
                    ]
                },
            },
        ]

        # Add strengths as numbered list
        for idx, strength in enumerate(eval_data.get("strengths", []), 1):
            content_blocks.append(
                {
                    "object": "block",
                    "type": "numbered_list_item",
                    "numbered_list_item": {
                        "rich_text": [{"type": "text", "text": {"content": strength}}]
                    },
                }
            )

        # Gaps/Weaknesses heading
        content_blocks.append(
            {
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [
                        {
                            "type": "text",
                            "text": {"content": "\nGaps / Weaknesses"},
                            "annotations": {"bold": True},
                        }
                    ]
                },
            }
        )

        # Add gaps as numbered list
        for idx, gap in enumerate(eval_data.get("gaps", []), 1):
            content_blocks.append(
                {
                    "object": "block",
                    "type": "numbered_list_item",
                    "numbered_list_item": {
                        "rich_text": [{"type": "text", "text": {"content": gap}}]
                    },
                }
            )

        # Story Assessment
        content_blocks.append(
            {
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [
                        {
                            "type": "text",
                            "text": {"content": "\nStory Assessment: "},
                            "annotations": {"bold": True},
                        },
                        {
                            "type": "text",
                            "text": {
                                "content": eval_data.get("story_assessment", "N/A")
                            },
                        },
                    ]
                },
            }
        )

        # Visa Check
        content_blocks.append(
            {
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [
                        {
                            "type": "text",
                            "text": {"content": "\nVisa Check: "},
                            "annotations": {"bold": True},
                        },
                        {
                            "type": "text",
                            "text": {"content": eval_data.get("visa_warning", "N/A")},
                        },
                    ]
                },
            }
        )

        # Create Notion page with updated properties
        response = await notion.pages.create(
            parent={"database_id": DATABASE_ID},
            properties={
                "Position": {"title": [{"text": {"content": job_name}}]},
                "Company": {"rich_text": [{"text": {"content": company}}]},
                "Job Posting": {"url": job_data["url"]},
                "Match Score": {"number": eval_data.get("match_score", 0) / 100},
                "Stage": {"select": {"name": "Saved"}},  # Default to Saved
                "Work Mode": {"select": {"name": work_mode or "Not specified"}},
                "location": {"rich_text": [{"text": {"content": location}}]},
                "Outcome": {"select": {"name": "Active"}},  # Default to Active
                # "Date Added": {"date": {"start": datetime.now().isoformat()}},
            },
            children=content_blocks,
        )

        logger.info(f"Successfully saved to Notion: {response['id']}")

        return {"notion_page_id": response["id"], "notion_url": response["url"]}

    except Exception as e:
        logger.error(f"Failed to save to Notion: {str(e)}")
        raise Exception(f"Notion save failed: {str(e)}")
