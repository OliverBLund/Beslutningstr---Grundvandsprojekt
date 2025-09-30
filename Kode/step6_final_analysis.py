"""
Step 6: Final Comprehensive Analysis
=====================================

Decision-support analysis comparing Core vs Expanded scenarios:
- Core: Step 5b compound-specific sites (substance data)
- Expanded: Core + branch-only sites (≤500m, no losseplads)

Analyzes GVFK progression, branch/activity patterns, and geographic distribution.
"""

import pandas as pd
import geopandas as gpd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import os
from collections import Counter

from config import get_output_path, get_visualization_path, GRUNDVAND_PATH, WORKFLOW_SETTINGS

# Professional styling
plt.rcParams.update({
    'font.family': ['Arial', 'DejaVu Sans', 'sans-serif'],
    'font.size': 10,
    'axes.titlesize': 14,
    'axes.labelsize': 12,
    'figure.dpi': 100,
    'savefig.dpi': 300,
    'savefig.bbox': 'tight'
})

COLORS = {
    'core': '#1E88E5',           # Blue for core scenario
    'expanded': '#FFC107',        # Amber for expanded
    'new_gvfk': '#FF5722',       # Red-orange for new GVFKs
    'shared': '#43A047',          # Green for shared
    'neutral': '#757575'          # Gray
}


# ============================================================================
# PHASE 1: DATA LOADING AND PREPARATION
# ============================================================================

def load_gvfk_area_volume():
    """
    Load GVFK area and volume data from CSV.

    Returns:
        dict: {gvfk_name: {'area_km2': float, 'volume_m3': float}}
    """
    print("\n[PHASE 1] Loading GVFK area/volume data...")

    # Path to area/volume file (one level up from GRUNDVAND_PATH, then into Data folder)
    grundvand_dir = os.path.dirname(GRUNDVAND_PATH)
    area_volume_path = os.path.join(grundvand_dir, "volumen areal_genbesøg.csv")

    if not os.path.exists(area_volume_path):
        print(f"Warning: Area/volume file not found at {area_volume_path}")
        return {}

    # Load with Danish decimal separator
    df = pd.read_csv(area_volume_path, sep=';', decimal=',', encoding='utf-8')

    # Create lookup dictionary
    gvfk_data = {}
    for _, row in df.iterrows():
        gvfk_name = row['GVFK']
        try:
            area = float(row['Areal [km2]'])
            volume = float(row['Volumen'])
            gvfk_data[gvfk_name] = {
                'area_km2': area,
                'volume_m3': volume
            }
        except (ValueError, KeyError) as e:
            continue

    print(f"  Loaded area/volume data for {len(gvfk_data)} GVFKs")
    return gvfk_data


def load_substance_sites():
    """
    Load Step 5b compound-specific sites (Core scenario).

    Returns:
        pd.DataFrame: Sites with substance data
    """
    print("\n[PHASE 1] Loading substance sites (Core scenario)...")

    sites_path = get_output_path('step5_compound_specific_sites')
    if not os.path.exists(sites_path):
        raise FileNotFoundError(f"Compound-specific sites not found: {sites_path}")

    substance_sites = pd.read_csv(sites_path)

    n_sites = len(substance_sites)
    n_gvfks = substance_sites['Closest_GVFK'].dropna().nunique()

    print(f"  Loaded {n_sites:,} substance sites across {n_gvfks} GVFKs")

    return substance_sites


def load_and_filter_branch_sites():
    """
    Load and filter branch-only sites (≤500m, no losseplads).

    Returns:
        pd.DataFrame: Filtered branch-only sites
    """
    print("\n[PHASE 1] Loading and filtering branch-only sites...")

    unknown_path = get_output_path('step5_unknown_substance_sites')
    if not os.path.exists(unknown_path):
        raise FileNotFoundError(f"Unknown substance sites not found: {unknown_path}")

    unknown_sites = pd.read_csv(unknown_path)

    print(f"  Total unknown substance sites: {len(unknown_sites):,}")

    # Filter 1: Distance ≤500m
    branch_sites = unknown_sites[unknown_sites['Final_Distance_m'] <= 500].copy()
    print(f"  After ≤500m filter: {len(branch_sites):,} sites")

    # Filter 2: Exclude losseplads keywords
    def has_losseplads(text):
        if pd.isna(text):
            return False
        text_lower = str(text).lower()
        keywords = ['losseplads', 'affald', 'depon', 'fyldplads', 'skraldeplads']
        return any(keyword in text_lower for keyword in keywords)

    branch_sites = branch_sites[
        ~(branch_sites['Lokalitetensbranche'].apply(has_losseplads) |
          branch_sites['Lokalitetensaktivitet'].apply(has_losseplads))
    ].copy()

    n_sites = len(branch_sites)
    n_gvfks = branch_sites['Closest_GVFK'].dropna().nunique()

    print(f"  After losseplads exclusion: {n_sites:,} sites")
    print(f"  Branch-only sites span {n_gvfks} GVFKs")

    return branch_sites


def categorize_gvfks(substance_sites, branch_sites):
    """
    Categorize GVFKs into shared, new, and substance-only groups.

    Args:
        substance_sites: Core scenario sites
        branch_sites: Branch-only sites

    Returns:
        dict: {
            'core_gvfks': set,
            'branch_gvfks': set,
            'shared_gvfks': set,
            'new_gvfks': set,
            'substance_only_gvfks': set,
            'expanded_gvfks': set
        }
    """
    print("\n[PHASE 1] Categorizing GVFKs...")

    core_gvfks = set(substance_sites['Closest_GVFK'].dropna().unique())
    branch_gvfks = set(branch_sites['Closest_GVFK'].dropna().unique())

    shared_gvfks = core_gvfks & branch_gvfks
    new_gvfks = branch_gvfks - core_gvfks
    substance_only_gvfks = core_gvfks - branch_gvfks
    expanded_gvfks = core_gvfks | branch_gvfks

    print(f"  Core GVFKs (substance sites): {len(core_gvfks)}")
    print(f"  Branch GVFKs (total): {len(branch_gvfks)}")
    print(f"  Shared GVFKs (both types): {len(shared_gvfks)}")
    print(f"  New GVFKs (branch-only): {len(new_gvfks)}")
    print(f"  Substance-only GVFKs: {len(substance_only_gvfks)}")
    print(f"  Expanded GVFKs (total): {len(expanded_gvfks)}")

    # Verify math
    assert len(shared_gvfks) + len(substance_only_gvfks) == len(core_gvfks)
    assert len(shared_gvfks) + len(new_gvfks) == len(branch_gvfks)

    return {
        'core_gvfks': core_gvfks,
        'branch_gvfks': branch_gvfks,
        'shared_gvfks': shared_gvfks,
        'new_gvfks': new_gvfks,
        'substance_only_gvfks': substance_only_gvfks,
        'expanded_gvfks': expanded_gvfks
    }


def filter_sites_by_gvfk_category(branch_sites, new_gvfks):
    """
    Filter branch-only sites to those in the "new" GVFKs.

    Args:
        branch_sites: All branch-only sites
        new_gvfks: Set of new GVFK names

    Returns:
        pd.DataFrame: Sites in new GVFKs only
    """
    print("\n[PHASE 1] Filtering sites in new GVFKs...")

    sites_in_new_gvfks = branch_sites[
        branch_sites['Closest_GVFK'].isin(new_gvfks)
    ].copy()

    print(f"  Sites in new {len(new_gvfks)} GVFKs: {len(sites_in_new_gvfks):,}")

    return sites_in_new_gvfks


def load_gvfk_shapefiles():
    """
    Load GVFK shapefiles for geographic analysis.

    Returns:
        dict: {'all_dk': GeoDataFrame, 'step2': GeoDataFrame, 'step3': GeoDataFrame}
    """
    print("\n[PHASE 1] Loading GVFK shapefiles...")

    shapefiles = {}

    # All Denmark
    if os.path.exists(GRUNDVAND_PATH):
        shapefiles['all_dk'] = gpd.read_file(GRUNDVAND_PATH)
        print(f"  All Denmark: {len(shapefiles['all_dk'])} GVFKs")

    # Step 2
    step2_path = get_output_path('step2_river_gvfk')
    if os.path.exists(step2_path):
        shapefiles['step2'] = gpd.read_file(step2_path)
        print(f"  Step 2 (river contact): {len(shapefiles['step2'])} GVFKs")

    # Step 3
    step3_path = get_output_path('step3_gvfk_polygons')
    if os.path.exists(step3_path):
        shapefiles['step3'] = gpd.read_file(step3_path)
        print(f"  Step 3 (V1/V2 sites): {len(shapefiles['step3'])} GVFKs")

    return shapefiles


def run_phase1():
    """
    Execute Phase 1: Load and prepare all data.

    Returns:
        dict: All loaded data and categorizations
    """
    print("\n" + "=" * 60)
    print("PHASE 1: DATA LOADING AND PREPARATION")
    print("=" * 60)

    # Load data
    gvfk_area_volume = load_gvfk_area_volume()
    substance_sites = load_substance_sites()
    branch_sites = load_and_filter_branch_sites()

    # Categorize GVFKs
    gvfk_categories = categorize_gvfks(substance_sites, branch_sites)

    # Filter sites in new GVFKs
    sites_in_new_gvfks = filter_sites_by_gvfk_category(
        branch_sites,
        gvfk_categories['new_gvfks']
    )

    # Load shapefiles
    shapefiles = load_gvfk_shapefiles()

    print("\n" + "=" * 60)
    print("✓ PHASE 1 COMPLETE")
    print("=" * 60)

    return {
        'gvfk_area_volume': gvfk_area_volume,
        'substance_sites': substance_sites,
        'branch_sites': branch_sites,
        'sites_in_new_gvfks': sites_in_new_gvfks,
        'gvfk_categories': gvfk_categories,
        'shapefiles': shapefiles
    }


# ============================================================================
# PHASE 2: GVFK PROGRESSION METRICS
# ============================================================================

def calculate_gvfk_metrics(gvfk_set, gvfk_area_volume):
    """
    Calculate aggregate metrics for a set of GVFKs.

    Args:
        gvfk_set: Set of GVFK names
        gvfk_area_volume: Dictionary with area/volume data per GVFK

    Returns:
        dict: {'count': int, 'area_km2': float, 'volume_m3': float}
    """
    count = len(gvfk_set)
    total_area = 0.0
    total_volume = 0.0

    for gvfk in gvfk_set:
        if gvfk in gvfk_area_volume:
            total_area += gvfk_area_volume[gvfk]['area_km2']
            total_volume += gvfk_area_volume[gvfk]['volume_m3']

    return {
        'count': count,
        'area_km2': total_area,
        'volume_m3': total_volume
    }


def create_gvfk_count_progression_chart(shapefiles, gvfk_categories, output_dir):
    """
    Create bar chart showing GVFK count progression through workflow.

    Args:
        shapefiles: Dict with 'all_dk', 'step2', 'step3' GeoDataFrames
        gvfk_categories: Dict with 'core_gvfks', 'expanded_gvfks'
        output_dir: Output directory path
    """
    print("\n[PHASE 2] Creating GVFK count progression chart...")

    # Calculate counts
    steps = []
    counts = []

    if 'all_dk' in shapefiles:
        steps.append('Step 1:\nAll Denmark')
        counts.append(len(shapefiles['all_dk']))

    if 'step2' in shapefiles:
        steps.append('Step 2:\nRiver Contact')
        counts.append(len(shapefiles['step2']))

    if 'step3' in shapefiles:
        steps.append('Step 3:\nV1/V2 Sites')
        counts.append(len(shapefiles['step3']))

    steps.append('Step 5b:\nCore\n(Substance)')
    counts.append(len(gvfk_categories['core_gvfks']))

    steps.append('Step 5b+:\nExpanded\n(+Branch)')
    counts.append(len(gvfk_categories['expanded_gvfks']))

    # Create figure
    fig, ax = plt.subplots(figsize=(10, 6))

    # Create bars with different colors
    colors = ['#90CAF9', '#64B5F6', '#42A5F5', COLORS['core'], COLORS['expanded']]
    bars = ax.bar(steps, counts, color=colors, edgecolor='black', linewidth=0.5)

    # Add value labels on bars
    for bar, count in zip(bars, counts):
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height,
                f'{count:,}',
                ha='center', va='bottom', fontweight='bold', fontsize=11)

    # Formatting
    ax.set_ylabel('Number of GVFKs', fontweight='bold')
    ax.set_title('GVFK Progression Through Workflow', fontweight='bold', fontsize=14, pad=15)
    ax.grid(axis='y', alpha=0.3, linestyle='--')
    ax.set_axisbelow(True)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)

    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'gvfk_count_progression.png'), dpi=300, bbox_inches='tight')
    plt.close()

    print(f"  Saved: gvfk_count_progression.png")


def create_area_volume_progression_chart(shapefiles, gvfk_categories, gvfk_area_volume, output_dir):
    """
    Create dual-axis chart showing area and volume progression.

    Args:
        shapefiles: Dict with 'all_dk', 'step2', 'step3' GeoDataFrames
        gvfk_categories: Dict with GVFK sets
        gvfk_area_volume: Dict with area/volume data
        output_dir: Output directory path
    """
    print("\n[PHASE 2] Creating area/volume progression chart...")

    # Calculate metrics for each step
    steps = []
    areas = []
    volumes = []

    if 'all_dk' in shapefiles:
        gvfk_set = set(shapefiles['all_dk']['GVFK'].unique())
        metrics = calculate_gvfk_metrics(gvfk_set, gvfk_area_volume)
        steps.append('Step 1:\nAll Denmark')
        areas.append(metrics['area_km2'])
        volumes.append(metrics['volume_m3'])

    if 'step2' in shapefiles:
        gvfk_set = set(shapefiles['step2']['GVFK'].unique())
        metrics = calculate_gvfk_metrics(gvfk_set, gvfk_area_volume)
        steps.append('Step 2:\nRiver Contact')
        areas.append(metrics['area_km2'])
        volumes.append(metrics['volume_m3'])

    if 'step3' in shapefiles:
        gvfk_set = set(shapefiles['step3']['GVFK'].unique())
        metrics = calculate_gvfk_metrics(gvfk_set, gvfk_area_volume)
        steps.append('Step 3:\nV1/V2 Sites')
        areas.append(metrics['area_km2'])
        volumes.append(metrics['volume_m3'])

    core_metrics = calculate_gvfk_metrics(gvfk_categories['core_gvfks'], gvfk_area_volume)
    steps.append('Step 5b:\nCore')
    areas.append(core_metrics['area_km2'])
    volumes.append(core_metrics['volume_m3'])

    expanded_metrics = calculate_gvfk_metrics(gvfk_categories['expanded_gvfks'], gvfk_area_volume)
    steps.append('Step 5b+:\nExpanded')
    areas.append(expanded_metrics['area_km2'])
    volumes.append(expanded_metrics['volume_m3'])

    # Create figure with dual axes
    fig, ax1 = plt.subplots(figsize=(10, 6))

    # Area on left axis
    x_pos = np.arange(len(steps))
    width = 0.35

    bars1 = ax1.bar(x_pos - width/2, areas, width, label='Area (km²)',
                     color='#4CAF50', alpha=0.8, edgecolor='black', linewidth=0.5)
    ax1.set_ylabel('Area (km²)', fontweight='bold', color='#4CAF50')
    ax1.tick_params(axis='y', labelcolor='#4CAF50')
    ax1.set_xticks(x_pos)
    ax1.set_xticklabels(steps)

    # Volume on right axis
    ax2 = ax1.twinx()
    bars2 = ax2.bar(x_pos + width/2, volumes, width, label='Volume (m³)',
                     color='#2196F3', alpha=0.8, edgecolor='black', linewidth=0.5)
    ax2.set_ylabel('Volume (m³)', fontweight='bold', color='#2196F3')
    ax2.tick_params(axis='y', labelcolor='#2196F3')

    # Title and grid
    ax1.set_title('GVFK Area and Volume Progression', fontweight='bold', fontsize=14, pad=15)
    ax1.grid(axis='y', alpha=0.3, linestyle='--')
    ax1.set_axisbelow(True)

    # Legend
    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2, loc='upper right')

    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'gvfk_area_volume_progression.png'), dpi=300, bbox_inches='tight')
    plt.close()

    print(f"  Saved: gvfk_area_volume_progression.png")


def create_progression_table(shapefiles, gvfk_categories, gvfk_area_volume, output_dir):
    """
    Create detailed progression table with percentages.

    Args:
        shapefiles: Dict with GeoDataFrames
        gvfk_categories: Dict with GVFK sets
        gvfk_area_volume: Dict with area/volume data
        output_dir: Output directory path

    Returns:
        pd.DataFrame: Progression table
    """
    print("\n[PHASE 2] Creating progression table...")

    rows = []

    # Step 1: All Denmark (baseline)
    if 'all_dk' in shapefiles:
        gvfk_set = set(shapefiles['all_dk']['GVFK'].unique())
        metrics = calculate_gvfk_metrics(gvfk_set, gvfk_area_volume)
        rows.append({
            'Step': 'Step 1: All Denmark',
            'GVFK Count': metrics['count'],
            'Area (km²)': metrics['area_km2'],
            'Volume (m³)': metrics['volume_m3']
        })
        baseline_count = metrics['count']
        baseline_area = metrics['area_km2']
        baseline_volume = metrics['volume_m3']

    # Step 2: River Contact
    if 'step2' in shapefiles:
        gvfk_set = set(shapefiles['step2']['GVFK'].unique())
        metrics = calculate_gvfk_metrics(gvfk_set, gvfk_area_volume)
        rows.append({
            'Step': 'Step 2: River Contact',
            'GVFK Count': metrics['count'],
            'Area (km²)': metrics['area_km2'],
            'Volume (m³)': metrics['volume_m3']
        })

    # Step 3: V1/V2 Sites
    if 'step3' in shapefiles:
        gvfk_set = set(shapefiles['step3']['GVFK'].unique())
        metrics = calculate_gvfk_metrics(gvfk_set, gvfk_area_volume)
        rows.append({
            'Step': 'Step 3: V1/V2 Sites',
            'GVFK Count': metrics['count'],
            'Area (km²)': metrics['area_km2'],
            'Volume (m³)': metrics['volume_m3']
        })

    # Step 5b: Core (substance sites)
    core_metrics = calculate_gvfk_metrics(gvfk_categories['core_gvfks'], gvfk_area_volume)
    rows.append({
        'Step': 'Step 5b: Core (Substance)',
        'GVFK Count': core_metrics['count'],
        'Area (km²)': core_metrics['area_km2'],
        'Volume (m³)': core_metrics['volume_m3']
    })

    # Step 5b+: Expanded (substance + branch)
    expanded_metrics = calculate_gvfk_metrics(gvfk_categories['expanded_gvfks'], gvfk_area_volume)
    rows.append({
        'Step': 'Step 5b+: Expanded (+Branch)',
        'GVFK Count': expanded_metrics['count'],
        'Area (km²)': expanded_metrics['area_km2'],
        'Volume (m³)': expanded_metrics['volume_m3']
    })

    # Create DataFrame
    df = pd.DataFrame(rows)

    # Add percentage columns
    if baseline_count > 0:
        df['% of Baseline Count'] = (df['GVFK Count'] / baseline_count * 100).round(1)
        df['% of Baseline Area'] = (df['Area (km²)'] / baseline_area * 100).round(1)
        df['% of Baseline Volume'] = (df['Volume (m³)'] / baseline_volume * 100).round(1)

    # Save to CSV
    table_path = os.path.join(output_dir, 'gvfk_progression_table.csv')
    df.to_csv(table_path, index=False)

    print(f"  Saved: gvfk_progression_table.csv")
    print("\n  Progression Summary:")
    print(df.to_string(index=False))

    return df


def create_expansion_breakdown_chart(gvfk_categories, gvfk_area_volume, output_dir):
    """
    Create chart showing contribution of new GVFKs to expanded scenario.

    Args:
        gvfk_categories: Dict with GVFK sets
        gvfk_area_volume: Dict with area/volume data
        output_dir: Output directory path
    """
    print("\n[PHASE 2] Creating expansion breakdown chart...")

    # Calculate metrics
    core_metrics = calculate_gvfk_metrics(gvfk_categories['core_gvfks'], gvfk_area_volume)
    new_metrics = calculate_gvfk_metrics(gvfk_categories['new_gvfks'], gvfk_area_volume)

    # Create subplots
    fig, axes = plt.subplots(1, 3, figsize=(15, 5))

    # Count breakdown
    ax1 = axes[0]
    categories = ['Core\n(Substance)', 'New\n(Branch-only)']
    counts = [core_metrics['count'], new_metrics['count']]
    colors_plot = [COLORS['core'], COLORS['new_gvfk']]
    bars1 = ax1.bar(categories, counts, color=colors_plot, edgecolor='black', linewidth=0.5)
    ax1.set_ylabel('Number of GVFKs', fontweight='bold')
    ax1.set_title('GVFK Count Breakdown', fontweight='bold')
    ax1.grid(axis='y', alpha=0.3, linestyle='--')
    ax1.set_axisbelow(True)
    for bar, count in zip(bars1, counts):
        height = bar.get_height()
        ax1.text(bar.get_x() + bar.get_width()/2., height,
                f'{count:,}', ha='center', va='bottom', fontweight='bold')

    # Area breakdown
    ax2 = axes[1]
    areas = [core_metrics['area_km2'], new_metrics['area_km2']]
    bars2 = ax2.bar(categories, areas, color=colors_plot, edgecolor='black', linewidth=0.5)
    ax2.set_ylabel('Area (km²)', fontweight='bold')
    ax2.set_title('Area Breakdown', fontweight='bold')
    ax2.grid(axis='y', alpha=0.3, linestyle='--')
    ax2.set_axisbelow(True)
    for bar, area in zip(bars2, areas):
        height = bar.get_height()
        ax2.text(bar.get_x() + bar.get_width()/2., height,
                f'{area:,.0f}', ha='center', va='bottom', fontweight='bold')

    # Volume breakdown
    ax3 = axes[2]
    volumes = [core_metrics['volume_m3'], new_metrics['volume_m3']]
    bars3 = ax3.bar(categories, volumes, color=colors_plot, edgecolor='black', linewidth=0.5)
    ax3.set_ylabel('Volume (m³)', fontweight='bold')
    ax3.set_title('Volume Breakdown', fontweight='bold')
    ax3.grid(axis='y', alpha=0.3, linestyle='--')
    ax3.set_axisbelow(True)
    for bar, volume in zip(bars3, volumes):
        height = bar.get_height()
        ax3.text(bar.get_x() + bar.get_width()/2., height,
                f'{volume:,.0f}', ha='center', va='bottom', fontweight='bold')

    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'gvfk_expansion_breakdown.png'), dpi=300, bbox_inches='tight')
    plt.close()

    print(f"  Saved: gvfk_expansion_breakdown.png")


def run_phase2(data, output_dir):
    """
    Execute Phase 2: GVFK progression metrics and visualizations.

    Args:
        data: Dictionary from Phase 1 with loaded data
        output_dir: Output directory path
    """
    print("\n" + "=" * 60)
    print("PHASE 2: GVFK PROGRESSION METRICS")
    print("=" * 60)

    gvfk_area_volume = data['gvfk_area_volume']
    gvfk_categories = data['gvfk_categories']
    shapefiles = data['shapefiles']

    # Create visualizations
    create_gvfk_count_progression_chart(shapefiles, gvfk_categories, output_dir)
    create_area_volume_progression_chart(shapefiles, gvfk_categories, gvfk_area_volume, output_dir)
    progression_df = create_progression_table(shapefiles, gvfk_categories, gvfk_area_volume, output_dir)
    create_expansion_breakdown_chart(gvfk_categories, gvfk_area_volume, output_dir)

    print("\n" + "=" * 60)
    print("✓ PHASE 2 COMPLETE")
    print("=" * 60)

    return progression_df


# ============================================================================
# MAIN EXECUTION
# ============================================================================

def run_step6_analysis():
    """
    Run complete Step 6 final analysis.
    """
    print("\n" + "=" * 80)
    print("STEP 6: FINAL COMPREHENSIVE ANALYSIS")
    print("=" * 80)
    print("\nComparing Core vs Expanded scenarios:")
    print("  Core: Step 5b compound-specific sites (substance data)")
    print("  Expanded: Core + branch-only sites (<=500m, no losseplads)")
    print("=" * 80)

    # Create output directory
    output_dir = get_visualization_path('step6')
    os.makedirs(output_dir, exist_ok=True)
    print(f"\nOutput directory: {output_dir}")

    # Phase 1: Load data
    data = run_phase1()

    # Phase 2: GVFK progression metrics
    progression_df = run_phase2(data, output_dir)

    # TODO: Phase 3, 4 to be implemented

    print("\n" + "=" * 80)
    print("✓ STEP 6 ANALYSIS COMPLETE (Phases 1-2)")
    print("=" * 80)
    print(f"\nResults saved to: {output_dir}")


if __name__ == "__main__":
    run_step6_analysis()