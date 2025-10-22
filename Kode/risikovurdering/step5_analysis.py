"""
Step 5 Risk Assessment - Analysis and Reporting Functions
========================================================

Analysis, summary, and reporting functions for Step 5 risk assessment.
"""

import pandas as pd
import os
from collections import Counter
from config import get_output_path
from .step5_utils import _extract_unique_gvfk_names, get_keyword_stats


def print_keyword_summary():
    """Print summary of keyword matching statistics."""
    keyword_stats = get_keyword_stats()

    print(f"\nLOSSEPLADS KEYWORD MATCHING SUMMARY:")
    print("=" * 50)
    print(f"Total sites checked: {keyword_stats['total_checks']:,}")

    # Branch keyword stats
    branch_total = sum(keyword_stats["branch"].values())
    print(f"\nBranch keyword matches: {branch_total:,}")
    for keyword, count in sorted(
        keyword_stats["branch"].items(), key=lambda x: x[1], reverse=True
    ):
        print(f"  {keyword}: {count:,} matches")

    # Activity keyword stats
    activity_total = sum(keyword_stats["activity"].values())
    print(f"\nActivity keyword matches: {activity_total:,}")
    for keyword, count in sorted(
        keyword_stats["activity"].items(), key=lambda x: x[1], reverse=True
    ):
        print(f"  {keyword}: {count:,} matches")

    # Combined stats
    total_matches = branch_total + activity_total
    if keyword_stats["total_checks"] > 0:
        print(f"\nTotal keyword matches: {total_matches:,}")
        print(
            f"Percentage of sites with landfill keywords: {total_matches / keyword_stats['total_checks'] * 100:.1f}%"
        )


def print_summary(
    distance_results, general_sites, compound_combinations, compound_sites
):
    """Print comprehensive summary of risk assessment results."""
    total_sites = len(distance_results)
    general_count = len(general_sites)
    compound_unique = len(compound_sites)
    compound_total = len(compound_combinations)

    print(f"\n" + "=" * 80)
    print(f"STEP 5: COMPREHENSIVE RISK ASSESSMENT RESULTS")
    print(f"=" * 80)
    print(f"Input: {total_sites:,} sites analyzed from Step 4")

    # GENERAL ASSESSMENT
    print(f"\nGENERAL ASSESSMENT (500m universal threshold):")
    print(
        f"- Sites within 500m: {general_count:,} ({general_count / total_sites * 100:.1f}%)"
    )

    # Top categories from general assessment
    if not general_sites.empty:
        print(f"\nTop Categories (General Assessment):")

        # Industries
        if "Lokalitetensbranche" in general_sites.columns:
            all_industries = []
            for ind_str in general_sites["Lokalitetensbranche"].dropna():
                industries = [i.strip() for i in str(ind_str).split(";") if i.strip()]
                all_industries.extend(industries)
            if all_industries:
                ind_counts = pd.Series(all_industries).value_counts().head(3)
                ind_str = ", ".join([f"{k} ({v})" for k, v in ind_counts.items()])
                print(f"  Industries: {ind_str}")

        # Activities
        if "Lokalitetensaktivitet" in general_sites.columns:
            all_activities = []
            for act_str in general_sites["Lokalitetensaktivitet"].dropna():
                activities = [a.strip() for a in str(act_str).split(";") if a.strip()]
                all_activities.extend(activities)
            if all_activities:
                act_counts = pd.Series(all_activities).value_counts().head(3)
                act_str = ", ".join([f"{k} ({v})" for k, v in act_counts.items()])
                print(f"  Activities: {act_str}")

        # Substances
        if "Lokalitetensstoffer" in general_sites.columns:
            all_substances = []
            for sub_str in general_sites["Lokalitetensstoffer"].dropna():
                substances = [s.strip() for s in str(sub_str).split(";") if s.strip()]
                all_substances.extend(substances)
            if all_substances:
                sub_counts = pd.Series(all_substances).value_counts().head(3)
                sub_str = ", ".join([f"{k} ({v})" for k, v in sub_counts.items()])
                print(f"  Substances: {sub_str}")

    # COMPOUND-SPECIFIC ASSESSMENT
    print(f"\nCOMPOUND-SPECIFIC ASSESSMENT (literature-based thresholds):")
    print(
        f"- Unique sites qualifying: {compound_unique:,} ({compound_unique / total_sites * 100:.1f}%)"
    )
    print(f"- Total site-substance combinations: {compound_total:,}")

    if compound_unique > 0:
        avg_substances = compound_total / compound_unique
        print(f"- Average qualifying substances per site: {avg_substances:.1f}")

    # Multi-substance distribution
    if not compound_combinations.empty:
        substances_per_site = compound_combinations.groupby("Lokalitet_ID").size()

        print(f"\nMulti-Substance Site Distribution:")
        for i in range(1, 4):
            count = (substances_per_site == i).sum()
            if count > 0:
                print(f"  {i} substance{'s' if i > 1 else ''}: {count:,} sites")

        # 4+ substances
        count_4plus = (substances_per_site >= 4).sum()
        if count_4plus > 0:
            print(f"  4+ substances: {count_4plus:,} sites")
            max_substances = substances_per_site.max()
            max_site = substances_per_site.idxmax()
            print(f"  Maximum: {max_substances} substances (Site: {max_site})")

    # Category breakdown with thresholds
    if not compound_combinations.empty:
        print(f"\nCategory Breakdown (by occurrences):")
        print(f"{'Category':<25} {'Threshold':<10} {'Occur.':<8} {'Sites':<8}")
        print(f"{'-' * 25} {'-' * 10} {'-' * 8} {'-' * 8}")

        # Get category statistics
        category_stats = {}
        for category in compound_combinations["Qualifying_Category"].unique():
            cat_data = compound_combinations[
                compound_combinations["Qualifying_Category"] == category
            ]
            threshold = (
                cat_data["Category_Threshold_m"].iloc[0] if not cat_data.empty else 500
            )
            unique_sites = cat_data["Lokalitet_ID"].nunique()
            category_stats[category] = {
                "threshold": threshold,
                "occurrences": len(cat_data),
                "sites": unique_sites,
            }

        # Sort by occurrences and print
        sorted_cats = sorted(
            category_stats.items(), key=lambda x: x[1]["occurrences"], reverse=True
        )
        for category, stats in sorted_cats[:8]:  # Top 8 categories
            threshold_str = f"{stats['threshold']:.1f}m"
            print(
                f"{category:<25} {threshold_str:<10} {stats['occurrences']:<8,} {stats['sites']:<8,}"
            )

    # Count unique GVFKs at each filtering stage
    # General assessment (500m)
    if not general_sites.empty and "GVFK" in general_sites.columns:
        general_gvfks = general_sites["GVFK"].dropna().nunique()
        general_pct = (general_gvfks / 2043) * 100
        print(
            f"{'With sites <=500m (General)':<45} {general_gvfks:<8,} {general_pct:<10.1f}%"
        )

    # Compound-specific assessment - MUST use combinations to get accurate GVFK count
    # (compound_sites is deduplicated by lokalitet, losing some GVFK associations)
    if not compound_combinations.empty and "GVFK" in compound_combinations.columns:
        compound_gvfks = compound_combinations["GVFK"].dropna().nunique()
        compound_pct = (compound_gvfks / 2043) * 100
        print(
            f"{'With compound-specific risk (Step 5)':<45} {compound_gvfks:<8,} {compound_pct:<10.1f}%"
        )


def print_comprehensive_summary(
    all_distance_results,
    general_sites,
    compound_combinations,
    parked_sites,
):
    """
    Print comprehensive workflow summary showing complete Step 5 flow.

    Args:
        all_distance_results: All site-GVFK combinations from Step 4
        general_sites: Results from general assessment (500m)
        compound_combinations: All site-GVFK-substance combinations from compound assessment
        parked_sites: Sites without substance or landfill data
    """
    print("\n" + "=" * 70)
    print("STEP 5: COMPREHENSIVE WORKFLOW SUMMARY")
    print("=" * 70)

    # INPUT FROM STEP 4
    total_combinations = len(all_distance_results)
    total_unique_sites = all_distance_results["Lokalitet_ID"].nunique()
    total_unique_gvfks = all_distance_results["GVFK"].nunique()

    print("\nINPUT FROM STEP 4:")
    print(f"  {total_combinations:,} site-GVFK combinations")
    print(f"  → {total_unique_sites:,} unique sites")
    print(f"  → {total_unique_gvfks:,} unique GVFKs")

    # DATA SEPARATION
    qualifying_combinations = (
        len(all_distance_results) - len(parked_sites)
        if not parked_sites.empty
        else len(all_distance_results)
    )
    qualifying_unique_sites = (
        all_distance_results[
            ~all_distance_results["Lokalitet_ID"].isin(parked_sites["Lokalitet_ID"])
        ]["Lokalitet_ID"].nunique()
        if not parked_sites.empty
        else total_unique_sites
    )
    qualifying_unique_gvfks = (
        all_distance_results[
            ~all_distance_results["Lokalitet_ID"].isin(parked_sites["Lokalitet_ID"])
        ]["GVFK"].nunique()
        if not parked_sites.empty
        else total_unique_gvfks
    )

    parked_combinations = len(parked_sites) if not parked_sites.empty else 0
    parked_unique_sites = (
        parked_sites["Lokalitet_ID"].nunique() if not parked_sites.empty else 0
    )

    print("\nDATA SEPARATION:")
    print(
        f"  Qualifying (with substance/landfill data): {qualifying_combinations:,} combinations"
    )
    print(f"    → {qualifying_unique_sites:,} unique sites")
    print(f"    → {qualifying_unique_gvfks:,} unique GVFKs")
    print(f"  Parked (no qualifying data): {parked_combinations:,} combinations")
    print(f"    → {parked_unique_sites:,} unique sites")

    # STEP 5a - GENERAL ASSESSMENT
    general_combinations = len(general_sites)
    general_unique_sites = (
        general_sites["Lokalitet_ID"].nunique() if not general_sites.empty else 0
    )
    general_unique_gvfks = (
        general_sites["GVFK"].nunique() if not general_sites.empty else 0
    )

    print("\nSTEP 5a - GENERAL ASSESSMENT (Universal 500m Threshold):")
    print(f"  Applied to: {qualifying_combinations:,} qualifying combinations")
    print(f"  Result: {general_combinations:,} combinations within 500m")
    print(f"    → {general_unique_sites:,} unique sites")
    print(f"    → {general_unique_gvfks:,} unique GVFKs")

    # STEP 5b - COMPOUND-SPECIFIC ASSESSMENT
    compound_total = len(compound_combinations)
    compound_unique_sites = (
        compound_combinations["Lokalitet_ID"].nunique()
        if not compound_combinations.empty
        else 0
    )
    compound_unique_gvfks = (
        compound_combinations["GVFK"].nunique()
        if not compound_combinations.empty
        else 0
    )

    print("\nSTEP 5b - COMPOUND-SPECIFIC ASSESSMENT (Variable Thresholds):")
    print(f"  Applied to: {qualifying_combinations:,} qualifying combinations")
    print(f"  Result: {compound_total:,} site-GVFK-substance combinations")
    print(f"    → {compound_unique_sites:,} unique sites")
    print(f"    → {compound_unique_gvfks:,} unique GVFKs")

    print("=" * 70)


def generate_gvfk_risk_summary():
    """
    Generate a summary table of GVFKs at risk based on Step 5a general assessment (500m threshold).
    This represents the true "generel risiko" baseline - GVFKs with sites within 500m.
    This should be called after run_step5() completes.
    """
    # Load Step 5a general assessment results (the true "generel risiko" baseline)
    general_file = get_output_path("step5_high_risk_sites")
    if not os.path.exists(general_file):
        print("No Step 5a general assessment results found. Run Step 5 first.")
        return None

    general_df = pd.read_csv(general_file)

    # Get all unique GVFKs from general assessment (lokalitet-GVFK combinations within 500m)
    all_gvfks = general_df["GVFK"].dropna().unique()

    # Also load compound combinations for category breakdown (optional)
    compound_file = get_output_path("step5_compound_detailed_combinations")
    compound_df = None
    if os.path.exists(compound_file):
        compound_df = pd.read_csv(compound_file)

    if len(all_gvfks) == 0:
        print("Warning: No GVFKs found in general assessment results")
        return None

    # Create GVFK summary
    gvfk_summary = []

    # Process each GVFK
    for gvfk in all_gvfks:
        # Get lokalitet-GVFK combinations in this GVFK from general assessment
        gvfk_combinations = general_df[general_df["GVFK"] == gvfk]
        unique_sites = gvfk_combinations["Lokalitet_ID"].nunique()

        # Initialize category counts
        category_counts = {}
        total_combinations = 0

        # If compound data is available, get category breakdown for this GVFK
        if compound_df is not None:
            # Find compound combinations for this GVFK
            gvfk_compounds = compound_df[compound_df["GVFK"] == gvfk]
            if not gvfk_compounds.empty:
                category_counts = (
                    gvfk_compounds["Qualifying_Category"].value_counts().to_dict()
                )
                total_combinations = len(gvfk_compounds)

        # Build summary row for this GVFK
        summary_row = {
            "GVFK": gvfk,
            "Total_Sites": unique_sites,
            "Total_Combinations": total_combinations,
        }

        # Add counts for each category (if available)
        for category, count in category_counts.items():
            summary_row[category] = count

        gvfk_summary.append(summary_row)

    # Convert to DataFrame and sort
    if gvfk_summary:
        gvfk_df = pd.DataFrame(gvfk_summary).fillna(0)
        gvfk_df = gvfk_df.sort_values("Total_Sites", ascending=False)

        # Save to CSV
        output_path = get_output_path("step5_gvfk_risk_summary")
        gvfk_df.to_csv(output_path, index=False)

        print(f"\nâœ“ GVFK risk summary saved: {output_path}")
        print(f"  Total GVFKs at risk: {len(gvfk_df)}")
        print(
            f"  Top 5 GVFKs by site count: {', '.join(gvfk_df.head()['GVFK'].tolist())}"
        )

        return gvfk_df

    return None

def handle_unknown_substance_sites(sites_without_substances):
    """
    Handle sites without substance data separately.
    These sites are "parked" for separate analysis.

    Args:
        sites_without_substances (DataFrame): Sites without substance data

    Returns:
        DataFrame: Sites without substances (unchanged, just documented)
    """
    if sites_without_substances.empty:
        print("No sites without substance data found.")
        return sites_without_substances

    print(f"\nUnknown Substance Sites Analysis:")
    print(f"  Total sites without substance data: {len(sites_without_substances)}")

    # Save these sites separately
    if len(sites_without_substances) > 0:
        unknown_path = get_output_path("step5_unknown_substance_sites")
        sites_without_substances.to_csv(unknown_path, index=False)
        print(f"  Saved to: {unknown_path}")

        # Basic statistics
        if "Distance_to_River_m" in sites_without_substances.columns:
            mean_dist = sites_without_substances["Distance_to_River_m"].mean()
            median_dist = sites_without_substances["Distance_to_River_m"].median()
            within_500m = (sites_without_substances["Distance_to_River_m"] <= 500).sum()
            print(
                f"  Distance statistics: mean={mean_dist:.0f}m, median={median_dist:.0f}m"
            )
            print(
                f"  Sites within 500m: {within_500m} ({within_500m / len(sites_without_substances) * 100:.1f}%)"
            )

        # Branch information if available
        if "Lokalitetensbranche" in sites_without_substances.columns:
            branches = sites_without_substances["Lokalitetensbranche"].value_counts()
            print(f"  Top branches: {', '.join(branches.head(3).index.tolist())}")

    return sites_without_substances
