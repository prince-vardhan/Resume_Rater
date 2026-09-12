function SkillChips({ skills, tone }) {
  if (!skills || skills.length === 0) {
    return <span className="muted">none detected</span>
  }
  return (
    <div className="chip-row">
      {skills.map((skill) => (
        <span key={skill} className={`chip chip-${tone}`}>
          {skill}
        </span>
      ))}
    </div>
  )
}

export default function SkillsSummary({ requiredSkills, parsingWarnings, biasFlags }) {
  return (
    <section className="card">
      <h2>Required skills detected in JD</h2>
      <div className="skills-grid">
        <div>
          <h3>Required</h3>
          <SkillChips skills={requiredSkills?.required} tone="required" />
        </div>
        <div>
          <h3>Preferred</h3>
          <SkillChips skills={requiredSkills?.preferred} tone="preferred" />
        </div>
      </div>

      {parsingWarnings?.length > 0 && (
        <details className="notice notice-warning" open>
          <summary>⚠️ Parsing warnings ({parsingWarnings.length})</summary>
          <ul>
            {parsingWarnings.map((w, i) => (
              <li key={i}>
                <strong>{w.file}</strong>: {w.detail}
              </li>
            ))}
          </ul>
        </details>
      )}

      {biasFlags?.length > 0 && (
        <details className="notice notice-info">
          <summary>🚩 JD phrasing flags ({biasFlags.length}) — bonus feature</summary>
          <ul>
            {biasFlags.map((flag, i) => (
              <li key={i}>{flag}</li>
            ))}
          </ul>
        </details>
      )}
    </section>
  )
}
