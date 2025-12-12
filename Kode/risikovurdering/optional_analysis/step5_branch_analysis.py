"""
Step 5 Branch Analysis: Analyzing sites without substance data
============================================================

BASELINE COMPARISON - IMPORTANT:
This analysis compares branch-only sites against Step 5a (general 500m assessment).

Step 5a Baseline ("generel risiko"):
- ALL substance sites within universal 500m threshold
- Source: step5_high_risk_sites_500m.csv OR step5_gvfk_risk_summary.csv
- Result: ~300+ GVFKs (see lines 471-491 for file loading)
- This is the "generel risiko" category for ALL substance sites regardless of compound type

Branch-only Sites Analysis:
- Sites WITHOUT substance data but WITH branch/activity information
- Source: step5_unknown_substance_sites.csv
- Filtered to â‰¤500m for "generel risiko" impact analysis (line 457)
- Result: ~44 additional GVFKs beyond the Step 5a baseline

KEY DISTINCTION vs step6_final_analysis.py:
- THIS analysis (step5_branch) compares against Step 5a (general 500m, ~300+ GVFKs)
  resulting in ~44 additional GVFKs (see _analyze_generel_risiko_impact, lines 453-541)
- step6_final_analysis.py compares against Step 5b (compound-specific, 217 GVFKs)
  resulting in 92 additional GVFKs - both are CORRECT but measure different things
- Step 5a has MORE GVFKs (looser threshold), so fewer appear "new" here

The analysis focuses on:
- Distance distributions compared to substance sites
- Branch/activity frequency analysis
- Geographic distribution patterns
- Basic risk profiling based on proximity to rivers
- GVFK impact on "generel risiko" category (lines 453-541)

Output: Separate folder structure under Resultater/branch_analysis/
"""

import sys
from pathlib import Path

# Add the Kode directory to Python path for config import when running independently
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import os
from datetime import datetime
from config import RESULTS_DIR as RESULTS_PATH

# Set matplotlib to use Danish-friendly encoding
plt.rcParams["font.family"] = "DejaVu Sans"
plt.rcParams["axes.unicode_minus"] = False


def run_branch_analysis(sites_without_substances, sites_with_substances=None):
    """
    Run comprehensive analysis of branch-only sites.

    Args:
        sites_without_substances (DataFrame): Sites with branch data but no substances
        sites_with_substances (DataFrame, optional): Sites with substances for comparison

    Returns:
        dict: Analysis results and statistics
    """
    print(f"\n{'=' * 60}")
    print(f"BRANCH-ONLY SITES ANALYSIS")
    print(f"{'=' * 60}")

    # Set up output directory
    branch_output_dir = _setup_output_directory()

    # CRITICAL: Deduplicate by Lokalitet_ID first to get unique sites
    # (The input contains site-GVFK combinations, not unique sites)
    print(f"\nInput data: {len(sites_without_substances):,} site-GVFK combinations")
    unique_parked_sites = sites_without_substances.drop_duplicates(subset="Lokalitet_ID")
    print(f"Unique parked sites: {len(unique_parked_sites):,}")
    
    # Filter to ≤500m for the main analysis (general risk assessment threshold)
    parked_500m = unique_parked_sites[unique_parked_sites["Distance_to_River_m"] <= 500]
    print(f"Unique parked sites ≤500m: {len(parked_500m):,}\n")

    # Basic statistics
    print(f"Analyzing {len(unique_parked_sites):,} unique sites without substance data")

    # Run analysis components
    results = {}

    # 1. Distance analysis
    print(f"\n1. Distance Analysis")
    print(f"-" * 20)
    distance_stats = _analyze_distances(
        unique_parked_sites, sites_with_substances, branch_output_dir
    )
    results["distance_analysis"] = distance_stats

    # 2. Branch frequency analysis
    print(f"\n2. Branch Analysis")
    print(f"-" * 18)
    branch_stats = _analyze_branches(unique_parked_sites, branch_output_dir)
    results["branch_analysis"] = branch_stats

    # 2b. Activity frequency analysis
    print(f"\n2b. Activity Analysis")
    print(f"-" * 19)
    activity_stats = _analyze_activities(unique_parked_sites, branch_output_dir)
    results["activity_analysis"] = activity_stats

    # 2c. Industry comparison (if substance sites available)
    if sites_with_substances is not None:
        print(f"\n2c. Industry Comparison")
        print(f"-" * 21)
        industry_comparison = _compare_industries(
            unique_parked_sites, sites_with_substances, branch_output_dir
        )
        results["industry_comparison"] = industry_comparison

        # 2d. Activity comparison
        print(f"\n2d. Activity Comparison")
        print(f"-" * 21)
        activity_comparison = _compare_activities(
            unique_parked_sites, sites_with_substances, branch_output_dir
        )
        results["activity_comparison"] = activity_comparison

    # 3. Geographic distribution (≤500m only for consistency with impact analysis)
    print(f"\n3. Geographic Distribution (≤500m)")
    print(f"-" * 25)
    geo_stats = _analyze_geography(parked_500m, branch_output_dir)
    results["geographic_analysis"] = geo_stats

    # 4. GVFK analysis
    print(f"\n4. GVFK Distribution")
    print(f"-" * 19)
    gvfk_stats = _analyze_gvfk_distribution(unique_parked_sites, branch_output_dir)
    results["gvfk_analysis"] = gvfk_stats

    # 5. "Generel Risiko" GVFK Impact Analysis
    print(f"\n5. 'Generel Risiko' GVFK Impact Analysis")
    print(f"-" * 40)
    generel_risiko_impact = _analyze_generel_risiko_impact(
        unique_parked_sites, branch_output_dir
    )
    results["generel_risiko_impact"] = generel_risiko_impact

    # Save comprehensive summary
    _save_analysis_summary(results, unique_parked_sites, branch_output_dir)

    # Create comprehensive professional visualizations
    _create_professional_visualizations(
        unique_parked_sites, sites_with_substances, results, branch_output_dir
    )

    # Final comparison summary
    if sites_with_substances is not None:
        _print_final_comparison(
            results, len(unique_parked_sites), len(sites_with_substances)
        )

    print(f"\nâœ“ BRANCH ANALYSIS COMPLETED")
    print(f"Results saved to: {branch_output_dir}")

    return results


def _setup_output_directory():
    """Create and return the branch analysis output directory."""
    branch_dir = os.path.join(RESULTS_PATH, "branch_analysis")
    figures_dir = os.path.join(branch_dir, "Figures")

    os.makedirs(branch_dir, exist_ok=True)
    os.makedirs(figures_dir, exist_ok=True)

    return branch_dir


def _analyze_distances(sites_without_substances, sites_with_substances, output_dir):
    """Analyze distance distributions and create comparison plots."""

    # Distance statistics for branch-only sites
    distances = sites_without_substances["Distance_to_River_m"]

    stats = {
        "mean_distance": distances.mean(),
        "median_distance": distances.median(),
        "std_distance": distances.std(),
        "within_250m": (distances <= 250).sum(),
        "within_500m": (distances <= 500).sum(),
        "within_1000m": (distances <= 1000).sum(),
        "within_1500m": (distances <= 1500).sum(),
    }

    # Comparative statistics if substance sites provided
    if sites_with_substances is not None:
        substance_distances = sites_with_substances["Distance_to_River_m"]
        substance_stats = {
            "within_250m": (substance_distances <= 250).sum(),
            "within_500m": (substance_distances <= 500).sum(),
            "within_1000m": (substance_distances <= 1000).sum(),
            "within_1500m": (substance_distances <= 1500).sum(),
        }

        print(f"  DISTANCE COMPARISON:")
        print(f"    Threshold    Branch-only     Substance sites   Additional sites")
        print(f"    ---------    -----------     ---------------   ----------------")
        for threshold in ["250m", "500m", "1000m", "1500m"]:
            threshold_key = f"within_{threshold[:-1]}m"
            branch_count = stats[threshold_key]
            substance_count = substance_stats[threshold_key]
            branch_pct = branch_count / len(sites_without_substances) * 100
            substance_pct = substance_count / len(sites_with_substances) * 100
            additional = branch_count
            print(
                f"    â‰¤{threshold:<8} {branch_count:>6,} ({branch_pct:>4.1f}%)   {substance_count:>6,} ({substance_pct:>4.1f}%)   +{additional:,} ({additional / (substance_count + additional) * 100:.1f}% increase)"
            )
    else:
        print(f"  Distance statistics:")
        print(f"    Mean: {stats['mean_distance']:.0f}m")
        print(f"    Median: {stats['median_distance']:.0f}m")
        print(
            f"    Sites <=250m: {stats['within_250m']:,} ({stats['within_250m'] / len(sites_without_substances) * 100:.1f}%)"
        )
        print(
            f"    Sites <=500m: {stats['within_500m']:,} ({stats['within_500m'] / len(sites_without_substances) * 100:.1f}%)"
        )
        print(
            f"    Sites <=1000m: {stats['within_1000m']:,} ({stats['within_1000m'] / len(sites_without_substances) * 100:.1f}%)"
        )

    # Create distance comparison plots
    _create_distance_plots(sites_without_substances, sites_with_substances, output_dir)

    return stats


def _analyze_branches(sites_without_substances, output_dir):
    """Analyze branch frequency and create visualizations, handling semicolon-separated lists."""

    # Extract and count individual branches from semicolon-separated lists
    all_branches = []
    multi_branch_sites = 0

    for branch_str in sites_without_substances["Lokalitetensbranche"]:
        if pd.notna(branch_str) and str(branch_str).strip():
            # Split by semicolon and clean up each branch
            branches = [b.strip() for b in str(branch_str).split(";") if b.strip()]
            all_branches.extend(branches)
            if len(branches) > 1:
                multi_branch_sites += 1

    # Count individual branch occurrences
    branch_counts = pd.Series(all_branches).value_counts()

    print(f"  Total branch occurrences: {len(all_branches):,}")
    print(f"  Total unique branches: {len(branch_counts)}")
    print(
        f"  Sites with multiple branches: {multi_branch_sites:,} ({multi_branch_sites / len(sites_without_substances) * 100:.1f}%)"
    )
    print(f"  Top 5 branches:")
    for i, (branch, count) in enumerate(branch_counts.head().items()):
        print(
            f"    {i + 1}. {branch}: {count:,} occurrences ({count / len(all_branches) * 100:.1f}%)"
        )

    # Create branch frequency plots
    _create_branch_plots(
        branch_counts, sites_without_substances, output_dir, len(all_branches)
    )

    return {
        "total_branch_occurrences": len(all_branches),
        "total_unique_branches": len(branch_counts),
        "multi_branch_sites": multi_branch_sites,
        "top_branches": branch_counts.head(10).to_dict(),
        "branch_distribution": branch_counts.to_dict(),
    }


def _analyze_activities(sites_without_substances, output_dir):
    """Analyze activity frequency and create visualizations, handling semicolon-separated lists."""

    # Extract and count individual activities from semicolon-separated lists
    all_activities = []
    multi_activity_sites = 0

    for activity_str in sites_without_substances["Lokalitetensaktivitet"]:
        if pd.notna(activity_str) and str(activity_str).strip():
            # Split by semicolon and clean up each activity
            activities = [a.strip() for a in str(activity_str).split(";") if a.strip()]
            all_activities.extend(activities)
            if len(activities) > 1:
                multi_activity_sites += 1

    # Count individual activity occurrences
    activity_counts = pd.Series(all_activities).value_counts()

    print(f"  Total activity occurrences: {len(all_activities):,}")
    print(f"  Total unique activities: {len(activity_counts)}")
    print(
        f"  Sites with multiple activities: {multi_activity_sites:,} ({multi_activity_sites / len(sites_without_substances) * 100:.1f}%)"
    )
    print(f"  Top 5 activities:")
    for i, (activity, count) in enumerate(activity_counts.head().items()):
        print(
            f"    {i + 1}. {activity}: {count:,} occurrences ({count / len(all_activities) * 100:.1f}%)"
        )

    return {
        "total_activity_occurrences": len(all_activities),
        "total_unique_activities": len(activity_counts),
        "multi_activity_sites": multi_activity_sites,
        "top_activities": activity_counts.head(10).to_dict(),
        "activity_distribution": activity_counts.to_dict(),
    }


def _compare_activities(sites_without_substances, sites_with_substances, output_dir):
    """Compare activity distributions between the two datasets."""

    # Get activity counts from branch-only sites
    branch_activities = []
    for activity_str in sites_without_substances["Lokalitetensaktivitet"]:
        if pd.notna(activity_str) and str(activity_str).strip():
            activities = [a.strip() for a in str(activity_str).split(";") if a.strip()]
            branch_activities.extend(activities)
    branch_activity_counts = pd.Series(branch_activities).value_counts()

    # Get activity counts from substance sites
    substance_activities = []
    for activity_str in sites_with_substances["Lokalitetensaktivitet"]:
        if pd.notna(activity_str) and str(activity_str).strip():
            activities = [a.strip() for a in str(activity_str).split(";") if a.strip()]
            substance_activities.extend(activities)
    substance_activity_counts = pd.Series(substance_activities).value_counts()

    # Find overlap and differences
    all_activities = set(branch_activity_counts.index) | set(
        substance_activity_counts.index
    )
    common_activities = set(branch_activity_counts.index) & set(
        substance_activity_counts.index
    )
    branch_only_activities = set(branch_activity_counts.index) - set(
        substance_activity_counts.index
    )
    substance_only_activities = set(substance_activity_counts.index) - set(
        branch_activity_counts.index
    )

    print(f"  Activity overlap analysis:")
    print(f"    Total unique activities: {len(all_activities)}")
    print(
        f"    Common to both datasets: {len(common_activities)} ({len(common_activities) / len(all_activities) * 100:.1f}%)"
    )
    print(
        f"    Only in branch-only sites: {len(branch_only_activities)} ({len(branch_only_activities) / len(all_activities) * 100:.1f}%)"
    )
    print(
        f"    Only in substance sites: {len(substance_only_activities)} ({len(substance_only_activities) / len(all_activities) * 100:.1f}%)"
    )

    # Top common activities
    if len(common_activities) > 0:
        print(f"\n  Top common activities:")
        common_comparison = []
        for activity in common_activities:
            branch_count = branch_activity_counts.get(activity, 0)
            substance_count = substance_activity_counts.get(activity, 0)
            total_count = branch_count + substance_count
            common_comparison.append(
                (activity, branch_count, substance_count, total_count)
            )

        common_comparison.sort(key=lambda x: x[3], reverse=True)
        for i, (activity, b_count, s_count, total) in enumerate(common_comparison[:5]):
            b_pct = (
                b_count / len(branch_activities) * 100
                if len(branch_activities) > 0
                else 0
            )
            s_pct = (
                s_count / len(substance_activities) * 100
                if len(substance_activities) > 0
                else 0
            )
            print(f"    {i + 1}. {activity[:40]}...")
            print(
                f"       Branch-only: {b_count:,} ({b_pct:.1f}%), Substance: {s_count:,} ({s_pct:.1f}%)"
            )

    # High-risk activities
    high_risk_keywords = [
        "benzin",
        "olie",
        "brÃ¦ndstof",
        "kemisk",
        "oplag",
        "rengÃ¸ring",
        "reparation",
        "salg",
    ]
    high_risk_common = []
    for activity in common_activities:
        if any(keyword in activity.lower() for keyword in high_risk_keywords):
            branch_count = branch_activity_counts.get(activity, 0)
            substance_count = substance_activity_counts.get(activity, 0)
            high_risk_common.append((activity, branch_count, substance_count))

    if high_risk_common:
        print(f"\n  High-risk activities in both datasets:")
        for activity, b_count, s_count in sorted(
            high_risk_common, key=lambda x: x[1] + x[2], reverse=True
        )[:3]:
            print(f"    {activity}: Branch-only {b_count:,}, Substance {s_count:,}")

    return {
        "total_activities": len(all_activities),
        "common_activities": len(common_activities),
        "branch_only_activities": len(branch_only_activities),
        "substance_only_activities": len(substance_only_activities),
        "high_risk_common": high_risk_common,
        "top_common": common_comparison[:10] if "common_comparison" in locals() else [],
    }


def _compare_industries(sites_without_substances, sites_with_substances, output_dir):
    """Compare industry/branch distributions between the two datasets."""

    # Get branch counts from branch-only sites
    branch_branches = []
    for branch_str in sites_without_substances["Lokalitetensbranche"]:
        if pd.notna(branch_str) and str(branch_str).strip():
            branches = [b.strip() for b in str(branch_str).split(";") if b.strip()]
            branch_branches.extend(branches)
    branch_counts = pd.Series(branch_branches).value_counts()

    # Get branch counts from substance sites
    substance_branches = []
    for branch_str in sites_with_substances["Lokalitetensbranche"]:
        if pd.notna(branch_str) and str(branch_str).strip():
            branches = [b.strip() for b in str(branch_str).split(";") if b.strip()]
            substance_branches.extend(branches)
    substance_counts = pd.Series(substance_branches).value_counts()

    # Find overlap and differences
    all_branches = set(branch_counts.index) | set(substance_counts.index)
    common_branches = set(branch_counts.index) & set(substance_counts.index)
    branch_only_branches = set(branch_counts.index) - set(substance_counts.index)
    substance_only_branches = set(substance_counts.index) - set(branch_counts.index)

    print(f"  Industry overlap analysis:")
    print(f"    Total unique industries: {len(all_branches)}")
    print(
        f"    Common to both datasets: {len(common_branches)} ({len(common_branches) / len(all_branches) * 100:.1f}%)"
    )
    print(
        f"    Only in branch-only sites: {len(branch_only_branches)} ({len(branch_only_branches) / len(all_branches) * 100:.1f}%)"
    )
    print(
        f"    Only in substance sites: {len(substance_only_branches)} ({len(substance_only_branches) / len(all_branches) * 100:.1f}%)"
    )

    # Top common industries
    if len(common_branches) > 0:
        print(f"\n  Top common industries:")
        common_comparison = []
        for branch in common_branches:
            branch_count = branch_counts.get(branch, 0)
            substance_count = substance_counts.get(branch, 0)
            total_count = branch_count + substance_count
            common_comparison.append(
                (branch, branch_count, substance_count, total_count)
            )

        common_comparison.sort(key=lambda x: x[3], reverse=True)
        for i, (branch, b_count, s_count, total) in enumerate(common_comparison[:5]):
            b_pct = (
                b_count / len(branch_branches) * 100 if len(branch_branches) > 0 else 0
            )
            s_pct = (
                s_count / len(substance_branches) * 100
                if len(substance_branches) > 0
                else 0
            )
            print(f"    {i + 1}. {branch[:40]}...")
            print(
                f"       Branch-only: {b_count:,} ({b_pct:.1f}%), Substance: {s_count:,} ({s_pct:.1f}%)"
            )

    # High-risk branches that are common
    high_risk_keywords = [
        "servicestationer",
        "autoreparation",
        "benzin",
        "olie",
        "kemisk",
        "tank",
        "brÃ¦ndstof",
    ]
    high_risk_common = []
    for branch in common_branches:
        if any(keyword in branch.lower() for keyword in high_risk_keywords):
            branch_count = branch_counts.get(branch, 0)
            substance_count = substance_counts.get(branch, 0)
            high_risk_common.append((branch, branch_count, substance_count))

    if high_risk_common:
        print(f"\n  High-risk industries in both datasets:")
        for branch, b_count, s_count in sorted(
            high_risk_common, key=lambda x: x[1] + x[2], reverse=True
        )[:3]:
            print(f"    {branch}: Branch-only {b_count:,}, Substance {s_count:,}")

    return {
        "total_industries": len(all_branches),
        "common_industries": len(common_branches),
        "branch_only_industries": len(branch_only_branches),
        "substance_only_industries": len(substance_only_branches),
        "high_risk_common": high_risk_common,
        "top_common": common_comparison[:10] if "common_comparison" in locals() else [],
    }


def _analyze_geography(sites_without_substances, output_dir):
    """Analyze geographic distribution patterns."""

    # Region analysis
    if "Regionsnavn" in sites_without_substances.columns:
        region_counts = sites_without_substances["Regionsnavn"].value_counts()
        print(f"  Distribution by region:")
        for region, count in region_counts.head().items():
            print(
                f"    {region}: {count:,} sites ({count / len(sites_without_substances) * 100:.1f}%)"
            )

    # Municipality analysis
    if "Kommunenavn" in sites_without_substances.columns:
        kommune_counts = sites_without_substances["Kommunenavn"].value_counts()
        print(f"  Top municipalities:")
        for kommune, count in kommune_counts.head(3).items():
            print(f"    {kommune}: {count:,} sites")

    return {
        "regions": region_counts.to_dict()
        if "Regionsnavn" in sites_without_substances.columns
        else {},
        "municipalities": kommune_counts.head(20).to_dict()
        if "Kommunenavn" in sites_without_substances.columns
        else {},
    }


def _analyze_gvfk_distribution(sites_without_substances, output_dir):
    """Analyze which GVFKs contain branch-only sites and potential impact."""

    # Count sites per GVFK for branch-only sites
    gvfk_counts = (
        sites_without_substances.groupby("GVFK").size().sort_values(ascending=False)
    )

    print(f"  Branch-only sites distributed across {len(gvfk_counts)} GVFKs")
    print(f"  Top GVFKs with branch-only sites:")
    for gvfk, count in gvfk_counts.head(5).items():
        print(f"    {gvfk}: {count:,} sites")

    # Analyze sites within 500m threshold by GVFK
    branch_500m = sites_without_substances[
        sites_without_substances["Distance_to_River_m"] <= 500
    ]
    if not branch_500m.empty:
        gvfk_500m_counts = (
            branch_500m.groupby("GVFK").size().sort_values(ascending=False)
        )
        print(f"\n  GVFKs with branch-only sites â‰¤500m: {len(gvfk_500m_counts)}")
        print(f"  Top GVFKs by sites â‰¤500m:")
        for gvfk, count in gvfk_500m_counts.head(3).items():
            total_in_gvfk = gvfk_counts.get(gvfk, 0)
            print(f"    {gvfk}: {count:,} sites â‰¤500m (of {total_in_gvfk:,} total)")
    else:
        gvfk_500m_counts = pd.Series()

    return {
        "total_gvfks_with_branch_sites": len(gvfk_counts),
        "gvfks_with_sites_within_500m": len(gvfk_500m_counts)
        if not gvfk_500m_counts.empty
        else 0,
        "top_gvfks": gvfk_counts.head(20).to_dict(),
        "top_gvfks_500m": gvfk_500m_counts.head(10).to_dict()
        if not gvfk_500m_counts.empty
        else {},
        "gvfk_distribution": gvfk_counts.to_dict(),
        "gvfk_500m_counts": gvfk_500m_counts,
    }


def _analyze_generel_risiko_impact(sites_without_substances, output_dir):
    """Analyze how many additional GVFKs would move to 'generel risiko' category with branch-only sites."""

    # Get branch-only sites within 500m (the threshold for "generel risiko")
    branch_500m = sites_without_substances[
        sites_without_substances["Distance_to_River_m"] <= 500
    ]

    if branch_500m.empty:
        print(f"  No branch-only sites within 500m threshold")
        return {
            "branch_sites_500m": 0,
            "additional_gvfks": 0,
            "current_generel_risiko_gvfks": 0,
            "expanded_generel_risiko_gvfks": 0,
        }

    # Get unique GVFKs from branch-only sites within 500m
    branch_gvfks_500m = set(branch_500m["GVFK"].unique())

    # Load current Step 5a general assessment (500m sites) - this is the true "generel risiko" baseline
    try:
        # Try using Step 5a general assessment (current workflow output)
        from config import get_output_path
        step5a_file = get_output_path("step5_high_risk_sites")
        if os.path.exists(step5a_file):
            step5a_df = pd.read_csv(step5a_file)
            current_generel_risiko_gvfks = set(step5a_df["GVFK"].dropna().unique())
            current_count = len(current_generel_risiko_gvfks)
            print(f"  Using Step 5a general assessment file: {current_count} GVFKs")
        else:
            # Fallback: Try GVFK risk summary if it exists
            current_gvfk_file = os.path.join(RESULTS_PATH, "step5_gvfk_risk_summary.csv")
            if os.path.exists(current_gvfk_file):
                current_gvfk_df = pd.read_csv(current_gvfk_file)
                current_generel_risiko_gvfks = set(current_gvfk_df["GVFK"].dropna().unique())
                current_count = len(current_generel_risiko_gvfks)
                print(f"  Using GVFK risk summary file: {current_count} GVFKs")
            else:
                raise FileNotFoundError(
                    f"Neither Step 5a file ({step5a_file}) nor GVFK risk summary found"
                )

    except Exception as e:
        print(f"  Error: Could not load current 'generel risiko' baseline: {e}")
        raise

    # Calculate overlap and new GVFKs
    already_in_generel_risiko = branch_gvfks_500m & current_generel_risiko_gvfks
    new_generel_risiko_gvfks = branch_gvfks_500m - current_generel_risiko_gvfks

    # Calculate totals
    additional_gvfks = len(new_generel_risiko_gvfks)
    expanded_total = current_count + additional_gvfks

    print(f"  GENEREL RISIKO GVFK IMPACT ANALYSIS:")
    print(
        f"  Current 'generel risiko' GVFKs (with substance/landfill sites â‰¤500m): {current_count}"
    )
    print(f"  Branch-only sites â‰¤500m: {len(branch_500m):,} sites")
    print(f"  GVFKs with branch-only sites â‰¤500m: {len(branch_gvfks_500m)}")
    print(f"  ")
    print(f"  GVFKs already in 'generel risiko': {len(already_in_generel_risiko)}")
    print(f"  NEW GVFKs that would be added to 'generel risiko': {additional_gvfks}")
    print(f"  ")
    print(f"  EXPANDED TOTAL 'generel risiko' GVFKs: {expanded_total}")
    print(
        f"  Percentage increase: {(additional_gvfks / current_count * 100) if current_count > 0 else 0:.1f}%"
    )

    # Show some examples of new GVFKs
    if new_generel_risiko_gvfks:
        print(f"\n  Examples of NEW 'generel risiko' GVFKs from branch-only sites:")
        branch_gvfk_counts = branch_500m["GVFK"].value_counts()
        new_gvfk_examples = []
        for gvfk in new_generel_risiko_gvfks:
            site_count = branch_gvfk_counts.get(gvfk, 0)
            new_gvfk_examples.append((gvfk, site_count))

        # Sort by site count and show top examples
        new_gvfk_examples.sort(key=lambda x: x[1], reverse=True)
        for i, (gvfk, count) in enumerate(new_gvfk_examples[:5]):
            print(f"    {i + 1}. {gvfk}: {count} branch-only sites â‰¤500m")

    return {
        "branch_sites_500m": len(branch_500m),
        "gvfks_with_branch_sites_500m": len(branch_gvfks_500m),
        "current_generel_risiko_gvfks": current_count,
        "already_in_generel_risiko": len(already_in_generel_risiko),
        "additional_gvfks": additional_gvfks,
        "expanded_generel_risiko_gvfks": expanded_total,
        "percentage_increase": (additional_gvfks / current_count * 100)
        if current_count > 0
        else 0,
        "new_gvfk_examples": new_gvfk_examples[:10]
        if "new_gvfk_examples" in locals()
        else [],
        "branch_gvfks_500m": list(branch_gvfks_500m),
        "new_generel_risiko_gvfks": list(new_generel_risiko_gvfks),
    }


def _create_distance_plots(branch_sites, substance_sites, output_dir):
    """Create professional distance comparison visualization."""

    # Set professional styling
    plt.style.use("seaborn-v0_8-whitegrid")
    colors = ["#2E86AB", "#A23B72"]  # Professional blue and magenta

    fig, ax = plt.subplots(1, 1, figsize=(12, 8))

    # Get distance data
    branch_distances = branch_sites["Distance_to_River_m"]

    # Create overlapping histogram with transparency
    ax.hist(
        branch_distances,
        bins=60,
        alpha=0.7,
        label=f"Branch-only sites (n={len(branch_distances):,})",
        color=colors[0],
        density=True,
        edgecolor="white",
        linewidth=0.5,
    )

    if substance_sites is not None:
        substance_distances = substance_sites["Distance_to_River_m"]
        ax.hist(
            substance_distances,
            bins=60,
            alpha=0.7,
            label=f"Substance sites (n={len(substance_distances):,})",
            color=colors[1],
            density=True,
            edgecolor="white",
            linewidth=0.5,
        )

    # Add threshold lines with clean styling
    thresholds = [250, 500, 1000, 1500]
    threshold_colors = ["#FF6B6B", "#4ECDC4", "#45B7D1", "#96CEB4"]

    for i, threshold in enumerate(thresholds):
        ax.axvline(
            threshold, color=threshold_colors[i], linestyle="--", alpha=0.8, linewidth=2
        )

        # Add clean annotations
        branch_count = (branch_distances <= threshold).sum()
        branch_pct = branch_count / len(branch_distances) * 100

        if substance_sites is not None:
            substance_count = (substance_distances <= threshold).sum()
            substance_pct = substance_count / len(substance_distances) * 100
            label = f"{threshold}m\n{branch_pct:.1f}% | {substance_pct:.1f}%"
        else:
            label = f"{threshold}m\n{branch_pct:.1f}%"

        ax.text(
            threshold,
            ax.get_ylim()[1] * 0.9,
            label,
            ha="center",
            va="top",
            fontsize=10,
            bbox=dict(boxstyle="round,pad=0.3", facecolor="white", alpha=0.8),
        )

    # Professional styling
    ax.set_xlabel("Distance to River (m)", fontsize=14, fontweight="bold")
    ax.set_ylabel("Density", fontsize=14, fontweight="bold")
    ax.set_title(
        "Distance Distribution Comparison:\nBranch-only vs Substance Sites",
        fontsize=16,
        fontweight="bold",
        pad=20,
    )

    # Clean legend
    ax.legend(loc="upper right", frameon=True, fancybox=True, shadow=True, fontsize=12)

    # Set limits and grid
    ax.set_xlim(0, 8000)
    ax.grid(True, alpha=0.3, linestyle="-", linewidth=0.5)
    ax.set_facecolor("#FAFAFA")

    # Remove top and right spines
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color("#CCCCCC")
    ax.spines["bottom"].set_color("#CCCCCC")

    plt.tight_layout()
    plt.savefig(
        os.path.join(output_dir, "Figures", "distance_comparison.png"),
        dpi=300,
        bbox_inches="tight",
        facecolor="white",
    )
    plt.close()

    print(f"  âœ“ Professional distance comparison plot saved")


def _create_branch_plots(branch_counts, sites_data, output_dir, total_occurrences):
    """Create branch frequency visualizations."""

    # Top branches bar chart
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10))

    # Top 15 branches
    top_branches = branch_counts.head(15)
    ax1.barh(range(len(top_branches)), top_branches.values, color="skyblue")
    ax1.set_yticks(range(len(top_branches)))
    ax1.set_yticklabels(
        [
            label[:50] + "..." if len(label) > 50 else label
            for label in top_branches.index
        ]
    )
    ax1.set_xlabel("Number of Occurrences")
    ax1.set_title(
        "Top 15 Branches in Branch-Only Sites (Individual Branch Occurrences)"
    )

    # Add value labels
    for i, v in enumerate(top_branches.values):
        ax1.text(v + max(top_branches.values) * 0.01, i, f"{v:,}", va="center")

    # Branch distribution (pie chart for top categories)
    top_10_branches = branch_counts.head(10)
    other_count = branch_counts.iloc[10:].sum()

    if other_count > 0:
        pie_data = list(top_10_branches.values) + [other_count]
        pie_labels = list(top_10_branches.index) + ["Other"]
    else:
        pie_data = top_10_branches.values
        pie_labels = top_10_branches.index

    # Truncate labels for pie chart
    pie_labels = [
        label[:20] + "..." if len(label) > 20 else label for label in pie_labels
    ]

    ax2.pie(pie_data, labels=pie_labels, autopct="%1.1f%%", startangle=90)
    ax2.set_title("Branch Distribution (Individual Occurrences - Top 10 + Other)")

    plt.tight_layout()
    plt.savefig(
        os.path.join(output_dir, "Figures", "branch_frequency.png"),
        dpi=300,
        bbox_inches="tight",
    )
    plt.close()

    print(f"  âœ“ Branch frequency plots saved")


def _count_occurrences_by_category(sites_df, column_name):
    """
    Count category occurrences, handling semicolon-separated values.
    This matches the counting method used in step5_visualizations.py.
    Returns dict with category -> occurrence_count mapping.
    """
    all_categories = []

    for idx, row in sites_df.iterrows():
        if pd.notna(row[column_name]) and str(row[column_name]).strip():
            # Split semicolon-separated values
            categories = [
                cat.strip() for cat in str(row[column_name]).split(";") if cat.strip()
            ]
            all_categories.extend(categories)

    # Count occurrences
    if all_categories:
        category_counts = pd.Series(all_categories).value_counts()
        return category_counts.to_dict()
    else:
        return {}


def _create_professional_visualizations(
    branch_sites, substance_sites, results, output_dir
):
    """Create comprehensive suite of professional visualizations."""

    print(f"\nCreating professional visualizations...")

    # Set up professional styling
    plt.style.use("seaborn-v0_8-whitegrid")
    colors = ["#2E86AB", "#A23B72", "#F18F01", "#C73E1D", "#4ECDC4", "#45B7D1"]

    # 1. Industry/Activity Comparison Charts
    _create_industry_comparison_charts(
        branch_sites, substance_sites, results, output_dir, colors
    )

    # 2. Geographic Comparison Charts
    _create_geographic_comparison_charts(
        branch_sites, substance_sites, results, output_dir, colors
    )

    # 3. GVFK Impact Visualizations
    _create_gvfk_impact_charts(branch_sites, results, output_dir, colors)

    # 4. Executive Summary Dashboard
    _create_executive_dashboard(
        branch_sites, substance_sites, results, output_dir, colors
    )

    print(f"  âœ“ All professional visualizations completed")


def _create_industry_comparison_charts(
    branch_sites, substance_sites, results, output_dir, colors
):
    """Create professional industry and activity comparison charts."""

    if substance_sites is None:
        return

    # Filter branch-only sites to â‰¤500m for fair comparison with substance sites (which are pre-filtered)
    branch_sites_500m = branch_sites[branch_sites["Distance_to_River_m"] <= 500]

    print(
        f"  Filtering for comparison: {len(branch_sites_500m):,} of {len(branch_sites):,} branch-only sites â‰¤500m"
    )

    # Branch comparison chart
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 8))

    # Calculate branch occurrence counts (matches step5_visualizations.py method)
    branch_branch_sites = _count_occurrences_by_category(
        branch_sites_500m, "Lokalitetensbranche"
    )
    substance_branch_sites = _count_occurrences_by_category(
        substance_sites, "Lokalitetensbranche"
    )

    # Get top common branches by total sites
    common_branches = set(branch_branch_sites.keys()) & set(
        substance_branch_sites.keys()
    )
    if common_branches:
        branch_totals = [
            (
                branch,
                branch_branch_sites.get(branch, 0),
                substance_branch_sites.get(branch, 0),
                branch_branch_sites.get(branch, 0)
                + substance_branch_sites.get(branch, 0),
            )
            for branch in common_branches
        ]

        top_branches = sorted(branch_totals, key=lambda x: x[3], reverse=True)[
            :8
        ]  # Top 8

        branch_names = [
            item[0][:30] + "..." if len(item[0]) > 30 else item[0]
            for item in top_branches
        ]
        branch_counts = [item[1] for item in top_branches]  # Occurrence counts
        substance_counts = [item[2] for item in top_branches]  # Occurrence counts

        y_pos = np.arange(len(branch_names))

        # Horizontal bar chart
        bars1 = ax1.barh(
            y_pos - 0.2,
            branch_counts,
            0.4,
            label="Branch-only sites",
            color=colors[0],
            alpha=0.8,
        )
        bars2 = ax1.barh(
            y_pos + 0.2,
            substance_counts,
            0.4,
            label="Substance sites",
            color=colors[1],
            alpha=0.8,
        )

        ax1.set_yticks(y_pos)
        ax1.set_yticklabels(branch_names, fontsize=10)
        ax1.set_xlabel("Number of Occurrences", fontsize=12, fontweight="bold")
        ax1.set_title(
            "Top Industries: Branch-only vs Substance Sites (Occurrences)",
            fontsize=14,
            fontweight="bold",
            pad=20,
        )
        ax1.legend(fontsize=11)
        ax1.grid(True, alpha=0.3, axis="x")

        # Add value labels
        for bar in bars1:
            width = bar.get_width()
            ax1.text(
                width + max(branch_counts) * 0.01,
                bar.get_y() + bar.get_height() / 2,
                f"{int(width):,}",
                ha="left",
                va="center",
                fontsize=9,
            )
        for bar in bars2:
            width = bar.get_width()
            ax1.text(
                width + max(substance_counts) * 0.01,
                bar.get_y() + bar.get_height() / 2,
                f"{int(width):,}",
                ha="left",
                va="center",
                fontsize=9,
            )

    # Activity comparison chart
    branch_activity_sites = _count_occurrences_by_category(
        branch_sites_500m, "Lokalitetensaktivitet"
    )
    substance_activity_sites = _count_occurrences_by_category(
        substance_sites, "Lokalitetensaktivitet"
    )

    # Get top common activities by total sites
    common_activities = set(branch_activity_sites.keys()) & set(
        substance_activity_sites.keys()
    )
    if common_activities:
        activity_totals = [
            (
                activity,
                branch_activity_sites.get(activity, 0),
                substance_activity_sites.get(activity, 0),
                branch_activity_sites.get(activity, 0)
                + substance_activity_sites.get(activity, 0),
            )
            for activity in common_activities
        ]

        top_activities = sorted(activity_totals, key=lambda x: x[3], reverse=True)[
            :8
        ]  # Top 8

        activity_names = [
            item[0][:30] + "..." if len(item[0]) > 30 else item[0]
            for item in top_activities
        ]
        branch_activity_counts = [
            item[1] for item in top_activities
        ]  # Occurrence counts
        substance_activity_counts = [
            item[2] for item in top_activities
        ]  # Occurrence counts

        y_pos = np.arange(len(activity_names))

        # Horizontal bar chart
        bars3 = ax2.barh(
            y_pos - 0.2,
            branch_activity_counts,
            0.4,
            label="Branch-only sites",
            color=colors[2],
            alpha=0.8,
        )
        bars4 = ax2.barh(
            y_pos + 0.2,
            substance_activity_counts,
            0.4,
            label="Substance sites",
            color=colors[3],
            alpha=0.8,
        )

        ax2.set_yticks(y_pos)
        ax2.set_yticklabels(activity_names, fontsize=10)
        ax2.set_xlabel("Number of Occurrences", fontsize=12, fontweight="bold")
        ax2.set_title(
            "Top Activities: Branch-only vs Substance Sites (Occurrences)",
            fontsize=14,
            fontweight="bold",
            pad=20,
        )
        ax2.legend(fontsize=11)
        ax2.grid(True, alpha=0.3, axis="x")

        # Add value labels
        for bar in bars3:
            width = bar.get_width()
            ax2.text(
                width + max(branch_activity_counts) * 0.01,
                bar.get_y() + bar.get_height() / 2,
                f"{int(width):,}",
                ha="left",
                va="center",
                fontsize=9,
            )
        for bar in bars4:
            width = bar.get_width()
            ax2.text(
                width + max(substance_activity_counts) * 0.01,
                bar.get_y() + bar.get_height() / 2,
                f"{int(width):,}",
                ha="left",
                va="center",
                fontsize=9,
            )

    # Clean styling
    for ax in [ax1, ax2]:
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.set_facecolor("#FAFAFA")

    plt.tight_layout()
    plt.savefig(
        os.path.join(output_dir, "Figures", "industry_activity_comparison.png"),
        dpi=300,
        bbox_inches="tight",
        facecolor="white",
    )
    plt.close()

    print(f"  âœ“ Industry/Activity comparison charts saved")


def _create_geographic_comparison_charts(
    branch_sites, substance_sites, results, output_dir, colors
):
    """Create geographic and regional comparison visualizations."""

    # Filter branch-only sites to â‰¤500m for fair comparison
    branch_sites_500m = branch_sites[branch_sites["Distance_to_River_m"] <= 500]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 8))

    # Regional comparison
    if "Regionsnavn" in branch_sites_500m.columns:
        branch_regions = branch_sites_500m["Regionsnavn"].value_counts()

        if substance_sites is not None and "Regionsnavn" in substance_sites.columns:
            substance_regions = substance_sites["Regionsnavn"].value_counts()

            # Get common regions
            common_regions = set(branch_regions.index) & set(substance_regions.index)
            if common_regions:
                regions = list(common_regions)[:5]  # Top 5 regions
                branch_counts = [branch_regions.get(region, 0) for region in regions]
                substance_counts = [
                    substance_regions.get(region, 0) for region in regions
                ]

                # Clean region names
                region_names = [region.replace("Region ", "") for region in regions]

                y_pos = np.arange(len(region_names))

                bars1 = ax1.barh(
                    y_pos - 0.2,
                    branch_counts,
                    0.4,
                    label="Branch-only sites",
                    color=colors[0],
                    alpha=0.8,
                )
                bars2 = ax1.barh(
                    y_pos + 0.2,
                    substance_counts,
                    0.4,
                    label="Substance sites",
                    color=colors[1],
                    alpha=0.8,
                )

                ax1.set_yticks(y_pos)
                ax1.set_yticklabels(region_names, fontsize=12)
                ax1.set_xlabel("Number of Sites", fontsize=12, fontweight="bold")
                ax1.set_title(
                    "Regional Distribution Comparison",
                    fontsize=14,
                    fontweight="bold",
                    pad=20,
                )
                ax1.legend(fontsize=11)
                ax1.grid(True, alpha=0.3, axis="x")

                # Add value labels
                for bar in bars1:
                    width = bar.get_width()
                    ax1.text(
                        width + max(branch_counts) * 0.01,
                        bar.get_y() + bar.get_height() / 2,
                        f"{int(width):,}",
                        ha="left",
                        va="center",
                        fontsize=10,
                    )
                for bar in bars2:
                    width = bar.get_width()
                    ax1.text(
                        width + max(substance_counts) * 0.01,
                        bar.get_y() + bar.get_height() / 2,
                        f"{int(width):,}",
                        ha="left",
                        va="center",
                        fontsize=10,
                    )

    # Municipality impact (branch-only sites only)
    if "Kommunenavn" in branch_sites_500m.columns:
        top_municipalities = branch_sites_500m["Kommunenavn"].value_counts().head(8)

        # Clean municipality names
        muni_names = [name.replace(" Kommune", "") for name in top_municipalities.index]
        muni_counts = top_municipalities.values

        bars = ax2.bar(range(len(muni_names)), muni_counts, color=colors[2], alpha=0.8)

        ax2.set_xticks(range(len(muni_names)))
        ax2.set_xticklabels(muni_names, rotation=45, ha="right", fontsize=10)
        ax2.set_ylabel("Number of Branch-only Sites", fontsize=12, fontweight="bold")
        ax2.set_title(
            "Top Municipalities with Branch-only Sites",
            fontsize=14,
            fontweight="bold",
            pad=20,
        )
        ax2.grid(True, alpha=0.3, axis="y")

        # Add value labels
        for bar in bars:
            height = bar.get_height()
            ax2.text(
                bar.get_x() + bar.get_width() / 2.0,
                height + max(muni_counts) * 0.01,
                f"{int(height):,}",
                ha="center",
                va="bottom",
                fontsize=10,
            )

    # Clean styling
    for ax in [ax1, ax2]:
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.set_facecolor("#FAFAFA")

    plt.tight_layout()
    plt.savefig(
        os.path.join(output_dir, "Figures", "geographic_comparison.png"),
        dpi=300,
        bbox_inches="tight",
        facecolor="white",
    )
    plt.close()

    print(f"  âœ“ Geographic comparison charts saved")


def _create_gvfk_impact_charts(branch_sites, results, output_dir, colors):
    """Create GVFK impact visualization."""

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 8))

    if "gvfk_analysis" in results:
        # Top GVFKs with branch-only sites
        if results["gvfk_analysis"]["top_gvfks"]:
            top_gvfks = list(results["gvfk_analysis"]["top_gvfks"].items())[:10]

            gvfk_names = [
                gvfk[:15] + "..." if len(gvfk) > 15 else gvfk
                for gvfk, count in top_gvfks
            ]
            gvfk_counts = [count for gvfk, count in top_gvfks]

            bars = ax1.bar(
                range(len(gvfk_names)), gvfk_counts, color=colors[4], alpha=0.8
            )

            ax1.set_xticks(range(len(gvfk_names)))
            ax1.set_xticklabels(gvfk_names, rotation=45, ha="right", fontsize=9)
            ax1.set_ylabel(
                "Number of Branch-only Sites", fontsize=12, fontweight="bold"
            )
            ax1.set_title(
                "Top GVFKs by Branch-only Site Count",
                fontsize=14,
                fontweight="bold",
                pad=20,
            )
            ax1.grid(True, alpha=0.3, axis="y")

            # Add value labels
            for bar in bars:
                height = bar.get_height()
                ax1.text(
                    bar.get_x() + bar.get_width() / 2.0,
                    height + max(gvfk_counts) * 0.01,
                    f"{int(height)}",
                    ha="center",
                    va="bottom",
                    fontsize=9,
                )

        # GVFK impact by distance thresholds
        if "distance_analysis" in results:
            thresholds = ["â‰¤250m", "â‰¤500m", "â‰¤1000m", "â‰¤1500m"]
            threshold_keys = [
                "within_250m",
                "within_500m",
                "within_1000m",
                "within_1500m",
            ]

            # Calculate sites at each threshold
            site_counts = [results["distance_analysis"][key] for key in threshold_keys]

            # Estimate GVFK counts (simplified - could be improved with actual GVFK analysis per threshold)
            gvfk_estimates = []
            for threshold_key in threshold_keys:
                sites_at_threshold = branch_sites[
                    branch_sites["Distance_to_River_m"]
                    <= int(threshold_key.split("_")[1][:-1])
                ]
                gvfk_count = (
                    sites_at_threshold["GVFK"].nunique()
                    if not sites_at_threshold.empty
                    else 0
                )
                gvfk_estimates.append(gvfk_count)

            bars = ax2.bar(thresholds, gvfk_estimates, color=colors[5], alpha=0.8)

            ax2.set_ylabel("Number of GVFKs Affected", fontsize=12, fontweight="bold")
            ax2.set_title(
                "GVFKs Affected by Distance Threshold",
                fontsize=14,
                fontweight="bold",
                pad=20,
            )
            ax2.grid(True, alpha=0.3, axis="y")

            # Add value labels
            for bar, sites in zip(bars, site_counts):
                height = bar.get_height()
                ax2.text(
                    bar.get_x() + bar.get_width() / 2.0,
                    height + max(gvfk_estimates) * 0.01,
                    f"{int(height)} GVFKs\n({sites:,} sites)",
                    ha="center",
                    va="bottom",
                    fontsize=10,
                )

    # Clean styling
    for ax in [ax1, ax2]:
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.set_facecolor("#FAFAFA")

    plt.tight_layout()
    plt.savefig(
        os.path.join(output_dir, "Figures", "gvfk_impact.png"),
        dpi=300,
        bbox_inches="tight",
        facecolor="white",
    )
    plt.close()

    print(f"  âœ“ GVFK impact charts saved")


def _create_executive_dashboard(
    branch_sites, substance_sites, results, output_dir, colors
):
    """Create executive summary dashboard."""

    # Filter branch-only sites to â‰¤500m for comparison charts
    branch_sites_500m = branch_sites[branch_sites["Distance_to_River_m"] <= 500]

    fig = plt.figure(figsize=(16, 12))
    gs = fig.add_gridspec(3, 3, hspace=0.3, wspace=0.3)

    # Title
    fig.suptitle(
        "Branch-only Sites Analysis: Executive Dashboard\n(Comparison charts filtered to â‰¤500m)",
        fontsize=18,
        fontweight="bold",
        y=0.95,
    )

    # 1. Key metrics panel (top left)
    ax1 = fig.add_subplot(gs[0, 0])

    # Key numbers
    branch_count = len(branch_sites)
    substance_count = len(substance_sites) if substance_sites is not None else 0
    total_sites = branch_count + substance_count

    metrics_text = f"""
DATASET OVERVIEW
â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
Branch-only sites: {branch_count:,}
Substance sites: {substance_count:,}
Total sites: {total_sites:,}

Branch-only proportion: {branch_count / total_sites * 100:.1f}%
"""

    if "distance_analysis" in results:
        sites_500m = results["distance_analysis"]["within_500m"]
        metrics_text += f"""
RISK PROFILE
â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
Sites â‰¤500m: {sites_500m:,} ({sites_500m / branch_count * 100:.1f}%)
Additional risk sites: +{sites_500m:,}
"""

    ax1.text(
        0.05,
        0.95,
        metrics_text,
        transform=ax1.transAxes,
        fontsize=11,
        verticalalignment="top",
        fontfamily="monospace",
        bbox=dict(boxstyle="round,pad=0.5", facecolor=colors[0], alpha=0.1),
    )
    ax1.set_xlim(0, 1)
    ax1.set_ylim(0, 1)
    ax1.axis("off")

    # 2. Distance threshold comparison (top middle and right)
    ax2 = fig.add_subplot(gs[0, 1:])

    if "distance_analysis" in results:
        thresholds = ["â‰¤250m", "â‰¤500m", "â‰¤1000m", "â‰¤1500m"]
        threshold_keys = ["within_250m", "within_500m", "within_1000m", "within_1500m"]

        branch_counts = [results["distance_analysis"][key] for key in threshold_keys]

        if substance_sites is not None:
            # Calculate substance site counts for comparison
            substance_distances = substance_sites["Distance_to_River_m"]
            substance_counts = [
                (substance_distances <= 250).sum(),
                (substance_distances <= 500).sum(),
                (substance_distances <= 1000).sum(),
                (substance_distances <= 1500).sum(),
            ]
        else:
            substance_counts = [0] * 4

        x = np.arange(len(thresholds))
        width = 0.35

        bars1 = ax2.bar(
            x - width / 2,
            branch_counts,
            width,
            label="Branch-only sites",
            color=colors[0],
            alpha=0.8,
        )
        bars2 = ax2.bar(
            x + width / 2,
            substance_counts,
            width,
            label="Substance sites",
            color=colors[1],
            alpha=0.8,
        )

        ax2.set_xlabel("Distance Threshold", fontsize=12, fontweight="bold")
        ax2.set_ylabel("Number of Sites", fontsize=12, fontweight="bold")
        ax2.set_title(
            "Site Distribution by Distance Threshold", fontsize=14, fontweight="bold"
        )
        ax2.set_xticks(x)
        ax2.set_xticklabels(thresholds)
        ax2.legend()
        ax2.grid(True, alpha=0.3, axis="y")

        # Add percentage increase annotations
        for i, (bar1, bar2) in enumerate(zip(bars1, bars2)):
            if substance_counts[i] > 0:
                increase = (
                    branch_counts[i] / (branch_counts[i] + substance_counts[i]) * 100
                )
                ax2.text(
                    bar1.get_x() + bar1.get_width() / 2,
                    bar1.get_height() + max(branch_counts) * 0.02,
                    f"+{increase:.0f}%",
                    ha="center",
                    va="bottom",
                    fontsize=10,
                    fontweight="bold",
                )

    # 3. Top industries (middle left)
    ax3 = fig.add_subplot(gs[1, :])

    # Use occurrence counts to match step5_visualizations.py methodology
    branch_site_counts = _count_occurrences_by_category(
        branch_sites, "Lokalitetensbranche"
    )
    if branch_site_counts:
        top_branches = sorted(
            branch_site_counts.items(), key=lambda x: x[1], reverse=True
        )[:10]

        branch_names = [
            name[:25] + "..." if len(name) > 25 else name
            for name, count in top_branches
        ]
        branch_counts = [count for name, count in top_branches]

        bars = ax3.barh(
            range(len(branch_names)), branch_counts, color=colors[2], alpha=0.8
        )

        ax3.set_yticks(range(len(branch_names)))
        ax3.set_yticklabels(branch_names, fontsize=10)
        ax3.set_xlabel("Number of Occurrences", fontsize=12, fontweight="bold")
        ax3.set_title(
            "Top 10 Industries in Branch-only Sites (Occurrences)",
            fontsize=14,
            fontweight="bold",
        )
        ax3.grid(True, alpha=0.3, axis="x")

        # Add value labels
        for bar in bars:
            width = bar.get_width()
            ax3.text(
                width + max(branch_counts) * 0.01,
                bar.get_y() + bar.get_height() / 2,
                f"{int(width):,}",
                ha="left",
                va="center",
                fontsize=10,
            )

    # Clean styling for all subplots
    for ax in [ax2, ax3]:
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.set_facecolor("#FAFAFA")

    plt.savefig(
        os.path.join(output_dir, "Figures", "executive_dashboard.png"),
        dpi=300,
        bbox_inches="tight",
        facecolor="white",
    )
    plt.close()

    print(f"  âœ“ Executive dashboard saved")


def _save_analysis_summary(results, sites_data, output_dir):
    """Save comprehensive analysis summary."""

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    summary_content = f"""
BRANCH-ONLY SITES ANALYSIS SUMMARY
Generated: {timestamp}
{"=" * 50}

OVERVIEW:
Total sites analyzed: {len(sites_data):,}
Sites without substance data but with branch information

DISTANCE ANALYSIS:
Mean distance to river: {results["distance_analysis"]["mean_distance"]:.0f}m
Median distance to river: {results["distance_analysis"]["median_distance"]:.0f}m
Sites within 500m: {results["distance_analysis"]["within_500m"]:,} ({results["distance_analysis"]["within_500m"] / len(sites_data) * 100:.1f}%)
Sites within 1000m: {results["distance_analysis"]["within_1000m"]:,} ({results["distance_analysis"]["within_1000m"] / len(sites_data) * 100:.1f}%)

BRANCH ANALYSIS:
Total branch occurrences: {results["branch_analysis"]["total_branch_occurrences"]:,}
Total unique branches: {results["branch_analysis"]["total_unique_branches"]}
Sites with multiple branches: {results["branch_analysis"]["multi_branch_sites"]:,} ({results["branch_analysis"]["multi_branch_sites"] / len(sites_data) * 100:.1f}%)
Top 5 branches (by occurrences):
"""

    for i, (branch, count) in enumerate(
        list(results["branch_analysis"]["top_branches"].items())[:5]
    ):
        summary_content += f"  {i + 1}. {branch}: {count:,} occurrences ({count / results['branch_analysis']['total_branch_occurrences'] * 100:.1f}%)\n"

    summary_content += f"""
GVFK DISTRIBUTION:
Branch-only sites found in {results["gvfk_analysis"]["total_gvfks_with_branch_sites"]} GVFKs
Top 3 GVFKs with branch-only sites:
"""

    for i, (gvfk, count) in enumerate(
        list(results["gvfk_analysis"]["top_gvfks"].items())[:3]
    ):
        summary_content += f"  {i + 1}. {gvfk}: {count:,} sites\n"

    # Add "Generel Risiko" impact if available
    if "generel_risiko_impact" in results:
        gr_impact = results["generel_risiko_impact"]
        summary_content += f"""
'GENEREL RISIKO' GVFK IMPACT:
Current 'generel risiko' GVFKs: {gr_impact["current_generel_risiko_gvfks"]}
Branch-only sites â‰¤500m: {gr_impact["branch_sites_500m"]:,} sites
Additional GVFKs from branch-only sites: {gr_impact["additional_gvfks"]}
EXPANDED TOTAL 'generel risiko' GVFKs: {gr_impact["expanded_generel_risiko_gvfks"]}
Percentage increase: {gr_impact["percentage_increase"]:.1f}%
"""

    summary_content += f"""
FILES GENERATED:
- branch_only_sites_detailed.csv (detailed site data)
- Figures/distance_comparison.png (distance analysis)
- Figures/branch_frequency.png (branch frequency analysis)
- branch_analysis_summary.txt (this file)

{"=" * 50}
"""

    # Save summary
    with open(
        os.path.join(output_dir, "branch_analysis_summary.txt"), "w", encoding="utf-8"
    ) as f:
        f.write(summary_content)

    # Save detailed CSV
    sites_data.to_csv(
        os.path.join(output_dir, "branch_only_sites_detailed.csv"), 
        index=False,
        encoding="utf-8"
    )

    print(f"  âœ“ Analysis summary and detailed data saved")


def _print_final_comparison(results, branch_sites_count, substance_sites_count):
    """Print a final summary comparison between branch-only and substance sites."""

    print(f"\n{'=' * 60}")
    print(f"FINAL COMPARATIVE SUMMARY")
    print(f"{'=' * 60}")

    print(f"Dataset Sizes:")
    print(f"  Branch-only sites: {branch_sites_count:,}")
    print(f"  Substance sites: {substance_sites_count:,}")
    print(f"  Total sites: {branch_sites_count + substance_sites_count:,}")
    print(
        f"  Branch-only proportion: {branch_sites_count / (branch_sites_count + substance_sites_count) * 100:.1f}%"
    )

    # Distance comparison
    if "distance_analysis" in results:
        branch_500m = results["distance_analysis"]["within_500m"]
        print(f"\nDistance Analysis:")
        print(
            f"  Branch-only sites â‰¤500m: {branch_500m:,} ({branch_500m / branch_sites_count * 100:.1f}%)"
        )
        print(
            f"  This represents {branch_500m:,} additional sites that could qualify for risk assessment"
        )

    # Industry overlap
    if "industry_comparison" in results:
        common = results["industry_comparison"]["common_industries"]
        branch_only = results["industry_comparison"]["branch_only_industries"]
        print(f"\nIndustry Analysis:")
        print(f"  Industries in common: {common}")
        print(f"  New industries from branch-only sites: {branch_only}")

    # GVFK impact
    if "gvfk_analysis" in results:
        gvfks_affected = results["gvfk_analysis"]["total_gvfks_with_branch_sites"]
        gvfks_500m = results["gvfk_analysis"]["gvfks_with_sites_within_500m"]
        print(f"\nGVFK Impact:")
        print(f"  Additional GVFKs with branch-only sites: {gvfks_affected}")
        print(f"  GVFKs with branch-only sites â‰¤500m: {gvfks_500m}")

    print(f"\nKey Decision Points:")
    print(f"  1. Branch-only sites are closer to rivers than expected")
    print(f"  2. Many common high-risk industries (gas stations, auto repair)")
    print(f"  3. Could add substantial sites to risk assessment")
    print(f"  4. Geographic coverage is extensive")
    print(f"\nNote: Visualizations show unique SITE counts (not occurrence counts)")
    print(
        f"      A site with 'Auto;Gas' contributes to both categories but counts as 1 site each"
    )


def create_danish_presentation_charts(results, branch_sites, output_dir):
    """Create Danish-language charts for presentation slides."""

    print("\nCreating Danish presentation charts...")

    # Create presentation subfolder
    presentation_dir = os.path.join(output_dir, "Presentation")
    os.makedirs(presentation_dir, exist_ok=True)

    # Color palette for consistency
    colors = [
        "#2E86AB",
        "#A23B72",
        "#F18F01",
        "#C73E1D",
        "#6A994E",
        "#577590",
        "#F8961E",
    ]

    # Generate 500m filtered analysis data for the charts
    print("  Generating 500m filtered analysis data...")
    sites_500m = (
        branch_sites[branch_sites["Distance_to_River_m"] <= 500]
        if "Distance_to_River_m" in branch_sites.columns
        else pd.DataFrame()
    )

    if not sites_500m.empty:
        # Add 500m filtered branch analysis
        results["branch_500m_analysis"] = _analyze_branches_500m(sites_500m)
        results["activity_500m_analysis"] = _analyze_activities_500m(sites_500m)
        print(f"    âœ“ Filtered data for {len(sites_500m)} sites â‰¤500m")
    else:
        print(f"    ! No sites â‰¤500m found or distance column missing")

    # 1. Top 5 Branches Chart (Danish) - 500m filtered
    _create_top_branches_danish_chart(results, presentation_dir, colors)

    # 2. Top 5 Activities Chart (Danish) - 500m filtered
    _create_top_activities_danish_chart(results, presentation_dir, colors)

    # 3. GVFK Impact Chart (Danish)
    _create_gvfk_impact_danish_chart(results, presentation_dir, colors)

    # 4. Distance Distribution Chart (Danish)
    _create_distance_distribution_danish_chart(results, presentation_dir, colors)

    print(f"  âœ“ Danish presentation charts saved to: {presentation_dir}")


def _analyze_branches_500m(sites_500m):
    """Analyze branch distribution for sites â‰¤500m only."""

    all_branches = []
    for branch_str in sites_500m["Lokalitetensbranche"]:
        if pd.notna(branch_str) and str(branch_str).strip():
            branches = [b.strip() for b in str(branch_str).split(";") if b.strip()]
            all_branches.extend(branches)

    if not all_branches:
        return {"top_branches": {}, "total_branch_occurrences": 0}

    branch_counts = pd.Series(all_branches).value_counts()

    return {
        "top_branches": branch_counts.to_dict(),
        "total_branch_occurrences": len(all_branches),
    }


def _analyze_activities_500m(sites_500m):
    """Analyze activity distribution for sites â‰¤500m only."""

    all_activities = []
    for activity_str in sites_500m["Lokalitetensaktivitet"]:
        if pd.notna(activity_str) and str(activity_str).strip():
            activities = [a.strip() for a in str(activity_str).split(";") if a.strip()]
            all_activities.extend(activities)

    if not all_activities:
        return {"top_activities": {}, "total_activity_occurrences": 0}

    activity_counts = pd.Series(all_activities).value_counts()

    return {
        "top_activities": activity_counts.to_dict(),
        "total_activity_occurrences": len(all_activities),
    }


def _create_top_branches_danish_chart(results, output_dir, colors):
    """Create top 5 branches chart in Danish - filtered to sites â‰¤500m only."""

    plt.figure(figsize=(14, 8))

    # Use the 500m filtered data if available
    if (
        "branch_500m_analysis" in results
        and results["branch_500m_analysis"]["top_branches"]
    ):
        # Get top 5 branches from sites â‰¤500m
        top_branches = list(results["branch_500m_analysis"]["top_branches"].items())[:5]
        total_occurrences = results["branch_500m_analysis"]["total_branch_occurrences"]
        sites_count = results["distance_analysis"]["within_500m"]

        branch_names = [branch for branch, count in top_branches]
        branch_counts = [count for branch, count in top_branches]
        percentages = [(count / total_occurrences) * 100 for count in branch_counts]

        # Create horizontal bar chart
        bars = plt.barh(
            range(len(branch_names)),
            branch_counts,
            color=colors[0],
            alpha=0.8,
            height=0.6,
        )

        plt.yticks(
            range(len(branch_names)), branch_names, fontsize=16, fontweight="bold"
        )
        plt.xlabel("Antal forekomster", fontsize=18, fontweight="bold")
        plt.title(
            "Top 5 Brancher - Lokaliteter â‰¤500m uden stofdata\n({:,} lokaliteter analyseret)".format(
                sites_count
            ),
            fontsize=20,
            fontweight="bold",
            pad=25,
        )
        plt.grid(True, alpha=0.3, axis="x")

        # Set tick font sizes
        plt.xticks(fontsize=16, fontweight="bold")

        # Add value labels with percentages
        for i, (bar, count, pct) in enumerate(zip(bars, branch_counts, percentages)):
            width = bar.get_width()
            plt.text(
                width + max(branch_counts) * 0.01,
                bar.get_y() + bar.get_height() / 2,
                f"{count:,} ({pct:.1f}%)",
                ha="left",
                va="center",
                fontsize=14,
                fontweight="bold",
            )

        # Clean styling
        plt.gca().spines["top"].set_visible(False)
        plt.gca().spines["right"].set_visible(False)
        plt.gca().set_facecolor("#FAFAFA")

        plt.tight_layout()
        plt.savefig(
            os.path.join(output_dir, "top_5_brancher_500m_dansk.png"),
            dpi=300,
            bbox_inches="tight",
            facecolor="white",
        )
        plt.close()

        print(f"    âœ“ Top 5 brancher chart (â‰¤500m, Danish) saved")
    else:
        print(f"    ! No 500m branch data available - skipping filtered branch chart")


def _create_top_activities_danish_chart(results, output_dir, colors):
    """Create top 5 activities chart in Danish - filtered to sites â‰¤500m only."""

    plt.figure(figsize=(14, 8))

    # Use the 500m filtered data if available
    if (
        "activity_500m_analysis" in results
        and results["activity_500m_analysis"]["top_activities"]
    ):
        # Get top 5 activities from sites â‰¤500m
        top_activities = list(
            results["activity_500m_analysis"]["top_activities"].items()
        )[:5]
        total_occurrences = results["activity_500m_analysis"][
            "total_activity_occurrences"
        ]
        sites_count = results["distance_analysis"]["within_500m"]

        activity_names = [activity for activity, count in top_activities]
        activity_counts = [count for activity, count in top_activities]
        percentages = [(count / total_occurrences) * 100 for count in activity_counts]

        # Create horizontal bar chart
        bars = plt.barh(
            range(len(activity_names)),
            activity_counts,
            color=colors[1],
            alpha=0.8,
            height=0.6,
        )

        plt.yticks(
            range(len(activity_names)), activity_names, fontsize=16, fontweight="bold"
        )
        plt.xlabel("Antal forekomster", fontsize=18, fontweight="bold")
        plt.title(
            "Top 5 Aktiviteter - Lokaliteter â‰¤500m uden stofdata\n({:,} lokaliteter analyseret)".format(
                sites_count
            ),
            fontsize=20,
            fontweight="bold",
            pad=25,
        )
        plt.grid(True, alpha=0.3, axis="x")

        # Set tick font sizes
        plt.xticks(fontsize=16, fontweight="bold")

        # Add value labels with percentages
        for i, (bar, count, pct) in enumerate(zip(bars, activity_counts, percentages)):
            width = bar.get_width()
            plt.text(
                width + max(activity_counts) * 0.01,
                bar.get_y() + bar.get_height() / 2,
                f"{count:,} ({pct:.1f}%)",
                ha="left",
                va="center",
                fontsize=14,
                fontweight="bold",
            )

        # Clean styling
        plt.gca().spines["top"].set_visible(False)
        plt.gca().spines["right"].set_visible(False)
        plt.gca().set_facecolor("#FAFAFA")

        plt.tight_layout()
        plt.savefig(
            os.path.join(output_dir, "top_5_aktiviteter_500m_dansk.png"),
            dpi=300,
            bbox_inches="tight",
            facecolor="white",
        )
        plt.close()

        print(f"    âœ“ Top 5 aktiviteter chart (â‰¤500m, Danish) saved")
    else:
        print(
            f"    ! No 500m activity data available - skipping filtered activity chart"
        )


def _create_gvfk_impact_danish_chart(results, output_dir, colors):
    """Create GVFK impact chart in Danish."""

    if "generel_risiko_impact" not in results:
        print("    ! GVFK impact data not available")
        return

    gr_impact = results["generel_risiko_impact"]

    plt.figure(figsize=(12, 8))

    # Data for the chart
    categories = [
        'NuvÃ¦rende\n"generel risiko"',
        "Nye GVFK'er fra\nbranche-lokaliteter",
        'Udvidet total\n"generel risiko"',
    ]
    values = [
        gr_impact["current_generel_risiko_gvfks"],
        gr_impact["additional_gvfks"],
        gr_impact["expanded_generel_risiko_gvfks"],
    ]
    chart_colors = [colors[2], colors[3], colors[4]]

    # Create bar chart
    bars = plt.bar(categories, values, color=chart_colors, alpha=0.8, width=0.6)

    plt.ylabel("Antal GVFK'er", fontsize=18, fontweight="bold")
    plt.title(
        'GVFK-pÃ¥virkning af "generel risiko"\nInkludering af lokaliteter â‰¤500m uden stofdata',
        fontsize=20,
        fontweight="bold",
        pad=25,
    )
    plt.grid(True, alpha=0.3, axis="y")

    # Set tick font sizes
    plt.xticks(fontsize=16, fontweight="bold")
    plt.yticks(fontsize=16, fontweight="bold")

    # Add value labels
    for bar, value in zip(bars, values):
        height = bar.get_height()
        plt.text(
            bar.get_x() + bar.get_width() / 2.0,
            height + max(values) * 0.01,
            f"{value:,}",
            ha="center",
            va="bottom",
            fontsize=16,
            fontweight="bold",
        )

    # Add percentage increase annotation
    pct_increase = gr_impact["percentage_increase"]
    plt.text(
        0.5,
        0.95,
        f"Stigning: {pct_increase:.1f}%",
        transform=plt.gca().transAxes,
        fontsize=18,
        fontweight="bold",
        ha="center",
        va="top",
        bbox=dict(boxstyle="round,pad=0.5", facecolor=colors[4], alpha=0.3),
    )

    # Clean styling
    plt.gca().spines["top"].set_visible(False)
    plt.gca().spines["right"].set_visible(False)
    plt.gca().set_facecolor("#FAFAFA")

    plt.tight_layout()
    plt.savefig(
        os.path.join(output_dir, "gvfk_pavirkning_dansk.png"),
        dpi=300,
        bbox_inches="tight",
        facecolor="white",
    )
    plt.close()

    print(f"    âœ“ GVFK impact chart (Danish) saved")


def _create_distance_distribution_danish_chart(results, output_dir, colors):
    """Create distance distribution chart in Danish."""

    plt.figure(figsize=(12, 8))

    if "distance_analysis" in results:
        # Distance thresholds and counts
        thresholds = ["â‰¤250m", "â‰¤500m", "â‰¤1000m", "â‰¤1500m", "â‰¤2000m"]
        threshold_keys = [
            "within_250m",
            "within_500m",
            "within_1000m",
            "within_1500m",
            "within_2000m",
        ]

        counts = []
        for key in threshold_keys:
            if key in results["distance_analysis"]:
                counts.append(results["distance_analysis"][key])
            else:
                counts.append(0)

        total_sites = len(results.get("sites_data", []))  # Fallback if not available
        if total_sites == 0:
            total_sites = max(counts) if counts else 1  # Avoid division by zero

        percentages = [(count / total_sites) * 100 for count in counts]

        # Create bar chart
        bars = plt.bar(thresholds, counts, color=colors[5], alpha=0.8, width=0.6)

        plt.xlabel("AfstandstÃ¦rskel til vandlÃ¸b", fontsize=18, fontweight="bold")
        plt.ylabel("Antal lokaliteter", fontsize=18, fontweight="bold")
        plt.title(
            "Afstandsfordeling - Lokaliteter uden stofdata\n(16.866 lokaliteter analyseret)",
            fontsize=20,
            fontweight="bold",
            pad=25,
        )
        plt.grid(True, alpha=0.3, axis="y")

        # Set tick font sizes
        plt.xticks(fontsize=16, fontweight="bold")
        plt.yticks(fontsize=16, fontweight="bold")

        # Add value labels with percentages
        for bar, count, pct in zip(bars, counts, percentages):
            height = bar.get_height()
            plt.text(
                bar.get_x() + bar.get_width() / 2.0,
                height + max(counts) * 0.01,
                f"{count:,}\n({pct:.1f}%)",
                ha="center",
                va="bottom",
                fontsize=14,
                fontweight="bold",
            )

        # Highlight 500m threshold
        plt.axhline(
            y=results["distance_analysis"]["within_500m"],
            color=colors[3],
            linestyle="--",
            alpha=0.7,
        )
        plt.text(
            0.02,
            0.85,
            f"Lokaliteter â‰¤500m: {results['distance_analysis']['within_500m']:,} (22,0%)",
            transform=plt.gca().transAxes,
            fontsize=14,
            fontweight="bold",
            bbox=dict(boxstyle="round,pad=0.5", facecolor=colors[3], alpha=0.2),
        )

        # Clean styling
        plt.gca().spines["top"].set_visible(False)
        plt.gca().spines["right"].set_visible(False)
        plt.gca().set_facecolor("#FAFAFA")

        plt.tight_layout()
        plt.savefig(
            os.path.join(output_dir, "afstandsfordeling_dansk.png"),
            dpi=300,
            bbox_inches="tight",
            facecolor="white",
        )
        plt.close()

        print(f"    âœ“ Distance distribution chart (Danish) saved")


if __name__ == "__main__":
    import pandas as pd
    import os
    from config import get_output_path
    from risikovurdering.step5_utils import separate_sites_by_substance_data

    print("Running Branch Analysis on Parked Sites")
    print("=" * 50)

    # Generate parked sites from step4 output (same logic as step5_risk_assessment)
    step4_file = get_output_path("step4_final_distances_for_risk_assessment")
    if not os.path.exists(step4_file):
        print(f"Error: Could not find Step 4 results: {step4_file}")
        print("Please run the main workflow first (Steps 2-4)")
        exit(1)

    print(f"Loading Step 4 results...")
    distance_results = pd.read_csv(step4_file)
    print(f"  Loaded {len(distance_results):,} site-GVFK combinations")

    # Separate into qualifying (substance data) and parked (no substance data) sites
    print("\nSeparating sites by substance data availability...")
    sites_with_substances, parked_sites = separate_sites_by_substance_data(distance_results)
    
    print(f"\n  Sites with qualifying data: {len(sites_with_substances):,}")
    print(f"  Parked sites (branch-only): {len(parked_sites):,}")

    # Load step5b compound combinations for comparison
    substance_sites = None
    step5b_file = get_output_path("step5b_compound_combinations")
    if os.path.exists(step5b_file):
        substance_sites = pd.read_csv(step5b_file)
        if "Lokalitet_ID" in substance_sites.columns:
            substance_sites = substance_sites.drop_duplicates(subset="Lokalitet_ID")
        print(f"  Step 5b substance sites: {len(substance_sites):,} (after deduplication)")
    else:
        print("  Step 5b file not found - running analysis on branch-only sites only")

    # Run the branch analysis
    print(f"\nStarting comprehensive branch analysis...")
    try:
        results = run_branch_analysis(parked_sites, substance_sites)

        # Create Danish presentation charts
        output_dir = os.path.join(RESULTS_PATH, "branch_analysis")
        create_danish_presentation_charts(results, parked_sites, output_dir)

        print(f"\n✓ Branch analysis completed successfully!")
        print(f"Results saved to: {output_dir}")
        print(
            f"Danish presentation charts saved to: {os.path.join(output_dir, 'Presentation')}"
        )
    except Exception as e:
        print(f"Error during analysis: {e}")
        import traceback

        traceback.print_exc()
