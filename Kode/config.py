"""Core configuration for groundwater analysis workflows.

Centralized configuration for file locations, workflow settings, and paths.
All paths use `pathlib.Path` objects for cross-platform compatibility.

User-configurable settings are loaded from SETTINGS.yaml
"""

from __future__ import annotations

from pathlib import Path

import yaml

# -------------------------------------------------------------------
# Project structure
# -------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent

DATA_DIR = PROJECT_ROOT / "Data"
SHAPE_DIR = DATA_DIR / "shp files"
RESULTS_DIR = PROJECT_ROOT / "Resultater"
CACHE_DIR = RESULTS_DIR / "cache"

# Organized step-specific output directories
STEP2_DIR = RESULTS_DIR / "step2_river_contact"
STEP2_DATA_DIR = STEP2_DIR / "data"
STEP2_FIGURES_DIR = STEP2_DIR / "figures"

STEP3_DIR = RESULTS_DIR / "step3_v1v2_sites"
STEP3_DATA_DIR = STEP3_DIR / "data"
STEP3_FIGURES_DIR = STEP3_DIR / "figures"

STEP4_DIR = RESULTS_DIR / "step4_distances"
STEP4_DATA_DIR = STEP4_DIR / "data"
STEP4_FIGURES_DIR = STEP4_DIR / "figures"

STEP5_DIR = RESULTS_DIR / "step5_risk_assessment"
STEP5_DATA_DIR = STEP5_DIR / "data"
STEP5_FIGURES_DIR = STEP5_DIR / "figures"

STEP6_DIR = RESULTS_DIR / "step6_tilstandsvurdering"
STEP6_DATA_DIR = STEP6_DIR / "data"
STEP6_FIGURES_DIR = STEP6_DIR / "figures"
STEP6_FIGURES_COMBINED_DIR = STEP6_FIGURES_DIR / "combined"
STEP6_FIGURES_ANALYTICAL_DIR = STEP6_FIGURES_DIR / "analytical"
STEP6_FIGURES_DIAGNOSTICS_DIR = STEP6_FIGURES_DIR / "diagnostics"

WORKFLOW_SUMMARY_DIR = RESULTS_DIR / "workflow_summary"

# Legacy FIGURES_DIR for backward compatibility (can be removed after full migration)
FIGURES_DIR = RESULTS_DIR / "Figures"

# -------------------------------------------------------------------
# Load user settings from YAML
# -------------------------------------------------------------------
SETTINGS_FILE = BASE_DIR / "SETTINGS.yaml"


def _load_workflow_settings():
    """Load workflow settings from SETTINGS.yaml file."""
    if not SETTINGS_FILE.exists():
        print(f"WARNING: {SETTINGS_FILE} not found. Using default settings.")
        return {
            "risk_threshold_m": 500,
            "additional_thresholds_m": [250, 500, 1000, 1500, 2000],
            "progress_interval_percent": 10,
            "contact_filter_value": 1,
            "enable_multi_threshold_analysis": False,
        }

    try:
        with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
            settings = yaml.safe_load(f)
        return settings
    except Exception as e:
        print(f"ERROR loading {SETTINGS_FILE}: {e}")
        print("Using default settings.")
        return {
            "risk_threshold_m": 500,
            "additional_thresholds_m": [250, 500, 1000, 1500, 2000],
            "progress_interval_percent": 10,
            "contact_filter_value": 1,
            "enable_multi_threshold_analysis": False,
        }


WORKFLOW_SETTINGS = _load_workflow_settings()

# -------------------------------------------------------------------
# Step 6 Map Generation Settings
# -------------------------------------------------------------------
STEP6_MAP_SETTINGS = {
    "generate_category_maps": True,  # Generate maps for all categories
    "generate_compound_maps": True,  # Generate specific compound maps
    # Specific compounds to generate maps for (expandable list)
    "compounds_to_map": [
        "Benzen",
        "Toluen",
        "Ethylbenzen",
        "Xylener",
        "Naphthalen",
        "Vinylchlorid",
        "1,1,1-Trichlorethan",
        "Tetrachlorethylen (PCE)",
        "Trichlorethylen (TCE)",
        "cis-1,2-Dichlorethylen",
    ],
    # Which river metrics to generate (all 4 for overall maps)
    "river_metrics_overall": [
        "cmix_pct_mkk",
        "cmix_absolute",
        "exceedance_ratio",
        "total_flux",
    ],
    # Which river metric to use for category/compound maps (default: Cmix % of MKK)
    "river_metric_filtered": "cmix_pct_mkk",
}

# -------------------------------------------------------------------
# Input Data Column Mappings
# -------------------------------------------------------------------
# Configure column names for external input files to adapt workflow to different datasets
#
# Usage: Access via COLUMN_MAPPINGS['source_file']['column_purpose']
# Example: gvfk_col = COLUMN_MAPPINGS['grundvand']['gvfk_id']

COLUMN_MAPPINGS = {
    # GVFK (Groundwater aquifer) shapefile
    'grundvand': {
        'gvfk_id': 'Navn',              # GVFK unique identifier column
    },

    # River network shapefile
    'rivers': {
        'river_id': 'ov_id',            # River segment unique ID
        'river_name': 'ov_navn',        # River segment name (optional, for display)
        'gvfk_id': 'GVForekom',         # GVFK name associated with river
        'contact': 'Kontakt',           # Contact indicator column (1 = has contact)
        'length': 'Shape_Leng',         # River segment length
    },

    # V1/V2 contamination CSV files
    'contamination_csv': {
        'site_id': 'Lokalitetsnr',      # Site unique identifier
        'gvfk_id': 'Navn',              # GVFK name
        'substances': 'Lokalitetensstoffer',  # Contaminating substances (semicolon-separated)
        'branch': 'Lokalitetensbranche',      # Industry/branch classification
        'activity': 'Lokalitetensaktivitet',  # Activity type
        'site_name': 'Lokalitetsnavn',        # Site name (optional)
        'status': 'Lokalitetetsforureningsstatus',  # Contamination status
        'region': 'Regionsnavn',              # Region name (optional)
        'municipality': 'Kommunenavn',        # Municipality name (optional)
    },

    # V1/V2 site geometry shapefiles
    'contamination_shp': {
        'site_id': 'Lokalitet_',        # Site identifier (note trailing underscore in Danish data!)
    },

    # GVFK to DK-model layer mapping CSV
    'gvfk_layer_mapping': {
        'gvfk_id': 'GVForekom',         # GVFK identifier
        'model_layer': 'DK-modellag',   # DK-model aquifer layer (e.g., 'ks3', 'ks4')
    },

    # River flow Q-points shapefile
    'flow_points': {
        'river_id': 'ov_id',            # River segment ID (links to rivers)
        'flow_mean': 'mean',            # Mean flow (m³/s)
        'flow_q90': 'Q90',              # Q90 flow (m³/s)
        'flow_q95': 'Q95',              # Q95 flow (m³/s) - low flow scenario
    },
}

# -------------------------------------------------------------------
# Input data paths
# -------------------------------------------------------------------
GRUNDVAND_PATH = SHAPE_DIR / "VP3Genbesøg_grundvand_geometri.shp"
RIVERS_PATH = SHAPE_DIR / "Rivers_gvf_rev20230825_kontakt.shp"
V1_CSV_PATH = DATA_DIR / "v1_gvfk_forurening.csv"
V2_CSV_PATH = DATA_DIR / "v2_gvfk_forurening.csv"
V1_SHP_PATH = SHAPE_DIR / "V1FLADER.shp"
V2_SHP_PATH = SHAPE_DIR / "V2FLADER.shp"

# Tilstandsvurdering specific inputs (optional - for advanced analysis)
GVFK_LAYER_MAPPING_PATH = DATA_DIR / "vp3_h1_grundvandsforekomster_VP3Genbesøg.csv"
GVD_RASTER_DIR = DATA_DIR / "dkm2019_vp3_GVD"
GVFK_AREA_VOLUME_PATH = DATA_DIR / "volumen areal_genbesøg.csv"
RIVER_FLOW_POINTS_PATH = (
    DATA_DIR
    / "dkm2019_vp3_qpunkter_inklq95"
    / "dkm_qpoints_gvf_rev20230825_kontakt_inklQ95.shp"
)

# Cache files for repeated spatial operations
V1_DISSOLVED_CACHE = CACHE_DIR / "v1_dissolved_geometries.shp"
V2_DISSOLVED_CACHE = CACHE_DIR / "v2_dissolved_geometries.shp"

# -------------------------------------------------------------------
# Output file paths - CORE WORKFLOW (Steps 1-6)
# -------------------------------------------------------------------
CORE_OUTPUTS = {
    # Step 2: GVFKs with river contact
    "step2_river_gvfk": STEP2_DATA_DIR / "step2_gvfk_with_rivers.shp",
    # Step 3: V1/V2 contamination sites
    "step3_v1v2_sites": STEP3_DATA_DIR / "step3_v1v2_sites.shp",
    "step3_gvfk_polygons": STEP3_DATA_DIR / "step3_gvfk_with_v1v2.shp",
    # Step 4: Distance calculations
    "step4_final_distances_for_risk_assessment": STEP4_DATA_DIR
    / "step4_final_distances.csv",
    "step4_valid_distances": STEP4_DATA_DIR / "step4_valid_distances.csv",
    "unique_lokalitet_distances": STEP4_DATA_DIR / "unique_lokalitet_distances.csv",
    "unique_lokalitet_distances_shp": STEP4_DATA_DIR / "unique_lokalitet_distances.shp",
    # Step 5a: General assessment (500m universal threshold)
    "step5_high_risk_sites": STEP5_DATA_DIR
    / f"step5_high_risk_sites_{WORKFLOW_SETTINGS['risk_threshold_m']}m.csv",
    "step5_gvfk_high_risk": STEP5_DATA_DIR
    / f"step5_gvfk_high_risk_{WORKFLOW_SETTINGS['risk_threshold_m']}m.shp",
    # Step 5b: Compound-specific assessment
    "step5_compound_detailed_combinations": STEP5_DATA_DIR
    / "step5_compound_detailed_combinations.csv",
    "step5_compound_specific_sites": STEP5_DATA_DIR / "step5_compound_specific_sites.csv",
    "step5_compound_gvfk_high_risk": STEP5_DATA_DIR / "step5_compound_gvfk_high_risk.shp",
    # Step 5: Sites without substance data (parked for later analysis)
    "step5_unknown_substance_sites": STEP5_DATA_DIR / "step5_unknown_substance_sites.csv",
    # Step 6: Tilstandsvurdering outputs
    "step6_flux_site_segment": STEP6_DATA_DIR / "step6_flux_site_segment.csv",
    "step6_cmix_results": STEP6_DATA_DIR / "step6_cmix_results.csv",
    "step6_segment_summary": STEP6_DATA_DIR / "step6_segment_summary.csv",
    "step6_site_mkk_exceedances": STEP6_DATA_DIR / "step6_sites_mkk_exceedance.csv",
    "step6_gvfk_mkk_exceedances": STEP6_DATA_DIR / "step6_gvfk_mkk_exceedance.csv",
    "step6_filtering_audit": STEP6_DATA_DIR / "step6_filtering_audit_detailed.csv",
    # Workflow summary
    "workflow_summary": WORKFLOW_SUMMARY_DIR / "workflow_summary.csv",
    "interactive_distance_map": WORKFLOW_SUMMARY_DIR / "interactive_distance_map.html",
}

# -------------------------------------------------------------------
# Output file paths - OPTIONAL ANALYSIS
# -------------------------------------------------------------------
# These files are created by optional analysis modules in risikovurdering/optional_analysis/
# and are not part of the core workflow. See optional_analysis/ folder for details.
OPTIONAL_OUTPUTS = {
    # Step 5: Additional summary files (optional)
    "step5_gvfk_risk_summary": STEP5_DATA_DIR / "step5_gvfk_risk_summary.csv",
    "step5_category_summary": STEP5_DATA_DIR / "step5_category_summary.csv",
    "step5_category_substance_summary": STEP5_DATA_DIR
    / "step5_category_substance_summary.csv",
    "step5_category_flags": STEP5_DATA_DIR / "step5_category_flags.csv",
    "step5_multi_threshold_analysis": STEP5_DATA_DIR
    / "step5_multi_threshold_analysis.csv",
    "step5_category_distance_statistics": STEP5_DATA_DIR
    / "step5_category_distance_statistics.csv",
    "step5_threshold_effectiveness": STEP5_DATA_DIR / "step5_threshold_effectiveness.csv",
    "step5_compound_catalog": STEP5_DATA_DIR / "step5_compound_catalog.csv",
}

# Combined dictionary for get_output_path() compatibility
OUTPUT_FILES = {**CORE_OUTPUTS, **OPTIONAL_OUTPUTS}


# -------------------------------------------------------------------
# Helper utilities
# -------------------------------------------------------------------
def _ensure_directory(path: Path) -> None:
    """Ensure parent directory exists for a file path."""
    Path(path).parent.mkdir(parents=True, exist_ok=True)


def ensure_results_directory() -> None:
    """Create the results directory tree if it does not already exist."""
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)


def ensure_cache_directory() -> None:
    """Create the cache directory if it does not already exist."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)


def get_output_path(file_key: str, threshold_m: int | None = None) -> Path:
    """
    Return the full path for a configured output file.

    Args:
        file_key: Key from OUTPUT_FILES dictionary
        threshold_m: Optional threshold value for dynamic filenames

    Returns:
        Path object for the output file

    Raises:
        KeyError: If file_key is not found in OUTPUT_FILES
    """
    if file_key not in OUTPUT_FILES:
        raise KeyError(
            f"Unknown file key: {file_key}. Available keys: {', '.join(OUTPUT_FILES.keys())}"
        )

    path = OUTPUT_FILES[file_key]

    if threshold_m is not None and "{threshold}" in str(path):
        path = Path(str(path).format(threshold=threshold_m))

    _ensure_directory(path)
    return Path(path)


def get_visualization_path(*parts: str) -> Path:
    """
    Return (and create) a folder for visualizations organized by step.

    Args:
        *parts: Path components to join (e.g., 'step5', 'category_maps')
                First part should be step identifier (step2, step3, step4, step5, step6, workflow_summary)

    Returns:
        Path object for the visualization directory

    Examples:
        get_visualization_path('step5') → Resultater/step5_risk_assessment/figures/
        get_visualization_path('step5', 'maps') → Resultater/step5_risk_assessment/figures/maps/
        get_visualization_path('step6', 'combined') → Resultater/step6_tilstandsvurdering/figures/combined/
    """
    if len(parts) == 1 and isinstance(parts[0], str) and "/" in parts[0]:
        pieces = [segment for segment in parts[0].split("/") if segment]
    else:
        pieces = [str(part) for part in parts if part]

    if not pieces:
        # Default to legacy FIGURES_DIR if no path specified
        viz_path = FIGURES_DIR
    elif pieces[0] == "step2":
        viz_path = STEP2_FIGURES_DIR.joinpath(*pieces[1:]) if len(pieces) > 1 else STEP2_FIGURES_DIR
    elif pieces[0] == "step3":
        viz_path = STEP3_FIGURES_DIR.joinpath(*pieces[1:]) if len(pieces) > 1 else STEP3_FIGURES_DIR
    elif pieces[0] == "step4":
        viz_path = STEP4_FIGURES_DIR.joinpath(*pieces[1:]) if len(pieces) > 1 else STEP4_FIGURES_DIR
    elif pieces[0] == "step5":
        viz_path = STEP5_FIGURES_DIR.joinpath(*pieces[1:]) if len(pieces) > 1 else STEP5_FIGURES_DIR
    elif pieces[0] == "step6":
        viz_path = STEP6_FIGURES_DIR.joinpath(*pieces[1:]) if len(pieces) > 1 else STEP6_FIGURES_DIR
    elif pieces[0] == "workflow_summary":
        viz_path = WORKFLOW_SUMMARY_DIR.joinpath(*pieces[1:]) if len(pieces) > 1 else WORKFLOW_SUMMARY_DIR
    else:
        # Legacy path for unrecognized step identifiers
        viz_path = FIGURES_DIR.joinpath(*pieces)

    viz_path.mkdir(parents=True, exist_ok=True)
    return viz_path


def validate_input_files() -> bool:
    """
    Check that all critical input datasets are present.

    Returns:
        True if all required files exist, False otherwise
    """
    required_files = [
        GRUNDVAND_PATH,
        RIVERS_PATH,
        V1_CSV_PATH,
        V2_CSV_PATH,
        V1_SHP_PATH,
        V2_SHP_PATH,
    ]

    missing_files = [path for path in required_files if not Path(path).exists()]
    if missing_files:
        print("ERROR: Missing required input files:")
        for path in missing_files:
            print(f"  - {path}")
        print("\nPlease ensure all input data files are in the correct location.")
        print("See README_WORKFLOW.md for data requirements.")
        return False
    return True


def is_cache_valid(cache_path: Path, source_path: Path) -> bool:
    """
    Return True if the cache file is newer than the source file.

    Args:
        cache_path: Path to cache file
        source_path: Path to source file

    Returns:
        True if cache is valid (exists and newer than source)
    """
    cache_path = Path(cache_path)
    source_path = Path(source_path)

    if not cache_path.exists() or not source_path.exists():
        return False

    return cache_path.stat().st_mtime > source_path.stat().st_mtime


# -------------------------------------------------------------------
# Step 6: Concentration and MKK Configuration
# -------------------------------------------------------------------
# Standard concentrations (µg/L) from Delprojekt 3, Bilag D3
# Hierarchy: Activity+Substance → Losseplads+Substance → Compound → Category Scenario

STANDARD_CONCENTRATIONS = {
    # Level 1/2: Activity/Branch + Substance overrides (90% fractiles from D3)
    "activity_substance": {
        "Servicestationer_Benzen": 8000.0,  # D3 Table 3
        "Benzin og olie, salg af_Benzen": 8000.0,  # Synonym
        "Villaolietank_Olie C10-C25": 6000.0,  # D3 Table 4
        "Renserier_Trichlorethylen": 42000.0,  # D3 Table 6
        "Renserier_Tetrachlorethylen": 2500.0,  # Placeholder (not in D3)
        "Maskinindustri_Toluen": 1200.0,  # Placeholder
    },
    # Level 3: Losseplads context + specific overrides
    "losseplads": {
        "Benzen": 17.0,  # D3 Table 3
        "Olie C10-C25": 2500.0,  # D3 Table 4
        "Trichlorethylen": 2.2,  # D3 Table 6
        "Phenol": 6.4,  # D3 Table 8
        "Arsen": 25.0,  # D3 Table 16
        "COD": 380000.0,  # D3 Table 17
        # Category fallbacks for landfill context
        "BTXER": 3000.0,
        "PAH_FORBINDELSER": 2500.0,
        "UORGANISKE_FORBINDELSER": 1800.0,
        "PHENOLER": 1500.0,
        "KLOREREDE_OPLØSNINGSMIDLER": 2800.0,
        "PESTICIDER": 1000.0,
    },
    # Level 4: Specific compound defaults (general worst-case)
    "compound": {
        "Olie C10-C25": 3000.0,  # D3 Table 4
        "Benzen": 400.0,  # D3 Table 3
        "1,1,1-Trichlorethan": 100.0,  # D3 Table 5
        "Trichlorethylen": 42000.0,  # D3 Table 6
        "Chloroform": 100.0,  # D3 Table 7
        "Chlorbenzen": 100.0,  # D3 Table 12
        "Phenol": 1300.0,  # D3 Table 8
        "4-Nonylphenol": 9.0,  # D3 Table 9
        "2,6-dichlorphenol": 10000.0,  # D3 Table 11
        "MTBE": 50000.0,  # D3 Table 10
        "Fluoranthen": 30.0,  # D3 Table 13
        "Mechlorprop": 1000.0,  # D3 Table 14
        "Atrazin": 12.0,  # D3 Table 15
        "Arsen": 100.0,  # D3 Table 16
        "Cyanid": 3500.0,  # D3 Table 18
        "COD": 380000.0,  # D3 Table 17
    },
    # Level 5: Category scenarios (one per modelstof)
    "category": {
        # BTEX / Oil (2 scenarios)
        "BTXER__via_Benzen": 400.0,
        "BTXER__via_Olie C10-C25": 3000.0,
        # Chlorinated solvents (4 scenarios)
        "KLOREREDE_OPLØSNINGSMIDLER__via_1,1,1-Trichlorethan": 100.0,
        "KLOREREDE_OPLØSNINGSMIDLER__via_Trichlorethylen": 42000.0,
        "KLOREREDE_OPLØSNINGSMIDLER__via_Chloroform": 100.0,
        "KLOREREDE_OPLØSNINGSMIDLER__via_Chlorbenzen": 100.0,
        # Synonym category (KLOREDE_KULBRINTER)
        "KLOREDE_KULBRINTER__via_1,1,1-Trichlorethan": 100.0,
        "KLOREDE_KULBRINTER__via_Trichlorethylen": 42000.0,
        "KLOREDE_KULBRINTER__via_Chloroform": 100.0,
        "KLOREDE_KULBRINTER__via_Chlorbenzen": 100.0,
        # Polar compounds (2 scenarios)
        "POLARE_FORBINDELSER__via_MTBE": 50000.0,
        "POLARE_FORBINDELSER__via_4-Nonylphenol": 9.0,
        # Phenols (1 scenario)
        "PHENOLER__via_Phenol": 1300.0,
        # Chlorinated phenols (1 scenario)
        "KLOREREDE_PHENOLER__via_2,6-dichlorphenol": 10000.0,
        # Pesticides (2 scenarios)
        "PESTICIDER__via_Mechlorprop": 1000.0,
        "PESTICIDER__via_Atrazin": 12.0,
        # PAH (1 scenario)
        "PAH_FORBINDELSER__via_Fluoranthen": 30.0,
        # Inorganics (2 scenarios)
        "UORGANISKE_FORBINDELSER__via_Arsen": 100.0,
        "UORGANISKE_FORBINDELSER__via_Cyanid": 3500.0,
        # Categories without modelstof basis (use -1 to indicate no valid concentration)
        "LOSSEPLADS": -1,  # Only use specific losseplads overrides (e.g., losseplads["BTXER"])
        "ANDRE": -1,  # No valid concentration available
        "PFAS": -1,  # Not from D3 - requires validation
    },
}

# Category to modelstof scenario mapping
CATEGORY_SCENARIOS = {
    "BTXER": ["Benzen", "Olie C10-C25"],
    "KLOREREDE_OPLØSNINGSMIDLER": [
        "1,1,1-Trichlorethan",
        "Trichlorethylen",
        "Chloroform",
        "Chlorbenzen",
    ],
    "KLOREDE_KULBRINTER": [
        "1,1,1-Trichlorethan",
        "Trichlorethylen",
        "Chloroform",
        "Chlorbenzen",
    ],
    "POLARE_FORBINDELSER": ["MTBE", "4-Nonylphenol"],
    "PHENOLER": ["Phenol"],
    "KLOREREDE_PHENOLER": ["2,6-dichlorphenol"],
    "PESTICIDER": ["Mechlorprop", "Atrazin"],
    "PAH_FORBINDELSER": ["Fluoranthen"],
    "UORGANISKE_FORBINDELSER": ["Arsen", "Cyanid"],
    "LOSSEPLADS": [],
    "ANDRE": [],
    "PFAS": [],
}

# The 16 modelstoffer from Delprojekt 3 (eligible for substance-specific MKK)
MODELSTOFFER = {
    "Olie C10-C25",
    "Benzen",
    "1,1,1-Trichlorethan",
    "Trichlorethylen",
    "Chloroform",
    "Chlorbenzen",
    "Phenol",
    "4-Nonylphenol",
    "2,6-dichlorphenol",
    "MTBE",
    "Fluoranthen",
    "Mechlorprop",
    "Atrazin",
    "Arsen",
    "Cyanid",
    "COD",
}

# MKK thresholds (µg/L) - AA-EQS for freshwater
# Source: BEK nr. 1022 af 25/08/2010 (Bilag 2 & 3) and BEK nr. 796/2023
# Only modelstoffer get substance-specific MKK; others use category MKK
MKK_THRESHOLDS = {
    # Modelstoffer (substance-specific)
    "Benzen": 10.0,
    "Olie C10-C25": None,  # No EQS for fraction
    "1,1,1-Trichlorethan": 21.0,
    "Trichlorethylen": 10.0,
    "Chloroform": 2.5,
    "Chlorbenzen": None,
    "Phenol": 7.7,
    "4-Nonylphenol": 0.3,
    "2,6-dichlorphenol": 3.4,
    "MTBE": 10.0,
    "Fluoranthen": 0.0063,
    "Mechlorprop": 18.0,
    "Atrazin": 0.6,
    "Arsen": 4.3,
    "Cyanid": 10.0,
    "COD": 1000.0,
    # Categories (lowest EQS in group)
    "BTXER": 10.0,
    "PAH_FORBINDELSER": 0.1,
    "PHENOLER": 0.3,
    "KLOREREDE_PHENOLER": 3.4,
    "POLARE_FORBINDELSER": 10.0,
    "KLOREREDE_OPLØSNINGSMIDLER": 2.5,
    "KLOREDE_KULBRINTER": 2.5,
    "PESTICIDER": 0.6,
    "UORGANISKE_FORBINDELSER": 4.3,
    "PFAS": 0.0044,  # BEK 796/2023
    "LOSSEPLADS": 10.0,
    "ANDRE": 10.0,
}

# Flow scenario column mapping
# Using only Q95 (low flow scenario) for simplified analysis
FLOW_SCENARIO_COLUMNS = {
    "Q95": "Q95",
}

# Seconds per year (for flux calculations)
SECONDS_PER_YEAR = 365.25 * 24 * 60 * 60

# -------------------------------------------------------------------
# Module exports
# -------------------------------------------------------------------
__all__ = [
    # Directories
    "BASE_DIR",
    "PROJECT_ROOT",
    "DATA_DIR",
    "SHAPE_DIR",
    "RESULTS_DIR",
    "FIGURES_DIR",
    "CACHE_DIR",
    # Input files
    "GRUNDVAND_PATH",
    "RIVERS_PATH",
    "V1_CSV_PATH",
    "V2_CSV_PATH",
    "V1_SHP_PATH",
    "V2_SHP_PATH",
    "GVFK_LAYER_MAPPING_PATH",
    "GVD_RASTER_DIR",
    "GVFK_AREA_VOLUME_PATH",
    "RIVER_FLOW_POINTS_PATH",
    # Cache files
    "V1_DISSOLVED_CACHE",
    "V2_DISSOLVED_CACHE",
    # Settings
    "WORKFLOW_SETTINGS",
    "STEP6_MAP_SETTINGS",
    # Output dictionaries
    "CORE_OUTPUTS",
    "OPTIONAL_OUTPUTS",
    "OUTPUT_FILES",
    # Column mappings
    "COLUMN_MAPPINGS",
    # Helper functions
    "ensure_results_directory",
    "ensure_cache_directory",
    "get_output_path",
    "get_visualization_path",
    "validate_input_files",
    "is_cache_valid",
    # Step 6 constants
    "STANDARD_CONCENTRATIONS",
    "CATEGORY_SCENARIOS",
    "MODELSTOFFER",
    "MKK_THRESHOLDS",
    "FLOW_SCENARIO_COLUMNS",
    "SECONDS_PER_YEAR",
]
