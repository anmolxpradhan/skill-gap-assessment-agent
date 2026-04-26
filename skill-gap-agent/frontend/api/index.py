"""
Skill Gap Assessment Agent — Stateless FastAPI backend for Vercel.
Gemini chat history is owned by the frontend and sent with every request.
"""

import json
import os
import re
from typing import Optional

from google import genai
from google.genai import types
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

load_dotenv()

# ── Gemini client — lazily initialised on first use ───────────────────────────

_GEMINI_CLIENT: Optional[genai.Client] = None


def _get_client() -> genai.Client:
    global _GEMINI_CLIENT
    if _GEMINI_CLIENT is None:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise HTTPException(status_code=500, detail="GEMINI_API_KEY is not configured on the server.")
        _GEMINI_CLIENT = genai.Client(
            api_key=api_key,
            http_options=types.HttpOptions(api_version="v1alpha"),
        )
    return _GEMINI_CLIENT

# ── App ───────────────────────────────────────────────────────────────────────

app = FastAPI(title="Skill Gap Assessment Agent")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── System prompt ─────────────────────────────────────────────────────────────

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


# ── Pydantic models ───────────────────────────────────────────────────────────

class HistoryEntry(BaseModel):
    role: str   # "user" or "model"
    text: str


class SessionCreate(BaseModel):
    jd_text: str
    resume_text: str


class ChatMessage(BaseModel):
    message: str
    history: list[HistoryEntry]


# ── Helpers ───────────────────────────────────────────────────────────────────

def _build_chat(history: Optional[list[HistoryEntry]] = None):
    """Create a Gemini chat, seeded with prior history if provided."""
    gemini_history = []
    if history:
        for entry in history:
            gemini_history.append(
                types.Content(role=entry.role, parts=[types.Part(text=entry.text)])
            )
    return _get_client().chats.create(
        model="gemini-2.5-flash",
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            temperature=0.7,
            max_output_tokens=2048,
        ),
        history=gemini_history or None,
    )


def _try_parse_json(s: str) -> Optional[dict]:
    s = re.sub(r"^```(?:json)?\s*", "", s.strip(), flags=re.MULTILINE).strip()
    s = re.sub(r"```\s*$", "", s, flags=re.MULTILINE).strip()
    try:
        return json.loads(s)
    except json.JSONDecodeError:
        return None


def _parse_blocks(text: str) -> tuple[Optional[dict], Optional[dict]]:
    gap_analysis = None
    learning_plan = None

    ga_match = re.search(r"<gap_analysis>(.*?)</gap_analysis>", text, re.DOTALL)
    lp_match = re.search(r"<learning_plan>(.*?)</learning_plan>", text, re.DOTALL)

    if ga_match:
        gap_analysis = _try_parse_json(ga_match.group(1))
    if lp_match:
        learning_plan = _try_parse_json(lp_match.group(1))

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
    text = re.sub(r"<gap_analysis>.*?</gap_analysis>", "", text, flags=re.DOTALL)
    text = re.sub(r"<learning_plan>.*?</learning_plan>", "", text, flags=re.DOTALL)

    def _remove_data_codeblock(m: re.Match) -> str:
        parsed = _try_parse_json(m.group(1))
        if parsed and ("skills_assessed" in parsed or "focus_areas" in parsed):
            return ""
        return m.group(0)

    text = re.sub(r"```(?:json)?\s*([\s\S]*?)```", _remove_data_codeblock, text)
    return text.strip()


# ── Routes ────────────────────────────────────────────────────────────────────

@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.post("/api/session")
async def create_session(req: SessionCreate):
    try:
        chat = _build_chat()
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

    # Return history so the frontend can send it back with the next request
    history = [
        {"role": "user", "text": initial_prompt},
        {"role": "model", "text": text},
    ]

    return {
        "message": _strip_xml(text),
        "phase": phase,
        "gap_analysis": gap_analysis,
        "learning_plan": learning_plan,
        "history": history,
    }


@app.post("/api/chat")
async def send_message(req: ChatMessage):
    try:
        # Rebuild chat from the full prior history, then send the new message
        chat = _build_chat(req.history)
        response = chat.send_message(req.message)
        text = response.text
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc))

    gap_analysis, learning_plan = _parse_blocks(text)
    phase = 3 if learning_plan else (2 if gap_analysis else 1)

    new_history = [e.model_dump() for e in req.history] + [
        {"role": "user", "text": req.message},
        {"role": "model", "text": text},
    ]

    return {
        "message": _strip_xml(text),
        "phase": phase,
        "gap_analysis": gap_analysis,
        "learning_plan": learning_plan,
        "history": new_history,
    }


# Vercel invokes this FastAPI ASGI `app` directly (do not wrap with Mangum).
