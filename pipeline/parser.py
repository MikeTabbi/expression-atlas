#!/usr/bin/env python3
"""
parser.py — Stage 1: instrument export -> clean table

Reads a QuantStudio .xls export and emits the clean table defined in the
data contract. Gene-agnostic: works on C5 today, C3 tomorrow, no code change.

    python parser.py <export.xls> [-o clean_table.csv]

WHAT THIS DOES NOT DO
---------------------
It does not assign salt_level or timepoint_h. Sample IDs are randomized by the
lab (confirmed by Krystal 2026-07: first digit = TRIAL, not salt level; salt is
deliberately not encoded because samples and chamber positions are randomized).
Those labels come from a separate SAMPLE SHEET that the lab fills in. Until that
exists, those columns are emitted empty and the Atlas can't label its axes.
"""

import argparse
import sys
import pandas as pd


# The instrument writes ~7 rows of preamble before the real header.
HEADER_ROW = 7
RESULTS_SHEET = "Results"

# Wells the instrument itself flagged as dead. The machine already does this
# job well — we respect its flags rather than recomputing QC.
HARD_FAIL_FLAGS = ["NOAMP", "EXPFAIL"]

# The final schema. Must match the data contract exactly — Kevin, Adam, and
# Zion all build against these column names.
CLEAN_COLUMNS = [
    "gene", "sample_id", "trial",
    "salt_level", "timepoint_h",
    "fold_change", "fold_change_sd", "n_replicates",
    "ddct", "direction", "flagged",
]

# Thresholds for calling a change real vs. noise.
# PLACEHOLDER — ask the lab for their convention before the poster.
UP_THRESHOLD = 1.2
DOWN_THRESHOLD = 0.83


def load_results(path):
    """Open the export and return the Results sheet with a real header."""
    try:
        xls = pd.ExcelFile(path, engine="calamine")
    except Exception:
        # .xlsx exports need a different engine
        xls = pd.ExcelFile(path, engine="openpyxl")

    if RESULTS_SHEET not in xls.sheet_names:
        raise ValueError(
            f"No '{RESULTS_SHEET}' sheet in {path}. Found: {xls.sheet_names}"
        )

    df = pd.read_excel(xls, sheet_name=RESULTS_SHEET, header=HEADER_ROW)
    # Drop the trailing junk rows the instrument appends
    df = df[df["Target Name"].notna()]
    return df


def drop_dead_wells(df):
    """Remove wells the instrument flagged as failed."""
    before = len(df)
    for flag in HARD_FAIL_FLAGS:
        if flag in df.columns:
            df = df[df[flag] != "Y"]
    dropped = before - len(df)
    if dropped:
        print(f"  dropped {dropped} dead well(s) [{', '.join(HARD_FAIL_FLAGS)}]")
    return df


def direction_label(rq):
    if pd.isna(rq):
        return None
    if rq >= UP_THRESHOLD:
        return "up"
    if rq <= DOWN_THRESHOLD:
        return "down"
    return "flat"


def parse(path):
    print(f"Reading {path}")
    df = load_results(path)
    print(f"  {len(df)} data rows, targets: {sorted(df['Target Name'].unique())}")

    df = drop_dead_wells(df)

    # ---- Reference genes carry no RQ -------------------------------------
    # RQ only exists for target genes normalized against the housekeeping gene.
    # Actin/18S/EF1a rows have RQ = NaN by definition. They're essential to the
    # instrument's math but they are not rows on the Atlas.
    has_rq = df.groupby("Target Name")["RQ"].apply(lambda s: s.notna().any())
    target_genes = has_rq[has_rq].index.tolist()
    reference_genes = has_rq[~has_rq].index.tolist()
    if reference_genes:
        print(f"  reference gene(s) excluded (no RQ): {reference_genes}")
    df = df[df["Target Name"].isin(target_genes)]

    # ---- Aggregate to one row per (gene, sample) -------------------------
    # NOTE: the instrument computes RQ per SAMPLE, not per well — every
    # replicate row carries the same RQ. So we do NOT average RQ (that would
    # be averaging a number with itself). We take it once, and measure
    # replicate spread from Ct, which DOES vary well to well.
    rows = []
    for (gene, sample), grp in df.groupby(["Target Name", "Sample Name"]):
        rq = grp["RQ"].dropna()
        if rq.empty:
            continue
        rq_value = rq.iloc[0]

        ct = pd.to_numeric(grp["Cт"], errors="coerce").dropna()  # 'Undetermined' -> NaN

        ddct = pd.to_numeric(grp["ΔΔCт"], errors="coerce").dropna()

        rows.append({
            "gene": gene,
            "sample_id": str(sample),
            "trial": trial_from_sample_id(sample),
            "salt_level": None,      # <- from the sample sheet, not the export
            "timepoint_h": None,     # <- from the sample sheet, not the export
            "fold_change": round(float(rq_value), 4),
            "fold_change_sd": round(float(ct.std()), 4) if len(ct) > 1 else None,
            "n_replicates": int(len(ct)),
            "ddct": round(float(ddct.mean()), 4) if not ddct.empty else None,
            "direction": direction_label(rq_value),
            "flagged": bool((grp.get("HIGHSD") == "Y").any()),
        })

    clean = pd.DataFrame(rows, columns=CLEAN_COLUMNS)
    print(f"  -> {len(clean)} clean rows ({clean['gene'].nunique()} gene(s))")
    return clean


def trial_from_sample_id(sample_id):
    """
    First digit of the sample ID is the TRIAL number.
    Confirmed by Krystal: it is NOT the salt level. Salt level is not encoded
    in the ID at all — the lab randomizes sample numbers and chamber positions.
    """
    s = str(sample_id).replace(".0", "").strip()
    if s.isdigit() and len(s) == 3:
        return int(s[0])
    return None


def main():
    ap = argparse.ArgumentParser(description="qPCR export -> clean table")
    ap.add_argument("input", help="instrument .xls/.xlsx export")
    ap.add_argument("-o", "--output", default="clean_table.csv")
    args = ap.parse_args()

    try:
        clean = parse(args.input)
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)

    clean.to_csv(args.output, index=False)
    print(f"Wrote {args.output}")

    if clean["salt_level"].isna().all():
        print(
            "\nNOTE: salt_level and timepoint_h are empty.\n"
            "      They come from the lab's sample sheet, which doesn't exist yet.\n"
            "      The Atlas cannot label its axes until it does."
        )


if __name__ == "__main__":
    main()
