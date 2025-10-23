"""
Step 5 Visualizations: Essential Verification Plots
===================================================

Creates minimal visualizations for verifying core risk assessment functionality:
1. Distance distribution with thresholds
2. Category breakdown
3. GV FK progression through workflow

For extended visualizations, see optional_analysis/ folder.
"""

import pandas as pd
import matplotlib.pyplot as plt
import os

# Simple clean styling
plt.rcParams.update({
    'font.family': ['Arial', 'DejaVu Sans', 'sans-serif'],
    'font.size': 10,
    'axes.titlesize': 12,
    'axes.labelsize': 11,
    'figure.dpi': 100,
    'savefig.dpi': 300,
    'savefig.bbox': 'tight',
})


def create_step5_visualizations():
    """Create essential Step 5 verification plots."""
    print("Creating essential Step 5 visualizations...")

    from config import get_visualization_path, get_output_path, WORKFLOW_SETTINGS

    figures_path = get_visualization_path("step5")
    os.makedirs(figures_path, exist_ok=True)

    # Plot 1: Distance distribution for general assessment (500m threshold)
    high_risk_file = get_output_path("step5_high_risk_sites")
    if os.path.exists(high_risk_file):
        try:
            high_risk_sites = pd.read_csv(high_risk_file)
            create_distance_distribution(high_risk_sites, figures_path,
                                        WORKFLOW_SETTINGS['risk_threshold_m'])
            print(f"  ✓ Distance distribution plot created")
        except Exception as e:
            print(f"  ⚠ Could not create distance distribution: {e}")
    else:
        print(f"  ⚠ General assessment file not found: {high_risk_file}")

    # Plot 2: Category breakdown for compound-specific assessment
    compound_file = get_output_path("step5_compound_detailed_combinations")
    if os.path.exists(compound_file):
        try:
            compound_combinations = pd.read_csv(compound_file)
            create_category_breakdown(compound_combinations, figures_path)
            print(f"  ✓ Category breakdown plot created")
        except Exception as e:
            print(f"  ⚠ Could not create category breakdown: {e}")
    else:
        print(f"  ⚠ Compound combinations file not found: {compound_file}")

    # Plot 3: GVFK progression through workflow
    try:
        create_gvfk_progression_chart(figures_path)
        print(f"  ✓ GVFK progression chart created")
    except Exception as e:
        print(f"  ⚠ Could not create GVFK progression: {e}")

    print(f"\n[OK] Essential visualizations saved to: {figures_path}")


def create_distance_distribution(high_risk_sites, figures_path, threshold_m=500):
    """
    Create histogram showing distance distribution of high-risk sites.
    Verifies that distance calculation and threshold application work correctly.
    """
    if 'Final_Distance_m' not in high_risk_sites.columns and 'Distance_to_River_m' not in high_risk_sites.columns:
        print("  Warning: No distance column found in data")
        return

    distance_col = 'Final_Distance_m' if 'Final_Distance_m' in high_risk_sites.columns else 'Distance_to_River_m'
    distances = high_risk_sites[distance_col].dropna()

    fig, ax = plt.subplots(figsize=(10, 6))

    # Create histogram
    ax.hist(distances, bins=50, edgecolor='black', alpha=0.7, color='#1E88E5')

    # Add threshold line
    ax.axvline(x=threshold_m, color='red', linestyle='--', linewidth=2,
               label=f'Threshold: {threshold_m}m')

    # Labels and title
    ax.set_xlabel('Distance to River (m)', fontweight='bold')
    ax.set_ylabel('Number of Sites', fontweight='bold')
    ax.set_title(f'Distance Distribution of High-Risk Sites (≤{threshold_m}m)',
                 fontweight='bold', pad=15)
    ax.legend()
    ax.grid(axis='y', alpha=0.3)

    # Add statistics text box
    stats_text = f"Total Sites: {len(distances):,}\nMean: {distances.mean():.1f}m\nMedian: {distances.median():.1f}m"
    ax.text(0.98, 0.97, stats_text, transform=ax.transAxes,
            verticalalignment='top', horizontalalignment='right',
            bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))

    plt.tight_layout()
    plt.savefig(os.path.join(figures_path, 'step5a_distance_distribution.png'))
    plt.close()


def create_category_breakdown(compound_combinations, figures_path):
    """
    Create bar chart showing number of site-GVFK-substance combinations per category.
    Verifies that compound categorization is working correctly.
    """
    if 'Qualifying_Category' not in compound_combinations.columns:
        print("  Warning: No category column found in data")
        return

    # Count combinations per category
    category_counts = compound_combinations['Qualifying_Category'].value_counts()

    # Sort by count
    category_counts = category_counts.sort_values(ascending=True)

    fig, ax = plt.subplots(figsize=(10, 8))

    # Create horizontal bar chart
    colors = plt.cm.Set3(range(len(category_counts)))
    ax.barh(category_counts.index, category_counts.values, color=colors, edgecolor='black')

    # Labels and title
    ax.set_xlabel('Number of Site-GVFK-Substance Combinations', fontweight='bold')
    ax.set_ylabel('Compound Category', fontweight='bold')
    ax.set_title('Compound Category Distribution (Step 5b)', fontweight='bold', pad=15)
    ax.grid(axis='x', alpha=0.3)

    # Add value labels on bars
    for i, (cat, count) in enumerate(category_counts.items()):
        ax.text(count, i, f'  {count:,}', va='center', ha='left', fontweight='bold')

    # Add summary statistics
    total_combinations = len(compound_combinations)
    unique_sites = compound_combinations['Lokalitet_ID'].nunique() if 'Lokalitet_ID' in compound_combinations.columns else 0
    unique_gvfks = compound_combinations['GVFK'].nunique() if 'GVFK' in compound_combinations.columns else 0

    summary_text = f"Total: {total_combinations:,} combinations\n{unique_sites:,} sites | {unique_gvfks} GVFKs"
    ax.text(0.98, 0.02, summary_text, transform=ax.transAxes,
            verticalalignment='bottom', horizontalalignment='right',
            bbox=dict(boxstyle='round', facecolor='lightblue', alpha=0.5))

    plt.tight_layout()
    plt.savefig(os.path.join(figures_path, 'step5b_category_breakdown.png'))
    plt.close()


def create_gvfk_progression_chart(figures_path):
    """
    Create bar chart showing GVFK count progression through workflow steps.
    Verifies that filtering logic is working correctly at each step.
    """
    from config import get_output_path, GRUNDVAND_PATH
    import geopandas as gpd

    steps = []
    counts = []

    # Step 1: All Denmark
    try:
        all_gvfk = gpd.read_file(GRUNDVAND_PATH)
        steps.append('Step 1:\nAll GVFKs')
        counts.append(len(all_gvfk))
    except:
        pass

    # Step 2: River contact
    step2_file = get_output_path('step2_river_gvfk')
    if os.path.exists(step2_file):
        try:
            river_gvfk = gpd.read_file(step2_file)
            steps.append('Step 2:\nRiver Contact')
            counts.append(len(river_gvfk))
        except:
            pass

    # Step 3: V1/V2 sites
    step3_file = get_output_path('step3_gvfk_polygons')
    if os.path.exists(step3_file):
        try:
            v1v2_gvfk = gpd.read_file(step3_file)
            steps.append('Step 3:\nV1/V2 Sites')
            counts.append(len(v1v2_gvfk))
        except:
            pass

    # Step 5a: General assessment (500m)
    step5a_file = get_output_path('step5_high_risk_sites')
    if os.path.exists(step5a_file):
        try:
            step5a_sites = pd.read_csv(step5a_file)
            gvfk_count = step5a_sites['GVFK'].nunique() if 'GVFK' in step5a_sites.columns else 0
            steps.append('Step 5a:\nGeneral\n(≤500m)')
            counts.append(gvfk_count)
        except:
            pass

    # Step 5b: Compound-specific
    step5b_file = get_output_path('step5_compound_detailed_combinations')
    if os.path.exists(step5b_file):
        try:
            step5b_combinations = pd.read_csv(step5b_file)
            gvfk_col = 'GVFK' if 'GVFK' in step5b_combinations.columns else 'Closest_GVFK'
            gvfk_count = step5b_combinations[gvfk_col].nunique() if gvfk_col in step5b_combinations.columns else 0
            steps.append('Step 5b:\nCompound-\nSpecific')
            counts.append(gvfk_count)
        except:
            pass

    if not steps:
        print("  Warning: No step data found for progression chart")
        return

    fig, ax = plt.subplots(figsize=(10, 6))

    # Create bar chart with gradient colors
    colors = ['#90CAF9', '#64B5F6', '#42A5F5', '#2196F3', '#1976D2']
    bars = ax.bar(steps, counts, color=colors[:len(steps)], edgecolor='black', linewidth=1)

    # Add value labels on bars
    for bar, count in zip(bars, counts):
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width() / 2., height,
                f'{count:,}',
                ha='center', va='bottom', fontweight='bold')

    # Labels and title
    ax.set_ylabel('Number of GVFKs', fontweight='bold')
    ax.set_title('GVFK Progression Through Workflow', fontweight='bold', fontsize=14, pad=15)
    ax.grid(axis='y', alpha=0.3)
    ax.set_axisbelow(True)

    plt.tight_layout()
    plt.savefig(os.path.join(figures_path, 'workflow_gvfk_progression.png'))
    plt.close()


if __name__ == "__main__":
    # Allow running this module independently
    create_step5_visualizations()
