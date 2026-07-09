// ============================================================================
// ExpressionAtlas.jsx  —  SCAFFOLD (built by Mike, filled in by Kevin & Adam)
// ============================================================================
// Mike sets this file up and hands it over. Kevin and Adam never touch build
// config, never wire up CSV loading. They only fill in the marked sections.
//
// Data comes in already parsed as an array of row objects, each shaped exactly
// like a row of clean_table_mock.csv:
//   { gene, salt_level, timepoint_h, fold_change, fold_change_sd,
//     n_replicates, ddct, direction, flagged }
// ============================================================================

import { useState, useMemo } from "react";

// The axes. These come straight from the data contract.
const SALT_LEVELS = ["0ppt", "15ppt", "25ppt"];        // 3 rows
const TIMEPOINTS  = [0, 6, 12, 24, 48, 72, 96];        // 7 columns

// ---------------------------------------------------------------------------
// MIKE'S PART (already done) — load the CSV, hand rows to the component
// ---------------------------------------------------------------------------
// In the real app this comes from the parser / API. For now, Mike wires up
// a fetch of clean_table_mock.csv and passes the parsed rows in as a prop.
// Kevin and Adam just receive `rows`.
// ---------------------------------------------------------------------------

export default function ExpressionAtlas({ rows }) {
  const [selectedGene, setSelectedGene] = useState("C5");

  // List of genes present in the data (drives Adam's dropdown)
  const genes = useMemo(
    () => [...new Set(rows.map((r) => r.gene))],
    [rows]
  );

  // =========================================================================
  // KEVIN'S PART — THE GRID LOGIC
  // =========================================================================
  // Goal: turn the flat `rows` array into a lookup so we can ask
  //   "what's the fold_change for C5 at 25ppt, 48h?"
  // and get an answer instantly.
  //
  // TODO(Kevin):
  //   1. Filter `rows` down to only the selected gene.
  //   2. Build a lookup keyed by `${salt_level}|${timepoint_h}`.
  //   3. Return it so the render below can pull each cell's value.
  //
  // Hint: a plain object works fine.
  //   lookup["25ppt|48"] === { fold_change: 3.2, fold_change_sd: 0.4, ... }
  //
  // Build defensively: some cells may be MISSING when real data lands
  // (a condition where every replicate failed). Return undefined for those,
  // don't crash.
  // =========================================================================
  const cellLookup = useMemo(() => {
    const lookup = {};

    // ---- Kevin: your code goes here ----
    //
    // rows
    //   .filter(r => r.gene === selectedGene)
    //   .forEach(r => {
    //     lookup[`${r.salt_level}|${r.timepoint_h}`] = r;
    //   });
    //
    // ------------------------------------

    return lookup;
  }, [rows, selectedGene]);

  // =========================================================================
  // KEVIN'S PART — THE COLOR SCALE
  // =========================================================================
  // Goal: map a fold_change number to a color.
  //   > 1  = upregulated  (one color, more intense the higher it goes)
  //   < 1  = downregulated (another color, more intense the lower it goes)
  //   ~ 1  = flat (neutral / near-white)
  //
  // TODO(Kevin): return a CSS color string for a given fold_change value.
  // Start crude (three flat colors: up / down / flat). Refine to a gradient
  // once the grid is correct. CORRECTNESS FIRST, prettiness second.
  // =========================================================================
  function colorForFoldChange(fc) {
    if (fc === undefined || fc === null) return "#f0f0f0"; // missing cell

    // ---- Kevin: your code goes here ----
    //
    // if (fc >= 1.2) return "...";   // up
    // if (fc <= 0.83) return "...";  // down
    // return "...";                  // flat
    //
    // ------------------------------------

    return "#ffffff";
  }

  return (
    <div className="atlas">
      {/* ===================================================================
          ADAM'S PART — THE GENE SWITCHER
          ===================================================================
          TODO(Adam): a dropdown listing `genes`. On change, call
          setSelectedGene(...). The grid re-renders automatically.
          =================================================================== */}
      <div className="atlas-controls">
        {/* Adam: your dropdown goes here */}
      </div>

      {/* ===================================================================
          THE GRID  —  Kevin's lookup fills it, Adam styles it
          =================================================================== */}
      <table className="atlas-grid">
        <thead>
          <tr>
            <th></th>
            {TIMEPOINTS.map((t) => (
              <th key={t}>{t}h</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {SALT_LEVELS.map((salt) => (
            <tr key={salt}>
              <th>{salt}</th>
              {TIMEPOINTS.map((tp) => {
                const cell = cellLookup[`${salt}|${tp}`];
                const fc = cell?.fold_change;

                return (
                  <td
                    key={tp}
                    style={{ backgroundColor: colorForFoldChange(fc) }}
                    // =====================================================
                    // ADAM'S PART — HOVER TOOLTIP
                    // =====================================================
                    // TODO(Adam): on hover, show exact fold_change and
                    // fold_change_sd. A `title` attribute is the 5-minute
                    // version; a real tooltip component is the good version.
                    // Start with `title`, upgrade later.
                    //
                    // Also: if cell.flagged is true, add a small visual
                    // indicator (a dot, a border) — those are borderline
                    // readings the biologist should look at.
                    // =====================================================
                  >
                    {fc !== undefined ? fc.toFixed(2) : "—"}
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>

      {/* ===================================================================
          ADAM'S PART — THE COLOR LEGEND
          ===================================================================
          TODO(Adam): a small legend explaining what the colors mean.
          "Upregulated (>1)" / "Flat (~1)" / "Downregulated (<1)"
          Without this, nobody knows what they're looking at.
          =================================================================== */}
      <div className="atlas-legend">
        {/* Adam: your legend goes here */}
      </div>
    </div>
  );
}

// ============================================================================
// THE HANDOFF CONTRACT between Kevin and Adam
// ============================================================================
// Kevin owns:  cellLookup  +  colorForFoldChange
// Adam owns:   the dropdown, the tooltip, the legend, the CSS
//
// They meet at: the `cell` object inside the grid render.
// Kevin guarantees it's either a full row object or `undefined`.
// Adam can rely on that and never has to ask where the data came from.
//
// AGREE ON THIS ON DAY ONE. Not week three.
// ============================================================================
