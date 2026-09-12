function fmt(n, digits = 3) {
  return typeof n === 'number' ? n.toFixed(digits) : '-'
}

export default function RankingTable({ ranking }) {
  return (
    <section className="card">
      <h2>Ranked candidates</h2>
      <div className="table-scroll">
        <table className="ranking-table">
          <thead>
            <tr>
              <th>Rank</th>
              <th>Candidate</th>
              <th>Score</th>
              <th>Keyword</th>
              <th>Semantic</th>
              <th>Required coverage</th>
              <th>Missing required</th>
            </tr>
          </thead>
          <tbody>
            {ranking.map((c) => (
              <tr key={c.resume_id} className={c.rank <= 3 ? 'row-top' : ''}>
                <td>{c.rank}</td>
                <td className="candidate-cell">{c.resume_id}</td>
                <td>
                  <span className="score-badge">{fmt(c.score)}</span>
                </td>
                <td>{fmt(c.keyword_norm, 2)}</td>
                <td>{fmt(c.semantic_norm, 2)}</td>
                <td>{fmt(c.required_skill_coverage, 2)}</td>
                <td className="missing-cell">
                  {c.missing_skills?.length ? c.missing_skills.join(', ') : '—'}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  )
}
