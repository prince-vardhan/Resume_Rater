import { useState } from 'react'
import { rankCandidates } from './api'
import UploadForm from './components/UploadForm'
import SkillsSummary from './components/SkillsSummary'
import RankingTable from './components/RankingTable'
import ExplanationCards from './components/ExplanationCards'
import ComparisonPanel from './components/ComparisonPanel'
import AeroShards from './components/AeroShards'
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
    <div className="app-shell">
      <AeroShards
        className="app-background"
        backgroundColor="#120F17"
        shardColor="#896ABD"
        accentColor="#A855F7"
        placement="full"
        flow="stream"
        material="pearl"
        detail="balanced"
        effect="none"
        scale={1}
        spread={1}
        depth={1}
        speed={1}
        spin={1}
        interaction="repel"
        density={1.5}
        shardSize={1.1}
        stretch={1}
        turbulence={1}
        glow={1}
        edgeSoftness={2}
        bloom={0.5}
        grain={0.05}
        chromaticAberration={0.0075}
        transitionDuration={1}
        interactionRadius={1.5}
        interactionStrength={0.5}
        rippleIntensity={1}
        holdToGather
        paused={false}
      />

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
    </div>
  )
}

export default App
