"""Core configuration for groundwater analysis workflows.

The goal is to keep file locations and shared settings in one
self-contained module. All paths are expressed with `pathlib.Path`
objects to stay explicit and cross-platform friendly.
"""

from __future__ import annotations

from pathlib import Path

# -------------------------------------------------------------------
# Project structure
# -------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent

DATA_DIR = PROJECT_ROOT / "Data"
SHAPE_DIR = DATA_DIR / "shp files"
RESULTS_DIR = PROJECT_ROOT / "Resultater"
FIGURES_DIR = RESULTS_DIR / "Figures"
CACHE_DIR = RESULTS_DIR / "cache"

# -------------------------------------------------------------------
# Input data
# -------------------------------------------------------------------
GRUNDVAND_PATH = SHAPE_DIR / "VP3Genbesøg_grundvand_geometri.shp"
RIVERS_PATH = SHAPE_DIR / "Rivers_gvf_rev20230825_kontakt.shp"
V1_CSV_PATH = DATA_DIR / "v1_gvfk_forurening.csv"
V2_CSV_PATH = DATA_DIR / "v2_gvfk_forurening.csv"
V1_SHP_PATH = SHAPE_DIR / "V1FLADER.shp"
V2_SHP_PATH = SHAPE_DIR / "V2FLADER.shp"

# Tilstandsvurdering specific inputs
GVFK_LAYER_MAPPING_PATH = DATA_DIR / "vp3_h1_grundvandsforekomster_VP3Genbesøg.csv"
GVD_RASTER_DIR = DATA_DIR / "dkm2019_vp3_GVD"
GVFK_AREA_VOLUME_PATH = DATA_DIR / "volumen areal_genbesøg.csv"

# Cache files for repeated spatial operations
V1_DISSOLVED_CACHE = CACHE_DIR / "v1_dissolved_geometries.shp"
V2_DISSOLVED_CACHE = CACHE_DIR / "v2_dissolved_geometries.shp"

# -------------------------------------------------------------------
# Workflow settings
# -------------------------------------------------------------------
WORKFLOW_SETTINGS = {
    "risk_threshold_m": 500,
    "additional_thresholds_m": [250, 500, 1000, 1500, 2000],
    "progress_interval_percent": 10,
    "contact_filter_value": 1,
    "enable_multi_threshold_analysis": False,
}

# -------------------------------------------------------------------
# Output locations
# -------------------------------------------------------------------
OUTPUT_FILES = {
    # Cross-step dependencies
    "step4_final_distances_for_risk_assessment": RESULTS_DIR / "step4_final_distances.csv",

    # Files used by visualisations or downstream steps
    "step2_river_gvfk": RESULTS_DIR / "step2_gvfk_with_rivers.shp",
    "step3_v1v2_sites": RESULTS_DIR / "step3_v1v2_sites.shp",
    "step3_gvfk_polygons": RESULTS_DIR / "step3_gvfk_with_v1v2.shp",
    "step5_gvfk_high_risk": RESULTS_DIR / f"step5_gvfk_high_risk_{WORKFLOW_SETTINGS['risk_threshold_m']}m.shp",
    "unique_lokalitet_distances": RESULTS_DIR / "unique_lokalitet_distances.csv",
    "unique_lokalitet_distances_shp": RESULTS_DIR / "unique_lokalitet_distances.shp",
    "step4_valid_distances": RESULTS_DIR / "step4_valid_distances.csv",
    "interactive_distance_map": RESULTS_DIR / "interactive_distance_map.html",

    # Step 5 core outputs
    "step5_high_risk_sites": RESULTS_DIR / f"step5_high_risk_sites_{WORKFLOW_SETTINGS['risk_threshold_m']}m.csv",
    "step5_compound_specific_sites": RESULTS_DIR / "step5_compound_specific_sites.csv",
    "step5_compound_detailed_combinations": RESULTS_DIR / "step5_compound_detailed_combinations.csv",
    "step5_unknown_substance_sites": RESULTS_DIR / "step5_unknown_substance_sites.csv",
    "step5_compound_gvfk_high_risk": RESULTS_DIR / "step5_compound_gvfk_high_risk.shp",
    "step5_gvfk_risk_summary": RESULTS_DIR / "step5_gvfk_risk_summary.csv",
    "step5_category_summary": RESULTS_DIR / "step5_category_summary.csv",
    "step5_category_substance_summary": RESULTS_DIR / "step5_category_substance_summary.csv",
    "step5_category_flags": RESULTS_DIR / "step5_category_flags.csv",
    "step5_multi_threshold_analysis": RESULTS_DIR / "step5_multi_threshold_analysis.csv",
    "step5_category_distance_statistics": RESULTS_DIR / "step5_category_distance_statistics.csv",
    "step5_threshold_effectiveness": RESULTS_DIR / "step5_threshold_effectiveness.csv",
    "step5_compound_catalog": RESULTS_DIR / "step5_compound_catalog.csv",

    # Shared summary
    "workflow_summary": RESULTS_DIR / "workflow_summary.csv",

    # Tilstandsvurdering outputs
    "step6_flux_results": RESULTS_DIR / "step6_flux_results.csv",
}

# -------------------------------------------------------------------
# Helper utilities
# -------------------------------------------------------------------
def _ensure_directory(path: Path) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)


def ensure_results_directory() -> None:
    """Create the results directory tree if it does not already exist."""
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)


def ensure_cache_directory() -> None:
    """Create the cache directory if it does not already exist."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)


def get_output_path(file_key: str, threshold_m: int | None = None) -> Path:
    """Return the full path for a configured output file."""
    if file_key not in OUTPUT_FILES:
        raise KeyError(f"Unknown file key: {file_key}")

    path = OUTPUT_FILES[file_key]

    if threshold_m is not None and "{threshold}" in str(path):
        path = Path(str(path).format(threshold=threshold_m))

    _ensure_directory(path)
    return Path(path)


def get_visualization_path(*parts: str) -> Path:
    """Return (and create) a folder inside `Resultater/Figures`."""
    if len(parts) == 1 and isinstance(parts[0], str) and "/" in parts[0]:
        pieces = [segment for segment in parts[0].split("/") if segment]
    else:
        pieces = [str(part) for part in parts if part]

    viz_path = FIGURES_DIR.joinpath(*pieces) if pieces else FIGURES_DIR
    viz_path.mkdir(parents=True, exist_ok=True)
    return viz_path


def validate_input_files() -> bool:
    """Check that all critical input datasets are present."""
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
        print("Missing input files:")
        for path in missing_files:
            print(f"  - {path}")
        return False
    return True


def is_cache_valid(cache_path: Path, source_path: Path) -> bool:
    """Return True if the cache file is newer than the source file."""
    cache_path = Path(cache_path)
    source_path = Path(source_path)

    if not cache_path.exists() or not source_path.exists():
        return False

    return cache_path.stat().st_mtime > source_path.stat().st_mtime


__all__ = [
    "BASE_DIR",
    "PROJECT_ROOT",
    "DATA_DIR",
    "SHAPE_DIR",
    "RESULTS_DIR",
    "FIGURES_DIR",
    "CACHE_DIR",
    "GRUNDVAND_PATH",
    "RIVERS_PATH",
    "V1_CSV_PATH",
    "V2_CSV_PATH",
    "V1_SHP_PATH",
    "V2_SHP_PATH",
    "GVFK_LAYER_MAPPING_PATH",
    "GVD_RASTER_DIR",
    "GVFK_AREA_VOLUME_PATH",
    "V1_DISSOLVED_CACHE",
    "V2_DISSOLVED_CACHE",
    "WORKFLOW_SETTINGS",
    "OUTPUT_FILES",
    "ensure_results_directory",
    "ensure_cache_directory",
    "get_output_path",
    "get_visualization_path",
    "validate_input_files",
    "is_cache_valid",
]
