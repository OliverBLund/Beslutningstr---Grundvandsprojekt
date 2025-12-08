"""
Step 4: Calculate distances between V1/V2 sites and river segments.

This module calculates distances for each lokalitet-GVFK combination,
identifies minimum distances per site, and creates output files for
risk assessment and visualization.
"""

import geopandas as gpd
import pandas as pd
import numpy as np
import os
from config import (
    COLUMN_MAPPINGS,
    GRUNDVAND_LAYER_NAME,
    GRUNDVAND_PATH,
    RIVERS_LAYER_NAME,
    RIVERS_PATH,
    WORKFLOW_SETTINGS,
    get_output_path,
)
from .step_reporter import report_step_header, report_counts, report_subsection


def run_step4(v1v2_combined):
    """
    Step 4: Calculate distances between V1/V2 sites and river segments with contact.
    Handles one-to-many site-GVFK relationships: calculates distances for each
    lokalitet-GVFK combination separately.

    Args:
        v1v2_combined (GeoDataFrame): V1/V2 sites with GVFK relationships from Step 3

    Returns:
        DataFrame: Distance calculation results with minimum distance flags
    """
    report_step_header(4, "Calculate Distances")

    if v1v2_combined.empty:
        print("No V1/V2 sites from Step 3 - cannot calculate distances")
        return None

    gvfk_name_col = COLUMN_MAPPINGS["contamination_csv"]["gvfk_id"]
    site_id_col = COLUMN_MAPPINGS["contamination_shp"]["site_id"]

    # Load rivers dataset
    rivers = gpd.read_file(RIVERS_PATH, layer=RIVERS_LAYER_NAME)
    river_gvfk_col = COLUMN_MAPPINGS["rivers"]["gvfk_id"]
    contact_col = COLUMN_MAPPINGS["rivers"]["contact"]

    if river_gvfk_col not in rivers.columns:
        raise ValueError(f"'{river_gvfk_col}' column not found in rivers dataset")

    rivers[river_gvfk_col] = rivers[river_gvfk_col].astype(str).str.strip()
    valid_gvfk_mask = rivers[river_gvfk_col] != ""

    # Filter for river-GVFK contact
    if contact_col in rivers.columns:
        contact_value = WORKFLOW_SETTINGS["contact_filter_value"]
        rivers_with_contact = rivers[
            (rivers[contact_col] == contact_value) & valid_gvfk_mask
        ]
    else:
        # New Grunddata format: GVFK presence IS the contact indicator
        rivers_with_contact = rivers[valid_gvfk_mask]

    if rivers_with_contact.empty:
        print("No river segments with GVFK contact - cannot calculate distances")
        return None

    # Ensure same CRS
    target_crs = v1v2_combined.crs
    if rivers_with_contact.crs != target_crs:
        rivers_with_contact = rivers_with_contact.to_crs(target_crs)

    # Input summary
    report_subsection("INPUT")
    report_counts(
        "Site-GVFK combinations",
        sites=v1v2_combined[site_id_col].nunique(),
        combinations=len(v1v2_combined),
    )

    # Calculate distances for each lokalitet-GVFK combination
    results_data = []
    total_combinations = len(v1v2_combined)

    for idx, row in v1v2_combined.iterrows():
        # Get row properties
        lokalitet_id = row[site_id_col]
        gvfk_name = row[gvfk_name_col]
        site_type = row.get("Lokalitete", "Unknown")
        site_geom = row.geometry

        # Validate data
        if pd.isna(gvfk_name) or site_geom is None or site_geom.is_empty:
            continue

        # Find river segments in the same GVFK with contact
        matching_rivers = rivers_with_contact[
            rivers_with_contact[river_gvfk_col] == gvfk_name
        ]

        segment_indices = matching_rivers.index.tolist()
        segment_ov_ids = []
        if len(segment_indices) > 0 and "ov_id" in matching_rivers.columns:
            segment_ov_ids = [
                str(val) if pd.notna(val) else ""
                for val in matching_rivers["ov_id"]
            ]

        segment_indices_str = ";".join(str(idx) for idx in segment_indices) if segment_indices else ""
        segment_ov_ids_str = ";".join(segment_ov_ids) if segment_ov_ids else ""

        # Initialize result for this combination
        result = {
            "Lokalitet_ID": lokalitet_id,
            "GVFK": gvfk_name,
            "Site_Type": site_type,
            "Has_Matching_Rivers": len(matching_rivers) > 0,
            "River_Count": len(matching_rivers),
            "Distance_to_River_m": None,
            "River_Segment_Count": len(matching_rivers),
            "River_Segment_FIDs": segment_indices_str,
            "River_Segment_ov_ids": segment_ov_ids_str,
            "Nearest_River_FID": None,
            "Nearest_River_ov_id": None,
            "Nearest_River_ov_navn": None,
        }

        # Preserve Step 5 columns if available
        step5_columns = [
            "Lokalitetensbranche",
            "Lokalitetensaktivitet",
            "Lokalitetensstoffer",
            "Lokalitetsnavn",
            "Lokalitetetsforureningsstatus",
            "Regionsnavn",
            "Kommunenavn",
        ]
        for col in step5_columns:
            if col in row.index:
                result[col] = row[col]

        if matching_rivers.empty:
            # No rivers with contact in this GVFK
            result["Distance_to_River_m"] = None
        else:
            # Calculate minimum distance to all matching river segments
            min_distance = float("inf")
            nearest_river_idx = None
            nearest_river_row = None

            for river_idx, river in matching_rivers.iterrows():
                distance = site_geom.distance(river.geometry)
                if distance < min_distance:
                    min_distance = distance
                    nearest_river_idx = river_idx
                    nearest_river_row = river

            if min_distance == float("inf"):
                result["Distance_to_River_m"] = None
            else:
                result["Distance_to_River_m"] = min_distance
                if nearest_river_idx is not None:
                    result["Nearest_River_FID"] = int(nearest_river_idx)
                if nearest_river_row is not None:
                    if "ov_id" in nearest_river_row:
                        result["Nearest_River_ov_id"] = nearest_river_row.get("ov_id")
                    if "ov_navn" in nearest_river_row:
                        result["Nearest_River_ov_navn"] = nearest_river_row.get("ov_navn")

        results_data.append(result)

    # Create results DataFrame
    if not results_data:
        print("No distances could be calculated")
        return None

    results_df = pd.DataFrame(results_data)

    # Filter to only combinations with valid distances
    valid_results = results_df[results_df["Distance_to_River_m"].notna()].copy()

    if valid_results.empty:
        print("No valid distances calculated")
        return None

    # Add minimum distance identification for each site
    site_min_distances = (
        valid_results.groupby("Lokalitet_ID")["Distance_to_River_m"].min().reset_index()
    )
    site_min_distances.columns = ["Lokalitet_ID", "Min_Distance_m"]

    # Add flag for minimum distance per site
    results_df = results_df.merge(site_min_distances, on="Lokalitet_ID", how="left")
    results_df["Is_Min_Distance"] = (
        results_df["Distance_to_River_m"] == results_df["Min_Distance_m"]
    ) & results_df["Distance_to_River_m"].notna()

    # Update valid_results with the new columns
    valid_results = results_df[results_df["Distance_to_River_m"].notna()].copy()

    # Output summary
    report_subsection("OUTPUT")
    unique_sites_with_distances = valid_results["Lokalitet_ID"].nunique()
    report_counts(
        "Site-GVFK combinations with distances",
        sites=unique_sites_with_distances,
        combinations=len(valid_results),
    )

    if len(valid_results) > 0:
        # Statistics for minimum distances per site
        min_distances_only = valid_results[valid_results["Is_Min_Distance"] == True][
            "Distance_to_River_m"
        ]
        print(
            f"  Distance stats (min per site): mean={min_distances_only.mean():.0f}m, median={min_distances_only.median():.0f}m"
        )

    # Save results
    _save_distance_results(results_df, valid_results, v1v2_combined, site_id_col)

    # Create interactive map
    if len(valid_results) > 0:
        _create_interactive_map(v1v2_combined, rivers_with_contact, valid_results)

    return results_df


def _save_distance_results(results_df, valid_results, v1v2_combined, site_id_col):
    """Save distance calculation results - all lokalitet-GVFK combinations."""

    if len(valid_results) == 0:
        return

    # Save valid distances (used by visualizations)
    valid_results.to_csv(get_output_path("step4_valid_distances"), index=False, encoding="utf-8")

    # Prepare ALL lokalitet-GVFK combinations for risk assessment (no aggregation)
    base_columns = [
        "Lokalitet_ID",
        "GVFK",
        "Site_Type",
        "Distance_to_River_m",
        "Nearest_River_FID",
        "Nearest_River_ov_id",
        "Nearest_River_ov_navn",
        "River_Segment_Count",
        "River_Segment_FIDs",
        "River_Segment_ov_ids",
    ]
    step5_columns = [
        "Lokalitetensbranche",
        "Lokalitetensaktivitet",
        "Lokalitetensstoffer",
        "Lokalitetsnavn",
        "Lokalitetetsforureningsstatus",
        "Regionsnavn",
        "Kommunenavn",
    ]
    available_step5_columns = [
        col for col in step5_columns if col in valid_results.columns
    ]

    output_columns = base_columns + available_step5_columns
    all_combinations = valid_results[output_columns].copy()

    # Save ALL combinations for Step 5 (no minimum filtering, no aggregation)
    all_combinations.to_csv(
        get_output_path("step4_final_distances_for_risk_assessment"), index=False, encoding="utf-8"
    )

    # Create unique distances file (used by visualizations - one row per site)
    min_distance_entries = valid_results[valid_results["Is_Min_Distance"] == True].copy()
    unique_distances = (
        min_distance_entries.sort_values(["Lokalitet_ID", "GVFK"])
        .groupby("Lokalitet_ID")
        .first()
        .reset_index()
    )

    # Prepare unique distances with renamed columns for visualization compatibility
    unique_distances = unique_distances[output_columns].copy()
    unique_distances = unique_distances.rename(columns={"Lokalitet_ID": "Lokalitetsnr"})
    unique_distances.to_csv(get_output_path("unique_lokalitet_distances"), index=False, encoding="utf-8")

    # Create shapefile version with geometry (for visualizations that need geometries)
    if not v1v2_combined.empty:
        # Get geometry for each unique lokalitet (take first occurrence)
        site_geometries = v1v2_combined.drop_duplicates(site_id_col)[
            [site_id_col, "geometry"]
        ]
        site_geometries = site_geometries.rename(columns={site_id_col: "Lokalitetsnr"})

        # Merge with unique distances
        unique_distances_with_geom = unique_distances.merge(
            site_geometries, on="Lokalitetsnr", how="left"
        )

        # Create GeoDataFrame and save shapefile
        unique_gdf = gpd.GeoDataFrame(unique_distances_with_geom, crs=v1v2_combined.crs)
        unique_gdf.to_file(get_output_path("unique_lokalitet_distances_shp"), encoding="utf-8")


def _create_interactive_map(v1v2_combined, rivers_with_contact, valid_results):
    """Create interactive map visualization using sampled data."""

    gvfk_name_col = COLUMN_MAPPINGS["contamination_csv"]["gvfk_id"]
    site_id_col = COLUMN_MAPPINGS["contamination_shp"]["site_id"]
    gvfk_polygon_col = COLUMN_MAPPINGS["grundvand"]["gvfk_id"]

    # Sample data for visualization - limit to 1000 sites for performance
    total_sites = valid_results["Lokalitet_ID"].nunique()
    if total_sites <= 1000:
        sampled_site_ids = valid_results["Lokalitet_ID"].unique()
    else:
        sampled_site_ids = np.random.choice(
            valid_results["Lokalitet_ID"].unique(), size=1000, replace=False
        )

    sampled_results = valid_results[
        valid_results["Lokalitet_ID"].isin(sampled_site_ids)
    ].copy()

    # Get GVFK polygons for visualization
    gvf = gpd.read_file(GRUNDVAND_PATH, layer=GRUNDVAND_LAYER_NAME)
    sampled_gvfks = set(sampled_results["GVFK"].unique())
    relevant_gvfk_polygons = gvf[gvf[gvfk_polygon_col].isin(sampled_gvfks)]

    # Add distance data to combined data for mapping
    v1v2_with_distances = v1v2_combined.copy()
    lookup_data = {}
    for _, row in sampled_results.iterrows():
        key = f"{row['Lokalitet_ID']}_{row['GVFK']}"
        lookup_data[key] = {
            "Distance_m": row["Distance_to_River_m"],
            "Is_Min_Dist": row["Is_Min_Distance"],
            "Min_Dist_m": row.get("Min_Distance_m", row["Distance_to_River_m"]),
        }

    v1v2_with_distances["lookup_key"] = (
        v1v2_with_distances[site_id_col].astype(str)
        + "_"
        + v1v2_with_distances[gvfk_name_col].astype(str)
    )

    for key, data in lookup_data.items():
        mask = v1v2_with_distances["lookup_key"] == key
        v1v2_with_distances.loc[mask, "Distance_m"] = data["Distance_m"]
        v1v2_with_distances.loc[mask, "Is_Min_Dist"] = data["Is_Min_Dist"]
        v1v2_with_distances.loc[mask, "Min_Dist_m"] = data["Min_Dist_m"]

    # Filter to sampled combinations
    sampled_combinations = v1v2_with_distances[
        v1v2_with_distances[site_id_col].isin(sampled_results["Lokalitet_ID"])
        & v1v2_with_distances[gvfk_name_col].isin(sampled_results["GVFK"])
    ]

    if not sampled_combinations.empty:
        try:
            from .create_interactive_map import create_map

            create_map(
                sampled_combinations,
                rivers_with_contact,
                sampled_results,
                relevant_gvfk_polygons,
            )
            print(
                f"  Interactive map: {get_output_path('interactive_distance_map')}"
            )
        except ImportError:
            pass  # Skip silently if map module unavailable
        except Exception as e:
            import warnings
            warnings.filterwarnings(
                "ignore", category=UserWarning, module="pyogrio.raw"
            )
