# Skill Gap Agent

AI-powered technical interviewer that conducts a live 3-phase skill gap assessment and generates a personalised learning plan.

## Stack

| Layer    | Tech                              |
| -------- | --------------------------------- |
| Backend  | FastAPI + Gemini 1.5 Flash        |
| Frontend | React 18 + Vite + Recharts        |
| AI       | Google Gemini (free tier)         |

## Quick start

### 1. Backend

```bash
cd backend
cp .env.example .env          # add your GEMINI_API_KEY
pip install -r requirements.txt
uvicorn main:app --reload
```

Server runs at **http://localhost:8000**.

### 2. Frontend

```bash
cd frontend
npm install
npm run dev
```

App runs at **http://localhost:5173**. API calls to `/api/*` are proxied to the backend automatically.

### 3. API key

Get a free Gemini key at [aistudio.google.com](https://aistudio.google.com).  
Set it in `backend/.env` **or** paste it directly in the UI sidebar.

## How it works

1. **Phase 1 — Skill Profiling**: The agent extracts required skills from the JD silently, then asks targeted questions one at a time to probe real depth.
2. **Phase 2 — Gap Analysis**: After enough exchanges the agent outputs a structured `gap_analysis` JSON (skill scores, verdicts, summary).
3. **Phase 3 — Learning Plan**: Immediately follows with a `learning_plan` JSON (prioritised focus areas, real resources, weekly plan, readiness date).

Both JSON blocks are parsed and rendered live in the results panel alongside the chat.
