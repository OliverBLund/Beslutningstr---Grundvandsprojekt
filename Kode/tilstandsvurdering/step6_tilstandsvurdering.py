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
from rasterio.mask import mask
from shapely.geometry import mapping

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
STANDARD_CONCENTRATIONS = {
    # MERGED Level 1/2: Branche/Aktivitet + Substance overrides
    "activity_substance": {
        # Servicestationer / benzintanke
        "Servicestationer_Benzen": 8000.0,              # D3 Table 3 – Benzen, servicestationer (90% fraktil)
        "Benzin og olie, salg af_Benzen": 8000.0,       # Same (duplicate synonym)

        # Villaolietanke
        "Villaolietank_Olie C10-C25": 6000.0,           # D3 Table 4 – Olie, villaolietanke (90% fraktil)

        # Renserier (TCE)
        "Renserier_Trichlorethylen": 42000.0,           # D3 Table 6 – TCE generelt (renserier = "-")

        # PCE not modelstof → retained from your baseline as placeholder
        "Renserier_Tetrachlorethylen": 2500.0,          # Placeholder (not in Delprojekt modelstoffer)

        # Non-modelstoff example kept
        "Maskinindustri_Toluen": 1200.0,                # Placeholder
    },

    # Level 3: Losseplads + specific overrides
    "losseplads": {
        "Benzen": 17.0,                 # D3 Table 3 – Benzen, losseplads
        "Olie C10-C25": 2500.0,         # D3 Table 4 – Olie, losseplads
        "Trichlorethylen": 2.2,         # D3 Table 6 – TCE, losseplads
        "Phenol": 6.4,                  # D3 Table 8 – Phenol, losseplads
        "Arsen": 25.0,                  # D3 Table 16 – Arsen, losseplads
        "COD": 380000.0,                # D3 Table 17 – COD (landfill context)

        # Category fallbacks inside landfill context
        "BTXER": 3000.0,
        "PAH_FORBINDELSER": 2500.0,
        "UORGANISKE_FORBINDELSER": 1800.0,
        "PHENOLER": 1500.0,
        "KLOREREDE_OPLØSNINGSMIDLER": 2800.0,
        "PESTICIDER": 1000.0,
    },

    # Level 4: Specific compound defaults (worst-case)
    "compound": {
        "Olie C10-C25": 3000.0,               # D3 Table 4 – general
        "Benzen": 400.0,                     # D3 Table 3 – general
        "1,1,1-Trichlorethan": 100.0,        # D3 Table 5
        "Trichlorethylen": 42000.0,          # D3 Table 6
        "Chloroform": 100.0,                 # D3 Table 7 / text
        "Chlorbenzen": 100.0,                # D3 Table 12
        "Phenol": 1300.0,                    # D3 Table 8
        "4-Nonylphenol": 9.0,                # D3 Table 9
        "2,6-dichlorphenol": 10000.0,        # D3 Table 11
        "MTBE": 50000.0,                     # D3 Table 10
        "Fluoranthen": 30.0,                 # D3 Table 13
        "Mechlorprop": 1000.0,               # D3 Table 14
        "Atrazin": 12.0,                     # D3 Table 15
        "Arsen": 100.0,                      # D3 Table 16 – general
        "Cyanid": 3500.0,                    # D3 Table 18
        "COD": 380000.0,                     # D3 Table 17
    },

    # Level 5: Category scenarios based on modelstoffer
    # Each category may have multiple scenarios (one per modelstof)
    # All compounds in a group use these modelstof concentrations
    "category": {
        # BTEX / Oil (2 scenarios)
        "BTXER__via_Benzen": 400.0,                     # D3 Table 3 – Benzen general
        "BTXER__via_Olie C10-C25": 3000.0,              # D3 Table 4 – Olie C10-C25 general

        # Chlorinated solvents (4 scenarios)
        "KLOREREDE_OPLØSNINGSMIDLER__via_1,1,1-Trichlorethan": 100.0,     # D3 Table 5
        "KLOREREDE_OPLØSNINGSMIDLER__via_Trichlorethylen": 42000.0,       # D3 Table 6
        "KLOREREDE_OPLØSNINGSMIDLER__via_Chloroform": 100.0,              # D3 Table 7
        "KLOREREDE_OPLØSNINGSMIDLER__via_Chlorbenzen": 100.0,             # D3 Table 12

        # Chlorinated hydrocarbons (synonym category - same scenarios as KLOREREDE_OPLØSNINGSMIDLER)
        # NOTE: This category appears in Step 5 output due to categorization in refined_compound_analysis.py
        # It should ideally be merged with KLOREREDE_OPLØSNINGSMIDLER (see MONDAY_TODO_CATEGORIZATION.md)
        "KLOREDE_KULBRINTER__via_1,1,1-Trichlorethan": 100.0,     # D3 Table 5
        "KLOREDE_KULBRINTER__via_Trichlorethylen": 42000.0,       # D3 Table 6
        "KLOREDE_KULBRINTER__via_Chloroform": 100.0,              # D3 Table 7
        "KLOREDE_KULBRINTER__via_Chlorbenzen": 100.0,             # D3 Table 12

        # Polar compounds (2 scenarios)
        "POLARE_FORBINDELSER__via_MTBE": 50000.0,       # D3 Table 10
        "POLARE_FORBINDELSER__via_4-Nonylphenol": 9.0,  # D3 Table 9

        # Phenols (1 scenario)
        "PHENOLER__via_Phenol": 1300.0,                 # D3 Table 8

        # Chlorinated phenols (1 scenario)
        "KLOREREDE_PHENOLER__via_2,6-dichlorphenol": 10000.0,  # D3 Table 11

        # Pesticides (2 scenarios)
        "PESTICIDER__via_Mechlorprop": 1000.0,          # D3 Table 14
        "PESTICIDER__via_Atrazin": 12.0,                # D3 Table 15

        # PAH (1 scenario)
        "PAH_FORBINDELSER__via_Fluoranthen": 30.0,      # D3 Table 13

        # Inorganics (2 scenarios)
        "UORGANISKE_FORBINDELSER__via_Arsen": 100.0,    # D3 Table 16
        "UORGANISKE_FORBINDELSER__via_Cyanid": 3500.0,  # D3 Table 18

        # Categories without modelstof basis (kept for backward compatibility)
        "LOSSEPLADS": 1000.0,
        "ANDRE": 1000.0,
        "PFAS": 500.0,  # Not part of D3 modelstoffer
    },
}

# Map each category to its modelstof scenarios
# This defines which scenarios to generate for each compound group
CATEGORY_SCENARIOS = {
    "BTXER": ["Benzen", "Olie C10-C25"],
    "KLOREREDE_OPLØSNINGSMIDLER": ["1,1,1-Trichlorethan", "Trichlorethylen", "Chloroform", "Chlorbenzen"],
    "KLOREDE_KULBRINTER": ["1,1,1-Trichlorethan", "Trichlorethylen", "Chloroform", "Chlorbenzen"],  # Synonym
    "POLARE_FORBINDELSER": ["MTBE", "4-Nonylphenol"],
    "PHENOLER": ["Phenol"],
    "KLOREREDE_PHENOLER": ["2,6-dichlorphenol"],
    "PESTICIDER": ["Mechlorprop", "Atrazin"],
    "PAH_FORBINDELSER": ["Fluoranthen"],
    "UORGANISKE_FORBINDELSER": ["Arsen", "Cyanid"],
    # Categories without scenarios
    "LOSSEPLADS": [],
    "ANDRE": [],
    "PFAS": [],
}


# Flow statistics to import from the q-point shapefile.
FLOW_SCENARIO_COLUMNS = {
    "Average": "Mean",
    "Q90": "Q90",
    "Q95": "Q95",
}

# MKK reference values (µg/L) - Environmental Quality Standards (EQS) for freshwater.
# Alle værdier er AA-EQS (generelt kvalitetskrav) for ferskvand i µg/L.
# Kilder: BEK nr. 1022 af 25/08/2010 – Bilag 3 (EU-EQS) og Bilag 2 (nationale EQS).
#
# IMPORTANT: Per meeting decision - only use specific MKK for the 16 modelstoffer from Delprojekt 3.
# For other substances (non-modelstoffer), use category MKK values only.
# Substance-level entries take precedence over category-level entries.

# The 16 modelstoffer from Delprojekt 3 with specific MKK values
MODELSTOFFER = {
    "Olie C10-C25", "Benzen", "1,1,1-Trichlorethan", "Trichlorethylen",
    "Chloroform", "Chlorbenzen", "Phenol", "4-Nonylphenol", "2,6-dichlorphenol",
    "MTBE", "Fluoranthen", "Mechlorprop", "Atrazin", "Arsen", "Cyanid", "COD"
}

MKK_THRESHOLDS: Dict[str, float] = {
    # ============================================================================
    # MODELSTOFFER - The 16 modelstoffer from Delprojekt 3 (stof-specifikke MKK)
    # ============================================================================
    "Benzen": 10.0,                 # BEK 1022 Bilag 3 – Benzen: ferskvand 10
    "Olie C10-C25": None,           # Ingen EQS som fraktion (ikke et enkeltstof)
    "1,1,1-Trichlorethan": 21.0,    # BEK 1022 Bilag 2 – 1,1,1-trichlorethan: 21
    "Trichlorethylen": 10.0,        # BEK 1022 Bilag 3 – Trichlorethylen: 10
    "Chloroform": 2.5,              # BEK 1022 Bilag 3 – Trichlormethan (chloroform): 2.5
    "Chlorbenzen": None,            # Ikke opført i BEK 1022
    "Phenol": 7.7,                  # BEK 1022 Bilag 2 – Phenol: 7.7
    "4-Nonylphenol": 0.3,           # BEK 1022 Bilag 3 – Nonylphenol: 0.3
    "2,6-dichlorphenol": 3.4,       # BEK 1022 Bilag 2 – 2,6-dichlorphenol: 3.4
    "MTBE": 10.0,                   # BEK 1022 Bilag 2 – MTBE: 10
    "Fluoranthen": 0.1,             # BEK 1022 Bilag 3 – Fluoranthen: 0.1
    "Mechlorprop": 18.0,            # BEK 1022 Bilag 2 – mechlorprop-p: 18
    "Atrazin": 0.6,                 # BEK 1022 Bilag 3 – Atrazin: 0.6
    "Arsen": 4.3,                   # BEK 1022 Bilag 2 – Arsen (As): 4.3
    "Cyanid": 10.0,                 # Konservativ værdi (ikke i BEK 1022)
    "COD": 1000.0,                  # Konservativ værdi (indikator, ikke EQS-stof)

    # ============================================================================
    # KATEGORI-MKK - Afledt fra modelstoffer (laveste EQS i kategorien)
    # Alle ikke-modelstoffer bruger disse værdier
    # ============================================================================
    "BTXER": 10.0,                       # Fra Benzen (strammest i BTEX-gruppen)
    "PAH_FORBINDELSER": 0.1,             # Fra Fluoranthen
    "PHENOLER": 0.3,                     # Fra 4-Nonylphenol (strammest: 0.3 < 7.7)
    "KLOREREDE_PHENOLER": 3.4,           # Fra 2,6-dichlorphenol
    "POLARE_FORBINDELSER": 10.0,         # Fra MTBE
    "KLOREREDE_OPLØSNINGSMIDLER": 2.5,   # Fra Chloroform (strammest: 2.5 < 10 < 21)
    "KLOREDE_KULBRINTER": 2.5,           # Samme som KLOREREDE_OPLØSNINGSMIDLER
    "PESTICIDER": 0.6,                   # Fra Atrazin (strammest: 0.6 < 18)
    "UORGANISKE_FORBINDELSER": 4.3,      # Fra Arsen
    "PFAS": 0.0044,                      # BEK 796/2023 - PFAS_24 group EQS
    "LOSSEPLADS": 10.0,                  # Konservativ fallback
    "ANDRE": 10.0,                       # Konservativ fallback for uspecificerede
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

    enriched_results, negative_infiltration = _prepare_flux_inputs(
        step5_results, site_geometries, layer_mapping, river_segments
    )
    flux_details = _calculate_flux(enriched_results)
    segment_flux = _aggregate_flux_by_segment(flux_details)

    flow_scenarios = _load_flow_scenarios()
    cmix_results = _calculate_cmix(segment_flux, flow_scenarios)
    cmix_results = _apply_mkk_thresholds(cmix_results)
    segment_summary = _build_segment_summary(flux_details, segment_flux, cmix_results)

    _export_results(flux_details, segment_flux, cmix_results, segment_summary)
    analyze_and_visualize_step6(
        flux_details,
        segment_flux,
        cmix_results,
        segment_summary,
        negative_infiltration=negative_infiltration,
        site_geometries=site_geometries,
    )

    return {
        "site_flux": flux_details,
        "segment_flux": segment_flux,
        "cmix_results": cmix_results,
        "segment_summary": segment_summary,
        "negative_infiltration": negative_infiltration,
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

    # Use maximum flow per segment (downstream end, most conservative dilution)
    aggregated = (
        flow_points.groupby("ov_id")[list(FLOW_SCENARIO_COLUMNS.keys())]
        .max(numeric_only=True)
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
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Attach areas, modellag, infiltration, and river segment metadata.

    Returns:
        Tuple containing the filtered enrichment DataFrame and the rows that
        were dropped due to negative infiltration (for diagnostics/visualization).
    """
    enriched = step5_results.copy()
    negative_rows = pd.DataFrame(columns=enriched.columns)

    # Attach areas and centroids
    area_lookup = dict(zip(site_geometries["Lokalitet_"], site_geometries["Area_m2"]))
    centroid_lookup = dict(zip(site_geometries["Lokalitet_"], site_geometries["Centroid"]))
    geometry_lookup = dict(zip(site_geometries["Lokalitet_"], site_geometries["geometry"]))
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

    infiltration_stats = _calculate_infiltration(
        enriched, centroid_lookup, geometry_lookup
    )

    enriched["Infiltration_mm_per_year"] = infiltration_stats["Combined_Infiltration_mm_per_year"]
    enriched["Centroid_Infiltration_mm_per_year"] = infiltration_stats["Centroid_Infiltration_mm_per_year"]
    enriched["Polygon_Infiltration_mm_per_year"] = infiltration_stats["Polygon_Infiltration_mm_per_year"]
    enriched["Polygon_Infiltration_Min_mm_per_year"] = infiltration_stats["Polygon_Infiltration_Min_mm_per_year"]
    enriched["Polygon_Infiltration_Max_mm_per_year"] = infiltration_stats["Polygon_Infiltration_Max_mm_per_year"]
    enriched["Polygon_Infiltration_Pixel_Count"] = infiltration_stats["Polygon_Infiltration_Pixel_Count"]

    # Negative GVD means upward groundwater flow (discharge zones near gaining streams)
    # Surface contamination won't infiltrate downward in these areas
    negative_mask = enriched["Infiltration_mm_per_year"] < 0
    negative_count = negative_mask.sum()
    if negative_count > 0:
        # Capture statistics BEFORE removal
        initial_rows = len(enriched)
        initial_sites = enriched["Lokalitet_ID"].nunique()
        initial_gvfk = enriched["GVFK"].nunique()

        negative_rows = enriched.loc[negative_mask].copy()
        negative_rows["Sampled_Layers"] = negative_rows["DK-modellag"].apply(
            lambda text: ", ".join(_parse_dk_modellag(text)) if pd.notna(text) else ""
        )
        removed_sites = sorted(enriched.loc[negative_mask, "Lokalitet_ID"].unique())
        removed_gvfk = sorted(enriched.loc[negative_mask, "GVFK"].unique())

        # Apply filter
        enriched = enriched[~negative_mask].copy()

        # Capture statistics AFTER removal
        final_rows = len(enriched)
        final_sites = enriched["Lokalitet_ID"].nunique()
        final_gvfk = enriched["GVFK"].nunique()

        # Calculate sites/GVFK that were completely removed vs partially removed
        remaining_sites = set(enriched["Lokalitet_ID"].unique())
        remaining_gvfk = set(enriched["GVFK"].unique())
        completely_removed_sites = [s for s in removed_sites if s not in remaining_sites]
        completely_removed_gvfk = [g for g in removed_gvfk if g not in remaining_gvfk]

        print("\nINFO: Removing rows with negative infiltration (opstrømningszoner).")
        print(f"   BEFORE: {initial_rows} rows, {initial_sites} sites, {initial_gvfk} GVFK")
        print(f"   REMOVED: {negative_count} rows ({negative_count/initial_rows*100:.1f}%)")
        print(f"   AFTER: {final_rows} rows, {final_sites} sites, {final_gvfk} GVFK")
        print(f"\n   Sites with removed rows: {len(removed_sites)}")
        print(f"   Sites completely removed: {len(completely_removed_sites)} (all rows had negative infiltration)")
        print(f"   Sites partially affected: {len(removed_sites) - len(completely_removed_sites)} (some rows retained)")
        print(f"\n   GVFK with removed rows: {len(removed_gvfk)}")
        print(f"   GVFK completely removed: {len(completely_removed_gvfk)}")
        print(f"   GVFK partially affected: {len(removed_gvfk) - len(completely_removed_gvfk)}")
        print(f"\n   Example affected sites: {', '.join(removed_sites[:5])}"
              f"{' ...' if len(removed_sites) > 5 else ''}")
        print(f"   Example affected GVFK: {', '.join(removed_gvfk[:5])}"
              f"{' ...' if len(removed_gvfk) > 5 else ''}\n")

    # Filter out rows where infiltration data is missing
    if enriched["Infiltration_mm_per_year"].isna().any():
        missing_infiltration = enriched["Infiltration_mm_per_year"].isna().sum()
        missing_sites = enriched.loc[enriched["Infiltration_mm_per_year"].isna(), "Lokalitet_ID"].unique()
        print(f"\nWARNING: Missing infiltration data for {len(missing_sites)} site(s):")
        print(f"   Sites: {', '.join(sorted(missing_sites)[:10])}{' ...' if len(missing_sites) > 10 else ''}")
        print(f"   Affected rows: {missing_infiltration}")
        print(f"   Reason: Site polygon/centroid fall outside infiltration raster coverage.")
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

    if "Sampled_Layers" not in negative_rows.columns:
        negative_rows["Sampled_Layers"] = pd.Series(dtype=str)

    return enriched, negative_rows


def _calculate_infiltration(
    enriched: pd.DataFrame,
    centroid_lookup: Dict[str, Any],
    geometry_lookup: Dict[str, Any],
    source_crs = None,
) -> pd.DataFrame:
    """
    Sample infiltration rasters for each (Lokalitet_ID, modellag) pair.
    Returns a DataFrame with combined, polygon, and centroid metrics aligned with `enriched`.

    Args:
        source_crs: CRS of the input geometries (default: EPSG:25832 for Denmark)
    """
    if source_crs is None:
        source_crs = "EPSG:25832"  # Standard for Denmark

    cache: Dict[Tuple[str, str], Dict[str, float]] = {}

    records: List[Dict[str, float]] = []
    for _, row in enriched.iterrows():
        site_id = row["Lokalitet_ID"]
        modellag = row["DK-modellag"]
        key = (site_id, modellag)

        if key not in cache:
            centroid = centroid_lookup.get(site_id)
            if centroid is None:
                raise ValueError(f"No centroid found for site {site_id}")
            geometry = geometry_lookup.get(site_id)
            if geometry is None:
                raise ValueError(f"No geometry found for site {site_id}")

            layers = _parse_dk_modellag(modellag)
            if not layers:
                raise ValueError(f"Could not interpret modellag '{modellag}' for {site_id}")

            layer_results: List[Dict[str, float]] = []
            for layer in layers:
                try:
                    layer_stats = _sample_infiltration(layer, geometry, centroid, source_crs)
                    layer_results.append(layer_stats)
                except ValueError as exc:
                    print(f"\nWARNING: {exc}")
                    layer_results.append(
                        {
                            "combined": None,
                            "polygon_mean": None,
                            "polygon_min": None,
                            "polygon_max": None,
                            "polygon_pixel_count": 0,
                            "centroid": None,
                        }
                    )

            combined_values = [item["combined"] for item in layer_results if item["combined"] is not None]
            polygon_values = [item["polygon_mean"] for item in layer_results if item["polygon_mean"] is not None]
            centroid_values = [item["centroid"] for item in layer_results if item["centroid"] is not None]
            polygon_mins = [item["polygon_min"] for item in layer_results if item["polygon_min"] is not None]
            polygon_maxs = [item["polygon_max"] for item in layer_results if item["polygon_max"] is not None]
            pixel_counts = [item["polygon_pixel_count"] for item in layer_results if item["polygon_pixel_count"]]

            combined_mean = float(np.mean(combined_values)) if combined_values else None
            polygon_mean = float(np.mean(polygon_values)) if polygon_values else np.nan
            centroid_mean = float(np.mean(centroid_values)) if centroid_values else np.nan
            polygon_min = float(np.min(polygon_mins)) if polygon_mins else np.nan
            polygon_max = float(np.max(polygon_maxs)) if polygon_maxs else np.nan
            polygon_pixel_count = int(np.sum(pixel_counts)) if pixel_counts else 0

            cache[key] = {
                "Combined_Infiltration_mm_per_year": combined_mean,
                "Centroid_Infiltration_mm_per_year": centroid_mean,
                "Polygon_Infiltration_mm_per_year": polygon_mean,
                "Polygon_Infiltration_Min_mm_per_year": polygon_min,
                "Polygon_Infiltration_Max_mm_per_year": polygon_max,
                "Polygon_Infiltration_Pixel_Count": polygon_pixel_count,
            }

        records.append(cache[key])

    return pd.DataFrame(records, index=enriched.index)


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


def _sample_infiltration(layer: str, geometry, centroid, source_crs: str = "EPSG:25832") -> Dict[str, float]:
    """
    Sample the infiltration raster for a given layer using the full site polygon.
    Returns both polygon-level statistics and centroid fallback value.

    Note: Assumes rasters and geometries are in the same CRS (EPSG:25832 for Denmark).
    """
    if layer.startswith("lag"):
        layer = "lay12"

    raster_path = Path(GVD_RASTER_DIR) / f"DKM_gvd_{layer}.tif"
    if not raster_path.exists():
        raise FileNotFoundError(f"Infiltration raster not found: {raster_path}")

    polygon_mean = None
    polygon_min = None
    polygon_max = None
    pixel_count = 0

    with rasterio.open(raster_path) as src:

        try:
            data, _ = mask(src, [mapping(geometry)], crop=True)
            band = data[0]
            valid = band[(band != src.nodata) & (~np.isnan(band))]
            if valid.size > 0:
                polygon_mean = float(valid.mean())
                polygon_min = float(valid.min())
                polygon_max = float(valid.max())
                pixel_count = int(valid.size)
        except ValueError:
            pass

        x, y = centroid.x, centroid.y
        centroid_value = next(src.sample([(x, y)]), [np.nan])[0]
        if centroid_value is None or np.isnan(centroid_value) or centroid_value == src.nodata:
            # Enhanced error message with diagnostics
            geom_bounds = geometry.bounds
            raise ValueError(
                f"Infiltration raster {raster_path.name} returned no data for site.\n"
                f"   Centroid: ({x:.1f}, {y:.1f})\n"
                f"   Geometry bounds: ({geom_bounds[0]:.1f}, {geom_bounds[1]:.1f}, {geom_bounds[2]:.1f}, {geom_bounds[3]:.1f})\n"
                f"   Raster bounds: {src.bounds}\n"
                f"   Sampled value: {centroid_value} (nodata={src.nodata})\n"
                f"   Possible causes: Site outside raster coverage, or at nodata location (coast/border)"
            )
        centroid_value = float(centroid_value)

    combined_value = polygon_mean if polygon_mean is not None else centroid_value

    return {
        "combined": combined_value,
        "polygon_mean": polygon_mean,
        "polygon_min": polygon_min,
        "polygon_max": polygon_max,
        "polygon_pixel_count": pixel_count,
        "centroid": centroid_value,
    }


# ---------------------------------------------------------------------------
# Flux calculation and aggregation
# ---------------------------------------------------------------------------#

def _lookup_standard_concentration(row: pd.Series, log_matches: bool = False) -> float:
    """
    Look up standard concentration with 4-level hierarchy.

    Priority:
    1. Industry/Activity + Substance (most specific, merged branche/aktivitet)
    2. Losseplads + Substance/Category (if applicable)
    3. Compound name
    4. Category (fallback)

    Logs when multiple industries/activities are tried (helps identify missing overrides).
    """

    substance = row['Qualifying_Substance']
    category = row['Qualifying_Category']
    branches = row.get('Lokalitetensbranche', '').split(';') if pd.notna(row.get('Lokalitetensbranche')) else []
    activities = row.get('Lokalitetensaktivitet', '').split(';') if pd.notna(row.get('Lokalitetensaktivitet')) else []

    # Clean up branches/activities (strip whitespace)
    branches = [b.strip() for b in branches if b.strip()]
    activities = [a.strip() for a in activities if a.strip()]

    # Combine branches and activities into a single list for Level 1 lookup
    all_industries = branches + activities
    tried_multiple = len(all_industries) > 1

    # Level 1: Try Industry/Activity + Substance (merged branche and aktivitet)
    for i, industry in enumerate(all_industries):
        key = f"{industry}_{substance}"
        if key in STANDARD_CONCENTRATIONS['activity_substance']:
            if log_matches or (tried_multiple and i == 0):
                print(f"  [OK] Concentration match (Industry/Activity): '{industry}' + '{substance}' -> {STANDARD_CONCENTRATIONS['activity_substance'][key]} ug/L")
                if tried_multiple:
                    print(f"    Note: Site has multiple industries/activities: {all_industries}")
            return STANDARD_CONCENTRATIONS['activity_substance'][key]

    # Level 2: Losseplads override (if applicable)
    is_losseplads = category == "LOSSEPLADS" or "Landfill Override:" in substance
    if is_losseplads:
        # Extract actual substance/category from "Landfill Override: BTXER" format
        if "Landfill Override:" in substance:
            actual_substance = substance.replace("Landfill Override:", "").strip()
        else:
            actual_substance = substance

        if actual_substance in STANDARD_CONCENTRATIONS['losseplads']:
            if log_matches:
                print(f"  [OK] Concentration match (Losseplads): '{actual_substance}' -> {STANDARD_CONCENTRATIONS['losseplads'][actual_substance]} ug/L")
            return STANDARD_CONCENTRATIONS['losseplads'][actual_substance]

    # Level 3: Direct compound lookup
    if substance in STANDARD_CONCENTRATIONS['compound']:
        return STANDARD_CONCENTRATIONS['compound'][substance]

    # Level 4: Category fallback
    if category in STANDARD_CONCENTRATIONS['category']:
        return STANDARD_CONCENTRATIONS['category'][category]

    # No match found - raise error with helpful message
    raise ValueError(
        f"No concentration defined for:\n"
        f"  Substance: '{substance}'\n"
        f"  Category: '{category}'\n"
        f"  Industries/Activities: {all_industries}"
    )


def _lookup_concentration_for_scenario(
    scenario_modelstof: str | None,
    category: str,
    original_substance: str | None,
    row: pd.Series
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
        if key in STANDARD_CONCENTRATIONS['activity_substance']:
            return STANDARD_CONCENTRATIONS['activity_substance'][key]

    # Level 2: Losseplads context
    if is_losseplads:
        # Try exact substance match
        if lookup_substance and lookup_substance in STANDARD_CONCENTRATIONS['losseplads']:
            return STANDARD_CONCENTRATIONS['losseplads'][lookup_substance]
        # Try category match
        if category in STANDARD_CONCENTRATIONS['losseplads']:
            return STANDARD_CONCENTRATIONS['losseplads'][category]

    # Level 3: Direct compound lookup (for modelstoffer)
    if lookup_substance and lookup_substance in STANDARD_CONCENTRATIONS['compound']:
        return STANDARD_CONCENTRATIONS['compound'][lookup_substance]

    # Level 4: Category scenario
    if scenario_modelstof:
        scenario_key = f"{category}__via_{scenario_modelstof}"
        if scenario_key in STANDARD_CONCENTRATIONS['category']:
            return STANDARD_CONCENTRATIONS['category'][scenario_key]

    # Level 5: Category fallback (for categories without scenarios)
    if category in STANDARD_CONCENTRATIONS['category']:
        return STANDARD_CONCENTRATIONS['category'][category]

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


def _calculate_flux(enriched: pd.DataFrame) -> pd.DataFrame:
    """
    Compute pollution flux (J = A · C · I) with scenario-based aggregation.

    Key changes:
    - All compounds in a category use modelstof concentrations (scenarios)
    - One flux value per scenario per site (NOT per individual substance)
    - Categories with multiple modelstoffer generate multiple scenarios

    Example: Site with 4 different BTXER compounds generates 2 flux rows:
      - BTXER__via_Benzen (400 µg/L)
      - BTXER__via_Olie C10-C25 (3000 µg/L)
    """
    print("\nCalculating flux using scenario-based approach...")
    print("  (Aggregating substances by category + scenario at site level)")

    # Group by site + GVFK + category to aggregate substances
    # This is the key change: we calculate ONE flux per scenario, not per substance
    grouping_cols = ["Lokalitet_ID", "GVFK", "Qualifying_Category",
                     "Area_m2", "Infiltration_mm_per_year",
                     "Nearest_River_FID", "Nearest_River_ov_id", "River_Segment_Name",
                     "River_Segment_Length_m", "River_Segment_GVFK", "Distance_to_River_m",
                     "River_Segment_Count"]

    # Get unique site-category combinations
    site_categories = enriched.groupby(grouping_cols, dropna=False).first().reset_index()

    flux_rows = []

    for _, site_cat in site_categories.iterrows():
        category = site_cat["Qualifying_Category"]

        # Get scenarios for this category
        scenarios = CATEGORY_SCENARIOS.get(category, [])

        if not scenarios:
            # Category has no scenarios (LOSSEPLADS, ANDRE, PFAS)
            # Use old approach: pick first substance as representative
            site_substances = enriched[
                (enriched["Lokalitet_ID"] == site_cat["Lokalitet_ID"]) &
                (enriched["GVFK"] == site_cat["GVFK"]) &
                (enriched["Qualifying_Category"] == category)
            ]
            first_substance = site_substances.iloc[0]["Qualifying_Substance"]

            # Lookup concentration using old method
            conc = _lookup_concentration_for_scenario(
                scenario_modelstof=None,
                category=category,
                original_substance=first_substance,
                row=site_cat
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
                    row=site_cat
                )

                # Create flux row for this scenario
                flux_row = site_cat.copy()
                flux_row["Qualifying_Substance"] = f"{category}__via_{modelstof}"
                flux_row["Standard_Concentration_ug_L"] = conc
                flux_row = _compute_flux_from_concentration(flux_row)
                flux_rows.append(flux_row)

    df = pd.DataFrame(flux_rows)

    print(f"  Input rows (substances): {len(enriched)}")
    print(f"  Output rows (scenarios): {len(df)}")
    print(f"  Concentration range: {df['Standard_Concentration_ug_L'].min():.1f} - {df['Standard_Concentration_ug_L'].max():.1f} µg/L")

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

        # Strip "Landfill Override:" prefix if present (MKK is the same regardless of source)
        if substance and "Landfill Override:" in substance:
            substance = substance.replace("Landfill Override:", "").strip()

        # Also strip "Branch/Activity:" prefix if present
        if substance and "Branch/Activity:" in substance:
            substance = substance.replace("Branch/Activity:", "").strip()

        # Per meeting decision: Only use substance-specific MKK for the 16 modelstoffer
        # For non-modelstoffer, skip to category MKK
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
