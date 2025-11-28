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
- Settings: Edit SETTINGS.yaml to modify risk thresholds
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
    print("\nValidating input data files...")
    if not validate_input_files():
        print("\nERROR: Missing required input files.")
        print("Check config.py for expected file locations.")
        return False
    print("✓ All required input files found")

    # Initialize results storage
    results = {}

    print("\n" + "=" * 80)
    print("STEP 1: Load All Groundwater Aquifers (GVFKs)")
    print("=" * 80)
    gvf, total_gvfk = run_step1()
    if gvf is None:
        print("✗ Step 1 failed. Cannot proceed.")
        return False
    print(f"✓ Step 1 complete: {total_gvfk:,} total GVFKs in Denmark")
    results["step1"] = {"gvf": gvf, "total_gvfk": total_gvfk}

    print("\n" + "=" * 80)
    print("STEP 2: Filter to GVFKs with River Contact")
    print("=" * 80)
    rivers_gvfk, river_contact_count, gvf_with_rivers = run_step2()
    if not rivers_gvfk:
        print("✗ Step 2 failed or found no GVFKs with river contact.")
        return False
    print(
        f"✓ Step 2 complete: {river_contact_count:,} GVFKs with river contact ({river_contact_count / total_gvfk * 100:.1f}% of total)"
    )
    results["step2"] = {
        "rivers_gvfk": rivers_gvfk,
        "river_contact_count": river_contact_count,
        "gvf_with_rivers": gvf_with_rivers,
    }

    print("\n" + "=" * 80)
    print("STEP 3: Identify V1/V2 Contaminated Sites in GVFKs")
    print("=" * 80)
    gvfk_with_v1v2_names, v1v2_sites = run_step3(rivers_gvfk)
    if v1v2_sites.empty:
        print("✗ Step 3 failed or found no V1/V2 sites.")
        return False
    unique_sites_count = (
        v1v2_sites["Lokalitet_"].nunique()
        if "Lokalitet_" in v1v2_sites.columns
        else len(v1v2_sites)
    )
    print(
        f"✓ Step 3 complete: {unique_sites_count:,} unique contaminated sites in {len(gvfk_with_v1v2_names):,} GVFKs"
    )
    results["step3"] = {
        "gvfk_with_v1v2_names": gvfk_with_v1v2_names,
        "v1v2_sites": v1v2_sites,
    }

    print("\n" + "=" * 80)
    print("STEP 4: Calculate Distances from Sites to Rivers")
    print("=" * 80)
    from risikovurdering.step4_distances import run_step4

    distance_results = run_step4(v1v2_sites)
    if distance_results is None:
        print("✗ Step 4 failed. Distance calculation unsuccessful.")
        return False
    print(f"✓ Step 4 complete: Calculated distances for site-GVFK combinations")

    results["step4"] = {"distance_results": distance_results}

    print("\n" + "=" * 80)
    print("STEP 5: Risk Assessment")
    print("=" * 80)
    print("Running dual risk assessment:")
    print("  5a) General assessment: Universal 500m threshold")
    print("  5b) Compound-specific: Literature-based variable thresholds")
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

    # Step 6: Tilstandsvurdering (State Assessment)
    print("\n" + "=" * 80)
    print("STEP 6: Tilstandsvurdering (State Assessment)")
    print("=" * 80)
    print("Computing pollution flux to river segments and mixing concentrations (Cmix)")

    try:
        step6_results = run_step6()
        results["step6"] = step6_results
        print(f"✓ Step 6 complete: Analyzed {len(step6_results['segment_summary'])} river segments")
        print(f"  - Site flux calculations: {len(step6_results['site_flux'])}")
        print(f"  - Cmix scenarios: {len(step6_results['cmix_results'])}")
        print(f"  - MKK exceedances: {len(step6_results['site_exceedances'])} sites")
    except Exception as e:
        print(f"✗ Step 6 failed: {e}")
        print("Continuing to visualizations with Steps 1-5 results only...")
        results["step6"] = {"success": False, "error": str(e)}

    # Create visualizations if available
    print("\n" + "=" * 80)
    print("Creating Verification Visualizations")
    print("=" * 80)
    create_visualizations_if_available(results)

    print("\n" + "=" * 80)
    print("✓ WORKFLOW COMPLETED SUCCESSFULLY")
    print("=" * 80)
    print("\nResults saved to: Resultater/")
    print("  - Step-specific outputs: Resultater/step{N}_{name}/data/")
    print("  - Step-specific figures: Resultater/step{N}_{name}/figures/")
    print("  - Workflow summary: Resultater/workflow_summary/")
    print("\nFor extended analysis, see: risikovurdering/optional_analysis/")
    return True


def generate_workflow_summary(results):
    """
    Generate and save workflow summary statistics to CSV.

    Creates a summary table showing the progression of GVFKs and sites through
    each workflow step, with percentage calculations.

    Args:
        results (dict): Dictionary containing results from all workflow steps.
                       Expected keys: 'step1', 'step2', 'step3', 'step4', 'step5'

    Output:
        Saves workflow_summary.csv to Resultater/ directory

    Note:
        This is a simple numerical summary. For visualizations, see
        Resultater/Figures/workflow_gvfk_progression.png
    """
    print("Generating workflow summary...")

    # Extract key statistics
    total_gvfk = results["step1"]["total_gvfk"]
    river_contact_count = results["step2"]["river_contact_count"]
    gvfk_with_v1v2_count = len(results["step3"]["gvfk_with_v1v2_names"])

    # V1/V2 site statistics
    v1v2_sites = results["step3"]["v1v2_sites"]
    unique_sites = v1v2_sites["Lokalitet_"].nunique() if not v1v2_sites.empty else 0
    total_site_gvfk_combinations = len(v1v2_sites) if not v1v2_sites.empty else 0

    # Step 5 statistics
    high_risk_site_count = 0
    compound_high_risk_site_count = 0
    high_risk_gvfk_count = 0

    if "step5" in results:
        # General assessment results
        if results["step5"]["general_high_risk_sites"] is not None:
            high_risk_site_count = len(results["step5"]["general_high_risk_sites"])

        # Compound-specific assessment results
        if results["step5"]["compound_high_risk_sites"] is not None:
            compound_high_risk_site_count = len(
                results["step5"]["compound_high_risk_sites"]
            )

        # GVFK count (from general assessment for consistency)
        high_risk_gvfk_count = results["step5"].get("high_risk_gvfk_count", 0)

    # Distance statistics (if available) - load from corrected final distances file
    distance_stats = {}
    if results["step4"]["distance_results"] is not None:
        # Use the corrected final distances file instead of raw results to avoid duplicates
        final_distances_path = get_output_path(
            "step4_final_distances_for_risk_assessment"
        )
        if os.path.exists(final_distances_path):
            try:
                corrected_final_distances = pd.read_csv(final_distances_path)

                # Get total combinations from raw results for comparison
                distance_results = results["step4"]["distance_results"]
                valid_distances = distance_results[
                    distance_results["Distance_to_River_m"].notna()
                ]

                distance_stats = {
                    "total_combinations_with_distances": len(valid_distances),
                    "unique_sites_with_distances": len(
                        corrected_final_distances
                    ),  # Now uses deduplicated count
                    "average_final_distance_m": corrected_final_distances[
                        "Final_Distance_m"
                    ].mean(),
                    "median_final_distance_m": corrected_final_distances[
                        "Final_Distance_m"
                    ].median(),
                }
            except Exception as e:
                print(f"Warning: Could not load corrected final distances file: {e}")
                # Fallback to old method with duplicate counting
                final_distances = valid_distances[
                    valid_distances["Is_Min_Distance"] == True
                ]
                distance_stats = {
                    "total_combinations_with_distances": len(valid_distances),
                    "unique_sites_with_distances": len(final_distances),
                    "average_final_distance_m": final_distances[
                        "Distance_to_River_m"
                    ].mean()
                    if len(final_distances) > 0
                    else 0,
                    "median_final_distance_m": final_distances[
                        "Distance_to_River_m"
                    ].median()
                    if len(final_distances) > 0
                    else 0,
                }

    # Print summary to console
    print("WORKFLOW SUMMARY")
    print("=" * 60)
    print(f"Total unique groundwater aquifers (GVFK): {total_gvfk}")
    print(
        f"GVFKs in contact with targeted rivers: {river_contact_count} ({(river_contact_count / total_gvfk * 100):.1f}%)"
    )
    print(
        f"GVFKs with river contact AND V1/V2 sites: {gvfk_with_v1v2_count} ({(gvfk_with_v1v2_count / total_gvfk * 100):.1f}%)"
    )
    print(
        f"GVFKs with high-risk sites (<=500m from rivers): {high_risk_gvfk_count} ({(high_risk_gvfk_count / total_gvfk * 100):.1f}% of total, {(high_risk_gvfk_count / gvfk_with_v1v2_count * 100 if gvfk_with_v1v2_count > 0 else 0):.1f}% of V1/V2 GVFKs)"
    )

    if unique_sites > 0:
        print(f"Unique V1/V2 sites (localities): {unique_sites}")
        print(f"Total site-GVFK combinations: {total_site_gvfk_combinations}")
        print(
            f"Average GVFKs per site: {total_site_gvfk_combinations / unique_sites:.1f}"
        )

    if distance_stats:
        print(
            f"Site-GVFK combinations with distances: {distance_stats['total_combinations_with_distances']}"
        )
        print(
            f"Unique sites with final distances: {distance_stats['unique_sites_with_distances']}"
        )
        print(
            f"Average final distance per site: {distance_stats['average_final_distance_m']:.1f}m"
        )
        print(
            f"Median final distance per site: {distance_stats['median_final_distance_m']:.1f}m"
        )

    if high_risk_site_count > 0:
        print(
            f"High-risk sites - General assessment (<=500m): {high_risk_site_count} ({(high_risk_site_count / unique_sites * 100 if unique_sites > 0 else 0):.1f}% of sites)"
        )

    if compound_high_risk_site_count > 0:
        print(
            f"High-risk sites - Compound-specific assessment: {compound_high_risk_site_count} ({(compound_high_risk_site_count / unique_sites * 100 if unique_sites > 0 else 0):.1f}% of sites)"
        )

    # Report category analysis results if available
    if "step5" in results and results["step5"].get("category_results") is not None:
        print(f"Category-based analysis: Completed with professional visualizations")

    if high_risk_site_count == 0 and compound_high_risk_site_count == 0:
        print("Step 5 risk assessment: Not completed successfully")

    # Create summary DataFrame
    summary_data = {
        "Step": [
            "Step 1: All GVFKs",
            "Step 2: GVFKs with River Contact",
            "Step 3: GVFKs with River Contact and V1/V2 Sites",
            "Step 3: Unique V1/V2 Sites (Localities)",
            "Step 3: Total Site-GVFK Combinations",
            "Step 5: GVFKs with High-Risk Sites (<=500m)",
            "Step 5: High-Risk Sites - General Assessment (<=500m)",
            "Step 5: High-Risk Sites - Compound-Specific Assessment",
        ],
        "Count": [
            total_gvfk,
            river_contact_count,
            gvfk_with_v1v2_count,
            unique_sites,
            total_site_gvfk_combinations,
            high_risk_gvfk_count,
            high_risk_site_count,
            compound_high_risk_site_count,
        ],
        "Percentage_of_Total_GVFKs": [
            "100.0%",
            f"{(river_contact_count / total_gvfk * 100):.1f}%",
            f"{(gvfk_with_v1v2_count / total_gvfk * 100):.1f}%",
            "N/A (Site-level)",
            "N/A (Combination-level)",
            f"{(high_risk_gvfk_count / total_gvfk * 100):.1f}%",
            f"{(high_risk_site_count / unique_sites * 100 if unique_sites > 0 else 0):.1f}% of sites",
            f"{(compound_high_risk_site_count / unique_sites * 100 if unique_sites > 0 else 0):.1f}% of sites",
        ],
    }

    # Add distance statistics if available
    if distance_stats:
        summary_data["Step"].extend(
            [
                "Step 4: Site-GVFK Combinations with Distances",
                "Step 4: Unique Sites with Final Distances",
                "Step 4: Average Final Distance per Site (m)",
            ]
        )
        summary_data["Count"].extend(
            [
                distance_stats["total_combinations_with_distances"],
                distance_stats["unique_sites_with_distances"],
                f"{distance_stats['average_final_distance_m']:.1f}",
            ]
        )
        summary_data["Percentage_of_Total_GVFKs"].extend(
            ["N/A (Combination-level)", "N/A (Site-level)", "N/A (Distance metric)"]
        )

    # Save summary
    workflow_summary = pd.DataFrame(summary_data)
    summary_path = get_output_path("workflow_summary")
    workflow_summary.to_csv(summary_path, index=False)
    print(f"Summary saved to: {summary_path}")


def create_visualizations_if_available(results):
    """
    Create core workflow visualizations.

    Note: Extended visualizations moved to risikovurdering/optional_analysis/

    Args:
        results (dict): Dictionary containing results from all workflow steps
    """
    print("Creating visualizations...")

    try:
        # Try to import and run selected visualizations (optional - moved to optional_analysis/)
        from risikovurdering.optional_analysis.selected_visualizations import (
            create_distance_histogram_with_thresholds,
            create_progression_plot,
        )

        results_path = "Resultater"

        # Create distance histogram if distance data is available
        if results["step4"]["distance_results"] is not None:
            try:
                create_distance_histogram_with_thresholds(results_path)
            except Exception as e:
                print(f"WARNING: Could not create distance histogram - {e}")

        # Create GVFK progression plot
        try:
            import os
            from config import GRUNDVAND_PATH, WORKFLOW_SUMMARY_DIR

            # Define required files for progression plot including Step 5
            required_files = {
                "all_gvfk": GRUNDVAND_PATH,  # Use original file since Step 1 no longer creates output
                "river_gvfk": get_output_path("step2_river_gvfk"),
                "v1v2_gvfk": get_output_path("step3_gvfk_polygons"),
                "high_risk_gvfk": get_output_path("step5_gvfk_high_risk"),
            }
            WORKFLOW_SUMMARY_DIR.mkdir(parents=True, exist_ok=True)
            create_progression_plot(str(WORKFLOW_SUMMARY_DIR), required_files)
        except Exception as e:
            print(f"WARNING: Could not create progression plot - {e}")

    except ImportError:
        print(
            "WARNING: Extended visualizations module not found (moved to optional_analysis/). Skipping optional plots."
        )
        print(
            "To create extended visualizations, see risikovurdering/optional_analysis/README.md"
        )

    # Create Step 5 visualizations if high-risk sites are available
    step5_has_results = False
    if "step5" in results:
        general_sites = results["step5"].get("general_high_risk_sites")
        compound_sites = results["step5"].get("compound_high_risk_sites")
        if (general_sites is not None and not general_sites.empty) or (
            compound_sites is not None and not compound_sites.empty
        ):
            step5_has_results = True

    if step5_has_results:
        try:
            from risikovurdering.step5_visualizations import create_step5_visualizations

            create_step5_visualizations()
        except ImportError:
            print("WARNING: Step 5 visualization module not found.")
        except Exception as e:
            print(f"WARNING: Could not create Step 5 visualizations - {e}")


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
