import { useState } from 'react'
import InputPanel from './components/InputPanel'
import ChatInterface from './components/ChatInterface'
import SkillRadar from './components/SkillRadar'
import LearningPlan from './components/LearningPlan'
import PhaseIndicator from './components/PhaseIndicator'

const API_BASE = import.meta.env.VITE_API_URL || ''
const SESSIONS_KEY = 'skill-gap-sessions'

// ── Sidebar ───────────────────────────────────────────────────────────────────

function Sidebar({ sessions, activeSessionId, onNew, onLoad }) {
  return (
    <aside className="sidebar">
      {/* Brand */}
      <div className="sidebar-header">
        <div className="sidebar-brand">
          <span className="brand-mark">✦</span>
          <span className="brand-name">Skill Gap Agent</span>
        </div>
        <button className="new-btn" onClick={onNew}>
          <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
            <path d="M7 1v12M1 7h12" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round"/>
          </svg>
          New Assessment
        </button>
      </div>

      {/* Session list */}
      <nav className="sidebar-nav">
        {sessions.length > 0 && <p className="nav-label">Recent</p>}
        {sessions.length === 0 ? (
          <p className="nav-empty">Start an assessment to see it here</p>
        ) : (
          sessions.map(s => (
            <button
              key={s.id}
              className={`nav-item ${s.id === activeSessionId ? 'active' : ''}`}
              onClick={() => onLoad(s)}
              title={s.title}
            >
              <span className="nav-item-title">{s.title}</span>
              <span className="nav-item-date">
                {new Date(s.date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
              </span>
            </button>
          ))
        )}
      </nav>
    </aside>
  )
}

// ── Results panel (shared between chat + saved views) ─────────────────────────

function ResultsPanel({ gapAnalysis, learningPlan, resultsTab, onTabChange }) {
  return (
    <aside className="results-col">
      <div className="results-tabs">
        {gapAnalysis && (
          <button
            className={`tab-btn ${resultsTab === 'radar' ? 'active' : ''}`}
            onClick={() => onTabChange('radar')}
          >
            Skill Scores
          </button>
        )}
        {learningPlan && (
          <button
            className={`tab-btn ${resultsTab === 'plan' ? 'active' : ''}`}
            onClick={() => onTabChange('plan')}
          >
            Learning Plan
          </button>
        )}
      </div>
      <div className="results-body">
        {resultsTab === 'radar' && gapAnalysis && <SkillRadar data={gapAnalysis} />}
        {resultsTab === 'plan' && learningPlan && <LearningPlan data={learningPlan} />}
      </div>
    </aside>
  )
}

// ── Root ──────────────────────────────────────────────────────────────────────

export default function App() {
  const [view, setView] = useState('input')         // 'input' | 'chat' | 'saved'
  const [sessionId, setSessionId] = useState(null)
  const [activeSessionId, setActiveSessionId] = useState(null)
  const [messages, setMessages] = useState([])
  const [phase, setPhase] = useState(1)
  const [gapAnalysis, setGapAnalysis] = useState(null)
  const [learningPlan, setLearningPlan] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [resultsTab, setResultsTab] = useState('radar')
  const [jdText, setJdText] = useState('')

  const [sessions, setSessions] = useState(() => {
    try { return JSON.parse(localStorage.getItem(SESSIONS_KEY) || '[]') } catch { return [] }
  })

  // Save a completed session and switch to the full-width plan view
  const saveAndShowPlan = (sid, plan, gap, jd) => {
    const raw = jd.trim()
    const title = (raw.slice(0, 42) + (raw.length > 42 ? '…' : '')) || 'Assessment'
    const session = {
      id: sid,
      title,
      date: new Date().toISOString(),
      learningPlan: plan,
      gapAnalysis: gap,
    }
    setSessions(prev => {
      const updated = [session, ...prev.filter(s => s.id !== sid)]
      localStorage.setItem(SESSIONS_KEY, JSON.stringify(updated))
      return updated
    })
    setActiveSessionId(sid)
    setView('saved')
  }

  // ── API calls ───────────────────────────────────────────────────────────────

  const startSession = async ({ jdText: jd, resumeText }) => {
    setJdText(jd)
    setLoading(true)
    setError(null)
    try {
      const res = await fetch(`${API_BASE}/api/session`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ jd_text: jd, resume_text: resumeText }),
      })
      const data = await res.json()
      if (!res.ok) throw new Error(data.detail || 'Failed to start session')

      setSessionId(data.session_id)
      setMessages([{ role: 'assistant', content: data.message }])
      setPhase(data.phase)
      if (data.gap_analysis) { setGapAnalysis(data.gap_analysis); setResultsTab('radar') }
      if (data.learning_plan) {
        setLearningPlan(data.learning_plan)
        saveAndShowPlan(data.session_id, data.learning_plan, data.gap_analysis, jd)
      } else {
        setView('chat')
      }
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const sendMessage = async (text) => {
    setMessages(prev => [...prev, { role: 'user', content: text }])
    setLoading(true)
    try {
      const res = await fetch(`${API_BASE}/api/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: sessionId, message: text }),
      })
      const data = await res.json()
      if (!res.ok) throw new Error(data.detail || 'Error')

      setMessages(prev => [...prev, { role: 'assistant', content: data.message }])
      setPhase(data.phase)

      const latestGap = data.gap_analysis || gapAnalysis
      if (data.gap_analysis) { setGapAnalysis(data.gap_analysis); setResultsTab('radar') }

      if (data.learning_plan) {
        setLearningPlan(data.learning_plan)
        // Switch to full-width plan view — identical to loading from history
        saveAndShowPlan(sessionId, data.learning_plan, latestGap, jdText)
      }
    } catch (err) {
      setMessages(prev => [...prev, { role: 'assistant', content: `Error: ${err.message}` }])
    } finally {
      setLoading(false)
    }
  }

  // ── Navigation ──────────────────────────────────────────────────────────────

  const handleNew = () => {
    setView('input')
    setSessionId(null)
    setActiveSessionId(null)
    setMessages([])
    setPhase(1)
    setGapAnalysis(null)
    setLearningPlan(null)
    setError(null)
    setResultsTab('radar')
    setJdText('')
  }

  const handleLoad = (session) => {
    setActiveSessionId(session.id)
    setGapAnalysis(session.gapAnalysis)
    setLearningPlan(session.learningPlan)
    setResultsTab('plan')
    setView('saved')
  }

  const showResults = gapAnalysis || learningPlan

  // ── Render ──────────────────────────────────────────────────────────────────

  return (
    <div className="app-layout">
      <Sidebar
        sessions={sessions}
        activeSessionId={activeSessionId}
        onNew={handleNew}
        onLoad={handleLoad}
      />

      <div className="main-panel">

        {/* ── View 1: Input ── */}
        {view === 'input' && (
          <InputPanel
            onStart={startSession}
            loading={loading}
            error={error}
          />
        )}

        {/* ── View 2: Chat + live results ── */}
        {view === 'chat' && (
          <div className={`chat-layout ${showResults ? 'has-results' : ''}`}>
            <div className="chat-col">
              <div className="chat-topbar">
                <PhaseIndicator phase={phase} />
              </div>
              <ChatInterface
                messages={messages}
                onSend={sendMessage}
                loading={loading}
                phase={phase}
                onViewPlan={() => setResultsTab('plan')}
                gapAnalysis={gapAnalysis}
                learningPlan={learningPlan}
              />
            </div>
            {showResults && (
              <ResultsPanel
                gapAnalysis={gapAnalysis}
                learningPlan={learningPlan}
                resultsTab={resultsTab}
                onTabChange={setResultsTab}
              />
            )}
          </div>
        )}

        {/* ── View 3: Saved / completed session (full-width) ── */}
        {view === 'saved' && (
          <div className="saved-view">
            <div className="saved-topbar">
              <div className="saved-topbar-left">
                <h1 className="saved-title">
                  {sessions.find(s => s.id === activeSessionId)?.title || 'Assessment'}
                </h1>
                <PhaseIndicator phase={3} />
              </div>
              <div className="results-tabs borderless">
                {gapAnalysis && (
                  <button
                    className={`tab-btn ${resultsTab === 'radar' ? 'active' : ''}`}
                    onClick={() => setResultsTab('radar')}
                  >
                    Skill Scores
                  </button>
                )}
                {learningPlan && (
                  <button
                    className={`tab-btn ${resultsTab === 'plan' ? 'active' : ''}`}
                    onClick={() => setResultsTab('plan')}
                  >
                    Learning Plan
                  </button>
                )}
              </div>
            </div>
            <div className="saved-body">
              {resultsTab === 'radar' && gapAnalysis && <SkillRadar data={gapAnalysis} />}
              {resultsTab === 'plan' && learningPlan && <LearningPlan data={learningPlan} />}
            </div>
          </div>
        )}

      </div>
    </div>
  )
}
