# Skill Gap Assessment Agent

An AI-powered technical interviewer that takes a **Job Description** and a **candidate resume**, conducts a live adaptive Q&A assessment, identifies skill gaps, and generates a personalised learning plan with curated resources and time estimates.

Built with **FastAPI** (backend) + **React + Vite** (frontend) + **Google Gemini 2.5 Flash**.

### Live app (Vercel)

**Deployed demo:** [https://skill-gap-assessment-agent-iw8wl8kkw-anmolxpradhans-projects.vercel.app/](https://skill-gap-assessment-agent-iw8wl8kkw-anmolxpradhans-projects.vercel.app/)

Ensure **`GEMINI_API_KEY`** is set in that Vercel project’s **Settings → Environment Variables**, then redeploy, or API calls will fail.

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

1. Open [Google AI Studio](https://aistudio.google.com) → **Get API key** → create a key.
2. Put it only in local env files — **never commit keys** or paste them into public READMEs (Google may disable leaked keys).

```bash
cp backend/.env.example backend/.env
# Edit backend/.env and set GEMINI_API_KEY=your_key_here
```

> Free tier limits apply (see Google’s current quotas in AI Studio).

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

## Deployment (Vercel — full-stack)

### Step 1 — Import the repo

1. Go to [vercel.com](https://vercel.com) → **Add New Project** → import this repo.
2. Set **Root Directory** to: `skill-gap-agent/frontend`
3. Framework should detect as **Vite** (or set **Framework Preset** to **Vite** in project settings if needed).

### Step 2 — Environment variable

Under **Settings → Environment Variables**, add:

| Name | Value |
|---|---|
| `GEMINI_API_KEY` | *(paste a fresh key from [AI Studio](https://aistudio.google.com) — do not reuse a key that was ever committed or shared publicly)* |

Redeploy after adding or changing the key.

### Step 3 — Deploy

Push to `main` or trigger **Redeploy** from the Deployments tab. The Vite app is served from `dist/`; API routes live under `/api/*` (`api/index.py`).

> **Stateless API:** Chat history is kept in the browser and sent with each request so it works on Vercel serverless.

---

## Features

- Drag & drop resume upload (`.pdf`, `.docx`, `.txt`) with client-side text extraction
- Persistent session history in the sidebar (localStorage)
- Live skill radar chart after gap analysis
- Full-width learning plan view with expandable focus area cards
- No login required — runs entirely locally
