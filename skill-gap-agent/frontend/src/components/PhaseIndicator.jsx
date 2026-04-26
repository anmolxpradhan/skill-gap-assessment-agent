const PHASES = [
  { num: 1, label: 'Skill Profiling' },
  { num: 2, label: 'Gap Analysis' },
  { num: 3, label: 'Learning Plan' },
]

export default function PhaseIndicator({ phase }) {
  return (
    <div className="phase-indicator">
      {PHASES.map((p, i) => {
        const isDone = phase > p.num
        const isActive = phase === p.num
        return (
          <div key={p.num} className="phase-step-wrap">
            <div className={`phase-step ${isDone ? 'done' : ''} ${isActive ? 'active' : ''}`}>
              <div className="phase-dot">
                {isDone ? (
                  <svg width="10" height="10" viewBox="0 0 10 10" fill="none">
                    <path d="M2 5l2.5 2.5L8 3" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                  </svg>
                ) : (
                  p.num
                )}
              </div>
              <span className="phase-label">{p.label}</span>
            </div>
            {i < PHASES.length - 1 && (
              <div className={`phase-connector ${phase > p.num ? 'filled' : ''}`} />
            )}
          </div>
        )
      })}
    </div>
  )
}
