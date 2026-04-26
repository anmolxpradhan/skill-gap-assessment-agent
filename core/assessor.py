"""
Adaptive conversational assessment engine.

For each required skill the agent asks 3 questions of escalating depth:
  Q1 – conceptual understanding
  Q2 – practical application / "show me you've done this"
  Q3 – edge-case / problem-solving scenario

After Q3 (or sooner if the candidate clearly deflects) it internally rates
proficiency on a 1-5 scale and moves to the next skill.
"""

import json
import re
from dataclasses import dataclass, field
from typing import Optional
import google.generativeai as genai

from core.skill_extractor import SkillRequirement, CandidateProfile

LEVEL_LABELS = {1: "Novice", 2: "Beginner", 3: "Intermediate", 4: "Advanced", 5: "Expert"}

SYSTEM_PROMPT = """You are a senior technical interviewer conducting a friendly but rigorous skill assessment.
Your goal is to discover the candidate's *actual* proficiency, not just what they claim.

Guidelines:
- Be warm and conversational; this is a dialogue, not an interrogation.
- Ask ONE question at a time. Never ask multiple questions in the same turn.
- Keep questions concise (2-4 sentences max).
- Adapt the next question's difficulty based on the quality of the previous answer.
- When you see an evasive or very vague answer, gently probe further.
- Never reveal the internal rating while the assessment is ongoing.
- Do not praise answers excessively; a neutral acknowledgement is fine (e.g. "Got it.", "Thanks.").
"""


@dataclass
class Turn:
    role: str   # "assessor" | "candidate"
    text: str


@dataclass
class SkillSession:
    skill: SkillRequirement
    candidate_claimed: bool          # Did the resume mention this skill?
    turns: list[Turn] = field(default_factory=list)
    question_count: int = 0
    final_rating: Optional[int] = None          # 1-5, filled after assessment
    final_rating_label: Optional[str] = None
    rating_rationale: Optional[str] = None
    complete: bool = False


def _clean_json(text: str) -> str:
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    return text.strip()


def _gemini_history(session: SkillSession) -> list[dict]:
    """Convert turns into the format Gemini's multi-turn API expects."""
    history = []
    for turn in session.turns:
        role = "model" if turn.role == "assessor" else "user"
        history.append({"role": role, "parts": [{"text": turn.text}]})
    return history


def generate_opening_question(
    skill: SkillRequirement,
    candidate: CandidateProfile,
    claimed: bool,
    model: genai.GenerativeModel,
) -> str:
    """Generate the first question for a skill."""
    claimed_note = (
        f"The candidate lists '{skill.name}' on their resume."
        if claimed
        else f"The candidate does NOT list '{skill.name}' on their resume."
    )
    context = f"""
Skill to assess: {skill.name} (category: {skill.category})
Required proficiency for the role: {skill.required_level_label} ({skill.required_level}/5)
{claimed_note}
Candidate background: {candidate.summary}

Generate the FIRST assessment question. It should test conceptual understanding.
Start with a brief one-sentence transition like "Let's talk about [skill]." then the question.
Keep it conversational and open-ended. Output only the question text, nothing else.
"""
    chat = model.start_chat(history=[])
    response = chat.send_message(SYSTEM_PROMPT + "\n\n" + context)
    return response.text.strip()


def generate_followup_question(
    session: SkillSession,
    model: genai.GenerativeModel,
    candidate: CandidateProfile,
) -> str:
    """Generate Q2 or Q3 based on conversation so far."""
    q_num = session.question_count + 1
    depth = "practical application (ask about a real project or hands-on scenario)" if q_num == 2 \
        else "a problem-solving edge case or architectural decision"

    context = f"""
You are assessing: {session.skill.name}
Required level: {session.skill.required_level_label}
Candidate background: {candidate.summary}
This is question {q_num} of 3. Focus on: {depth}.
Based on the conversation so far, generate the next question.
Output ONLY the question text with a one-word-or-brief acknowledgement prefix like "Got it." or "Interesting."
"""
    history = _gemini_history(session)
    chat = model.start_chat(history=history)
    response = chat.send_message(context)
    return response.text.strip()


def rate_skill(session: SkillSession, model: genai.GenerativeModel) -> SkillSession:
    """
    After 3 Q&A turns, ask the model to rate the skill and explain why.
    Updates session in place and marks it complete.
    """
    qa_transcript = "\n".join(
        f"{'Assessor' if t.role == 'assessor' else 'Candidate'}: {t.text}"
        for t in session.turns
    )

    prompt = f"""
You interviewed a candidate on: {session.skill.name}
Required proficiency: {session.skill.required_level_label} ({session.skill.required_level}/5)

Transcript:
{qa_transcript}

Rate their ACTUAL demonstrated proficiency (1-5):
1 = Novice (no real knowledge)
2 = Beginner (basic awareness, no depth)
3 = Intermediate (solid working knowledge)
4 = Advanced (deep expertise, nuanced understanding)
5 = Expert (mastery, can teach / architect)

Return ONLY a valid JSON object:
{{
  "rating": <integer 1-5>,
  "label": "<Novice|Beginner|Intermediate|Advanced|Expert>",
  "rationale": "<2-3 sentences explaining the rating based on specific answers>"
}}
"""
    response = model.generate_content(prompt)
    raw = _clean_json(response.text)

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        data = json.loads(match.group()) if match else {"rating": 2, "label": "Beginner", "rationale": "Could not parse rating."}

    session.final_rating = data.get("rating", 2)
    session.final_rating_label = data.get("label", LEVEL_LABELS[session.final_rating])
    session.rating_rationale = data.get("rationale", "")
    session.complete = True
    return session


def get_transition_message(
    completed_session: SkillSession,
    next_skill: Optional[SkillRequirement],
    model: genai.GenerativeModel,
) -> str:
    """
    Generate a short natural transition between skills.
    E.g. "Thanks for sharing that. Let's move on to React..."
    """
    if next_skill is None:
        prompt = (
            f"The assessment of {completed_session.skill.name} is done. "
            "Generate a warm 1-sentence closing before the report is generated. "
            "Something like 'Great, that covers all the skills I wanted to explore!'"
        )
    else:
        prompt = (
            f"We just finished assessing {completed_session.skill.name}. "
            f"Next skill is {next_skill.name}. "
            "Generate a ONE-sentence natural transition (e.g. 'Got it — let's switch to React.'). "
            "Output only the transition sentence."
        )
    response = model.generate_content(prompt)
    return response.text.strip()
