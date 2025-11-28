"""
Step 5c: Infiltration-Based Site Filtering
===========================================

Filters sites based on groundwater flow direction using pixel-level majority voting.

This step analyzes infiltration rasters to determine if a site has predominantly
upward (negative) or downward (positive) groundwater flow. Sites with upward flow
(opstrømningszoner) are removed from the risk assessment.

Method:
1. Sample infiltration rasters for each site using GVD layers
2. For each pixel: Convert infiltration to binary (< 0 → 0, > 0 → 1)
3. Use majority rule across all pixels to determine flow direction
4. Remove sites with upward gradient (majority = 0)
5. Update step5 output files with filtered results

Input:
- Step 5 compound-specific results (step5_compound_detailed_combinations.csv)
- Site geometries from Step 3
- GVFK layer mapping
- GVD infiltration rasters

Output:
- Filtered step5_compound_detailed_combinations.csv (overwrites original)
- Filtering report showing removed sites and statistics
"""

from __future__ import annotations

import sys
from pathlib import Path
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

from config import (
    GVD_RASTER_DIR,
    GVFK_LAYER_MAPPING_PATH,
    get_output_path,
)


def filter_sites_by_infiltration_direction(
    step5_results: pd.DataFrame,
    site_geometries: gpd.GeoDataFrame,
    layer_mapping: pd.DataFrame,
    verbose: bool = True,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Filter sites based on groundwater flow direction using majority voting.

    Args:
        step5_results: DataFrame from step5_risk_assessment (compound detailed combinations)
        site_geometries: GeoDataFrame with site polygons
        layer_mapping: DataFrame mapping GVFK to DK-modellag
        verbose: Whether to print detailed progress information

    Returns:
        Tuple of (filtered_results, removed_sites_df)
        - filtered_results: Sites with downward flow (kept for analysis)
        - removed_sites_df: Sites with upward flow (removed)
    """
    if verbose:
        print("\n" + "=" * 80)
        print("STEP 5c: INFILTRATION-BASED SITE FILTERING")
        print("=" * 80)
        print("Analyzing groundwater flow direction using pixel-level majority voting")
        print("=" * 80 + "\n")

    # Get initial statistics
    initial_combinations = len(step5_results)
    initial_sites = step5_results["Lokalitet_ID"].nunique()
    initial_gvfks = step5_results["GVFK"].nunique()

    if verbose:
        print(f"INPUT from Step 5b:")
        print(f"  {initial_combinations:,} site-GVFK-substance combinations")
        print(f"  {initial_sites:,} unique sites")
        print(f"  {initial_gvfks:,} unique GVFKs\n")

    # Merge layer mapping info
    enriched = step5_results.merge(
        layer_mapping[["GVForekom", "DK-modellag"]],
        left_on="GVFK",
        right_on="GVForekom",
        how="left",
    )

    # Filter out rows with missing modellag (like Step 6 does)
    # This prevents trying to sample infiltration for GVFKs without layer mapping
    missing_modellag_count = enriched["DK-modellag"].isna().sum()
    if missing_modellag_count > 0 and verbose:
        missing_gvfks = enriched.loc[enriched["DK-modellag"].isna(), "GVFK"].unique()
        print(f"Note: Skipping {missing_modellag_count} rows with missing DK-modellag for GVFK(s): {', '.join(sorted(missing_gvfks))}")
        print(f"      These rows will be analyzed at site-level using other GVFKs with layer mapping\n")

    enriched = enriched[enriched["DK-modellag"].notna()].copy()

    # Create lookups from geometries
    geometry_lookup = dict(zip(site_geometries["Lokalitet_"], site_geometries["geometry"]))

    # Analyze infiltration direction for each site-GVFK pair
    if verbose:
        print("Analyzing infiltration direction for each site-GVFK combination...")

    site_gvfk_flow_directions = _analyze_site_gvfk_flow_directions(
        enriched, geometry_lookup, verbose=verbose
    )

    # Create filter masks based on site-GVFK pairs
    def get_flow_direction(row):
        key = (row["Lokalitet_ID"], row["GVFK"])
        return site_gvfk_flow_directions.get(key, "no_data")

    # Apply flow direction to original step5_results
    step5_with_direction = step5_results.copy()
    step5_with_direction["Flow_Direction"] = step5_with_direction.apply(get_flow_direction, axis=1)

    # Separate by flow direction
    filtered_results = step5_with_direction[
        (step5_with_direction["Flow_Direction"] == "downward") |
        (step5_with_direction["Flow_Direction"] == "no_data")
    ].drop(columns=["Flow_Direction"]).copy()

    removed_results = step5_with_direction[
        step5_with_direction["Flow_Direction"] == "upward"
    ].drop(columns=["Flow_Direction"]).copy()

    no_data_results = step5_with_direction[
        step5_with_direction["Flow_Direction"] == "no_data"
    ].drop(columns=["Flow_Direction"]).copy()

    # Calculate final statistics (based on analyzed combinations only)
    analyzed_combinations = initial_combinations - missing_modellag_count if missing_modellag_count > 0 else initial_combinations

    final_combinations = len(filtered_results)
    final_sites = filtered_results["Lokalitet_ID"].nunique() if not filtered_results.empty else 0
    final_gvfks = filtered_results["GVFK"].nunique() if not filtered_results.empty else 0

    removed_combinations = len(removed_results)
    removed_sites_count = removed_results["Lokalitet_ID"].nunique() if not removed_results.empty else 0
    removed_gvfks = removed_results["GVFK"].nunique() if not removed_results.empty else 0

    no_data_combinations = len(no_data_results)
    no_data_sites_count = no_data_results["Lokalitet_ID"].nunique() if not no_data_results.empty else 0

    # Count how many kept vs removed
    kept_analyzed = len([d for d in site_gvfk_flow_directions.values() if d in ["downward", "no_data"]])
    removed_analyzed = len([d for d in site_gvfk_flow_directions.values() if d == "upward"])

    # Print summary
    if verbose:
        print("\n" + "=" * 80)
        print("INFILTRATION FILTERING SUMMARY")
        print("=" * 80)
        print(f"\nDownward flow (KEPT):")
        print(f"  {final_combinations:,} combinations ({final_combinations / initial_combinations * 100:.1f}%)")
        print(f"  {final_sites:,} sites ({final_sites / initial_sites * 100:.1f}%)")
        print(f"  {final_gvfks:,} GVFKs")

        print(f"\nUpward flow - REMOVED (opstrømningszoner):")
        print(f"  {removed_combinations:,} combinations ({removed_combinations / initial_combinations * 100:.1f}%)")
        print(f"  {removed_sites_count:,} sites ({removed_sites_count / initial_sites * 100:.1f}%)")
        print(f"  {removed_gvfks:,} GVFKs affected")

        if no_data_sites_count > 0:
            print(f"\nNo infiltration data available (KEPT by default):")
            print(f"  {no_data_combinations:,} combinations")
            print(f"  {no_data_sites_count:,} sites")
            print(f"  (Sites outside raster coverage - proceeding with caution)")

        print("\n" + "=" * 80 + "\n")

    # filtered_results already includes no_data rows, so no need to concatenate
    return filtered_results, removed_results


def _analyze_site_gvfk_flow_directions(
    enriched: pd.DataFrame,
    geometry_lookup: Dict,
    verbose: bool = True,
) -> Dict[tuple, str]:
    """
    Analyze flow direction for each site-GVFK pair using majority voting on pixels.

    Args:
        enriched: DataFrame with site-GVFK combinations and DK-modellag
        geometry_lookup: Dict mapping Lokalitet_ID to geometry
        verbose: Whether to print progress

    Returns:
        Dict mapping (Lokalitet_ID, GVFK) tuple to flow direction ("upward", "downward", or "no_data")
    """
    # Get unique site-GVFK pairs
    site_gvfk_pairs = enriched[["Lokalitet_ID", "GVFK", "DK-modellag"]].drop_duplicates()

    site_gvfk_flow_directions = {}
    total_pairs = len(site_gvfk_pairs)

    if verbose:
        print(f"Analyzing {total_pairs:,} unique site-GVFK pairs...\n")

    processed = 0
    for _, row in site_gvfk_pairs.iterrows():
        processed += 1
        lokalitet_id = row["Lokalitet_ID"]
        gvfk = row["GVFK"]
        dk_modellag = row["DK-modellag"]

        key = (lokalitet_id, gvfk)
        geometry = geometry_lookup.get(lokalitet_id)

        if geometry is None:
            site_gvfk_flow_directions[key] = "no_data"
            continue

        # Collect pixel values for this specific GVFK's layers
        all_pixel_values = []
        layers = _parse_dk_modellag(dk_modellag)

        # Get centroid for fallback sampling
        centroid = geometry.centroid if geometry is not None else None

        for layer in layers:
            pixel_values = _sample_infiltration_pixels(layer, geometry, centroid)
            if pixel_values is not None and len(pixel_values) > 0:
                all_pixel_values.extend(pixel_values)

        # Determine flow direction using majority voting
        if len(all_pixel_values) == 0:
            flow_direction = "no_data"
        else:
            # Convert to binary: < 0 → 0 (upward), ≥ 0 → 1 (downward)
            binary_values = [1 if v >= 0 else 0 for v in all_pixel_values]
            majority_vote = sum(binary_values) / len(binary_values)

            # Majority rule: > 0.5 means more downward pixels
            if majority_vote > 0.5:
                flow_direction = "downward"
            else:
                flow_direction = "upward"

        site_gvfk_flow_directions[key] = flow_direction

        # Progress indicator
        if verbose and processed % 100 == 0:
            print(f"  Processed {processed}/{total_pairs} site-GVFK pairs...")

    if verbose:
        print(f"  Completed analysis for {total_pairs} site-GVFK pairs\n")

        # Print distribution
        upward_count = sum(1 for d in site_gvfk_flow_directions.values() if d == "upward")
        downward_count = sum(1 for d in site_gvfk_flow_directions.values() if d == "downward")
        no_data_count = sum(1 for d in site_gvfk_flow_directions.values() if d == "no_data")

        print("Flow direction distribution:")
        print(f"  Downward (positive infiltration): {downward_count:,} site-GVFK pairs ({downward_count/total_pairs*100:.1f}%)")
        print(f"  Upward (negative infiltration):   {upward_count:,} site-GVFK pairs ({upward_count/total_pairs*100:.1f}%)")
        print(f"  No data:                          {no_data_count:,} site-GVFK pairs ({no_data_count/total_pairs*100:.1f}%)\n")

    return site_gvfk_flow_directions


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


def _sample_infiltration_pixels(layer: str, geometry, centroid, source_crs: str = "EPSG:25832") -> List[float] | None:
    """
    Sample all pixel values from infiltration raster for given geometry.
    Uses polygon sampling with centroid fallback (same strategy as Step 6).

    Args:
        layer: GVD layer code (e.g., "ks", "kalk")
        geometry: Site polygon geometry
        centroid: Site centroid (for fallback if polygon fails)
        source_crs: CRS of the geometry

    Returns:
        List of pixel values, or None if no data available
    """
    raster_file = GVD_RASTER_DIR / f"DKM_gvd_{layer}.tif"

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

            # If polygon sampling succeeded, return those values
            if polygon_values is not None:
                return polygon_values

            # Fallback: Try centroid sampling
            if centroid is not None:
                try:
                    coords = [(centroid.x, centroid.y)]
                    sampled = list(src.sample(coords))
                    if sampled and sampled[0][0] != nodata:
                        centroid_value = float(sampled[0][0])
                        return [centroid_value]  # Return as list for consistency
                except Exception:
                    pass

            return None

    except Exception as e:
        return None


def run_step5c_filtering(verbose: bool = True) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Run Step 5c infiltration filtering on Step 5 results.

    Returns:
        Tuple of (filtered_results, removed_sites)
    """
    # Load required data
    if verbose:
        print("\nLoading data for infiltration filtering...")

    # Load Step 5 results
    step5_path = get_output_path("step5_compound_detailed_combinations")
    step5_results = pd.read_csv(step5_path, encoding='utf-8')

    # Load site geometries
    from data_loaders import load_site_geometries
    site_geometries = load_site_geometries()

    # Load layer mapping
    if not GVFK_LAYER_MAPPING_PATH.exists():
        raise FileNotFoundError(
            f"GVFK layer mapping not found: {GVFK_LAYER_MAPPING_PATH}"
        )

    # Try multiple encodings (Danish files often use Windows-1252 or latin1)
    for encoding in ['utf-8', 'windows-1252', 'latin1', 'iso-8859-1']:
        try:
            layer_mapping = pd.read_csv(GVFK_LAYER_MAPPING_PATH, sep=';', encoding=encoding)
            break
        except UnicodeDecodeError:
            if encoding == 'iso-8859-1':
                raise
            continue

    # Run filtering
    filtered_results, removed_sites = filter_sites_by_infiltration_direction(
        step5_results, site_geometries, layer_mapping, verbose=verbose
    )

    # Save filtered results (overwrite original)
    if verbose:
        print("Saving filtered results...")

    filtered_results.to_csv(step5_path, index=False, encoding='utf-8')

    # Save removed sites for reference
    removed_path = get_output_path("step5_infiltration_removed_sites")
    removed_sites.to_csv(removed_path, index=False, encoding='utf-8')

    if verbose:
        print(f"  ✓ Updated: {step5_path.name}")
        print(f"  ✓ Saved removed sites: {removed_path.name}")

    return filtered_results, removed_sites


if __name__ == "__main__":
    # Run standalone filtering
    filtered, removed = run_step5c_filtering(verbose=True)
    print(f"\n✓ Step 5c infiltration filtering completed")
    print(f"  Final results: {len(filtered):,} combinations, {filtered['Lokalitet_ID'].nunique():,} sites")
    print(f"  Removed: {removed['Lokalitet_ID'].nunique():,} sites with upward flow")
