"""Data loading utilities for groundwater analysis workflows.

This module centralizes all data loading functions to reduce code duplication
and improve maintainability across workflow steps.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict

import geopandas as gpd
import pandas as pd

from config import (
    FLOW_SCENARIO_COLUMNS,
    GVFK_LAYER_MAPPING_PATH,
    RIVER_FLOW_POINTS_PATH,
    RIVERS_PATH,
    get_output_path,
    COLUMN_MAPPINGS,
)


def load_step5_results() -> pd.DataFrame:
    """Load Step 5 output and validate required columns.

    Returns:
        DataFrame with site-GVFK-substance combinations

    Raises:
        ValueError: If file is empty or missing required columns
    """
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
    site_id_col = COLUMN_MAPPINGS['contamination_shp']['site_id']
    sites = gpd.read_file(get_output_path("step3_v1v2_sites"))
    if sites.empty:
        raise ValueError("Step 3 geometries are empty – cannot derive site areas.")

    dissolved = sites.dissolve(by=site_id_col, as_index=False)
    dissolved["Area_m2"] = dissolved.geometry.area
    dissolved["Centroid"] = dissolved.geometry.centroid

    return dissolved[[site_id_col, "Area_m2", "Centroid", "geometry"]]


def load_gvfk_layer_mapping() -> pd.DataFrame:
    """Load GVFK to DK-model layer mapping.

    Returns:
        DataFrame with GVForekom and DK-modellag columns

    Raises:
        FileNotFoundError: If mapping file doesn't exist
    """
    if not GVFK_LAYER_MAPPING_PATH.exists():
        raise FileNotFoundError(
            f"GVFK layer mapping not found: {GVFK_LAYER_MAPPING_PATH}\n"
            "This file is required for infiltration calculations."
        )

    # Try multiple encodings (Danish files often use Windows-1252 or latin1)
    for encoding in ['utf-8', 'windows-1252', 'latin1', 'iso-8859-1']:
        try:
            df = pd.read_csv(GVFK_LAYER_MAPPING_PATH, encoding=encoding, sep=';')
            break
        except UnicodeDecodeError:
            continue
    else:
        raise ValueError(f"Could not decode {GVFK_LAYER_MAPPING_PATH} with any common encoding")

    gvfk_col = COLUMN_MAPPINGS['gvfk_layer_mapping']['gvfk_id']
    layer_col = COLUMN_MAPPINGS['gvfk_layer_mapping']['model_layer']
    required_columns = [gvfk_col, layer_col]
    missing = [col for col in required_columns if col not in df.columns]
    if missing:
        raise ValueError(f"Layer mapping missing columns: {', '.join(missing)}")

    return df


def load_river_segments() -> gpd.GeoDataFrame:
    """Load river network with GVFK contact.

    Returns:
        GeoDataFrame with river segments and metadata

    Raises:
        FileNotFoundError: If river shapefile doesn't exist
    """
    if not RIVERS_PATH.exists():
        raise FileNotFoundError(f"River network not found: {RIVERS_PATH}")

    rivers = gpd.read_file(RIVERS_PATH, encoding='utf-8')
    if rivers.empty:
        raise ValueError("River segment file is empty – cannot continue.")

    # Create River_FID from index (consistent with original workflow)
    rivers = rivers.reset_index().rename(columns={"index": "River_FID"})

    river_id_col = COLUMN_MAPPINGS['rivers']['river_id']
    river_name_col = COLUMN_MAPPINGS['rivers']['river_name']
    length_col = COLUMN_MAPPINGS['rivers']['length']
    gvfk_col = COLUMN_MAPPINGS['rivers']['gvfk_id']
    required_columns = [river_id_col, river_name_col, length_col, gvfk_col]
    missing = [col for col in required_columns if col not in rivers.columns]
    if missing:
        raise ValueError(f"River shapefile missing columns: {', '.join(missing)}")

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

    qpoints = gpd.read_file(RIVER_FLOW_POINTS_PATH)

    river_id_col = COLUMN_MAPPINGS['flow_points']['river_id']

    # Check that flow columns exist
    missing = [col for col in FLOW_SCENARIO_COLUMNS if col not in qpoints.columns]
    if missing:
        raise ValueError(f"Q-point data missing flow columns: {', '.join(missing)}")

    # Melt to long format: one row per ov_id × scenario
    id_vars = [river_id_col]
    value_vars = list(FLOW_SCENARIO_COLUMNS.keys())

    flow_long = qpoints[id_vars + value_vars].melt(
        id_vars=id_vars,
        value_vars=value_vars,
        var_name="Scenario_raw",
        value_name="Flow_m3_s"
    )

    # Rename scenarios
    flow_long["Scenario"] = flow_long["Scenario_raw"].map(FLOW_SCENARIO_COLUMNS)
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
