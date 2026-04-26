# AI-Powered Skill Assessment & Personalised Learning Plan Agent

A resume tells you what someone *claims* to know — not how well they actually know it.

This agent takes a **Job Description** and a **candidate's resume**, conversationally assesses real proficiency on each required skill through an adaptive Q&A dialogue, identifies gaps, and generates a **personalised learning plan** focused on adjacent skills the candidate can realistically acquire — with curated free resources and time estimates.

---

## Free tier declaration

| Service / Library | Tier used | Limits |
|---|---|---|
| **Google Gemini 1.5 Flash** | Free (Google AI Studio) | 15 RPM · 1 500 req/day · 1M tokens/day |
| **Streamlit** | Open-source (self-hosted) | Unlimited |
| **PyPDF2** | Open-source | Unlimited |
| **python-dotenv** | Open-source | Unlimited |
| **Pydantic** | Open-source | Unlimited |

No credit card required. Everything runs locally.

---

## Quickstart

### 1. Clone / download and install dependencies
```bash
cd skill-assessment-agent
python -m venv .venv && source .venv/bin/activate   # optional but recommended
pip install -r requirements.txt
```

### 2. Get a free Gemini API key
Visit **https://aistudio.google.com** → *Get API key* → copy the key.

### 3. Set up the key
```bash
cp .env.example .env
# Edit .env and paste your key, or just enter it in the sidebar at runtime
```

### 4. Run the app
```bash
streamlit run app.py
```

Open **http://localhost:8501** in your browser.

---

## How it works

```
┌─────────────────────────────────────────────────────────────┐
│  1. SETUP                                                    │
│     Upload resume (PDF/TXT) + paste Job Description         │
│     ↓                                                        │
│  2. EXTRACTION  (1 LLM call)                                 │
│     • Parse required skills + levels from JD                │
│     • Extract claimed skills from resume                     │
│     ↓                                                        │
│  3. ASSESSMENT  (3 LLM calls per skill)                      │
│     For each required skill:                                 │
│       Q1 – conceptual understanding                         │
│       Q2 – practical application                            │
│       Q3 – edge-case / problem-solving                      │
│       → Internal rating 1-5 (Novice → Expert)               │
│     ↓                                                        │
│  4. REPORT  (1 LLM call)                                     │
│     • Gap analysis (required vs actual)                     │
│     • Prioritised learning roadmap                          │
│     • Adjacent skills the candidate can leverage            │
│     • Free resources with URLs                              │
│     • Time estimates (weeks + hours/week)                   │
└─────────────────────────────────────────────────────────────┘
```

---

## Project structure

```
skill-assessment-agent/
├── app.py                    # Streamlit UI — setup → assessment → report
├── core/
│   ├── skill_extractor.py    # LLM-based JD + resume parser
│   ├── assessor.py           # Adaptive conversational assessment engine
│   └── plan_generator.py     # Gap analysis + learning plan generator
├── utils/
│   └── pdf_parser.py         # PDF / text resume parsing (PyPDF2)
├── requirements.txt
├── .env.example
└── README.md
```

---

## Assessment scoring rubric

| Score | Label | Meaning |
|---|---|---|
| 1 | Novice | No real knowledge; only heard of it |
| 2 | Beginner | Basic awareness; no practical depth |
| 3 | Intermediate | Solid working knowledge; has used in projects |
| 4 | Advanced | Deep expertise; handles complex scenarios |
| 5 | Expert | Mastery; can teach, design systems, handle edge cases |

---

## Limitations & known constraints

- **Gemini free tier RPM**: The app adds small delays between calls to avoid hitting the 15 RPM limit. For more than ~8 skills you may occasionally see rate-limit errors; wait a minute and click the answer button again.
- **PDF parsing quality**: Complex multi-column or image-heavy PDFs may lose formatting. Plain-text paste is always reliable.
- **Resource URLs**: LLM-generated resource URLs are best-effort. Always verify links before following them.
- **Language**: English only for optimal quality.
