"""
Gap analysis and personalised learning plan generator.

After all skills are assessed this module:
  1. Computes the gap for each skill (required_level - actual_level)
  2. Identifies adjacent skills the candidate can leverage
  3. Generates a prioritised learning roadmap with free resources + time estimates
"""

import json
import re
from typing import Optional
from pydantic import BaseModel
import google.generativeai as genai

from core.skill_extractor import SkillRequirement, CandidateProfile
from core.assessor import SkillSession, LEVEL_LABELS


class Resource(BaseModel):
    title: str
    url: str
    platform: str       # YouTube / freeCodeCamp / Official Docs / Coursera (audit) / etc.
    type: str           # video / course / documentation / book / tutorial
    is_free: bool = True


class LearningItem(BaseModel):
    skill_name: str
    current_level: int
    current_label: str
    required_level: int
    required_label: str
    gap: int
    priority: str               # "critical" | "important" | "optional"
    adjacent_skills_leveraged: list[str]
    learning_path: list[str]    # ordered list of sub-topics to cover
    resources: list[Resource]
    estimated_weeks: int
    weekly_hours: int
    rationale: str              # why this skill matters for the role


class SkillGap(BaseModel):
    skill_name: str
    required_level: int
    required_label: str
    actual_level: int
    actual_label: str
    gap: int
    importance: str


class LearningPlan(BaseModel):
    candidate_name: Optional[str]
    job_title: str
    overall_readiness_pct: int   # 0-100
    readiness_label: str         # "Strong Match" / "Good Candidate" / "Needs Preparation" / "Significant Gap"
    strengths: list[str]         # skills where candidate meets or exceeds requirement
    gaps: list[SkillGap]
    items: list[LearningItem]    # ordered learning plan items
    executive_summary: str
    total_estimated_weeks: int


def _clean_json(text: str) -> str:
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    return text.strip()


def compute_gaps(sessions: list[SkillSession]) -> list[SkillGap]:
    gaps = []
    for s in sessions:
        if s.final_rating is None:
            continue
        gap = s.skill.required_level - s.final_rating
        if gap > 0:
            gaps.append(SkillGap(
                skill_name=s.skill.name,
                required_level=s.skill.required_level,
                required_label=s.skill.required_level_label,
                actual_level=s.final_rating,
                actual_label=s.final_rating_label or LEVEL_LABELS[s.final_rating],
                gap=gap,
                importance=s.skill.importance,
            ))
    # Sort by gap desc, must-haves first
    gaps.sort(key=lambda g: (g.importance != "must-have", -g.gap))
    return gaps


def generate_learning_plan(
    sessions: list[SkillSession],
    candidate: CandidateProfile,
    job_title: str,
    model: genai.GenerativeModel,
) -> LearningPlan:
    """Single LLM call that produces the complete learning plan as JSON."""

    skill_summary = []
    for s in sessions:
        if s.final_rating is None:
            continue
        skill_summary.append({
            "skill": s.skill.name,
            "category": s.skill.category,
            "required_level": s.skill.required_level,
            "required_label": s.skill.required_level_label,
            "actual_level": s.final_rating,
            "actual_label": s.final_rating_label,
            "gap": s.skill.required_level - s.final_rating,
            "importance": s.skill.importance,
            "rationale": s.rating_rationale,
        })

    claimed = ", ".join(candidate.claimed_skills) or "not specified"
    education = candidate.education or "not specified"

    prompt = f"""
You are a senior learning & development expert. Generate a personalised skill development plan.

## Candidate Profile
Name: {candidate.name or 'Candidate'}
Current role: {candidate.current_role or 'not specified'}
Years of experience: {candidate.years_experience or 'not specified'}
Education: {education}
Claimed skills: {claimed}
Background: {candidate.summary}

## Target Role
{job_title}

## Assessment Results
{json.dumps(skill_summary, indent=2)}

Generate a comprehensive personalised learning plan. Return ONLY valid JSON matching this schema exactly:
{{
  "candidate_name": "string or null",
  "job_title": "string",
  "overall_readiness_pct": <0-100 integer>,
  "readiness_label": "Strong Match|Good Candidate|Needs Preparation|Significant Gap",
  "strengths": ["skill names where actual >= required"],
  "gaps": [
    {{
      "skill_name": "string",
      "required_level": 1-5,
      "required_label": "string",
      "actual_level": 1-5,
      "actual_label": "string",
      "gap": 1-4,
      "importance": "must-have|nice-to-have"
    }}
  ],
  "items": [
    {{
      "skill_name": "string",
      "current_level": 1-5,
      "current_label": "string",
      "required_level": 1-5,
      "required_label": "string",
      "gap": 1-4,
      "priority": "critical|important|optional",
      "adjacent_skills_leveraged": ["skills the candidate already has that help learn this"],
      "learning_path": ["ordered list of 3-5 specific sub-topics to cover"],
      "resources": [
        {{
          "title": "resource title",
          "url": "real URL (must be a known free resource)",
          "platform": "YouTube|freeCodeCamp|Official Docs|Coursera (audit free)|edX (audit free)|Khan Academy|GitHub|Dev.to|MDN|roadmap.sh|other",
          "type": "video|course|documentation|tutorial|book",
          "is_free": true
        }}
      ],
      "estimated_weeks": <integer>,
      "weekly_hours": <integer 5-20>,
      "rationale": "1-2 sentences on why this skill matters for the role"
    }}
  ],
  "executive_summary": "3-4 sentence overview of the candidate's fit, key gaps, and recommended focus",
  "total_estimated_weeks": <sum of non-overlapping weeks>
}}

Critical rules:
- Only include skills with gap > 0 in "items" (learning plan items)
- Order "items" by priority: critical must-haves first
- "adjacent_skills_leveraged" must reference real skills the candidate demonstrated
- All resources MUST be genuinely free (no paywalled content; Coursera/edX audit mode is OK)
- Use REAL resource URLs from well-known platforms; do NOT invent URLs
- estimated_weeks should be realistic given the gap size and candidate's background
- total_estimated_weeks should assume some parallel learning (not purely sequential sum)
- Do NOT output anything outside the JSON object
"""

    response = model.generate_content(prompt)
    raw = _clean_json(response.text)

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        if match:
            data = json.loads(match.group())
        else:
            raise ValueError(f"Could not parse learning plan JSON:\n{raw[:500]}")

    # Ensure is_free is set on all resources
    for item in data.get("items", []):
        for res in item.get("resources", []):
            res.setdefault("is_free", True)

    return LearningPlan(**data)
