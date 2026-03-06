"""
Main workflow orchestrator for groundwater contamination risk assessment.

COMPLETE WORKFLOW (Steps 1-6)
==============================

This is the complete workflow for assessing groundwater contamination risk
from contaminated sites to groundwater aquifers (GVFKs) and computing impact
on river water quality.

WORKFLOW STEPS:
---------------
RISIKOVURDERING (Risk Assessment - Steps 1-5):
1. Load all groundwater aquifers (GVFKs) in Denmark
2. Filter to GVFKs with contact to targeted rivers (Kontakt = 1)
3. Identify contaminated sites (V1/V2) within these GVFKs
4. Calculate distances from each site to nearest river segment
5. Risk assessment:
   a) General assessment: Universal 500m threshold
   b) Compound-specific: Literature-based variable thresholds per contamination category

TILSTANDSVURDERING (State Assessment - Step 6):
6. Compute pollution flux from sites to river segments and calculate mixing
   concentrations (Cmix) under different flow scenarios, with MKK threshold exceedances

CORE OUTPUTS:
-------------
- CSV files: Risk assessment results, site-GVFK combinations, flux calculations, Cmix results
- Shapefiles: High-risk GVFKs for GIS visualization
- Plots: Verification plots, category analysis, exceedance maps, interactive visualizations

OPTIONAL ANALYSIS:
------------------
Extended analysis tools available in risikovurdering/optional_analysis/
Validation tools available in tools/
See that folder's README for details on branch analysis, comprehensive visualizations, etc.

CONFIGURATION:
--------------
- Settings: Edit WORKFLOW_SETTINGS in config.py to modify risk thresholds and GVD cap
- Paths: config.py contains all data file locations
- Requirements: Install dependencies with 'pip install -r requirements.txt'

USAGE:
------
    python main_workflow.py

Expected runtime: ~10-20 minutes depending on data size.
"""

import warnings
from shapely.errors import ShapelyDeprecationWarning
from config import validate_input_files, get_output_path, WORKFLOW_SETTINGS, TOTAL_GVFK_DENMARK

# Import step modules
from risikovurdering.step1_all_gvfk import run_step1
from risikovurdering.step2_river_contact import run_step2
from risikovurdering.step3_v1v2_sites import run_step3
from risikovurdering.step3b_infiltration_filter import run_step3b
from risikovurdering.step4_distances import run_step4
from risikovurdering.step5_risk_assessment import run_step5
from tilstandsvurdering.step6_tilstandsvurdering import run_step6

# Suppress shapely deprecation warnings
warnings.filterwarnings("ignore", category=ShapelyDeprecationWarning)


def main():
    """
    Run the complete groundwater risk and state assessment workflow (Steps 1-6).

    This function orchestrates all steps sequentially:
    - Step 1: Count total GVFKs in Denmark
    - Step 2: Filter to GVFKs with river contact (Kontakt = 1)
    - Step 3: Identify V1/V2 contaminated sites in these GVFKs
    - Step 4: Calculate site-to-river distances
    - Step 5: Risk assessment (general 500m + compound-specific)
    - Step 6: Tilstandsvurdering (flux calculation, Cmix, MKK exceedances)
    - Visualizations: Create verification plots and maps

    Returns:
        bool: True if workflow completed successfully, False if critical steps failed

    Note:
        Results are saved to Resultater/ directory.
        If Step 6 fails, workflow continues with Steps 1-5 results.
    """
    print("=" * 80)
    print("GROUNDWATER CONTAMINATION ASSESSMENT - COMPLETE WORKFLOW (Steps 1-6)")
    print("=" * 80)

    # Show sampling mode if enabled, used for testing and quicker runs
    sample_fraction = WORKFLOW_SETTINGS.get('sample_fraction')
    if sample_fraction and sample_fraction < 1.0:
        print(f"\n[TESTING MODE] Using {sample_fraction*100:.0f}% sample of data")
        print("   (Set sample_fraction=1 in config.py for full production run)\n")

    # Validate input files before starting
    if not validate_input_files():
        print("\nERROR: Missing required input files - check config.py")
        return False
    print("Input files validated\n")

    # STEP 1
    gvf, total_gvfk = run_step1()
    if gvf is None:
        print("✗ Step 1 failed - cannot proceed")
        return False

    # STEP 2
    rivers_gvfk, river_contact_count, gvf_with_rivers = run_step2()
    if not rivers_gvfk:
        print("✗ Step 2 failed - no GVFKs with river contact")
        return False

    # STEP 3
    gvfk_with_v1v2_names, v1v2_sites = run_step3(rivers_gvfk)
    if v1v2_sites.empty:
        print("✗ Step 3 failed - no V1/V2 sites found")
        return False

    # STEP 3b: Infiltration filter (filter sites in upward flow zones)
    v1v2_sites_filtered = run_step3b(v1v2_sites, verbose=True)
    if v1v2_sites_filtered.empty:
        print("✗ Step 3b failed - all sites filtered (no downward flow sites)")
        return False

    # STEP 4 - Uses filtered sites from Step 3b
    distance_results = run_step4(v1v2_sites_filtered)
    if distance_results is None:
        print("✗ Step 4 failed - distance calculation unsuccessful")
        return False

    # STEP 5
    step5_results = run_step5()
    if not step5_results["success"]:
        print("ERROR: Step 5 failed")
        return False

    # Step 6: Tilstandsvurdering (State Assessment)
    try:
        run_step6()
    except Exception as e:
        print(f"✗ Step 6 failed: {e}")

    # Create visualizations
    create_visualizations_if_available()

    print("\n" + "=" * 80)
    print("WORKFLOW COMPLETED")
    print("=" * 80)
    print(f"\nResults saved to: Resultater/\n")

    return True


def create_visualizations_if_available():
    """
    Create core workflow visualizations.

    Calls:
    - risikovurdering_plots: Step 4 distance histograms, Step 5 category plots
    - workflow_summary_plots: GVFK and sites progression charts (all steps)

    Optional (not called by default):
    - risikovurdering/optional_analysis/step5_branch_analysis.py: Branch analysis for sites without substances
    """
    plot_failures = []

    # Create Step 4-5 risikovurdering plots
    try:
        from risikovurdering.risikovurdering_plots import create_all_risikovurdering_plots
        create_all_risikovurdering_plots()
    except Exception as e:
        plot_failures.append(f"Risikovurdering plots: {e}")

    # Create workflow summary plots (progression through all steps)
    try:
        from workflow_summary_plots import create_workflow_summary_plots
        create_workflow_summary_plots()
    except Exception as e:
        plot_failures.append(f"Workflow summary plots: {e}")

    # Report any failures
    if plot_failures:
        print("\n⚠️  WARNING: Some visualizations failed:")
        for failure in plot_failures:
            print(f"    - {failure}")
        print("    Results are still valid, but plots are incomplete.\n")

if __name__ == "__main__":
    try:
        success = main()
        if not success:
            print("\n✗ Workflow failed. Check error messages above.")
    except Exception as e:
        print(f"\n✗ Workflow failed with error: {e}")
        import traceback

        traceback.print_exc()
