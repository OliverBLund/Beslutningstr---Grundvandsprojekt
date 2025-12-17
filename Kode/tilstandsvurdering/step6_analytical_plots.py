"""
Step 6 – Analytical Plots
==========================

Information-rich static plots for Step 6 analysis.
Focus: Clear, single-purpose plots that convey key insights.

Plots:
1. Category Impact Overview - Multi-metric category comparison
2. Exceedance Analysis - Frequency and severity by category
3. GVFK Summary - Aquifer-level impact scatter plot
4. Flow Scenario Sensitivity - Impact of river flow on exceedances
5. Exceedance Severity Distribution - Histogram of exceedance magnitudes
"""

from __future__ import annotations

import sys
from pathlib import Path
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

# Ensure repository root is importable
REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from Kode.config import get_visualization_path, CATEGORY_DISPLAY_NAMES

# Reset and apply professional PowerPoint-ready styling
plt.style.use('default')
plt.rcParams.update({
    'font.family': ['Arial', 'DejaVu Sans', 'sans-serif'],
    'font.size': 14,
    'axes.titlesize': 18,
    'axes.labelsize': 16,
    'xtick.labelsize': 12,
    'ytick.labelsize': 12,
    'figure.dpi': 100,
    'savefig.dpi': 300,
    'savefig.bbox': 'tight',
    'savefig.facecolor': 'white',
    'figure.facecolor': 'white',
    'axes.facecolor': 'white',
    'axes.grid': False,
})


def create_analytical_plots(
    site_flux: pd.DataFrame,
    segment_flux: pd.DataFrame,
    cmix_results: pd.DataFrame,
    segment_summary: pd.DataFrame,
) -> None:
    """Generate all analytical plots for Step 6."""

    output_dir = get_visualization_path("step6", "analytical")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Apply standardized category names
    for df in [site_flux, segment_flux, cmix_results]:
        if 'Qualifying_Category' in df.columns:
            df['Qualifying_Category'] = df['Qualifying_Category'].map(
                lambda x: CATEGORY_DISPLAY_NAMES.get(x, x)
            )

    # Plot 1: Category Impact Overview
    plot_category_impact_overview(site_flux, segment_flux, cmix_results, output_dir)

    # Plot 2: Exceedance Analysis
    plot_exceedance_analysis(cmix_results, output_dir)

    # Plot 3: GVFK Summary
    plot_gvfk_summary(site_flux, segment_summary, cmix_results, output_dir)

    # Plot 4: Flow Scenario Sensitivity
    plot_flow_scenario_sensitivity(cmix_results, output_dir)

    # Plot 5: Exceedance Severity Distribution (NEW)
    plot_exceedance_severity_distribution(cmix_results, output_dir)

    # Plot 6: Site-River Impact Summary (NEW)
    plot_site_river_impact(site_flux, cmix_results, output_dir)

    # Plot 7: Category Contribution to Exceedances (NEW)
    plot_category_exceedance_contribution(site_flux, cmix_results, output_dir)


def plot_category_impact_overview(
    site_flux: pd.DataFrame,
    segment_flux: pd.DataFrame,
    cmix_results: pd.DataFrame,
    output_dir: Path,
) -> None:
    """Multi-metric category comparison with professional styling."""

    # Aggregate metrics by category
    category_metrics = []

    for cat in segment_flux['Qualifying_Category'].unique():
        cat_segments = segment_flux[segment_flux['Qualifying_Category'] == cat]
        cat_cmix = cmix_results[cmix_results['Qualifying_Category'] == cat]

        metrics = {
            'Category': cat,
            'Affected_Rivers': cat_segments['Nearest_River_ov_id'].nunique(),
            'Total_Flux_kg': cat_segments['Total_Flux_kg_per_year'].sum(),
            'Exceedance_Count': cat_cmix['Exceedance_Flag'].sum() if len(cat_cmix) > 0 else 0,
            'Median_Exceedance_Ratio': cat_cmix[cat_cmix['Exceedance_Flag']]['Exceedance_Ratio'].median()
                                        if cat_cmix['Exceedance_Flag'].sum() > 0 else 0,
        }
        category_metrics.append(metrics)

    df = pd.DataFrame(category_metrics).sort_values('Total_Flux_kg', ascending=False)

    # Create figure with 2x2 subplots
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))
    # fig.suptitle('Category Impact Overview', fontsize=20, fontweight='bold', y=1.02)
    categories = df['Category'].values
    
    # Professional colors
    colors = ['#4A90D9', '#5BA55B', '#D14545', '#F5A623']

    # Plot 1: Affected Rivers
    ax1 = axes[0, 0]
    ax1.barh(categories, df['Affected_Rivers'], color=colors[0], edgecolor='white')
    ax1.set_xlabel('Antal påvirkede vandløbssegmenter', fontweight='bold')
    ax1.set_title('Vandløbspåvirkning', fontweight='bold')
    ax1.invert_yaxis()

    # Plot 2: Total Flux (log scale)
    ax2 = axes[0, 1]
    ax2.barh(categories, df['Total_Flux_kg'], color=colors[1], edgecolor='white')
    ax2.set_xlabel('Total Flux (kg/år)', fontweight='bold')
    ax2.set_xscale('log')
    ax2.set_title('Forureningsflux', fontweight='bold')
    ax2.invert_yaxis()

    # Plot 3: Exceedance Count
    ax3 = axes[1, 0]
    ax3.barh(categories, df['Exceedance_Count'], color=colors[2], edgecolor='white')
    ax3.set_xlabel('Antal MKK-overskridelser', fontweight='bold')
    ax3.set_title('Miljøkvalitetskrav (MKK)', fontweight='bold')
    ax3.invert_yaxis()

    # Plot 4: Median Exceedance Ratio
    ax4 = axes[1, 1]
    ax4.barh(categories, df['Median_Exceedance_Ratio'], color=colors[3], edgecolor='white')
    ax4.set_xlabel('Median overskridelsesratio (Cmix/MKK)', fontweight='bold')
    ax4.set_xscale('log')
    ax4.set_title('Overskridelsens alvorlighed', fontweight='bold')
    ax4.invert_yaxis()

    plt.tight_layout()
    plt.savefig(output_dir / 'category_impact_overview.png', facecolor='white')
    plt.close()


def plot_exceedance_analysis(cmix_results: pd.DataFrame, output_dir: Path) -> None:
    """Exceedance frequency and severity by category.
    
    Shows UNIQUE SEGMENTS affected per category (not total exceedance rows).
    This provides a cleaner metric that matches the report table.
    """
    from config import CATEGORY_DISPLAY_NAMES

    exceedances = cmix_results[cmix_results['Exceedance_Flag'] == True]

    if exceedances.empty:
        print("    Warning: No exceedances found for exceedance analysis plot")
        return

    # Aggregate by category - use nunique for segments, not count of rows
    category_exc = exceedances.groupby('Qualifying_Category').agg({
        'Nearest_River_FID': 'nunique',  # Unique segments, not row count
        'Exceedance_Ratio': ['median', 'max']
    }).reset_index()

    category_exc.columns = ['Category', 'Unique_Segments', 'Median_Ratio', 'Max_Ratio']
    category_exc = category_exc.sort_values('Unique_Segments', ascending=False)
    
    # Apply display names for cleaner labels
    category_exc['Display_Name'] = category_exc['Category'].map(
        lambda x: CATEGORY_DISPLAY_NAMES.get(x, x)
    )

    fig, ax1 = plt.subplots(figsize=(14, 8))

    # Bar plot for unique segment counts
    x = np.arange(len(category_exc))
    bars = ax1.bar(x, category_exc['Unique_Segments'], color='#D14545', edgecolor='white', 
                   label='Påvirkede segmenter')
    ax1.set_xlabel('Kategori', fontsize=16, fontweight='bold')
    ax1.set_ylabel('Antal påvirkede segmenter', fontsize=16, fontweight='bold', color='#D14545')
    ax1.tick_params(axis='y', labelcolor='#D14545', labelsize=14)
    ax1.tick_params(axis='x', labelsize=14)
    ax1.set_xticks(x)
    ax1.set_xticklabels(category_exc['Display_Name'], rotation=45, ha='right')
    
    # Add value labels on bars
    for bar, val in zip(bars, category_exc['Unique_Segments']):
        ax1.text(bar.get_x() + bar.get_width()/2., bar.get_height(),
                f'{val}', ha='center', va='bottom', fontweight='bold', fontsize=11)

    # Line plot for median ratio
    ax2 = ax1.twinx()
    line = ax2.plot(x, category_exc['Median_Ratio'], color='#F5A623', marker='o',
                    linewidth=3, markersize=10, label='Median overskridelsesratio')
    ax2.set_ylabel('Median overskridelsesratio (log skala)', fontsize=16, fontweight='bold', color='#F5A623')
    ax2.tick_params(axis='y', labelcolor='#F5A623', labelsize=14)
    ax2.set_yscale('log')

    # Combine legends
    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2, loc='upper right', fontsize=12)

    plt.tight_layout()
    plt.savefig(output_dir / 'exceedance_analysis.png', facecolor='white')
    plt.close()


def plot_gvfk_summary(
    site_flux: pd.DataFrame,
    segment_summary: pd.DataFrame,
    cmix_results: pd.DataFrame,
    output_dir: Path,
) -> None:
    """
    GVFK-level summary scatter plot.
    
    DATA SOURCES:
    - site_flux: step6_flux_site_segment.csv (per-site flux rows)
    - segment_summary: step6_segment_summary.csv (per-segment aggregated)
    - cmix_results: step6_cmix_results.csv (Cmix calculations)
    
    METRICS:
    - X-axis: Unique river segments (ov_id) from segment_summary
    - Y-axis: Total flux from site_flux
    - Color: Max exceedance ratio from cmix_results  
    - Size: Unique site count from site_flux
    """

    # Aggregate metrics by GVFK
    gvfk_metrics = []

    for gvfk in site_flux['GVFK'].unique():
        gvfk_sites = site_flux[site_flux['GVFK'] == gvfk]
        gvfk_segments = segment_summary[segment_summary['River_Segment_GVFK'] == gvfk]
        gvfk_cmix = cmix_results[cmix_results['River_Segment_GVFK'] == gvfk] if 'River_Segment_GVFK' in cmix_results.columns else pd.DataFrame()

        metrics = {
            'GVFK': gvfk,
            'Site_Count': gvfk_sites['Lokalitet_ID'].nunique(),
            'River_Segment_Count': gvfk_segments['Nearest_River_ov_id'].nunique() if len(gvfk_segments) > 0 else 0,
            'Total_Flux_kg': gvfk_sites['Pollution_Flux_kg_per_year'].sum(),
            'Max_Exceedance_Ratio': gvfk_cmix['Exceedance_Ratio'].max() if len(gvfk_cmix) > 0 else 0,
        }
        gvfk_metrics.append(metrics)

    df = pd.DataFrame(gvfk_metrics)
    df = df[df['River_Segment_Count'] > 0]  # Filter out GVFKs with no affected rivers

    fig, ax = plt.subplots(figsize=(14, 10))

    # Scatter plot
    scatter = ax.scatter(
        df['River_Segment_Count'],
        df['Total_Flux_kg'],
        s=df['Site_Count'] * 30,  # Size by site count
        c=df['Max_Exceedance_Ratio'],
        cmap='YlOrRd',
        alpha=0.7,
        edgecolors='black',
        linewidth=0.5,
        norm=plt.matplotlib.colors.LogNorm()
    )

    ax.set_xlabel('Antal påvirkede vandløbssegmenter', fontsize=14, fontweight='bold')
    ax.set_ylabel('Total forureningsflux (kg/år)', fontsize=14, fontweight='bold')
    ax.set_yscale('log')
    # ax.set_title('GVFK Summary: Impact and Severity', fontsize=18, fontweight='bold', pad=15)

    # Colorbar
    cbar = plt.colorbar(scatter, ax=ax)
    cbar.set_label('Maks overskridelsesratio', fontsize=12, fontweight='bold')

    # Add legend for size
    for size in [1, 5, 10, 20]:
        ax.scatter([], [], s=size*30, c='gray', alpha=0.5, edgecolors='black',
                  label=f'{size} sites')
    ax.legend(scatterpoints=1, frameon=True, labelspacing=1, title='Antal lokaliteter', 
              loc='upper left', fontsize=10)

    # Annotate top 5 GVFKs
    top5 = df.nlargest(5, 'Total_Flux_kg')
    for _, row in top5.iterrows():
        ax.annotate(
            row['GVFK'].replace('dkms_', '').replace('_ks', ''),  # Shorten GVFK name
            (row['River_Segment_Count'], row['Total_Flux_kg']),
            xytext=(5, 5),
            textcoords='offset points',
            fontsize=9,
            fontweight='bold',
            bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.8, edgecolor='gray')
        )

    plt.tight_layout()
    plt.savefig(output_dir / 'gvfk_summary.png', facecolor='white')
    plt.close()


def plot_flow_scenario_sensitivity(cmix_results: pd.DataFrame, output_dir: Path) -> None:
    """Box plot showing Cmix/MKK ratio distribution across flow scenarios."""

    if cmix_results.empty or 'Flow_Scenario' not in cmix_results.columns:
        print("    Warning: No flow scenario data for sensitivity plot")
        return

    # Clean scenario values
    scenario_values = cmix_results['Flow_Scenario'].dropna().map(lambda x: str(x).strip())
    if scenario_values.empty:
        print("    Warning: Flow scenario column contains only NaN/blank values")
        return
    
    available_scenarios = sorted(set(s for s in scenario_values if s))
    if not available_scenarios:
        print("    Warning: Flow scenario labels missing after cleaning")
        return
    print(f"      Available flow scenarios: {', '.join(available_scenarios)}")

    # Filter to only exceedances
    exc = cmix_results[cmix_results['Exceedance_Flag'] == True].copy()
    exc = exc[exc['Flow_Scenario'].notna()].copy()
    exc['Flow_Scenario'] = exc['Flow_Scenario'].astype(str).str.strip()
    exc = exc[exc['Flow_Scenario'] != ""]

    if exc.empty:
        print("    Warning: No exceedances for flow scenario sensitivity plot")
        return

    # Select top 6 categories by exceedance count
    top_cats = exc['Qualifying_Category'].value_counts().head(6).index
    exc_filtered = exc[exc['Qualifying_Category'].isin(top_cats)].copy()

    # Define proper scenario order (low flow to high flow)
    scenario_order = ['Q95', 'Q90', 'Q50', 'Q10', 'Q05']
    scenario_order = [s for s in scenario_order if s in exc_filtered['Flow_Scenario'].unique()]
    if not scenario_order:
        print("    Warning: No recognized flow scenarios available for plotting")
        return

    exc_filtered['Flow_Scenario'] = pd.Categorical(
        exc_filtered['Flow_Scenario'],
        categories=scenario_order,
        ordered=True
    )

    fig, ax = plt.subplots(figsize=(16, 10))

    # Professional color palette
    colors = ['#D14545', '#E57C23', '#F5A623', '#7CB342', '#4A90D9'][:len(scenario_order)]
    
    sns.boxplot(
        data=exc_filtered.sort_values('Qualifying_Category'),
        x='Qualifying_Category',
        y='Exceedance_Ratio',
        hue='Flow_Scenario',
        hue_order=scenario_order,
        ax=ax,
        palette=colors
    )

    ax.set_yscale('log')
    ax.set_xlabel('Kategori', fontsize=14, fontweight='bold')
    ax.set_ylabel('Overskridelsesratio (Cmix/MKK)', fontsize=14, fontweight='bold')
    # ax.set_title(
    #     f'Flow Scenario Sensitivity: Impact of River Flow on Exceedances\n'
    #     f'(Q95=low flow/worst case → Q05=high flow/best case)',
    #     fontsize=16, fontweight='bold', pad=15
    # )
    ax.legend(title='Vandføringsscenarie', loc='upper right', fontsize=11)
    plt.xticks(rotation=45, ha='right')

    plt.tight_layout()
    plt.savefig(output_dir / 'flow_scenario_sensitivity.png', facecolor='white')
    plt.close()


def plot_exceedance_severity_distribution(cmix_results: pd.DataFrame, output_dir: Path) -> None:
    """
    NEW: Histogram showing distribution of exceedance severity.
    Bins: 1-10x, 10-100x, 100-1000x, 1000x+ MKK exceedances.
    """
    
    exceedances = cmix_results[cmix_results['Exceedance_Flag'] == True].copy()
    
    if exceedances.empty:
        print("    Warning: No exceedances found for severity distribution plot")
        return
    
    # Define exceedance bins
    bins = [1, 10, 100, 1000, 10000]
    labels = ['1-10×', '10-100×', '100-1,000×', '1,000×+']
    
    exceedances['Severity_Bin'] = pd.cut(
        exceedances['Exceedance_Ratio'], 
        bins=bins, 
        labels=labels, 
        include_lowest=True
    )
    
    # Handle values above 10000
    exceedances.loc[exceedances['Exceedance_Ratio'] >= 10000, 'Severity_Bin'] = '1,000×+'
    
    # Count per bin
    severity_counts = exceedances['Severity_Bin'].value_counts().reindex(labels, fill_value=0)
    
    fig, ax = plt.subplots(figsize=(12, 8))
    
    # Color gradient from yellow (mild) to dark red (severe)
    colors = ['#F5A623', '#E57C23', '#D14545', '#8B0000']
    
    bars = ax.bar(severity_counts.index, severity_counts.values, color=colors, edgecolor='white', linewidth=2)
    
    # Add count labels on bars
    for bar, count in zip(bars, severity_counts.values):
        height = bar.get_height()
        if height > 0:
            ax.text(bar.get_x() + bar.get_width()/2., height + max(severity_counts)*0.02,
                   f'{count:,}', ha='center', va='bottom', fontsize=14, fontweight='bold')
    
    ax.set_xlabel('Overskridelsens alvorlighed (Cmix/MKK ratio)', fontsize=14, fontweight='bold')
    ax.set_ylabel('Antal overskridelser', fontsize=14, fontweight='bold')
    # ax.set_title('MKK Exceedance Severity Distribution', fontsize=18, fontweight='bold', pad=15)
    
    # Add summary stats
    total = len(exceedances)
    worst = exceedances['Exceedance_Ratio'].max()
    median = exceedances['Exceedance_Ratio'].median()
    
    stats_text = (
        f"Totale overskridelser: {total:,}\n"
        f"Median: {median:.1f}× MKK\n"
        f"Værst: {worst:,.0f}× MKK"
    )
    ax.text(0.98, 0.98, stats_text, transform=ax.transAxes, fontsize=12,
            verticalalignment='top', horizontalalignment='right',
            bbox=dict(boxstyle='round', facecolor='white', edgecolor='gray', alpha=0.9))
    
    plt.tight_layout()
    plt.savefig(output_dir / 'exceedance_severity_distribution.png', facecolor='white')
    plt.close()


def plot_site_river_impact(site_flux: pd.DataFrame, cmix_results: pd.DataFrame, output_dir: Path) -> None:
    """
    NEW: Shows how many sites affect how many river segments.
    Answers: How concentrated is pollution? Few sites = many rivers or distributed?
    """
    
    # cmix_results has Contributing_Site_IDs (semicolon-separated) and River_Segment_GVFK
    required_cols = ['Contributing_Site_IDs', 'River_Segment_GVFK', 'Exceedance_Flag']
    if not all(col in cmix_results.columns for col in required_cols):
        print(f"    Warning: Missing columns for site-river impact plot. Have: {cmix_results.columns.tolist()}")
        return
    
    exceedances = cmix_results[cmix_results['Exceedance_Flag'] == True].copy()
    
    if exceedances.empty:
        print("    Warning: No exceedances for site-river impact plot")
        return
    
    # Parse Contributing_Site_IDs and count rivers per site
    site_river_pairs = []
    for _, row in exceedances.iterrows():
        site_ids = str(row['Contributing_Site_IDs']).split(', ')
        gvfk = row['River_Segment_GVFK']
        for site_id in site_ids:
            site_id = site_id.strip()
            if site_id:
                site_river_pairs.append({'Site_ID': site_id, 'GVFK': gvfk})
    
    if not site_river_pairs:
        print("    Warning: No valid site-river pairs found")
        return
    
    pair_df = pd.DataFrame(site_river_pairs)
    
    # Count unique GVFKs affected per site
    site_gvfk_counts = pair_df.groupby('Site_ID')['GVFK'].nunique().reset_index()
    site_gvfk_counts.columns = ['Site_ID', 'Rivers_Affected']
    
    # Create histogram of sites by number of rivers they affect
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 7))
    
    # Left: Histogram of rivers affected per site
    max_rivers = site_gvfk_counts['Rivers_Affected'].max()
    bins = range(1, min(int(max_rivers) + 2, 21))  # Cap at 20 for readability
    
    counts, edges, bars = ax1.hist(site_gvfk_counts['Rivers_Affected'], bins=bins, 
                                    color='#2E86AB', edgecolor='white', linewidth=1.5)
    
    ax1.set_xlabel('Antal påvirkede vandløbssegmenter', fontsize=14, fontweight='bold')
    ax1.set_ylabel('Antal lokaliteter', fontsize=14, fontweight='bold')
    # ax1.set_title('Site Impact Distribution\n(How Many Rivers Does Each Site Affect?)', 
    #               fontsize=16, fontweight='bold', pad=15)
    ax1.set_title('Lokalitetspåvirkning', fontsize=16, fontweight='bold', pad=15) # Keep Subtitle
    
    # Add labels on significant bars
    max_count = max(counts) if len(counts) > 0 else 1
    for i, (count, bar) in enumerate(zip(counts, bars)):
        if count > 0:
            ax1.text(bar.get_x() + bar.get_width()/2., count + max_count*0.02,
                    f'{int(count)}', ha='center', va='bottom', fontsize=10, fontweight='bold')
    
    # Right: Top 15 most impactful sites
    top_sites = site_gvfk_counts.nlargest(15, 'Rivers_Affected')
    
    # Color gradient based on impact
    colors = plt.cm.Reds(np.linspace(0.3, 0.9, len(top_sites)))[::-1]
    
    bars2 = ax2.barh(range(len(top_sites)), top_sites['Rivers_Affected'].values, 
                     color=colors, edgecolor='white', linewidth=1.5)
    ax2.set_yticks(range(len(top_sites)))
    ax2.set_yticklabels([f"{str(sid)[:20]}..." if len(str(sid)) > 20 else str(sid) 
                         for sid in top_sites['Site_ID']], fontsize=10)
    ax2.invert_yaxis()
    ax2.set_xlabel('Antal påvirkede vandløbssegmenter', fontsize=14, fontweight='bold')
    ax2.set_title('Top 15 mest påvirkende lokaliteter', fontsize=16, fontweight='bold', pad=15) # Keep Subtitle
    
    # Add value labels
    max_rivers_val = max(top_sites['Rivers_Affected']) if len(top_sites) > 0 else 1
    for i, (bar, val) in enumerate(zip(bars2, top_sites['Rivers_Affected'].values)):
        ax2.text(val + max_rivers_val*0.02, bar.get_y() + bar.get_height()/2,
                f'{val}', ha='left', va='center', fontsize=11, fontweight='bold')
    
    # Add summary stats
    total_sites = len(site_gvfk_counts)
    total_rivers = pair_df['GVFK'].nunique()
    avg_per_site = site_gvfk_counts['Rivers_Affected'].mean()
    
    stats_text = (
        f"Sammenfatning:\n"
        f"• {total_sites:,} lokaliteter med overskridelser\n"
        f"• {total_rivers:,} påvirkede vandløb\n"
        f"• Gns: {avg_per_site:.1f} vandløb pr. site"
    )
    ax1.text(0.98, 0.98, stats_text, transform=ax1.transAxes, fontsize=11,
             verticalalignment='top', horizontalalignment='right',
             bbox=dict(boxstyle='round', facecolor='white', edgecolor='gray', alpha=0.9))
    
    plt.tight_layout()
    plt.savefig(output_dir / 'site_river_impact.png', facecolor='white')
    plt.close()


def plot_category_exceedance_contribution(site_flux: pd.DataFrame, cmix_results: pd.DataFrame, output_dir: Path) -> None:
    """
    NEW: Shows which site categories drive MKK exceedances.
    Bar chart with total exceedance count per category.
    """
    
    # cmix_results already has Qualifying_Category column
    if 'Qualifying_Category' not in cmix_results.columns:
        print("    Warning: Missing Qualifying_Category for category contribution plot")
        return
    
    exceedances = cmix_results[cmix_results['Exceedance_Flag'] == True].copy()
    
    if exceedances.empty:
        print("    Warning: No exceedances for category contribution plot")
        return
    
    category_col = 'Qualifying_Category'
    
    # Count exceedances by category
    category_counts = exceedances[category_col].value_counts()
    
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 8))
    
    # Left: Bar chart of exceedance counts by category
    colors = plt.cm.RdYlGn_r(np.linspace(0.2, 0.8, len(category_counts)))
    
    bars = ax1.bar(range(len(category_counts)), category_counts.values, 
                   color=colors, edgecolor='white', linewidth=2)
    ax1.set_xticks(range(len(category_counts)))
    ax1.set_xticklabels(category_counts.index, rotation=45, ha='right', fontsize=11)
    ax1.set_ylabel('Antal overskridelser', fontsize=14, fontweight='bold')
    ax1.set_title('Overskridelser pr. kategori', fontsize=18, fontweight='bold', pad=15) # Keep Subtitle
    
    # Add value labels
    max_cat_count = max(category_counts) if len(category_counts) > 0 else 1
    for bar, count in zip(bars, category_counts.values):
        height = bar.get_height()
        ax1.text(bar.get_x() + bar.get_width()/2., height + max_cat_count*0.02,
                f'{count:,}', ha='center', va='bottom', fontsize=12, fontweight='bold')
    
    # Right: Average exceedance severity by category
    avg_severity = exceedances.groupby(category_col)['Exceedance_Ratio'].median()
    avg_severity = avg_severity.reindex(category_counts.index)  # Same order
    
    severity_colors = plt.cm.Reds(np.linspace(0.3, 0.9, len(avg_severity)))
    
    bars2 = ax2.bar(range(len(avg_severity)), avg_severity.values,
                    color=severity_colors, edgecolor='white', linewidth=2)
    ax2.set_xticks(range(len(avg_severity)))
    ax2.set_xticklabels(avg_severity.index, rotation=45, ha='right', fontsize=11)
    ax2.set_ylabel('Median overskridelsesratio (Cmix/MKK)', fontsize=14, fontweight='bold')
    ax2.set_title('Overskridelses-alvorlighed pr. kategori', fontsize=18, fontweight='bold', pad=15) # Keep Subtitle
    ax2.set_yscale('log')  # Log scale for severity
    
    # Add value labels
    for bar, val in zip(bars2, avg_severity.values):
        if not np.isnan(val):
            ax2.text(bar.get_x() + bar.get_width()/2., val * 1.2,
                    f'{val:.1f}×', ha='center', va='bottom', fontsize=10, fontweight='bold')
    
    # Summary stats
    worst_cat = avg_severity.idxmax()
    most_freq_cat = category_counts.idxmax()
    
    stats_text = (
        f"Nøglefund:\n"
        f"• Flest overskridelser: {most_freq_cat}\n"
        f"  ({category_counts.max():,} overskridelser)\n"
        f"• Værst alvorlighed: {worst_cat}\n"
        f"  ({avg_severity.max():.1f}× median ratio)"
    )
    fig.text(0.5, 0.02, stats_text, ha='center', fontsize=12,
             bbox=dict(boxstyle='round', facecolor='lightyellow', edgecolor='orange', alpha=0.9))
    
    plt.tight_layout(rect=[0, 0.12, 1, 1])
    plt.savefig(output_dir / 'category_exceedance_contribution.png', facecolor='white')
    plt.close()

