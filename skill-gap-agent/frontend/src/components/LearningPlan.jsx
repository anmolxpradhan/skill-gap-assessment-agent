import { useState } from 'react'

const PRIORITY_META = {
  high:   { label: 'High',   color: '#dc2626', bg: '#fef2f2', border: '#fecaca' },
  medium: { label: 'Medium', color: '#ea580c', bg: '#fff7ed', border: '#fed7aa' },
  low:    { label: 'Low',    color: '#16a34a', bg: '#f0fdf4', border: '#bbf7d0' },
}

const TYPE_ICONS = {
  course:  '◉',
  book:    '📖',
  docs:    '📄',
  project: '🛠',
  video:   '🎥',
}

function FocusAreaCard({ area, defaultOpen }) {
  const [open, setOpen] = useState(defaultOpen)
  const meta = PRIORITY_META[area.priority] ?? PRIORITY_META.medium

  return (
    <div className="lp-card" style={{ borderColor: open ? '#cbd5e1' : '#e2e8f0' }}>
      {/* Header */}
      <button className="lp-card-header" onClick={() => setOpen(v => !v)}>
        <span className="lp-skill-name">{area.skill}</span>
        <div className="lp-card-header-right">
          <span
            className="lp-priority-badge"
            style={{ color: meta.color, background: meta.bg, border: `1px solid ${meta.border}` }}
          >
            {meta.label}
          </span>
          {area.time_to_proficiency && (
            <span className="lp-time-badge">{area.time_to_proficiency}</span>
          )}
          <span className="lp-chevron">{open ? '−' : '+'}</span>
        </div>
      </button>

      {/* Body */}
      {open && (
        <div className="lp-card-body">
          {/* Why */}
          {area.why && (
            <div className="lp-section">
              <p className="lp-section-label">Why this matters</p>
              <p className="lp-section-text">{area.why}</p>
            </div>
          )}

          {/* Weekly plan */}
          {area.weekly_plan && (
            <div className="lp-section">
              <p className="lp-section-label">Weekly plan</p>
              <p className="lp-section-text">{area.weekly_plan}</p>
            </div>
          )}

          {/* Resources */}
          {area.resources?.length > 0 && (
            <div className="lp-section">
              <p className="lp-section-label">Resources</p>
              <div className="lp-resources">
                {area.resources.map((res, i) => (
                  <div key={i} className="lp-resource-row">
                    <span className="lp-resource-icon">
                      {TYPE_ICONS[res.type] ?? '◌'}
                    </span>
                    <div className="lp-resource-info">
                      <a
                        href={res.url}
                        target="_blank"
                        rel="noreferrer"
                        className="lp-resource-title"
                      >
                        {res.title}
                      </a>
                      <div className="lp-resource-meta">
                        {res.type && (
                          <span className="lp-resource-type">{res.type}</span>
                        )}
                        {res.duration && (
                          <span className="lp-resource-duration">{res.duration}</span>
                        )}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

export default function LearningPlan({ data }) {
  if (!data) return null

  const sorted = [...(data.focus_areas ?? [])].sort((a, b) => {
    const order = { high: 0, medium: 1, low: 2 }
    return (order[a.priority] ?? 1) - (order[b.priority] ?? 1)
  })

  return (
    <div className="lp-root">
      <h2 className="lp-heading">Learning Plan</h2>

      {/* Summary stats */}
      <div className="lp-stats-grid">
        <div className="lp-stat-card">
          <div className="lp-stat-value">{data.total_estimated_time ?? '—'}</div>
          <div className="lp-stat-label">Total time</div>
        </div>
        <div className="lp-stat-card">
          <div className="lp-stat-value">{data.realistic_readiness_date ?? '—'}</div>
          <div className="lp-stat-label">Ready by</div>
        </div>
        <div className="lp-stat-card">
          <div className="lp-stat-value">{sorted.length}</div>
          <div className="lp-stat-label">Focus areas</div>
        </div>
      </div>

      {/* Focus areas */}
      <div className="lp-focus-list">
        {sorted.map((area, i) => (
          <FocusAreaCard key={i} area={area} defaultOpen={i === 0} />
        ))}
      </div>

      {/* Motivational note */}
      {data.motivational_note && (
        <div className="lp-motivational">
          <span className="lp-motivational-icon">✦</span>
          <p className="lp-motivational-text">{data.motivational_note}</p>
        </div>
      )}
    </div>
  )
}
