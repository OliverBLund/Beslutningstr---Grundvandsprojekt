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
'''
TODO step6:
Check polygoner vs centroid resultaterne
Check mængden af pixels capped? Der er mange.
Check mængden af pixels zeroed.
'''
import pandas as pd
import os
import warnings
from shapely.errors import ShapelyDeprecationWarning
from config import validate_input_files, get_output_path

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

    # Show sampling mode if enabled
    from config import WORKFLOW_SETTINGS
    sample_fraction = WORKFLOW_SETTINGS.get('sample_fraction')
    if sample_fraction and sample_fraction < 1.0:
        print(f"\n⚠️  TESTING MODE: Using {sample_fraction*100:.0f}% sample of data")
        print("   (Set sample_fraction=None in config.py for full production run)\n")

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
    from risikovurdering.step4_distances import run_step4
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

    # Print final summary
    print_final_summary()

    return True


def print_final_summary():
    """Print consolidated workflow summary by reading results from files."""
    print("\n" + "=" * 80)
    print("WORKFLOW SUMMARY")
    print("=" * 80)

    import os

    # Load results from files
    step2_path = get_output_path("step2_river_gvfk")
    step3_path = get_output_path("step3_v1v2_sites")
    step5a_path = get_output_path("step5_high_risk_sites")
    step5b_path = get_output_path("step5b_compound_combinations")
    step6_site_exc_path = get_output_path("step6_site_mkk_exceedances")
    step6_gvfk_exc_path = get_output_path("step6_gvfk_mkk_exceedances")
    step6_segment_path = get_output_path("step6_segment_summary")

    # Step 1 - total GVFK is a constant
    from config import TOTAL_GVFK_DENMARK
    total_gvfk = TOTAL_GVFK_DENMARK

    # Step 2
    river_gvfk = 0
    if os.path.exists(step2_path):
        try:
            import geopandas as gpd
            gvf_rivers = gpd.read_file(step2_path)
            river_gvfk = gvf_rivers["Navn"].nunique()
        except:
            pass

    # Step 3
    sites_count = gvfk_with_sites = 0
    if os.path.exists(step3_path):
        try:
            import geopandas as gpd
            v1v2_df = gpd.read_file(step3_path)
            sites_count = v1v2_df["Lokalitet_"].nunique()
            gvfk_with_sites = v1v2_df["Navn"].nunique()
        except:
            pass

    # Step 5a and 5b
    general_sites_count = general_gvfk_count = 0
    compound_sites_count = compound_gvfk_count = 0
    if os.path.exists(step5a_path):
        try:
            general_df = pd.read_csv(step5a_path)
            general_sites_count = general_df["Lokalitet_ID"].nunique()
            general_gvfk_count = general_df["GVFK"].nunique()
        except:
            pass
    if os.path.exists(step5b_path):
        try:
            compound_df = pd.read_csv(step5b_path)
            compound_sites_count = compound_df["Lokalitet_ID"].nunique()
            compound_gvfk_count = compound_df["GVFK"].nunique()
        except:
            pass

    # Step 6
    exc_sites = exc_gvfk = exc_segments = max_exc = 0
    if os.path.exists(step6_site_exc_path):
        try:
            site_exc_df = pd.read_csv(step6_site_exc_path)
            exc_sites = site_exc_df["Lokalitet_ID"].nunique()
        except:
            pass
    if os.path.exists(step6_gvfk_exc_path):
        try:
            gvfk_exc_df = pd.read_csv(step6_gvfk_exc_path)
            exc_gvfk = gvfk_exc_df["GVFK"].nunique()
        except:
            pass
    if os.path.exists(step6_segment_path):
        try:
            segment_df = pd.read_csv(step6_segment_path)
            if "Max_Exceedance_Ratio" in segment_df.columns:
                exc_segments = int((segment_df["Max_Exceedance_Ratio"] > 1).sum())
                max_exc = float(segment_df["Max_Exceedance_Ratio"].max())
        except:
            pass

    # Print summary
    print(f"\nStep 1: Total GVFKs in Denmark: {total_gvfk:,}")
    print(f"Step 2: GVFKs with river contact: {river_gvfk:,} ({river_gvfk/total_gvfk*100:.1f}%)" if total_gvfk > 0 else f"Step 2: GVFKs with river contact: {river_gvfk:,}")
    print(f"Step 3: GVFKs with contaminated sites: {gvfk_with_sites:,} ({gvfk_with_sites/river_gvfk*100:.1f}% of river-contact)" if river_gvfk > 0 else f"Step 3: GVFKs with contaminated sites: {gvfk_with_sites:,}")
    print(f"        Contaminated sites identified: {sites_count:,}")
    print(f"Step 5a: High-risk sites (≤500m): {general_sites_count:,} sites in {general_gvfk_count:,} GVFKs")
    print(f"Step 5b: Compound-specific risk: {compound_sites_count:,} sites in {compound_gvfk_count:,} GVFKs")
    print(f"        (Step 6 summary printed above)")

    print("\n" + "=" * 80)
    print("WORKFLOW COMPLETED")
    print("=" * 80)
    print(f"\nResults saved to: Resultater/\n")


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
