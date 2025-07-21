"""
Configuration file for the groundwater contamination analysis workflow.
Contains all paths, settings, and constants used across the workflow steps.
"""

import os

# Base paths
BASE_PATH = os.path.join(".", "Data", "shp files")
RESULTS_PATH = os.path.join(".", "Resultater")

# Input data paths
GRUNDVAND_PATH = os.path.join(BASE_PATH, "VP3Genbesøg_grundvand_geometri.shp")
RIVERS_PATH = os.path.join(BASE_PATH, "Rivers_gvf_rev20230825_kontakt.shp")

# V1/V2 data paths (CSV and shapefile combinations)
# Updated to use:
# - Main CSV files from Data/ directory (contain Step 5 columns: Lokalitetensbranche, Lokalitetensaktivitet, Lokalitetensstoffer)
# - V1FLADER/V2FLADER shapefiles (pre-dissolved, more comprehensive coverage)
V1_CSV_PATH = os.path.join(".", "Data", "v1_gvfk_forurening.csv")
V2_CSV_PATH = os.path.join(".", "Data", "v2_gvfk_forurening.csv")
V1_SHP_PATH = os.path.join(BASE_PATH, "V1FLADER.shp")
V2_SHP_PATH = os.path.join(BASE_PATH, "V2FLADER.shp")
#V1_SHP_PATH = os.path.join(BASE_PATH, "V1_gvfk_forurening.shp")
#V2_SHP_PATH = os.path.join(BASE_PATH, "V2_gvfk_forurening.shp")
# Output file names
OUTPUT_FILES = {
    'step1_gvfk': 'step1_all_gvfk.shp',
    'step2_river_gvfk': 'step2_gvfk_with_rivers.shp',
    'step3_v1v2_sites': 'step3_v1v2_sites.shp',
    'step3_gvfk_polygons': 'step3_gvfk_with_v1v2.shp',
    'step3_relationships': 'step3_site_gvfk_relationships.csv',
    'step4_distance_results': 'step4_distance_results.csv',
    'step4_valid_distances': 'step4_valid_distances.csv',
    'step4_final_distances_for_risk_assessment': 'step4_final_distances_for_risk_assessment.csv',
    'unique_lokalitet_distances': 'unique_lokalitet_distances.csv',
    'unique_lokalitet_distances_shp': 'unique_lokalitet_distances.shp',
    'v1v2_sites_with_distances_shp': 'v1v2_sites_with_distances.shp',
    'step4_site_level_summary': 'step4_site_level_summary.csv',
    'interactive_distance_map': 'interactive_distance_map.html',
    'step5_high_risk_sites': 'step5_high_risk_sites_500m.csv',
    'step5_analysis_summary': 'step5_analysis_summary_500m.csv',
    'step5_contamination_breakdown': 'step5_contamination_breakdown_500m.csv',
    'step5_gvfk_high_risk': 'step5_gvfk_high_risk_500m.shp',
    'workflow_summary': 'workflow_summary.csv'
}

# Analysis settings
DISTANCE_CALCULATION_SETTINGS = {
    'progress_interval_percent': 10,  # Print progress every 10%
    'contact_filter_value': 1,        # River segments with Kontakt = 1
    'max_visualization_sites': 1000   # Max sites for interactive map
}

# Visualization settings
MAP_SETTINGS = {
    'center_zoom': 10,
    'min_distance_color': 'red',
    'non_min_distance_color': 'orange',
    'min_distance_weight': 3,
    'non_min_distance_weight': 1,
    'min_distance_opacity': 1.0,
    'non_min_distance_opacity': 0.6
}

# Site type colors for visualizations
SITE_TYPE_COLORS = {
    'V1': 'red',
    'V2': 'blue', 
    'V1 og V2': 'purple',
    'Unknown': 'gray'
}

def ensure_results_directory():
    """Create results directory if it doesn't exist."""
    os.makedirs(RESULTS_PATH, exist_ok=True)

def get_output_path(file_key):
    """Get full path for an output file."""
    return os.path.join(RESULTS_PATH, OUTPUT_FILES[file_key])

def validate_input_files():
    """Check if all required input files exist."""
    required_files = [
        GRUNDVAND_PATH,
        RIVERS_PATH,
        V1_CSV_PATH,
        V2_CSV_PATH,
        V1_SHP_PATH,
        V2_SHP_PATH
    ]
    
    missing_files = []
    for file_path in required_files:
        if not os.path.exists(file_path):
            missing_files.append(file_path)
    
    if missing_files:
        print("WARNING: Missing input files:")
        for file_path in missing_files:
            print(f"  - {file_path}")
        return False
    
    return True 