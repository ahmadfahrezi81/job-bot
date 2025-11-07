# services/llm_resume_service.py
from openai import AsyncOpenAI
import logging
import os
import json

logger = logging.getLogger(__name__)
client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def load_master_resume() -> str:
    """Load the master resume content from file"""
    try:
        with open("data/resume-content.tex", "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        raise Exception("Master resume not found at data/resume-content.tex")


async def tailor_resume(
    job_description: str,
    evaluation: dict,
    job_title: str = None,
    company_name: str = None,
) -> dict:
    """
    Tailors resume content for a specific job posting.

    Args:
        job_description: Full text of the job posting
        evaluation: Dict containing match_score, strengths, gaps, etc.
        job_title: Title of the position (e.g., "Software Engineer - QA Automation")
        company_name: Name of the company (e.g., "GoTo Financial")

    Returns:
        {
            "tailored_content": "... LaTeX content ...",
            "pruning_strategy": {
                "summary": "...",
                "scoring_logic": "...",
                "role_breakdown": "..."
            },
            "tech_stack_analysis": {
                "table": [
                    {"tech": "...", "assessment": "...", "risk": "Low/Medium/High"}
                ],
                "suggested_additions": "..."
            },
            "change_summary": {
                "what_made_cut": "...",
                "what_removed": "...",
                "interview_prep": ["point 1", "point 2", ...]
            }
        }
    """
    logger.info("🎯 Starting resume tailoring...")
    logger.info(f"   • Job Title: {job_title or 'Not specified'}")
    logger.info(f"   • Company: {company_name or 'Not specified'}")

    # Load master resume
    try:
        master_resume = load_master_resume()
        logger.info(f"✅ Loaded master resume ({len(master_resume)} chars)")
    except Exception:
        logger.exception("❌ Failed to load master resume")
        raise

    # Extract key info from evaluation
    match_score = evaluation.get("match_score", 0)
    strengths = evaluation.get("strengths", [])
    gaps = evaluation.get("gaps", [])

    logger.info(f"📊 Tailoring for match score: {match_score}%")
    logger.info(f"   • {len(strengths)} strengths identified")
    logger.info(f"   • {len(gaps)} gaps identified")

    # Build role context string
    role_context = ""
    if job_title and company_name:
        role_context = f"Target Role: {job_title} at {company_name}"
    elif job_title:
        role_context = f"Target Role: {job_title}"
    elif company_name:
        role_context = f"Target Company: {company_name}"
    else:
        role_context = "Target Role: Not specified (use job description to infer)"

    # Build the prompt
    prompt = f"""
You are an expert resume optimization specialist. Your goal is to tailor a LaTeX resume content file for a specific job while maintaining complete honesty and ensuring it fits on ONE PAGE.

CONTEXT:
- Two-file LaTeX system: main.tex (formatting - never modify) + resume-content.tex (content only - you update this)
- {role_context}
- Current match score: {match_score}%

YOUR EVALUATION ALREADY IDENTIFIED:
Strengths:
{chr(10).join(f"• {s}" for s in strengths)}

Gaps:
{chr(10).join(f"• {g}" for g in gaps)}

YOUR TASKS:

1. Content Relevance Scoring & Pruning Strategy
For each bullet point in the master resume, assign a relevance score (0-10) based on the job description and target role.

STRICT One-Page Constraints:
• Experience section: Maximum 4 bullets per role (5-6 for most relevant role if all bullets are high-impact)
• Projects section: Keep 2 projects maximum with 4 bullets each
• Total bullets: 20-24 maximum (prioritize quality over arbitrary limits)
• Remove ALL nested sub-bullets unless absolutely critical with metrics

Pruning Logic:
• Remove bullets scoring <5 ONLY if they add no unique value
• Keep bullets scoring 7+ even if slightly longer — quality over brevity
• Consolidate redundant achievements only when they truly overlap
• Prioritize bullets with metrics and direct job keyword matches
• If a role is less relevant, reduce to 3-4 bullets maximum
• Cut entire projects only if relevance score is consistently below 6

Writing Optimization:
• Prioritize impact and metrics over brevity — never sacrifice substance for length
• Aim for ONE clean line per bullet (typically 12-18 words), but 20-25 words is FINE if it preserves critical metrics
• Keep technical specificity: mention tools, frameworks, and architectures where they demonstrate expertise
• Remove filler words ("responsible for", "worked on", "helped to", "instrumental in")
• Front-load impact: Start with result, then method
• Keep tech stack mentions in bullets when they show HOW you achieved results (e.g., "using Postman and SQL" adds context)
• Preserve ALL quantified metrics (numbers, percentages, time savings, user counts)
• Be precise and concise, but NEVER at the expense of losing impact

CRITICAL: NEVER remove these elements during optimization:
• Quantified metrics (e.g., "22 scripts", "60% faster", "200M+ users", "8 critical bugs")
• Specific tools that show technical depth (e.g., "Postman", "RBAC", "row-level security", "Appium/Selenium")
• Architectural terms that demonstrate seniority (e.g., "SSR hybrid", "serverless functions", "tenant-scoped", "multi-tenant")
• Impact statements with before/after data (e.g., "32% conversion increase", "40% faster loads", "95%+ test coverage")

If a bullet has 3+ of these elements, it should almost NEVER be cut.

CALIBRATION EXAMPLES OF HIGH-QUALITY BULLETS:

✅ EXCELLENT (keep this style):
"Built AI-powered test automation agent, reducing authentication test development by 60%."
→ Has: tool type, impact metric, specific achievement

✅ EXCELLENT:
"Delivered 22 Python automation scripts with Appium/Selenium, exceeding coverage targets by 15%."
→ Has: quantity, tools, impact metric

✅ EXCELLENT:
"Validated REST APIs using Postman and SQL; tracked 40+ bugs including 8 critical security issues."
→ Has: tools, process, quantified outcomes

✅ EXCELLENT:
"Architected multi-tenant SaaS POS with tenant-scoped users and real-time financial analytics."
→ Has: architecture terms, technical specificity, system scope

❌ BAD (avoid this):
"Developed automation scripts to improve testing efficiency."
→ Vague, no metrics, no tools mentioned

❌ BAD:
"Worked on API testing and bug tracking."
→ Passive voice, no specifics, no impact

2. Tech Stack Analysis
• Identify technologies from job description not currently shown
• Reference the target role ({job_title or 'role'} at {company_name or 'company'}) when making recommendations
• For each tech, assess if it can reasonably be added to existing projects based on transferable skills
• Format as structured table data with risk assessment
• Only suggest additions candidate could defend in interview
• Consider what skills {company_name or 'this company'} likely values based on the job description

3. Optimized Resume Content
Generate the complete tailored resume-content.tex file.

CRITICAL FORMATTING RULES:
• Keep ALL LaTeX commands exactly as shown
• Maintain structure: \\resumeSubheading{{Title}}{{Date}}{{Company}}{{Location}}
• Maintain structure: \\resumeProjectHeading{{Name}}{{URL}}{{Tech Stack}}
• Keep all \\resumeSubHeadingListStart and \\resumeSubHeadingListEnd
• Keep all \\resumeItemListStart and \\resumeItemListEnd
• Balance all braces {{}}
• Use date format: MMM. YYYY
• Do NOT add \\documentclass, \\begin{{document}}, or preamble commands

OPTIMIZATION GUIDELINES:
• Reorder sections if it strengthens narrative for {job_title or 'the target role'}
• Rewrite bullets to be maximally impactful while preserving metrics and technical depth
• Every bullet should fit cleanly on ONE line, but don't sacrifice critical details to force brevity
• Incorporate job description keywords naturally, especially those relevant to {company_name or 'the company'}
• Update tech stacks in project headers ONLY where defensible
• Ensure bullets tell progression story: capable → experienced → ready for {job_title or 'this role'}
• Tailor language and emphasis to align with {company_name or 'company'} culture if evident from job description

CURRENT MASTER RESUME:
{master_resume}

JOB DESCRIPTION:
{job_description}

Return ONLY valid JSON in this exact structure:

{{
    "tailored_content": "... complete LaTeX content for resume-content.tex ...",
    "pruning_strategy": {{
        "summary": "Brief overview of your pruning approach, how you optimized for {job_title or 'this role'} at {company_name or 'this company'}, and constraints applied",
        "scoring_logic": "Explanation of how you scored each section (0-10 scale), what made bullets relevant to {job_title or 'the role'}, and prioritization criteria",
        "role_breakdown": "Which roles/projects kept, their relevance scores for {job_title or 'this position'}, and bullet count decisions with justification"
    }},
    "tech_stack_analysis": {{
        "table": [
            {{"tech": "Technology name", "assessment": "Why it's relevant to {job_title or 'this role'} at {company_name or 'this company'} and how candidate can add it", "risk": "Low/Medium/High"}},
            {{"tech": "Another tech", "assessment": "Assessment explanation with company/role context", "risk": "Low/Medium/High"}}
        ],
        "suggested_additions": "Summary of recommended tech additions for {job_title or 'this role'}, where to place them, and why they strengthen the application to {company_name or 'this company'}"
    }},
    "change_summary": {{
        "what_made_cut": "Detailed explanation: which experiences/projects kept and why (with relevance scores for {job_title or 'the role'}), key bullets retained and their impact, total bullet count, how this aligns with {company_name or 'company'} expectations",
        "what_removed": "Detailed explanation: bullets cut due to low relevance to {job_title or 'this position'} or length, projects removed, redundant content consolidated, justification for each major cut",
        "interview_prep": [
            "Talking point 1 about specific experience or skill aligned with {job_title or 'this role'} at {company_name or 'this company'}",
            "Talking point 2 about how background fits {job_title or 'the role'} and company culture",
            "Talking point 3 about technical capabilities relevant to {company_name or 'this company'}",
            "Talking point 4 about measurable achievements that matter for {job_title or 'this position'}",
            "Talking point 5 addressing potential gaps or anticipated questions from {company_name or 'company'} interviewers"
        ]
    }}
}}

RULES:
• Be honest but strategic in pruning decisions — optimize for {job_title or 'this role'} at {company_name or 'this company'}
• ONE PAGE is non-negotiable - when in doubt, prioritize highest-impact bullets
• 19-23 bullets maximum across entire resume (quality over quantity)
• Only add tech where there's genuine transferability
• Never invent experiences, dates, or companies
• Maximize impact and technical depth — conciseness is secondary to substance
• Reference {job_title or 'the target role'} and {company_name or 'the company'} throughout your analysis to show targeted optimization
• Ensure all JSON strings are properly escaped (especially LaTeX content with backslashes)
"""

    try:
        logger.info("🚀 Sending tailoring request to OpenAI...")
        response = await client.chat.completions.create(
            model="gpt-4o",  # Use GPT-4 for better resume tailoring
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert resume optimization specialist. Always return valid JSON with properly escaped LaTeX content. Prioritize impact and technical depth over brevity.",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,  # Lower temp for consistent formatting
            response_format={"type": "json_object"},
        )

        raw_content = response.choices[0].message.content
        logger.debug("----- RAW RESUME TAILORING RESPONSE -----")
        logger.debug(raw_content[:2000])  # Log first 2000 chars
        logger.debug("-----------------------------------------")

        parsed = json.loads(raw_content)

        # Validate required fields
        required_fields = [
            "tailored_content",
            "pruning_strategy",
            "tech_stack_analysis",
            "change_summary",
        ]
        for field in required_fields:
            if field not in parsed:
                raise ValueError(f"Missing required field: {field}")

        # Validate nested structures
        if not isinstance(parsed["pruning_strategy"], dict):
            raise ValueError("pruning_strategy must be a dict")
        if not isinstance(parsed["tech_stack_analysis"], dict):
            raise ValueError("tech_stack_analysis must be a dict")
        if not isinstance(parsed["change_summary"], dict):
            raise ValueError("change_summary must be a dict")
        if not isinstance(parsed["change_summary"].get("interview_prep", []), list):
            raise ValueError("interview_prep must be a list")

        logger.info("✅ Resume tailoring completed successfully")
        logger.info(
            f"   • Tailored content length: {len(parsed['tailored_content'])} chars"
        )
        logger.info(
            f"   • Interview prep points: {len(parsed['change_summary'].get('interview_prep', []))}"
        )
        logger.info(
            f"   • Optimized for: {job_title or 'role'} at {company_name or 'company'}"
        )

        return parsed

    except Exception as e:
        logger.exception("❌ Resume tailoring failed")
        raise Exception(f"Resume tailoring failed: {str(e)}")
