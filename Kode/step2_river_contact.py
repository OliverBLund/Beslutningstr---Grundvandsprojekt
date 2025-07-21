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
    DISTANCE_CALCULATION_SETTINGS
)

# Suppress shapely deprecation warnings
warnings.filterwarnings("ignore", category=ShapelyDeprecationWarning)

def run_step2():
    """
    Execute Step 2: Count GVFK in contact with targeted rivers.
    
    Returns:
        tuple: (rivers_gvfk_list, unique_rivers_gvfk_count, gvf_with_rivers_geodataframe)
    """
    print("\nStep 2: Counting GVFK in contact with targeted rivers")
    
    # Ensure output directory exists
    ensure_results_directory()
    
    # Read the rivers contact shapefile
    try:
        rivers = gpd.read_file(RIVERS_PATH)
        print(f"Loaded rivers file: {len(rivers)} river segments")
    except Exception as e:
        print(f"Error loading rivers file: {e}")
        return [], 0, None
    
    # Filter to rivers with contact
    contact_value = DISTANCE_CALCULATION_SETTINGS['contact_filter_value']
    if 'Kontakt' in rivers.columns:
        rivers_with_contact = rivers[rivers['Kontakt'] == contact_value]
        print(f"River segments with Kontakt = {contact_value}: {len(rivers_with_contact)}")
    else:
        print("Warning: 'Kontakt' column not found. Using all river segments.")
        rivers_with_contact = rivers
    
    # Extract unique GVFK names from river contact data
    if 'GVForekom' not in rivers_with_contact.columns:
        print("Error: 'GVForekom' column not found in rivers file")
        return [], 0, None
    
    # Get list of GVFK names that have river contact
    rivers_gvfk = [
        gvf for gvf in rivers_with_contact["GVForekom"].unique() 
        if gvf is not None and isinstance(gvf, str)
    ]
    unique_rivers_gvfk = len(rivers_gvfk)
    print(f"Number of unique GVFK in contact with targeted rivers: {unique_rivers_gvfk}")
    
    # Load base GVFK file and filter to those with river contact
    try:
        gvf = gpd.read_file(GRUNDVAND_PATH)
        print(f"Loaded base GVFK file: {len(gvf)} features")
    except Exception as e:
        print(f"Error loading base GVFK file: {e}")
        return rivers_gvfk, unique_rivers_gvfk, None
    
    # Filter GVFK to only those with river contact
    if 'Navn' not in gvf.columns:
        print("Error: 'Navn' column not found in GVFK file")
        return rivers_gvfk, unique_rivers_gvfk, None
    
    gvf_with_rivers = gvf[gvf["Navn"].isin(rivers_gvfk)]
    print(f"Found {len(gvf_with_rivers)} GVFK geometries with river contact")
    
    # Save GVFK with river contact for visualization and subsequent steps
    output_path = get_output_path('step2_river_gvfk')
    try:
        gvf_with_rivers.to_file(output_path)
        print(f"Saved GVFK with river contact to: {output_path}")
    except Exception as e:
        print(f"Error saving GVFK with river contact: {e}")
    
    return rivers_gvfk, unique_rivers_gvfk, gvf_with_rivers

if __name__ == "__main__":
    # Allow running this step independently
    rivers_gvfk, count, gvf_rivers = run_step2()
    if rivers_gvfk:
        print(f"Step 2 completed successfully. Found {count} GVFK with river contact.")
    else:
        print("Step 2 failed or found no GVFK with river contact.") 