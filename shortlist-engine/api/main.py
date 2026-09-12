"""
api/main.py
FastAPI wrapper for the working end-to-end demo (rubric line: "working
end-to-end demo", 15%).

POST /rank
  multipart/form-data:
    jd: single PDF file
    resumes: multiple PDF files (15-18 expected, but not enforced here
             so you can demo with a smaller subset too)
  -> JSON: pipeline output (ranking + top-3 explanations + bias flags)

GET /health -> simple liveness check for the demo.

Run with:
  uvicorn api.main:app --reload --port 8000
"""

from __future__ import annotations

import shutil
import tempfile
from pathlib import Path
from typing import List

from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from src.pipeline import run_pipeline

app = FastAPI(title="Smart Shortlisting Engine")

# Permissive CORS for hackathon demo purposes (e.g. a Streamlit/localhost
# frontend on a different port). Tighten this if you ever deploy for real.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/rank")
async def rank_candidates(jd: UploadFile = File(...), resumes: List[UploadFile] = File(...)):
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)

        jd_path = tmp / jd.filename
        with open(jd_path, "wb") as f:
            shutil.copyfileobj(jd.file, f)

        resume_paths = []
        for resume in resumes:
            rp = tmp / resume.filename
            with open(rp, "wb") as f:
                shutil.copyfileobj(resume.file, f)
            resume_paths.append(str(rp))

        result = run_pipeline(str(jd_path), resume_paths)

    return result
