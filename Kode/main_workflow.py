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

import pandas as pd
import os
import warnings
from shapely.errors import ShapelyDeprecationWarning
from config import validate_input_files, get_output_path

# Import step modules
from risikovurdering.step1_all_gvfk import run_step1
from risikovurdering.step2_river_contact import run_step2
from risikovurdering.step3_v1v2_sites import run_step3
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

    # STEP 4
    from risikovurdering.step4_distances import run_step4
    distance_results = run_step4(v1v2_sites)
    if distance_results is None:
        print("✗ Step 4 failed - distance calculation unsuccessful")
        return False
    results["step4"] = {"distance_results": distance_results}

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

    print("\n" + "=" * 80)
    print("WORKFLOW COMPLETED")
    print("=" * 80)
    print(f"\nResults: Resultater/")
    return True

def create_visualizations_if_available(results):
    """Create core workflow visualizations (suppressed output for clean console)."""
    try:
        from risikovurdering.optional_analysis.selected_visualizations import (
            create_distance_histogram_with_thresholds,
            create_progression_plot,
        )

        if results["step4"]["distance_results"] is not None:
            try:
                # Extract dataframes from results dictionary (in-memory)
                unique_df = results["step4"].get("unique_distances")
                all_combos_df = results["step4"].get("distance_results")
                
                # Pass dataframes directly to plotting function
                create_distance_histogram_with_thresholds(
                    unique_df=unique_df,
                    all_combinations_df=all_combos_df
                )
            except Exception as e:
                print(f"Warning: Step 4 plotting failed: {e}")
                pass

        try:
            from config import GRUNDVAND_PATH, WORKFLOW_SUMMARY_DIR
            required_files = {
                "all_gvfk": GRUNDVAND_PATH,
                "river_gvfk": get_output_path("step2_river_gvfk"),
                "v1v2_gvfk": get_output_path("step3_gvfk_polygons"),
                "high_risk_gvfk": get_output_path("step5_gvfk_high_risk"),
            }
            WORKFLOW_SUMMARY_DIR.mkdir(parents=True, exist_ok=True)
            create_progression_plot(str(WORKFLOW_SUMMARY_DIR), required_files)
        except:
            pass
    except:
        pass




if __name__ == "__main__":
    try:
        success = main()
        if success:
            print(
                "\nWorkflow completed successfully! Check the 'Resultater' directory for output files."
            )
        else:
            print("\nWorkflow failed. Check error messages above.")
    except Exception as e:
        print(f"\nWorkflow failed with error: {e}")
        import traceback

        traceback.print_exc()
