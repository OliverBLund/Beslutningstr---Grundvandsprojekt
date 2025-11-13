"""
Ad-hoc diagnostics for extreme MKK exceedances in Step 6 outputs.

The goal is to pinpoint suspect combinations (very high Cmix/MKK ratios)
and capture the drivers behind them so they can be validated manually.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import List

import pandas as pd

import sys

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from Kode.config import RESULTS_DIR, get_output_path, ensure_results_directory

SECONDS_PER_YEAR = 365.25 * 24 * 60 * 60
DIAGNOSTICS_DIR = RESULTS_DIR / "step6" / "diagnostics"


def _load_site_exceedances() -> pd.DataFrame:
    """Read the filtered site-level exceedance table produced by Step 6."""
    path = get_output_path("step6_site_mkk_exceedances")
    if not path.exists():
        raise FileNotFoundError(
            f"Expected Step 6 exceedance file was not found: {path}\n"
            "Run step6_tilstandsvurdering.py first to generate it."
        )
    df = pd.read_csv(path, encoding="utf-8")
    if df.empty:
        raise ValueError("Step 6 exceedance file is empty; nothing to analyse.")
    return df


def _diagnose_row(row: pd.Series, flow_alert: float, flux_alert: float) -> str:
    """Generate a short description explaining why the ratio may be extreme."""
    reasons: List[str] = []
    flow = row.get("Flow_m3_s")
    if pd.notna(flow) and flow <= flow_alert:
        reasons.append(f"Very low flow ({flow:.4f} m3/s)")

    segment_flux = row.get("Segment_Total_Flux_kg_per_year")
    if pd.notna(segment_flux) and segment_flux >= flux_alert:
        reasons.append(f"High total flux ({segment_flux:.2f} kg/år)")

    site_flux = row.get("Pollution_Flux_kg_per_year")
    if pd.notna(site_flux) and site_flux >= flux_alert:
        reasons.append(f"High site flux ({site_flux:.2f} kg/år)")

    infiltration = row.get("Infiltration_mm_per_year")
    if pd.notna(infiltration) and infiltration > 1500:
        reasons.append(f"High infiltration ({infiltration:.0f} mm/år)")

    distance = row.get("Distance_to_River_m")
    if pd.notna(distance) and distance > 500:
        reasons.append(f"Long distance ({distance:.0f} m)")

    if not reasons:
        return "Check concentration / modellag inputs"
    return "; ".join(reasons)


def run_extreme_exceedance_analysis(
    ratio_threshold: float = 1_000.0,
    top_n: int = 25,
    flow_alert: float = 0.05,
    flux_alert: float = 10.0,
) -> Path:
    """
    Analyse site-level exceedances and record the worst offenders.

    Args:
        ratio_threshold: Minimum Cmix/MKK ratio to flag for detailed review.
        top_n: How many top rows (sorted by exceedance ratio) to include.
        flow_alert: Flow threshold (m3/s) below which rows are annotated as "low flow".
        flux_alert: Flux threshold (kg/year) above which rows are annotated.

    Returns:
        Path to the generated diagnostic CSV file.
    """
    ensure_results_directory()
    DIAGNOSTICS_DIR.mkdir(parents=True, exist_ok=True)

    exceedances = _load_site_exceedances()
    exceedances["Infiltration_m_per_year"] = exceedances.get("Infiltration_mm_per_year", 0) / 1000.0
    exceedances["Flux_ug_per_second"] = (
        exceedances.get("Pollution_Flux_kg_per_year", 0) * 1_000_000_000.0 / SECONDS_PER_YEAR
    )

    flagged = exceedances.loc[exceedances["Exceedance_Ratio"] >= ratio_threshold].copy()
    if flagged.empty:
        print(f"No exceedances met the selected ratio threshold ({ratio_threshold}).")
        return Path()

    flagged["Diagnosis"] = flagged.apply(_diagnose_row, axis=1, args=(flow_alert, flux_alert))
    flagged = flagged.sort_values("Exceedance_Ratio", ascending=False)

    preview = flagged.head(top_n).copy()
    preview_columns = [
        "GVFK",
        "Lokalitet_ID",
        "Lokalitetsnavn",
        "Nearest_River_ov_id",
        "River_Segment_Name",
        "Qualifying_Category",
        "Qualifying_Substance",
        "Flow_Scenario",
        "Flow_m3_s",
        "Pollution_Flux_kg_per_year",
        "Segment_Total_Flux_kg_per_year",
        "Infiltration_mm_per_year",
        "Area_m2",
        "Distance_to_River_m",
        "Cmix_ug_L",
        "MKK_ug_L",
        "Exceedance_Ratio",
        "Diagnosis",
    ]
    preview = preview[[col for col in preview_columns if col in preview.columns]]

    output_path = DIAGNOSTICS_DIR / f"extreme_exceedances_top{top_n}.csv"
    preview.to_csv(output_path, index=False, encoding="utf-8")

    print("\nEXTREME EXCEEDANCE ANALYSIS")
    print("=" * 70)
    print(f"Rows analysed: {len(exceedances):,}")
    print(f"Flagged (ratio ≥ {ratio_threshold}): {len(flagged):,}")
    print(f"Unique sites: {flagged['Lokalitet_ID'].nunique():,}")
    print(f"Unique GVFK: {flagged['GVFK'].nunique():,}")
    print(f"Unique river segments: {flagged['Nearest_River_ov_id'].nunique():,}")
    print("\nTop offenders:")
    for _, row in preview.head(5).iterrows():
        print(
            f"  {row['Lokalitet_ID']} @ {row['River_Segment_Name']} "
            f"({row['Flow_Scenario']}): {row['Exceedance_Ratio']:.2f}× MKK "
            f"[{row['Diagnosis']}]"
        )
    print(f"\nDetailed CSV: {output_path}")
    return output_path


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Analyse extreme Step 6 exceedances.")
    parser.add_argument(
        "--ratio-threshold",
        type=float,
        default=1_000.0,
        help="Minimum exceedance ratio to flag (default: 1000×).",
    )
    parser.add_argument(
        "--top-n",
        type=int,
        default=25,
        help="Number of top records to export (default: 25).",
    )
    parser.add_argument(
        "--flow-alert",
        type=float,
        default=0.05,
        help="Flow (m3/s) threshold considered suspiciously low (default: 0.05).",
    )
    parser.add_argument(
        "--flux-alert",
        type=float,
        default=10.0,
        help="Flux (kg/year) threshold considered very high (default: 10).",
    )
    return parser


if __name__ == "__main__":
    args = _build_parser().parse_args()
    run_extreme_exceedance_analysis(
        ratio_threshold=args.ratio_threshold,
        top_n=args.top_n,
        flow_alert=args.flow_alert,
        flux_alert=args.flux_alert,
    )
