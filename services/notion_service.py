# # services/notion_service.py
# from notion_client import AsyncClient
# import logging
# import os
# from datetime import datetime

# logger = logging.getLogger(__name__)

# notion = AsyncClient(auth=os.getenv("NOTION_API_KEY"))
# DATABASE_ID = os.getenv("NOTION_DATABASE_ID")


# async def save_job_to_notion(
#     job_data: dict, resume_data: dict = None, pdf_url: str = None
# ) -> dict:
#     """
#     Saves evaluated job to Notion database with evaluation and optional resume tailoring.

#     Expected job_data structure:
#     {
#         "url": "...",
#         "title": "Job Title @ Company",
#         "location": "...",
#         "work_mode": "Remote/Hybrid/Onsite",
#         "evaluation": {
#             "match_score": 75,
#             "summary": "...",
#             "strengths": [...],
#             "gaps": [...],
#             "story_assessment": "Strong – explanation",
#             "visa_warning": "✅/⚠️/🚫 message"
#         }
#     }

#     Args:
#         job_data: Job information and evaluation results
#         resume_data: Optional tailored resume data (if match_score > 70)
#         pdf_url: Optional public URL to compiled PDF resume


#     Optional resume_data structure (if match_score > 70):
#     {
#         "tailored_content": "... LaTeX content ...",
#         "pruning_strategy": {
#             "summary": "...",
#             "scoring_logic": "...",
#             "role_breakdown": "..."
#         },
#         "tech_stack_analysis": {
#             "table": [
#                 {"tech": "...", "assessment": "...", "risk": "Low/Medium/High"}
#             ],
#             "suggested_additions": "..."
#         },
#         "change_summary": {
#             "what_made_cut": "...",
#             "what_removed": "...",
#             "interview_prep": ["point 1", "point 2", ...]
#         }
#     }
#     """
#     logger.info(f"Saving job to Notion: {job_data['title']}")

#     try:
#         # Extract company from title (basic heuristic)
#         title = job_data["title"]
#         company = title.split("@")[-1].strip() if "@" in title else "Unknown"
#         job_name = title.split("@")[0].strip() if "@" in title else title

#         eval_data = job_data["evaluation"]
#         location = job_data.get("location", "Not specified")
#         work_mode = job_data.get("work_mode", "Not specified")

#         # ==========================================
#         # SECTION 1: HONEST EVALUATION
#         # ==========================================
#         content_blocks = [
#             {
#                 "object": "block",
#                 "type": "heading_2",
#                 "heading_2": {
#                     "rich_text": [
#                         {"type": "text", "text": {"content": "📊 1. Honest Evaluation"}}
#                     ]
#                 },
#             },
#             {
#                 "object": "block",
#                 "type": "paragraph",
#                 "paragraph": {
#                     "rich_text": [
#                         {
#                             "type": "text",
#                             "text": {"content": "Match Score: "},
#                             "annotations": {"bold": True},
#                         },
#                         {
#                             "type": "text",
#                             "text": {"content": f"{eval_data.get('match_score', 0)}%"},
#                         },
#                     ]
#                 },
#             },
#             {
#                 "object": "block",
#                 "type": "paragraph",
#                 "paragraph": {
#                     "rich_text": [
#                         {
#                             "type": "text",
#                             "text": {"content": "Summary of Fit:\n"},
#                             "annotations": {"bold": True},
#                         },
#                         {
#                             "type": "text",
#                             "text": {"content": eval_data.get("summary", "")},
#                         },
#                     ]
#                 },
#             },
#             {
#                 "object": "block",
#                 "type": "paragraph",
#                 "paragraph": {
#                     "rich_text": [
#                         {
#                             "type": "text",
#                             "text": {"content": "\nKey Strengths"},
#                             "annotations": {"bold": True},
#                         }
#                     ]
#                 },
#             },
#         ]

#         # Add strengths as numbered list
#         for strength in eval_data.get("strengths", []):
#             content_blocks.append(
#                 {
#                     "object": "block",
#                     "type": "numbered_list_item",
#                     "numbered_list_item": {
#                         "rich_text": [{"type": "text", "text": {"content": strength}}]
#                     },
#                 }
#             )

#         # Gaps/Weaknesses heading
#         content_blocks.append(
#             {
#                 "object": "block",
#                 "type": "paragraph",
#                 "paragraph": {
#                     "rich_text": [
#                         {
#                             "type": "text",
#                             "text": {"content": "\nGaps / Weaknesses"},
#                             "annotations": {"bold": True},
#                         }
#                     ]
#                 },
#             }
#         )

#         # Add gaps as numbered list
#         for gap in eval_data.get("gaps", []):
#             content_blocks.append(
#                 {
#                     "object": "block",
#                     "type": "numbered_list_item",
#                     "numbered_list_item": {
#                         "rich_text": [{"type": "text", "text": {"content": gap}}]
#                     },
#                 }
#             )

#         # Story Assessment
#         content_blocks.append(
#             {
#                 "object": "block",
#                 "type": "paragraph",
#                 "paragraph": {
#                     "rich_text": [
#                         {
#                             "type": "text",
#                             "text": {"content": "\nStory Assessment: "},
#                             "annotations": {"bold": True},
#                         },
#                         {
#                             "type": "text",
#                             "text": {
#                                 "content": eval_data.get("story_assessment", "N/A")
#                             },
#                         },
#                     ]
#                 },
#             }
#         )

#         # Visa Check (if present)
#         if "visa_warning" in eval_data:
#             content_blocks.append(
#                 {
#                     "object": "block",
#                     "type": "paragraph",
#                     "paragraph": {
#                         "rich_text": [
#                             {
#                                 "type": "text",
#                                 "text": {"content": "\nVisa Check: "},
#                                 "annotations": {"bold": True},
#                             },
#                             {
#                                 "type": "text",
#                                 "text": {
#                                     "content": eval_data.get("visa_warning", "N/A")
#                                 },
#                             },
#                         ]
#                     },
#                 }
#             )

#         # ==========================================
#         # SECTION 2: RESUME TAILORING (if provided)
#         # ==========================================
#         if resume_data:
#             logger.info("Adding resume tailoring section to Notion page")

#             pruning = resume_data.get("pruning_strategy", {})
#             tech_stack = resume_data.get("tech_stack_analysis", {})
#             change_summary = resume_data.get("change_summary", {})

#             # --- Section 2 Heading: Bullet Relevance Scoring & Pruning Logic ---
#             content_blocks.extend(
#                 [
#                     {
#                         "object": "block",
#                         "type": "heading_2",
#                         "heading_2": {
#                             "rich_text": [
#                                 {
#                                     "type": "text",
#                                     "text": {
#                                         "content": "📋 2. Bullet Relevance Scoring & Pruning Logic"
#                                     },
#                                 }
#                             ]
#                         },
#                     },
#                     {
#                         "object": "block",
#                         "type": "paragraph",
#                         "paragraph": {
#                             "rich_text": [
#                                 {
#                                     "type": "text",
#                                     "text": {"content": "Summary:\n"},
#                                     "annotations": {"bold": True},
#                                 },
#                                 {
#                                     "type": "text",
#                                     "text": {"content": pruning.get("summary", "N/A")},
#                                 },
#                             ]
#                         },
#                     },
#                     {
#                         "object": "block",
#                         "type": "paragraph",
#                         "paragraph": {
#                             "rich_text": [
#                                 {
#                                     "type": "text",
#                                     "text": {"content": "\nScoring Logic:\n"},
#                                     "annotations": {"bold": True},
#                                 },
#                                 {
#                                     "type": "text",
#                                     "text": {
#                                         "content": pruning.get("scoring_logic", "N/A")
#                                     },
#                                 },
#                             ]
#                         },
#                     },
#                     {
#                         "object": "block",
#                         "type": "paragraph",
#                         "paragraph": {
#                             "rich_text": [
#                                 {
#                                     "type": "text",
#                                     "text": {"content": "\nRole Breakdown:\n"},
#                                     "annotations": {"bold": True},
#                                 },
#                                 {
#                                     "type": "text",
#                                     "text": {
#                                         "content": pruning.get("role_breakdown", "N/A")
#                                     },
#                                 },
#                             ]
#                         },
#                     },
#                 ]
#             )

#             # --- Section 3 Heading: Tech Stack Gap Analysis ---
#             content_blocks.extend(
#                 [
#                     {
#                         "object": "block",
#                         "type": "heading_2",
#                         "heading_2": {
#                             "rich_text": [
#                                 {
#                                     "type": "text",
#                                     "text": {
#                                         "content": "🔍 3. Tech Stack Gap Analysis"
#                                     },
#                                 }
#                             ]
#                         },
#                     },
#                 ]
#             )

#             # Add tech stack table
#             tech_table = tech_stack.get("table", [])
#             if tech_table:
#                 # Create table header
#                 content_blocks.append(
#                     {
#                         "object": "block",
#                         "type": "table",
#                         "table": {
#                             "table_width": 3,
#                             "has_column_header": True,
#                             "has_row_header": False,
#                             "children": [
#                                 # Header row
#                                 {
#                                     "type": "table_row",
#                                     "table_row": {
#                                         "cells": [
#                                             [
#                                                 {
#                                                     "type": "text",
#                                                     "text": {"content": "Tech"},
#                                                     "annotations": {"bold": True},
#                                                 }
#                                             ],
#                                             [
#                                                 {
#                                                     "type": "text",
#                                                     "text": {"content": "Assessment"},
#                                                     "annotations": {"bold": True},
#                                                 }
#                                             ],
#                                             [
#                                                 {
#                                                     "type": "text",
#                                                     "text": {"content": "Risk"},
#                                                     "annotations": {"bold": True},
#                                                 }
#                                             ],
#                                         ]
#                                     },
#                                 },
#                                 # Data rows
#                                 *[
#                                     {
#                                         "type": "table_row",
#                                         "table_row": {
#                                             "cells": [
#                                                 [
#                                                     {
#                                                         "type": "text",
#                                                         "text": {
#                                                             "content": row.get(
#                                                                 "tech", ""
#                                                             )
#                                                         },
#                                                     }
#                                                 ],
#                                                 [
#                                                     {
#                                                         "type": "text",
#                                                         "text": {
#                                                             "content": row.get(
#                                                                 "assessment", ""
#                                                             )
#                                                         },
#                                                     }
#                                                 ],
#                                                 [
#                                                     {
#                                                         "type": "text",
#                                                         "text": {
#                                                             "content": row.get(
#                                                                 "risk", ""
#                                                             )
#                                                         },
#                                                     }
#                                                 ],
#                                             ]
#                                         },
#                                     }
#                                     for row in tech_table
#                                 ],
#                             ],
#                         },
#                     }
#                 )

#             # Suggested additions
#             content_blocks.append(
#                 {
#                     "object": "block",
#                     "type": "paragraph",
#                     "paragraph": {
#                         "rich_text": [
#                             {
#                                 "type": "text",
#                                 "text": {"content": "\nSuggested Additions:\n"},
#                                 "annotations": {"bold": True},
#                             },
#                             {
#                                 "type": "text",
#                                 "text": {
#                                     "content": tech_stack.get(
#                                         "suggested_additions", "N/A"
#                                     )
#                                 },
#                             },
#                         ]
#                     },
#                 }
#             )

#             # --- Section 4 Heading: Optimized Resume Content ---
#             content_blocks.extend(
#                 [
#                     {
#                         "object": "block",
#                         "type": "heading_2",
#                         "heading_2": {
#                             "rich_text": [
#                                 {
#                                     "type": "text",
#                                     "text": {
#                                         "content": "📄 4. Optimized Resume Content"
#                                     },
#                                 }
#                             ]
#                         },
#                     },
#                 ]
#             )

#             # Add tailored resume as code block
#             tailored_content = resume_data.get("tailored_content", "")
#             chunk_size = 1900
#             rich_text_items = []

#             for i in range(0, len(tailored_content), chunk_size):
#                 chunk = tailored_content[i : i + chunk_size]
#                 rich_text_items.append({"type": "text", "text": {"content": chunk}})

#             content_blocks.append(
#                 {
#                     "object": "block",
#                     "type": "code",
#                     "code": {
#                         "rich_text": rich_text_items,
#                         "language": "latex",
#                     },
#                 }
#             )

#             # --- Section 5 Heading: Change Summary ---
#             content_blocks.extend(
#                 [
#                     {
#                         "object": "block",
#                         "type": "heading_2",
#                         "heading_2": {
#                             "rich_text": [
#                                 {
#                                     "type": "text",
#                                     "text": {"content": "📋 5. Change Summary"},
#                                 }
#                             ]
#                         },
#                     },
#                     {
#                         "object": "block",
#                         "type": "paragraph",
#                         "paragraph": {
#                             "rich_text": [
#                                 {
#                                     "type": "text",
#                                     "text": {"content": "✅ What Made the Cut:\n"},
#                                     "annotations": {"bold": True},
#                                 },
#                                 {
#                                     "type": "text",
#                                     "text": {
#                                         "content": change_summary.get(
#                                             "what_made_cut", "N/A"
#                                         )
#                                     },
#                                 },
#                             ]
#                         },
#                     },
#                     {
#                         "object": "block",
#                         "type": "paragraph",
#                         "paragraph": {
#                             "rich_text": [
#                                 {
#                                     "type": "text",
#                                     "text": {"content": "\n✂️ What Was Removed:\n"},
#                                     "annotations": {"bold": True},
#                                 },
#                                 {
#                                     "type": "text",
#                                     "text": {
#                                         "content": change_summary.get(
#                                             "what_removed", "N/A"
#                                         )
#                                     },
#                                 },
#                             ]
#                         },
#                     },
#                     {
#                         "object": "block",
#                         "type": "paragraph",
#                         "paragraph": {
#                             "rich_text": [
#                                 {
#                                     "type": "text",
#                                     "text": {"content": "\n🎯 Interview Prep:"},
#                                     "annotations": {"bold": True},
#                                 }
#                             ]
#                         },
#                     },
#                 ]
#             )

#             # Add interview prep as numbered list
#             interview_prep = change_summary.get("interview_prep", [])
#             if isinstance(interview_prep, list):
#                 for point in interview_prep:
#                     content_blocks.append(
#                         {
#                             "object": "block",
#                             "type": "numbered_list_item",
#                             "numbered_list_item": {
#                                 "rich_text": [
#                                     {"type": "text", "text": {"content": point}}
#                                 ]
#                             },
#                         }
#                     )
#             else:
#                 # Fallback if interview_prep is a string
#                 content_blocks.append(
#                     {
#                         "object": "block",
#                         "type": "paragraph",
#                         "paragraph": {
#                             "rich_text": [
#                                 {"type": "text", "text": {"content": interview_prep}}
#                             ]
#                         },
#                     }
#                 )

#             # Add PDF download link if available
#             if pdf_url:
#                 logger.info(f"📎 Adding PDF URL to Notion: {pdf_url}")
#                 content_blocks.extend(
#                     [
#                         {
#                             "object": "block",
#                             "type": "heading_3",
#                             "heading_3": {
#                                 "rich_text": [
#                                     {
#                                         "type": "text",
#                                         "text": {
#                                             "content": "📥 Download Tailored Resume"
#                                         },
#                                     }
#                                 ]
#                             },
#                         },
#                         {
#                             "object": "block",
#                             "type": "file",
#                             "file": {
#                                 "type": "external",
#                                 "external": {"url": pdf_url},
#                             },
#                         },
#                     ]
#                 )

#         # ==========================================
#         # CREATE NOTION PAGE
#         # ==========================================
#         response = await notion.pages.create(
#             parent={"database_id": DATABASE_ID},
#             properties={
#                 "Position": {"title": [{"text": {"content": job_name}}]},
#                 "Company": {"rich_text": [{"text": {"content": company}}]},
#                 "Job Posting": {"url": job_data["url"]},
#                 "Match Score": {"number": eval_data.get("match_score", 0) / 100},
#                 "Stage": {"select": {"name": "Saved"}},
#                 "Work Mode": {"select": {"name": work_mode or "Not specified"}},
#                 "location": {"rich_text": [{"text": {"content": location}}]},
#                 "Outcome": {"select": {"name": "Active"}},
#             },
#             children=content_blocks,
#         )

#         logger.info(f"✅ Successfully saved to Notion: {response['id']}")

#         return {"notion_page_id": response["id"], "notion_url": response["url"]}

#     except Exception as e:
#         logger.error(f"Failed to save to Notion: {str(e)}")
#         raise Exception(f"Notion save failed: {str(e)}")

# services/notion_service.py
from notion_client import AsyncClient
import logging
import os
from datetime import datetime

logger = logging.getLogger(__name__)

notion = AsyncClient(auth=os.getenv("NOTION_API_KEY"))
DATABASE_ID = os.getenv("NOTION_DATABASE_ID")


async def save_job_to_notion(
    job_data: dict,
    resume_data: dict = None,
    pdf_url: str = None,
    cover_letter_data: dict = None,
    cover_letter_pdf_url: str = None,
) -> dict:
    """
    Saves evaluated job to Notion database with evaluation and optional resume + cover letter tailoring.

    Expected job_data structure:
    {
        "url": "...",
        "title": "Job Title @ Company",
        "location": "...",
        "work_mode": "Remote/Hybrid/Onsite",
        "evaluation": {
            "match_score": 75,
            "summary": "...",
            "strengths": [...],
            "gaps": [...],
            "story_assessment": "Strong – explanation",
            "visa_warning": "✅/⚠️/🚫 message"
        }
    }

    Args:
        job_data: Job information and evaluation results
        resume_data: Optional tailored resume data (if match_score > 70)
        pdf_url: Optional public URL to compiled PDF resume
        cover_letter_data: Optional tailored cover letter data (if match_score > 70)
        cover_letter_pdf_url: Optional public URL to compiled PDF cover letter
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

        # ==========================================
        # SECTION 1: HONEST EVALUATION
        # ==========================================
        content_blocks = [
            {
                "object": "block",
                "type": "heading_2",
                "heading_2": {
                    "rich_text": [
                        {"type": "text", "text": {"content": "📊 1. Honest Evaluation"}}
                    ]
                },
            },
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
        for strength in eval_data.get("strengths", []):
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
        for gap in eval_data.get("gaps", []):
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

        # Visa Check (if present)
        if "visa_warning" in eval_data:
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
                                "text": {
                                    "content": eval_data.get("visa_warning", "N/A")
                                },
                            },
                        ]
                    },
                }
            )

        # ==========================================
        # SECTION 2-5: RESUME TAILORING (if provided)
        # ==========================================
        if resume_data:
            logger.info("Adding resume tailoring section to Notion page")

            pruning = resume_data.get("pruning_strategy", {})
            tech_stack = resume_data.get("tech_stack_analysis", {})
            change_summary = resume_data.get("change_summary", {})

            # --- Section 2 Heading: Bullet Relevance Scoring & Pruning Logic ---
            content_blocks.extend(
                [
                    {
                        "object": "block",
                        "type": "heading_2",
                        "heading_2": {
                            "rich_text": [
                                {
                                    "type": "text",
                                    "text": {
                                        "content": "📋 2. Bullet Relevance Scoring & Pruning Logic"
                                    },
                                }
                            ]
                        },
                    },
                    {
                        "object": "block",
                        "type": "paragraph",
                        "paragraph": {
                            "rich_text": [
                                {
                                    "type": "text",
                                    "text": {"content": "Summary:\n"},
                                    "annotations": {"bold": True},
                                },
                                {
                                    "type": "text",
                                    "text": {"content": pruning.get("summary", "N/A")},
                                },
                            ]
                        },
                    },
                    {
                        "object": "block",
                        "type": "paragraph",
                        "paragraph": {
                            "rich_text": [
                                {
                                    "type": "text",
                                    "text": {"content": "\nScoring Logic:\n"},
                                    "annotations": {"bold": True},
                                },
                                {
                                    "type": "text",
                                    "text": {
                                        "content": pruning.get("scoring_logic", "N/A")
                                    },
                                },
                            ]
                        },
                    },
                    {
                        "object": "block",
                        "type": "paragraph",
                        "paragraph": {
                            "rich_text": [
                                {
                                    "type": "text",
                                    "text": {"content": "\nRole Breakdown:\n"},
                                    "annotations": {"bold": True},
                                },
                                {
                                    "type": "text",
                                    "text": {
                                        "content": pruning.get("role_breakdown", "N/A")
                                    },
                                },
                            ]
                        },
                    },
                ]
            )

            # --- Section 3 Heading: Tech Stack Gap Analysis ---
            content_blocks.extend(
                [
                    {
                        "object": "block",
                        "type": "heading_2",
                        "heading_2": {
                            "rich_text": [
                                {
                                    "type": "text",
                                    "text": {
                                        "content": "🔍 3. Tech Stack Gap Analysis"
                                    },
                                }
                            ]
                        },
                    },
                ]
            )

            # Add tech stack table
            tech_table = tech_stack.get("table", [])
            if tech_table:
                # Create table header
                content_blocks.append(
                    {
                        "object": "block",
                        "type": "table",
                        "table": {
                            "table_width": 3,
                            "has_column_header": True,
                            "has_row_header": False,
                            "children": [
                                # Header row
                                {
                                    "type": "table_row",
                                    "table_row": {
                                        "cells": [
                                            [
                                                {
                                                    "type": "text",
                                                    "text": {"content": "Tech"},
                                                    "annotations": {"bold": True},
                                                }
                                            ],
                                            [
                                                {
                                                    "type": "text",
                                                    "text": {"content": "Assessment"},
                                                    "annotations": {"bold": True},
                                                }
                                            ],
                                            [
                                                {
                                                    "type": "text",
                                                    "text": {"content": "Risk"},
                                                    "annotations": {"bold": True},
                                                }
                                            ],
                                        ]
                                    },
                                },
                                # Data rows
                                *[
                                    {
                                        "type": "table_row",
                                        "table_row": {
                                            "cells": [
                                                [
                                                    {
                                                        "type": "text",
                                                        "text": {
                                                            "content": row.get(
                                                                "tech", ""
                                                            )
                                                        },
                                                    }
                                                ],
                                                [
                                                    {
                                                        "type": "text",
                                                        "text": {
                                                            "content": row.get(
                                                                "assessment", ""
                                                            )
                                                        },
                                                    }
                                                ],
                                                [
                                                    {
                                                        "type": "text",
                                                        "text": {
                                                            "content": row.get(
                                                                "risk", ""
                                                            )
                                                        },
                                                    }
                                                ],
                                            ]
                                        },
                                    }
                                    for row in tech_table
                                ],
                            ],
                        },
                    }
                )

            # Suggested additions
            content_blocks.append(
                {
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [
                            {
                                "type": "text",
                                "text": {"content": "\nSuggested Additions:\n"},
                                "annotations": {"bold": True},
                            },
                            {
                                "type": "text",
                                "text": {
                                    "content": tech_stack.get(
                                        "suggested_additions", "N/A"
                                    )
                                },
                            },
                        ]
                    },
                }
            )

            # --- Section 4 Heading: Optimized Resume Content ---
            content_blocks.extend(
                [
                    {
                        "object": "block",
                        "type": "heading_2",
                        "heading_2": {
                            "rich_text": [
                                {
                                    "type": "text",
                                    "text": {
                                        "content": "📄 4. Optimized Resume Content"
                                    },
                                }
                            ]
                        },
                    },
                ]
            )

            # Add tailored resume as code block
            tailored_content = resume_data.get("tailored_content", "")
            chunk_size = 1900
            rich_text_items = []

            for i in range(0, len(tailored_content), chunk_size):
                chunk = tailored_content[i : i + chunk_size]
                rich_text_items.append({"type": "text", "text": {"content": chunk}})

            content_blocks.append(
                {
                    "object": "block",
                    "type": "code",
                    "code": {
                        "rich_text": rich_text_items,
                        "language": "latex",
                    },
                }
            )

            # --- Section 5 Heading: Change Summary ---
            content_blocks.extend(
                [
                    {
                        "object": "block",
                        "type": "heading_2",
                        "heading_2": {
                            "rich_text": [
                                {
                                    "type": "text",
                                    "text": {"content": "📋 5. Change Summary"},
                                }
                            ]
                        },
                    },
                    {
                        "object": "block",
                        "type": "paragraph",
                        "paragraph": {
                            "rich_text": [
                                {
                                    "type": "text",
                                    "text": {"content": "✅ What Made the Cut:\n"},
                                    "annotations": {"bold": True},
                                },
                                {
                                    "type": "text",
                                    "text": {
                                        "content": change_summary.get(
                                            "what_made_cut", "N/A"
                                        )
                                    },
                                },
                            ]
                        },
                    },
                    {
                        "object": "block",
                        "type": "paragraph",
                        "paragraph": {
                            "rich_text": [
                                {
                                    "type": "text",
                                    "text": {"content": "\n✂️ What Was Removed:\n"},
                                    "annotations": {"bold": True},
                                },
                                {
                                    "type": "text",
                                    "text": {
                                        "content": change_summary.get(
                                            "what_removed", "N/A"
                                        )
                                    },
                                },
                            ]
                        },
                    },
                    {
                        "object": "block",
                        "type": "paragraph",
                        "paragraph": {
                            "rich_text": [
                                {
                                    "type": "text",
                                    "text": {"content": "\n🎯 Interview Prep:"},
                                    "annotations": {"bold": True},
                                }
                            ]
                        },
                    },
                ]
            )

            # Add interview prep as numbered list
            interview_prep = change_summary.get("interview_prep", [])
            if isinstance(interview_prep, list):
                for point in interview_prep:
                    content_blocks.append(
                        {
                            "object": "block",
                            "type": "numbered_list_item",
                            "numbered_list_item": {
                                "rich_text": [
                                    {"type": "text", "text": {"content": point}}
                                ]
                            },
                        }
                    )
            else:
                # Fallback if interview_prep is a string
                content_blocks.append(
                    {
                        "object": "block",
                        "type": "paragraph",
                        "paragraph": {
                            "rich_text": [
                                {"type": "text", "text": {"content": interview_prep}}
                            ]
                        },
                    }
                )

            # Add PDF download link if available
            if pdf_url:
                logger.info(f"🔗 Adding resume PDF URL to Notion: {pdf_url}")
                content_blocks.extend(
                    [
                        {
                            "object": "block",
                            "type": "heading_3",
                            "heading_3": {
                                "rich_text": [
                                    {
                                        "type": "text",
                                        "text": {
                                            "content": "📥 Download Tailored Resume"
                                        },
                                    }
                                ]
                            },
                        },
                        {
                            "object": "block",
                            "type": "file",
                            "file": {
                                "type": "external",
                                "external": {"url": pdf_url},
                            },
                        },
                    ]
                )

        # ==========================================
        # SECTION 6: COVER LETTER (if provided)
        # ==========================================
        if cover_letter_data:
            logger.info("Adding cover letter section to Notion page")

            writing_strategy = cover_letter_data.get("writing_strategy", {})
            cl_change_summary = cover_letter_data.get("change_summary", {})

            # --- Section 6 Heading: Cover Letter Strategy ---
            content_blocks.extend(
                [
                    {
                        "object": "block",
                        "type": "heading_2",
                        "heading_2": {
                            "rich_text": [
                                {
                                    "type": "text",
                                    "text": {"content": "✍️ 6. Cover Letter"},
                                }
                            ]
                        },
                    },
                    {
                        "object": "block",
                        "type": "heading_3",
                        "heading_3": {
                            "rich_text": [
                                {
                                    "type": "text",
                                    "text": {"content": "Writing Strategy"},
                                }
                            ]
                        },
                    },
                    {
                        "object": "block",
                        "type": "paragraph",
                        "paragraph": {
                            "rich_text": [
                                {
                                    "type": "text",
                                    "text": {"content": "Summary:\n"},
                                    "annotations": {"bold": True},
                                },
                                {
                                    "type": "text",
                                    "text": {
                                        "content": writing_strategy.get(
                                            "summary", "N/A"
                                        )
                                    },
                                },
                            ]
                        },
                    },
                    {
                        "object": "block",
                        "type": "paragraph",
                        "paragraph": {
                            "rich_text": [
                                {
                                    "type": "text",
                                    "text": {"content": "\nOpening Hook:\n"},
                                    "annotations": {"bold": True},
                                },
                                {
                                    "type": "text",
                                    "text": {
                                        "content": writing_strategy.get(
                                            "opening_hook", "N/A"
                                        )
                                    },
                                },
                            ]
                        },
                    },
                    {
                        "object": "block",
                        "type": "paragraph",
                        "paragraph": {
                            "rich_text": [
                                {
                                    "type": "text",
                                    "text": {"content": "\nBody Focus:\n"},
                                    "annotations": {"bold": True},
                                },
                                {
                                    "type": "text",
                                    "text": {
                                        "content": writing_strategy.get(
                                            "body_focus", "N/A"
                                        )
                                    },
                                },
                            ]
                        },
                    },
                    {
                        "object": "block",
                        "type": "paragraph",
                        "paragraph": {
                            "rich_text": [
                                {
                                    "type": "text",
                                    "text": {"content": "\nGap Handling:\n"},
                                    "annotations": {"bold": True},
                                },
                                {
                                    "type": "text",
                                    "text": {
                                        "content": writing_strategy.get(
                                            "gap_handling", "N/A"
                                        )
                                    },
                                },
                            ]
                        },
                    },
                ]
            )

            # --- Tailored Cover Letter Content (Code Block) ---
            content_blocks.append(
                {
                    "object": "block",
                    "type": "heading_3",
                    "heading_3": {
                        "rich_text": [
                            {
                                "type": "text",
                                "text": {"content": "Tailored Cover Letter Content"},
                            }
                        ]
                    },
                }
            )

            # Add tailored cover letter as code block
            cl_tailored_content = cover_letter_data.get("tailored_content", "")
            chunk_size = 1900
            cl_rich_text_items = []

            for i in range(0, len(cl_tailored_content), chunk_size):
                chunk = cl_tailored_content[i : i + chunk_size]
                cl_rich_text_items.append({"type": "text", "text": {"content": chunk}})

            content_blocks.append(
                {
                    "object": "block",
                    "type": "code",
                    "code": {
                        "rich_text": cl_rich_text_items,
                        "language": "latex",
                    },
                }
            )

            # --- Change Summary ---
            content_blocks.extend(
                [
                    {
                        "object": "block",
                        "type": "heading_3",
                        "heading_3": {
                            "rich_text": [
                                {
                                    "type": "text",
                                    "text": {"content": "Change Summary"},
                                }
                            ]
                        },
                    },
                    {
                        "object": "block",
                        "type": "paragraph",
                        "paragraph": {
                            "rich_text": [
                                {
                                    "type": "text",
                                    "text": {"content": "Key Customizations:\n"},
                                    "annotations": {"bold": True},
                                },
                                {
                                    "type": "text",
                                    "text": {
                                        "content": cl_change_summary.get(
                                            "key_customizations", "N/A"
                                        )
                                    },
                                },
                            ]
                        },
                    },
                    {
                        "object": "block",
                        "type": "paragraph",
                        "paragraph": {
                            "rich_text": [
                                {
                                    "type": "text",
                                    "text": {"content": "\nWord Count: "},
                                    "annotations": {"bold": True},
                                },
                                {
                                    "type": "text",
                                    "text": {
                                        "content": cl_change_summary.get(
                                            "word_count", "N/A"
                                        )
                                    },
                                },
                            ]
                        },
                    },
                    {
                        "object": "block",
                        "type": "paragraph",
                        "paragraph": {
                            "rich_text": [
                                {
                                    "type": "text",
                                    "text": {"content": "\nStorytelling Arc:\n"},
                                    "annotations": {"bold": True},
                                },
                                {
                                    "type": "text",
                                    "text": {
                                        "content": cl_change_summary.get(
                                            "storytelling_arc", "N/A"
                                        )
                                    },
                                },
                            ]
                        },
                    },
                ]
            )

            # Add cover letter PDF download link if available
            if cover_letter_pdf_url:
                logger.info(
                    f"🔗 Adding cover letter PDF URL to Notion: {cover_letter_pdf_url}"
                )
                content_blocks.extend(
                    [
                        {
                            "object": "block",
                            "type": "heading_3",
                            "heading_3": {
                                "rich_text": [
                                    {
                                        "type": "text",
                                        "text": {
                                            "content": "📥 Download Tailored Cover Letter"
                                        },
                                    }
                                ]
                            },
                        },
                        {
                            "object": "block",
                            "type": "file",
                            "file": {
                                "type": "external",
                                "external": {"url": cover_letter_pdf_url},
                            },
                        },
                    ]
                )

        # ==========================================
        # CREATE NOTION PAGE
        # ==========================================
        response = await notion.pages.create(
            parent={"database_id": DATABASE_ID},
            properties={
                "Position": {"title": [{"text": {"content": job_name}}]},
                "Company": {"rich_text": [{"text": {"content": company}}]},
                "Job Posting": {"url": job_data["url"]},
                "Match Score": {"number": eval_data.get("match_score", 0) / 100},
                "Stage": {"select": {"name": "Saved"}},
                "Work Mode": {"select": {"name": work_mode or "Not specified"}},
                "location": {"rich_text": [{"text": {"content": location}}]},
                "Outcome": {"select": {"name": "Active"}},
            },
            children=content_blocks,
        )

        logger.info(f"✅ Successfully saved to Notion: {response['id']}")

        return {"notion_page_id": response["id"], "notion_url": response["url"]}

    except Exception as e:
        logger.error(f"Failed to save to Notion: {str(e)}")
        raise Exception(f"Notion save failed: {str(e)}")
