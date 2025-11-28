"""
Step 2: Count how many GVFK are in contact with targeted rivers.

This step identifies groundwater aquifers that have contact with river segments
where Kontakt = 1, indicating actual groundwater-surface water interaction.
"""

import geopandas as gpd
import warnings
from shapely.errors import ShapelyDeprecationWarning
from config import (
    GRUNDVAND_PATH, RIVERS_PATH, get_output_path, ensure_results_directory,
    WORKFLOW_SETTINGS, COLUMN_MAPPINGS
)

# Suppress shapely deprecation warnings
warnings.filterwarnings("ignore", category=ShapelyDeprecationWarning)

def run_step2():
    """
    Execute Step 2: Count GVFK in contact with targeted rivers.

    Returns:
        tuple: (rivers_gvfk_list, unique_rivers_gvfk_count, gvf_with_rivers_geodataframe)
    """
    print("Step 2: Counting GVFK in contact with targeted rivers")

    # Ensure output directory exists
    ensure_results_directory()

    # Read the rivers contact shapefile
    rivers = gpd.read_file(RIVERS_PATH, encoding='utf-8')

    # Get column names from mappings
    contact_col = COLUMN_MAPPINGS['rivers']['contact']
    river_gvfk_col = COLUMN_MAPPINGS['rivers']['gvfk_id']

    # Filter to rivers with contact
    contact_value = WORKFLOW_SETTINGS['contact_filter_value']
    if contact_col in rivers.columns:
        rivers_with_contact = rivers[rivers[contact_col] == contact_value]
    else:
        print(f"WARNING: '{contact_col}' column not found. Using all river segments.")
        rivers_with_contact = rivers

    # Extract unique GVFK names from river contact data
    if river_gvfk_col not in rivers_with_contact.columns:
        raise ValueError(f"'{river_gvfk_col}' column not found in rivers file")

    # Get list of GVFK names that have river contact
    rivers_gvfk = [
        gvf for gvf in rivers_with_contact[river_gvfk_col].unique()
        if gvf is not None and isinstance(gvf, str)
    ]
    unique_rivers_gvfk = len(rivers_gvfk)
    print(f"GVFK with river contact: {unique_rivers_gvfk}")

    # Load base GVFK file and filter to those with river contact
    gvf = gpd.read_file(GRUNDVAND_PATH)

    # Filter GVFK to only those with river contact
    gvfk_col = COLUMN_MAPPINGS['grundvand']['gvfk_id']
    if gvfk_col not in gvf.columns:
        raise ValueError(f"'{gvfk_col}' column not found in GVFK file")

    gvf_with_rivers = gvf[gvf[gvfk_col].isin(rivers_gvfk)]

    # Save GVFK with river contact for visualization and subsequent steps
    output_path = get_output_path('step2_river_gvfk')
    gvf_with_rivers.to_file(output_path, encoding="utf-8")
    print(f"Saved GVFK with river contact: {len(gvf_with_rivers)} geometries")

    return rivers_gvfk, unique_rivers_gvfk, gvf_with_rivers

if __name__ == "__main__":
    # Allow running this step independently
    rivers_gvfk, count, gvf_rivers = run_step2()
    if rivers_gvfk:
        print("################################################")
        print(f"Step 2 completed successfully. Found {count} GVFK with river contact.")
        print("################################################")
    else:
        print("Step 2 failed or found no GVFK with river contact.")
