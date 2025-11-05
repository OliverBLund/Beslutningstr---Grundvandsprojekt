"""
Step 6: Tilstandsvurdering (State Assessment)
============================================

This module follows the agreed workflow:
1. Load Step 5 results, site geometries, GVFK layer mapping, and river segments.
2. Derive areas and infiltration values (J = A · C · I) for every site–segment–substance combination.
3. Aggregate fluxes per river segment and join discharge scenarios.
4. Compute Cmix for each scenario and (optionally) compare to MKK values.
5. Export detailed, aggregated, and summary CSV files and trigger basic reporting.

The implementation intentionally keeps the logic straightforward: no silent fallbacks,
no hidden heuristics—issues surface as explicit exceptions or warnings.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Tuple

import geopandas as gpd
import numpy as np
import pandas as pd
import rasterio

# Ensure the repository root is importable when the script is executed directly.
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from config import (
    GVFK_LAYER_MAPPING_PATH,
    GVD_RASTER_DIR,
    RIVER_FLOW_POINTS_PATH,
    RIVERS_PATH,
    ensure_results_directory,
    get_output_path,
)
try:
    from .step6_visualizations import analyze_and_visualize_step6
except ImportError:  # Script executed directly
    from step6_visualizations import analyze_and_visualize_step6

# Seconds per (mean) year – used to derive flux per second.
SECONDS_PER_YEAR = 365.25 * 24 * 60 * 60

# Standard concentrations (µg/L) by contamination category.
STANDARD_CONCENTRATIONS: Dict[str, float] = {
    "LOSSEPLADS": 1000.0,
    "PAH_FORBINDELSER": 2000.0,
    "BTXER": 1500.0,
    "PHENOLER": 1200.0,
    "UORGANISKE_FORBINDELSER": 1800.0,
    "POLARE_FORBINDELSER": 1300.0,
    "KLOREREDE_OPLA~SNINGSMIDLER": 2500.0,
    "KLOREREDE_OPLØSNINGSMIDLER": 2500.0,  # Same as above, proper encoding
    "PESTICIDER": 800.0,
    "ANDRE": 1000.0,
    "KLOREDE_KULBRINTER": 2200.0,
    "KLOREREDE_PHENOLER": 1200.0,  # Similar to PHENOLER
    "PFAS": 500.0,  # PFAS - using conservative concentration
}

# Flow statistics to import from the q-point shapefile.
FLOW_SCENARIO_COLUMNS = {
    "Average": "Mean",
    "Q90": "Q90",
    "Q95": "Q95",
}

# Optional MKK reference values (µg/L).
# Keys may be either specific substances or broader contamination categories.
# Substance-level entries take precedence over category-level entries.
MKK_THRESHOLDS: Dict[str, float] = {
    # Category defaults (placeholder values – replace with real numbers)
    "BTXER": 10.0,
    "PAH_FORBINDELSER": 5.0,
    "PESTICIDER": 0.5,
    "LOSSEPLADS": 15.0,

    # Example compound overrides (if actual thresholds differ from the category)
    "Benzen": 5.0,      # Overrides BTXER category when substance == "Benzen"
    "Naphtalen": 3.0,   # Overrides PAH_FORBINDELSER
}

def run_step6() -> Dict[str, pd.DataFrame]:
    """
    Execute Step 6 workflow and return the produced DataFrames.

    Returns:
        Dict[str, DataFrame]: keys are 'site_flux', 'segment_flux',
        'cmix_results', and 'segment_summary'.
    """
    ensure_results_directory()

    step5_results = _load_step5_results()
    site_geometries = _load_site_geometries()
    layer_mapping = _load_layer_mapping()
    river_segments = _load_river_segments()

    enriched_results = _prepare_flux_inputs(step5_results, site_geometries, layer_mapping, river_segments)
    flux_details = _calculate_flux(enriched_results)
    segment_flux = _aggregate_flux_by_segment(flux_details)

    flow_scenarios = _load_flow_scenarios()
    cmix_results = _calculate_cmix(segment_flux, flow_scenarios)
    cmix_results = _apply_mkk_thresholds(cmix_results)
    segment_summary = _build_segment_summary(flux_details, segment_flux, cmix_results)

    _export_results(flux_details, segment_flux, cmix_results, segment_summary)
    analyze_and_visualize_step6(flux_details, segment_flux, cmix_results, segment_summary)

    return {
        "site_flux": flux_details,
        "segment_flux": segment_flux,
        "cmix_results": cmix_results,
        "segment_summary": segment_summary,
    }


# ---------------------------------------------------------------------------
# Loading helpers
# ---------------------------------------------------------------------------#

def _load_step5_results() -> pd.DataFrame:
    """Load Step 5 output and validate that required columns are present."""
    step5_path = get_output_path("step5_compound_detailed_combinations")
    df = pd.read_csv(step5_path, encoding='utf-8')

    if df.empty:
        raise ValueError(f"Step 5 output is empty: {step5_path}")

    required_columns = [
        "Lokalitet_ID",
        "GVFK",
        "Qualifying_Category",
        "Qualifying_Substance",
        "Distance_to_River_m",
        "Nearest_River_FID",
        "Nearest_River_ov_id",
        "River_Segment_Count",
    ]
    missing_columns = [col for col in required_columns if col not in df.columns]
    if missing_columns:
        raise ValueError(f"Step 5 output is missing columns: {', '.join(missing_columns)}")

    if df["Nearest_River_FID"].isna().any():
        raise ValueError("One or more rows are missing 'Nearest_River_FID' – rerun Step 4/5.")

    return df


def _load_site_geometries() -> gpd.GeoDataFrame:
    """
    Load Step 3 geometries and dissolve by site to obtain unique polygons and areas.
    """
    sites = gpd.read_file(get_output_path("step3_v1v2_sites"))
    if sites.empty:
        raise ValueError("Step 3 geometries are empty – cannot derive site areas.")

    dissolved = sites.dissolve(by="Lokalitet_", as_index=False)
    dissolved["Area_m2"] = dissolved.geometry.area
    dissolved["Centroid"] = dissolved.geometry.centroid

    return dissolved[["Lokalitet_", "Area_m2", "Centroid", "geometry"]]


def _load_layer_mapping() -> pd.DataFrame:
    """Load GVFK → modellag mapping."""
    mapping = pd.read_csv(GVFK_LAYER_MAPPING_PATH, sep=";", encoding="latin-1")
    if "GVForekom" not in mapping.columns or "DK-modellag" not in mapping.columns:
        raise ValueError("Layer mapping must contain 'GVForekom' and 'DK-modellag' columns.")

    return mapping[["GVForekom", "DK-modellag"]]


def _load_river_segments() -> gpd.GeoDataFrame:
    """Load river segments with contact information."""
    rivers = gpd.read_file(RIVERS_PATH, encoding='utf-8')
    if rivers.empty:
        raise ValueError("River segment file is empty – cannot continue.")
    rivers = rivers.reset_index().rename(columns={"index": "River_FID"})
    return rivers


def _load_flow_scenarios() -> pd.DataFrame:
    """
    Load discharge information per river segment and reshape into long format.

    Returns:
        DataFrame with columns ['ov_id', 'Scenario', 'Flow_m3_s'].
        Empty DataFrame is returned if the source file is missing.
    """
    flow_path = Path(RIVER_FLOW_POINTS_PATH)
    if not flow_path.exists():
        print(f"NOTE: Flow file not found at {flow_path}. Cmix calculations will be skipped.")
        return pd.DataFrame(columns=["ov_id", "Scenario", "Flow_m3_s"])

    flow_points = gpd.read_file(flow_path)
    required_columns = {"ov_id", *FLOW_SCENARIO_COLUMNS.keys()}
    missing_columns = required_columns.difference(flow_points.columns)
    if missing_columns:
        raise ValueError(
            f"Flow file is missing expected columns: {', '.join(sorted(missing_columns))}"
        )

    aggregated = (
        flow_points.groupby("ov_id")[list(FLOW_SCENARIO_COLUMNS.keys())]
        .mean(numeric_only=True)
        .reset_index()
    )

    long_format = aggregated.melt(
        id_vars="ov_id",
        value_vars=list(FLOW_SCENARIO_COLUMNS.keys()),
        var_name="Scenario",
        value_name="Flow_m3_s",
    )
    long_format["Scenario"] = long_format["Scenario"].map(FLOW_SCENARIO_COLUMNS)
    long_format = long_format.dropna(subset=["Flow_m3_s"])

    return long_format


# ---------------------------------------------------------------------------
# Preparation of flux inputs
# ---------------------------------------------------------------------------#

def _prepare_flux_inputs(
    step5_results: pd.DataFrame,
    site_geometries: gpd.GeoDataFrame,
    layer_mapping: pd.DataFrame,
    river_segments: gpd.GeoDataFrame,
) -> pd.DataFrame:
    """Attach areas, modellag, infiltration, and river segment metadata."""
    enriched = step5_results.copy()

    # Attach areas and centroids
    area_lookup = dict(zip(site_geometries["Lokalitet_"], site_geometries["Area_m2"]))
    centroid_lookup = dict(zip(site_geometries["Lokalitet_"], site_geometries["Centroid"]))
    enriched["Area_m2"] = enriched["Lokalitet_ID"].map(area_lookup)

    if enriched["Area_m2"].isna().any():
        missing_sites = enriched.loc[enriched["Area_m2"].isna(), "Lokalitet_ID"].unique()
        raise ValueError(
            "Missing geometries for the following sites: " + ", ".join(sorted(missing_sites))
        )

    # Attach modellag information
    # Only select the columns we need from layer_mapping (not all 83 columns!)
    enriched = enriched.merge(
        layer_mapping[["GVForekom", "DK-modellag"]],
        left_on="GVFK",
        right_on="GVForekom",
        how="left",
    )
    if enriched["DK-modellag"].isna().any():
        missing_layers = enriched.loc[enriched["DK-modellag"].isna(), "GVFK"].unique()
        missing_count = enriched["DK-modellag"].isna().sum()
        print(f"\nWARNING: Missing modellag mapping for {len(missing_layers)} GVFK(s):")
        print(f"   GVFKs: {', '.join(sorted(missing_layers))}")
        print(f"   Affected rows: {missing_count}")
        print(f"   These rows will be excluded from the analysis.")
        print(f"   -> TODO: Add these GVFKs to '{GVFK_LAYER_MAPPING_PATH.name}' for complete analysis.\n")

        # Filter out rows with missing modellag
        enriched = enriched[enriched["DK-modellag"].notna()].copy()

    enriched = enriched.drop(columns=["GVForekom"])

    # Compute infiltration values (mm/year) for each unique (site, modellag)
    enriched["Infiltration_mm_per_year"] = _calculate_infiltration(
        enriched, centroid_lookup
    )

    # Filter out rows where infiltration data is missing
    if enriched["Infiltration_mm_per_year"].isna().any():
        missing_infiltration = enriched["Infiltration_mm_per_year"].isna().sum()
        missing_sites = enriched.loc[enriched["Infiltration_mm_per_year"].isna(), "Lokalitet_ID"].unique()
        print(f"\nWARNING: Missing infiltration data for {len(missing_sites)} site(s):")
        print(f"   Sites: {', '.join(sorted(missing_sites)[:10])}{' ...' if len(missing_sites) > 10 else ''}")
        print(f"   Affected rows: {missing_infiltration}")
        print(f"   Reason: Site centroids fall outside infiltration raster coverage.")
        print(f"   These rows will be excluded from the analysis.\n")

        enriched = enriched[enriched["Infiltration_mm_per_year"].notna()].copy()

    # Attach river metadata
    segment_meta = river_segments[
        ["River_FID", "ov_id", "ov_navn", "Shape_Leng", "GVForekom"]
    ].copy()
    segment_meta = segment_meta.rename(
        columns={
            "ov_id": "River_Segment_ov_id",
            "ov_navn": "River_Segment_Name",
            "Shape_Leng": "River_Segment_Length_m",
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
            "River metadata missing for FID(s): " + ", ".join(str(fid) for fid in sorted(missing_fids))
        )

    # Sanity-check that ov_id matches the value received from Step 5
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

    return enriched


def _calculate_infiltration(
    enriched: pd.DataFrame,
    centroid_lookup: Dict[str, Any],
) -> pd.Series:
    """
    Sample infiltration rasters for each (Lokalitet_ID, modellag) pair.
    Returns a Series aligned with `enriched`.
    """
    cache: Dict[Tuple[str, str], float] = {}

    results: List[float] = []
    for _, row in enriched.iterrows():
        site_id = row["Lokalitet_ID"]
        modellag = row["DK-modellag"]
        key = (site_id, modellag)

        if key not in cache:
            centroid = centroid_lookup.get(site_id)
            if centroid is None:
                raise ValueError(f"No centroid found for site {site_id}")

            layers = _parse_dk_modellag(modellag)
            if not layers:
                raise ValueError(f"Could not interpret modellag '{modellag}' for {site_id}")

            # Sample infiltration for each layer, handling no-data cases
            values = []
            for layer in layers:
                try:
                    val = _sample_infiltration(layer, centroid)
                    values.append(val)
                except ValueError as e:
                    # Raster returned no data at this location
                    values.append(None)

            # If all values are None, store None to filter out later
            if all(v is None for v in values):
                cache[key] = None
            else:
                # Use mean of available values
                valid_values = [v for v in values if v is not None]
                cache[key] = float(np.mean(valid_values))

        results.append(cache[key])

    return pd.Series(results, index=enriched.index, name="Infiltration_mm_per_year")


def _parse_dk_modellag(dk_modellag: str) -> List[str]:
    """
    Interpret the modellag string and return individual layer identifiers.
    Handles simple cases like 'ks3', 'ks1 - ks3', and comma-separated lists.
    """
    if not dk_modellag or pd.isna(dk_modellag):
        return []

    text = str(dk_modellag).strip()
    if not text:
        return []

    if " - " in text:
        start, end = text.split(" - ")
        start = start.strip()
        end = end.strip()
        if len(start) < 3 or len(end) < 3:
            return [text]
        prefix = start[:2]
        try:
            start_num = int(start[2:])
            end_num = int(end[2:])
        except ValueError:
            return [text]
        return [f"{prefix}{i}" for i in range(start_num, end_num + 1)]

    separators = [",", ";", "/"]
    for sep in separators:
        if sep in text:
            return [part.strip() for part in text.split(sep) if part.strip()]

    return [text]


def _sample_infiltration(layer: str, centroid) -> float:
    """
    Sample the infiltration raster for a given layer at the site centroid.
    Returns the sampled value in mm/year.
    """
    # Handle special case: "lag" references should use "lay12" raster
    # (lag1, lag2, etc. all map to the combined lay12 raster)
    if layer.startswith("lag"):
        layer = "lay12"

    raster_path = Path(GVD_RASTER_DIR) / f"DKM_gvd_{layer}.tif"
    if not raster_path.exists():
        raise FileNotFoundError(f"Infiltration raster not found: {raster_path}")

    with rasterio.open(raster_path) as src:
        x, y = centroid.x, centroid.y
        value = next(src.sample([(x, y)]), [np.nan])[0]

        if value is None or np.isnan(value) or value == src.nodata:
            # Return None for no-data, will be handled upstream
            raise ValueError(
                f"Infiltration raster {raster_path.name} returned no data at ({x}, {y})."
            )
        return float(value)


# ---------------------------------------------------------------------------
# Flux calculation and aggregation
# ---------------------------------------------------------------------------#

def _calculate_flux(enriched: pd.DataFrame) -> pd.DataFrame:
    """Compute pollution flux (J = A · C · I) for each row."""
    df = enriched.copy()

    df["Standard_Concentration_ug_L"] = df["Qualifying_Category"].map(STANDARD_CONCENTRATIONS)
    if df["Standard_Concentration_ug_L"].isna().any():
        missing_categories = df.loc[
            df["Standard_Concentration_ug_L"].isna(), "Qualifying_Category"
        ].unique()
        raise ValueError(
            "No concentration defined for categories: " + ", ".join(sorted(missing_categories))
        )

    infiltration_m_per_year = df["Infiltration_mm_per_year"] / 1000.0
    volume_m3_per_year = df["Area_m2"] * infiltration_m_per_year
    concentration_ug_per_m3 = df["Standard_Concentration_ug_L"] * 1000.0

    df["Pollution_Flux_ug_per_year"] = volume_m3_per_year * concentration_ug_per_m3
    df["Pollution_Flux_mg_per_year"] = df["Pollution_Flux_ug_per_year"] / 1000.0
    df["Pollution_Flux_g_per_year"] = df["Pollution_Flux_ug_per_year"] / 1_000_000.0
    df["Pollution_Flux_kg_per_year"] = df["Pollution_Flux_ug_per_year"] / 1_000_000_000.0

    return df


def _aggregate_flux_by_segment(flux_details: pd.DataFrame) -> pd.DataFrame:
    """
    Aggregate fluxes per river segment and substance.
    Returns a DataFrame summarising totals and basic statistics.
    """
    if flux_details.empty:
        return pd.DataFrame()

    records: List[Dict[str, object]] = []
    group_columns = [
        "Nearest_River_FID",
        "Nearest_River_ov_id",
        "River_Segment_Name",
        "River_Segment_Length_m",
        "River_Segment_GVFK",
        "Qualifying_Category",
        "Qualifying_Substance",
    ]

    for group_keys, group_df in flux_details.groupby(group_columns, dropna=False):
        record = dict(zip(group_columns, group_keys))
        record["Total_Flux_ug_per_year"] = group_df["Pollution_Flux_ug_per_year"].sum()
        record["Total_Flux_mg_per_year"] = group_df["Pollution_Flux_mg_per_year"].sum()
        record["Total_Flux_g_per_year"] = group_df["Pollution_Flux_g_per_year"].sum()
        record["Total_Flux_kg_per_year"] = group_df["Pollution_Flux_kg_per_year"].sum()
        record["Contributing_Site_Count"] = group_df["Lokalitet_ID"].nunique()
        record["Contributing_Site_IDs"] = ", ".join(sorted(group_df["Lokalitet_ID"].unique()))
        record["Min_Distance_to_River_m"] = group_df["Distance_to_River_m"].min()
        record["Max_Distance_to_River_m"] = group_df["Distance_to_River_m"].max()
        record["River_Segment_Count"] = int(group_df["River_Segment_Count"].max())
        records.append(record)

    return pd.DataFrame.from_records(records)


# ---------------------------------------------------------------------------
# Hydraulics and compliance
# ---------------------------------------------------------------------------#

def _calculate_cmix(
    segment_flux: pd.DataFrame,
    flow_scenarios: pd.DataFrame,
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

    merged = segment_flux.merge(
        flow_scenarios,
        left_on="Nearest_River_ov_id",
        right_on="ov_id",
        how="left",
    ).drop(columns=["ov_id"])

    merged = merged.rename(columns={"Scenario": "Flow_Scenario"})
    valid_flow = merged["Flow_m3_s"].notna() & (merged["Flow_m3_s"] > 0)
    merged["Has_Flow_Data"] = valid_flow
    merged["Flux_ug_per_second"] = merged["Total_Flux_ug_per_year"] / SECONDS_PER_YEAR
    merged["Cmix_ug_L"] = np.where(
        valid_flow,
        merged["Flux_ug_per_second"] / merged["Flow_m3_s"],
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

        if substance in MKK_THRESHOLDS:
            return MKK_THRESHOLDS[substance]
        if category in MKK_THRESHOLDS:
            return MKK_THRESHOLDS[category]
        return np.nan

    cmix_results = cmix_results.copy()
    cmix_results["MKK_ug_L"] = cmix_results.apply(lookup_threshold, axis=1)
    cmix_results["Exceedance_Flag"] = cmix_results["MKK_ug_L"].notna() & (
        cmix_results["Cmix_ug_L"] > cmix_results["MKK_ug_L"]
    )
    cmix_results["Exceedance_Ratio"] = np.where(
        cmix_results["MKK_ug_L"].notna(),
        cmix_results["Cmix_ug_L"] / cmix_results["MKK_ug_L"],
        np.nan,
    )
    return cmix_results


def _build_segment_summary(
    flux_details: pd.DataFrame,
    segment_flux: pd.DataFrame,
    cmix_results: pd.DataFrame,
) -> pd.DataFrame:
    """Produce a concise per-segment overview."""
    if segment_flux.empty:
        return pd.DataFrame()

    summary_rows: List[Dict[str, object]] = []
    cmix_lookup = (
        cmix_results.groupby("Nearest_River_ov_id") if not cmix_results.empty else None
    )

    for segment_id, group in segment_flux.groupby("Nearest_River_ov_id"):
        related_sites = flux_details.loc[
            flux_details["Nearest_River_ov_id"] == segment_id, "Lokalitet_ID"
        ].unique()

        if cmix_lookup is not None and segment_id in cmix_lookup.groups:
            cmix_subset = cmix_lookup.get_group(segment_id)
        else:
            cmix_subset = pd.DataFrame()

        summary_rows.append(
            {
                "Nearest_River_ov_id": segment_id,
                "River_Segment_Name": group["River_Segment_Name"].iloc[0],
                "River_Segment_Length_m": group["River_Segment_Length_m"].iloc[0],
                "River_Segment_GVFK": group["River_Segment_GVFK"].iloc[0],
                "Total_Flux_kg_per_year": group["Total_Flux_kg_per_year"].sum(),
                "Substances": ", ".join(sorted(group["Qualifying_Substance"].unique())),
                "Categories": ", ".join(sorted(group["Qualifying_Category"].unique())),
                "Contributing_Site_Count": len(related_sites),
                "Contributing_Site_IDs": ", ".join(sorted(related_sites)),
                "Max_Exceedance_Ratio": (
                    cmix_subset["Exceedance_Ratio"].max()
                    if not cmix_subset.empty
                    else np.nan
                ),
                "Failing_Scenarios": ", ".join(
                    sorted(
                        cmix_subset.loc[
                            cmix_subset["Exceedance_Flag"], "Flow_Scenario"
                        ].unique()
                    )
                )
                if not cmix_subset.empty
                else "",
            }
        )

    return pd.DataFrame(summary_rows)


# ---------------------------------------------------------------------------
# Output handling
# ---------------------------------------------------------------------------#

def _export_results(
    flux_details: pd.DataFrame,
    segment_flux: pd.DataFrame,
    cmix_results: pd.DataFrame,
    segment_summary: pd.DataFrame,
) -> None:
    """Write all Step 6 outputs to disk."""
    flux_details.to_csv(get_output_path("step6_flux_site_segment"), index=False, encoding="utf-8")
    segment_flux.to_csv(get_output_path("step6_flux_by_segment"), index=False, encoding="utf-8")
    cmix_results.to_csv(get_output_path("step6_cmix_results"), index=False, encoding="utf-8")
    segment_summary.to_csv(get_output_path("step6_segment_summary"), index=False, encoding="utf-8")

    # Maintain legacy export for backward compatibility until consumers migrate.
    flux_details.to_csv(get_output_path("step6_flux_results"), index=False, encoding="utf-8")


if __name__ == "__main__":
    run_step6()
