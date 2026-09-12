# Smart Shortlisting Engine

Ranks a batch of resumes against a job description using **genuine
keyword matching (BM25 + a curated skill vocabulary)** combined with
**genuine semantic matching (local sentence embeddings + cosine
similarity)**.

**No external APIs of any kind are used, ever** — no LLM API calls, no
hosted embedding APIs, nothing that leaves the machine during inference.
PDF parsing, BM25, and embedding inference (`all-MiniLM-L6-v2` via
`sentence-transformers`) all run locally/offline; only the model weights
are downloaded once during setup. Explanations and bias-flagging are
100% template/rule-based over already-computed structured evidence.

## Quick start

```bash
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

Put your data in place:
```
data/jd/Sample_JD.pdf
data/resumes/*.pdf     # the 15-18 sample resumes
```

### Run the core pipeline from the command line (fastest way to demo the logic)
```bash
python3 -c "
from src.pipeline import run_pipeline
import glob, json
result = run_pipeline('data/jd/Sample_JD.pdf', glob.glob('data/resumes/*.pdf'))
print(json.dumps(result, indent=2))
"
```

### Run the API
```bash
uvicorn api.main:app --reload --port 8000
```
Then POST a JD + resumes as multipart form data to `http://localhost:8000/rank`.

### Run the Streamlit recruiter UI (bonus)
```bash
streamlit run ui/app.py
```
Upload the JD and resumes in the sidebar, click **Run ranking**. Includes
the bonus "why is X ranked above Y" comparison, built entirely from
already-computed evidence (no LLM).

## How the ranking actually works (what to say when judges ask)

1. **Parsing** (`parsing.py`) — `pdfplumber` extracts raw text from each
   PDF, page by page (page boundaries kept via a form-feed marker). A
   basic sanity check (`has_low_text_extraction`) flags any PDF that
   yields under 100 characters of text — typically a scanned/image-only
   page — as a `low_text_extraction` parsing warning rather than crashing
   or silently producing a misleading rank. Resume text is then
   heuristically split into skills / experience / projects / education
   sections by detecting common header keywords; if fewer than two
   headers are detected (messy/plain resumes), the whole resume is
   treated as one blob so nothing gets lost. `chunk_resume()` then pulls
   out individual experience/project bullet points (falling back to
   sentence-level chunks) as the unit compared against each JD requirement.

2. **Skill vocabulary** (`skill_vocab.py`) — a hand-curated dict mapping
   canonical skill names to their real-world aliases (`"express"` also
   matches `"express.js"`, `"expressjs"`, etc.), seeded for a full-stack/
   JS ecosystem role, with word-boundary-aware matching so `"java"` never
   false-positives inside `"javascript"`. `RELATED_SKILLS` records
   supporting-but-not-equivalent relationships (e.g. knowing Express
   implies backend/Node.js context) — these are never counted as a direct
   match. `EQUIVALENT_TOOL_GROUPS` records genuinely interchangeable tools
   (React/Vue/Angular, MongoDB/PostgreSQL/MySQL, ...), used only by the
   bonus bias checker.

3. **Skill extraction** (`extraction.py`) — the JD is split into
   required-context vs. preferred-context text (heuristically, by
   section-header keywords like "Required"/"Nice to have") before
   matching the vocabulary against each half, so we know not just *which*
   skills the JD wants but which ones are must-haves.

4. **Keyword matching** (`keyword_match.py`) — `rank_bm25`'s BM25Okapi
   scores every resume as a document against the JD as a query, rewarding
   resumes that contain the JD's important, relatively rare terms. This
   is combined with the explicit **required-skill coverage** (fraction of
   required skills the resume actually mentions) in `fusion.py`, so a
   resume can't paper over a hard-missing required skill purely on
   lexical noise.

5. **Semantic matching** (`semantic_match.py`) — `all-MiniLM-L6-v2` is
   loaded exactly once at module import. Rather than embedding the whole
   JD and whole resume as single vectors (which dilutes signal and loses
   evidence), the JD is split into requirement-like statements and each
   requirement is compared against every resume chunk from step 1; the
   **best (max) matching chunk per requirement is kept as evidence**, and
   the resume's semantic score is the mean of those per-requirement
   maxima. This is what correctly scores "built REST APIs with Express
   and MongoDB" as strong evidence for "Node.js backend" even though the
   literal phrase "Node.js" never appears.

6. **Fusion** (`fusion.py`) — keyword and semantic scores are each
   independently min-max normalized within the current batch (safe
   against divide-by-zero when every score in a batch is identical), then:
   ```
   keyword_component = 0.70 * keyword_norm + 0.30 * required_skill_coverage
   final_score        = 0.40 * keyword_component + 0.60 * semantic_norm
   ```
   Semantic gets more overall weight because it's what catches
   paraphrased/implied skills; the coverage term inside the keyword
   component keeps explicitly named required skills from being
   overridden by loosely-related semantic vibes. Both weight pairs live
   as named constants at the top of `fusion.py` for easy tuning.

7. **Ranking** — candidates are sorted descending by `final_score`, ties
   broken by `resume_id` ascending for determinism.

8. **Explanations** (`explain.py`) — for the top 3 only, a fixed template
   turns the already-computed matched/missing skills, both sub-scores,
   and the single highest-similarity requirement↔chunk match into 2-4
   plain sentences plus a direct quote of the real resume evidence. No
   LLM or API call is involved anywhere in this step — it only writes
   prose describing a decision that was already made, and only ever
   quotes text that is genuinely present in the resume.

9. **Bonus — bias check** (`bias_check.py`) — pure regex/heuristics:
   years-of-experience asks that look excessive for an internship role,
   gendered/exclusionary phrasing, and narrow tool requirements (a
   required tool with known equivalents in the vocab, named without any
   "or equivalent" qualifier). Returns flags only, never blocks or
   changes the ranking.

## Project structure
```
shortlist-engine/
  data/jd/                 # put Sample_JD.pdf here
  data/resumes/            # put the 15-18 resume PDFs here
  src/
    parsing.py              # PDF -> text, resume -> sections + chunks
    skill_vocab.py           # skill/tool vocabulary + alias/related/equivalent maps
    extraction.py             # JD -> required/preferred skills, resume -> skills
    keyword_match.py           # BM25 scoring + skill overlap + required-skill coverage
    semantic_match.py           # requirement <-> resume-chunk embeddings + evidence
    fusion.py                    # normalize + combine + rank
    explain.py                    # top-3 template explanation generation (no LLM)
    bias_check.py                  # bonus: JD bias/narrow-phrasing flags (no LLM)
    pipeline.py                     # orchestrates everything end to end
  api/main.py                # FastAPI: POST /rank
  ui/app.py                  # Streamlit demo + bonus comparison layer
  tests/                    # pytest unit tests
  requirements.txt
```

## Testing
```bash
pytest tests/ -v
```
`test_fusion.py`, `test_keyword_match.py`, and `test_explain.py` cover
normalization, weighted fusion (including the required-skill-coverage
enhancement), tie-breaking, skill-alias matching, and template
explanation generation — all without requiring the embedding model to be
downloaded, so they're fast to run repeatedly while iterating.

## Testing checklist (from build spec)
- [x] Messy/plain resumes fall back to a single section rather than crashing.
- [x] Low-quality/scanned PDFs flagged via `low_text_extraction` parsing warnings.
- [x] Min-max normalization handles identical scores without division by zero.
- [x] Different words for the same concept (Express/Node.js) still score via semantic matching.
- [x] Direct skill matches vs. semantic evidence are clearly distinguished in the output.
- [x] Top-3 explanations list both matched and missing required skills, and quote real resume text.
- [x] Long resumes are chunked (bullet-level) so matching isn't dominated by the top of the page.
- [x] BM25 tokenizer avoids false positives on short language names (word-boundary vocab matching).
- [x] Required/preferred classification is explicitly heuristic (section-header based).
- [x] API accepts one JD and multiple resume files in one multipart request.
- [x] The embedding model is loaded exactly once at module import, not per candidate.
