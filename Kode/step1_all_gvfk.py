"""
Step 1: Count total unique groundwater aquifers (GVFK) in the base file.

This step loads the base groundwater geometry file and counts unique GVFK
based on the ID column. Results are saved for use in subsequent steps.
"""

import geopandas as gpd
import warnings
from shapely.errors import ShapelyDeprecationWarning
from config import GRUNDVAND_PATH, get_output_path, ensure_results_directory

# Suppress shapely deprecation warnings
warnings.filterwarnings("ignore", category=ShapelyDeprecationWarning)

def run_step1():
    """
    Execute Step 1: Count total unique groundwater aquifers (GVFK).
    
    Returns:
        tuple: (gvf_geodataframe, unique_gvfk_count)
    """
    print("Step 1: Counting total unique groundwater aquifers (GVFK)")
    
    # Ensure output directory exists
    ensure_results_directory()
    
    # Read the base shapefile
    try:
        gvf = gpd.read_file(GRUNDVAND_PATH)
        print(f"Loaded groundwater geometry file: {len(gvf)} features")
    except Exception as e:
        print(f"Error loading groundwater file: {e}")
        return None, 0
    
    # Count unique GVFK based on ID column
    if 'Navn' not in gvf.columns:
        print("Error: 'Navn' column not found in groundwater file")
        return None, 0
    
    unique_gvfk = gvf["Navn"].nunique()
    print(f"Total number of unique groundwater aquifers (GVFK): {unique_gvfk}")
    
    # Save all GVFK for visualization and subsequent steps
    output_path = get_output_path('step1_gvfk')
    try:
        gvf.to_file(output_path)
        print(f"Saved all GVFK to: {output_path}")
    except Exception as e:
        print(f"Error saving GVFK file: {e}")
        return gvf, unique_gvfk
    
    return gvf, unique_gvfk

if __name__ == "__main__":
    # Allow running this step independently
    gvf_data, count = run_step1()
    if gvf_data is not None:
        print(f"Step 1 completed successfully. Found {count} unique GVFK.")
    else:
        print("Step 1 failed.") 