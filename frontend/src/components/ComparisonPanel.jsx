import { useMemo, useState } from 'react'

/**
 * "Why is X ranked above Y?" -- reuses the already-computed structured
 * evidence from the ranking response (no extra API call, no LLM). Mirrors
 * the equivalent comparison block in ui/app.py exactly.
 */
export default function ComparisonPanel({ ranking }) {
  const ids = useMemo(() => ranking.map((c) => c.resume_id), [ranking])
  const [candidateX, setCandidateX] = useState(ids[0])
  const [candidateY, setCandidateY] = useState(ids[Math.min(1, ids.length - 1)])

  const byId = useMemo(() => Object.fromEntries(ranking.map((c) => [c.resume_id, c])), [ranking])
  const x = byId[candidateX]
  const y = byId[candidateY]

  if (!x || !y) return null

  const onlyX = x.matched_skills.filter((s) => !y.matched_skills.includes(s)).sort()
  const onlyY = y.matched_skills.filter((s) => !x.matched_skills.includes(s)).sort()

  return (
    <section className="card">
      <h2>Ask: "Why is X ranked above Y?"</h2>
      <p className="muted">Bonus comparison -- computed from data already fetched, no extra request.</p>
      <div className="compare-selectors">
        <label>
          Candidate X
          <select value={candidateX} onChange={(e) => setCandidateX(e.target.value)}>
            {ids.map((id) => (
              <option key={id} value={id}>{id}</option>
            ))}
          </select>
        </label>
        <label>
          Candidate Y
          <select value={candidateY} onChange={(e) => setCandidateY(e.target.value)}>
            {ids.map((id) => (
              <option key={id} value={id}>{id}</option>
            ))}
          </select>
        </label>
      </div>

      <div className="compare-result">
        <p>
          <strong>{x.resume_id}</strong> is ranked #{x.rank} vs <strong>{y.resume_id}</strong> at #{y.rank}
          {' '}(score {x.score.toFixed(3)} vs {y.score.toFixed(3)}).
        </p>
        <p>
          Keyword match: {x.keyword_norm.toFixed(3)} vs {y.keyword_norm.toFixed(3)}. Semantic
          match: {x.semantic_norm.toFixed(3)} vs {y.semantic_norm.toFixed(3)}. Required-skill
          coverage: {x.required_skill_coverage.toFixed(2)} vs {y.required_skill_coverage.toFixed(2)}.
        </p>
        {onlyX.length > 0 && (
          <p>Required skills only <strong>{x.resume_id}</strong> has: {onlyX.join(', ')}</p>
        )}
        {onlyY.length > 0 && (
          <p>Required skills only <strong>{y.resume_id}</strong> has: {onlyY.join(', ')}</p>
        )}
        {onlyX.length === 0 && onlyY.length === 0 && (
          <p>Both matched the same required skills — the difference comes from semantic/keyword score strength, not distinct skills.</p>
        )}
      </div>
    </section>
  )
}
