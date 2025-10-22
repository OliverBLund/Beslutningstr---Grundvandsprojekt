"""
Step 5: Risk Assessment of High-Risk V1/V2 Sites
================================================

Core functionality for two-fold risk assessment:
1. General Risk Assessment: Universal 500m threshold
2. Compound-Specific Assessment: Literature-based thresholds per compound category

Clean, focused implementation with supporting functions moved to separate modules.
"""

import pandas as pd
import os

from config import get_output_path, ensure_results_directory, WORKFLOW_SETTINGS
from .step5_utils import (
    categorize_contamination_substance,
    categorize_by_branch_activity,
    create_gvfk_shapefile,
    separate_sites_by_substance_data,
)
from .step5_analysis import (
    print_keyword_summary,
    print_summary,
    generate_gvfk_risk_summary,
    handle_unknown_substance_sites,
)

# Landfill-specific thresholds for compound categories
# Only categories in this dictionary will be overridden to LOSSEPLADS
LANDFILL_THRESHOLDS = {
    "BTXER": 70,  # Benzen representative at landfills
    "KLOREREDE_OPLØSNINGSMIDLER": 100,  # TCE representative at landfills
    "PHENOLER": 35,  # Phenol representative at landfills
    "PESTICIDER": 180,  # MCPP representative at landfills
    "UORGANISKE_FORBINDELSER": 50,  # Arsen representative at landfills
    # Categories not in this dict (PAH_FORBINDELSER, ANDRE, POLARE_FORBINDELSER, etc.)
    # will NOT be overridden to LOSSEPLADS - add entries here to enable override
}


def run_step5():
    """Execute Step 5 risk assessment."""
    print(f"\nStep 5: Risk Assessment of High-Risk V1/V2 Sites")
    print("=" * 60)

    ensure_results_directory()

    # Load Step 4 results
    step4_file = get_output_path("step4_final_distances_for_risk_assessment")
    if not os.path.exists(step4_file):
        raise FileNotFoundError("Step 4 results not found. Please run Step 4 first.")

    distance_results = pd.read_csv(step4_file)
    print(f"Loaded {len(distance_results)} localities from Step 4")

    # Separate sites with and without substance data
    sites_with_substances, sites_without_substances = separate_sites_by_substance_data(
        distance_results
    )

    # Run both assessments on sites with substance data
    general_sites = run_general_assessment(sites_with_substances)
    compound_combinations, compound_sites = run_compound_assessment(
        sites_with_substances
    )

    # Handle sites without substance data separately
    unknown_substance_sites = handle_unknown_substance_sites(sites_without_substances)

    # Print analysis summaries
    print_keyword_summary()
    print_summary(
        distance_results, general_sites, compound_combinations, compound_sites
    )

    # Generate Step 5 visualizations
    print(f"\nGenerating Step 5 visualizations...")
    try:
        from .step5_visualizations import create_step5_visualizations

        create_step5_visualizations()
        print(f"✓ Step 5 visualizations completed")
    except ImportError:
        print(f"⚠ Step 5 visualization module not found")
    except Exception as e:
        print(f"⚠ Could not create Step 5 visualizations: {e}")

    print(f"\n✓ STEP 5 ANALYSIS COMPLETED")

    # Return format compatible with main_workflow.py
    return {
        "general_results": (general_sites, {"total_sites": len(general_sites)}),
        "compound_results": (
            compound_sites,
            {
                "unique_sites": len(compound_sites),
                "total_combinations": len(compound_combinations),
            },
        ),
        "unknown_substance_results": (
            unknown_substance_sites,
            {"total_sites": len(unknown_substance_sites)},
        ),
        "branch_analysis_results": (None, {"status": "completed"}),
        "multi_threshold_results": {},  # Empty for compatibility
        "success": True,
    }


def _analyze_multi_gvfk_impact(high_risk_combinations, all_combinations, threshold_m):
    """
    Analyze which sites contribute to multiple GVFKs and show the impact
    of the combination-level approach vs. the old minimum-distance approach.

    Args:
        high_risk_combinations: DataFrame of lokalitet-GVFK combinations within threshold
        all_combinations: DataFrame of all lokalitet-GVFK combinations (for comparison)
        threshold_m: Distance threshold used (e.g., 500)
    """
    if high_risk_combinations.empty:
        return

    print("\n" + "=" * 70)
    print("MULTI-GVFK SITE ANALYSIS")
    print("=" * 70)

    # 1. Multi-GVFK Site Distribution
    threshold_text = (
        f"{threshold_m}m" if not isinstance(threshold_m, str) else threshold_m
    )
    print(
        f"\n1. Sites by number of GVFKs affected (within {threshold_text} threshold):"
    )
    print("-" * 70)

    # Count GVFKs per site
    gvfks_per_site = high_risk_combinations.groupby("Lokalitet_ID")["GVFK"].nunique()
    total_sites = len(gvfks_per_site)

    # Distribution
    distribution = {
        "1 GVFK": (gvfks_per_site == 1).sum(),
        "2 GVFKs": (gvfks_per_site == 2).sum(),
        "3 GVFKs": (gvfks_per_site == 3).sum(),
        "4 GVFKs": (gvfks_per_site == 4).sum(),
        "5+ GVFKs": (gvfks_per_site >= 5).sum(),
    }

    for category, count in distribution.items():
        pct = (count / total_sites * 100) if total_sites > 0 else 0
        print(f"  {category:<10} {count:>6,} sites ({pct:>5.1f}%)")

    # Multi-GVFK sites (2+)
    multi_gvfk_sites = gvfks_per_site[gvfks_per_site > 1]
    multi_count = len(multi_gvfk_sites)
    multi_pct = (multi_count / total_sites * 100) if total_sites > 0 else 0

    print(
        f"\n  → Multi-GVFK sites (2+ GVFKs): {multi_count:,} ({multi_pct:.1f}% of sites)"
    )
    print(f"  → These sites contribute to {multi_gvfk_sites.sum():,} GVFK associations")

    # Top multi-GVFK sites
    if multi_count > 0:
        print(f"\n  Top 10 multi-GVFK threat sites:")
        top_sites = gvfks_per_site.nlargest(10)

        for rank, (site_id, gvfk_count) in enumerate(top_sites.items(), 1):
            # Get GVFKs for this site
            site_combos = high_risk_combinations[
                high_risk_combinations["Lokalitet_ID"] == site_id
            ].sort_values((
                "Distance_to_River_m"))
            

            gvfk_list = []
            for _, row in site_combos.head(
                5
            ).iterrows():  # Show first 5
                gvfk_list.append(f"{row['GVFK']} ({row['Distance_to_River_m']:.0f}m)")

            more_text = f" + {gvfk_count - 5} more" if gvfk_count > 5 else ""
            print(f"    {rank:2d}. Site {site_id}: {gvfk_count} GVFKs")
            print(f"        [{', '.join(gvfk_list)}{more_text}]")

    # 2. GVFK Contribution Analysis
    print("\n\n2. GVFK Contribution Breakdown:")
    print("-" * 70)

    sites_per_gvfk = high_risk_combinations.groupby("GVFK")["Lokalitet_ID"].nunique()

    gvfk_distribution = {
        "1 site": (sites_per_gvfk == 1).sum(),
        "2-5 sites": ((sites_per_gvfk >= 2) & (sites_per_gvfk <= 5)).sum(),
        "6-10 sites": ((sites_per_gvfk >= 6) & (sites_per_gvfk <= 10)).sum(),
        "11-20 sites": ((sites_per_gvfk >= 11) & (sites_per_gvfk <= 20)).sum(),
        "21+ sites": (sites_per_gvfk >= 21).sum(),
    }

    print("  GVFKs by number of contributing sites:")
    for category, count in gvfk_distribution.items():
        if count > 0:
            print(f"    {category:<15} {count:>4} GVFKs")

    # Most threatened GVFKs
    print(f"\n  Most threatened GVFKs (by site count):")
    top_gvfks = sites_per_gvfk.nlargest(5)
    for rank, (gvfk, site_count) in enumerate(top_gvfks.items(), 1):
        print(f"    {rank}. {gvfk}: {site_count} sites within {threshold_m}m")

    # 3. Approach Comparison: Old (min-distance) vs New (all combinations)
    # Only applicable for numeric thresholds (general assessment), not compound-specific
    print("\n\n3. APPROACH COMPARISON:")
    print("-" * 70)

    if isinstance(threshold_m, str):
        # For compound-specific, we can't do meaningful comparison since each has different threshold
        print(
            "  (Skipped for compound-specific assessment - variable thresholds per substance)"
        )
        all_with_threshold = pd.DataFrame()  # Empty to skip rest of comparison
    else:
        # Simulate old approach: keep only minimum distance per site
        all_with_threshold = all_combinations[
            all_combinations["Distance_to_River_m"] <= threshold_m
        ].copy()

    if not all_with_threshold.empty:
        # Get minimum distance per site
        min_distances = all_with_threshold.groupby("Lokalitet_ID")[
            "Distance_to_River_m"
        ].min()

        # Keep only the combinations matching minimum distances
        old_approach_combos = []
        for site_id, min_dist in min_distances.items():
            site_combos = all_with_threshold[
                all_with_threshold["Lokalitet_ID"] == site_id
            ]
            # If multiple GVFKs have same min distance, take first (alphabetically by GVFK)
            min_combo = (
                site_combos[site_combos["Distance_to_River_m"] == min_dist]
                .sort_values("GVFK")
                .iloc[0]
            )
            old_approach_combos.append(min_combo)

        old_approach_df = pd.DataFrame(old_approach_combos)
        old_gvfk_count = old_approach_df["GVFK"].nunique()
        old_combo_count = len(old_approach_df)
    else:
        old_gvfk_count = 0
        old_combo_count = 0

    # New approach stats
    new_gvfk_count = high_risk_combinations["GVFK"].nunique()
    new_combo_count = len(high_risk_combinations)
    new_site_count = high_risk_combinations["Lokalitet_ID"].nunique()

    print(f"  Old approach (minimum distance per site):")
    print(f"    Would keep:     {old_combo_count:>6,} combinations (1 per site)")
    print(f"    Would identify: {old_gvfk_count:>6,} GVFKs")

    print(f"\n  New approach (all qualifying combinations):")
    print(f"    Actually kept:       {new_combo_count:>6,} combinations")
    print(f"    Actually identified: {new_gvfk_count:>6,} GVFKs")
    print(f"    Unique sites:        {new_site_count:>6,}")

    # Calculate gain
    gvfk_gain = new_gvfk_count - old_gvfk_count
    combo_gain = new_combo_count - old_combo_count

    if old_gvfk_count > 0:
        gain_pct = (gvfk_gain / old_gvfk_count) * 100
        print(f"\n  GAIN: +{gvfk_gain} GVFKs (+{gain_pct:.1f}%)")
        print(f"        +{combo_gain} combinations retained")

    # Identify "new" GVFKs only found via multi-GVFK analysis
    if not all_with_threshold.empty and gvfk_gain > 0:
        old_gvfks = set(old_approach_df["GVFK"].unique())
        new_gvfks = set(high_risk_combinations["GVFK"].unique())
        exclusive_new_gvfks = new_gvfks - old_gvfks

        if exclusive_new_gvfks:
            print(
                f"\n  NEW GVFKs found ONLY via multi-GVFK analysis: {len(exclusive_new_gvfks)}"
            )
            print(f"  (These GVFKs have sites that were closer to other GVFKs)")

            # Show examples
            examples = list(exclusive_new_gvfks)[:5]
            for gvfk in examples:
                # Find sites contributing to this GVFK
                gvfk_sites = high_risk_combinations[
                    high_risk_combinations["GVFK"] == gvfk
                ]["Lokalitet_ID"].unique()

                # For first site, show why it wasn't selected in old approach
                if len(gvfk_sites) > 0:
                    example_site = gvfk_sites[0]

                    # Get this site's distance to this GVFK
                    dist_here = high_risk_combinations[
                        (high_risk_combinations["GVFK"] == gvfk)
                        & (high_risk_combinations["Lokalitet_ID"] == example_site)
                    ]["Distance_to_River_m"].iloc[0]

                    # Get this site's minimum distance (to any GVFK)
                    all_site_combos = all_with_threshold[
                        all_with_threshold["Lokalitet_ID"] == example_site
                    ]
                    min_dist = all_site_combos["Distance_to_River_m"].min()
                    min_gvfk = all_site_combos[
                        all_site_combos["Distance_to_River_m"] == min_dist
                    ]["GVFK"].iloc[0]

                    print(f"    • {gvfk}: Example Site {example_site}")
                    print(
                        f"        {dist_here:.0f}m to this GVFK, but min={min_dist:.0f}m to {min_gvfk}"
                    )

    print("=" * 70)


def run_general_assessment(distance_results):
    """
    General risk assessment using universal 500m threshold.

    Returns:
        DataFrame: Lokalitet-GVFK combinations within 500m threshold
    """
    risk_threshold_m = WORKFLOW_SETTINGS["risk_threshold_m"]
    total_input = len(distance_results)

    high_risk_combinations = distance_results[
        distance_results["Distance_to_River_m"] <= risk_threshold_m
    ].copy()

    within_threshold = len(high_risk_combinations)
    outside_threshold = total_input - within_threshold

    print("GENERAL ASSESSMENT SUMMARY")
    print("=" * 30)
    print(f"Input lokalitet-GVFK combinations: {total_input:,}")
    print(f"  Within {risk_threshold_m} m: {within_threshold:,}")
    print(f"  Beyond {risk_threshold_m} m: {outside_threshold:,}")

    # Save results
    if not high_risk_combinations.empty:
        sites_path = get_output_path("step5_high_risk_sites")
        high_risk_combinations.to_csv(sites_path, index=False)

        # Create GVFK shapefile
        create_gvfk_shapefile(high_risk_combinations, "step5_gvfk_high_risk")

        # Count unique GVFKs and sites
        unique_gvfks = high_risk_combinations["GVFK"].dropna().nunique()
        unique_sites = high_risk_combinations["Lokalitet_ID"].dropna().nunique()
        print(f"  Unique sites affected: {unique_sites:,}")
        print(f"  Unique GVFKs affected: {unique_gvfks:,}")

        # Multi-GVFK impact analysis
        _analyze_multi_gvfk_impact(
            high_risk_combinations, distance_results, risk_threshold_m
        )
    else:
        print("  No combinations within threshold; skipping shapefile export")

    return high_risk_combinations


def run_compound_assessment(distance_results):
    """
    Compound-specific risk assessment using literature-based thresholds.

    Returns:
        tuple: (compound_combinations DataFrame, unique_sites DataFrame)
    """
    total_input_combinations = len(distance_results)
    compound_combinations = apply_compound_filtering(distance_results)

    if compound_combinations.empty:
        print("COMPOUND-SPECIFIC ASSESSMENT SUMMARY")
        print("=" * 36)
        print(f"Input lokalitet-GVFK combinations: {total_input_combinations:,}")
        print("  No combinations met the compound thresholds.")
        return compound_combinations, pd.DataFrame()

    # Get unique sites for summary
    unique_sites = compound_combinations.drop_duplicates(subset=["Lokalitet_ID"]).copy()

    # Save results
    save_compound_results(compound_combinations, unique_sites)

    qualifying_sites = len(unique_sites)
    total_combinations = len(compound_combinations)
    unique_gvfks = compound_combinations["GVFK"].dropna().nunique()

    print("COMPOUND-SPECIFIC ASSESSMENT SUMMARY")
    print("=" * 36)
    print(f"Input lokalitet-GVFK combinations: {total_input_combinations:,}")
    qualifying_pct = (
        (total_combinations / total_input_combinations * 100)
        if total_input_combinations > 0
        else 0
    )
    print(
        f"  Combinations meeting compound thresholds: {total_combinations:,} ({qualifying_pct:.1f}%)"
    )
    print(f"  Unique sites in qualifying combinations: {qualifying_sites:,}")
    print(f"  Unique GVFKs affected: {unique_gvfks:,}")

    # Multi-GVFK impact analysis for compound-specific assessment
    # Note: We use a synthetic "compound threshold" since each combination may have different thresholds
    print("\n[Compound-Specific Multi-GVFK Analysis]")
    _analyze_multi_gvfk_impact(
        compound_combinations, distance_results, "compound-specific"
    )

    return compound_combinations, unique_sites


def apply_compound_filtering(distance_results):
    """
    Apply compound-specific distance filtering.

    Returns:
        DataFrame: All qualifying site-substance combinations
    """
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
            # Process substance-based categorization (existing logic)
            substances = [s.strip() for s in substances_str.split(";") if s.strip()]

            for substance in substances:
                category, compound_threshold = categorize_contamination_substance(
                    substance
                )

                if compound_threshold is None:
                    compound_threshold = WORKFLOW_SETTINGS.get("risk_threshold_m", 500)

                effective_threshold = compound_threshold
                if is_landfill_site and category in LANDFILL_THRESHOLDS:
                    effective_threshold = max(
                        effective_threshold, LANDFILL_THRESHOLDS[category]
                    )

                # Check if site is within this compound's threshold
                if site_distance <= effective_threshold:
                    # Create row for this qualifying combination
                    combo_row = row.to_dict()
                    combo_row["Qualifying_Substance"] = substance
                    combo_row["Qualifying_Category"] = category
                    combo_row["Category_Threshold_m"] = compound_threshold
                    combo_row["Within_Threshold"] = True
                    high_risk_combinations.append(combo_row)
        else:
            # Process branch/activity-based categorization for sites without substance data
            category, compound_threshold = categorize_by_branch_activity(
                branch_text, activity_text
            )

            if compound_threshold is None:
                compound_threshold = WORKFLOW_SETTINGS.get("risk_threshold_m", 500)

            # Check if site is within this category's threshold
            if site_distance <= compound_threshold:
                # Create row for this qualifying combination
                combo_row = row.to_dict()
                combo_row["Qualifying_Substance"] = f"Branch/Activity: {category}"
                combo_row["Qualifying_Category"] = category
                combo_row["Category_Threshold_m"] = compound_threshold
                combo_row["Within_Threshold"] = True
                high_risk_combinations.append(combo_row)

    # Convert to DataFrame for post-processing
    combinations_df = (
        pd.DataFrame(high_risk_combinations)
        if high_risk_combinations
        else pd.DataFrame()
    )

    if combinations_df.empty:
        return combinations_df

    # LANDFILL OVERRIDE: Check if any non-LOSSEPLADS sites should be reclassified
    print(f"\nApplying landfill override screening...")
    print(
        f"Landfill-specific thresholds defined for: {list(LANDFILL_THRESHOLDS.keys())}"
    )
    override_stats = {
        "total_checked": 0,
        "overridden": 0,
        "by_category": {},
        "skipped_no_threshold": {},
    }

    # Track original categories for statistics
    original_categories = (
        combinations_df["Qualifying_Category"].value_counts().to_dict()
    )

    # Initialize subcategory columns
    combinations_df["Losseplads_Subcategory"] = None
    combinations_df["Original_Category"] = None
    combinations_df["Landfill_Override_Applied"] = False

    # Process each site-substance combination for potential landfill override
    for idx, row in combinations_df.iterrows():
        override_stats["total_checked"] += 1

        # Skip if already classified as LOSSEPLADS
        if row["Qualifying_Category"] == "LOSSEPLADS":
            continue

        # Check if this site has landfill characteristics
        branch_text = row.get("Lokalitetensbranche", "")
        activity_text = row.get("Lokalitetensaktivitet", "")

        landfill_category, landfill_threshold = categorize_by_branch_activity(
            branch_text, activity_text
        )

        if landfill_category == "LOSSEPLADS":
            # Apply landfill override only if we have a specific threshold for this category
            original_category = row["Qualifying_Category"]
            site_distance = row["Distance_to_River_m"]

            # Check if this category has a landfill-specific threshold
            if original_category in LANDFILL_THRESHOLDS:
                # Use landfill-specific threshold for this category
                landfill_threshold = LANDFILL_THRESHOLDS[original_category]

                # Check if site still qualifies under landfill threshold
                if site_distance <= landfill_threshold:
                    # Apply override
                    combinations_df.loc[idx, "Original_Category"] = original_category
                    combinations_df.loc[idx, "Qualifying_Category"] = (
                        "LOSSEPLADS"  # Keep main category for compatibility
                    )
                    combinations_df.loc[idx, "Losseplads_Subcategory"] = (
                        f"LOSSEPLADS_{original_category}"  # Add subcategory info
                    )
                    combinations_df.loc[idx, "Category_Threshold_m"] = (
                        landfill_threshold
                    )
                    combinations_df.loc[idx, "Qualifying_Substance"] = (
                        f"Landfill Override: {original_category}"
                    )
                    combinations_df.loc[idx, "Landfill_Override_Applied"] = True

                    # Track statistics
                    override_stats["overridden"] += 1
                    if original_category not in override_stats["by_category"]:
                        override_stats["by_category"][original_category] = 0
                    override_stats["by_category"][original_category] += 1
                else:
                    # Site no longer qualifies under landfill threshold - remove it
                    combinations_df.drop(idx, inplace=True)
            else:
                # Category not in LANDFILL_THRESHOLDS - don't override, keep original classification
                if original_category not in override_stats["skipped_no_threshold"]:
                    override_stats["skipped_no_threshold"][original_category] = 0
                override_stats["skipped_no_threshold"][original_category] += 1
        # Note: Non-overridden rows already have Landfill_Override_Applied = False from initialization

    # Print override statistics
    print(f"Landfill override results:")
    print(f"  Total combinations checked: {override_stats['total_checked']}")
    print(f"  Combinations overridden to LOSSEPLADS: {override_stats['overridden']}")

    if override_stats["overridden"] > 0:
        print(f"  Overrides by original category:")
        for category, count in sorted(
            override_stats["by_category"].items(), key=lambda x: x[1], reverse=True
        ):
            print(f"    {category}: {count} combinations")

        # Show before/after category distribution
        final_categories = (
            combinations_df["Qualifying_Category"].value_counts().to_dict()
        )
        print(f"\n  Category changes (combinations):")
        all_categories = set(original_categories.keys()) | set(final_categories.keys())
        for category in sorted(all_categories):
            original_count = original_categories.get(category, 0)
            final_count = final_categories.get(category, 0)
            change = final_count - original_count
            change_str = f"({change:+d})" if change != 0 else ""
            print(f"    {category}: {original_count} -> {final_count} {change_str}")

        # Show LOSSEPLADS subcategory breakdown
        losseplads_subcategories = combinations_df[
            combinations_df["Landfill_Override_Applied"] == True
        ]["Losseplads_Subcategory"].value_counts()

        if not losseplads_subcategories.empty:
            print(f"\n  LOSSEPLADS subcategory breakdown:")
            for subcategory, count in losseplads_subcategories.items():
                print(f"    {subcategory}: {count} combinations")

    # Show categories that were skipped due to no landfill threshold
    if override_stats["skipped_no_threshold"]:
        print(f"\n  Categories NOT overridden (no landfill threshold defined):")
        for category, count in sorted(
            override_stats["skipped_no_threshold"].items(),
            key=lambda x: x[1],
            reverse=True,
        ):
            print(f"    {category}: {count} combinations skipped")

    return combinations_df


def save_compound_results(compound_combinations, unique_sites):
    """Save compound-specific assessment results."""
    # Save detailed combinations (all qualifying substance-site pairs)
    detailed_path = get_output_path("step5_compound_detailed_combinations")
    compound_combinations.to_csv(detailed_path, index=False)

    # Save unique sites for compatibility
    if not unique_sites.empty:
        sites_path = get_output_path("step5_compound_specific_sites")
        unique_sites.to_csv(sites_path, index=False)

    # Create GVFK shapefile
    create_gvfk_shapefile(compound_combinations, "step5_compound_gvfk_high_risk")


if __name__ == "__main__":
    # Run Step 5 risk assessment
    results = run_step5()

    if results["success"]:
        print(f"\nStep 5 completed successfully:")
        print(
            f"  General assessment: {results['general_results'][1]['total_sites']} sites"
        )
        print(
            f"  Compound-specific: {results['compound_results'][1]['unique_sites']} sites"
        )

        # Generate GVFK summary
        gvfk_summary = generate_gvfk_risk_summary()
