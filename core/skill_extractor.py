"""
Extracts structured skill requirements from a Job Description and claimed skills
from a candidate resume using Gemini. Returns normalized data for the assessor.
"""

import json
import re
from typing import Optional
import google.generativeai as genai
from pydantic import BaseModel


class SkillRequirement(BaseModel):
    name: str
    category: str           # e.g. "programming", "framework", "soft skill", "domain"
    required_level: int     # 1-5 (Novice to Expert)
    required_level_label: str
    importance: str         # "must-have" | "nice-to-have"
    context: str            # what the JD says about this skill


class CandidateProfile(BaseModel):
    name: Optional[str] = None
    current_role: Optional[str] = None
    years_experience: Optional[int] = None
    claimed_skills: list[str] = []
    education: Optional[str] = None
    summary: str = ""


class ExtractionResult(BaseModel):
    job_title: str
    company: Optional[str] = None
    required_skills: list[SkillRequirement]
    candidate: CandidateProfile


_LEVEL_MAP = {1: "Novice", 2: "Beginner", 3: "Intermediate", 4: "Advanced", 5: "Expert"}


def _clean_json(text: str) -> str:
    """Strip markdown fences if Gemini wraps the response."""
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    return text.strip()


def extract_skills(jd_text: str, resume_text: str, model: genai.GenerativeModel) -> ExtractionResult:
    """
    Single LLM call that parses both the JD and the resume simultaneously,
    returning structured skill requirements and a candidate profile.
    """
    prompt = f"""
You are a technical recruiter and skills analyst. Analyse the job description and resume below.

## Job Description
{jd_text}

## Resume
{resume_text}

Return ONLY a valid JSON object (no markdown, no explanation) with this exact schema:
{{
  "job_title": "string",
  "company": "string or null",
  "required_skills": [
    {{
      "name": "short skill name (e.g. Python, React, SQL, System Design)",
      "category": "programming|framework|cloud|database|devops|testing|soft_skill|domain|tool",
      "required_level": 1-5,
      "required_level_label": "Novice|Beginner|Intermediate|Advanced|Expert",
      "importance": "must-have|nice-to-have",
      "context": "one sentence from the JD explaining why this skill matters"
    }}
  ],
  "candidate": {{
    "name": "string or null",
    "current_role": "string or null",
    "years_experience": integer or null,
    "claimed_skills": ["list", "of", "skill", "names"],
    "education": "highest degree + field or null",
    "summary": "2-sentence summary of the candidate's background"
  }}
}}

Rules:
- Include 5-12 skills from the JD (focus on technical skills; include at most 2 soft skills)
- required_level must reflect what the JD actually demands (use 3=Intermediate as default unless JD says senior/lead → 4, junior → 2)
- claimed_skills should be raw skill names exactly as they appear in the resume
- Do NOT include any text outside the JSON
"""
    response = model.generate_content(prompt)
    raw = _clean_json(response.text)

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        # Fallback: try to extract the JSON object
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        if match:
            data = json.loads(match.group())
        else:
            raise ValueError(f"Could not parse LLM response as JSON:\n{raw[:500]}")

    # Normalise level labels
    for skill in data.get("required_skills", []):
        level = skill.get("required_level", 3)
        skill["required_level_label"] = _LEVEL_MAP.get(level, "Intermediate")

    return ExtractionResult(**data)
