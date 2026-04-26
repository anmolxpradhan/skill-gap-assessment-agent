"""
Skill Gap Assessment Agent — FastAPI Backend
Uses Gemini 2.5 Flash to conduct a 3-phase technical interview.
"""

import json
import os
import re
import uuid
from typing import Optional

from google import genai
from google.genai import types
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

load_dotenv()

app = FastAPI(title="Skill Gap Assessment Agent", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Gemini client — initialised once at startup ────────────────────────────────

_GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not _GEMINI_API_KEY:
    raise RuntimeError("GEMINI_API_KEY environment variable is not set.")

_GEMINI_CLIENT = genai.Client(
    api_key=_GEMINI_API_KEY,
    http_options=types.HttpOptions(api_version="v1alpha"),
)

# ── In-memory session store ────────────────────────────────────────────────────

_sessions: dict[str, dict] = {}

# ── System prompt ──────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are an expert technical interviewer conducting a live skill gap assessment.

You have received a Job Description and a candidate's Resume.

Your job has 3 sequential phases. Always state which phase you're in.

PHASE 1 — SKILL PROFILING (3–5 questions)
- Extract required skills from the JD silently
- Ask ONE targeted question at a time to probe actual depth, not surface knowledge
- Vary question types: explain a concept, debug a scenario, compare two approaches, describe a past project
- Don't repeat what's on the resume — dig deeper or expose gaps
- After each answer, probe once if the answer is vague before moving on

PHASE 2 — GAP IDENTIFICATION
- After sufficient questions, say "I have enough to assess your profile."
- Output a JSON block wrapped in <gap_analysis>...</gap_analysis> with this exact shape:
{
  "skills_assessed": [
    { "skill": string, "required_level": "junior|mid|senior", "demonstrated_level": "none|basic|proficient|expert", "score": 0-10, "verdict": "strong|acceptable|gap|critical_gap" }
  ],
  "summary": string
}

PHASE 3 — LEARNING PLAN
- Immediately after the gap_analysis block, output a JSON block wrapped in <learning_plan>...</learning_plan> with this shape:
{
  "focus_areas": [
    {
      "skill": string,
      "priority": "high|medium|low",
      "why": string,
      "resources": [
        { "title": string, "type": "course|book|docs|project|video", "url": string, "duration": string }
      ],
      "weekly_plan": string,
      "time_to_proficiency": string
    }
  ],
  "total_estimated_time": string,
  "realistic_readiness_date": string,
  "motivational_note": string
}

Rules:
- Only move to Phase 2 after at least 4 substantive exchanges
- Be direct, warm, and specific — no generic advice
- Resources must be REAL (Roadmap.sh, official docs, freeCodeCamp, Coursera, specific GitHub repos, etc.)
- Adjacent skills the candidate almost has should be prioritised over completely new ones"""


# ── Pydantic models ────────────────────────────────────────────────────────────

class SessionCreate(BaseModel):
    jd_text: str
    resume_text: str


class ChatMessage(BaseModel):
    session_id: str
    message: str


# ── Helpers ────────────────────────────────────────────────────────────────────

def _new_chat():
    """Create a new stateful chat using the shared global client."""
    return _GEMINI_CLIENT.chats.create(
        model="gemini-2.5-flash",
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            temperature=0.7,
            max_output_tokens=2048,
        ),
    )


def _try_parse_json(s: str) -> Optional[dict]:
    s = re.sub(r"^```(?:json)?\s*", "", s.strip(), flags=re.MULTILINE).strip()
    s = re.sub(r"```\s*$", "", s, flags=re.MULTILINE).strip()
    try:
        return json.loads(s)
    except json.JSONDecodeError:
        return None


def _parse_blocks(text: str) -> tuple[Optional[dict], Optional[dict]]:
    """Extract gap_analysis and learning_plan from XML tags or fenced code blocks."""
    gap_analysis = None
    learning_plan = None

    ga_match = re.search(r"<gap_analysis>(.*?)</gap_analysis>", text, re.DOTALL)
    lp_match = re.search(r"<learning_plan>(.*?)</learning_plan>", text, re.DOTALL)

    if ga_match:
        gap_analysis = _try_parse_json(ga_match.group(1))
    if lp_match:
        learning_plan = _try_parse_json(lp_match.group(1))

    # Fallback: model used ```json code blocks instead of XML tags
    if not gap_analysis or not learning_plan:
        for block in re.findall(r"```(?:json)?\s*([\s\S]*?)```", text):
            parsed = _try_parse_json(block)
            if parsed is None:
                continue
            if not gap_analysis and "skills_assessed" in parsed:
                gap_analysis = parsed
            elif not learning_plan and "focus_areas" in parsed:
                learning_plan = parsed

    return gap_analysis, learning_plan


def _strip_xml(text: str) -> str:
    """Remove XML tags and data JSON code blocks from display text."""
    text = re.sub(r"<gap_analysis>.*?</gap_analysis>", "", text, flags=re.DOTALL)
    text = re.sub(r"<learning_plan>.*?</learning_plan>", "", text, flags=re.DOTALL)

    def _remove_data_codeblock(m: re.Match) -> str:
        parsed = _try_parse_json(m.group(1))
        if parsed and ("skills_assessed" in parsed or "focus_areas" in parsed):
            return ""
        return m.group(0)

    text = re.sub(r"```(?:json)?\s*([\s\S]*?)```", _remove_data_codeblock, text)
    return text.strip()


# ── Routes ─────────────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/api/session")
async def create_session(req: SessionCreate):
    try:
        chat = _new_chat()
        initial_prompt = (
            f"**Job Description:**\n{req.jd_text}\n\n"
            f"**Candidate Resume:**\n{req.resume_text}\n\n"
            "Please begin the assessment. Start with Phase 1 and ask your first question."
        )
        response = chat.send_message(initial_prompt)
        text = response.text
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc))

    gap_analysis, learning_plan = _parse_blocks(text)
    phase = 3 if learning_plan else (2 if gap_analysis else 1)
    session_id = str(uuid.uuid4())

    _sessions[session_id] = {
        "chat": chat,
        "phase": phase,
        "gap_analysis": gap_analysis,
        "learning_plan": learning_plan,
    }

    return {
        "session_id": session_id,
        "message": _strip_xml(text),
        "phase": phase,
        "gap_analysis": gap_analysis,
        "learning_plan": learning_plan,
    }


@app.post("/api/chat")
async def send_message(req: ChatMessage):
    session = _sessions.get(req.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found. Please start a new session.")

    try:
        response = session["chat"].send_message(req.message)
        text = response.text
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc))

    gap_analysis, learning_plan = _parse_blocks(text)

    if gap_analysis:
        session["gap_analysis"] = gap_analysis
        session["phase"] = max(session["phase"], 2)

    if learning_plan:
        session["learning_plan"] = learning_plan
        session["phase"] = 3

    return {
        "message": _strip_xml(text),
        "phase": session["phase"],
        "gap_analysis": session.get("gap_analysis"),
        "learning_plan": session.get("learning_plan"),
    }
