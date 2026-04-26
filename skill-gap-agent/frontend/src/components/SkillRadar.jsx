import {
  Radar,
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  ResponsiveContainer,
  Tooltip,
} from 'recharts'

const VERDICT_META = {
  strong:       { label: 'Strong',        color: '#22c55e', bg: '#dcfce7' },
  acceptable:   { label: 'Acceptable',    color: '#3b82f6', bg: '#dbeafe' },
  gap:          { label: 'Gap',           color: '#f59e0b', bg: '#fef3c7' },
  critical_gap: { label: 'Critical Gap',  color: '#ef4444', bg: '#fee2e2' },
}

const LEVEL_ORDER = { none: 0, basic: 1, proficient: 2, expert: 3 }
const REQ_ORDER   = { junior: 1, mid: 2, senior: 3 }

function truncate(str, n = 14) {
  return str.length > n ? str.slice(0, n - 1) + '…' : str
}

export default function SkillRadar({ data }) {
  const skills = data?.skills_assessed ?? []
  if (!skills.length) return null

  const radarData = skills.map((s) => ({
    skill: truncate(s.skill),
    fullSkill: s.skill,
    score: s.score ?? 0,
    fullMark: 10,
  }))

  return (
    <div className="skill-radar">
      <h2 className="results-section-title">Skill Scores</h2>

      {data.summary && (
        <p className="radar-summary">{data.summary}</p>
      )}

      <div className="radar-chart-wrap">
        <ResponsiveContainer width="100%" height={280}>
          <RadarChart data={radarData} margin={{ top: 10, right: 30, bottom: 10, left: 30 }}>
            <PolarGrid stroke="#e2e8f0" />
            <PolarAngleAxis
              dataKey="skill"
              tick={{ fontSize: 11, fill: '#64748b', fontFamily: 'Inter, sans-serif' }}
            />
            <Radar
              name="Score"
              dataKey="score"
              stroke="#6366f1"
              fill="#6366f1"
              fillOpacity={0.15}
              strokeWidth={2}
            />
            <Tooltip
              formatter={(value, name, props) => [
                `${value}/10 — ${props.payload.fullSkill}`,
                'Score',
              ]}
              contentStyle={{
                fontSize: '12px',
                borderRadius: '8px',
                border: '1px solid #e2e8f0',
                fontFamily: 'Inter, sans-serif',
              }}
            />
          </RadarChart>
        </ResponsiveContainer>
      </div>

      <div className="skill-list">
        {skills.map((s) => {
          const meta = VERDICT_META[s.verdict] ?? VERDICT_META.acceptable
          const pct = ((s.score ?? 0) / 10) * 100
          return (
            <div key={s.skill} className="skill-row">
              <div className="skill-row-top">
                <span className="skill-name">{s.skill}</span>
                <span
                  className="verdict-badge"
                  style={{ background: meta.bg, color: meta.color }}
                >
                  {meta.label}
                </span>
              </div>
              <div className="skill-bar-wrap">
                <div
                  className="skill-bar-fill"
                  style={{
                    width: `${pct}%`,
                    background: meta.color,
                  }}
                />
              </div>
              <div className="skill-row-meta">
                <span>Demonstrated: <strong>{s.demonstrated_level}</strong></span>
                <span>Required: <strong>{s.required_level}</strong></span>
                <span className="skill-score">{s.score}/10</span>
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
