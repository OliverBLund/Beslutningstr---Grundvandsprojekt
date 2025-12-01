"""Data loading utilities for groundwater analysis workflows.

This module centralizes all data loading functions to reduce code duplication
and improve maintainability across workflow steps.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Iterable, Sequence

import geopandas as gpd
import pandas as pd

from config import (
    COLUMN_MAPPINGS,
    FLOW_SCENARIO_COLUMNS,
    GRUNDVAND_GDB_PATH,
    GRUNDVAND_LAYER_NAME,
    RIVER_FLOW_POINTS_LAYER,
    RIVER_FLOW_POINTS_PATH,
    RIVERS_LAYER_NAME,
    RIVERS_PATH,
    WORKFLOW_SETTINGS,
    get_output_path,
)


def load_step5_results() -> pd.DataFrame:
    """Load Step 5 output and validate required columns.

    Returns:
        DataFrame with site-GVFK-substance combinations

    Raises:
        ValueError: If file is empty or missing required columns
    """
    step5_path = get_output_path("step5_compound_detailed_combinations")
    df = pd.read_csv(step5_path, encoding="utf-8")

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
        raise ValueError(f"Step 5 output missing columns: {', '.join(missing_columns)}")

    if df["Nearest_River_FID"].isna().any():
        raise ValueError("One or more rows missing 'Nearest_River_FID' – rerun Step 4/5.")

    return df


def load_site_geometries() -> gpd.GeoDataFrame:
    """Load Step 3 site geometries and compute areas.

    Returns:
        GeoDataFrame with dissolved site polygons, areas, and centroids

    Raises:
        ValueError: If geometries are empty
    """
    site_id_col = COLUMN_MAPPINGS["contamination_shp"]["site_id"]
    sites = gpd.read_file(get_output_path("step3_v1v2_sites"))
    if sites.empty:
        raise ValueError("Step 3 geometries are empty – cannot derive site areas.")

    dissolved = sites.dissolve(by=site_id_col, as_index=False)
    dissolved["Area_m2"] = dissolved.geometry.area
    dissolved["Centroid"] = dissolved.geometry.centroid

    return dissolved[[site_id_col, "Area_m2", "Centroid", "geometry"]]


def load_gvfk_layer_mapping(columns: Sequence[str] | None = None) -> gpd.GeoDataFrame:
    """Load GVFK metadata (including raster layer codes) from the Grunddata geodatabase.

    Args:
        columns: Optional list of columns to return. If omitted, the full GeoDataFrame
            is returned.

    Returns:
        GeoDataFrame with at least GVFK identifiers and dkmlag assignments.

    Raises:
        FileNotFoundError: If the Grunddata geodatabase is missing.
        ValueError: If required columns are missing from the dataset.
    """
    if not GRUNDVAND_GDB_PATH.exists():
        raise FileNotFoundError(
            f"Grunddata geodatabase not found: {GRUNDVAND_GDB_PATH}\n"
            "This dataset is required for infiltration calculations."
        )

    gvfk_gdf = gpd.read_file(GRUNDVAND_GDB_PATH, layer=GRUNDVAND_LAYER_NAME)

    gvfk_col = COLUMN_MAPPINGS["gvfk_layer_mapping"]["gvfk_id"]
    layer_col = COLUMN_MAPPINGS["gvfk_layer_mapping"]["model_layer"]

    required: Iterable[str]
    if columns:
        required = set(columns) | {gvfk_col, layer_col}
    else:
        required = {gvfk_col, layer_col}

    missing = [col for col in required if col not in gvfk_gdf.columns]
    if missing:
        raise ValueError(
            f"Grunddata layer '{GRUNDVAND_LAYER_NAME}' missing columns: {', '.join(missing)}"
        )

    if columns:
        unique_cols = list(dict.fromkeys(columns))  # Preserve order while removing duplicates
        return gvfk_gdf[unique_cols].copy()

    return gvfk_gdf


def load_river_segments() -> gpd.GeoDataFrame:
    """Load river network with GVFK contact.

    Returns:
        GeoDataFrame with river segments and metadata

    Raises:
        FileNotFoundError: If river shapefile doesn't exist
    """
    if not RIVERS_PATH.exists():
        raise FileNotFoundError(f"River network not found: {RIVERS_PATH}")

    rivers = gpd.read_file(RIVERS_PATH, layer=RIVERS_LAYER_NAME)
    if rivers.empty:
        raise ValueError("River segment file is empty – cannot continue.")

    # Create River_FID from index (consistent with original workflow)
    rivers = rivers.reset_index().rename(columns={"index": "River_FID"})

    river_id_col = COLUMN_MAPPINGS["rivers"]["river_id"]
    river_name_col = COLUMN_MAPPINGS["rivers"]["river_name"]
    length_col = COLUMN_MAPPINGS["rivers"]["length"]
    gvfk_col = COLUMN_MAPPINGS["rivers"]["gvfk_id"]
    required_columns = [river_id_col, river_name_col, length_col, gvfk_col]
    missing = [col for col in required_columns if col not in rivers.columns]
    if missing:
        raise ValueError(f"River shapefile missing columns: {', '.join(missing)}")

    rivers[gvfk_col] = rivers[gvfk_col].astype(str).str.strip()
    contact_col = COLUMN_MAPPINGS["rivers"]["contact"]
    valid_mask = rivers[gvfk_col] != ""

    # Filter for river-GVFK contact:
    # - New Grunddata format: GVFK presence indicates contact
    # - Legacy format: Explicit 'Kontakt' column (if present, use it for compatibility)
    if contact_col in rivers.columns:
        contact_value = WORKFLOW_SETTINGS["contact_filter_value"]
        rivers = rivers[(rivers[contact_col] == contact_value) & valid_mask]
    else:
        # New Grunddata format: GVFK presence IS the contact indicator
        rivers = rivers[valid_mask]

    return rivers


def load_flow_scenarios() -> pd.DataFrame:
    """Load Q-point discharge data and prepare flow scenarios.

    Returns:
        DataFrame with ov_id, Scenario, and Flow_m3_s columns

    Raises:
        FileNotFoundError: If Q-point shapefile doesn't exist
    """
    if not RIVER_FLOW_POINTS_PATH.exists():
        raise FileNotFoundError(f"Flow data not found: {RIVER_FLOW_POINTS_PATH}")

    qpoints = gpd.read_file(RIVER_FLOW_POINTS_PATH, layer=RIVER_FLOW_POINTS_LAYER)

    river_id_col = COLUMN_MAPPINGS["flow_points"]["river_id"]

    # Determine which flow columns are available
    available = [col for col in FLOW_SCENARIO_COLUMNS if col in qpoints.columns]
    missing = [col for col in FLOW_SCENARIO_COLUMNS if col not in qpoints.columns]
    if not available:
        raise ValueError(
            "Q-point data missing all configured flow columns "
            f"({', '.join(FLOW_SCENARIO_COLUMNS.keys())})"
        )
    if missing:
        print(
            "Warning: Q-point data missing columns: "
            + ", ".join(missing)
            + ". Skipping those scenarios."
        )

    scenario_map = {col: FLOW_SCENARIO_COLUMNS[col] for col in available}

    # Melt to long format: one row per ov_id × scenario
    id_vars = [river_id_col]
    value_vars = list(scenario_map.keys())

    flow_long = qpoints[id_vars + value_vars].melt(
        id_vars=id_vars,
        value_vars=value_vars,
        var_name="Scenario_raw",
        value_name="Flow_m3_s",
    )

    # Rename scenarios
    flow_long["Scenario"] = flow_long["Scenario_raw"].map(scenario_map)
    flow_long = flow_long.drop(columns=["Scenario_raw"])

    # Take maximum flow per segment (conservative approach)
    flow_max = (
        flow_long.groupby([river_id_col, "Scenario"], dropna=False)["Flow_m3_s"]
        .max()
        .reset_index()
    )

    return flow_max


__all__ = [
    "load_step5_results",
    "load_site_geometries",
    "load_gvfk_layer_mapping",
    "load_river_segments",
    "load_flow_scenarios",
]
