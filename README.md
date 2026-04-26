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

## Deployment (Vercel — full-stack, one platform)

Both frontend and backend deploy together on Vercel in a single step.

### Step 1 — Import the repo

1. Go to [vercel.com](https://vercel.com) → **Add New Project**
2. Import `skill-gap-assessment-agent` from GitHub
3. Leave **Root Directory** as `/` (repo root) — `vercel.json` handles everything
4. Framework preset will show "Other" — that's correct, leave it

### Step 2 — Add the environment variable

Under **Environment Variables** before deploying, add:

| Name | Value |
|---|---|
| `GEMINI_API_KEY` | `AIzaSyDTzJXl103cXq8rAH3W30-KvEhjZq5t_s0` |

### Step 3 — Deploy

Click **Deploy**. Vercel will:
- Build the React frontend (`npm run build`)
- Deploy the FastAPI backend as a Python serverless function at `/api/*`
- Route all other traffic to the React SPA

Your live URL will be something like `https://skill-gap-assessment-agent.vercel.app`

> **How it works:** The backend is stateless — conversation history is stored in the browser and sent with each request, so it works perfectly with Vercel's serverless functions.

---

## Features

- Drag & drop resume upload (`.pdf`, `.docx`, `.txt`) with client-side text extraction
- Persistent session history in the sidebar (localStorage)
- Live skill radar chart after gap analysis
- Full-width learning plan view with expandable focus area cards
- No login required — runs entirely locally
