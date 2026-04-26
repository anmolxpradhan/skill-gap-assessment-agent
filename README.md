# Skill Gap Assessment Agent

An AI-powered technical interviewer that takes a **Job Description** and a **candidate resume**, conducts a live adaptive Q&A assessment, identifies skill gaps, and generates a personalised learning plan with curated resources and time estimates.

Built with **FastAPI** (backend) + **React + Vite** (frontend) + **Google Gemini 2.5 Flash**.

---

## How it works

```
Phase 1 — SKILL PROFILING
  Adaptive Q&A: concept explanations, debugging scenarios, comparisons
  ↓
Phase 2 — GAP ANALYSIS
  Scores each required skill (0–10), verdict: strong / acceptable / gap / critical_gap
  ↓
Phase 3 — LEARNING PLAN
  Prioritised focus areas, real resources (docs, courses, videos), weekly plan + time estimates
```

---

## Tech stack

| Layer | Technology |
|---|---|
| Backend API | FastAPI + Uvicorn |
| AI Model | Google Gemini 2.5 Flash |
| Frontend | React 18 + Vite |
| Charts | Recharts |
| File parsing | pdf.js (CDN) + mammoth.js (CDN) |
| Session storage | Browser localStorage |

---

## Setup

### 1. Clone the repo

```bash
git clone https://github.com/anmolxpradhan/skill-gap-assessment-agent.git
cd skill-gap-assessment-agent/skill-gap-agent
```

### 2. Gemini API key

A working API key is provided below — copy it into the backend `.env` file:

```
GEMINI_API_KEY=AIzaSyDTzJXl103cXq8rAH3W30-KvEhjZq5t_s0
```

```bash
echo "GEMINI_API_KEY=AIzaSyDTzJXl103cXq8rAH3W30-KvEhjZq5t_s0" > backend/.env
```

> This key uses the **Google AI Studio free tier** (15 RPM · 1,500 req/day). No credit card required.

### 3. Start the backend

```bash
cd backend
python -m venv venv && source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
python -m uvicorn main:app --reload
```

Backend runs at **http://127.0.0.1:8000**

### 4. Start the frontend

```bash
cd ../frontend
npm install
npm run dev
```

Frontend runs at **http://localhost:5173**

---

## Project structure

```
skill-gap-agent/
├── backend/
│   ├── main.py              # FastAPI app — session management, Gemini integration
│   ├── requirements.txt
│   └── .env.example
└── frontend/
    ├── src/
    │   ├── App.jsx           # Root — layout, state, session persistence
    │   ├── index.css
    │   └── components/
    │       ├── InputPanel.jsx      # JD + resume input with drag & drop upload
    │       ├── ChatInterface.jsx   # Live interview chat (Phase 1 & 2)
    │       ├── SkillRadar.jsx      # Gap analysis bar chart
    │       ├── LearningPlan.jsx    # Phase 3 learning plan view
    │       └── PhaseIndicator.jsx  # Progress indicator
    ├── index.html
    ├── package.json
    └── vite.config.js
```

---

## Features

- Drag & drop resume upload (`.pdf`, `.docx`, `.txt`) with client-side text extraction
- Persistent session history in the sidebar (localStorage)
- Live skill radar chart after gap analysis
- Full-width learning plan view with expandable focus area cards
- No login required — runs entirely locally
