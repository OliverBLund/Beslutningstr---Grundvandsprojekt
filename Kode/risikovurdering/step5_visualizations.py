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
    Uses display names for cleaner labels and shows percentages.
    """
    from config import CATEGORY_DISPLAY_NAMES
    
    if 'Qualifying_Category' not in compound_combinations.columns:
        print("  Warning: No category column found in data")
        return

    # Count combinations per category
    category_counts = compound_combinations['Qualifying_Category'].value_counts()
    total = category_counts.sum()

    # Sort by count (ascending for horizontal bar)
    category_counts = category_counts.sort_values(ascending=True)
    
    # Map to display names
    display_names = [CATEGORY_DISPLAY_NAMES.get(cat, cat) for cat in category_counts.index]

    fig, ax = plt.subplots(figsize=(12, 8))

    # Create horizontal bar chart with professional color
    bars = ax.barh(range(len(category_counts)), category_counts.values, 
                   color='#4A90D9', edgecolor='white', linewidth=1.5)
    
    ax.set_yticks(range(len(category_counts)))
    ax.set_yticklabels(display_names, fontsize=12)

    # Labels
    ax.set_xlabel('Antal kombinationer', fontsize=14, fontweight='bold')
    ax.set_ylabel('Stofkategori', fontsize=14, fontweight='bold')
    ax.grid(axis='x', alpha=0.3)

    # Add value labels on bars with count and percentage
    for i, (count, bar) in enumerate(zip(category_counts.values, bars)):
        pct = count / total * 100
        ax.text(count + total*0.01, bar.get_y() + bar.get_height()/2,
                f'{count:,} ({pct:.1f}%)', va='center', ha='left', 
                fontweight='bold', fontsize=11)
    
    # Extend x-axis to fit labels
    ax.set_xlim(0, category_counts.max() * 1.25)

    # Add summary statistics
    unique_sites = compound_combinations['Lokalitet_ID'].nunique() if 'Lokalitet_ID' in compound_combinations.columns else 0
    unique_gvfks = compound_combinations['GVFK'].nunique() if 'GVFK' in compound_combinations.columns else 0

    summary_text = f"Total: {total:,} kombinationer\n{unique_sites:,} lokaliteter | {unique_gvfks} GVF'er"
    ax.text(0.98, 0.02, summary_text, transform=ax.transAxes,
            verticalalignment='bottom', horizontalalignment='right',
            fontsize=11, bbox=dict(boxstyle='round', facecolor='lightblue', alpha=0.5))

    plt.tight_layout()
    plt.savefig(os.path.join(figures_path, 'step5b_category_breakdown.png'), dpi=150)
    plt.close()



