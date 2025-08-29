"""
Step 1: Count total unique groundwater aquifers (GVFK) in the base file.

This step loads the base groundwater geometry file and counts unique GVFK
based on the ID column. No output files are created as this is just counting.
"""

import geopandas as gpd
import warnings
from shapely.errors import ShapelyDeprecationWarning
from config import GRUNDVAND_PATH

# Suppress shapely deprecation warnings
warnings.filterwarnings("ignore", category=ShapelyDeprecationWarning)

def run_step1():
    """
    Execute Step 1: Count total unique groundwater aquifers (GVFK).
    
    Returns:
        tuple: (gvf_geodataframe, unique_gvfk_count)
    """
    print("Step 1: Counting total unique groundwater aquifers (GVFK)")
    
    # Read the base shapefile
    gvf = gpd.read_file(GRUNDVAND_PATH)
    
    # Count unique GVFK based on ID column
    if 'Navn' not in gvf.columns:
        raise ValueError("'Navn' column not found in groundwater file")
    
    unique_gvfk = gvf["Navn"].nunique()
    print(f"Total unique GVFK: {unique_gvfk}")
    
    return gvf, unique_gvfk

if __name__ == "__main__":
    # Allow running this step independently
    gvf_data, count = run_step1()
    if gvf_data is not None:
        print("################################################")
        print(f"Step 1 completed: {count} unique GVFK found.")
        print("#######################")
    else:
        print("Step 1 failed.") 