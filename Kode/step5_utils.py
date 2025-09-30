"""
Step 5 Risk Assessment - Utility Functions
==========================================

Supporting utilities for Step 5 risk assessment including categorization,
GVFK handling, and file operations.
"""

import pandas as pd
import geopandas as gpd
import os
from config import get_output_path, GRUNDVAND_PATH, WORKFLOW_SETTINGS

# Global cache for categorization data
_CATEGORIZATION_CACHE = None
_DEFAULT_OTHER_DISTANCE = 500

# Global variable to track keyword statistics
_KEYWORD_STATS = {'branch': {}, 'activity': {}, 'total_checks': 0}


def _load_categorization_from_excel():
    """Load compound categorization data from Excel file."""
    global _CATEGORIZATION_CACHE

    if _CATEGORIZATION_CACHE is not None:
        return _CATEGORIZATION_CACHE

    # Path to Excel file
    excel_path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)),
        "compound_categorization_review.xlsx"
    )

    # Load summary sheet for category distances
    summary_df = pd.read_excel(excel_path, sheet_name='Summary')

    # Build category → distance mapping
    category_distances = {}
    for _, row in summary_df.iterrows():
        category = row['Category']
        distance = row['Distance_m']
        if distance != 'TBD' and pd.notna(distance):
            category_distances[category] = float(distance)
        else:
            category_distances[category] = _DEFAULT_OTHER_DISTANCE

    # Load individual sheets for substance → category mapping AND compound-specific distances
    substance_to_category = {}
    substance_to_distance = {}
    xl_file = pd.ExcelFile(excel_path)
    category_sheets = [sheet for sheet in xl_file.sheet_names
                      if sheet not in ['Summary', 'Raw_Data']]

    for sheet_name in category_sheets:
        sheet_df = pd.read_excel(excel_path, sheet_name=sheet_name)

        if 'Substance' not in sheet_df.columns:
            raise ValueError(f"Sheet '{sheet_name}' missing required 'Substance' column")

        category = sheet_name.replace('_substances', '').upper()

        for _, row in sheet_df.iterrows():
            substance = row.get('Substance')
            distance = row.get('Distance_m')

            if pd.notna(substance):
                substance_key = str(substance).lower().strip()
                substance_to_category[substance_key] = category

                # Store compound-specific distance if available
                if pd.notna(distance) and distance != 'TBD':
                    substance_to_distance[substance_key] = float(distance)

    _CATEGORIZATION_CACHE = {
        'category_distances': category_distances,
        'substance_to_category': substance_to_category,
        'substance_to_distance': substance_to_distance
    }

    print(f"Loaded categorization: {len(category_distances)} categories, {len(substance_to_category)} substances, {len(substance_to_distance)} compound-specific distances")
    return _CATEGORIZATION_CACHE


def categorize_contamination_substance(substance_text):
    """
    Categorize a contamination substance using Excel-based categorization.

    Args:
        substance_text (str): The contamination substance text

    Returns:
        tuple: (category_name, distance_m)
    """
    if pd.isna(substance_text) or not isinstance(substance_text, str):
        return 'ANDRE', _DEFAULT_OTHER_DISTANCE

    # Load categorization data
    cat_data = _load_categorization_from_excel()
    substance_lower = substance_text.lower().strip()

    # Check for exact match first
    category = cat_data['substance_to_category'].get(substance_lower)

    if category:
        # Check for compound-specific distance first
        specific_distance = cat_data['substance_to_distance'].get(substance_lower)
        if specific_distance is not None:
            return category, specific_distance
        # Fall back to category default
        distance = cat_data['category_distances'].get(category, _DEFAULT_OTHER_DISTANCE)
        return category, distance

    # Check if substance contains any categorized substances
    for known_substance, known_category in cat_data['substance_to_category'].items():
        if known_substance in substance_lower or substance_lower in known_substance:
            # Check for compound-specific distance first
            specific_distance = cat_data['substance_to_distance'].get(known_substance)
            if specific_distance is not None:
                return known_category, specific_distance
            # Fall back to category default
            distance = cat_data['category_distances'].get(known_category, _DEFAULT_OTHER_DISTANCE)
            return known_category, distance

    # Default to ANDRE category
    return 'ANDRE', _DEFAULT_OTHER_DISTANCE


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
    _KEYWORD_STATS['total_checks'] += 1

    def contains_landfill_terms(text):
        if pd.isna(text):
            return False, None
        text_lower = str(text).lower()
        landfill_keywords = ['losseplads', 'affald', 'depon', 'fyldplads', 'skraldeplads']

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
        _KEYWORD_STATS['branch'][branch_keyword] = _KEYWORD_STATS['branch'].get(branch_keyword, 0) + 1
    if activity_match:
        _KEYWORD_STATS['activity'][activity_keyword] = _KEYWORD_STATS['activity'].get(activity_keyword, 0) + 1

    if branch_match or activity_match:
        return 'LOSSEPLADS', 100  # Use 500m threshold for landfills

    # Default to ANDRE category for non-landfill branch-only sites
    return 'ANDRE', _DEFAULT_OTHER_DISTANCE


def get_keyword_stats():
    """Return current keyword matching statistics."""
    return _KEYWORD_STATS.copy()


def _extract_unique_gvfk_names(df):
    """
    Extract all unique GVFK names from a dataframe.
    Handles both 'All_Affected_GVFKs' (semicolon-separated) and 'Closest_GVFK' columns.

    Returns:
        set: Unique GVFK names
    """
    gvfk_names = set()

    # First try All_Affected_GVFKs (semicolon-separated list)
    if 'All_Affected_GVFKs' in df.columns:
        for gvfk_list in df['All_Affected_GVFKs'].dropna():
            if str(gvfk_list) != 'nan' and gvfk_list:
                gvfks = [g.strip() for g in str(gvfk_list).split(';') if g.strip()]
                gvfk_names.update(gvfks)

    # If no GVFKs found, fall back to Closest_GVFK
    if not gvfk_names and 'Closest_GVFK' in df.columns:
        for gvfk in df['Closest_GVFK'].dropna():
            if str(gvfk) != 'nan' and gvfk:
                gvfk_names.add(str(gvfk).strip())

    return gvfk_names


def create_gvfk_shapefile(high_risk_sites, output_key):
    """Create shapefile of high-risk GVFK polygons."""
    try:
        grundvand_gdf = gpd.read_file(GRUNDVAND_PATH)

        # Get high-risk GVFK names
        high_risk_gvfk_names = set()
        for _, row in high_risk_sites.iterrows():
            gvfk_list = str(row.get('All_Affected_GVFKs', ''))
            if gvfk_list and gvfk_list != 'nan':
                gvfks = [g.strip() for g in gvfk_list.split(';') if g.strip()]
                high_risk_gvfk_names.update(gvfks)
            elif 'Closest_GVFK' in row:
                closest_gvfk = str(row['Closest_GVFK'])
                if closest_gvfk and closest_gvfk != 'nan':
                    high_risk_gvfk_names.add(closest_gvfk)

        # Filter GVFK polygons
        id_col = 'Navn' if 'Navn' in grundvand_gdf.columns else grundvand_gdf.columns[0]

        high_risk_gvfk_polygons = grundvand_gdf[
            grundvand_gdf[id_col].isin(high_risk_gvfk_names)
        ].copy()

        if not high_risk_gvfk_polygons.empty:
            output_path = get_output_path(output_key)
            high_risk_gvfk_polygons.to_file(output_path)
            print(f"  Created shapefile: {output_key} ({len(high_risk_gvfk_polygons)} GVFKs)")

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
    has_substances = distance_results['Lokalitetensstoffer'].notna() & \
                     (distance_results['Lokalitetensstoffer'].astype(str).str.strip() != '') & \
                     (distance_results['Lokalitetensstoffer'].astype(str) != 'nan')

    # Check which sites have landfill-related branch/activity data
    def contains_landfill_terms(text):
        if pd.isna(text):
            return False
        text_lower = str(text).lower()
        landfill_keywords = ['losseplads', 'affald', 'deponi', 'fyld', 'skraldeplads']
        return any(keyword in text_lower for keyword in landfill_keywords)

    has_landfill_branch = distance_results['Lokalitetensbranche'].apply(contains_landfill_terms)
    has_landfill_activity = distance_results['Lokalitetensaktivitet'].apply(contains_landfill_terms)
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
    has_branch_text = distance_results['Lokalitetensbranche'].fillna('').astype(str).str.strip() != ''
    has_activity_text = distance_results['Lokalitetensaktivitet'].fillna('').astype(str).str.strip() != ''
    has_any_text = has_branch_text | has_activity_text
    parked_with_text = ((~has_qualifying_data) & has_any_text).sum()
    parked_without_text = ((~has_qualifying_data) & ~has_any_text).sum()

    print("STEP 5 QUALIFICATION CHECK")
    print("=" * 35)
    print(f"Total sites received from Step 4: {total_sites:,}")
    if total_sites > 0:
        print(f"  -> Qualifying (substance data or landfill keywords): {qualifying_count:,} ({qualifying_count/total_sites*100:.1f}%)")
        print(f"  -> Parked (no qualifying data): {non_qualifying_count:,} ({non_qualifying_count/total_sites*100:.1f}%)")
    else:
        print(f"  -> Qualifying (substance data or landfill keywords): {qualifying_count}")
        print(f"  -> Parked (no qualifying data): {non_qualifying_count}")
    print("Qualifying breakdown:")
    print(f"  Substance-only sites: {substance_only:,}")
    print(f"  Landfill-only sites: {landfill_only:,}")
    print(f"  Both substance+landfill: {both:,}")
    print("Parked (non-qualifying) breakdown:")
    print(f"  With branch/activity text but no qualifying keywords: {parked_with_text:,}")
    print(f"  Without any branch/activity text: {parked_without_text:,}")

    return sites_with_qualifying_data, sites_without_qualifying_data
