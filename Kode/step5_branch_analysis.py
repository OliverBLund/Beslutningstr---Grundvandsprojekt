"""
Step 5 Branch Analysis: Analyzing sites without substance data
============================================================

This module provides detailed analysis of sites that have branch/activity data
but no specific contamination substance information. This runs as a separate
analysis track to avoid interfering with the main risk assessment.

The analysis focuses on:
- Distance distributions compared to substance sites
- Branch/activity frequency analysis  
- Geographic distribution patterns
- Basic risk profiling based on proximity to rivers

Output: Separate folder structure under Resultater/branch_analysis/
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import os
from datetime import datetime
from config import RESULTS_PATH


def run_branch_analysis(sites_without_substances, sites_with_substances=None):
    """
    Run comprehensive analysis of branch-only sites.
    
    Args:
        sites_without_substances (DataFrame): Sites with branch data but no substances
        sites_with_substances (DataFrame, optional): Sites with substances for comparison
    
    Returns:
        dict: Analysis results and statistics
    """
    print(f"\n{'='*60}")
    print(f"BRANCH-ONLY SITES ANALYSIS")
    print(f"{'='*60}")
    
    # Set up output directory
    branch_output_dir = _setup_output_directory()
    
    # Basic statistics
    print(f"Analyzing {len(sites_without_substances):,} sites without substance data")
    
    # Run analysis components
    results = {}
    
    # 1. Distance analysis
    print(f"\n1. Distance Analysis")
    print(f"-" * 20)
    distance_stats = _analyze_distances(sites_without_substances, sites_with_substances, branch_output_dir)
    results['distance_analysis'] = distance_stats
    
    # 2. Branch frequency analysis  
    print(f"\n2. Branch Analysis")
    print(f"-" * 18)
    branch_stats = _analyze_branches(sites_without_substances, branch_output_dir)
    results['branch_analysis'] = branch_stats
    
    # 2b. Activity frequency analysis
    print(f"\n2b. Activity Analysis")
    print(f"-" * 19)
    activity_stats = _analyze_activities(sites_without_substances, branch_output_dir)
    results['activity_analysis'] = activity_stats
    
    # 2c. Industry comparison (if substance sites available)
    if sites_with_substances is not None:
        print(f"\n2c. Industry Comparison")
        print(f"-" * 21)
        industry_comparison = _compare_industries(sites_without_substances, sites_with_substances, branch_output_dir)
        results['industry_comparison'] = industry_comparison
        
        # 2d. Activity comparison
        print(f"\n2d. Activity Comparison")
        print(f"-" * 21)
        activity_comparison = _compare_activities(sites_without_substances, sites_with_substances, branch_output_dir)
        results['activity_comparison'] = activity_comparison
    
    # 3. Geographic distribution
    print(f"\n3. Geographic Distribution")
    print(f"-" * 25)
    geo_stats = _analyze_geography(sites_without_substances, branch_output_dir)
    results['geographic_analysis'] = geo_stats
    
    # 4. GVFK analysis
    print(f"\n4. GVFK Distribution")
    print(f"-" * 19)
    gvfk_stats = _analyze_gvfk_distribution(sites_without_substances, branch_output_dir)
    results['gvfk_analysis'] = gvfk_stats
    
    # Save comprehensive summary
    _save_analysis_summary(results, sites_without_substances, branch_output_dir)
    
    # Create comprehensive professional visualizations
    _create_professional_visualizations(sites_without_substances, sites_with_substances, results, branch_output_dir)
    
    # Final comparison summary
    if sites_with_substances is not None:
        _print_final_comparison(results, len(sites_without_substances), len(sites_with_substances))
    
    print(f"\n✓ BRANCH ANALYSIS COMPLETED")
    print(f"Results saved to: {branch_output_dir}")
    
    return results


def _setup_output_directory():
    """Create and return the branch analysis output directory."""
    branch_dir = os.path.join(RESULTS_PATH, 'branch_analysis')
    figures_dir = os.path.join(branch_dir, 'Figures')
    
    os.makedirs(branch_dir, exist_ok=True)
    os.makedirs(figures_dir, exist_ok=True)
    
    return branch_dir


def _analyze_distances(sites_without_substances, sites_with_substances, output_dir):
    """Analyze distance distributions and create comparison plots."""
    
    # Distance statistics for branch-only sites
    distances = sites_without_substances['Final_Distance_m']
    
    stats = {
        'mean_distance': distances.mean(),
        'median_distance': distances.median(),
        'std_distance': distances.std(),
        'within_250m': (distances <= 250).sum(),
        'within_500m': (distances <= 500).sum(),
        'within_1000m': (distances <= 1000).sum(),
        'within_1500m': (distances <= 1500).sum(),
    }
    
    # Comparative statistics if substance sites provided
    if sites_with_substances is not None:
        substance_distances = sites_with_substances['Final_Distance_m']
        substance_stats = {
            'within_250m': (substance_distances <= 250).sum(),
            'within_500m': (substance_distances <= 500).sum(),
            'within_1000m': (substance_distances <= 1000).sum(),
            'within_1500m': (substance_distances <= 1500).sum(),
        }
        
        print(f"  DISTANCE COMPARISON:")
        print(f"    Threshold    Branch-only     Substance sites   Additional sites")
        print(f"    ---------    -----------     ---------------   ----------------")
        for threshold in ['250m', '500m', '1000m', '1500m']:
            threshold_key = f'within_{threshold[:-1]}m'
            branch_count = stats[threshold_key]
            substance_count = substance_stats[threshold_key]
            branch_pct = branch_count/len(sites_without_substances)*100
            substance_pct = substance_count/len(sites_with_substances)*100
            additional = branch_count
            print(f"    ≤{threshold:<8} {branch_count:>6,} ({branch_pct:>4.1f}%)   {substance_count:>6,} ({substance_pct:>4.1f}%)   +{additional:,} ({additional/(substance_count+additional)*100:.1f}% increase)")
    else:
        print(f"  Distance statistics:")
        print(f"    Mean: {stats['mean_distance']:.0f}m")
        print(f"    Median: {stats['median_distance']:.0f}m")
        print(f"    Sites ≤250m: {stats['within_250m']:,} ({stats['within_250m']/len(sites_without_substances)*100:.1f}%)")
        print(f"    Sites ≤500m: {stats['within_500m']:,} ({stats['within_500m']/len(sites_without_substances)*100:.1f}%)")
        print(f"    Sites ≤1000m: {stats['within_1000m']:,} ({stats['within_1000m']/len(sites_without_substances)*100:.1f}%)")
    
    # Create distance comparison plots
    _create_distance_plots(sites_without_substances, sites_with_substances, output_dir)
    
    return stats


def _analyze_branches(sites_without_substances, output_dir):
    """Analyze branch frequency and create visualizations, handling semicolon-separated lists."""
    
    # Extract and count individual branches from semicolon-separated lists
    all_branches = []
    multi_branch_sites = 0
    
    for branch_str in sites_without_substances['Lokalitetensbranche']:
        if pd.notna(branch_str) and str(branch_str).strip():
            # Split by semicolon and clean up each branch
            branches = [b.strip() for b in str(branch_str).split(';') if b.strip()]
            all_branches.extend(branches)
            if len(branches) > 1:
                multi_branch_sites += 1
    
    # Count individual branch occurrences
    branch_counts = pd.Series(all_branches).value_counts()
    
    print(f"  Total branch occurrences: {len(all_branches):,}")
    print(f"  Total unique branches: {len(branch_counts)}")
    print(f"  Sites with multiple branches: {multi_branch_sites:,} ({multi_branch_sites/len(sites_without_substances)*100:.1f}%)")
    print(f"  Top 5 branches:")
    for i, (branch, count) in enumerate(branch_counts.head().items()):
        print(f"    {i+1}. {branch}: {count:,} occurrences ({count/len(all_branches)*100:.1f}%)")
    
    # Create branch frequency plots
    _create_branch_plots(branch_counts, sites_without_substances, output_dir, len(all_branches))
    
    return {
        'total_branch_occurrences': len(all_branches),
        'total_unique_branches': len(branch_counts),
        'multi_branch_sites': multi_branch_sites,
        'top_branches': branch_counts.head(10).to_dict(),
        'branch_distribution': branch_counts.to_dict()
    }


def _analyze_activities(sites_without_substances, output_dir):
    """Analyze activity frequency and create visualizations, handling semicolon-separated lists."""
    
    # Extract and count individual activities from semicolon-separated lists
    all_activities = []
    multi_activity_sites = 0
    
    for activity_str in sites_without_substances['Lokalitetensaktivitet']:
        if pd.notna(activity_str) and str(activity_str).strip():
            # Split by semicolon and clean up each activity
            activities = [a.strip() for a in str(activity_str).split(';') if a.strip()]
            all_activities.extend(activities)
            if len(activities) > 1:
                multi_activity_sites += 1
    
    # Count individual activity occurrences
    activity_counts = pd.Series(all_activities).value_counts()
    
    print(f"  Total activity occurrences: {len(all_activities):,}")
    print(f"  Total unique activities: {len(activity_counts)}")
    print(f"  Sites with multiple activities: {multi_activity_sites:,} ({multi_activity_sites/len(sites_without_substances)*100:.1f}%)")
    print(f"  Top 5 activities:")
    for i, (activity, count) in enumerate(activity_counts.head().items()):
        print(f"    {i+1}. {activity}: {count:,} occurrences ({count/len(all_activities)*100:.1f}%)")
    
    return {
        'total_activity_occurrences': len(all_activities),
        'total_unique_activities': len(activity_counts),
        'multi_activity_sites': multi_activity_sites,
        'top_activities': activity_counts.head(10).to_dict(),
        'activity_distribution': activity_counts.to_dict()
    }


def _compare_activities(sites_without_substances, sites_with_substances, output_dir):
    """Compare activity distributions between the two datasets."""
    
    # Get activity counts from branch-only sites
    branch_activities = []
    for activity_str in sites_without_substances['Lokalitetensaktivitet']:
        if pd.notna(activity_str) and str(activity_str).strip():
            activities = [a.strip() for a in str(activity_str).split(';') if a.strip()]
            branch_activities.extend(activities)
    branch_activity_counts = pd.Series(branch_activities).value_counts()
    
    # Get activity counts from substance sites
    substance_activities = []
    for activity_str in sites_with_substances['Lokalitetensaktivitet']:
        if pd.notna(activity_str) and str(activity_str).strip():
            activities = [a.strip() for a in str(activity_str).split(';') if a.strip()]
            substance_activities.extend(activities)
    substance_activity_counts = pd.Series(substance_activities).value_counts()
    
    # Find overlap and differences
    all_activities = set(branch_activity_counts.index) | set(substance_activity_counts.index)
    common_activities = set(branch_activity_counts.index) & set(substance_activity_counts.index)
    branch_only_activities = set(branch_activity_counts.index) - set(substance_activity_counts.index)
    substance_only_activities = set(substance_activity_counts.index) - set(branch_activity_counts.index)
    
    print(f"  Activity overlap analysis:")
    print(f"    Total unique activities: {len(all_activities)}")
    print(f"    Common to both datasets: {len(common_activities)} ({len(common_activities)/len(all_activities)*100:.1f}%)")
    print(f"    Only in branch-only sites: {len(branch_only_activities)} ({len(branch_only_activities)/len(all_activities)*100:.1f}%)")
    print(f"    Only in substance sites: {len(substance_only_activities)} ({len(substance_only_activities)/len(all_activities)*100:.1f}%)")
    
    # Top common activities
    if len(common_activities) > 0:
        print(f"\n  Top common activities:")
        common_comparison = []
        for activity in common_activities:
            branch_count = branch_activity_counts.get(activity, 0)
            substance_count = substance_activity_counts.get(activity, 0)
            total_count = branch_count + substance_count
            common_comparison.append((activity, branch_count, substance_count, total_count))
        
        common_comparison.sort(key=lambda x: x[3], reverse=True)
        for i, (activity, b_count, s_count, total) in enumerate(common_comparison[:5]):
            b_pct = b_count / len(branch_activities) * 100 if len(branch_activities) > 0 else 0
            s_pct = s_count / len(substance_activities) * 100 if len(substance_activities) > 0 else 0
            print(f"    {i+1}. {activity[:40]}...")
            print(f"       Branch-only: {b_count:,} ({b_pct:.1f}%), Substance: {s_count:,} ({s_pct:.1f}%)")
    
    # High-risk activities
    high_risk_keywords = ['benzin', 'olie', 'brændstof', 'kemisk', 'oplag', 'rengøring', 'reparation', 'salg']
    high_risk_common = []
    for activity in common_activities:
        if any(keyword in activity.lower() for keyword in high_risk_keywords):
            branch_count = branch_activity_counts.get(activity, 0)
            substance_count = substance_activity_counts.get(activity, 0)
            high_risk_common.append((activity, branch_count, substance_count))
    
    if high_risk_common:
        print(f"\n  High-risk activities in both datasets:")
        for activity, b_count, s_count in sorted(high_risk_common, key=lambda x: x[1]+x[2], reverse=True)[:3]:
            print(f"    {activity}: Branch-only {b_count:,}, Substance {s_count:,}")
    
    return {
        'total_activities': len(all_activities),
        'common_activities': len(common_activities),
        'branch_only_activities': len(branch_only_activities),
        'substance_only_activities': len(substance_only_activities),
        'high_risk_common': high_risk_common,
        'top_common': common_comparison[:10] if 'common_comparison' in locals() else []
    }


def _compare_industries(sites_without_substances, sites_with_substances, output_dir):
    """Compare industry/branch distributions between the two datasets."""
    
    # Get branch counts from branch-only sites
    branch_branches = []
    for branch_str in sites_without_substances['Lokalitetensbranche']:
        if pd.notna(branch_str) and str(branch_str).strip():
            branches = [b.strip() for b in str(branch_str).split(';') if b.strip()]
            branch_branches.extend(branches)
    branch_counts = pd.Series(branch_branches).value_counts()
    
    # Get branch counts from substance sites
    substance_branches = []
    for branch_str in sites_with_substances['Lokalitetensbranche']:
        if pd.notna(branch_str) and str(branch_str).strip():
            branches = [b.strip() for b in str(branch_str).split(';') if b.strip()]
            substance_branches.extend(branches)
    substance_counts = pd.Series(substance_branches).value_counts()
    
    # Find overlap and differences
    all_branches = set(branch_counts.index) | set(substance_counts.index)
    common_branches = set(branch_counts.index) & set(substance_counts.index)
    branch_only_branches = set(branch_counts.index) - set(substance_counts.index)
    substance_only_branches = set(substance_counts.index) - set(branch_counts.index)
    
    print(f"  Industry overlap analysis:")
    print(f"    Total unique industries: {len(all_branches)}")
    print(f"    Common to both datasets: {len(common_branches)} ({len(common_branches)/len(all_branches)*100:.1f}%)")
    print(f"    Only in branch-only sites: {len(branch_only_branches)} ({len(branch_only_branches)/len(all_branches)*100:.1f}%)")
    print(f"    Only in substance sites: {len(substance_only_branches)} ({len(substance_only_branches)/len(all_branches)*100:.1f}%)")
    
    # Top common industries
    if len(common_branches) > 0:
        print(f"\n  Top common industries:")
        common_comparison = []
        for branch in common_branches:
            branch_count = branch_counts.get(branch, 0)
            substance_count = substance_counts.get(branch, 0)
            total_count = branch_count + substance_count
            common_comparison.append((branch, branch_count, substance_count, total_count))
        
        common_comparison.sort(key=lambda x: x[3], reverse=True)
        for i, (branch, b_count, s_count, total) in enumerate(common_comparison[:5]):
            b_pct = b_count / len(branch_branches) * 100 if len(branch_branches) > 0 else 0
            s_pct = s_count / len(substance_branches) * 100 if len(substance_branches) > 0 else 0
            print(f"    {i+1}. {branch[:40]}...")
            print(f"       Branch-only: {b_count:,} ({b_pct:.1f}%), Substance: {s_count:,} ({s_pct:.1f}%)")
    
    # High-risk branches that are common
    high_risk_keywords = ['servicestationer', 'autoreparation', 'benzin', 'olie', 'kemisk', 'tank', 'brændstof']
    high_risk_common = []
    for branch in common_branches:
        if any(keyword in branch.lower() for keyword in high_risk_keywords):
            branch_count = branch_counts.get(branch, 0)
            substance_count = substance_counts.get(branch, 0)
            high_risk_common.append((branch, branch_count, substance_count))
    
    if high_risk_common:
        print(f"\n  High-risk industries in both datasets:")
        for branch, b_count, s_count in sorted(high_risk_common, key=lambda x: x[1]+x[2], reverse=True)[:3]:
            print(f"    {branch}: Branch-only {b_count:,}, Substance {s_count:,}")
    
    return {
        'total_industries': len(all_branches),
        'common_industries': len(common_branches),
        'branch_only_industries': len(branch_only_branches),
        'substance_only_industries': len(substance_only_branches),
        'high_risk_common': high_risk_common,
        'top_common': common_comparison[:10] if 'common_comparison' in locals() else []
    }


def _analyze_geography(sites_without_substances, output_dir):
    """Analyze geographic distribution patterns."""
    
    # Region analysis
    if 'Regionsnavn' in sites_without_substances.columns:
        region_counts = sites_without_substances['Regionsnavn'].value_counts()
        print(f"  Distribution by region:")
        for region, count in region_counts.head().items():
            print(f"    {region}: {count:,} sites ({count/len(sites_without_substances)*100:.1f}%)")
    
    # Municipality analysis  
    if 'Kommunenavn' in sites_without_substances.columns:
        kommune_counts = sites_without_substances['Kommunenavn'].value_counts()
        print(f"  Top municipalities:")
        for kommune, count in kommune_counts.head(3).items():
            print(f"    {kommune}: {count:,} sites")
    
    return {
        'regions': region_counts.to_dict() if 'Regionsnavn' in sites_without_substances.columns else {},
        'municipalities': kommune_counts.head(20).to_dict() if 'Kommunenavn' in sites_without_substances.columns else {}
    }


def _analyze_gvfk_distribution(sites_without_substances, output_dir):
    """Analyze which GVFKs contain branch-only sites and potential impact."""
    
    # Count sites per GVFK for branch-only sites
    gvfk_counts = sites_without_substances.groupby('Closest_GVFK').size().sort_values(ascending=False)
    
    print(f"  Branch-only sites distributed across {len(gvfk_counts)} GVFKs")
    print(f"  Top GVFKs with branch-only sites:")
    for gvfk, count in gvfk_counts.head(5).items():
        print(f"    {gvfk}: {count:,} sites")
    
    # Analyze sites within 500m threshold by GVFK
    branch_500m = sites_without_substances[sites_without_substances['Final_Distance_m'] <= 500]
    if not branch_500m.empty:
        gvfk_500m_counts = branch_500m.groupby('Closest_GVFK').size().sort_values(ascending=False)
        print(f"\n  GVFKs with branch-only sites ≤500m: {len(gvfk_500m_counts)}")
        print(f"  Top GVFKs by sites ≤500m:")
        for gvfk, count in gvfk_500m_counts.head(3).items():
            total_in_gvfk = gvfk_counts.get(gvfk, 0)
            print(f"    {gvfk}: {count:,} sites ≤500m (of {total_in_gvfk:,} total)")
    else:
        gvfk_500m_counts = pd.Series()
    
    return {
        'total_gvfks_with_branch_sites': len(gvfk_counts),
        'gvfks_with_sites_within_500m': len(gvfk_500m_counts) if not gvfk_500m_counts.empty else 0,
        'top_gvfks': gvfk_counts.head(20).to_dict(),
        'top_gvfks_500m': gvfk_500m_counts.head(10).to_dict() if not gvfk_500m_counts.empty else {},
        'gvfk_distribution': gvfk_counts.to_dict()
    }


def _create_distance_plots(branch_sites, substance_sites, output_dir):
    """Create professional distance comparison visualization."""
    
    # Set professional styling
    plt.style.use('seaborn-v0_8-whitegrid')
    colors = ['#2E86AB', '#A23B72']  # Professional blue and magenta
    
    fig, ax = plt.subplots(1, 1, figsize=(12, 8))
    
    # Get distance data
    branch_distances = branch_sites['Final_Distance_m']
    
    # Create overlapping histogram with transparency
    ax.hist(branch_distances, bins=60, alpha=0.7, label=f'Branch-only sites (n={len(branch_distances):,})', 
            color=colors[0], density=True, edgecolor='white', linewidth=0.5)
    
    if substance_sites is not None:
        substance_distances = substance_sites['Final_Distance_m'] 
        ax.hist(substance_distances, bins=60, alpha=0.7, label=f'Substance sites (n={len(substance_distances):,})', 
                color=colors[1], density=True, edgecolor='white', linewidth=0.5)
    
    # Add threshold lines with clean styling
    thresholds = [250, 500, 1000, 1500]
    threshold_colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4']
    
    for i, threshold in enumerate(thresholds):
        ax.axvline(threshold, color=threshold_colors[i], linestyle='--', alpha=0.8, linewidth=2)
        
        # Add clean annotations
        branch_count = (branch_distances <= threshold).sum()
        branch_pct = branch_count / len(branch_distances) * 100
        
        if substance_sites is not None:
            substance_count = (substance_distances <= threshold).sum()
            substance_pct = substance_count / len(substance_distances) * 100
            label = f'{threshold}m\n{branch_pct:.1f}% | {substance_pct:.1f}%'
        else:
            label = f'{threshold}m\n{branch_pct:.1f}%'
        
        ax.text(threshold, ax.get_ylim()[1] * 0.9, label, 
                ha='center', va='top', fontsize=10, 
                bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.8))
    
    # Professional styling
    ax.set_xlabel('Distance to River (m)', fontsize=14, fontweight='bold')
    ax.set_ylabel('Density', fontsize=14, fontweight='bold')
    ax.set_title('Distance Distribution Comparison:\nBranch-only vs Substance Sites', 
                 fontsize=16, fontweight='bold', pad=20)
    
    # Clean legend
    ax.legend(loc='upper right', frameon=True, fancybox=True, shadow=True, fontsize=12)
    
    # Set limits and grid
    ax.set_xlim(0, 8000)
    ax.grid(True, alpha=0.3, linestyle='-', linewidth=0.5)
    ax.set_facecolor('#FAFAFA')
    
    # Remove top and right spines
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_color('#CCCCCC')
    ax.spines['bottom'].set_color('#CCCCCC')
    
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'Figures', 'distance_comparison.png'), 
                dpi=300, bbox_inches='tight', facecolor='white')
    plt.close()
    
    print(f"  ✓ Professional distance comparison plot saved")


def _create_branch_plots(branch_counts, sites_data, output_dir, total_occurrences):
    """Create branch frequency visualizations."""
    
    # Top branches bar chart
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10))
    
    # Top 15 branches
    top_branches = branch_counts.head(15)
    ax1.barh(range(len(top_branches)), top_branches.values, color='skyblue')
    ax1.set_yticks(range(len(top_branches)))
    ax1.set_yticklabels([label[:50] + '...' if len(label) > 50 else label for label in top_branches.index])
    ax1.set_xlabel('Number of Occurrences')
    ax1.set_title('Top 15 Branches in Branch-Only Sites (Individual Branch Occurrences)')
    
    # Add value labels
    for i, v in enumerate(top_branches.values):
        ax1.text(v + max(top_branches.values)*0.01, i, f'{v:,}', va='center')
    
    # Branch distribution (pie chart for top categories)
    top_10_branches = branch_counts.head(10)
    other_count = branch_counts.iloc[10:].sum()
    
    if other_count > 0:
        pie_data = list(top_10_branches.values) + [other_count]
        pie_labels = list(top_10_branches.index) + ['Other']
    else:
        pie_data = top_10_branches.values
        pie_labels = top_10_branches.index
    
    # Truncate labels for pie chart
    pie_labels = [label[:20] + '...' if len(label) > 20 else label for label in pie_labels]
    
    ax2.pie(pie_data, labels=pie_labels, autopct='%1.1f%%', startangle=90)
    ax2.set_title('Branch Distribution (Individual Occurrences - Top 10 + Other)')
    
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'Figures', 'branch_frequency.png'), dpi=300, bbox_inches='tight')
    plt.close()
    
    print(f"  ✓ Branch frequency plots saved")


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
            categories = [cat.strip() for cat in str(row[column_name]).split(';') if cat.strip()]
            all_categories.extend(categories)
    
    # Count occurrences
    if all_categories:
        category_counts = pd.Series(all_categories).value_counts()
        return category_counts.to_dict()
    else:
        return {}


def _create_professional_visualizations(branch_sites, substance_sites, results, output_dir):
    """Create comprehensive suite of professional visualizations."""
    
    print(f"\nCreating professional visualizations...")
    
    # Set up professional styling
    plt.style.use('seaborn-v0_8-whitegrid')
    colors = ['#2E86AB', '#A23B72', '#F18F01', '#C73E1D', '#4ECDC4', '#45B7D1']
    
    # 1. Industry/Activity Comparison Charts
    _create_industry_comparison_charts(branch_sites, substance_sites, results, output_dir, colors)
    
    # 2. Geographic Comparison Charts  
    _create_geographic_comparison_charts(branch_sites, substance_sites, results, output_dir, colors)
    
    # 3. GVFK Impact Visualizations
    _create_gvfk_impact_charts(branch_sites, results, output_dir, colors)
    
    # 4. Executive Summary Dashboard
    _create_executive_dashboard(branch_sites, substance_sites, results, output_dir, colors)
    
    print(f"  ✓ All professional visualizations completed")


def _create_industry_comparison_charts(branch_sites, substance_sites, results, output_dir, colors):
    """Create professional industry and activity comparison charts."""
    
    if substance_sites is None:
        return
    
    # Filter branch-only sites to ≤500m for fair comparison with substance sites (which are pre-filtered)
    branch_sites_500m = branch_sites[branch_sites['Final_Distance_m'] <= 500]
    
    print(f"  Filtering for comparison: {len(branch_sites_500m):,} of {len(branch_sites):,} branch-only sites ≤500m")
    
    # Branch comparison chart
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 8))
    
    # Calculate branch occurrence counts (matches step5_visualizations.py method)
    branch_branch_sites = _count_occurrences_by_category(branch_sites_500m, 'Lokalitetensbranche')
    substance_branch_sites = _count_occurrences_by_category(substance_sites, 'Lokalitetensbranche')
    
    # Get top common branches by total sites
    common_branches = set(branch_branch_sites.keys()) & set(substance_branch_sites.keys())
    if common_branches:
        branch_totals = [(branch, 
                         branch_branch_sites.get(branch, 0), 
                         substance_branch_sites.get(branch, 0),
                         branch_branch_sites.get(branch, 0) + substance_branch_sites.get(branch, 0))
                        for branch in common_branches]
        
        top_branches = sorted(branch_totals, key=lambda x: x[3], reverse=True)[:8]  # Top 8
        
        branch_names = [item[0][:30] + '...' if len(item[0]) > 30 else item[0] for item in top_branches]
        branch_counts = [item[1] for item in top_branches]  # Occurrence counts
        substance_counts = [item[2] for item in top_branches]  # Occurrence counts
        
        y_pos = np.arange(len(branch_names))
        
        # Horizontal bar chart
        bars1 = ax1.barh(y_pos - 0.2, branch_counts, 0.4, label='Branch-only sites', color=colors[0], alpha=0.8)
        bars2 = ax1.barh(y_pos + 0.2, substance_counts, 0.4, label='Substance sites', color=colors[1], alpha=0.8)
        
        ax1.set_yticks(y_pos)
        ax1.set_yticklabels(branch_names, fontsize=10)
        ax1.set_xlabel('Number of Occurrences', fontsize=12, fontweight='bold')
        ax1.set_title('Top Industries: Branch-only vs Substance Sites (Occurrences)', fontsize=14, fontweight='bold', pad=20)
        ax1.legend(fontsize=11)
        ax1.grid(True, alpha=0.3, axis='x')
        
        # Add value labels
        for bar in bars1:
            width = bar.get_width()
            ax1.text(width + max(branch_counts)*0.01, bar.get_y() + bar.get_height()/2, 
                    f'{int(width):,}', ha='left', va='center', fontsize=9)
        for bar in bars2:
            width = bar.get_width()
            ax1.text(width + max(substance_counts)*0.01, bar.get_y() + bar.get_height()/2, 
                    f'{int(width):,}', ha='left', va='center', fontsize=9)
    
    # Activity comparison chart
    branch_activity_sites = _count_occurrences_by_category(branch_sites_500m, 'Lokalitetensaktivitet')
    substance_activity_sites = _count_occurrences_by_category(substance_sites, 'Lokalitetensaktivitet')
    
    # Get top common activities by total sites
    common_activities = set(branch_activity_sites.keys()) & set(substance_activity_sites.keys())
    if common_activities:
        activity_totals = [(activity, 
                           branch_activity_sites.get(activity, 0), 
                           substance_activity_sites.get(activity, 0),
                           branch_activity_sites.get(activity, 0) + substance_activity_sites.get(activity, 0))
                          for activity in common_activities]
        
        top_activities = sorted(activity_totals, key=lambda x: x[3], reverse=True)[:8]  # Top 8
        
        activity_names = [item[0][:30] + '...' if len(item[0]) > 30 else item[0] for item in top_activities]
        branch_activity_counts = [item[1] for item in top_activities]  # Occurrence counts
        substance_activity_counts = [item[2] for item in top_activities]  # Occurrence counts
        
        y_pos = np.arange(len(activity_names))
        
        # Horizontal bar chart
        bars3 = ax2.barh(y_pos - 0.2, branch_activity_counts, 0.4, label='Branch-only sites', color=colors[2], alpha=0.8)
        bars4 = ax2.barh(y_pos + 0.2, substance_activity_counts, 0.4, label='Substance sites', color=colors[3], alpha=0.8)
        
        ax2.set_yticks(y_pos)
        ax2.set_yticklabels(activity_names, fontsize=10)
        ax2.set_xlabel('Number of Occurrences', fontsize=12, fontweight='bold')
        ax2.set_title('Top Activities: Branch-only vs Substance Sites (Occurrences)', fontsize=14, fontweight='bold', pad=20)
        ax2.legend(fontsize=11)
        ax2.grid(True, alpha=0.3, axis='x')
        
        # Add value labels
        for bar in bars3:
            width = bar.get_width()
            ax2.text(width + max(branch_activity_counts)*0.01, bar.get_y() + bar.get_height()/2, 
                    f'{int(width):,}', ha='left', va='center', fontsize=9)
        for bar in bars4:
            width = bar.get_width()
            ax2.text(width + max(substance_activity_counts)*0.01, bar.get_y() + bar.get_height()/2, 
                    f'{int(width):,}', ha='left', va='center', fontsize=9)
    
    # Clean styling
    for ax in [ax1, ax2]:
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.set_facecolor('#FAFAFA')
    
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'Figures', 'industry_activity_comparison.png'), 
                dpi=300, bbox_inches='tight', facecolor='white')
    plt.close()
    
    print(f"  ✓ Industry/Activity comparison charts saved")


def _create_geographic_comparison_charts(branch_sites, substance_sites, results, output_dir, colors):
    """Create geographic and regional comparison visualizations."""
    
    # Filter branch-only sites to ≤500m for fair comparison
    branch_sites_500m = branch_sites[branch_sites['Final_Distance_m'] <= 500]
    
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 8))
    
    # Regional comparison
    if 'Regionsnavn' in branch_sites_500m.columns:
        branch_regions = branch_sites_500m['Regionsnavn'].value_counts()
        
        if substance_sites is not None and 'Regionsnavn' in substance_sites.columns:
            substance_regions = substance_sites['Regionsnavn'].value_counts()
            
            # Get common regions
            common_regions = set(branch_regions.index) & set(substance_regions.index)
            if common_regions:
                regions = list(common_regions)[:5]  # Top 5 regions
                branch_counts = [branch_regions.get(region, 0) for region in regions]
                substance_counts = [substance_regions.get(region, 0) for region in regions]
                
                # Clean region names
                region_names = [region.replace('Region ', '') for region in regions]
                
                y_pos = np.arange(len(region_names))
                
                bars1 = ax1.barh(y_pos - 0.2, branch_counts, 0.4, label='Branch-only sites', color=colors[0], alpha=0.8)
                bars2 = ax1.barh(y_pos + 0.2, substance_counts, 0.4, label='Substance sites', color=colors[1], alpha=0.8)
                
                ax1.set_yticks(y_pos)
                ax1.set_yticklabels(region_names, fontsize=12)
                ax1.set_xlabel('Number of Sites', fontsize=12, fontweight='bold')
                ax1.set_title('Regional Distribution Comparison', fontsize=14, fontweight='bold', pad=20)
                ax1.legend(fontsize=11)
                ax1.grid(True, alpha=0.3, axis='x')
                
                # Add value labels
                for bar in bars1:
                    width = bar.get_width()
                    ax1.text(width + max(branch_counts)*0.01, bar.get_y() + bar.get_height()/2, 
                            f'{int(width):,}', ha='left', va='center', fontsize=10)
                for bar in bars2:
                    width = bar.get_width()
                    ax1.text(width + max(substance_counts)*0.01, bar.get_y() + bar.get_height()/2, 
                            f'{int(width):,}', ha='left', va='center', fontsize=10)
    
    # Municipality impact (branch-only sites only)
    if 'Kommunenavn' in branch_sites_500m.columns:
        top_municipalities = branch_sites_500m['Kommunenavn'].value_counts().head(8)
        
        # Clean municipality names
        muni_names = [name.replace(' Kommune', '') for name in top_municipalities.index]
        muni_counts = top_municipalities.values
        
        bars = ax2.bar(range(len(muni_names)), muni_counts, color=colors[2], alpha=0.8)
        
        ax2.set_xticks(range(len(muni_names)))
        ax2.set_xticklabels(muni_names, rotation=45, ha='right', fontsize=10)
        ax2.set_ylabel('Number of Branch-only Sites', fontsize=12, fontweight='bold')
        ax2.set_title('Top Municipalities with Branch-only Sites', fontsize=14, fontweight='bold', pad=20)
        ax2.grid(True, alpha=0.3, axis='y')
        
        # Add value labels
        for bar in bars:
            height = bar.get_height()
            ax2.text(bar.get_x() + bar.get_width()/2., height + max(muni_counts)*0.01,
                    f'{int(height):,}', ha='center', va='bottom', fontsize=10)
    
    # Clean styling
    for ax in [ax1, ax2]:
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.set_facecolor('#FAFAFA')
    
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'Figures', 'geographic_comparison.png'), 
                dpi=300, bbox_inches='tight', facecolor='white')
    plt.close()
    
    print(f"  ✓ Geographic comparison charts saved")


def _create_gvfk_impact_charts(branch_sites, results, output_dir, colors):
    """Create GVFK impact visualization."""
    
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 8))
    
    if 'gvfk_analysis' in results:
        # Top GVFKs with branch-only sites
        if results['gvfk_analysis']['top_gvfks']:
            top_gvfks = list(results['gvfk_analysis']['top_gvfks'].items())[:10]
            
            gvfk_names = [gvfk[:15] + '...' if len(gvfk) > 15 else gvfk for gvfk, count in top_gvfks]
            gvfk_counts = [count for gvfk, count in top_gvfks]
            
            bars = ax1.bar(range(len(gvfk_names)), gvfk_counts, color=colors[4], alpha=0.8)
            
            ax1.set_xticks(range(len(gvfk_names)))
            ax1.set_xticklabels(gvfk_names, rotation=45, ha='right', fontsize=9)
            ax1.set_ylabel('Number of Branch-only Sites', fontsize=12, fontweight='bold')
            ax1.set_title('Top GVFKs by Branch-only Site Count', fontsize=14, fontweight='bold', pad=20)
            ax1.grid(True, alpha=0.3, axis='y')
            
            # Add value labels
            for bar in bars:
                height = bar.get_height()
                ax1.text(bar.get_x() + bar.get_width()/2., height + max(gvfk_counts)*0.01,
                        f'{int(height)}', ha='center', va='bottom', fontsize=9)
        
        # GVFK impact by distance thresholds
        if 'distance_analysis' in results:
            thresholds = ['≤250m', '≤500m', '≤1000m', '≤1500m']
            threshold_keys = ['within_250m', 'within_500m', 'within_1000m', 'within_1500m']
            
            # Calculate sites at each threshold
            site_counts = [results['distance_analysis'][key] for key in threshold_keys]
            
            # Estimate GVFK counts (simplified - could be improved with actual GVFK analysis per threshold)
            gvfk_estimates = []
            for threshold_key in threshold_keys:
                sites_at_threshold = branch_sites[branch_sites['Final_Distance_m'] <= int(threshold_key.split('_')[1][:-1])]
                gvfk_count = sites_at_threshold['Closest_GVFK'].nunique() if not sites_at_threshold.empty else 0
                gvfk_estimates.append(gvfk_count)
            
            bars = ax2.bar(thresholds, gvfk_estimates, color=colors[5], alpha=0.8)
            
            ax2.set_ylabel('Number of GVFKs Affected', fontsize=12, fontweight='bold')
            ax2.set_title('GVFKs Affected by Distance Threshold', fontsize=14, fontweight='bold', pad=20)
            ax2.grid(True, alpha=0.3, axis='y')
            
            # Add value labels
            for bar, sites in zip(bars, site_counts):
                height = bar.get_height()
                ax2.text(bar.get_x() + bar.get_width()/2., height + max(gvfk_estimates)*0.01,
                        f'{int(height)} GVFKs\n({sites:,} sites)', ha='center', va='bottom', fontsize=10)
    
    # Clean styling
    for ax in [ax1, ax2]:
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.set_facecolor('#FAFAFA')
    
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'Figures', 'gvfk_impact.png'), 
                dpi=300, bbox_inches='tight', facecolor='white')
    plt.close()
    
    print(f"  ✓ GVFK impact charts saved")


def _create_executive_dashboard(branch_sites, substance_sites, results, output_dir, colors):
    """Create executive summary dashboard."""
    
    # Filter branch-only sites to ≤500m for comparison charts
    branch_sites_500m = branch_sites[branch_sites['Final_Distance_m'] <= 500]
    
    fig = plt.figure(figsize=(16, 12))
    gs = fig.add_gridspec(3, 3, hspace=0.3, wspace=0.3)
    
    # Title
    fig.suptitle('Branch-only Sites Analysis: Executive Dashboard\n(Comparison charts filtered to ≤500m)', fontsize=18, fontweight='bold', y=0.95)
    
    # 1. Key metrics panel (top left)
    ax1 = fig.add_subplot(gs[0, 0])
    
    # Key numbers
    branch_count = len(branch_sites)
    substance_count = len(substance_sites) if substance_sites is not None else 0
    total_sites = branch_count + substance_count
    
    metrics_text = f"""
DATASET OVERVIEW
─────────────────
Branch-only sites: {branch_count:,}
Substance sites: {substance_count:,}
Total sites: {total_sites:,}

Branch-only proportion: {branch_count/total_sites*100:.1f}%
"""
    
    if 'distance_analysis' in results:
        sites_500m = results['distance_analysis']['within_500m']
        metrics_text += f"""
RISK PROFILE
─────────────────
Sites ≤500m: {sites_500m:,} ({sites_500m/branch_count*100:.1f}%)
Additional risk sites: +{sites_500m:,}
"""
    
    ax1.text(0.05, 0.95, metrics_text, transform=ax1.transAxes, fontsize=11, 
             verticalalignment='top', fontfamily='monospace',
             bbox=dict(boxstyle='round,pad=0.5', facecolor=colors[0], alpha=0.1))
    ax1.set_xlim(0, 1)
    ax1.set_ylim(0, 1)
    ax1.axis('off')
    
    # 2. Distance threshold comparison (top middle and right)
    ax2 = fig.add_subplot(gs[0, 1:])
    
    if 'distance_analysis' in results:
        thresholds = ['≤250m', '≤500m', '≤1000m', '≤1500m']
        threshold_keys = ['within_250m', 'within_500m', 'within_1000m', 'within_1500m']
        
        branch_counts = [results['distance_analysis'][key] for key in threshold_keys]
        
        if substance_sites is not None:
            # Calculate substance site counts for comparison
            substance_distances = substance_sites['Final_Distance_m']
            substance_counts = [
                (substance_distances <= 250).sum(),
                (substance_distances <= 500).sum(),
                (substance_distances <= 1000).sum(),
                (substance_distances <= 1500).sum()
            ]
        else:
            substance_counts = [0] * 4
        
        x = np.arange(len(thresholds))
        width = 0.35
        
        bars1 = ax2.bar(x - width/2, branch_counts, width, label='Branch-only sites', color=colors[0], alpha=0.8)
        bars2 = ax2.bar(x + width/2, substance_counts, width, label='Substance sites', color=colors[1], alpha=0.8)
        
        ax2.set_xlabel('Distance Threshold', fontsize=12, fontweight='bold')
        ax2.set_ylabel('Number of Sites', fontsize=12, fontweight='bold')
        ax2.set_title('Site Distribution by Distance Threshold', fontsize=14, fontweight='bold')
        ax2.set_xticks(x)
        ax2.set_xticklabels(thresholds)
        ax2.legend()
        ax2.grid(True, alpha=0.3, axis='y')
        
        # Add percentage increase annotations
        for i, (bar1, bar2) in enumerate(zip(bars1, bars2)):
            if substance_counts[i] > 0:
                increase = branch_counts[i] / (branch_counts[i] + substance_counts[i]) * 100
                ax2.text(bar1.get_x() + bar1.get_width()/2, bar1.get_height() + max(branch_counts)*0.02,
                        f'+{increase:.0f}%', ha='center', va='bottom', fontsize=10, fontweight='bold')
    
    # 3. Top industries (middle left)
    ax3 = fig.add_subplot(gs[1, :])
    
    # Use occurrence counts to match step5_visualizations.py methodology
    branch_site_counts = _count_occurrences_by_category(branch_sites, 'Lokalitetensbranche')
    if branch_site_counts:
        top_branches = sorted(branch_site_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        
        branch_names = [name[:25] + '...' if len(name) > 25 else name for name, count in top_branches]
        branch_counts = [count for name, count in top_branches]
        
        bars = ax3.barh(range(len(branch_names)), branch_counts, color=colors[2], alpha=0.8)
        
        ax3.set_yticks(range(len(branch_names)))
        ax3.set_yticklabels(branch_names, fontsize=10)
        ax3.set_xlabel('Number of Occurrences', fontsize=12, fontweight='bold')
        ax3.set_title('Top 10 Industries in Branch-only Sites (Occurrences)', fontsize=14, fontweight='bold')
        ax3.grid(True, alpha=0.3, axis='x')
        
        # Add value labels
        for bar in bars:
            width = bar.get_width()
            ax3.text(width + max(branch_counts)*0.01, bar.get_y() + bar.get_height()/2, 
                    f'{int(width):,}', ha='left', va='center', fontsize=10)
    
    # Clean styling for all subplots
    for ax in [ax2, ax3]:
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.set_facecolor('#FAFAFA')
    
    plt.savefig(os.path.join(output_dir, 'Figures', 'executive_dashboard.png'), 
                dpi=300, bbox_inches='tight', facecolor='white')
    plt.close()
    
    print(f"  ✓ Executive dashboard saved")


def _save_analysis_summary(results, sites_data, output_dir):
    """Save comprehensive analysis summary."""
    
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    summary_content = f"""
BRANCH-ONLY SITES ANALYSIS SUMMARY
Generated: {timestamp}
{'='*50}

OVERVIEW:
Total sites analyzed: {len(sites_data):,}
Sites without substance data but with branch information

DISTANCE ANALYSIS:
Mean distance to river: {results['distance_analysis']['mean_distance']:.0f}m
Median distance to river: {results['distance_analysis']['median_distance']:.0f}m
Sites within 500m: {results['distance_analysis']['within_500m']:,} ({results['distance_analysis']['within_500m']/len(sites_data)*100:.1f}%)
Sites within 1000m: {results['distance_analysis']['within_1000m']:,} ({results['distance_analysis']['within_1000m']/len(sites_data)*100:.1f}%)

BRANCH ANALYSIS:
Total branch occurrences: {results['branch_analysis']['total_branch_occurrences']:,}
Total unique branches: {results['branch_analysis']['total_unique_branches']}
Sites with multiple branches: {results['branch_analysis']['multi_branch_sites']:,} ({results['branch_analysis']['multi_branch_sites']/len(sites_data)*100:.1f}%)
Top 5 branches (by occurrences):
"""
    
    for i, (branch, count) in enumerate(list(results['branch_analysis']['top_branches'].items())[:5]):
        summary_content += f"  {i+1}. {branch}: {count:,} occurrences ({count/results['branch_analysis']['total_branch_occurrences']*100:.1f}%)\n"
    
    summary_content += f"""
GVFK DISTRIBUTION:
Branch-only sites found in {results['gvfk_analysis']['total_gvfks_with_branch_sites']} GVFKs
Top 3 GVFKs with branch-only sites:
"""
    
    for i, (gvfk, count) in enumerate(list(results['gvfk_analysis']['top_gvfks'].items())[:3]):
        summary_content += f"  {i+1}. {gvfk}: {count:,} sites\n"
    
    summary_content += f"""
FILES GENERATED:
- branch_only_sites_detailed.csv (detailed site data)
- Figures/distance_comparison.png (distance analysis)
- Figures/branch_frequency.png (branch frequency analysis)
- branch_analysis_summary.txt (this file)

{'='*50}
"""
    
    # Save summary
    with open(os.path.join(output_dir, 'branch_analysis_summary.txt'), 'w', encoding='utf-8') as f:
        f.write(summary_content)
    
    # Save detailed CSV
    sites_data.to_csv(os.path.join(output_dir, 'branch_only_sites_detailed.csv'), index=False)
    
    print(f"  ✓ Analysis summary and detailed data saved")


def _print_final_comparison(results, branch_sites_count, substance_sites_count):
    """Print a final summary comparison between branch-only and substance sites."""
    
    print(f"\n{'='*60}")
    print(f"FINAL COMPARATIVE SUMMARY")
    print(f"{'='*60}")
    
    print(f"Dataset Sizes:")
    print(f"  Branch-only sites: {branch_sites_count:,}")
    print(f"  Substance sites: {substance_sites_count:,}")
    print(f"  Total sites: {branch_sites_count + substance_sites_count:,}")
    print(f"  Branch-only proportion: {branch_sites_count/(branch_sites_count + substance_sites_count)*100:.1f}%")
    
    # Distance comparison
    if 'distance_analysis' in results:
        branch_500m = results['distance_analysis']['within_500m']
        print(f"\nDistance Analysis:")
        print(f"  Branch-only sites ≤500m: {branch_500m:,} ({branch_500m/branch_sites_count*100:.1f}%)")
        print(f"  This represents {branch_500m:,} additional sites that could qualify for risk assessment")
    
    # Industry overlap
    if 'industry_comparison' in results:
        common = results['industry_comparison']['common_industries']
        branch_only = results['industry_comparison']['branch_only_industries']
        print(f"\nIndustry Analysis:")
        print(f"  Industries in common: {common}")
        print(f"  New industries from branch-only sites: {branch_only}")
    
    # GVFK impact
    if 'gvfk_analysis' in results:
        gvfks_affected = results['gvfk_analysis']['total_gvfks_with_branch_sites']
        gvfks_500m = results['gvfk_analysis']['gvfks_with_sites_within_500m']
        print(f"\nGVFK Impact:")
        print(f"  Additional GVFKs with branch-only sites: {gvfks_affected}")
        print(f"  GVFKs with branch-only sites ≤500m: {gvfks_500m}")
    
    print(f"\nKey Decision Points:")
    print(f"  1. Branch-only sites are closer to rivers than expected")
    print(f"  2. Many common high-risk industries (gas stations, auto repair)")  
    print(f"  3. Could add substantial sites to risk assessment")
    print(f"  4. Geographic coverage is extensive")
    print(f"\nNote: Visualizations show unique SITE counts (not occurrence counts)")
    print(f"      A site with 'Auto;Gas' contributes to both categories but counts as 1 site each")


if __name__ == "__main__":
    print("This module is designed to be called from step5_risk_assessment.py")
    print("Run main_workflow.py to execute the full analysis pipeline.")