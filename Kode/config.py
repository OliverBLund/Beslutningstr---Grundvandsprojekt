"""
Configuration file for the groundwater contamination analysis workflow.
Contains all paths, settings, and constants used across the workflow steps.
"""

import os

# Base paths - Use absolute paths to avoid working directory issues
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # Project root (parent of Kode)
BASE_PATH = os.path.join(PROJECT_ROOT, "Data", "shp files")
RESULTS_PATH = os.path.join(PROJECT_ROOT, "Resultater")

# Step-specific result folders
STEP_FOLDERS = {
    'step1': os.path.join(RESULTS_PATH, "Step1_GVFK_Base"),
    'step2': os.path.join(RESULTS_PATH, "Step2_River_Contact"),
    'step3': os.path.join(RESULTS_PATH, "Step3_V1V2_Sites"),
    'step4': os.path.join(RESULTS_PATH, "Step4_Distances"),
    'step5': os.path.join(RESULTS_PATH, "Step5_Risk_Assessment"),
    'workflow': os.path.join(RESULTS_PATH, "Workflow_Summary"),
}

# Visualization subfolders for each step
VISUALIZATION_FOLDERS = {
    'step1': os.path.join(STEP_FOLDERS['step1'], "Figures"),
    'step2': os.path.join(STEP_FOLDERS['step2'], "Figures"),
    'step3': os.path.join(STEP_FOLDERS['step3'], "Figures"),
    'step4': os.path.join(STEP_FOLDERS['step4'], "Figures"),
    'step5': os.path.join(STEP_FOLDERS['step5'], "Figures"),
    'workflow': os.path.join(STEP_FOLDERS['workflow'], "Figures"),
}

# Input data paths
GRUNDVAND_PATH = os.path.join(BASE_PATH, "VP3Genbesøg_grundvand_geometri.shp")
RIVERS_PATH = os.path.join(BASE_PATH, "Rivers_gvf_rev20230825_kontakt.shp")

# V1/V2 data paths (CSV and shapefile combinations)
# Updated to use:
# - Main CSV files from Data/ directory (contain Step 5 columns: Lokalitetensbranche, Lokalitetensaktivitet, Lokalitetensstoffer)
# - V1FLADER/V2FLADER shapefiles (pre-dissolved, more comprehensive coverage)
V1_CSV_PATH = os.path.join(PROJECT_ROOT, "Data", "v1_gvfk_forurening.csv")
V2_CSV_PATH = os.path.join(PROJECT_ROOT, "Data", "v2_gvfk_forurening.csv")
V1_SHP_PATH = os.path.join(BASE_PATH, "V1FLADER.shp")
V2_SHP_PATH = os.path.join(BASE_PATH, "V2FLADER.shp")
#V1_SHP_PATH = os.path.join(BASE_PATH, "V1_gvfk_forurening.shp")
#V2_SHP_PATH = os.path.join(BASE_PATH, "V2_gvfk_forurening.shp")
# Output file names with dynamic threshold placeholders

OUTPUT_FILES_TEMPLATES = {
    # Step 1: GVFK Base Data
    'step1_gvfk': os.path.join('Step1_GVFK_Base', 'step1_all_gvfk.shp'),
    
    # Step 2: River Contact Analysis  
    'step2_river_gvfk': os.path.join('Step2_River_Contact', 'step2_gvfk_with_rivers.shp'),
    
    # Step 3: V1/V2 Sites Analysis
    'step3_v1v2_sites': os.path.join('Step3_V1V2_Sites', 'step3_v1v2_sites.shp'),
    'step3_gvfk_polygons': os.path.join('Step3_V1V2_Sites', 'step3_gvfk_with_v1v2.shp'),
    'step3_relationships': os.path.join('Step3_V1V2_Sites', 'step3_site_gvfk_relationships.csv'),
    
    # Step 4: Distance Analysis
    'step4_distance_results': os.path.join('Step4_Distances', 'step4_distance_results.csv'),
    'step4_valid_distances': os.path.join('Step4_Distances', 'step4_valid_distances.csv'),
    'step4_final_distances_for_risk_assessment': os.path.join('Step4_Distances', 'step4_final_distances_for_risk_assessment.csv'),
    'unique_lokalitet_distances': os.path.join('Step4_Distances', 'unique_lokalitet_distances.csv'),
    'unique_lokalitet_distances_shp': os.path.join('Step4_Distances', 'unique_lokalitet_distances.shp'),
    'v1v2_sites_with_distances_shp': os.path.join('Step4_Distances', 'v1v2_sites_with_distances.shp'),
    'step4_site_level_summary': os.path.join('Step4_Distances', 'step4_site_level_summary.csv'),
    'interactive_distance_map': os.path.join('Step4_Distances', 'interactive_distance_map.html'),
    
    # Step 5: Risk Assessment (Threshold-dependent files use {risk_threshold_m} placeholder)
    'step5_high_risk_sites': os.path.join('Step5_Risk_Assessment', 'step5_high_risk_sites_{risk_threshold_m}m.csv'),
    'step5_analysis_summary': os.path.join('Step5_Risk_Assessment', 'step5_analysis_summary_{risk_threshold_m}m.csv'),
    'step5_contamination_breakdown': os.path.join('Step5_Risk_Assessment', 'step5_contamination_breakdown_{risk_threshold_m}m.csv'),
    'step5_gvfk_high_risk': os.path.join('Step5_Risk_Assessment', 'step5_gvfk_high_risk_{risk_threshold_m}m.shp'),
    
    # Step 5: Compound-Specific Analysis
    'step5_compound_specific_sites': os.path.join('Step5_Risk_Assessment', 'Compound_Specific', 'step5_compound_specific_high_risk_sites.csv'),
    'step5_compound_analysis_summary': os.path.join('Step5_Risk_Assessment', 'Compound_Specific', 'step5_compound_specific_analysis_summary.csv'),
    'step5_compound_breakdown': os.path.join('Step5_Risk_Assessment', 'Compound_Specific', 'step5_compound_specific_breakdown.csv'),
    'step5_compound_gvfk_high_risk': os.path.join('Step5_Risk_Assessment', 'Compound_Specific', 'step5_compound_specific_gvfk_high_risk.shp'),
    'step5_compound_distance_mapping': os.path.join('Step5_Risk_Assessment', 'Compound_Specific', 'step5_compound_distance_mapping.csv'),
    
    # Step 5: Category (keyword) Based Analysis
    'step5_category_flags': os.path.join('Step5_Risk_Assessment', 'Category_Analysis', 'step5_category_flags.csv'),
    'step5_category_summary': os.path.join('Step5_Risk_Assessment', 'Category_Analysis', 'step5_category_summary.csv'),
    'step5_category_substance_summary': os.path.join('Step5_Risk_Assessment', 'Category_Analysis', 'step5_category_substance_summary.csv'),
    'step5_category_overview_png': os.path.join('Step5_Risk_Assessment', 'Category_Analysis', 'step5_category_overview.png'),
    'step5_category_dashboard_png': os.path.join('Step5_Risk_Assessment', 'Category_Analysis', 'step5_category_dashboard.png'),
    'step5_category_detailed_png': os.path.join('Step5_Risk_Assessment', 'Category_Analysis', 'step5_category_detailed_analysis.png'),
    
    # Workflow Summary
    'workflow_summary': os.path.join('Workflow_Summary', 'workflow_summary.csv')
}

# WORKFLOW ANALYSIS PARAMETERS - Centralized control for all analysis settings
WORKFLOW_SETTINGS = {
    # Risk Assessment Thresholds
    'risk_threshold_m': 500,                    # Primary risk distance threshold for Step 5
    'additional_thresholds_m': [250, 500, 1000, 1500, 2000],  # For sensitivity analysis and visualizations
    
    # Data Filtering Settings
    'require_contamination_data': True,         # Only include sites with documented contamination substances
    'contact_filter_value': 1,                  # River segments with Kontakt = 1 (actual groundwater-surface water interaction)
    
    # Processing Settings
    'progress_interval_percent': 10,            # Print progress every 10% during distance calculations
    'max_visualization_sites': 1000,           # Max sites for interactive map (performance limit)
    
    # Geometry and Data Validation
    'validate_geometries': True,                # Check for valid geometries before processing
    'expected_crs': 'EPSG:25832',              # Expected CRS (UTM32 EUREF89 for Denmark)
    'allow_empty_contamination': False,        # Whether to include sites without contamination data
}

# COMPOUND-SPECIFIC RISK ASSESSMENT SETTINGS
COMPOUND_RISK_DISTANCES = {
    # High mobility compounds (longer distances)
    'Tetrachlorethylen': 800,                   # Chlorinated solvent - very mobile
    'Trichlorethylen': 800,                     # Chlorinated solvent - very mobile
    'Benzin': 600,                              # Gasoline - high mobility
    'Olie-benzin': 600,                         # Oil-gasoline mixture
    
    # Medium mobility petroleum products
    'Olieprodukter': 400,                       # General oil products
    'Fyringsolie': 350,                         # Heating oil
    'Olie': 350,                                # General oil
    'Diesel': 350,                              # Diesel fuel
    
    # Lower mobility compounds
    'Tungmetaller': 200,                        # Heavy metals - limited mobility
    'Bly': 150,                                 # Lead - low mobility
    'Nikkel': 200,                              # Nickel - limited mobility
    'Kobber': 150,                              # Copper - low mobility
    'Zink': 200,                                # Zinc - somewhat mobile
    
    # Special cases
    'Lossepladsperkolat': 500,                  # Landfill leachate - mixed compounds
    'PAH': 250,                                 # Polycyclic aromatic hydrocarbons - moderate mobility
    'BTEX': 500,                                # Benzene, toluene, ethylbenzene, xylene - mobile
    
    # Default for unspecified compounds
    'default': 300,                             # Conservative default for unknown compounds
}

# Legacy OUTPUT_FILES for backward compatibility - will use default threshold
OUTPUT_FILES = {key: template.format(risk_threshold_m=WORKFLOW_SETTINGS['risk_threshold_m']) 
                for key, template in OUTPUT_FILES_TEMPLATES.items()}

# Legacy settings for backward compatibility - DEPRECATED, use WORKFLOW_SETTINGS instead
DISTANCE_CALCULATION_SETTINGS = {
    'progress_interval_percent': WORKFLOW_SETTINGS['progress_interval_percent'],
    'contact_filter_value': WORKFLOW_SETTINGS['contact_filter_value'],
    'max_visualization_sites': WORKFLOW_SETTINGS['max_visualization_sites']
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
    """Create results directory and all step-specific subdirectories if they don't exist."""
    # Create main results directory
    os.makedirs(RESULTS_PATH, exist_ok=True)
    
    # Create all step-specific subdirectories
    for step_name, step_path in STEP_FOLDERS.items():
        os.makedirs(step_path, exist_ok=True)
    
    # Create all visualization subdirectories
    for step_name, viz_path in VISUALIZATION_FOLDERS.items():
        os.makedirs(viz_path, exist_ok=True)
    
    # Create Step 5 subdirectories for compound-specific and category analysis
    step5_compound_path = os.path.join(STEP_FOLDERS['step5'], 'Compound_Specific')
    step5_category_path = os.path.join(STEP_FOLDERS['step5'], 'Category_Analysis')
    os.makedirs(step5_compound_path, exist_ok=True)
    os.makedirs(step5_category_path, exist_ok=True)

def get_output_path(file_key, risk_threshold_m=None):
    """
    Get full path for an output file with optional threshold override.
    
    Args:
        file_key (str): Key from OUTPUT_FILES_TEMPLATES
        risk_threshold_m (int, optional): Override risk threshold for file naming.
                                        If None, uses WORKFLOW_SETTINGS['risk_threshold_m']
    
    Returns:
        str: Full path to output file
    """
    if risk_threshold_m is None:
        risk_threshold_m = WORKFLOW_SETTINGS['risk_threshold_m']
    
    filename_template = OUTPUT_FILES_TEMPLATES[file_key]
    relative_path = filename_template.format(risk_threshold_m=risk_threshold_m)
    full_path = os.path.join(RESULTS_PATH, relative_path)
    
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
    if step_name not in VISUALIZATION_FOLDERS:
        raise ValueError(f"Unknown step: {step_name}. Available steps: {list(VISUALIZATION_FOLDERS.keys())}")
    
    viz_path = VISUALIZATION_FOLDERS[step_name]
    os.makedirs(viz_path, exist_ok=True)
    return viz_path

def get_output_filename(file_key, risk_threshold_m=None):
    """
    Get filename for an output file with optional threshold override.
    
    Args:
        file_key (str): Key from OUTPUT_FILES_TEMPLATES
        risk_threshold_m (int, optional): Override risk threshold for file naming.
                                        If None, uses WORKFLOW_SETTINGS['risk_threshold_m']
    
    Returns:
        str: Filename with threshold substituted
    """
    if risk_threshold_m is None:
        risk_threshold_m = WORKFLOW_SETTINGS['risk_threshold_m']
    
    filename_template = OUTPUT_FILES_TEMPLATES[file_key]
    return filename_template.format(risk_threshold_m=risk_threshold_m)

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

def validate_workflow_settings():
    """
    Validate WORKFLOW_SETTINGS for consistency and correctness.
    
    Returns:
        tuple: (is_valid: bool, validation_messages: list)
    """
    messages = []
    is_valid = True
    
    # Validate risk thresholds
    if WORKFLOW_SETTINGS['risk_threshold_m'] <= 0:
        messages.append("ERROR: risk_threshold_m must be positive")
        is_valid = False
    
    if not all(t > 0 for t in WORKFLOW_SETTINGS['additional_thresholds_m']):
        messages.append("ERROR: All additional_thresholds_m must be positive")
        is_valid = False
    
    if WORKFLOW_SETTINGS['risk_threshold_m'] not in WORKFLOW_SETTINGS['additional_thresholds_m']:
        messages.append("WARNING: risk_threshold_m not in additional_thresholds_m list")
    
    # Validate progress settings
    if not (0 < WORKFLOW_SETTINGS['progress_interval_percent'] <= 100):
        messages.append("ERROR: progress_interval_percent must be between 1 and 100")
        is_valid = False
    
    if WORKFLOW_SETTINGS['max_visualization_sites'] <= 0:
        messages.append("ERROR: max_visualization_sites must be positive")
        is_valid = False
    
    # Validate contact filter
    if WORKFLOW_SETTINGS['contact_filter_value'] not in [0, 1]:
        messages.append("WARNING: contact_filter_value should typically be 0 or 1")
    
    # Validate CRS format
    expected_crs = WORKFLOW_SETTINGS['expected_crs']
    if not expected_crs.startswith('EPSG:'):
        messages.append("WARNING: expected_crs should be in EPSG format (e.g., 'EPSG:25832')")
    
    return is_valid, messages

def print_workflow_settings_summary():
    """
    Print a comprehensive summary of current workflow settings.
    """
    print("WORKFLOW CONFIGURATION SUMMARY")
    print("=" * 60)
    
    # Output Folder Structure
    print(f"Output Folder Structure:")
    print(f"  Main Results: {RESULTS_PATH}")
    for step_name, step_path in STEP_FOLDERS.items():
        step_display = step_name.replace('_', ' ').title()
        print(f"    {step_display}: {os.path.relpath(step_path)}")
    print(f"    Step 5 Subfolders:")
    print(f"      Compound Specific: Step5_Risk_Assessment/Compound_Specific")
    print(f"      Category Analysis: Step5_Risk_Assessment/Category_Analysis")
    
    # Risk Assessment Settings
    print(f"\nRisk Assessment:")
    print(f"  Primary threshold: {WORKFLOW_SETTINGS['risk_threshold_m']}m")
    print(f"  Additional thresholds: {WORKFLOW_SETTINGS['additional_thresholds_m']}")
    print(f"  Require contamination data: {WORKFLOW_SETTINGS['require_contamination_data']}")
    print(f"  Allow empty contamination: {WORKFLOW_SETTINGS['allow_empty_contamination']}")
    
    # Data Processing Settings
    print(f"\nData Processing:")
    print(f"  River contact filter: Kontakt = {WORKFLOW_SETTINGS['contact_filter_value']}")
    print(f"  Progress reporting: Every {WORKFLOW_SETTINGS['progress_interval_percent']}%")
    print(f"  Max visualization sites: {WORKFLOW_SETTINGS['max_visualization_sites']}")
    
    # Validation Settings
    print(f"\nValidation:")
    print(f"  Geometry validation: {WORKFLOW_SETTINGS['validate_geometries']}")
    print(f"  Expected CRS: {WORKFLOW_SETTINGS['expected_crs']}")
    
    # File naming preview
    print(f"\nOutput File Examples (with {WORKFLOW_SETTINGS['risk_threshold_m']}m threshold):")
    step5_examples = [
        'step5_high_risk_sites',
        'step5_analysis_summary', 
        'step5_gvfk_high_risk'
    ]
    for key in step5_examples:
        filename = get_output_filename(key)
        print(f"  {key}: {filename}")
    
    # Validation check
    print(f"\nConfiguration Validation:")
    is_valid, messages = validate_workflow_settings()
    if is_valid:
        print("  ✓ All settings are valid")
    else:
        print("  ✗ Configuration issues found:")
    
    for message in messages:
        level = "ERROR" if message.startswith("ERROR") else "WARNING"
        print(f"    {level}: {message.split(': ', 1)[1]}")
    
    print("=" * 60) 