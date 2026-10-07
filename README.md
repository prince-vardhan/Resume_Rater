# Resume_Rater — ResuFilter / Smart Shortlisting Engine

Given **one job description (PDF)** and a **batch of resumes (PDFs)**, this project ranks every candidate from best to worst fit, gives each a score, and writes a short, evidence-based explanation for the **top 3**. It also flags potentially biased or overly narrow wording in the JD.

It was built as a hackathon deliverable with two hard rules:

1. **Ranking must come from real keyword matching (BM25 + a skill vocabulary) combined with real semantic matching (embeddings + cosine similarity)** — never from asking an LLM to "score this resume out of 100".
2. **No external APIs.** No LLM calls, no hosted embedding services, nothing leaves the machine during inference. The embedding model's weights are downloaded once at setup, then everything runs locally/offline. Explanations and bias flags are template/rule-based.

---

## Tech stack

### Backend / engine (`shortlist-engine/`) — Python 3.11+
| Purpose | Technology |
|---|---|
| PDF text extraction | `pdfplumber` 0.11.4 |
| Keyword ranking | `rank_bm25` 0.2.2 (BM25Okapi) |
| Semantic embeddings | `sentence-transformers` 3.0.1 with the open-weight `all-MiniLM-L6-v2` model (runs on CPU, pulls in PyTorch) |
| Numerics (cosine similarity, min-max normalisation) | `numpy` 1.26.4 |
| REST API | `fastapi` 0.112.0 + `uvicorn` 0.30.5 + `python-multipart` 0.0.9 (file uploads) |
| Optional recruiter UI | `streamlit` 1.37.0 |
| Tests | `pytest` 8.3.2 |
| Standard-library pieces | `re` (regex skill/section matching, bias heuristics), `pathlib`, `tempfile`, `shutil` |

### Frontend (`frontend/`)
| Purpose | Technology |
|---|---|
| UI framework | React 19 |
| Build tool / dev server | Vite 8 (with `@vitejs/plugin-react`) |
| Compiler optimisation | React Compiler (`babel-plugin-react-compiler`, via `@rolldown/plugin-babel`) |
| Animation | `framer-motion` |
| WebGPU animated background | `vgpu` (used by the custom `AeroShards` component) |
| Linting | ESLint 10 + `eslint-plugin-react-hooks` + `eslint-plugin-react-refresh` |
| Styling | Plain CSS (`App.css`, `index.css`, `AeroShards.css`) |
| HTTP | Browser `fetch` + `FormData` |

### Tooling
- `shortlist-engine/run.sh` — one-command setup/run script (creates a venv in `~/.cache`, installs deps, runs CLI / API / UI / frontend / tests).
- Git for version control; `BUILD_SPEC.md` is the original design spec.

---

## Repository layout

```
Resume_Rater/
├── README.md                  ← you are here
├── BUILD_SPEC.md              ← original v2 build spec (stage-by-stage design)
├── frontend/                  ← React + Vite web app ("ResuFilter")
│   ├── index.html, vite.config.js, package.json, .env.example
│   └── src/
│       ├── main.jsx, App.jsx, api.js, App.css, index.css
│       └── components/
│           ├── UploadForm.jsx        # pick JD + resumes, "Run ranking" button
│           ├── SkillsSummary.jsx     # JD required/preferred skills, parsing warnings, bias flags
│           ├── RankingTable.jsx      # full ranked table
│           ├── ExplanationCards.jsx  # top-3 explanations
│           ├── ComparisonPanel.jsx   # "Why is X ranked above Y?"
│           └── AeroShards.jsx/.css   # WebGPU animated background
└── shortlist-engine/          ← Python engine
    ├── run.sh, requirements.txt, README.md
    ├── data/
    │   ├── jd/Sample_JD.pdf               # sample JD (TechNova Solutions – Junior Full Stack Developer Intern)
    │   └── resumes/Resume_01…18_*.pdf     # 18 sample resumes
    ├── src/
    │   ├── parsing.py          # PDF → text, resume → sections → chunks
    │   ├── skill_vocab.py      # skill → alias dictionary, related skills, equivalent-tool groups
    │   ├── extraction.py       # JD required vs preferred skills; resume skills
    │   ├── keyword_match.py    # BM25 scores + required-skill overlap/coverage
    │   ├── semantic_match.py   # requirement ↔ resume-chunk embeddings & evidence
    │   ├── fusion.py           # normalise, weight, combine, rank
    │   ├── explain.py          # template-based top-3 explanations
    │   ├── bias_check.py       # heuristic JD bias flags
    │   └── pipeline.py         # orchestrates everything: run_pipeline()
    ├── api/main.py             # FastAPI: GET /health, POST /rank
    ├── ui/app.py               # Streamlit alternative UI
    └── tests/                  # pytest unit tests
```

---

## How it works (end to end)

```
 JD PDF + resume PDFs
        │
        ▼
 [1] parsing.py ──► raw text per file (+ low-text warnings), resume sections, bullet chunks
        │
        ├──► [2] extraction.py + skill_vocab.py ──► JD required / preferred skills; each resume's skills
        │             │
        │             ▼
        ├──► [3] keyword_match.py ──► BM25 score + matched/missing required skills + coverage
        │
        ├──► [4] semantic_match.py ─► per-requirement best-matching resume chunk + semantic score
        │
        ▼
 [5] fusion.py ──► min-max normalise → weighted final score → sorted ranking
        │
        ├──► [6] explain.py ──► template explanation for top 3
        └──► [7] bias_check.py ─► heuristic flags on the JD
        │
        ▼
   JSON result  →  FastAPI  →  React app (or Streamlit)
```

### 1. Parsing — `parsing.py`
- `extract_text()` uses `pdfplumber` page by page. Pages that fail to extract are skipped rather than crashing; pages are joined with a form-feed marker so page boundaries are preserved.
- Some PDFs emit literal `(cid:127)` text for unmapped bullet glyphs; these are cleaned (turned into `•` at line start, dropped elsewhere).
- `has_low_text_extraction()` flags any file with fewer than 100 characters (likely a scanned image) as `low_text_extraction` — the run continues and surfaces a warning.
- `split_resume_sections()` finds headers (Skills / Experience / Projects / Education) with regex. If fewer than two headers are found, the whole resume is treated as one blob.
- `chunk_resume()` produces the units used for semantic matching: bullet lines from Experience/Projects first, sentence/line fallback otherwise, then Skills/Education sentences; de-duplicated in order.

### 2. Skill vocabulary & extraction — `skill_vocab.py`, `extraction.py`
- `SKILL_VOCAB` maps ~50 canonical skills (javascript, react, nodejs, express, mongodb, docker, aws, rest_api, ci_cd, …) to their aliases (`"nodejs": ["node", "nodejs", "node.js", "node js"]`).
- Matching is **word-boundary aware** (`(?<![a-zA-Z0-9])alias(?![a-zA-Z0-9])`), so `java` never matches inside `javascript`.
- `RELATED_SKILLS` (e.g. express → nodejs) is only supporting context — **never counted as a direct match**.
- `EQUIVALENT_TOOL_GROUPS` (React/Vue/Angular, MongoDB/PostgreSQL/MySQL, Express/Django/Flask/FastAPI/Spring) is used only by the bias checker.
- The JD is split heuristically into **required** and **preferred** text using line-start headers ("Required", "Must-have", "Preferred", "Nice to have", "Bonus", …). With no headers, everything counts as required. A skill in both buckets stays "required".

### 3. Keyword matching — `keyword_match.py`
- Tokenises with `[a-zA-Z0-9+#.-]+` (keeps `c++`, `node.js`, `c#`), builds a `BM25Okapi` index over all resumes, and scores the JD as the query.
- `skill_overlap()` computes, per resume, matched/missing required skills, matched preferred skills, and **required-skill coverage** (matched ÷ required).

### 4. Semantic matching — `semantic_match.py`
- Loads `all-MiniLM-L6-v2` **once** at import.
- Splits the JD into requirement statements (bullets, else sentences; headers and fragments dropped; falls back to the whole JD).
- For each requirement, computes cosine similarity against every resume chunk and keeps the **maximum** — the best evidence. A resume's semantic score is the **mean of those maxima**.
- This is why "built REST APIs with Express and MongoDB" can support a "Node.js backend" requirement even without the literal phrase. The best chunk is kept verbatim so explanations quote real resume text.

### 5. Fusion & ranking — `fusion.py`
Both scores are min-max normalised **within the current batch** (identical scores → 0.5 to avoid divide-by-zero), then:

```
keyword_component = 0.70 · keyword_norm + 0.30 · required_skill_coverage
final_score       = 0.40 · keyword_component + 0.60 · semantic_norm
```

Semantic gets more weight (catches paraphrases); the coverage term stops strong semantic "vibes" from hiding a missing required skill. Sorted descending; ties broken by `resume_id`. The score is **relative to the batch**, not an absolute employability score.

### 6. Explanations — `explain.py`
For the top 3 only, a fixed template reports rank, score, matched/total required skills, missing skills, preferred skills, the two normalised sub-scores, and quotes the highest-similarity requirement ↔ resume chunk. Nothing is invented; no LLM.

### 7. Bias check (bonus) — `bias_check.py`
Pure heuristics, advisory only (never affects ranking):
- Internship JD asking for ≥2 years of experience.
- Gendered/exclusionary words ("rockstar", "ninja", "salesman", "young and energetic", …) and culture-fit buzzwords ("digital native", "wear many hats", …).
- Narrow tooling: a single tool from an equivalent group required with no "or equivalent / similar / comparable" wording.

### 8. Pipeline & output — `pipeline.py`
`run_pipeline(jd_path, resume_paths)` returns:

```json
{
  "jd_required_skills": {"required": [...], "preferred": [...]},
  "ranking": [{
    "rank": 1, "resume_id": "Resume_01_Aditi_Sharma", "score": 0.87,
    "keyword_norm": 0.91, "semantic_norm": 0.84, "required_skill_coverage": 0.875,
    "matched_skills": [...], "missing_skills": [...], "matched_preferred": [...],
    "requirement_evidence": [...],      // top 3 only
    "explanation": "..."                // top 3 only
  }],
  "parsing_warnings": [...],
  "bias_flags": [...]
}
```

### 9. API — `api/main.py`
- `GET /health` → `{"status": "ok"}`
- `POST /rank` — multipart form: `jd` (one PDF) + `resumes` (many PDFs). Files go to a temp dir, `run_pipeline` runs, JSON is returned. CORS is wide open (`*`) for demo purposes — tighten before real deployment.

### 10. Frontends
- **React app (`frontend/`)**: `App.jsx` holds state (JD file, resume files, result, loading, error). `api.js` posts a `FormData` to `${VITE_API_BASE_URL}/rank` (default `http://localhost:8000`). After a run it shows the detected JD skills + warnings + bias flags, the full ranking table, top-3 explanation cards, and a "Why is X ranked above Y?" comparison panel (computed client-side from the existing response). A WebGPU shard animation (`AeroShards`) forms the background.
- **Streamlit app (`shortlist-engine/ui/app.py`)**: same flow and comparison feature in a single Python file; calls `run_pipeline` directly (no API needed).

---

## Getting started

Prerequisites: Python 3.11+, Node.js (for the React app). First run needs internet once to download the embedding model weights; afterwards it works offline.

```bash
cd shortlist-engine

./run.sh            # rank the PDFs in data/jd and data/resumes, print JSON
./run.sh api        # FastAPI on http://localhost:8000
./run.sh ui         # Streamlit UI
./run.sh frontend   # React dev server (run alongside ./run.sh api)
./run.sh test       # pytest
```

Manual setup:
```bash
cd shortlist-engine
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
uvicorn api.main:app --reload --port 8000

# in another terminal
cd frontend
cp .env.example .env.local      # optional; sets VITE_API_BASE_URL
npm install
npm run dev
```

Then open the Vite URL (usually http://localhost:5173), upload a JD PDF plus resume PDFs, and click **Run ranking**.

## Testing
`pytest tests/ -v` (from `shortlist-engine/`) covers parsing, keyword/skill matching, fusion (including tie-breaking and the coverage blend), explanations, and the bias checker. Tests don't need the embedding model, so they run fast.

## Limitations
- Skill detection is limited to the hand-curated vocabulary (currently tuned for a full-stack/JS internship role); extend `SKILL_VOCAB` for other roles.
- Required/preferred classification and section splitting are heuristics based on header keywords.
- Scanned/image-only PDFs aren't OCR'd — they're flagged and ranked on limited evidence.
- Scores are relative within a batch and not comparable across runs.
- Bias flags are advisory, keyword-based, and can miss or over-flag.
