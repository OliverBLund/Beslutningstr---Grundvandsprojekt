"""
Step 5 Risk Assessment - Utility Functions
==========================================

Supporting utilities for Step 5 risk assessment including categorization,
GVFK handling, and file operations.
"""

from __future__ import annotations

from pathlib import Path
import sys

import pandas as pd
import geopandas as gpd

if __package__ is None or __package__ == "":
    sys.path.append(str(Path(__file__).resolve().parents[1]))

from config import (
    GRUNDVAND_LAYER_NAME,
    GRUNDVAND_PATH,
    WORKFLOW_SETTINGS,
    get_output_path,
)
from risikovurdering.compound_categories import (
    DEFAULT_DISTANCE,
    categorize_substance,
    get_category_distance,
)

# Global variable to track keyword statistics
_KEYWORD_STATS = {"branch": {}, "activity": {}, "total_checks": 0}


def categorize_contamination_substance(substance_text: str):
    """Categorise a contamination substance using keyword matching."""
    if pd.isna(substance_text) or not isinstance(substance_text, str):
        return "ANDRE", DEFAULT_DISTANCE

    category, distance = categorize_substance(substance_text)
    if pd.isna(distance) or distance is None:
        distance = get_category_distance(category)

    return category, float(distance)


def categorize_by_branch_activity(branch_text, activity_text):
    """
    Categorize sites by branch/activity data when no substance data is available.
    Currently handles LOSSEPLADS category identification.

    Args:
        branch_text (str): Branch data
        activity_text (str): Activity data

    Returns:
        tuple: (category_name, distance_m) or ('ANDRE', default_distance)
    """
    global _KEYWORD_STATS
    _KEYWORD_STATS["total_checks"] += 1

    def contains_landfill_terms(text):
        if pd.isna(text):
            return False, None
        text_lower = str(text).lower()
        landfill_keywords = [
            "losseplads",
            "affald",
            "depon",
            "fyldplads",
            "skraldeplads",
        ]

        # Check each keyword and return which one matched
        for keyword in landfill_keywords:
            if keyword in text_lower:
                return True, keyword
        return False, None

    # Check branch and activity data
    branch_match, branch_keyword = contains_landfill_terms(branch_text)
    activity_match, activity_keyword = contains_landfill_terms(activity_text)

    # Track statistics
    if branch_match:
        _KEYWORD_STATS["branch"][branch_keyword] = (
            _KEYWORD_STATS["branch"].get(branch_keyword, 0) + 1
        )
    if activity_match:
        _KEYWORD_STATS["activity"][activity_keyword] = (
            _KEYWORD_STATS["activity"].get(activity_keyword, 0) + 1
        )

    if branch_match or activity_match:
        return "LOSSEPLADS", get_category_distance("LOSSEPLADS")

    # Default to ANDRE category for non-landfill branch-only sites
    return "ANDRE", DEFAULT_DISTANCE


def get_keyword_stats():
    """Return current keyword matching statistics."""
    return _KEYWORD_STATS.copy()


def _extract_unique_gvfk_names(df):
    """
    Extract all unique GVFK names from a dataframe.
    Works with 'GVFK' column from lokalitet-GVFK combinations.

    Returns:
        set: Unique GVFK names
    """
    gvfk_names = set()

    # Extract from GVFK column (each row is a lokalitet-GVFK combination)
    if "GVFK" in df.columns:
        for gvfk in df["GVFK"].dropna():
            if str(gvfk) != "nan" and gvfk:
                gvfk_names.add(str(gvfk).strip())

    return gvfk_names


def create_gvfk_shapefile(high_risk_combinations, output_key):
    """Create shapefile of high-risk GVFK polygons from lokalitet-GVFK combinations."""
    try:
        grundvand_gdf = gpd.read_file(GRUNDVAND_PATH, layer=GRUNDVAND_LAYER_NAME)

        # Get high-risk GVFK names from combinations
        high_risk_gvfk_names = _extract_unique_gvfk_names(high_risk_combinations)

        # Filter GVFK polygons
        id_col = "Navn" if "Navn" in grundvand_gdf.columns else grundvand_gdf.columns[0]

        high_risk_gvfk_polygons = grundvand_gdf[
            grundvand_gdf[id_col].isin(high_risk_gvfk_names)
        ].copy()

        if not high_risk_gvfk_polygons.empty:
            output_path = get_output_path(output_key)
            high_risk_gvfk_polygons.to_file(output_path, encoding="utf-8")
            print(
                f"  Created shapefile: {output_key} ({len(high_risk_gvfk_polygons)} GVFKs)"
            )

    except Exception as e:
        print(f"  Warning: Could not create shapefile {output_key}: {e}")


def separate_sites_by_substance_data(distance_results):
    """
    Separate sites into those with and without qualifying data.
    Sites qualify if they have either:
    1. Substance data, OR
    2. Landfill-related branch/activity data (for LOSSEPLADS category)

    Args:
        distance_results (DataFrame): All sites from Step 4

    Returns:
        tuple: (sites_with_qualifying_data, sites_without_qualifying_data)
    """
    # Check which sites have substance data
    has_substances = (
        distance_results["Lokalitetensstoffer"].notna()
        & (distance_results["Lokalitetensstoffer"].astype(str).str.strip() != "")
        & (distance_results["Lokalitetensstoffer"].astype(str) != "nan")
    )

    # Check which sites have landfill-related branch/activity data
    def contains_landfill_terms(text):
        if pd.isna(text):
            return False
        text_lower = str(text).lower()
        landfill_keywords = ["losseplads", "affald", "deponi", "fyld", "skraldeplads"]
        return any(keyword in text_lower for keyword in landfill_keywords)

    has_landfill_branch = distance_results["Lokalitetensbranche"].apply(
        contains_landfill_terms
    )
    has_landfill_activity = distance_results["Lokalitetensaktivitet"].apply(
        contains_landfill_terms
    )
    has_landfill_data = has_landfill_branch | has_landfill_activity

    # Sites qualify if they have substances OR landfill data
    has_qualifying_data = has_substances | has_landfill_data

    sites_with_qualifying_data = distance_results[has_qualifying_data].copy()
    sites_without_qualifying_data = distance_results[~has_qualifying_data].copy()

    # Diagnostic output
    total_sites = len(distance_results)
    qualifying_count = len(sites_with_qualifying_data)
    non_qualifying_count = len(sites_without_qualifying_data)
    substance_only = (has_substances & ~has_landfill_data).sum()
    landfill_only = (~has_substances & has_landfill_data).sum()
    both = (has_substances & has_landfill_data).sum()

    # Additional diagnostics for parked sites
    has_branch_text = (
        distance_results["Lokalitetensbranche"].fillna("").astype(str).str.strip() != ""
    )
    has_activity_text = (
        distance_results["Lokalitetensaktivitet"].fillna("").astype(str).str.strip()
        != ""
    )
    has_any_text = has_branch_text | has_activity_text
    parked_with_text = ((~has_qualifying_data) & has_any_text).sum()
    parked_without_text = ((~has_qualifying_data) & ~has_any_text).sum()

    print("STEP 5 QUALIFICATION CHECK")
    print("=" * 35)
    print(f"Total sites received from Step 4: {total_sites:,}")
    if total_sites > 0:
        print(
            f"  -> Qualifying (substance data or landfill keywords): {qualifying_count:,} ({qualifying_count / total_sites * 100:.1f}%)"
        )
        print(
            f"  -> Parked (no qualifying data): {non_qualifying_count:,} ({non_qualifying_count / total_sites * 100:.1f}%)"
        )
    else:
        print(
            f"  -> Qualifying (substance data or landfill keywords): {qualifying_count}"
        )
        print(f"  -> Parked (no qualifying data): {non_qualifying_count}")
    print("Qualifying breakdown:")
    print(f"  Substance-only sites: {substance_only:,}")
    print(f"  Landfill-only sites: {landfill_only:,}")
    print(f"  Both substance+landfill: {both:,}")
    print("Parked (non-qualifying) breakdown:")
    print(
        f"  With branch/activity text but no qualifying keywords: {parked_with_text:,}"
    )
    print(f"  Without any branch/activity text: {parked_without_text:,}")

    return sites_with_qualifying_data, sites_without_qualifying_data
