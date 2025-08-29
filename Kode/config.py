"""
Configuration file for the groundwater contamination analysis workflow.
Simplified configuration with essential paths and settings only.
"""

import os

# Base paths
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE_PATH = os.path.join(PROJECT_ROOT, "Data", "shp files")
RESULTS_PATH = os.path.join(PROJECT_ROOT, "Resultater")

# Input data paths
GRUNDVAND_PATH = os.path.join(BASE_PATH, "VP3Genbesøg_grundvand_geometri.shp")
RIVERS_PATH = os.path.join(BASE_PATH, "Rivers_gvf_rev20230825_kontakt.shp")
V1_CSV_PATH = os.path.join(PROJECT_ROOT, "Data", "v1_gvfk_forurening.csv")
V2_CSV_PATH = os.path.join(PROJECT_ROOT, "Data", "v2_gvfk_forurening.csv")
V1_SHP_PATH = os.path.join(BASE_PATH, "V1FLADER.shp")
V2_SHP_PATH = os.path.join(BASE_PATH, "V2FLADER.shp")

# Core workflow settings
WORKFLOW_SETTINGS = {
    'risk_threshold_m': 500,
    'additional_thresholds_m': [250, 500, 1000, 1500, 2000],  # For visualizations
    'progress_interval_percent': 10,
    'contact_filter_value': 1,
}

# Essential output files (only files used by downstream steps or visualizations)
OUTPUT_FILES = {
    # Cross-step dependencies
    'step4_final_distances_for_risk_assessment': os.path.join(RESULTS_PATH, 'step4_final_distances.csv'),
    
    # Files used by visualizations
    'step2_river_gvfk': os.path.join(RESULTS_PATH, 'step2_gvfk_with_rivers.shp'),
    'step3_v1v2_sites': os.path.join(RESULTS_PATH, 'step3_v1v2_sites.shp'),
    'step3_gvfk_polygons': os.path.join(RESULTS_PATH, 'step3_gvfk_with_v1v2.shp'),
    'step5_gvfk_high_risk': os.path.join(RESULTS_PATH, f'step5_gvfk_high_risk_{WORKFLOW_SETTINGS["risk_threshold_m"]}m.shp'),
    'unique_lokalitet_distances': os.path.join(RESULTS_PATH, 'unique_lokalitet_distances.csv'),
    'unique_lokalitet_distances_shp': os.path.join(RESULTS_PATH, 'unique_lokalitet_distances.shp'),
    'step4_valid_distances': os.path.join(RESULTS_PATH, 'step4_valid_distances.csv'),
    'interactive_distance_map': os.path.join(RESULTS_PATH, 'interactive_distance_map.html'),
    
    # Final outputs  
    'step5_high_risk_sites': os.path.join(RESULTS_PATH, f'step5_high_risk_sites_{WORKFLOW_SETTINGS["risk_threshold_m"]}m.csv'),
    'step5_compound_specific_sites': os.path.join(RESULTS_PATH, 'step5_compound_specific_sites.csv'),
    'step5_compound_gvfk_high_risk': os.path.join(RESULTS_PATH, 'step5_compound_gvfk_high_risk.shp'),
    'workflow_summary': os.path.join(RESULTS_PATH, 'workflow_summary.csv'),
    
    # Category analysis files (for compound-specific visualizations)
    'step5_category_summary': os.path.join(RESULTS_PATH, 'step5_category_summary.csv'),
    'step5_category_substance_summary': os.path.join(RESULTS_PATH, 'step5_category_substance_summary.csv'),
    'step5_category_flags': os.path.join(RESULTS_PATH, 'step5_category_flags.csv')
}

def ensure_results_directory():
    """Create results directory if it doesn't exist."""
    os.makedirs(RESULTS_PATH, exist_ok=True)

def get_output_path(file_key, threshold_m=None):
    """
    Get full path for an output file.
    
    Args:
        file_key (str): Key from OUTPUT_FILES
        threshold_m (int, optional): Threshold parameter (for backward compatibility)
    
    Returns:
        str: Full path to output file
    """
    if file_key not in OUTPUT_FILES:
        raise KeyError(f"Unknown file key: {file_key}")
    
    full_path = OUTPUT_FILES[file_key]
    
    # Ensure the directory exists
    output_dir = os.path.dirname(full_path)
    os.makedirs(output_dir, exist_ok=True)
    
    return full_path

def get_visualization_path(step_name):
    """
    Get the visualization folder path for a specific step.
    
    Args:
        step_name (str): Step name ('step1', 'step2', etc.)
    
    Returns:
        str: Full path to step's visualization folder
    """
    viz_path = os.path.join(RESULTS_PATH, "Figures", step_name)
    os.makedirs(viz_path, exist_ok=True)
    return viz_path

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
    
    missing_files = [file_path for file_path in required_files if not os.path.exists(file_path)]
    
    if missing_files:
        print("Missing input files:")
        for file_path in missing_files:
            print(f"  - {file_path}")
        return False
    
    return True