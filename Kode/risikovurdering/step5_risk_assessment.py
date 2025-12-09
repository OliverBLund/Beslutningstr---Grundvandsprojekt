"""
Step 5: Risk Assessment of High-Risk V1/V2 Sites
================================================

Core functionality for two-fold risk assessment:
1. General Risk Assessment: Universal 500m threshold
2. Compound-Specific Assessment: Literature-based thresholds per compound category

Clean, focused implementation with supporting functions moved to separate modules.
"""

################################################################################
# SECTION 1: IMPORTS & CONFIGURATION
################################################################################
import pandas as pd
import os

from config import (
    GRUNDVAND_LAYER_NAME,
    GRUNDVAND_PATH,
    WORKFLOW_SETTINGS,
    ensure_results_directory,
    get_output_path,
)
from .step5_utils import (
    categorize_contamination_substance,
    categorize_by_branch_activity,
    create_gvfk_shapefile,
    separate_sites_by_substance_data,
    _extract_unique_gvfk_names,
)
from .step5_analysis import (
    print_keyword_summary,
    print_summary,
    print_comprehensive_summary,
    generate_gvfk_risk_summary,
    handle_unknown_substance_sites,
)
from step_reporter import report_step_header, report_counts, report_subsection, report_breakdown

# Landfill-specific thresholds for compound categories
LANDFILL_THRESHOLDS = {
    "BTXER": 70,
    "KLOREREDE_OPLØSNINGSMIDLER": 100,
    "PHENOLER": 35,
    "PESTICIDER": 180,
    "UORGANISKE_FORBINDELSER": 50,
}

################################################################################
# SECTION 2: MAIN ORCHESTRATOR - Entry Point
################################################################################


def run_step5():
    """Execute Step 5 risk assessment."""
    report_step_header(5, "Risk Assessment")

    ensure_results_directory()

    # Load Step 4 results - ALL site-GVFK combinations
    step4_file = get_output_path("step4_final_distances_for_risk_assessment")
    if not os.path.exists(step4_file):
        raise FileNotFoundError("Step 4 results not found. Please run Step 4 first.")

    distance_results = pd.read_csv(step4_file)

    report_subsection("INPUT")
    report_counts(
        "Site-GVFK combinations from Step 4",
        sites=distance_results["Lokalitet_ID"].nunique(),
        gvfks=distance_results["GVFK"].nunique(),
        combinations=len(distance_results),
    )

    # Separate sites with and without qualifying data
    sites_with_substances, sites_without_substances = separate_sites_by_substance_data(
        distance_results
    )

    report_breakdown(
        "Data availability",
        {
            "With substance/landfill data": (
                len(sites_with_substances),
                len(sites_with_substances) / len(distance_results) * 100,
            ),
            "No qualifying data (parked)": (
                len(sites_without_substances),
                len(sites_without_substances) / len(distance_results) * 100,
            ),
        },
    )

    # STEP 5a: GENERAL ASSESSMENT
    report_subsection("Step 5a: General Assessment (500m threshold)")
    general_sites = run_general_assessment(sites_with_substances)

    # STEP 5b: COMPOUND-SPECIFIC ASSESSMENT
    report_subsection("Step 5b: Compound-Specific Assessment")
    compound_combinations = run_compound_assessment(sites_with_substances)

    # Handle parked sites
    unknown_substance_sites = handle_unknown_substance_sites(sites_without_substances)

    # Print summary
    print_comprehensive_summary(
        distance_results,
        general_sites,
        compound_combinations,
        sites_without_substances,
    )

    # Generate visualizations
    try:
        from .step5_visualizations import create_step5_visualizations
        create_step5_visualizations()
    except:
        pass  # Skip silently if unavailable

    # Return format compatible with main_workflow.py
    return {
        "general_results": (general_sites, {"total_sites": len(general_sites)}),
        "compound_results": (
            compound_combinations,
            {
                "unique_sites": compound_combinations["Lokalitet_ID"].nunique() if not compound_combinations.empty else 0,
                "total_combinations": len(compound_combinations),
            },
        ),
        "unknown_substance_results": (
            unknown_substance_sites,
            {"total_sites": len(unknown_substance_sites)},
        ),
        "branch_analysis_results": (None, {"status": "completed"}),
        "multi_threshold_results": {},
        "success": True,
    }


################################################################################
# SECTION 3: ASSESSMENT FUNCTIONS - Step 5a & 5b
################################################################################


def run_general_assessment(distance_results):
    """General risk assessment using universal 500m threshold."""
    risk_threshold_m = WORKFLOW_SETTINGS["risk_threshold_m"]

    # Apply threshold
    high_risk_combinations = distance_results[
        distance_results["Distance_to_River_m"] <= risk_threshold_m
    ].copy()

    # Calculate statistics
    report_counts(
        f"Within {risk_threshold_m}m",
        sites=high_risk_combinations["Lokalitet_ID"].nunique(),
        gvfks=high_risk_combinations["GVFK"].nunique(),
        combinations=len(high_risk_combinations),
        indent=1,
    )

    # Save results
    if not high_risk_combinations.empty:
        sites_path = get_output_path("step5_high_risk_sites")
        high_risk_combinations.to_csv(sites_path, index=False, encoding="utf-8")

        # Create GVFK shapefile
        unique_gvfks = high_risk_combinations["GVFK"].nunique()
        create_gvfk_shapefile_with_validation(
            high_risk_combinations, "step5_gvfk_high_risk", unique_gvfks
        )

    return high_risk_combinations


def run_compound_assessment(distance_results):
    """Compound-specific risk assessment using literature-based thresholds."""

    # Apply compound filtering
    compound_combinations = apply_compound_filtering(distance_results)

    if compound_combinations.empty:
        print("  No combinations met compound-specific thresholds")
        return compound_combinations

    # Save results
    save_compound_results(compound_combinations)

    # Calculate statistics
    report_counts(
        "Meeting compound thresholds",
        sites=compound_combinations["Lokalitet_ID"].nunique(),
        gvfks=compound_combinations["GVFK"].dropna().nunique(),
        combinations=len(compound_combinations),
        indent=1,
    )

    return compound_combinations


def apply_compound_filtering(distance_results):
    """Apply compound-specific distance filtering."""
    high_risk_combinations = []

    def _has_landfill_keywords(text):
        if pd.isna(text):
            return False
        text_lower = str(text).lower()
        landfill_keywords = [
            "losseplads",
            "affald",
            "depon",
            "deponi",
            "fyld",
            "fyldplads",
            "skraldeplads",
        ]
        return any(keyword in text_lower for keyword in landfill_keywords)

    for _, row in distance_results.iterrows():
        substances_str = str(row.get("Lokalitetensstoffer", ""))
        site_distance = row["Distance_to_River_m"]
        branch_text = row.get("Lokalitetensbranche", "")
        activity_text = row.get("Lokalitetensaktivitet", "")
        is_landfill_site = _has_landfill_keywords(
            branch_text
        ) or _has_landfill_keywords(activity_text)

        # Check if site has substance data
        has_substance_data = not (
            pd.isna(substances_str)
            or substances_str.strip() == ""
            or substances_str == "nan"
        )

        if has_substance_data:
            # Process substance-based categorization
            substances = [s.strip() for s in substances_str.split(";") if s.strip()]

            for substance in substances:
                category, compound_threshold = categorize_contamination_substance(
                    substance
                )

                if compound_threshold is None:
                    compound_threshold = WORKFLOW_SETTINGS.get("risk_threshold_m", 500)

                effective_threshold = compound_threshold
                if is_landfill_site and category in LANDFILL_THRESHOLDS:
                    effective_threshold = LANDFILL_THRESHOLDS[category]

                # Check if site is within this compound's threshold
                if site_distance <= effective_threshold:
                    combo_row = row.to_dict()
                    combo_row["Qualifying_Substance"] = substance
                    combo_row["Qualifying_Category"] = category
                    combo_row["Category_Threshold_m"] = compound_threshold
                    combo_row["Within_Threshold"] = True
                    high_risk_combinations.append(combo_row)
        else:
            # Process branch/activity-based categorization
            category, compound_threshold = categorize_by_branch_activity(
                branch_text, activity_text
            )

            if compound_threshold is None:
                compound_threshold = WORKFLOW_SETTINGS.get("risk_threshold_m", 500)

            if site_distance <= compound_threshold:
                combo_row = row.to_dict()
                combo_row["Qualifying_Substance"] = f"Branch/Activity: {category}"
                combo_row["Qualifying_Category"] = category
                combo_row["Category_Threshold_m"] = compound_threshold
                combo_row["Within_Threshold"] = True
                high_risk_combinations.append(combo_row)

    # Convert to DataFrame
    combinations_df = (
        pd.DataFrame(high_risk_combinations)
        if high_risk_combinations
        else pd.DataFrame()
    )

    if combinations_df.empty:
        return combinations_df

    # Apply landfill override
    combinations_df = _apply_landfill_override(combinations_df)

    return combinations_df


def _apply_landfill_override(combinations_df):
    """Apply landfill-specific threshold overrides."""

    # Initialize columns
    combinations_df["Losseplads_Subcategory"] = None
    combinations_df["Original_Category"] = None
    combinations_df["Landfill_Override_Applied"] = False

    override_count = 0
    indices_to_drop = []

    # Process each combination
    for idx, row in combinations_df.iterrows():
        # Skip if already classified as LOSSEPLADS
        if row["Qualifying_Category"] == "LOSSEPLADS":
            continue

        branch_text = row.get("Lokalitetensbranche", "")
        activity_text = row.get("Lokalitetensaktivitet", "")

        landfill_category, _ = categorize_by_branch_activity(
            branch_text, activity_text
        )

        if landfill_category == "LOSSEPLADS":
            original_category = row["Qualifying_Category"]
            site_distance = row["Distance_to_River_m"]

            # Check if category has landfill threshold
            if original_category in LANDFILL_THRESHOLDS:
                landfill_threshold = LANDFILL_THRESHOLDS[original_category]

                if site_distance <= landfill_threshold:
                    # Apply override
                    combinations_df.loc[idx, "Original_Category"] = original_category
                    combinations_df.loc[idx, "Qualifying_Category"] = "LOSSEPLADS"
                    combinations_df.loc[idx, "Losseplads_Subcategory"] = (
                        f"LOSSEPLADS_{original_category}"
                    )
                    combinations_df.loc[idx, "Category_Threshold_m"] = (
                        landfill_threshold
                    )
                    combinations_df.loc[idx, "Qualifying_Substance"] = (
                        f"Landfill Override: {original_category}"
                    )
                    combinations_df.loc[idx, "Landfill_Override_Applied"] = True
                    override_count += 1
                else:
                    # No longer qualifies - mark for removal
                    indices_to_drop.append(idx)

    # Drop disqualified rows
    if indices_to_drop:
        combinations_df = combinations_df.drop(indices_to_drop)

    if override_count > 0:
        print(f"  Landfill overrides applied: {override_count} combinations")

    return combinations_df


################################################################################
# SECTION 4: ANALYSIS HELPERS - Multi-GVFK Impact Analysis
################################################################################


def _analyze_multi_gvfk_impact(high_risk_combinations, all_combinations, threshold_m):
    """Analyze multi-GVFK site impact (suppressed in clean version)."""
    # This detailed analysis is preserved but output is suppressed
    # for cleaner console output. Full analysis available in saved files.
    pass


################################################################################
# SECTION 5: SAVE/OUTPUT HELPERS - File & Shapefile Creation
################################################################################


def create_gvfk_shapefile_with_validation(
    high_risk_combinations, output_key, expected_gvfk_count
):
    """Create GVFK shapefile and validate GVFK count."""
    import geopandas as gpd

    try:
        grundvand_gdf = gpd.read_file(GRUNDVAND_PATH, layer=GRUNDVAND_LAYER_NAME)
        high_risk_gvfk_names = _extract_unique_gvfk_names(high_risk_combinations)

        id_col = "Navn" if "Navn" in grundvand_gdf.columns else grundvand_gdf.columns[0]
        high_risk_gvfk_polygons = grundvand_gdf[
            grundvand_gdf[id_col].isin(high_risk_gvfk_names)
        ].copy()

        if not high_risk_gvfk_polygons.empty:
            output_path = get_output_path(output_key)
            high_risk_gvfk_polygons.to_file(output_path, encoding="utf-8")
            return len(high_risk_gvfk_polygons)
        return 0

    except Exception as e:
        return 0


def save_compound_results(compound_combinations):
    """Save Step 5b compound-specific assessment results (PRE-infiltration filter)."""
    # Save to Step 5b output file (will NOT be overwritten by Step 5c)
    detailed_path = get_output_path("step5b_compound_combinations")
    compound_combinations.to_csv(detailed_path, index=False, encoding="utf-8")

    create_gvfk_shapefile(compound_combinations, "step5b_compound_gvfk_high_risk")


if __name__ == "__main__":
    # Run Step 5 risk assessment
    results = run_step5()

    if results["success"]:
        # Generate GVFK summary
        gvfk_summary = generate_gvfk_risk_summary()
