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

    # Initialize results storage
    results = {}

    # STEP 1
    gvf, total_gvfk = run_step1()
    if gvf is None:
        print("✗ Step 1 failed - cannot proceed")
        return False
    results["step1"] = {"gvf": gvf, "total_gvfk": total_gvfk}

    # STEP 2
    rivers_gvfk, river_contact_count, gvf_with_rivers = run_step2()
    if not rivers_gvfk:
        print("✗ Step 2 failed - no GVFKs with river contact")
        return False
    results["step2"] = {
        "rivers_gvfk": rivers_gvfk,
        "river_contact_count": river_contact_count,
        "gvf_with_rivers": gvf_with_rivers,
    }

    # STEP 3
    gvfk_with_v1v2_names, v1v2_sites = run_step3(rivers_gvfk)
    if v1v2_sites.empty:
        print("✗ Step 3 failed - no V1/V2 sites found")
        return False
    results["step3"] = {
        "gvfk_with_v1v2_names": gvfk_with_v1v2_names,
        "v1v2_sites": v1v2_sites,
    }

    # STEP 3b: Infiltration filter (filter sites in upward flow zones)
    v1v2_sites_filtered = run_step3b(v1v2_sites)
    if v1v2_sites_filtered.empty:
        print("✗ Step 3b failed - all sites filtered (no downward flow sites)")
        return False
    results["step3b"] = {
        "v1v2_sites_filtered": v1v2_sites_filtered,
    }

    # STEP 4 - Uses filtered sites from Step 3b
    from risikovurdering.step4_distances import run_step4
    distance_results = run_step4(v1v2_sites_filtered)
    if distance_results is None:
        print("✗ Step 4 failed - distance calculation unsuccessful")
        return False
    # Store all results from step 4 (includes distance_results, unique_distances for plotting)
    results["step4"] = distance_results

    # STEP 5
    step5_results = run_step5()

    if not step5_results["success"]:
        print(f"ERROR: Step 5 failed")
        results["step5"] = {
            "general_high_risk_sites": None,
            "general_analysis": None,
            "compound_high_risk_sites": None,
            "compound_analysis": None,
            "high_risk_gvfk_count": 0,
        }
    else:
        # Extract data from step5 results
        general_results = step5_results["general_results"]
        compound_results = step5_results["compound_results"]

        general_sites, general_analysis = general_results
        compound_sites, compound_analysis = compound_results

        # Use general results for summary statistics
        high_risk_sites = general_sites if general_sites is not None else pd.DataFrame()

        # Extract GVFK count from general results
        high_risk_gvfk_count = 0
        if not high_risk_sites.empty:
            if "All_Affected_GVFKs" in high_risk_sites.columns:
                all_gvfks = set()
                for gvfk_list in high_risk_sites["All_Affected_GVFKs"].dropna():
                    if pd.isna(gvfk_list) or gvfk_list == "":
                        continue
                    gvfks = [
                        gvfk.strip()
                        for gvfk in str(gvfk_list).split(";")
                        if gvfk.strip()
                    ]
                    all_gvfks.update(gvfks)
                high_risk_gvfk_count = len(all_gvfks)
            elif "Closest_GVFK" in high_risk_sites.columns:
                high_risk_gvfk_count = high_risk_sites["Closest_GVFK"].nunique()

        results["step5"] = {
            "general_high_risk_sites": general_sites,
            "general_analysis": general_analysis,
            "compound_high_risk_sites": compound_sites,
            "compound_analysis": compound_analysis,
            "high_risk_gvfk_count": high_risk_gvfk_count,
            "success": True,
            # Backward compatibility
            "high_risk_sites": high_risk_sites,
            "risk_analysis": general_analysis,
        }

    # Step 5c: Infiltration-Based Filtering
    try:
        from risikovurdering.step5c_infiltration_filter import run_step5c_filtering
        filtered_results, removed_sites = run_step5c_filtering(verbose=True)

        if not filtered_results.empty:
            results["step5c"] = {
                "filtered_results": filtered_results,
                "removed_sites": removed_sites,
                "filtered_sites_count": filtered_results["Lokalitet_ID"].nunique(),
                "filtered_gvfk_count": filtered_results["GVFK"].nunique(),
                "removed_sites_count": removed_sites["Lokalitet_ID"].nunique() if not removed_sites.empty else 0,
                "success": True,
            }
        else:
            results["step5c"] = {"success": False, "error": "No sites remaining after filtering"}
    except Exception as e:
        print(f"✗ Step 5c failed: {e}")
        results["step5c"] = {"success": False, "error": str(e)}

    # Step 6: Tilstandsvurdering (State Assessment)
    try:
        step6_results = run_step6()
        results["step6"] = step6_results
    except Exception as e:
        print(f"✗ Step 6 failed: {e}")
        results["step6"] = {"success": False, "error": str(e)}

    # Create visualizations if available
    create_visualizations_if_available(results)

    # Print final consolidated summary
    print_final_summary(results)

    return True

def _safe_nunique(df, col_name):
    """Safely get nunique with error handling."""
    try:
        if df is not None and not df.empty and col_name in df.columns:
            return df[col_name].nunique()
    except:
        pass
    return 0


def print_final_summary(results):
    """Print consolidated workflow summary with key metrics from all steps."""
    print("\n" + "=" * 80)
    print("WORKFLOW SUMMARY")
    print("=" * 80)

    # Step 1-2
    total_gvfk = results.get("step1", {}).get("total_gvfk", 0)
    river_gvfk = results.get("step2", {}).get("river_contact_count", 0)

    # Step 3 - try both possible column names (Lokalitetsnr is from shapefile, Lokalitet_ID is created by step4)
    v1v2_sites = results.get("step3", {}).get("v1v2_sites")
    sites_count = _safe_nunique(v1v2_sites, "Lokalitetsnr") or _safe_nunique(v1v2_sites, "Lokalitet_ID")
    gvfk_with_sites = len(results.get("step3", {}).get("gvfk_with_v1v2_names", []))

    # Step 5
    step5 = results.get("step5", {})
    general_sites = step5.get("general_high_risk_sites")
    compound_sites = step5.get("compound_high_risk_sites")
    general_sites_count = _safe_nunique(general_sites, "Lokalitet_ID")
    general_gvfk_count = _safe_nunique(general_sites, "GVFK")
    compound_sites_count = _safe_nunique(compound_sites, "Lokalitet_ID")
    compound_gvfk_count = _safe_nunique(compound_sites, "GVFK")

    # Step 5c
    step5c = results.get("step5c", {})
    filtered_sites_count = step5c.get("filtered_sites_count", 0) if step5c.get("success") else compound_sites_count
    removed_sites_count = step5c.get("removed_sites_count", 0)

    # Step 6
    step6 = results.get("step6", {})
    exc_sites = exc_gvfk = exc_segments = max_exc = 0
    if step6.get("success"):
        site_exc = step6.get("site_exceedances")
        gvfk_exc = step6.get("gvfk_exceedances")
        segment_summary = step6.get("segment_summary")

        exc_sites = _safe_nunique(site_exc, "Lokalitet_ID")
        exc_gvfk = _safe_nunique(gvfk_exc, "GVFK")
        if segment_summary is not None and not segment_summary.empty:
            try:
                if "Max_Exceedance_Ratio" in segment_summary.columns:
                    exc_segments = int((segment_summary["Max_Exceedance_Ratio"] > 1).sum())
                    max_exc = float(segment_summary["Max_Exceedance_Ratio"].max())
            except Exception as e:
                # Gracefully handle any calculation errors
                pass

    # Print summary
    print(f"\nStep 1: Total GVFKs in Denmark: {total_gvfk:,}")
    print(f"Step 2: GVFKs with river contact: {river_gvfk:,} ({river_gvfk/total_gvfk*100:.1f}%)" if total_gvfk > 0 else f"Step 2: GVFKs with river contact: {river_gvfk:,}")
    print(f"Step 3: GVFKs with contaminated sites: {gvfk_with_sites:,} ({gvfk_with_sites/river_gvfk*100:.1f}% of river-contact)" if river_gvfk > 0 else f"Step 3: GVFKs with contaminated sites: {gvfk_with_sites:,}")
    print(f"        Contaminated sites identified: {sites_count:,}")
    print(f"Step 5a: High-risk sites (≤500m): {general_sites_count:,} sites in {general_gvfk_count:,} GVFKs")
    print(f"Step 5b: Compound-specific risk: {compound_sites_count:,} sites in {compound_gvfk_count:,} GVFKs")
    if step5c.get("success"):
        print(f"Step 5c: After infiltration filter: {filtered_sites_count:,} sites ({removed_sites_count:,} removed - upward flow)")

    # Step 6 - always show if completed, even if no exceedances
    if step6.get("success"):
        print(f"Step 6: MKK exceedances: {exc_sites:,} sites in {exc_gvfk:,} GVFKs affecting {exc_segments:,} river segments")
        if max_exc > 1:
            print(f"        Worst exceedance: {max_exc:,.0f}x MKK")

    print("\n" + "=" * 80)
    print("WORKFLOW COMPLETED")
    print("=" * 80)
    print(f"\nResults saved to: Resultater/\n")


def create_visualizations_if_available(results):
    """
    Create core workflow visualizations.
    
    Calls:
    - risikovurdering_plots: Step 4 distance histograms, Step 5 category plots
    - workflow_summary_plots: GVFK and sites progression charts (all steps)
    
    Optional (not called by default):
    - risikovurdering/optional_analysis/step5_branch_analysis.py: Branch analysis for sites without substances
    """
    # Create Step 4-5 risikovurdering plots
    try:
        from risikovurdering.risikovurdering_plots import create_all_risikovurdering_plots
        create_all_risikovurdering_plots()
    except Exception as e:
        print(f"  ⚠ Risikovurdering plots failed: {e}")

    # Create workflow summary plots (progression through all steps)
    try:
        from workflow_summary_plots import create_workflow_summary_plots
        create_workflow_summary_plots()
    except Exception as e:
        print(f"  ⚠ Workflow summary plots failed: {e}")





if __name__ == "__main__":
    try:
        success = main()
        if not success:
            print("\n✗ Workflow failed. Check error messages above.")
    except Exception as e:
        print(f"\n✗ Workflow failed with error: {e}")
        import traceback

        traceback.print_exc()
