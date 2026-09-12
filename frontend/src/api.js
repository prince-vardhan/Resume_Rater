const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

/**
 * POST one JD PDF + multiple resume PDFs to the FastAPI backend's /rank
 * endpoint and return the parsed pipeline output (ranking, jd_required_skills,
 * parsing_warnings, bias_flags) -- same payload the Streamlit UI consumes.
 */
export async function rankCandidates(jdFile, resumeFiles) {
  const formData = new FormData()
  formData.append('jd', jdFile)
  for (const file of resumeFiles) {
    formData.append('resumes', file)
  }

  let res
  try {
    res = await fetch(`${API_BASE}/rank`, { method: 'POST', body: formData })
  } catch {
    throw new Error(
      `Could not reach the API at ${API_BASE}. Is it running? (uvicorn api.main:app --reload --port 8000)`
    )
  }

  if (!res.ok) {
    let detail = res.statusText
    try {
      const body = await res.json()
      detail = body.detail ? JSON.stringify(body.detail) : JSON.stringify(body)
    } catch {
      // response wasn't JSON, fall back to statusText
    }
    throw new Error(`Ranking request failed (${res.status}): ${detail}`)
  }

  return res.json()
}
