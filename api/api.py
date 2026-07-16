#!/usr/bin/env python3
"""
api.py — Stage 4: the bridge between the React app and the Python pipeline.

WHY THIS EXISTS
---------------
The Atlas is a browser app (JavaScript). The parser and narrator are Python.
Browsers can't call Python functions. This server is the translator: React
makes HTTP requests, FastAPI runs the Python, JSON comes back.

    React  ──HTTP──>  api.py  ──>  parser.py     (Stage 1)
                              ──>  narrator/     (Stage 3, Zion's — later)

RUN IT
------
    pip install fastapi uvicorn python-multipart
    uvicorn api:app --reload --port 8000

    Docs at http://localhost:8000/docs  (FastAPI generates these free —
    hand that URL to Kevin and Adam so they can see the endpoints)

ENDPOINTS
---------
    GET  /health          is the server up?
    POST /api/parse       upload an .xls  -> clean table as JSON
    GET  /api/atlas       the last-parsed table (or the mock)
"""

import io
import sys
from pathlib import Path

import pandas as pd
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware

# Import the parser we already built. Same code the CLI uses — one source of
# truth, so a fix in parser.py fixes both paths.
sys.path.insert(0, str(Path(__file__).parent.parent / "pipeline"))
from parser import load_results, drop_dead_wells, direction_label, trial_from_sample_id, CLEAN_COLUMNS  # noqa: E402


app = FastAPI(title="Expression Atlas API")

# The React dev server runs on :5173, this runs on :8000. Different ports =
# different origins, and browsers block that by default. CORS opens the door.
# NOTE: allow_origins=["*"] is fine for local dev. Lock it down before anything
# goes on a real network.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory cache of the most recent parse. Good enough for a demo — resets
# when the server restarts. If we ever need it to survive, that's what S3 is for.
_last_table: pd.DataFrame | None = None


def parse_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """
    The same aggregation logic as parser.py's parse(), but operating on an
    already-loaded DataFrame instead of a file path.

    Reminder of the two non-obvious rules (both discovered from the real file):
      1. RQ is computed per SAMPLE, not per well — every replicate row carries
         the same RQ. Don't average it. Spread comes from Ct, which does vary.
      2. Reference genes (Actin/18S/EF1a) have NO RQ at all — RQ only exists
         for targets normalized against them. Detect and exclude automatically.
    """
    df = drop_dead_wells(df)

    has_rq = df.groupby("Target Name")["RQ"].apply(lambda s: s.notna().any())
    target_genes = has_rq[has_rq].index.tolist()
    df = df[df["Target Name"].isin(target_genes)]

    rows = []
    for (gene, sample), grp in df.groupby(["Target Name", "Sample Name"]):
        rq = grp["RQ"].dropna()
        if rq.empty:
            continue
        rq_value = float(rq.iloc[0])

        ct = pd.to_numeric(grp["Cт"], errors="coerce").dropna()
        ddct = pd.to_numeric(grp["ΔΔCт"], errors="coerce").dropna()

        rows.append({
            "gene": gene,
            "sample_id": str(sample),
            "trial": trial_from_sample_id(sample),
            "salt_level": None,     # <- sample sheet, once it exists
            "timepoint_h": None,    # <- sample sheet, once it exists
            "fold_change": round(rq_value, 4),
            "fold_change_sd": round(float(ct.std()), 4) if len(ct) > 1 else None,
            "n_replicates": int(len(ct)),
            "ddct": round(float(ddct.mean()), 4) if not ddct.empty else None,
            "direction": direction_label(rq_value),
            "flagged": bool((grp.get("HIGHSD") == "Y").any()),
        })

    return pd.DataFrame(rows, columns=CLEAN_COLUMNS)


def to_records(df: pd.DataFrame) -> list[dict]:
    """DataFrame -> JSON-safe list of dicts. NaN isn't valid JSON; None is."""
    return df.where(pd.notna(df), None).to_dict(orient="records")


@app.get("/health")
def health():
    """Cheap way for the front-end to check the server's alive."""
    return {"status": "ok", "has_data": _last_table is not None}


@app.post("/api/parse")
async def parse_upload(file: UploadFile = File(...)):
    """
    Upload an instrument export, get the clean table back as JSON.
    This is the endpoint behind the live demo: Dr. Todd drops a file, the
    Atlas builds.
    """
    global _last_table

    if not file.filename.lower().endswith((".xls", ".xlsx")):
        raise HTTPException(400, "Expected a .xls or .xlsx instrument export")

    contents = await file.read()

    try:
        # load_results wants a path-like; BytesIO works for pandas too
        df = load_results(io.BytesIO(contents))
    except Exception as e:
        raise HTTPException(400, f"Couldn't read that file: {e}")

    try:
        clean = parse_dataframe(df)
    except Exception as e:
        raise HTTPException(500, f"Parse failed: {e}")

    if clean.empty:
        raise HTTPException(422, "No target genes with RQ values found in that export")

    _last_table = clean

    return {
        "filename": file.filename,
        "row_count": len(clean),
        "genes": sorted(clean["gene"].unique().tolist()),
        # Honest signal to the front-end: the Atlas can't label its axes yet.
        "has_conditions": bool(clean["salt_level"].notna().any()),
        "rows": to_records(clean),
    }


@app.get("/api/atlas")
def get_atlas():
    """
    The last-parsed table. Falls back to the mock CSV so the front-end always
    has something to render — Kevin and Adam can build against this without
    ever uploading a file.
    """
    if _last_table is not None:
        df = _last_table
        source = "uploaded"
    else:
        mock = Path(__file__).parent.parent / "public" / "clean_table_mock.csv"
        if not mock.exists():
            raise HTTPException(404, "No data parsed yet and no mock CSV found")
        df = pd.read_csv(mock)
        source = "mock"

    return {
        "source": source,
        "row_count": len(df),
        "genes": sorted(df["gene"].unique().tolist()),
        "has_conditions": bool(df["salt_level"].notna().any()),
        "rows": to_records(df),
    }
