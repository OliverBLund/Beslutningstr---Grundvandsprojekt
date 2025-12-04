"""
Step 6: Tilstandsvurdering (State Assessment)
============================================

Calculates pollution flux from contaminated sites to river segments and computes
mixing concentrations (Cmix) under different flow scenarios.

Workflow:
1. Load data (Step 5 results, geometries, GVFK mapping, rivers, flow)
2. Prepare flux inputs (attach areas, infiltration, river metadata)
3. Calculate flux per site-scenario (J = A · C · I)
4. Aggregate flux by river segment
5. Compute Cmix for Mean/Q90/Q95 scenarios
6. Apply MKK thresholds and flag exceedances
7. Export results and visualizations

Core calculations remain in this file; constants and data loading extracted to
config.py and data_loaders.py for maintainability.
"""

from __future__ import annotations

# Ensure repository root is importable
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

import geopandas as gpd
import numpy as np
import pandas as pd
import rasterio
from rasterio.mask import mask
from shapely.geometry import mapping

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# Import configuration and constants
from config import (
    CATEGORY_SCENARIOS,
    COLUMN_MAPPINGS,
    GRUNDVAND_LAYER_NAME,
    GVD_RASTER_DIR,
    FLOW_SCENARIO_COLUMNS,
    STEP6_FLOW_SELECTION_MODE,
    STEP6_PRIMARY_FLOW_SCENARIO,
    MKK_THRESHOLDS,
    MODELSTOFFER,
    RESULTS_DIR,
    SECONDS_PER_YEAR,
    STANDARD_CONCENTRATIONS,
    ensure_results_directory,
    get_output_path,
)

# Import data loaders
from data_loaders import (
    load_flow_scenarios,
    load_flow_scenarios_extended,
    load_gvfk_layer_mapping,
    load_river_segments,
    load_site_geometries,
    load_step5_results,
)

# Import visualizations
try:
    from .step6_visualizations import analyze_and_visualize_step6
except ImportError:
    from step6_visualizations import analyze_and_visualize_step6


# ===========================================================================
# Main workflow
# ===========================================================================


def run_step6() -> Dict[str, pd.DataFrame]:
    """
    Execute Step 6 workflow and return the produced DataFrames.

    Returns:
        Dict with keys: site_flux, segment_flux, cmix_results, segment_summary,
        site_exceedances, gvfk_exceedances, negative_infiltration
    """
    ensure_results_directory()

    print("\n" + "=" * 60)
    print("STEP 6: TILSTANDSVURDERING")
    print("=" * 60)

    # Load data
    print("\n[1/6] Loading data...")
    step5_results = load_step5_results()
    site_geometries = load_site_geometries()
    layer_mapping = load_gvfk_layer_mapping(columns=["GVForekom", "dkmlag", "dknr"])
    river_segments = load_river_segments()

    # Prepare flux inputs (filtering + infiltration)
    print("[2/6] Preparing flux inputs (filtering + infiltration)...")
    enriched_results, negative_infiltration, filtering_audit, pixel_data_records = _prepare_flux_inputs(
        step5_results, site_geometries, layer_mapping, river_segments
    )

    # Calculate flux
    print("[3/6] Calculating flux (scenario-based approach)...")
    flux_details = _calculate_flux(enriched_results)

    # Aggregate by segment
    print("[4/6] Aggregating flux by segment...")
    segment_flux = _aggregate_flux_by_segment(flux_details)

    # Compute Cmix
    print("[5/6] Computing Cmix (all flow scenarios: Q05, Q10, Q50, Q90, Q95)...")
    # Load flows (ov_id max) and raw Q-points (for nearest-per-segment mode)
    flow_scenarios, qpoints_gdf = load_flow_scenarios_extended()

    cmix_results = _calculate_cmix(segment_flux, flow_scenarios, qpoints_gdf)
    cmix_results = _apply_mkk_thresholds(cmix_results)

    # Build summaries
    print("[6/6] Building summaries & exporting...")
    segment_summary = _build_segment_summary(flux_details, segment_flux, cmix_results)
    site_exceedances, gvfk_exceedances = _extract_exceedance_views(
        flux_details, cmix_results
    )

    # Export
    _export_results(
        flux_details,
        cmix_results,
        segment_summary,
        site_exceedances,
    )

    # Export filtering audit
    if not filtering_audit.empty:
        audit_path = get_output_path("step6_filtering_audit")
        filtering_audit.to_csv(audit_path, index=False, encoding="utf-8")
        print(f"\n{'=' * 60}")
        print(f"Filtering audit exported: {audit_path.name}")
        print(f"Total filtered entries: {len(filtering_audit)}")
        print(
            f"  Filter 1 (Missing modellag): {(filtering_audit['Filter_Stage'] == 'Filter_1_Missing_Modellag').sum()}"
        )
        print(
            f"  Filter 2 (Negative infiltration): {(filtering_audit['Filter_Stage'] == 'Filter_2_Negative_Infiltration').sum()}"
        )
        print(
            f"  Filter 3 (Missing infiltration): {(filtering_audit['Filter_Stage'] == 'Filter_3_Missing_Infiltration').sum()}"
        )
        print(f"{'=' * 60}\n")

    # Visualize
    analyze_and_visualize_step6(
        flux_details,
        segment_flux,
        cmix_results,
        segment_summary,
        negative_infiltration=negative_infiltration,
        site_geometries=site_geometries,
        site_exceedances=site_exceedances,
        gvfk_exceedances=gvfk_exceedances,
        pixel_data_records=pixel_data_records,
        enriched_results=enriched_results,
    )

    print("\n" + "=" * 60)
    print("Step 6 completed successfully!")
    print("=" * 60 + "\n")

    return {
        "site_flux": flux_details,
        "segment_flux": segment_flux,
        "cmix_results": cmix_results,
        "segment_summary": segment_summary,
        "site_exceedances": site_exceedances,
        "gvfk_exceedances": gvfk_exceedances,
        "negative_infiltration": negative_infiltration,
    }


# ===========================================================================
# Data preparation (filtering + infiltration)
# ===========================================================================


def _prepare_flux_inputs(
    step5_results: pd.DataFrame,
    site_geometries: gpd.GeoDataFrame,
    layer_mapping: pd.DataFrame,
    river_segments: gpd.GeoDataFrame,
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, List[Dict[str, Any]]]:
    """Attach areas, modellag, infiltration, and river segment metadata.

    Returns:
        Tuple containing:
        - enriched: Filtered DataFrame ready for flux calculation
        - negative_rows: Rows with negative infiltration (for diagnostics/visualization)
        - filtering_audit: Complete audit trail of all filtered rows
        - pixel_data_records: All pixel values sampled for distribution visualization
    """
    # Print initial statistics
    initial_total_rows = len(step5_results)
    initial_total_sites = step5_results["Lokalitet_ID"].nunique()
    initial_total_gvfk = step5_results["GVFK"].nunique()

    print("\n" + "=" * 80)
    print("FILTERING CASCADE – Step 6 Data Preparation")
    print("=" * 80)
    print(
        f"INPUT from Step 5: {initial_total_rows} rows, {initial_total_sites} sites, {initial_total_gvfk} GVFK"
    )
    print("=" * 80 + "\n")

    enriched = step5_results.copy()
    negative_rows = pd.DataFrame(columns=enriched.columns)

    # Initialize filtering audit trail
    filtering_audit = []

    # Attach areas and centroids
    area_lookup = dict(zip(site_geometries["Lokalitet_"], site_geometries["Area_m2"]))
    centroid_lookup = dict(
        zip(site_geometries["Lokalitet_"], site_geometries["Centroid"])
    )
    geometry_lookup = dict(
        zip(site_geometries["Lokalitet_"], site_geometries["geometry"])
    )
    enriched["Area_m2"] = enriched["Lokalitet_ID"].map(area_lookup)

    if enriched["Area_m2"].isna().any():
        missing_sites = enriched.loc[
            enriched["Area_m2"].isna(), "Lokalitet_ID"
        ].unique()
        raise ValueError(
            "Missing geometries for the following sites: "
            + ", ".join(sorted(missing_sites))
        )

    # Attach modellag information
    # Deduplicate GVFK→modellag mapping to avoid row explosion.
    # Some GVFK polygons appear multiple times; we collapse to one row per GVFK
    # and, if multiple modellag values exist, join them with "/".
    layer_info = (
        layer_mapping[["GVForekom", "dkmlag", "dknr"]]
        .dropna(subset=["GVForekom"])
        .groupby("GVForekom", as_index=False)
        .agg(
            {
                "dkmlag": lambda s: "/".join(
                    sorted({str(v).strip() for v in s if pd.notna(v) and str(v).strip()})
                ),
                "dknr": lambda s: next((v for v in s if pd.notna(v)), None),
            }
        )
        .rename(columns={"dkmlag": "DK-modellag", "dknr": "Model_Region"})
    )
    enriched = enriched.merge(
        layer_info,
        left_on="GVFK",
        right_on="GVForekom",
        how="left",
    )
    enriched["Model_Region"] = enriched["Model_Region"].fillna("dk16")
    if enriched["DK-modellag"].isna().any():
        missing_layers = enriched.loc[enriched["DK-modellag"].isna(), "GVFK"].unique()
        missing_count = enriched["DK-modellag"].isna().sum()
        missing_sites_count = enriched.loc[
            enriched["DK-modellag"].isna(), "Lokalitet_ID"
        ].nunique()
        missing_sites_list = enriched.loc[
            enriched["DK-modellag"].isna(), "Lokalitet_ID"
        ].unique()

        print(f"FILTER 1: Missing modellag mapping")
        print(
            f"   GVFKs affected: {len(missing_layers)} ({', '.join(sorted(missing_layers))})"
        )
        print(
            f"   Rows removed: {missing_count} ({missing_count / initial_total_rows * 100:.1f}%)"
        )
        print(f"   Sites removed: {missing_sites_count}")
        print(
            f"   Example sites: {', '.join(sorted(missing_sites_list)[:5])}{' ...' if len(missing_sites_list) > 5 else ''}"
        )
        print(
            "   -> TODO: Add these GVFKs to the Grunddata layer "
            f"'{GRUNDVAND_LAYER_NAME}' with a valid dkmlag assignment.\n"
        )

        # Track filtered rows in audit
        filtered = enriched[enriched["DK-modellag"].isna()]
        for _, row in filtered.iterrows():
            filtering_audit.append(
                {
                    "Lokalitet_ID": row["Lokalitet_ID"],
                    "Lokalitetsnavn": row.get("Lokalitetsnavn", "N/A"),
                    "GVFK": row["GVFK"],
                    "Qualifying_Category": row["Qualifying_Category"],
                    "Nearest_River_ov_id": row.get("Nearest_River_ov_id", "N/A"),
                    "Distance_to_River_m": row.get("Distance_to_River_m", None),
                    "Filter_Stage": "Filter_1_Missing_Modellag",
                    "Filter_Reason": f"No dkmlag mapping for GVFK {row['GVFK']}",
                    "Additional_Info": f"Add {row['GVFK']} to Grunddata layer '{GRUNDVAND_LAYER_NAME}'",
                }
            )

        # Filter out rows with missing modellag
        enriched = enriched[enriched["DK-modellag"].notna()].copy()

        after_filter1_rows = len(enriched)
        after_filter1_sites = enriched["Lokalitet_ID"].nunique()
        after_filter1_gvfk = enriched["GVFK"].nunique()
        print(
            f"   AFTER FILTER 1: {after_filter1_rows} rows, {after_filter1_sites} sites, {after_filter1_gvfk} GVFK\n"
        )

    enriched = enriched.drop(columns=["GVForekom"])

    infiltration_stats, pixel_data_records = _calculate_infiltration(
        enriched, centroid_lookup, geometry_lookup
    )

    enriched["Infiltration_mm_per_year"] = infiltration_stats[
        "Combined_Infiltration_mm_per_year"
    ]
    enriched["Centroid_Infiltration_mm_per_year"] = infiltration_stats[
        "Centroid_Infiltration_mm_per_year"
    ]
    enriched["Polygon_Infiltration_mm_per_year"] = infiltration_stats[
        "Polygon_Infiltration_mm_per_year"
    ]
    enriched["Polygon_Infiltration_Min_mm_per_year"] = infiltration_stats[
        "Polygon_Infiltration_Min_mm_per_year"
    ]
    enriched["Polygon_Infiltration_Max_mm_per_year"] = infiltration_stats[
        "Polygon_Infiltration_Max_mm_per_year"
    ]
    enriched["Polygon_Infiltration_Pixel_Count"] = infiltration_stats[
        "Polygon_Infiltration_Pixel_Count"
    ]

    # Filter negative infiltration
    negative_mask = enriched["Infiltration_mm_per_year"] < 0
    negative_count = negative_mask.sum()
    if negative_count > 0:
        before_filter2_rows = len(enriched)
        before_filter2_sites = enriched["Lokalitet_ID"].nunique()
        before_filter2_gvfk = enriched["GVFK"].nunique()

        negative_rows = enriched.loc[negative_mask].copy()
        negative_rows["Sampled_Layers"] = negative_rows["DK-modellag"].apply(
            lambda text: ", ".join(_parse_dk_modellag(text)) if pd.notna(text) else ""
        )
        removed_sites = sorted(enriched.loc[negative_mask, "Lokalitet_ID"].unique())
        removed_gvfk = sorted(enriched.loc[negative_mask, "GVFK"].unique())

        # Track filtered rows in audit
        for _, row in negative_rows.iterrows():
            filtering_audit.append(
                {
                    "Lokalitet_ID": row["Lokalitet_ID"],
                    "Lokalitetsnavn": row.get("Lokalitetsnavn", "N/A"),
                    "GVFK": row["GVFK"],
                    "Qualifying_Category": row["Qualifying_Category"],
                    "Nearest_River_ov_id": row.get("Nearest_River_ov_id", "N/A"),
                    "Distance_to_River_m": row.get("Distance_to_River_m", None),
                    "Filter_Stage": "Filter_2_Negative_Infiltration",
                    "Filter_Reason": f"Negative infiltration: {row['Infiltration_mm_per_year']:.1f} mm/yr",
                    "Additional_Info": f"Opstrømningszone - layers: {row.get('Sampled_Layers', 'N/A')}",
                }
            )

        enriched = enriched[~negative_mask].copy()

        after_filter2_rows = len(enriched)
        after_filter2_sites = enriched["Lokalitet_ID"].nunique()
        after_filter2_gvfk = enriched["GVFK"].nunique()

        remaining_sites = set(enriched["Lokalitet_ID"].unique())
        remaining_gvfk = set(enriched["GVFK"].unique())
        completely_removed_sites = [
            s for s in removed_sites if s not in remaining_sites
        ]
        completely_removed_gvfk = [g for g in removed_gvfk if g not in remaining_gvfk]

        print(f"FILTER 2: Negative infiltration (opstroemningszoner)")
        print(
            f"   Rows removed: {negative_count} ({negative_count / before_filter2_rows * 100:.1f}%)"
        )
        print(f"   Sites with removed rows: {len(removed_sites)}")
        print(
            f"   Sites completely removed: {len(completely_removed_sites)} (all rows had negative infiltration)"
        )
        print(
            f"   Sites partially affected: {len(removed_sites) - len(completely_removed_sites)} (some rows retained in other locations)"
        )
        print(f"   GVFK completely removed: {len(completely_removed_gvfk)}")
        print(
            f"   GVFK partially affected: {len(removed_gvfk) - len(completely_removed_gvfk)}"
        )
        print(
            f"   Example sites: {', '.join(removed_sites[:5])}{' ...' if len(removed_sites) > 5 else ''}\n"
        )
        print(
            f"   AFTER FILTER 2: {after_filter2_rows} rows, {after_filter2_sites} sites, {after_filter2_gvfk} GVFK\n"
        )

    # Filter missing infiltration
    if enriched["Infiltration_mm_per_year"].isna().any():
        before_filter3_rows = len(enriched)
        before_filter3_sites = enriched["Lokalitet_ID"].nunique()
        before_filter3_gvfk = enriched["GVFK"].nunique()

        missing_infiltration = enriched["Infiltration_mm_per_year"].isna().sum()
        missing_sites = enriched.loc[
            enriched["Infiltration_mm_per_year"].isna(), "Lokalitet_ID"
        ].unique()

        print(f"FILTER 3: Missing infiltration data (outside raster coverage)")
        print(
            f"   Rows removed: {missing_infiltration} ({missing_infiltration / before_filter3_rows * 100:.1f}%)"
        )
        print(f"   Sites removed: {len(missing_sites)}")
        print(
            f"   Example sites: {', '.join(sorted(missing_sites)[:10])}{' ...' if len(missing_sites) > 10 else ''}"
        )
        print(
            f"   Reason: Site polygon/centroid fall outside infiltration raster coverage.\n"
        )

        # Track filtered rows in audit
        filtered = enriched[enriched["Infiltration_mm_per_year"].isna()]
        for _, row in filtered.iterrows():
            filtering_audit.append(
                {
                    "Lokalitet_ID": row["Lokalitet_ID"],
                    "Lokalitetsnavn": row.get("Lokalitetsnavn", "N/A"),
                    "GVFK": row["GVFK"],
                    "Qualifying_Category": row["Qualifying_Category"],
                    "Nearest_River_ov_id": row.get("Nearest_River_ov_id", "N/A"),
                    "Distance_to_River_m": row.get("Distance_to_River_m", None),
                    "Filter_Stage": "Filter_3_Missing_Infiltration",
                    "Filter_Reason": "No infiltration data",
                    "Additional_Info": f"Site outside raster coverage or at nodata location - layers: {row.get('DK-modellag', 'N/A')}",
                }
            )

        enriched = enriched[enriched["Infiltration_mm_per_year"].notna()].copy()

        after_filter3_rows = len(enriched)
        after_filter3_sites = enriched["Lokalitet_ID"].nunique()
        after_filter3_gvfk = enriched["GVFK"].nunique()
        print(
            f"   AFTER FILTER 3: {after_filter3_rows} rows, {after_filter3_sites} sites, {after_filter3_gvfk} GVFK\n"
        )

    # Attach river metadata
    river_length_col = COLUMN_MAPPINGS["rivers"]["length"]
    segment_meta = river_segments[
        ["River_FID", "ov_id", "ov_navn", river_length_col, "GVForekom"]
    ].copy()
    segment_meta = segment_meta.rename(
        columns={
            "ov_id": "River_Segment_ov_id",
            "ov_navn": "River_Segment_Name",
            river_length_col: "River_Segment_Length_m",
            "GVForekom": "River_Segment_GVFK",
        }
    )

    enriched = enriched.merge(
        segment_meta,
        left_on="Nearest_River_FID",
        right_on="River_FID",
        how="left",
    )

    if enriched["River_Segment_Name"].isna().any():
        missing_fids = enriched.loc[
            enriched["River_Segment_Name"].isna(), "Nearest_River_FID"
        ].unique()
        raise ValueError(
            "River metadata missing for FID(s): "
            + ", ".join(str(fid) for fid in sorted(missing_fids))
        )

    # Sanity-check ov_id matches
    mismatches = enriched[
        enriched["Nearest_River_ov_id"].astype(str)
        != enriched["River_Segment_ov_id"].astype(str)
    ]
    if not mismatches.empty:
        raise ValueError(
            "Nearest_River_ov_id from Step 5 does not match river shapefile for "
            f"{len(mismatches)} rows."
        )

    enriched = enriched.drop(columns=["River_FID", "River_Segment_ov_id"])

    if "Sampled_Layers" not in negative_rows.columns:
        negative_rows["Sampled_Layers"] = pd.Series(dtype=str)

    # Final summary
    final_rows = len(enriched)
    final_sites = enriched["Lokalitet_ID"].nunique()
    final_gvfk = enriched["GVFK"].nunique()

    print("=" * 80)
    print("FILTERING CASCADE SUMMARY")
    print("=" * 80)
    print(
        f"INPUT:  {initial_total_rows} rows, {initial_total_sites} sites, {initial_total_gvfk} GVFK"
    )
    print(f"OUTPUT: {final_rows} rows, {final_sites} sites, {final_gvfk} GVFK")
    print(
        f"TOTAL REMOVED: {initial_total_rows - final_rows} rows ({(initial_total_rows - final_rows) / initial_total_rows * 100:.1f}%), {initial_total_sites - final_sites} sites ({(initial_total_sites - final_sites) / initial_total_sites * 100:.1f}%)"
    )
    print("=" * 80 + "\n")

    # Convert audit to DataFrame
    audit_df = pd.DataFrame(filtering_audit)

    return enriched, negative_rows, audit_df, pixel_data_records


# ===========================================================================
# Infiltration calculation
# ===========================================================================


def _calculate_infiltration(
    enriched: pd.DataFrame,
    centroid_lookup: Dict[str, Any],
    geometry_lookup: Dict[str, Any],
    source_crs=None,
) -> Tuple[pd.DataFrame, List[Dict[str, Any]]]:
    """
    Sample GVD rasters for infiltration using combined centroid + polygon strategy.

    Returns:
        Tuple containing:
        - DataFrame with infiltration columns for each row
        - List of pixel data records for distribution visualization
    """
    if source_crs is None:
        source_crs = "EPSG:25832"

    infiltration_records = []
    pixel_data_records = []  # NEW: Collect all pixel values

    # Track GVD value cleaning statistics
    total_pixels_capped = 0
    total_pixels_zeroed = 0
    total_centroids_capped = 0
    total_centroids_zeroed = 0
    sites_with_capped_pixels = set()
    sites_with_zeroed_pixels = set()

    # Track sampling method usage
    sites_using_centroid = set()  # Sites that used centroid-only sampling
    sites_using_polygon = set()   # Sites that used polygon sampling
    sites_without_data = set()    # Sites with no raster coverage

    for idx, row in enriched.iterrows():
        lokalitet_id = row["Lokalitet_ID"]
        dk_modellag = row["DK-modellag"]
        model_region = row.get("Model_Region", "dk16")

        centroid = centroid_lookup.get(lokalitet_id)
        geometry = geometry_lookup.get(lokalitet_id)

        layers = _parse_dk_modellag(dk_modellag)

        combined_values = []
        centroid_values = []
        polygon_values = []
        polygon_mins = []
        polygon_maxs = []
        pixel_counts = []

        for layer in layers:
            result = _sample_infiltration(layer, model_region, geometry, centroid, source_crs)

            if result["Combined"] is not None:
                combined_values.append(result["Combined"])
            if result["Centroid"] is not None:
                centroid_values.append(result["Centroid"])
            if result["Polygon_Mean"] is not None:
                polygon_values.append(result["Polygon_Mean"])
            if result["Polygon_Min"] is not None:
                polygon_mins.append(result["Polygon_Min"])
            if result["Polygon_Max"] is not None:
                polygon_maxs.append(result["Polygon_Max"])
            if result["Polygon_Pixel_Count"] is not None:
                pixel_counts.append(result["Polygon_Pixel_Count"])

            # NEW: Collect all pixel values for this site
            if result.get("All_Pixel_Values") is not None and len(result["All_Pixel_Values"]) > 0:
                pixel_data_records.append({
                    "Lokalitet_ID": lokalitet_id,
                    "Layer": layer,
                    "Pixel_Values": result["All_Pixel_Values"],
                    "Pixel_Count": len(result["All_Pixel_Values"])
                })

            # Track capping/zeroing statistics
            if result.get("Pixels_Capped", 0) > 0:
                total_pixels_capped += result["Pixels_Capped"]
                sites_with_capped_pixels.add(lokalitet_id)
            if result.get("Pixels_Zeroed", 0) > 0:
                total_pixels_zeroed += result["Pixels_Zeroed"]
                sites_with_zeroed_pixels.add(lokalitet_id)
            if result.get("Centroid_Capped", False):
                total_centroids_capped += 1
            if result.get("Centroid_Zeroed", False):
                total_centroids_zeroed += 1

        # Track which sampling method was used for this site
        if polygon_values:
            # Polygon sampling succeeded
            sites_using_polygon.add(lokalitet_id)
        elif centroid_values:
            # Only centroid sampling succeeded (polygon failed or unavailable)
            sites_using_centroid.add(lokalitet_id)
        else:
            # No data available for this site
            sites_without_data.add(lokalitet_id)

        # Use mean of all sampled layers
        record = {
            "Combined_Infiltration_mm_per_year": np.mean(combined_values)
            if combined_values
            else np.nan,
            "Centroid_Infiltration_mm_per_year": np.mean(centroid_values)
            if centroid_values
            else np.nan,
            "Polygon_Infiltration_mm_per_year": np.mean(polygon_values)
            if polygon_values
            else np.nan,
            "Polygon_Infiltration_Min_mm_per_year": np.mean(polygon_mins)
            if polygon_mins
            else np.nan,
            "Polygon_Infiltration_Max_mm_per_year": np.mean(polygon_maxs)
            if polygon_maxs
            else np.nan,
            "Polygon_Infiltration_Pixel_Count": int(np.mean(pixel_counts))
            if pixel_counts
            else 0,
        }

        infiltration_records.append(record)

    # Report comprehensive infiltration sampling statistics
    from config import WORKFLOW_SETTINGS
    gvd_cap = WORKFLOW_SETTINGS.get("gvd_max_infiltration_cap", 750)

    total_sites = len(set(enriched["Lokalitet_ID"]))

    print("\n" + "=" * 80)
    print("INFILTRATION SAMPLING SUMMARY")
    print("=" * 80)

    # Sampling method breakdown
    print(f"\nSampling method usage (total {total_sites} unique sites):")
    print(f"  Polygon sampling:     {len(sites_using_polygon):,} sites ({len(sites_using_polygon)/total_sites*100:.1f}%)")
    print(f"  Centroid-only:        {len(sites_using_centroid):,} sites ({len(sites_using_centroid)/total_sites*100:.1f}%)")
    print(f"  No raster coverage:   {len(sites_without_data):,} sites ({len(sites_without_data)/total_sites*100:.1f}%)")

    # GVD value cleaning statistics
    print(f"\nGVD value cleaning (cap: {gvd_cap} mm/year):")
    print(f"  Pixels capped (>{gvd_cap}):  {total_pixels_capped:,} pixels, {len(sites_with_capped_pixels):,} sites")
    print(f"  Pixels zeroed (<0):         {total_pixels_zeroed:,} pixels, {len(sites_with_zeroed_pixels):,} sites")

    if total_centroids_capped > 0 or total_centroids_zeroed > 0:
        print(f"  Centroid adjustments:       ", end="")
        parts = []
        if total_centroids_capped > 0:
            parts.append(f"{total_centroids_capped:,} capped")
        if total_centroids_zeroed > 0:
            parts.append(f"{total_centroids_zeroed:,} zeroed")
        print(", ".join(parts))

    # List sites without data if any
    if sites_without_data:
        print(f"\nSites without raster coverage (n={len(sites_without_data)}):")
        sorted_sites = sorted(sites_without_data)
        if len(sorted_sites) <= 20:
            for site_id in sorted_sites:
                print(f"  - {site_id}")
        else:
            for site_id in sorted_sites[:10]:
                print(f"  - {site_id}")
            print(f"  ... and {len(sorted_sites)-10} more (see log for details)")

    print("=" * 80 + "\n")

    return pd.DataFrame(infiltration_records, index=enriched.index), pixel_data_records


def _parse_dk_modellag(dk_modellag: str) -> List[str]:
    """Parse DK-modellag string to list of layer codes.

    Handles multiple separator formats:
    - Semicolon: "Kalk: kalk; Ks2: ks2"
    - Slash: "kvs_0200/kvs_0400"
    - Single value: "ks2"
    """
    if pd.isna(dk_modellag) or not dk_modellag:
        return []

    # Handle format like "Kalk: kalk; ..." or "kvs_0200/kvs_0400" or just "ks2"
    layers = []

    # First try splitting on semicolon, then slash, then treat as single value
    dk_modellag_str = str(dk_modellag).strip()
    if ";" in dk_modellag_str:
        parts = [p.strip() for p in dk_modellag_str.split(";")]
    elif "/" in dk_modellag_str:
        parts = [p.strip() for p in dk_modellag_str.split("/")]
    else:
        parts = [dk_modellag_str]

    for part in parts:
        if ":" in part:
            layer_code = part.split(":")[1].strip().lower()
        else:
            layer_code = part.strip().lower()

        if layer_code and layer_code not in layers:
            layers.append(layer_code)

    return layers


def _sample_infiltration(
    layer: str,
    model_region: str,
    geometry,
    centroid,
    source_crs: str = "EPSG:25832",
) -> Dict[str, float]:
    """
    Sample a single GVD raster layer using both polygon and centroid.

    Returns dict with Combined, Centroid, Polygon_Mean, Polygon_Min, Polygon_Max, Polygon_Pixel_Count, All_Pixel_Values.
    """
    normalized_layer = str(layer).lower()
    raster_filename = _build_raster_filename(normalized_layer, model_region)
    if not raster_filename:
        return {
            "Combined": None,
            "Centroid": None,
            "Polygon_Mean": None,
            "Polygon_Min": None,
            "Polygon_Max": None,
            "Polygon_Pixel_Count": None,
            "All_Pixel_Values": None,
        }

    raster_file = GVD_RASTER_DIR / raster_filename

    if not raster_file.exists() and not raster_filename.startswith("dk16_"):
        fallback = GVD_RASTER_DIR / f"dk16_gvd_{normalized_layer}.tif"
        if fallback.exists():
            raster_file = fallback

    if not raster_file.exists():
        return {
            "Combined": None,
            "Centroid": None,
            "Polygon_Mean": None,
            "Polygon_Min": None,
            "Polygon_Max": None,
            "Polygon_Pixel_Count": None,
            "All_Pixel_Values": None,
        }

    try:
        with rasterio.open(raster_file) as src:
            nodata = src.nodata

            # Get GVD cap from settings
            from config import WORKFLOW_SETTINGS
            gvd_cap = WORKFLOW_SETTINGS.get("gvd_max_infiltration_cap", 750)

            # Sample centroid
            centroid_value = None
            centroid_capped = False
            centroid_zeroed = False
            if centroid is not None:
                coords = [(centroid.x, centroid.y)]
                sampled = list(src.sample(coords))
                if sampled and sampled[0][0] != nodata:
                    raw_value = float(sampled[0][0])
                    # Clean centroid value: zero negative, cap positive
                    if raw_value < 0:
                        centroid_value = 0.0
                        centroid_zeroed = True
                    elif raw_value > gvd_cap:
                        centroid_value = gvd_cap
                        centroid_capped = True
                    else:
                        centroid_value = raw_value

            # Sample polygon
            polygon_mean = None
            polygon_min = None
            polygon_max = None
            pixel_count = 0
            all_pixel_values = None  # NEW: Store all pixel values
            pixels_capped = 0
            pixels_zeroed = 0

            if geometry is not None:
                try:
                    geom_geojson = [mapping(geometry)]
                    masked_data, _ = mask(
                        src, geom_geojson, crop=True, all_touched=False
                    )
                    valid_data = masked_data[
                        (masked_data != nodata) & (~np.isnan(masked_data))
                    ]

                    if valid_data.size > 0:
                        # Clean GVD values: zero negative (upward flux), cap positive values
                        # Count how many values are affected
                        pixels_zeroed = int(np.sum(valid_data < 0))
                        pixels_capped = int(np.sum(valid_data > gvd_cap))

                        # Zero out negative values (upward flux)
                        cleaned_data = np.where(valid_data < 0, 0, valid_data)
                        # Cap positive values
                        cleaned_data = np.where(cleaned_data > gvd_cap, gvd_cap, cleaned_data)

                        polygon_mean = float(np.mean(cleaned_data))
                        polygon_min = float(np.min(cleaned_data))
                        polygon_max = float(np.max(cleaned_data))
                        pixel_count = int(cleaned_data.size)
                        all_pixel_values = cleaned_data.flatten().tolist()  # NEW: Store all pixel values
                except Exception:
                    pass

            # Combined strategy: prefer polygon if available, else centroid
            combined_value = (
                polygon_mean if polygon_mean is not None else centroid_value
            )

            # Note: Individual no-data warnings suppressed - see aggregated report at end of _calculate_infiltration()

            return {
                "Combined": combined_value,
                "Centroid": centroid_value,
                "Polygon_Mean": polygon_mean,
                "Polygon_Min": polygon_min,
                "Polygon_Max": polygon_max,
                "Polygon_Pixel_Count": pixel_count,
                "All_Pixel_Values": all_pixel_values,  # NEW: Return all pixel values
                "Pixels_Capped": pixels_capped,
                "Pixels_Zeroed": pixels_zeroed,
                "Centroid_Capped": centroid_capped,
                "Centroid_Zeroed": centroid_zeroed,
            }

    except Exception as e:
        print(f"ERROR sampling {raster_file.name}: {e}")
        return {
            "Combined": None,
            "Centroid": None,
            "Polygon_Mean": None,
            "Polygon_Min": None,
            "Polygon_Max": None,
            "Polygon_Pixel_Count": None,
            "All_Pixel_Values": None,
            "Pixels_Capped": 0,
            "Pixels_Zeroed": 0,
            "Centroid_Capped": False,
            "Centroid_Zeroed": False,
        }


def _build_raster_filename(layer: str, model_region: str | None) -> str | None:
    """Return raster filename with appropriate dk16/dk7 prefix."""
    if not layer:
        return None

    region = (model_region or "").lower()
    if region.startswith("dk7"):
        prefix = "dk7"
    else:
        prefix = "dk16"

    return f"{prefix}_gvd_{layer}.tif"


# ===========================================================================
# Concentration lookup
# ===========================================================================


def _lookup_concentration_for_scenario(
    scenario_modelstof: str | None,
    category: str,
    original_substance: str | None,
    row: pd.Series,
) -> float:
    """
    Lookup concentration for a scenario using the hierarchy.

    Args:
        scenario_modelstof: The modelstof for this scenario (e.g., "Benzen", "Olie C10-C25")
                           None for categories without scenarios
        category: The compound category (e.g., "BTXER")
        original_substance: Original substance name (only used if no scenario)
        row: The data row with site information (for activity/losseplads context)

    Returns:
        Concentration in µg/L

    Hierarchy:
        1. Activity + Modelstof (e.g., "Servicestationer_Benzen")
        2. Losseplads + Modelstof
        3. Losseplads + Category
        4. Compound (modelstof)
        5. Category scenario
    """
    # Extract context from row
    branche = row.get("Lokalitetensbranche") or row.get("Branche") or ""
    aktivitet = row.get("Lokalitetensaktivitet") or row.get("Aktivitet") or ""
    industries = str(branche).split(";") if pd.notna(branche) else []
    activities = str(aktivitet).split(";") if pd.notna(aktivitet) else []
    all_industries = [x.strip() for x in industries + activities if x.strip()]

    is_losseplads = category == "LOSSEPLADS" or (
        original_substance and "Landfill Override:" in original_substance
    )

    # Determine which substance to use for hierarchy lookup
    lookup_substance = scenario_modelstof if scenario_modelstof else original_substance

    # Level 1: Activity + Substance
    for industry in all_industries:
        key = f"{industry}_{lookup_substance}"
        if key in STANDARD_CONCENTRATIONS["activity_substance"]:
            return STANDARD_CONCENTRATIONS["activity_substance"][key]

    # Level 2: Losseplads context
    if is_losseplads:
        # Try exact substance match
        if (
            lookup_substance
            and lookup_substance in STANDARD_CONCENTRATIONS["losseplads"]
        ):
            return STANDARD_CONCENTRATIONS["losseplads"][lookup_substance]
        # Try category match
        if category in STANDARD_CONCENTRATIONS["losseplads"]:
            return STANDARD_CONCENTRATIONS["losseplads"][category]

    # Level 3: Direct compound lookup (for modelstoffer)
    if lookup_substance and lookup_substance in STANDARD_CONCENTRATIONS["compound"]:
        return STANDARD_CONCENTRATIONS["compound"][lookup_substance]

    # Level 4: Category scenario
    if scenario_modelstof:
        scenario_key = f"{category}__via_{scenario_modelstof}"
        if scenario_key in STANDARD_CONCENTRATIONS["category"]:
            return STANDARD_CONCENTRATIONS["category"][scenario_key]

    # Level 5: Category fallback (for categories without scenarios)
    if category in STANDARD_CONCENTRATIONS["category"]:
        return STANDARD_CONCENTRATIONS["category"][category]

    # No match - raise error
    raise ValueError(
        f"No concentration for scenario:\n"
        f"  Category: {category}\n"
        f"  Modelstof: {scenario_modelstof}\n"
        f"  Original substance: {original_substance}"
    )


def _compute_flux_from_concentration(row: pd.Series) -> pd.Series:
    """
    Compute flux from concentration, area, and infiltration.

    Formula: Flux = Area × Infiltration × Concentration

    Units:
        Area: m²
        Infiltration: mm/year → converted to m/year
        Concentration: µg/L → converted to µg/m³
        Flux: µg/year → also converted to mg, g, kg
    """
    infiltration_m_yr = row["Infiltration_mm_per_year"] / 1000.0
    volume_m3_yr = row["Area_m2"] * infiltration_m_yr
    concentration_ug_m3 = row["Standard_Concentration_ug_L"] * 1000.0

    flux_ug_yr = volume_m3_yr * concentration_ug_m3

    row["Pollution_Flux_ug_per_year"] = flux_ug_yr
    row["Pollution_Flux_mg_per_year"] = flux_ug_yr / 1000.0
    row["Pollution_Flux_g_per_year"] = flux_ug_yr / 1_000_000.0
    row["Pollution_Flux_kg_per_year"] = flux_ug_yr / 1_000_000_000.0

    return row


# ===========================================================================
# Flux calculation (scenario-based)
# ===========================================================================


def _calculate_flux(enriched: pd.DataFrame) -> pd.DataFrame:
    """
    Compute pollution flux (J = A · C · I) with scenario-based aggregation.

    Key approach:
    - All compounds in a category use modelstof concentrations (scenarios)
    - One flux value per scenario per site per river
    - Categories with multiple modelstoffer generate multiple scenarios
    - Sites affecting multiple GVFK: flux calculated once per river, but tracked for ALL GVFK

    Example: Site with 4 different BTXER compounds generates 2 flux rows:
      - BTXER__via_Benzen (400 µg/L)
      - BTXER__via_Olie C10-C25 (3000 µg/L)
    """
    # Group by site + segment + category to aggregate substances
    # Flux is calculated ONCE per river, but we track ALL GVFK affected
    grouping_cols = ["Lokalitet_ID", "Nearest_River_ov_id", "Qualifying_Category"]

    # BEFORE aggregating: collect ALL GVFK for each (site + river + category) combination
    gvfk_tracking = (
        enriched.groupby(grouping_cols, dropna=False)["GVFK"]
        .apply(list)
        .reset_index()
    )
    gvfk_tracking.columns = ["Lokalitet_ID", "Nearest_River_ov_id", "Qualifying_Category", "All_GVFK"]

    # Aggregate all metadata, taking minimum distance and first occurrence of other fields
    grouped = (
        enriched.groupby(grouping_cols, dropna=False)
        .agg(
            {
                "GVFK": "first",  # Temporary - used for concentration lookup only
                "Area_m2": "first",  # Area is constant per site
                "Infiltration_mm_per_year": "first",  # Infiltration is constant per site
                "Nearest_River_FID": "first",  # Take first FID
                "River_Segment_Name": "first",
                "River_Segment_Length_m": "first",
                "River_Segment_GVFK": "first",
                "Distance_to_River_m": "min",  # Use MINIMUM distance across all GVFKs
                "River_Segment_Count": "max",  # Use maximum count
            }
        )
        .reset_index()
    )

    site_categories = grouped

    flux_rows = []

    for _, site_cat in site_categories.iterrows():
        category = site_cat["Qualifying_Category"]

        # Get scenarios for this category
        scenarios = CATEGORY_SCENARIOS.get(category, [])

        if not scenarios:
            # Category has no scenarios (LOSSEPLADS, ANDRE, PFAS)
            # Use old approach: pick first substance as representative
            site_substances = enriched[
                (enriched["Lokalitet_ID"] == site_cat["Lokalitet_ID"])
                & (enriched["GVFK"] == site_cat["GVFK"])
                & (enriched["Qualifying_Category"] == category)
            ]
            first_substance = site_substances.iloc[0]["Qualifying_Substance"]

            # Lookup concentration using old method
            conc = _lookup_concentration_for_scenario(
                scenario_modelstof=None,
                category=category,
                original_substance=first_substance,
                row=site_cat,
            )

            # Create single flux row
            flux_row = site_cat.copy()
            flux_row["Qualifying_Substance"] = first_substance
            flux_row["Standard_Concentration_ug_L"] = conc
            flux_row = _compute_flux_from_concentration(flux_row)
            flux_rows.append(flux_row)
        else:
            # Category has scenarios - generate one flux row per scenario
            for modelstof in scenarios:
                # Lookup concentration for this scenario
                conc = _lookup_concentration_for_scenario(
                    scenario_modelstof=modelstof,
                    category=category,
                    original_substance=None,  # Not used for scenarios
                    row=site_cat,
                )

                # Create flux row for this scenario
                flux_row = site_cat.copy()
                flux_row["Qualifying_Substance"] = f"{category}__via_{modelstof}"
                flux_row["Standard_Concentration_ug_L"] = conc
                flux_row = _compute_flux_from_concentration(flux_row)
                flux_rows.append(flux_row)

    df = pd.DataFrame(flux_rows)

    # Now expand each row to include ALL GVFK that were involved
    # Merge with gvfk_tracking to get the list of all GVFK
    df = df.merge(
        gvfk_tracking,
        on=["Lokalitet_ID", "Nearest_River_ov_id", "Qualifying_Category"],
        how="left"
    )

    # Expand: one row per GVFK
    expanded_rows = []
    for _, row in df.iterrows():
        all_gvfk = row["All_GVFK"]
        if isinstance(all_gvfk, list) and len(all_gvfk) > 0:
            for gvfk in all_gvfk:
                expanded_row = row.copy()
                expanded_row["GVFK"] = gvfk
                expanded_rows.append(expanded_row)
        else:
            # Fallback: keep original row as-is
            expanded_rows.append(row)

    df = pd.DataFrame(expanded_rows)

    # Drop the helper column
    if "All_GVFK" in df.columns:
        df = df.drop(columns=["All_GVFK"])

    # Filter out rows with invalid concentration (-1)
    rows_before = len(df)
    invalid_rows = df[df["Standard_Concentration_ug_L"] == -1]
    df = df[df["Standard_Concentration_ug_L"] != -1].copy()
    rows_after = len(df)

    print(f"  Input rows (substances): {len(enriched)}")
    print(f"  Output rows (scenarios): {rows_after}")
    if rows_before > rows_after:
        removed = rows_before - rows_after
        print(
            f"  Filtered out {removed} rows where STANDARD_CONCENTRATIONS returned -1 "
            f"(no valid concentration defined for those categories in config)."
        )
        # Show which categories were filtered (e.g., LOSSEPLADS, ANDRE, PFAS)
        filtered_categories = invalid_rows["Qualifying_Category"].value_counts()
        for cat, count in filtered_categories.items():
            print(f"    - {cat}: {count} rows")

    if not df.empty:
        print(
            f"  Concentration range: {df['Standard_Concentration_ug_L'].min():.1f} - {df['Standard_Concentration_ug_L'].max():.1f} µg/L"
        )

    return df


def _aggregate_flux_by_segment(flux_details: pd.DataFrame) -> pd.DataFrame:
    """
    Aggregate fluxes per river segment and substance.
    Returns a DataFrame summarising totals and basic statistics.

    IMPORTANT: Use River_FID to keep split geometries distinct even if ov_id repeats.
    """
    if flux_details.empty:
        return pd.DataFrame()

    records: List[Dict[str, object]] = []
    # Group by FID + ov_id + category + substance
    group_columns = [
        "Nearest_River_FID",
        "Nearest_River_ov_id",
        "Qualifying_Category",
        "Qualifying_Substance",
    ]

    for group_keys, group_df in flux_details.groupby(group_columns, dropna=False):
        record = dict(zip(group_columns, group_keys))
        # Aggregate metadata - take first occurrence
        record["Nearest_River_FID"] = int(group_df["Nearest_River_FID"].iloc[0])
        record["River_Segment_Name"] = group_df["River_Segment_Name"].iloc[0]
        record["River_Segment_Length_m"] = group_df["River_Segment_Length_m"].iloc[0]
        record["River_Segment_GVFK"] = group_df["River_Segment_GVFK"].iloc[0]

        # Aggregate flux values
        record["Total_Flux_ug_per_year"] = group_df["Pollution_Flux_ug_per_year"].sum()
        record["Total_Flux_mg_per_year"] = group_df["Pollution_Flux_mg_per_year"].sum()
        record["Total_Flux_g_per_year"] = group_df["Pollution_Flux_g_per_year"].sum()
        record["Total_Flux_kg_per_year"] = group_df["Pollution_Flux_kg_per_year"].sum()

        # Aggregate site information
        record["Contributing_Site_Count"] = group_df["Lokalitet_ID"].nunique()
        record["Contributing_Site_IDs"] = ", ".join(
            sorted(group_df["Lokalitet_ID"].unique())
        )
        record["Min_Distance_to_River_m"] = group_df["Distance_to_River_m"].min()
        record["Max_Distance_to_River_m"] = group_df["Distance_to_River_m"].max()
        record["River_Segment_Count"] = int(group_df["River_Segment_Count"].max())
        records.append(record)

    return pd.DataFrame.from_records(records)


# ===========================================================================
# Cmix calculation and MKK application
# ===========================================================================


def _calculate_cmix(
    segment_flux: pd.DataFrame,
    flow_scenarios: pd.DataFrame,
    qpoints_gdf: gpd.GeoDataFrame | None = None,
) -> pd.DataFrame:
    """
    Combine aggregated flux with flow scenarios to compute Cmix.
    Returns an empty DataFrame if either input is empty.
    """
    if segment_flux.empty or flow_scenarios.empty:
        if segment_flux.empty:
            print("NOTE: No segment flux rows available. Skipping Cmix calculation.")
        else:
            print("NOTE: Flow scenarios missing. Cmix calculation skipped.")
        return pd.DataFrame()

    # Build flow lookup by ov_id (baseline)
    flow_by_ov = {
        (str(row["ov_id"]), row["Scenario"]): row["Flow_m3_s"]
        for _, row in flow_scenarios.iterrows()
        if pd.notna(row["Flow_m3_s"])
    }

    # Optional: build flow lookup by River_FID (nearest-per-segment)
    flow_by_fid = {}
    if (
        qpoints_gdf is not None
        and STEP6_FLOW_SELECTION_MODE == "max_near_segment"
        and "geometry" in qpoints_gdf.columns
    ):
        try:
            rivers = load_river_segments()
            if rivers.crs != qpoints_gdf.crs:
                rivers = rivers.to_crs(qpoints_gdf.crs)

            scenario_cols = [c for c in FLOW_SCENARIO_COLUMNS if c in qpoints_gdf.columns]
            if scenario_cols:
                flow_long = qpoints_gdf.melt(
                    id_vars=["ov_id", "geometry"],
                    value_vars=scenario_cols,
                    var_name="Scenario_raw",
                    value_name="Flow_m3_s",
                )
                flow_long["Scenario"] = flow_long["Scenario_raw"].map(FLOW_SCENARIO_COLUMNS)
                flow_long = flow_long.drop(columns=["Scenario_raw"])
                flow_long = flow_long[
                    flow_long["Flow_m3_s"].notna() & (flow_long["Flow_m3_s"] > 0)
                ].reset_index(drop=True)

                # Project to metric CRS for distance if needed
                rivers_proj = rivers
                flow_proj = flow_long
                try:
                    if rivers_proj.crs.is_geographic:
                        rivers_proj = rivers_proj.to_crs(epsg=25832)
                        flow_proj = flow_long.copy()
                        flow_proj["geometry"] = flow_long["geometry"].to_crs(epsg=25832).values
                except Exception:
                    flow_proj = flow_long

                buffer_dist = 100.0
                for _, seg in rivers_proj.iterrows():
                    seg_fid = seg.get("River_FID")
                    if pd.isna(seg_fid) or seg.geometry is None:
                        continue
                    try:
                        seg_fid_int = int(seg_fid)
                    except Exception:
                        continue
                    dists = flow_proj.geometry.distance(seg.geometry)
                    nearby_idx = dists <= buffer_dist
                    if not nearby_idx.any():
                        continue
                    nearby = flow_proj[nearby_idx]
                    idx_max_near = nearby.groupby("Scenario")["Flow_m3_s"].idxmax()
                    max_near = nearby.loc[idx_max_near]
                    for _, row in max_near.iterrows():
                        flow_by_fid[(seg_fid_int, row["Scenario"])] = row["Flow_m3_s"]
            else:
                print("NOTE: No scenario columns in Q-point data for nearest-per-segment flow.")
        except Exception as exc:
            print(f"NOTE: Nearest-per-segment flow lookup failed; using ov_id max only. ({exc})")

    merged = segment_flux.merge(
        flow_scenarios,
        left_on="Nearest_River_ov_id",
        right_on="ov_id",
        how="left",
    ).drop(columns=["ov_id"])

    merged = merged.rename(columns={"Scenario": "Flow_Scenario"})

    # Override Flow_m3_s using FID-based lookup if available (nearest mode), else ov_id max
    def _flow_lookup(row):
        key_fid = (row.get("Nearest_River_FID"), row.get("Flow_Scenario"))
        if key_fid in flow_by_fid:
            return flow_by_fid[key_fid]
        key_ov = (str(row.get("Nearest_River_ov_id")), row.get("Flow_Scenario"))
        return flow_by_ov.get(key_ov, np.nan)

    merged["Flow_m3_s"] = merged.apply(_flow_lookup, axis=1)
    valid_flow = merged["Flow_m3_s"].notna() & (merged["Flow_m3_s"] > 0)
    merged["Has_Flow_Data"] = valid_flow
    merged["Flux_ug_per_second"] = merged["Total_Flux_ug_per_year"] / SECONDS_PER_YEAR
    # Cmix in ug/L = Flux (ug/s) / Flow (m3/s) / 1000 (L/m3)
    merged["Cmix_ug_L"] = np.where(
        valid_flow,
        merged["Flux_ug_per_second"] / (merged["Flow_m3_s"] * 1000),
        np.nan,
    )

    return merged


def _apply_mkk_thresholds(cmix_results: pd.DataFrame) -> pd.DataFrame:
    """
    Apply in-memory MKK thresholds (if provided) and compute exceedance flags.
    The lookup checks substance first and then falls back to category.
    """
    if cmix_results.empty:
        return cmix_results

    if not MKK_THRESHOLDS:
        cmix_results["MKK_ug_L"] = np.nan
        cmix_results["Exceedance_Flag"] = False
        cmix_results["Exceedance_Ratio"] = np.nan
        print("NOTE: No MKK thresholds defined. Exceedance metrics left blank.")
        return cmix_results

    def lookup_threshold(row: pd.Series) -> float:
        substance = row.get("Qualifying_Substance")
        category = row.get("Qualifying_Category")

        # Strip "Landfill Override:" prefix if present
        if substance and "Landfill Override:" in substance:
            substance = substance.replace("Landfill Override:", "").strip()

        # Strip "Branch/Activity:" prefix if present
        if substance and "Branch/Activity:" in substance:
            substance = substance.replace("Branch/Activity:", "").strip()

        # Per meeting decision: Only use substance-specific MKK for the 16 modelstoffer
        if substance in MODELSTOFFER and substance in MKK_THRESHOLDS:
            return MKK_THRESHOLDS[substance]

        # All other substances use category MKK
        if category in MKK_THRESHOLDS:
            return MKK_THRESHOLDS[category]
        return np.nan

    cmix_results = cmix_results.copy()
    cmix_results["MKK_ug_L"] = cmix_results.apply(lookup_threshold, axis=1)
    cmix_results["Exceedance_Flag"] = cmix_results["MKK_ug_L"].notna() & (
        cmix_results["Cmix_ug_L"] > cmix_results["MKK_ug_L"]
    )
    cmix_results["Exceedance_Ratio"] = np.where(
        cmix_results["MKK_ug_L"].notna() & (cmix_results["MKK_ug_L"] > 0),
        cmix_results["Cmix_ug_L"] / cmix_results["MKK_ug_L"],
        np.nan,
    )

    return cmix_results


# ===========================================================================
# Summary and exceedance views
# ===========================================================================


def _build_segment_summary(
    flux_details: pd.DataFrame,
    segment_flux: pd.DataFrame,
    cmix_results: pd.DataFrame,
) -> pd.DataFrame:
    """
    Build a one-row-per-segment summary showing total flux, max exceedance ratio,
    scenario lists, and contributing sites.
    """
    if cmix_results.empty:
        return pd.DataFrame()

    group_cols = [
        "Nearest_River_FID",
        "Nearest_River_ov_id",
        "River_Segment_Name",
        "River_Segment_GVFK",
    ]

    agg_funcs = {
        "Total_Flux_kg_per_year": "sum",
        "Cmix_ug_L": "max",
        "Exceedance_Ratio": "max",
        "Flow_Scenario": lambda s: ", ".join(sorted(set(str(v) for v in s.dropna()))),
        "Qualifying_Category": lambda s: ", ".join(
            sorted(set(str(v) for v in s.dropna()))
        ),
    }

    summary = (
        cmix_results.groupby(group_cols, dropna=False).agg(agg_funcs).reset_index()
    )

    # Add site counts and IDs
    site_info = (
        flux_details.groupby(["Nearest_River_FID", "Nearest_River_ov_id"], dropna=False)["Lokalitet_ID"]
        .agg(Site_Count="nunique", Site_IDs=lambda x: ", ".join(sorted(set(x))))
        .reset_index()
    )

    summary = summary.merge(site_info, on=["Nearest_River_FID", "Nearest_River_ov_id"], how="left")

    # Rename columns (keep Total_Flux_kg_per_year for backwards compatibility with visualization code)
    summary = summary.rename(
        columns={
            "Cmix_ug_L": "Max_Cmix_ug_L",
            "Exceedance_Ratio": "Max_Exceedance_Ratio",
            "Flow_Scenario": "Flow_Scenarios",
            "Qualifying_Category": "Categories",
        }
    )

    # Flag exceedances
    summary["Has_MKK_Exceedance"] = summary["Max_Exceedance_Ratio"].notna() & (
        summary["Max_Exceedance_Ratio"] > 1.0
    )

    # Add Failing_Scenarios column (expected by visualization code)
    # This identifies which flow scenarios exceed MKK for each segment
    failing_scenarios = []
    for _, row in summary.iterrows():
        ov_id = row["Nearest_River_ov_id"]
        segment_cmix = cmix_results[
            (cmix_results["Nearest_River_ov_id"] == ov_id)
            & (cmix_results["Exceedance_Flag"] == True)
        ]
        if not segment_cmix.empty:
            scenarios = sorted(segment_cmix["Flow_Scenario"].unique())
            failing_scenarios.append(", ".join(scenarios))
        else:
            failing_scenarios.append("")

    summary["Failing_Scenarios"] = failing_scenarios

    return summary.sort_values(
        "Max_Exceedance_Ratio", ascending=False, na_position="last"
    )


def _extract_exceedance_views(
    flux_details: pd.DataFrame,
    cmix_results: pd.DataFrame,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Create per-site and per-GVFK tables limited to segments with MKK exceedances.
    """

    site_columns = [
        "GVFK",
        "Lokalitet_ID",
        "Lokalitetsnavn",
        "Qualifying_Category",
        "Qualifying_Substance",
        "Pollution_Flux_kg_per_year",
        "Nearest_River_FID",
        "Nearest_River_ov_id",
        "River_Segment_Name",
        "River_Segment_GVFK",
        "Flow_Scenario",
        "Flow_m3_s",
        "Cmix_ug_L",
        "MKK_ug_L",
        "Exceedance_Ratio",
        "Segment_Total_Flux_kg_per_year",
        "Distance_to_River_m",
    ]

    gvfk_columns = [
        "GVFK",
        "Nearest_River_FID",
        "Nearest_River_ov_id",
        "River_Segment_Name",
        "River_Segment_GVFK",
        "Contributing_Site_Count",
        "Site_IDs",
        "Categories",
        "Substances",
        "Flow_Scenarios",
        "Total_Site_Flux_kg_per_year",
        "Segment_Total_Flux_kg_per_year",
        "Max_Cmix_ug_L",
        "MKK_ug_L",
        "Max_Exceedance_Ratio",
    ]

    if cmix_results.empty or "Exceedance_Flag" not in cmix_results.columns:
        return pd.DataFrame(columns=site_columns), pd.DataFrame(columns=gvfk_columns)

    exceedances = cmix_results.loc[cmix_results["Exceedance_Flag"] == True].copy()
    if exceedances.empty:
        return pd.DataFrame(columns=site_columns), pd.DataFrame(columns=gvfk_columns)

    merge_cols = ["Nearest_River_FID", "Nearest_River_ov_id", "Qualifying_Substance", "Qualifying_Category"]
    subset_cols = merge_cols + [
        "Flow_Scenario",
        "Cmix_ug_L",
        "MKK_ug_L",
        "Exceedance_Ratio",
    ]

    if "Flow_m3_s" in exceedances.columns:
        subset_cols.append("Flow_m3_s")

    if "Total_Flux_kg_per_year" in exceedances.columns:
        subset_cols.append("Total_Flux_kg_per_year")

    exceed_subset = exceedances[subset_cols].copy()
    if "Total_Flux_kg_per_year" in exceed_subset.columns:
        exceed_subset = exceed_subset.rename(
            columns={"Total_Flux_kg_per_year": "Segment_Total_Flux_kg_per_year"}
        )

    site_exceedances = flux_details.merge(exceed_subset, on=merge_cols, how="inner")
    if site_exceedances.empty:
        return pd.DataFrame(columns=site_columns), pd.DataFrame(columns=gvfk_columns)

    def _ensure_columns(df: pd.DataFrame, columns: List[str]) -> List[str]:
        return [col for col in columns if col in df.columns]

    site_exceedances = site_exceedances.sort_values(
        ["Exceedance_Ratio", "GVFK"], ascending=[False, True], ignore_index=True
    )
    site_view = site_exceedances[_ensure_columns(site_exceedances, site_columns)].copy()

    def _join_unique(values: pd.Series) -> str:
        unique_vals = sorted({str(v) for v in values.dropna() if str(v)})
        return ", ".join(unique_vals)

    group_cols = [
        "GVFK",
        "Nearest_River_FID",
        "Nearest_River_ov_id",
        "River_Segment_Name",
        "River_Segment_GVFK",
    ]
    agg_map = {
        "Lokalitet_ID": lambda s: len(set(s)),
        "Pollution_Flux_kg_per_year": "sum",
        "Qualifying_Category": _join_unique,
        "Qualifying_Substance": _join_unique,
        "Flow_Scenario": _join_unique,
        "Cmix_ug_L": "max",
        "MKK_ug_L": "max",
        "Exceedance_Ratio": "max",
    }
    if "Segment_Total_Flux_kg_per_year" in site_exceedances.columns:
        agg_map["Segment_Total_Flux_kg_per_year"] = "max"
    grouped = (
        site_exceedances.groupby(group_cols, dropna=False).agg(agg_map).reset_index()
    )

    if not grouped.empty:
        grouped = grouped.rename(
            columns={
                "Lokalitet_ID": "Contributing_Site_Count",
                "Pollution_Flux_kg_per_year": "Total_Site_Flux_kg_per_year",
                "Qualifying_Category": "Categories",
                "Qualifying_Substance": "Substances",
                "Flow_Scenario": "Flow_Scenarios",
                "Cmix_ug_L": "Max_Cmix_ug_L",
                "Exceedance_Ratio": "Max_Exceedance_Ratio",
            }
        )
        site_ids = (
            site_exceedances.groupby(group_cols, dropna=False)["Lokalitet_ID"]
            .apply(lambda s: ", ".join(sorted(set(s))))
            .reset_index(name="Site_IDs")
        )
        grouped = grouped.merge(site_ids, on=group_cols, how="left")

    gvfk_view = grouped[_ensure_columns(grouped, gvfk_columns)].copy()
    return site_view, gvfk_view


# ===========================================================================
# Output export
# ===========================================================================


def _export_results(
    flux_details: pd.DataFrame,
    cmix_results: pd.DataFrame,
    segment_summary: pd.DataFrame,
    site_exceedances: pd.DataFrame,
) -> None:
    """Write Step 6 core outputs to disk."""
    flux_details.to_csv(
        get_output_path("step6_flux_site_segment"), index=False, encoding="utf-8"
    )
    cmix_results.to_csv(
        get_output_path("step6_cmix_results"), index=False, encoding="utf-8"
    )
    segment_summary.to_csv(
        get_output_path("step6_segment_summary"), index=False, encoding="utf-8"
    )
    site_exceedances.to_csv(
        get_output_path("step6_site_mkk_exceedances"), index=False, encoding="utf-8"
    )

    print(f"\nExported {len(flux_details)} site-level flux records")
    print(f"Exported {len(cmix_results)} Cmix scenarios")
    print(f"Exported {len(segment_summary)} segment summaries")
    print(f"Exported {len(site_exceedances)} site exceedance records")
    # Quick reminder of primary Step 6 outputs
    print("\nStep 6 output files (see config.py CORE_OUTPUTS):")
    print(f"  - site_flux:        {get_output_path('step6_flux_site_segment')}")
    print(f"  - cmix_results:     {get_output_path('step6_cmix_results')}")
    print(f"  - segment_summary:  {get_output_path('step6_segment_summary')}")
    print(f"  - site_exceedances: {get_output_path('step6_site_mkk_exceedances')}")


# ===========================================================================
# Entry point
# ===========================================================================

if __name__ == "__main__":
    run_step6()
