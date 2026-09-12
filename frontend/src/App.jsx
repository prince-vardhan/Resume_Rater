import { useState } from 'react'
import { rankCandidates } from './api'
import UploadForm from './components/UploadForm'
import SkillsSummary from './components/SkillsSummary'
import RankingTable from './components/RankingTable'
import ExplanationCards from './components/ExplanationCards'
import ComparisonPanel from './components/ComparisonPanel'
import './App.css'

function App() {
  const [jdFile, setJdFile] = useState(null)
  const [resumeFiles, setResumeFiles] = useState([])
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  async function handleRun() {
    setLoading(true)
    setError(null)
    try {
      const data = await rankCandidates(jdFile, resumeFiles)
      setResult(data)
    } catch (err) {
      setError(err.message || 'Something went wrong while ranking.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="page">
      <header className="page-header">
        <h1>Smart Shortlisting Engine</h1>
        <p className="subtitle">
          Ranks resumes against a job description using BM25 keyword matching + local
          sentence-embedding semantic matching (all-MiniLM-L6-v2). No external APIs are called
          at any point — explanations and bias flags are template/rule-based over
          already-computed evidence.
        </p>
      </header>

      <UploadForm
        jdFile={jdFile}
        resumeFiles={resumeFiles}
        onJdChange={setJdFile}
        onResumesChange={setResumeFiles}
        onRun={handleRun}
        loading={loading}
      />

      {error && (
        <div className="card notice notice-error">
          <strong>Error:</strong> {error}
        </div>
      )}

      {loading && (
        <div className="card loading-card">
          <div className="spinner" />
          <span>Parsing resumes, scoring, and ranking…</span>
        </div>
      )}

      {result && !loading && (
        <>
          <SkillsSummary
            requiredSkills={result.jd_required_skills}
            parsingWarnings={result.parsing_warnings}
            biasFlags={result.bias_flags}
          />
          <RankingTable ranking={result.ranking} />
          <ExplanationCards ranking={result.ranking} />
          <ComparisonPanel ranking={result.ranking} />
        </>
      )}

      {!result && !loading && !error && (
        <p className="empty-state">Upload a JD and resumes above, then click Run ranking.</p>
      )}
    </div>
  )
}

export default App
