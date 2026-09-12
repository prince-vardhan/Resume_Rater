# Smart Shortlisting Engine — Frontend

A React + Vite client for the `shortlist-engine` FastAPI backend. Full feature
parity with the Streamlit demo (`shortlist-engine/ui/app.py`), which still
works standalone if you ever want it:

- Upload one JD PDF + multiple resume PDFs
- Required/preferred skills detected in the JD
- Parsing warnings (e.g. scanned/image-only PDFs) and JD bias-phrasing flags
- Full ranked candidate table (score, keyword/semantic sub-scores, required-
  skill coverage, missing required skills)
- Top-3 evidence-grounded explanation cards (quoting real resume text)
- "Why is X ranked above Y?" comparison, computed client-side from the
  already-fetched ranking data — no extra request, no LLM

## Run it

1. Start the backend first (from `shortlist-engine/`):
   ```bash
   ./run.sh api
   # or: uvicorn api.main:app --reload --port 8000
   ```
2. In this directory:
   ```bash
   npm install
   npm run dev
   ```
3. Open the printed local URL (default `http://localhost:5173`).

If your API runs somewhere other than `http://localhost:8000`, copy
`.env.example` to `.env.local` and set `VITE_API_BASE_URL` accordingly.

## Build for production

```bash
npm run build
npm run preview   # serve the production build locally to sanity-check it
```
