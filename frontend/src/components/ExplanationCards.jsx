export default function ExplanationCards({ ranking }) {
  const top3 = ranking.slice(0, 3)

  return (
    <section className="card">
      <h2>Top 3 explanations</h2>
      <div className="explanation-grid">
        {top3.map((c) => (
          <article key={c.resume_id} className="explanation-card">
            <header>
              <span className="rank-badge">#{c.rank}</span>
              <span className="candidate-cell">{c.resume_id}</span>
              <span className="score-badge">{c.score.toFixed(3)}</span>
            </header>
            <pre className="explanation-text">{c.explanation}</pre>
            <footer className="chip-row">
              {c.matched_skills?.map((s) => (
                <span key={s} className="chip chip-required">{s}</span>
              ))}
              {c.missing_skills?.map((s) => (
                <span key={s} className="chip chip-missing">{s}</span>
              ))}
            </footer>
          </article>
        ))}
      </div>
    </section>
  )
}
