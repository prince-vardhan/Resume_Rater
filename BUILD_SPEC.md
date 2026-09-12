# Smart shortlisting engine — build spec (v2)

## Context

Hackathon deliverable: given one job description and a batch of 15–18 resumes (PDFs), rank all candidates from best to worst fit with a final score, and produce a short explanation for the top 3 (matched skills + missing skills).

**Hard constraint:** the ranking must come from genuine keyword matching (BM25 + skill vocabulary) combined with genuine semantic matching (embeddings + cosine similarity) — not from asking an LLM to score a resume out of 100.

**No external APIs of any kind are allowed for this hackathon** — no LLM API calls, hosted embedding APIs, or anything that leaves the machine during inference. Everything must run locally: local PDF parsing, a local BM25 implementation, and a locally-run open-weight embedding model (`sentence-transformers` with `all-MiniLM-L6-v2`). The model weights may be downloaded once during setup, then the model runs locally/offline. Explanations and bias-flagging are template/rule-based, not LLM calls.

## Tech stack

- Python 3.11+
- `pdfplumber` — resume/JD PDF text extraction
- `rank_bm25` — BM25 keyword scoring
- `sentence-transformers` (`all-MiniLM-L6-v2`) — local embeddings on CPU
- `numpy` — score fusion math
- `fastapi` + `uvicorn` — API layer
- `streamlit` — optional recruiter UI
- No external APIs

## Project structure

```
shortlist-engine/
  data/
    jd/                     # sample JD PDF
    resumes/                # sample resume PDFs
  src/
    parsing.py              # PDF -> text, resume -> sections/chunks
    skill_vocab.py          # skill/tool vocabulary + alias map
    extraction.py            # JD -> required skills, resume -> mentioned skills
    keyword_match.py         # BM25 scoring + explicit skill overlap
    semantic_match.py        # requirement-to-resume-chunk embeddings + cosine similarity
    fusion.py                # normalize + combine + rank
    explain.py               # top-3 explanation generation
    bias_check.py            # bonus: narrow/biased JD phrasing checks
    pipeline.py              # orchestrates all stages end to end
  api/
    main.py                 # FastAPI app: POST /rank
  ui/
    app.py                  # Streamlit demo (optional)
  tests/
    test_fusion.py
    test_keyword_match.py
  requirements.txt
  README.md
```

## Stage-by-stage spec

### 1. `parsing.py`

`extract_text(pdf_path) -> str`
- Use pdfplumber to extract text from every page.
- Preserve page boundaries where practical so evidence can later be traced back to a page.
- Add a basic extraction sanity check:
  ```python
  text = extract_text(path)
  if len(text.strip()) < 100:
      flag = "low_text_extraction"
  ```
- The system should not crash because a resume is image-only or badly formatted. Instead, return a warning/flag and continue where possible.

`split_resume_sections(text) -> dict`
- Best-effort split into: `skills`, `experience`, `projects`, `education`.
- Use case-insensitive regex/header detection against common section names.
- Do not over-engineer this stage. If section headers are not detected, fall back to the full text as one section.

**Resume chunking**
- Also provide a lightweight chunking function for semantic matching: `chunk_resume(text_or_sections) -> list[str]`.
- Prefer experience/project bullets as individual chunks. Fall back to short text blocks when bullets cannot be reliably detected.
- The goal is to compare JD requirement ↔ resume bullet/chunk rather than relying only on one embedding of the entire resume.

### 2. `skill_vocab.py`

Create a hand-curated dictionary:

```python
SKILL_VOCAB = {
    "javascript": [...],
    "typescript": [...],
    "react": [...],
    "node.js": [...],
    "express": [...],
    "mongodb": [...],
    "sql": [...],
    "git": [...],
    "docker": [...],
    "aws": [...],
    "rest_api": [...],
}
```

- Seed it from the sample JD/resumes and common full-stack/JavaScript ecosystem terms.
- Example:
  ```python
  "express": ["express", "express.js", "expressjs"],
  "mongodb": ["mongodb", "mongo", "mongo db"],
  "react": ["react", "reactjs", "react.js"],
  ```
- Use word-boundary-aware matching. Do not use naive substring matching because terms such as `java`, `c`, `r`, and `go` can create false positives.
- Recommended pattern: `pattern = r"(?<!\w)" + re.escape(alias) + r"(?!\w)"`
- Optionally maintain related-skill relationships:
  ```python
  RELATED_SKILLS = {
      "express": ["node.js", "rest_api"],
      "react": ["javascript", "frontend"],
      "mongodb": ["node.js", "backend"],
  }
  ```
- Related skills should not count as direct skill matches. They are supporting semantic context only.

### 3. `extraction.py`

`extract_required_skills(jd_text, vocab) -> list[str]`
- Regex-match vocabulary aliases against the JD.
- Also identify which skills appear in required/must-have context vs. preferred/nice-to-have/bonus context.
- Use heuristic section/block detection. Do not attempt to build a full NLP classifier. The implementation should explicitly treat required/preferred classification as heuristic.

`extract_resume_skills(resume_text, vocab) -> list[str]`
- Apply the same normalized, word-boundary-aware matching to each resume.
- Return canonical skill names, not aliases.

### 4. `keyword_match.py`

- Build a BM25 index using `rank_bm25.BM25Okapi` over the resume corpus.
- Use consistent text preprocessing and tokenization. Recommended basic tokenizer: `re.findall(r"[a-zA-Z0-9+#.-]+", text.lower())`.
- Normalize common variants before BM25 tokenization where useful.

`keyword_score(jd_text, resume_texts) -> ...`
- For every resume, compute BM25 score against the JD and explicit required-skill overlap.
- Return: raw BM25 score, matched required skills, missing required skills, required-skill coverage.
- The explicit skill evidence is passed directly to `explain.py`.

### 5. `semantic_match.py`

- Load `all-MiniLM-L6-v2` exactly once at module level: `MODEL = SentenceTransformer("all-MiniLM-L6-v2")`. Do not reload the model for each candidate or pipeline call.

**Primary semantic matching strategy**

Do not rely only on `embedding(JD) ↔ embedding(whole resume)`, because long resumes can exceed the model's input limit and lose relevant information through truncation. Instead, use requirement-level and chunk-level matching:

```
JD                              Resume
 ├── requirement 1                ├── experience bullet 1
 ├── requirement 2                ├── experience bullet 2
 ├── requirement 3                ├── project bullet 1
 └── requirement N                ├── project bullet 2
                                   └── ...
```

For each JD requirement:

```
requirement_i
      ↓
embedding(requirement_i)
      ↓
cosine similarity against every resume chunk
      ↓
maximum similarity = best evidence for requirement_i
```

Then calculate the resume's semantic score as the average of the best per-requirement similarities:

```python
requirement_score_i = max(
    cosine_similarity(requirement_i, resume_chunk_j)
    for resume_chunk_j in resume_chunks
)

semantic_score = mean(requirement_score_i for every requirement_i)
```

**Evidence output**
- For each resume, also return the best-matching chunk for each requirement, including its similarity score. Example:
  ```
  JD requirement: "Build REST APIs using Express.js"
  Best resume evidence: "Developed REST APIs using Node.js and Express..."
  Similarity: 0.84
  ```
- This evidence is used by `explain.py` and must come directly from the resume text rather than being invented.
- If requirement extraction is unavailable or produces no useful requirements, fall back to section/chunk-level comparison against the full JD embedding.

### 6. `fusion.py`

- Normalize keyword and semantic scores independently within the current batch using min-max normalization.
- Constants:
  ```python
  KEYWORD_WEIGHT = 0.40
  SEMANTIC_WEIGHT = 0.60
  ```
- Base formula:
  ```python
  final_score = (
      KEYWORD_WEIGHT * keyword_norm +
      SEMANTIC_WEIGHT * semantic_norm
  )
  ```

**Keyword component enhancement**

To prevent semantic similarity from overriding hard missing skills too easily, incorporate explicit required-skill coverage into the keyword component:

```python
keyword_component = (
    0.70 * keyword_norm +
    0.30 * required_skill_coverage
)

final_score = (
    KEYWORD_WEIGHT * keyword_component +
    SEMANTIC_WEIGHT * semantic_norm
)
```

This still uses genuine BM25 and genuine embedding/cosine similarity. The skill vocabulary is an explicit supporting lexical signal.

**Safe min-max normalization**

Handle identical scores to avoid division by zero:

```python
def minmax(scores):
    lo = min(scores)
    hi = max(scores)
    if hi == lo:
        return [0.5] * len(scores)
    return [(x - lo) / (hi - lo) for x in scores]
```

The final score is a relative score within the current candidate batch, not a universal employability score.

`rank(candidates) -> list[dict]`
- Sort descending by `final_score`. Each result should contain at minimum:
  ```json
  {
    "resume_id": "resume_01",
    "rank": 1,
    "score": 0.87,
    "keyword_norm": 0.91,
    "semantic_norm": 0.84,
    "required_skill_coverage": 0.875,
    "matched_skills": ["react", "node.js", "mongodb"],
    "missing_skills": ["docker"]
  }
  ```

### 7. `explain.py`

- Only generate explanations for the top 3.
- Use structured evidence already computed. No LLM/API call.
- Example template:
  ```
  Ranked #{rank} with a score of {score:.2f}. Matched
  {n_matched}/{n_required} required skills directly
  ({matched_skills}). Semantic matching found supporting evidence
  against the JD requirements, with a normalized semantic score of
  {semantic_norm:.2f}. Missing: {missing_skills or "none"}.

  Best evidence:
  "{best_resume_chunk}"
  ```
- The explanation must not invent experience, skills, or achievements.
- `best_resume_chunk` must be the actual resume bullet/chunk associated with the highest relevant requirement-level semantic similarity.
- Output per candidate:
  ```json
  {
    "rank": 1,
    "score": 0.87,
    "matched_skills": ["react", "node.js", "mongodb"],
    "missing_skills": ["docker"],
    "explanation": "..."
  }
  ```
- Prefer wording such as "evidence-grounded ranking" or "transparent scoring with lexical and semantic evidence" rather than claiming that cosine similarity itself fully explains why two texts are similar.

### 8. `bias_check.py` — bonus

- Pure heuristic checks only.
- **Check for exclusionary/gendered wording** — examples: "rockstar", "ninja", "young and energetic", other curated exclusionary/gender-coded terms.
- **Check unrealistic experience requirements** — use a regex to identify years-of-experience requirements that appear excessive for an intern role.
- **Check narrow tooling requirements** — flag cases where the JD requires one specific tool but the vocabulary contains known equivalents and the JD does not use language such as "or equivalent", "similar framework", "comparable technology".
- Return a short list of heuristic flags. Do not make the bias checker a blocking decision.

### 9. `pipeline.py`

`run_pipeline(jd_path, resume_paths) -> dict`

Call every stage in order:

```
JD PDF
  ↓
PDF extraction
  ↓
JD skill extraction + requirement extraction
  ↓
Resume PDF extraction
  ↓
Resume sectioning + chunking
  ↓
Resume skill extraction
  ↓
BM25 scoring
  ↓
Requirement ↔ resume bullet/chunk semantic matching
  ↓
Score normalization
  ↓
Score fusion
  ↓
Ranking
  ↓
Top-3 evidence-grounded explanations
  ↓
Optional bias flags
```

Return the full ranked list, top-3 explanations, parsing warnings, and optional bias flags. This is the single function used by both the API and test/demo scripts.

### 10. `api/main.py`

- Implement `POST /rank`.
- Use `multipart/form-data` with `jd: UploadFile` and `resumes: List[UploadFile]`.
- Save uploaded files to a temporary directory and call `run_pipeline(jd_path, resume_paths)`.
- For unit/local testing, the Python pipeline function may also accept filesystem paths directly.
- No authentication or persistence is required for the hackathon demo.

### 11. `ui/app.py` — optional bonus

Streamlit page should provide:
- JD upload
- Multiple resume upload
- Run ranking button
- Ranked candidate table
- Top-3 explanation cards
- Optional comparison control for "candidate X vs. candidate Y — why X ranked above Y"

The comparison should reuse the same evidence from `explain.py` rather than introducing an LLM-based chat layer.

## Build order

Build in this order and get the core working end to end early:

1. `parsing.py` + `skill_vocab.py`
2. Resume chunking
3. `extraction.py`
4. `keyword_match.py`
5. `semantic_match.py` using requirement ↔ resume bullet/chunk matching
6. `fusion.py`
7. `explain.py`
8. `api/main.py`
9. Bonus features only after stages 1–8 work

Do not build the whole-document semantic approach first and plan to rewrite it later. Requirement-to-chunk matching should be the primary semantic design from the start.

## Testing checklist before demo

- [ ] Full batch of 15–18 resumes runs without crashing on the messiest formatted resume.
- [ ] Low-quality/scanned PDFs are detected and flagged instead of silently producing misleading rankings.
- [ ] Scores show meaningful spread without being dominated by one outlier.
- [ ] Min-max normalization handles identical scores without division by zero.
- [ ] A resume using different words for the same concept (for example, Express/Node.js backend) still receives reasonable semantic credit.
- [ ] Direct skill matches and semantic/related-skill evidence are clearly distinguished.
- [ ] Top-3 explanations correctly list both matched and missing required skills.
- [ ] Explanations quote/surface actual resume evidence rather than inventing prose.
- [ ] Long resumes are chunked so semantic matching does not depend only on the beginning of the document.
- [ ] BM25 tokenization does not create false positives for short programming-language names.
- [ ] Required/preferred skill classification is treated as heuristic.
- [ ] API accepts one JD and 15–18 resume files in one request.
- [ ] The embedding model is loaded once, not once per candidate.

## How to explain the ranking to judges

The ranking has three transparent evidence sources:

**1. Keyword matching — BM25**

The JD is treated as a query against the resume corpus. BM25 rewards terms that occur in a resume and are especially informative relative to the other resumes. The system also performs explicit vocabulary-based skill matching, allowing aliases such as `Express.js = ExpressJS = Express`, `React = ReactJS = React.js`, `MongoDB = Mongo = Mongo DB`.

**2. Semantic matching — local embeddings**

The JD is broken into requirement statements and each resume is broken into experience/project bullets or short chunks. The system computes JD requirement ↔ resume bullet/chunk similarity using local sentence embeddings and cosine similarity. For each requirement, the strongest matching resume chunk is used as the semantic evidence. The overall semantic score is the average of those best requirement-level matches. This allows semantically similar evidence to receive credit even when the exact JD wording is absent.

**3. Score fusion**

The normalized keyword and semantic signals are combined: 40% keyword component + 60% semantic component = final ranking score. The weights are configurable constants rather than learned or hidden inside an LLM.

## Efficiency expectations

For a hackathon batch of 15–18 resumes, performance should be more than adequate on a normal laptop CPU. BM25, skill extraction, cosine calculations, and score fusion are lightweight. The main startup/inference cost is the local transformer model.

The important optimization is to load the model once: `MODEL = SentenceTransformer("all-MiniLM-L6-v2")`. Do not instantiate the model inside `semantic_score()` for every candidate.

The main engineering risks are therefore ranking robustness and PDF quality, not computational scale.

## Key design decision

The core semantic comparison is JD requirement ↔ resume bullet/chunk, not merely whole JD ↔ whole resume. This makes the system more robust to long resumes, better at identifying the evidence behind a match, and much easier to explain during the hackathon demo.
