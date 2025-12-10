"""
Step 3b: Infiltration-Based Site Filtering (Early in Workflow)
================================================================

Filters sites based on groundwater flow direction BEFORE distance calculation.
This step runs AFTER Step 3 (site identification) and BEFORE Step 4 (distance).

Uses the existing infiltration filter logic from Step 5c but adapted to work
with the v1v2_sites GeoDataFrame from Step 3.

Benefits of filtering early:
- Performance: Skip distance calculations for sites we'll filter anyway
- Cleaner data: Sites with upward flow don't appear in intermediate outputs
- Logic: Upward flow sites shouldn't be in risk assessment at all

Filter logic (Conservative - Option A):
- For each site-GVFK combination, check flow direction
- KEEP if downward flow OR if no infiltration data available
- REMOVE if upward flow (discharge zone)
"""

from pathlib import Path
import sys
from typing import Tuple

import geopandas as gpd
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from config import get_output_path, RESULTS_DIR
from data_loaders import load_gvfk_layer_mapping
from risikovurdering.step5c_infiltration_filter import (
    _analyze_site_gvfk_flow_directions,
)
from step_reporter import report_step_header, report_counts, report_subsection


def run_step3b(
    v1v2_sites: gpd.GeoDataFrame,
    verbose: bool = True,
) -> gpd.GeoDataFrame:
    """
    Step 3b: Filter sites based on groundwater flow direction.
    
    Runs AFTER Step 3 and BEFORE Step 4.
    
    Args:
        v1v2_sites: GeoDataFrame from Step 3 with site-GVFK combinations
        verbose: Print detailed progress
        
    Returns:
        Filtered GeoDataFrame with upward flow sites removed
    """
    report_step_header("3b", "Infiltration Filter")
    
    # Get column names from the GeoDataFrame
    # v1v2_sites uses 'Lokalitet_' for site ID and 'Navn' for GVFK
    site_id_col = "Lokalitet_"
    gvfk_col = "Navn"
    
    # Initial counts
    initial_rows = len(v1v2_sites)
    initial_sites = v1v2_sites[site_id_col].nunique()
    initial_gvfks = v1v2_sites[gvfk_col].nunique()
    
    if verbose:
        report_subsection("Input from Step 3")
        report_counts([
            ("Site-GVFK combinations", initial_rows),
            ("Unique sites", initial_sites),
            ("Unique GVFKs", initial_gvfks),
        ])
    
    # Load layer mapping for GVFK -> DK-modellag
    layer_mapping = load_gvfk_layer_mapping(columns=["GVForekom", "dkmlag", "dknr"])
    
    # Create a simplified DataFrame for flow analysis
    # We need: Lokalitet_ID, GVFK (as expected by _analyze_site_gvfk_flow_directions)
    analysis_df = pd.DataFrame({
        "Lokalitet_ID": v1v2_sites[site_id_col].values,
        "GVFK": v1v2_sites[gvfk_col].values,
    })
    
    # Merge layer mapping info
    layer_columns = ["GVForekom", "dkmlag", "dknr"]
    enriched = analysis_df.merge(
        layer_mapping[layer_columns],
        left_on="GVFK",
        right_on="GVForekom",
        how="left",
    )
    enriched = enriched.rename(columns={"dkmlag": "DK-modellag", "dknr": "Model_Region"})
    enriched["Model_Region"] = enriched["Model_Region"].fillna("dk16")
    
    # Filter rows with missing modellag
    missing_modellag_count = enriched["DK-modellag"].isna().sum()
    if missing_modellag_count > 0:
        missing_gvfks = enriched.loc[enriched["DK-modellag"].isna(), "GVFK"].unique()
        if verbose:
            print(f"  Note: {missing_modellag_count} rows lack DK-modellag mapping")
            print(f"        GVFKs: {', '.join(sorted(set(missing_gvfks))[:5])}{'...' if len(missing_gvfks) > 5 else ''}")
    
    enriched_valid = enriched[enriched["DK-modellag"].notna()].copy()
    
    # Create geometry lookup
    geometry_lookup = dict(zip(v1v2_sites[site_id_col], v1v2_sites["geometry"]))
    
    # Analyze flow direction for each site-GVFK pair
    if verbose:
        report_subsection("Analyzing infiltration direction")
        print("  Sampling GVD rasters for each site-GVFK combination...")
    
    site_gvfk_flow_directions = _analyze_site_gvfk_flow_directions(
        enriched_valid, geometry_lookup, verbose=verbose
    )
    
    # Create flow direction column for filtering
    def get_flow_direction(row):
        key = (row[site_id_col], row[gvfk_col])
        return site_gvfk_flow_directions.get(key, "no_data")
    
    v1v2_with_direction = v1v2_sites.copy()
    v1v2_with_direction["Flow_Direction"] = v1v2_with_direction.apply(get_flow_direction, axis=1)
    
    # Filter: keep downward and no_data, remove upward
    filtered_sites = v1v2_with_direction[
        (v1v2_with_direction["Flow_Direction"] == "downward") |
        (v1v2_with_direction["Flow_Direction"] == "no_data")
    ].copy()
    
    removed_sites = v1v2_with_direction[
        v1v2_with_direction["Flow_Direction"] == "upward"
    ].copy()
    
    # Remove temporary column from output
    if "Flow_Direction" in filtered_sites.columns:
        filtered_sites = filtered_sites.drop(columns=["Flow_Direction"])
    
    # Final statistics
    final_rows = len(filtered_sites)
    final_sites = filtered_sites[site_id_col].nunique() if not filtered_sites.empty else 0
    final_gvfks = filtered_sites[gvfk_col].nunique() if not filtered_sites.empty else 0
    
    removed_rows = len(removed_sites)
    removed_sites_count = removed_sites[site_id_col].nunique() if not removed_sites.empty else 0
    
    if verbose:
        report_subsection("Filtering Results")
        pct = lambda p, t: (p / t * 100) if t else 0
        
        print(f"  KEPT (downward flow or no data):")
        print(f"    {final_rows:,} combinations ({pct(final_rows, initial_rows):.1f}%)")
        print(f"    {final_sites:,} sites ({pct(final_sites, initial_sites):.1f}%)")
        print(f"    {final_gvfks:,} GVFKs")
        
        print(f"\n  REMOVED (upward flow - discharge zones):")
        print(f"    {removed_rows:,} combinations ({pct(removed_rows, initial_rows):.1f}%)")
        print(f"    {removed_sites_count:,} sites")
    
    # Save filtered shapefile
    output_path = get_output_path("step3b_filtered_sites")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    filtered_sites.to_file(output_path, driver="ESRI Shapefile")
    
    # Save removed sites CSV for audit
    removed_csv_path = RESULTS_DIR / "step3b_removed_upward_flow.csv"
    if not removed_sites.empty:
        removed_audit = removed_sites[[site_id_col, gvfk_col]].copy()
        removed_audit.to_csv(removed_csv_path, index=False)
    
    if verbose:
        print(f"\n  Saved: {output_path.name}")
        if not removed_sites.empty:
            print(f"  Saved: {removed_csv_path.name} (audit trail)")
    
    return filtered_sites


if __name__ == "__main__":
    # Test run (requires Step 3 results)
    from risikovurdering.step2_river_contact import run_step2
    from risikovurdering.step3_v1v2_sites import run_step3
    
    print("Running Step 3b test...")
    rivers_gvfk, _, _ = run_step2()
    _, v1v2_sites = run_step3(rivers_gvfk)
    
    filtered = run_step3b(v1v2_sites)
    print(f"\nFiltered sites: {len(filtered):,} rows")
