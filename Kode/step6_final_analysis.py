"""
Step 6: Final Comprehensive Analysis
=====================================

BASELINE COMPARISON - IMPORTANT:
This analysis compares against Step 5b (compound-specific) NOT Step 5a (general 500m).

Core Scenario (Step 5b):
- Sites WITH substance data using compound-specific distance thresholds
- Source: step5_compound_specific_sites.csv (see step5_risk_assessment.py lines 137-176)
- Result: ~1,740 sites spanning 217 GVFKs
- These sites qualified under literature-based variable thresholds per compound category

Expanded Scenario (Step 5b+):
- Core + branch-only sites (<=500m, no losseplads keywords)
- Branch-only source: step5_unknown_substance_sites.csv (sites WITHOUT substance data)
- Filtering: Final_Distance_m <= 500 AND excludes losseplads keywords (see lines 129-139)
- Result: Core (217 GVFKs) + New (92 GVFKs) = 309 total GVFKs
- The 92 "new" GVFKs have ONLY branch-only sites, no substance sites

KEY DISTINCTION vs step5_branch_analysis.py:
- step5_branch_analysis.py compares branch-only sites against Step 5a (general 500m assessment)
  which includes ALL substance sites within 500m (~300+ GVFKs), resulting in ~44 additional GVFKs
- THIS analysis (step6) compares against Step 5b (compound-specific, 217 GVFKs),
  resulting in 92 additional GVFKs - this is CORRECT for decision-support
- See step5_branch_analysis.py lines 453-541 (_analyze_generel_risiko_impact) for comparison

Analysis outputs:
Phase 1: Data loading and GVFK categorization (lines 42-292)
Phase 2: GVFK progression metrics and visualizations (lines 294-656)
Phase 3: Three-way branch/activity comparison (TODO)
Phase 4: Geographic visualizations (TODO)
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

    # Path to area/volume file
    # GRUNDVAND_PATH is in Data/shp files/, we need Data/volumen areal_genbesøg.csv
    grundvand_dir = os.path.dirname(GRUNDVAND_PATH)  # Gets Data/shp files
    data_dir = os.path.dirname(grundvand_dir)  # Gets Data
    area_volume_path = os.path.join(data_dir, "volumen areal_genbesøg.csv")

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
    Load and filter branch-only sites (<=500m, no losseplads).

    Returns:
        pd.DataFrame: Filtered branch-only sites
    """
    print("\n[PHASE 1] Loading and filtering branch-only sites...")

    unknown_path = get_output_path('step5_unknown_substance_sites')
    if not os.path.exists(unknown_path):
        raise FileNotFoundError(f"Unknown substance sites not found: {unknown_path}")

    unknown_sites = pd.read_csv(unknown_path)

    print(f"  Total unknown substance sites: {len(unknown_sites):,}")

    # Filter 1: Distance <=500m
    branch_sites = unknown_sites[unknown_sites['Final_Distance_m'] <= 500].copy()
    print(f"  After <=500m filter: {len(branch_sites):,} sites")

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
    print("[OK] PHASE 1 COMPLETE")
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
    Create dual-axis chart showing area and volume progression with stacked bars for Step 5b+.

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

    # Track Step 5b expansion separately for stacking
    core_area = 0
    core_volume = 0
    new_area = 0
    new_volume = 0

    if 'all_dk' in shapefiles:
        gvfk_set = set(shapefiles['all_dk']['Navn'].unique())
        metrics = calculate_gvfk_metrics(gvfk_set, gvfk_area_volume)
        steps.append('Step 1:\nAll Denmark')
        areas.append(metrics['area_km2'])
        volumes.append(metrics['volume_m3'])

    if 'step2' in shapefiles:
        gvfk_set = set(shapefiles['step2']['Navn'].unique())
        metrics = calculate_gvfk_metrics(gvfk_set, gvfk_area_volume)
        steps.append('Step 2:\nRiver Contact')
        areas.append(metrics['area_km2'])
        volumes.append(metrics['volume_m3'])

    if 'step3' in shapefiles:
        gvfk_set = set(shapefiles['step3']['Navn'].unique())
        metrics = calculate_gvfk_metrics(gvfk_set, gvfk_area_volume)
        steps.append('Step 3:\nV1/V2 Sites')
        areas.append(metrics['area_km2'])
        volumes.append(metrics['volume_m3'])

    core_metrics = calculate_gvfk_metrics(gvfk_categories['core_gvfks'], gvfk_area_volume)
    steps.append('Step 5b:\nCore')
    areas.append(core_metrics['area_km2'])
    volumes.append(core_metrics['volume_m3'])
    core_area = core_metrics['area_km2']
    core_volume = core_metrics['volume_m3']

    # Calculate just the NEW contribution
    new_metrics = calculate_gvfk_metrics(gvfk_categories['new_gvfks'], gvfk_area_volume)
    steps.append('Step 5b+:\nExpanded')
    areas.append(core_area)  # Base for stacking
    volumes.append(core_volume)  # Base for stacking
    new_area = new_metrics['area_km2']
    new_volume = new_metrics['volume_m3']

    # Create figure with dual axes
    fig, ax1 = plt.subplots(figsize=(12, 7))

    x_pos = np.arange(len(steps))
    width = 0.35

    # Area on left axis - with stacked bar for Step 5b+
    bars1_base = ax1.bar(x_pos - width/2, areas, width, label='Area (km²) - Core',
                         color='#4CAF50', alpha=0.8, edgecolor='black', linewidth=0.5)

    # Add stacked portion for Step 5b+ (last bar only)
    if len(steps) > 0:
        bars1_stack = ax1.bar(x_pos[-1] - width/2, new_area, width,
                             bottom=core_area, label='Area (km²) - +92 New GVFKs',
                             color='#FFC107', alpha=0.8, edgecolor='black', linewidth=0.5)
        # Add annotation showing the increase
        ax1.text(x_pos[-1] - width/2, core_area + new_area/2,
                f'+{new_area:,.0f}\nkm²', ha='center', va='center',
                fontweight='bold', fontsize=9, color='black')

    ax1.set_ylabel('Area (km²)', fontweight='bold', color='#4CAF50', fontsize=12)
    ax1.tick_params(axis='y', labelcolor='#4CAF50')
    ax1.set_xticks(x_pos)
    ax1.set_xticklabels(steps, fontsize=10)

    # Volume on right axis - with stacked bar for Step 5b+
    ax2 = ax1.twinx()
    bars2_base = ax2.bar(x_pos + width/2, volumes, width, label='Volume (m³) - Core',
                         color='#2196F3', alpha=0.8, edgecolor='black', linewidth=0.5)

    # Add stacked portion for Step 5b+ (last bar only)
    if len(steps) > 0:
        bars2_stack = ax2.bar(x_pos[-1] + width/2, new_volume, width,
                             bottom=core_volume, label='Volume (m³) - +92 New GVFKs',
                             color='#FF9800', alpha=0.8, edgecolor='black', linewidth=0.5)
        # Add annotation showing the increase
        ax2.text(x_pos[-1] + width/2, core_volume + new_volume/2,
                f'+{new_volume:.2e}\nm³', ha='center', va='center',
                fontweight='bold', fontsize=9, color='black')

    ax2.set_ylabel('Volume (m³)', fontweight='bold', color='#2196F3', fontsize=12)
    ax2.tick_params(axis='y', labelcolor='#2196F3')

    # Title and grid
    ax1.set_title('GVFK Area and Volume Progression\n(Step 5b+ shows stacked contribution from 92 new GVFKs)',
                  fontweight='bold', fontsize=13, pad=15)
    ax1.grid(axis='y', alpha=0.3, linestyle='--')
    ax1.set_axisbelow(True)

    # Combined legend
    handles1, labels1 = ax1.get_legend_handles_labels()
    handles2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(handles1 + handles2, labels1 + labels2, loc='upper left', fontsize=9)

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
        gvfk_set = set(shapefiles['all_dk']['Navn'].unique())
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
        gvfk_set = set(shapefiles['step2']['Navn'].unique())
        metrics = calculate_gvfk_metrics(gvfk_set, gvfk_area_volume)
        rows.append({
            'Step': 'Step 2: River Contact',
            'GVFK Count': metrics['count'],
            'Area (km²)': metrics['area_km2'],
            'Volume (m³)': metrics['volume_m3']
        })

    # Step 3: V1/V2 Sites
    if 'step3' in shapefiles:
        gvfk_set = set(shapefiles['step3']['Navn'].unique())
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
    print("[OK] PHASE 2 COMPLETE")
    print("=" * 60)

    return progression_df


# ============================================================================
# PHASE 3: THREE-WAY BRANCH/ACTIVITY COMPARISON
# ============================================================================

def count_occurrences(df, column_name):
    """
    Count occurrences from semicolon-separated column.

    Args:
        df: DataFrame with the column
        column_name: Name of column with semicolon-separated values

    Returns:
        pd.Series: Value counts of all occurrences
    """
    all_items = []

    for value in df[column_name].dropna():
        if pd.notna(value) and str(value).strip():
            items = [item.strip() for item in str(value).split(';') if item.strip()]
            all_items.extend(items)

    if all_items:
        return pd.Series(all_items).value_counts()
    else:
        return pd.Series(dtype=int)


def analyze_three_groups(substance_sites, all_branch_sites, new_gvfk_sites):
    """
    Analyze branch/activity patterns across three groups.

    Args:
        substance_sites: Group A - substance sites
        all_branch_sites: Group B - all branch-only sites
        new_gvfk_sites: Group C - sites in new GVFKs only

    Returns:
        dict: Analysis results for branches and activities
    """
    print("\n[PHASE 3] Analyzing three-way comparison...")

    # Count occurrences for each group
    print("  Counting branch occurrences...")
    branches_A = count_occurrences(substance_sites, 'Lokalitetensbranche')
    branches_B = count_occurrences(all_branch_sites, 'Lokalitetensbranche')
    branches_C = count_occurrences(new_gvfk_sites, 'Lokalitetensbranche')

    print("  Counting activity occurrences...")
    activities_A = count_occurrences(substance_sites, 'Lokalitetensaktivitet')
    activities_B = count_occurrences(all_branch_sites, 'Lokalitetensaktivitet')
    activities_C = count_occurrences(new_gvfk_sites, 'Lokalitetensaktivitet')

    # Summary statistics
    print(f"\n  Group A (Substance sites): {len(substance_sites):,} sites")
    print(f"    Branches: {len(branches_A)} unique, {branches_A.sum():,} total occurrences")
    print(f"    Activities: {len(activities_A)} unique, {activities_A.sum():,} total occurrences")

    print(f"\n  Group B (All branch-only): {len(all_branch_sites):,} sites")
    print(f"    Branches: {len(branches_B)} unique, {branches_B.sum():,} total occurrences")
    print(f"    Activities: {len(activities_B)} unique, {activities_B.sum():,} total occurrences")

    print(f"\n  Group C (New GVFK sites only): {len(new_gvfk_sites):,} sites")
    print(f"    Branches: {len(branches_C)} unique, {branches_C.sum():,} total occurrences")
    print(f"    Activities: {len(activities_C)} unique, {activities_C.sum():,} total occurrences")

    # Overlap analysis
    branch_overlap = analyze_overlap(branches_A, branches_B, branches_C, "Branches")
    activity_overlap = analyze_overlap(activities_A, activities_B, activities_C, "Activities")

    return {
        'branches': {'A': branches_A, 'B': branches_B, 'C': branches_C},
        'activities': {'A': activities_A, 'B': activities_B, 'C': activities_C},
        'branch_overlap': branch_overlap,
        'activity_overlap': activity_overlap
    }


def analyze_overlap(series_A, series_B, series_C, label):
    """
    Analyze overlap between three series.

    Args:
        series_A, series_B, series_C: Value count series for each group
        label: Label for printing (Branches/Activities)

    Returns:
        dict: Overlap statistics
    """
    set_A = set(series_A.index)
    set_B = set(series_B.index)
    set_C = set(series_C.index)

    common_all = set_A & set_B & set_C
    common_AC = set_A & set_C
    unique_C = set_C - set_A - set_B

    print(f"\n  {label} Overlap Analysis:")
    print(f"    Unique in A: {len(set_A)}")
    print(f"    Unique in B: {len(set_B)}")
    print(f"    Unique in C: {len(set_C)}")
    print(f"    Common to all three: {len(common_all)}")
    print(f"    Common to A and C: {len(common_AC)}")
    print(f"    Unique to C only: {len(unique_C)}")
    if len(set_C) > 0:
        print(f"    Overlap % (C with A): {len(common_AC)/len(set_C)*100:.1f}%")

    return {
        'unique_A': len(set_A),
        'unique_B': len(set_B),
        'unique_C': len(set_C),
        'common_all': len(common_all),
        'common_AC': len(common_AC),
        'unique_C_only': len(unique_C),
        'overlap_pct': len(common_AC)/len(set_C)*100 if len(set_C) > 0 else 0
    }


def create_three_way_comparison_chart(comparison_data, data_type, output_dir):
    """
    Create three-way comparison horizontal bar chart.

    Args:
        comparison_data: Dict with 'A', 'B', 'C' series
        data_type: 'branches' or 'activities'
        output_dir: Output directory path
    """
    print(f"\n[PHASE 3] Creating three-way {data_type} comparison chart...")

    series_A = comparison_data['A']
    series_B = comparison_data['B']
    series_C = comparison_data['C']

    # Get top 15 by combined total occurrences
    all_items = set(series_A.index) | set(series_B.index) | set(series_C.index)

    item_totals = []
    for item in all_items:
        total = series_A.get(item, 0) + series_B.get(item, 0) + series_C.get(item, 0)
        item_totals.append((item, total))

    item_totals.sort(key=lambda x: x[1], reverse=True)
    top_15_items = [item for item, _ in item_totals[:15]]

    # Get counts for each group
    counts_A = [series_A.get(item, 0) for item in top_15_items]
    counts_B = [series_B.get(item, 0) for item in top_15_items]
    counts_C = [series_C.get(item, 0) for item in top_15_items]

    # Truncate long names
    item_names = [name[:40] + '...' if len(name) > 40 else name for name in top_15_items]

    # Create figure - taller for 15 items
    fig, ax = plt.subplots(figsize=(14, 10))

    y_pos = np.arange(len(item_names))
    width = 0.25

    # Three bars side by side
    bars1 = ax.barh(y_pos - width, counts_A, width,
                    label='Group A: Substance (1,740 sites)',
                    color=COLORS['core'], alpha=0.8)
    bars2 = ax.barh(y_pos, counts_B, width,
                    label='Group B: All Branch-only (3,714 sites)',
                    color=COLORS['expanded'], alpha=0.8)
    bars3 = ax.barh(y_pos + width, counts_C, width,
                    label='Group C: New GVFKs only (241 sites)',
                    color=COLORS['new_gvfk'], alpha=0.8)

    ax.set_yticks(y_pos)
    ax.set_yticklabels(item_names, fontsize=10)
    ax.set_xlabel('Number of Occurrences', fontweight='bold', fontsize=12)
    ax.set_title(f'Top 15 {data_type.title()}: Three-way Comparison',
                 fontweight='bold', fontsize=14, pad=15)
    ax.legend(fontsize=10, loc='lower right')
    ax.grid(axis='x', alpha=0.3, linestyle='--')
    ax.set_axisbelow(True)

    # Add value labels for Group C (smallest, most interesting)
    for bar, count in zip(bars3, counts_C):
        if count > 0:
            width_val = bar.get_width()
            ax.text(width_val + max(counts_A + counts_B + counts_C)*0.01,
                   bar.get_y() + bar.get_height()/2,
                   f'{int(count)}', ha='left', va='center', fontsize=9,
                   color=COLORS['new_gvfk'], fontweight='bold')

    # Clean styling
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.set_facecolor('#FAFAFA')

    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, f'three_way_{data_type}_comparison.png'),
                dpi=300, bbox_inches='tight')
    plt.close()

    print(f"  Saved: three_way_{data_type}_comparison.png")


def create_overlap_visualization(branch_overlap, activity_overlap, output_dir):
    """
    Create overlap analysis visualization.

    Args:
        branch_overlap: Branch overlap statistics
        activity_overlap: Activity overlap statistics
        output_dir: Output directory path
    """
    print("\n[PHASE 3] Creating overlap visualization...")

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))

    # Branch overlap
    categories = ['Unique\nin A', 'Unique\nin B', 'Unique\nin C',
                  'Common\nto all 3', 'Common\nA & C', 'Unique\nC only']
    values_branch = [
        branch_overlap['unique_A'],
        branch_overlap['unique_B'],
        branch_overlap['unique_C'],
        branch_overlap['common_all'],
        branch_overlap['common_AC'],
        branch_overlap['unique_C_only']
    ]

    colors_plot = ['#1E88E5', '#FFC107', '#FF5722', '#43A047', '#9C27B0', '#E91E63']

    bars1 = ax1.bar(range(len(categories)), values_branch, color=colors_plot, alpha=0.8)
    ax1.set_xticks(range(len(categories)))
    ax1.set_xticklabels(categories, fontsize=9)
    ax1.set_ylabel('Count', fontweight='bold')
    ax1.set_title('Branch Overlap Analysis', fontweight='bold', fontsize=12)
    ax1.grid(axis='y', alpha=0.3, linestyle='--')

    # Add value labels
    for bar in bars1:
        height = bar.get_height()
        ax1.text(bar.get_x() + bar.get_width()/2., height,
                f'{int(height)}', ha='center', va='bottom', fontsize=10, fontweight='bold')

    # Activity overlap
    values_activity = [
        activity_overlap['unique_A'],
        activity_overlap['unique_B'],
        activity_overlap['unique_C'],
        activity_overlap['common_all'],
        activity_overlap['common_AC'],
        activity_overlap['unique_C_only']
    ]

    bars2 = ax2.bar(range(len(categories)), values_activity, color=colors_plot, alpha=0.8)
    ax2.set_xticks(range(len(categories)))
    ax2.set_xticklabels(categories, fontsize=9)
    ax2.set_ylabel('Count', fontweight='bold')
    ax2.set_title('Activity Overlap Analysis', fontweight='bold', fontsize=12)
    ax2.grid(axis='y', alpha=0.3, linestyle='--')

    # Add value labels
    for bar in bars2:
        height = bar.get_height()
        ax2.text(bar.get_x() + bar.get_width()/2., height,
                f'{int(height)}', ha='center', va='bottom', fontsize=10, fontweight='bold')

    # Clean styling
    for ax in [ax1, ax2]:
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.set_facecolor('#FAFAFA')

    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'overlap_analysis.png'),
                dpi=300, bbox_inches='tight')
    plt.close()

    print(f"  Saved: overlap_analysis.png")


def create_comparison_tables(comparison_results, substance_sites, all_branch_sites,
                            new_gvfk_sites, gvfk_categories, output_dir):
    """
    Create comparison tables for three groups.

    Args:
        comparison_results: Results from analyze_three_groups
        substance_sites, all_branch_sites, new_gvfk_sites: Site DataFrames
        gvfk_categories: GVFK categorization dict
        output_dir: Output directory path
    """
    print("\n[PHASE 3] Creating comparison tables...")

    branches_A = comparison_results['branches']['A']
    branches_B = comparison_results['branches']['B']
    branches_C = comparison_results['branches']['C']
    activities_A = comparison_results['activities']['A']
    activities_B = comparison_results['activities']['B']
    activities_C = comparison_results['activities']['C']

    # Table 1: Group characteristics summary
    summary_data = {
        'Metric': [
            'Total sites',
            'GVFKs',
            'Unique branches',
            'Unique activities',
            'Total branch occurrences',
            'Total activity occurrences',
            'Top branch',
            'Top activity',
            'Avg sites per GVFK'
        ],
        'Group A (Substance)': [
            len(substance_sites),
            len(gvfk_categories['core_gvfks']),
            len(branches_A),
            len(activities_A),
            branches_A.sum(),
            activities_A.sum(),
            f"{branches_A.index[0]} ({branches_A.iloc[0]})" if len(branches_A) > 0 else "N/A",
            f"{activities_A.index[0]} ({activities_A.iloc[0]})" if len(activities_A) > 0 else "N/A",
            f"{len(substance_sites) / len(gvfk_categories['core_gvfks']):.1f}"
        ],
        'Group B (All Branch-only)': [
            len(all_branch_sites),
            len(gvfk_categories['branch_gvfks']),
            len(branches_B),
            len(activities_B),
            branches_B.sum(),
            activities_B.sum(),
            f"{branches_B.index[0]} ({branches_B.iloc[0]})" if len(branches_B) > 0 else "N/A",
            f"{activities_B.index[0]} ({activities_B.iloc[0]})" if len(activities_B) > 0 else "N/A",
            f"{len(all_branch_sites) / len(gvfk_categories['branch_gvfks']):.1f}"
        ],
        'Group C (New GVFKs only)': [
            len(new_gvfk_sites),
            len(gvfk_categories['new_gvfks']),
            len(branches_C),
            len(activities_C),
            branches_C.sum(),
            activities_C.sum(),
            f"{branches_C.index[0]} ({branches_C.iloc[0]})" if len(branches_C) > 0 else "N/A",
            f"{activities_C.index[0]} ({activities_C.iloc[0]})" if len(activities_C) > 0 else "N/A",
            f"{len(new_gvfk_sites) / len(gvfk_categories['new_gvfks']):.1f}"
        ]
    }

    summary_df = pd.DataFrame(summary_data)
    summary_path = os.path.join(output_dir, 'three_group_characteristics.csv')
    summary_df.to_csv(summary_path, index=False)
    print(f"  Saved: three_group_characteristics.csv")

    # Table 2: Top 15 branches comparison
    top_branches = create_top_15_comparison_table(branches_A, branches_B, branches_C,
                                                   'branches', output_dir)

    # Table 3: Top 15 activities comparison
    top_activities = create_top_15_comparison_table(activities_A, activities_B, activities_C,
                                                     'activities', output_dir)

    return summary_df, top_branches, top_activities


def create_top_15_comparison_table(series_A, series_B, series_C, data_type, output_dir):
    """
    Create top 15 comparison table.

    Args:
        series_A, series_B, series_C: Value count series for each group
        data_type: 'branches' or 'activities'
        output_dir: Output directory path

    Returns:
        pd.DataFrame: Top 15 comparison table
    """
    # Get top 15 by combined total
    all_items = set(series_A.index) | set(series_B.index) | set(series_C.index)

    item_totals = []
    for item in all_items:
        total = series_A.get(item, 0) + series_B.get(item, 0) + series_C.get(item, 0)
        item_totals.append((
            item,
            series_A.get(item, 0),
            series_B.get(item, 0),
            series_C.get(item, 0),
            total
        ))

    item_totals.sort(key=lambda x: x[4], reverse=True)
    top_15 = item_totals[:15]

    df = pd.DataFrame(top_15, columns=[
        data_type.capitalize()[:-1],  # Branch or Activity (singular)
        'Group A (Substance) occurrences',
        'Group B (All Branch-only) occurrences',
        'Group C (New GVFKs) occurrences',
        'Total occurrences'
    ])

    df.insert(0, 'Rank', range(1, len(df) + 1))

    table_path = os.path.join(output_dir, f'top_15_{data_type}_comparison.csv')
    df.to_csv(table_path, index=False)
    print(f"  Saved: top_15_{data_type}_comparison.csv")

    return df


def run_phase3(data, output_dir):
    """
    Execute Phase 3: Three-way branch/activity comparison.

    Args:
        data: Dictionary from Phase 1 with loaded data
        output_dir: Output directory path
    """
    print("\n" + "=" * 60)
    print("PHASE 3: THREE-WAY BRANCH/ACTIVITY COMPARISON")
    print("=" * 60)

    substance_sites = data['substance_sites']
    all_branch_sites = data['branch_sites']
    new_gvfk_sites = data['sites_in_new_gvfks']
    gvfk_categories = data['gvfk_categories']

    # Analyze three groups
    comparison_results = analyze_three_groups(substance_sites, all_branch_sites, new_gvfk_sites)

    # Create visualizations
    create_three_way_comparison_chart(comparison_results['branches'], 'branches', output_dir)
    create_three_way_comparison_chart(comparison_results['activities'], 'activities', output_dir)
    create_overlap_visualization(comparison_results['branch_overlap'],
                                 comparison_results['activity_overlap'],
                                 output_dir)

    # Create tables
    summary_df, top_branches, top_activities = create_comparison_tables(
        comparison_results, substance_sites, all_branch_sites,
        new_gvfk_sites, gvfk_categories, output_dir
    )

    print("\n" + "=" * 60)
    print("[OK] PHASE 3 COMPLETE")
    print("=" * 60)

    return comparison_results


# ============================================================================
# PHASE 4: GEOGRAPHIC VISUALIZATIONS
# ============================================================================

def create_hexagonal_heatmap(sites_gdf, title, output_path, hex_size_km=10):
    """
    Create hexagonal heatmap showing site density.

    Args:
        sites_gdf: GeoDataFrame with site points
        title: Map title
        output_path: Output file path
        hex_size_km: Hexagon size in kilometers
    """
    print(f"\n[PHASE 4] Creating hexagonal heatmap: {title}...")

    if len(sites_gdf) == 0:
        print(f"  Warning: No sites to map")
        return

    # Create figure
    fig, ax = plt.subplots(figsize=(12, 14))

    # Create hexbin (matplotlib's hexagonal binning)
    # Convert hex size from km to map units (assuming EPSG:25832 in meters)
    hex_size_m = hex_size_km * 2000

    # Get coordinates
    x = sites_gdf.geometry.x
    y = sites_gdf.geometry.y

    # Create hexbin plot
    hexbin = ax.hexbin(x, y, gridsize=int(100000/hex_size_m),
                       cmap='YlOrRd', mincnt=1, alpha=0.8, edgecolors='gray', linewidths=0.2)

    # Add colorbar
    cbar = plt.colorbar(hexbin, ax=ax, label='Number of sites')
    cbar.ax.tick_params(labelsize=10)

    # Set title and labels
    ax.set_title(title, fontsize=14, fontweight='bold', pad=15)
    ax.set_xlabel('Easting (m)', fontsize=11)
    ax.set_ylabel('Northing (m)', fontsize=11)

    # Format axes
    ax.ticklabel_format(style='plain', axis='both')
    ax.grid(True, alpha=0.3, linestyle='--')

    # Add site count annotation
    ax.text(0.02, 0.98, f'Total sites: {len(sites_gdf):,}',
            transform=ax.transAxes, fontsize=12, fontweight='bold',
            verticalalignment='top',
            bbox=dict(boxstyle='round,pad=0.5', facecolor='white', alpha=0.8))

    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()

    print(f"  Saved: {os.path.basename(output_path)}")


def create_side_by_side_heatmaps(substance_sites, expanded_sites, output_dir):
    """
    Create side-by-side hexagonal heatmaps for Core vs Expanded.

    Args:
        substance_sites: DataFrame with substance site IDs
        expanded_sites: DataFrame with all site IDs (substance + branch)
        output_dir: Output directory path
    """
    print("\n[PHASE 4] Creating side-by-side hexagonal heatmaps...")

    # Load Denmark regions as backdrop
    regions_path = os.path.join(os.path.dirname(GRUNDVAND_PATH), "..", "regionsinddeling")
    denmark_gdf = None
    if os.path.exists(regions_path):
        try:
            denmark_gdf = gpd.read_file(regions_path)
            print(f"  Loaded Denmark regions backdrop")
        except:
            print(f"  Warning: Could not load Denmark backdrop")

    # Load site geometries from Step 4 (unique lokalitet distances shapefile)
    # This has ONE geometry per Lokalitet_ID (not duplicates like Step 3)
    step4_sites_path = get_output_path('unique_lokalitet_distances_shp')
    if not os.path.exists(step4_sites_path):
        print(f"  Warning: Step 4 unique lokalitet shapefile not found, skipping heatmaps")
        return

    step4_gdf = gpd.read_file(step4_sites_path)
    print(f"  Loaded {len(step4_gdf)} unique sites from Step 4 with geometries")

    # Step 4 shapefile uses 'Lokalitetsnr' which gets truncated to 'Lokalitets'
    # But our Step 5 CSVs use 'Lokalitet_ID' as the column name
    # Let's check what the ID column is actually called in the shapefile
    if 'Lokalitets' in step4_gdf.columns:
        id_col = 'Lokalitets'
    elif 'Lokalitet_' in step4_gdf.columns:
        id_col = 'Lokalitet_'
    elif 'Lokalitetsn' in step4_gdf.columns:
        id_col = 'Lokalitetsn'
    else:
        print(f"  Warning: Cannot find ID column. Available: {list(step4_gdf.columns)[:10]}")
        return

    # IMPORTANT: Only get sites that are actually in our Step 5 filtered results
    substance_ids = set(substance_sites['Lokalitet_ID'].unique())
    branch_ids = set(expanded_sites['Lokalitet_ID'].unique())

    substance_gdf = step4_gdf[step4_gdf[id_col].isin(substance_ids)].copy()

    # Expanded = substance + branch-only (no duplicates)
    expanded_ids = substance_ids | branch_ids
    expanded_gdf = step4_gdf[step4_gdf[id_col].isin(expanded_ids)].copy()

    print(f"  Matched {len(substance_gdf):,} substance sites with geometries")
    print(f"  Matched {len(expanded_gdf):,} expanded sites with geometries")

    if len(substance_gdf) == 0 or len(expanded_gdf) == 0:
        print(f"  Warning: No sites matched with geometries, skipping heatmaps")
        return

    # Convert to centroids if polygons
    if substance_gdf.geom_type.iloc[0] != 'Point':
        substance_gdf = substance_gdf.copy()
        substance_gdf['geometry'] = substance_gdf.geometry.centroid
    if expanded_gdf.geom_type.iloc[0] != 'Point':
        expanded_gdf = expanded_gdf.copy()
        expanded_gdf['geometry'] = expanded_gdf.geometry.centroid

    # Create side-by-side figure - larger size
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(24, 14))

    # Plot Denmark backdrop on both
    if denmark_gdf is not None:
        denmark_gdf.boundary.plot(ax=ax1, color='black', linewidth=1.5, zorder=1)
        denmark_gdf.plot(ax=ax1, color='white', alpha=0.3, zorder=0)
        denmark_gdf.boundary.plot(ax=ax2, color='black', linewidth=1.5, zorder=1)
        denmark_gdf.plot(ax=ax2, color='white', alpha=0.3, zorder=0)

    # Larger hexagons - 50% bigger than before
    gridsize = 27  # Larger hexagons (was 40)

    # Core scenario (left) - use Oranges colormap for both
    x1 = substance_gdf.geometry.x
    y1 = substance_gdf.geometry.y
    hexbin1 = ax1.hexbin(x1, y1, gridsize=gridsize,
                         cmap='Oranges', mincnt=1, alpha=0.7, edgecolors='none', zorder=2)

    # Expanded scenario (right) - same Oranges colormap for comparison
    x2 = expanded_gdf.geometry.x
    y2 = expanded_gdf.geometry.y
    hexbin2 = ax2.hexbin(x2, y2, gridsize=gridsize,
                         cmap='Oranges', mincnt=1, alpha=0.7, edgecolors='none', zorder=2)

    # IMPORTANT: Use same vmin/vmax for comparable colorbars
    vmax = max(hexbin1.get_array().max(), hexbin2.get_array().max())
    hexbin1.set_clim(vmin=1, vmax=vmax)
    hexbin2.set_clim(vmin=1, vmax=vmax)

    # Smaller colorbars
    cbar1 = plt.colorbar(hexbin1, ax=ax1, label='Number of sites', shrink=0.6, pad=0.02)
    cbar1.ax.tick_params(labelsize=9)
    cbar2 = plt.colorbar(hexbin2, ax=ax2, label='Number of sites', shrink=0.6, pad=0.02)
    cbar2.ax.tick_params(labelsize=9)

    ax1.set_title(f'Core Scenario: Substance Sites Only\n({len(substance_gdf):,} sites, 217 GVFKs)',
                  fontsize=14, fontweight='bold', pad=15)
    ax1.set_aspect('equal')
    ax1.axis('off')

    ax2.set_title(f'Expanded Scenario: Substance + Branch-only\n({len(expanded_gdf):,} sites, 309 GVFKs)',
                  fontsize=14, fontweight='bold', pad=15)
    ax2.set_aspect('equal')
    ax2.axis('off')

    # Match axis limits to Denmark extent if available
    if denmark_gdf is not None:
        bounds = denmark_gdf.total_bounds
        ax1.set_xlim(bounds[0], bounds[2])
        ax1.set_ylim(bounds[1], bounds[3])
        ax2.set_xlim(bounds[0], bounds[2])
        ax2.set_ylim(bounds[1], bounds[3])
    else:
        # Match to data extent
        all_x = list(x1) + list(x2)
        all_y = list(y1) + list(y2)
        xlim = (min(all_x), max(all_x))
        ylim = (min(all_y), max(all_y))
        ax1.set_xlim(xlim)
        ax1.set_ylim(ylim)
        ax2.set_xlim(xlim)
        ax2.set_ylim(ylim)

    plt.tight_layout()
    output_path = os.path.join(output_dir, 'hexagonal_heatmap_comparison.png')
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()

    print(f"  Saved: hexagonal_heatmap_comparison.png")


def create_gvfk_choropleth_maps(shapefiles, substance_sites, all_sites,
                                 gvfk_categories, output_dir):
    """
    Create side-by-side GVFK choropleth maps.

    Args:
        shapefiles: Dict with GVFK shapefiles
        substance_sites: Core scenario sites
        all_sites: Expanded scenario sites (substance + branch)
        gvfk_categories: GVFK categorization dict
        output_dir: Output directory path
    """
    print("\n[PHASE 4] Creating GVFK choropleth maps...")

    if 'all_dk' not in shapefiles:
        print("  Warning: Denmark shapefile not available")
        return

    all_dk_gdf = shapefiles['all_dk']

    # Count sites per GVFK for each scenario
    core_counts = substance_sites.groupby('Closest_GVFK').size()
    expanded_counts = all_sites.groupby('Closest_GVFK').size()

    # Merge with GeoDataFrame
    core_gdf = all_dk_gdf.copy()
    core_gdf['site_count'] = core_gdf['Navn'].map(core_counts).fillna(0)
    core_gdf = core_gdf[core_gdf['site_count'] > 0]  # Only GVFKs with sites

    expanded_gdf = all_dk_gdf.copy()
    expanded_gdf['site_count'] = expanded_gdf['Navn'].map(expanded_counts).fillna(0)
    expanded_gdf = expanded_gdf[expanded_gdf['site_count'] > 0]

    # Mark new GVFKs
    expanded_gdf['is_new'] = expanded_gdf['Navn'].isin(gvfk_categories['new_gvfks'])

    # Create side-by-side figure - larger size
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(24, 14))

    # Use same vmin/vmax for comparable legends
    vmin = 1
    vmax = max(core_gdf['site_count'].max(), expanded_gdf['site_count'].max())

    # Core scenario (left) - use Oranges colormap for both
    core_gdf.plot(column='site_count', ax=ax1, legend=True,
                  cmap='Oranges', edgecolor='black', linewidth=0.3,
                  vmin=vmin, vmax=vmax,
                  legend_kwds={'label': 'Sites per GVFK', 'shrink': 0.6, 'pad': 0.02})
    ax1.set_title(f'Core Scenario: {len(core_gdf)} GVFKs with Substance Sites\n(1,740 sites total)',
                  fontsize=14, fontweight='bold', pad=15)
    ax1.set_aspect('equal')
    ax1.axis('off')

    # Expanded scenario (right) - separate new GVFKs
    shared_expanded = expanded_gdf[~expanded_gdf['is_new']]
    new_expanded = expanded_gdf[expanded_gdf['is_new']]

    # Plot shared GVFKs first - same Oranges colormap for comparison
    shared_expanded.plot(column='site_count', ax=ax2, legend=True,
                         cmap='Oranges', edgecolor='black', linewidth=0.3,
                         vmin=vmin, vmax=vmax,
                         legend_kwds={'label': 'Sites per GVFK', 'shrink': 0.6, 'pad': 0.02})

    # Overlay new GVFKs with special styling
    if len(new_expanded) > 0:
        new_expanded.plot(ax=ax2, facecolor='none', edgecolor='red',
                         linewidth=2.5, hatch='///', alpha=0.7)

    ax2.set_title(f'Expanded Scenario: {len(expanded_gdf)} GVFKs (217 core + 92 new)\n(5,454 sites total)\nRed hatched = New GVFKs from branch-only sites',
                  fontsize=14, fontweight='bold', pad=15)
    ax2.set_aspect('equal')
    ax2.axis('off')

    plt.tight_layout()
    output_path = os.path.join(output_dir, 'gvfk_choropleth_comparison.png')
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()

    print(f"  Saved: gvfk_choropleth_comparison.png")


def create_regional_distribution_table(substance_sites, all_sites, gvfk_categories, output_dir):
    """
    Create regional distribution comparison table.

    Args:
        substance_sites: Core scenario sites
        all_sites: Expanded scenario sites
        gvfk_categories: GVFK categorization
        output_dir: Output directory path
    """
    print("\n[PHASE 4] Creating regional distribution table...")

    if 'Regionsnavn' not in substance_sites.columns:
        print("  Warning: No region information available")
        return

    # Count by region for each scenario
    core_region_sites = substance_sites.groupby('Regionsnavn').size()
    core_region_gvfks = substance_sites.groupby('Regionsnavn')['Closest_GVFK'].nunique()

    expanded_region_sites = all_sites.groupby('Regionsnavn').size()
    expanded_region_gvfks = all_sites.groupby('Regionsnavn')['Closest_GVFK'].nunique()

    # Build table
    regions = sorted(set(core_region_sites.index) | set(expanded_region_sites.index))

    table_data = []
    for region in regions:
        core_s = core_region_sites.get(region, 0)
        core_g = core_region_gvfks.get(region, 0)
        exp_s = expanded_region_sites.get(region, 0)
        exp_g = expanded_region_gvfks.get(region, 0)

        table_data.append({
            'Region': region,
            'Core GVFKs': core_g,
            'Core Sites': core_s,
            'Expanded GVFKs': exp_g,
            'Expanded Sites': exp_s,
            'Change GVFKs': exp_g - core_g,
            'Change Sites': exp_s - core_s
        })

    # Add total row
    table_data.append({
        'Region': 'TOTAL',
        'Core GVFKs': len(gvfk_categories['core_gvfks']),
        'Core Sites': len(substance_sites),
        'Expanded GVFKs': len(gvfk_categories['expanded_gvfks']),
        'Expanded Sites': len(all_sites),
        'Change GVFKs': len(gvfk_categories['new_gvfks']),
        'Change Sites': len(all_sites) - len(substance_sites)
    })

    df = pd.DataFrame(table_data)
    table_path = os.path.join(output_dir, 'regional_distribution.csv')
    df.to_csv(table_path, index=False)

    print(f"  Saved: regional_distribution.csv")
    print("\n  Regional Distribution:")
    print(df.to_string(index=False))

    return df


def create_new_gvfk_characteristics_table(new_gvfk_sites, gvfk_area_volume,
                                          gvfk_categories, output_dir):
    """
    Create detailed characteristics table for the 92 new GVFKs.

    Args:
        new_gvfk_sites: Sites in new GVFKs
        gvfk_area_volume: Area/volume lookup dict
        gvfk_categories: GVFK categorization
        output_dir: Output directory path
    """
    print("\n[PHASE 4] Creating new GVFK characteristics table...")

    new_gvfks = sorted(gvfk_categories['new_gvfks'])

    table_data = []
    for gvfk in new_gvfks:
        sites_in_gvfk = new_gvfk_sites[new_gvfk_sites['Closest_GVFK'] == gvfk]

        # Get area/volume
        area = gvfk_area_volume.get(gvfk, {}).get('area_km2', 0)
        volume = gvfk_area_volume.get(gvfk, {}).get('volume_m3', 0)

        # Get top branch and activity
        branches = count_occurrences(sites_in_gvfk, 'Lokalitetensbranche')
        activities = count_occurrences(sites_in_gvfk, 'Lokalitetensaktivitet')

        top_branch = f"{branches.index[0]} ({branches.iloc[0]})" if len(branches) > 0 else "N/A"
        top_activity = f"{activities.index[0]} ({activities.iloc[0]})" if len(activities) > 0 else "N/A"

        table_data.append({
            'GVFK': gvfk,
            'Sites': len(sites_in_gvfk),
            'Area (km²)': f"{area:.2f}",
            'Volume (m³)': f"{volume:.0f}",
            'Top Branch': top_branch,
            'Top Activity': top_activity
        })

    df = pd.DataFrame(table_data)
    table_path = os.path.join(output_dir, 'new_gvfk_characteristics.csv')
    df.to_csv(table_path, index=False)

    print(f"  Saved: new_gvfk_characteristics.csv")
    print(f"  Characterized {len(new_gvfks)} new GVFKs")

    return df


def run_phase4(data, output_dir):
    """
    Execute Phase 4: Geographic visualizations.

    Args:
        data: Dictionary from Phase 1 with loaded data
        output_dir: Output directory path
    """
    print("\n" + "=" * 60)
    print("PHASE 4: GEOGRAPHIC VISUALIZATIONS")
    print("=" * 60)

    substance_sites = data['substance_sites']
    branch_sites = data['branch_sites']
    new_gvfk_sites = data['sites_in_new_gvfks']
    gvfk_categories = data['gvfk_categories']
    gvfk_area_volume = data['gvfk_area_volume']
    shapefiles = data['shapefiles']

    # Combine for expanded scenario
    all_sites = pd.concat([substance_sites, branch_sites], ignore_index=True)

    # Create hexagonal heatmaps
    create_side_by_side_heatmaps(substance_sites, all_sites, output_dir)

    # Create choropleth maps
    create_gvfk_choropleth_maps(shapefiles, substance_sites, all_sites,
                                gvfk_categories, output_dir)

    # Create tables
    regional_df = create_regional_distribution_table(substance_sites, all_sites,
                                                     gvfk_categories, output_dir)

    new_gvfk_df = create_new_gvfk_characteristics_table(new_gvfk_sites, gvfk_area_volume,
                                                        gvfk_categories, output_dir)

    print("\n" + "=" * 60)
    print("[OK] PHASE 4 COMPLETE")
    print("=" * 60)

    return {
        'regional_distribution': regional_df,
        'new_gvfk_characteristics': new_gvfk_df
    }


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

    # Phase 3: Three-way branch/activity comparison
    comparison_results = run_phase3(data, output_dir)

    # Phase 4: Geographic visualizations
    geographic_results = run_phase4(data, output_dir)

    print("\n" + "=" * 80)
    print("[OK] STEP 6 ANALYSIS COMPLETE (ALL PHASES)")
    print("=" * 80)
    print(f"\nResults saved to: {output_dir}")
    print(f"\nGenerated outputs:")
    print(f"  - 4 progression visualizations")
    print(f"  - 3 comparison charts")
    print(f"  - 2 geographic maps")
    print(f"  - 5 comparison tables")


if __name__ == "__main__":
    run_step6_analysis()