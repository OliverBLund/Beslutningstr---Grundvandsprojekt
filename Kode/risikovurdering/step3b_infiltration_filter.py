"""
Step 3b: Infiltration-Based Site Filtering (Early in Workflow)
================================================================

Filters sites based on groundwater flow direction BEFORE distance calculation.
This step runs AFTER Step 3 (site identification) and BEFORE Step 4 (distance).

Uses infiltration filter logic to analyze pixel-level majority voting
for flow direction determination.

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
from typing import Dict, List, Tuple

import geopandas as gpd
import numpy as np
import pandas as pd
import rasterio
from rasterio.mask import mask
from shapely.geometry import mapping

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from config import get_output_path, RESULTS_DIR, GVD_RASTER_DIR
from data_loaders import load_gvfk_layer_mapping
from step_reporter import report_step_header, report_counts, report_subsection


# =============================================================================
# Helper functions for infiltration analysis (moved from step5c)
# =============================================================================

def _build_raster_filename(layer: str, model_region: str | None) -> str | None:
    """Construct raster filename using dk16/dk7 prefixes."""
    if not layer:
        return None

    normalized_layer = str(layer).lower()
    region = (model_region or "").lower()
    if region.startswith("dk7"):
        prefix = "dk7"
    else:
        prefix = "dk16"

    return f"{prefix}_gvd_{normalized_layer}.tif"


def _parse_dk_modellag(dk_modellag: str) -> List[str]:
    """Parse DK-modellag string to list of layer codes."""
    if pd.isna(dk_modellag) or not dk_modellag:
        return []

    layers = []
    parts = [p.strip() for p in str(dk_modellag).split(";")]

    for part in parts:
        if ":" in part:
            layer_code = part.split(":")[1].strip().lower()
        else:
            layer_code = part.strip().lower()

        if layer_code and layer_code not in layers:
            layers.append(layer_code)

    return layers


def _sample_infiltration_pixels(
    layer: str,
    model_region: str,
    geometry,
    centroid,
    source_crs: str = "EPSG:25832",
) -> List[float] | None:
    """
    Sample all pixel values from infiltration raster for given geometry.
    Uses polygon sampling with centroid fallback (same strategy as Step 6).
    """
    normalized_layer = str(layer).lower()
    raster_filename = _build_raster_filename(normalized_layer, model_region)
    if raster_filename is None:
        return None

    raster_file = GVD_RASTER_DIR / raster_filename

    # Fallback to mainland raster if regional file missing
    if not raster_file.exists() and not raster_filename.startswith("dk16_"):
        fallback = GVD_RASTER_DIR / f"dk16_gvd_{normalized_layer}.tif"
        if fallback.exists():
            raster_file = fallback

    if not raster_file.exists():
        return None

    try:
        with rasterio.open(raster_file) as src:
            nodata = src.nodata

            # Try polygon sampling first
            polygon_values = None
            if geometry is not None:
                try:
                    geom_geojson = [mapping(geometry)]
                    masked_data, _ = mask(src, geom_geojson, crop=True, all_touched=False)
                    valid_data = masked_data[
                        (masked_data != nodata) & (~np.isnan(masked_data))
                    ]

                    if valid_data.size > 0:
                        polygon_values = valid_data.flatten().tolist()
                except Exception:
                    pass

            if polygon_values is not None:
                return polygon_values

            # Fallback: Try centroid sampling
            if centroid is not None:
                try:
                    coords = [(centroid.x, centroid.y)]
                    sampled = list(src.sample(coords))
                    if sampled and sampled[0][0] != nodata:
                        centroid_value = float(sampled[0][0])
                        return [centroid_value]
                except Exception:
                    pass

            return None

    except Exception:
        return None


def _analyze_site_gvfk_flow_directions(
    enriched: pd.DataFrame,
    geometry_lookup: Dict,
    verbose: bool = True,
) -> Dict[tuple, str]:
    """
    Analyze flow direction for each site-GVFK pair using majority voting on pixels.

    Returns:
        Dict mapping (Lokalitet_ID, GVFK) tuple to flow direction
    """
    site_gvfk_pairs = enriched[
        ["Lokalitet_ID", "GVFK", "DK-modellag", "Model_Region"]
    ].drop_duplicates()

    site_gvfk_flow_directions = {}
    total_pairs = len(site_gvfk_pairs)
    
    # Diagnostic tracking
    pixel_counts = []  # Track number of pixels per site-GVFK
    majority_votes = []  # Track majority vote percentages
    site_classifications = {}  # Track (lokalitet_id, gvfk) -> (flow_direction, majority_vote, pixel_count)

    if verbose:
        print(f"  Analyzing {total_pairs:,} unique site-GVFK pairs...")

    processed = 0
    for _, row in site_gvfk_pairs.iterrows():
        processed += 1
        lokalitet_id = row["Lokalitet_ID"]
        gvfk = row["GVFK"]
        dk_modellag = row["DK-modellag"]
        model_region = row["Model_Region"]

        key = (lokalitet_id, gvfk)
        geometry = geometry_lookup.get(lokalitet_id)

        if geometry is None:
            site_gvfk_flow_directions[key] = "no_data"
            site_classifications[key] = ("no_data", None, 0)
            continue

        all_pixel_values = []
        layers = _parse_dk_modellag(dk_modellag)
        centroid = geometry.centroid if geometry is not None else None

        for layer in layers:
            pixel_values = _sample_infiltration_pixels(layer, model_region, geometry, centroid)
            if pixel_values is not None and len(pixel_values) > 0:
                all_pixel_values.extend(pixel_values)

        # Determine flow direction using majority voting
        if len(all_pixel_values) == 0:
            flow_direction = "no_data"
            majority_vote = None
            pixel_count = 0
        else:
            binary_values = [1 if v >= 0 else 0 for v in all_pixel_values]
            majority_vote = sum(binary_values) / len(binary_values)
            flow_direction = "downward" if majority_vote > 0.5 else "upward"
            pixel_count = len(all_pixel_values)
            
            # Track for diagnostics
            pixel_counts.append(pixel_count)
            majority_votes.append(majority_vote)

        site_gvfk_flow_directions[key] = flow_direction
        site_classifications[key] = (flow_direction, majority_vote, pixel_count)

        if verbose and processed % 500 == 0:
            print(f"    Processed {processed}/{total_pairs} site-GVFK pairs...")

    if verbose:
        upward_count = sum(1 for d in site_gvfk_flow_directions.values() if d == "upward")
        downward_count = sum(1 for d in site_gvfk_flow_directions.values() if d == "downward")
        no_data_count = sum(1 for d in site_gvfk_flow_directions.values() if d == "no_data")

        if total_pairs > 0:
            print(f"  Flow direction: {downward_count:,} downward, {upward_count:,} upward, {no_data_count:,} no_data")
        
        # Print detailed diagnostics
        if len(majority_votes) > 0:
            print(f"\n  Diagnostic Statistics:")
            print(f"  ─────────────────────────────────────────────────────")
            
            # Pixel count statistics
            import numpy as np
            pixel_arr = np.array(pixel_counts)
            print(f"  Pixel counts per site-GVFK:")
            print(f"    Mean: {pixel_arr.mean():.1f} pixels")
            print(f"    Median: {np.median(pixel_arr):.0f} pixels")
            print(f"    Min: {pixel_arr.min():.0f}, Max: {pixel_arr.max():.0f}")
            print(f"    Sites with ≤5 pixels: {(pixel_arr <= 5).sum():,} ({(pixel_arr <= 5).sum()/len(pixel_arr)*100:.1f}%)")
            
            # Majority vote distribution
            vote_arr = np.array(majority_votes)
            print(f"\n  Majority vote distribution:")
            print(f"    Mean: {vote_arr.mean()*100:.1f}% positive pixels")
            print(f"    Median: {np.median(vote_arr)*100:.1f}% positive pixels")
            
            # Boundary cases (45-55% range)
            boundary_cases = ((vote_arr >= 0.45) & (vote_arr <= 0.55)).sum()
            print(f"\n  Boundary cases (45-55% positive pixels):")
            print(f"    Count: {boundary_cases:,} site-GVFK pairs ({boundary_cases/len(vote_arr)*100:.1f}%)")
            
            # Very close to 50% (48-52%)
            very_close = ((vote_arr >= 0.48) & (vote_arr <= 0.52)).sum()
            print(f"    Very close to 50% (48-52%): {very_close:,} ({very_close/len(vote_arr)*100:.1f}%)")
            
            # Classification breakdown by pixel count
            downward_pixels = [pixel_counts[i] for i, v in enumerate(majority_votes) if v > 0.5]
            upward_pixels = [pixel_counts[i] for i, v in enumerate(majority_votes) if v <= 0.5]
            
            if len(downward_pixels) > 0:
                print(f"\n  Downward-classified sites:")
                print(f"    Mean pixels: {np.mean(downward_pixels):.1f}")
                print(f"    Mean positive %: {np.mean([v for v in vote_arr if v > 0.5])*100:.1f}%")
            
            if len(upward_pixels) > 0:
                print(f"\n  Upward-classified sites:")
                print(f"    Mean pixels: {np.mean(upward_pixels):.1f}")
                print(f"    Mean positive %: {np.mean([v for v in vote_arr if v <= 0.5])*100:.1f}%")
            
            # Per-site analysis (aggregate across all GVFK affiliations)
            site_pixel_totals = {}  # lokalitet_id -> total pixels across all GVFKs
            for (lokalitet_id, gvfk), (flow_dir, maj_vote, pix_count) in site_classifications.items():
                if pix_count > 0:  # Only count sites with data
                    if lokalitet_id not in site_pixel_totals:
                        site_pixel_totals[lokalitet_id] = 0
                    site_pixel_totals[lokalitet_id] += pix_count
            
            if len(site_pixel_totals) > 0:
                site_pixels_arr = np.array(list(site_pixel_totals.values()))
                print(f"\n  Per-site pixel totals (aggregated across all GVFKs):")
                print(f"    Unique sites analyzed: {len(site_pixel_totals):,}")
                print(f"    Mean: {site_pixels_arr.mean():.1f} pixels")
                print(f"    Median: {np.median(site_pixels_arr):.0f} pixels")
                print(f"    Sites with ≤5 pixels total: {(site_pixels_arr <= 5).sum():,} ({(site_pixels_arr <= 5).sum()/len(site_pixels_arr)*100:.1f}%)")
                print(f"    Sites with ≤10 pixels total: {(site_pixels_arr <= 10).sum():,} ({(site_pixels_arr <= 10).sum()/len(site_pixels_arr)*100:.1f}%)")
            
            print(f"  ─────────────────────────────────────────────────────")

    return site_gvfk_flow_directions


# =============================================================================
# Main Step 3b 
# =============================================================================


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
