"""
Step 6 – Analytical Plots
==========================

Information-rich static plots for Step 6 analysis.
Focus: Clear, single-purpose plots that convey multiple dimensions of data.
"""

from __future__ import annotations

import sys
from pathlib import Path
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from typing import Dict

# Ensure repository root is importable
REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from Kode.config import get_visualization_path

# Set style
plt.style.use('seaborn-v0_8-darkgrid')
sns.set_palette("husl")


def create_analytical_plots(
    site_flux: pd.DataFrame,
    segment_flux: pd.DataFrame,
    cmix_results: pd.DataFrame,
    segment_summary: pd.DataFrame,
) -> None:
    """Generate all analytical plots for Step 6."""

    output_dir = get_visualization_path("step6", "analytical")
    output_dir.mkdir(parents=True, exist_ok=True)

    print("  Creating analytical plots...")

    # Plot 1: Category Impact Overview
    print("    - Category impact overview...")
    plot_category_impact_overview(site_flux, segment_flux, cmix_results, output_dir)

    # Plot 2: Top Polluters - Sites
    print("    - Top polluting sites...")
    plot_top_polluting_sites(site_flux, output_dir)

    # Plot 3: Top Affected Rivers
    print("    - Top affected rivers...")
    plot_top_affected_rivers(segment_flux, output_dir)

    # Plot 4: Exceedance Analysis
    print("    - Exceedance analysis...")
    plot_exceedance_analysis(cmix_results, output_dir)

    # Plot 5: GVFK Summary
    print("    - GVFK summary...")
    plot_gvfk_summary(site_flux, segment_summary, cmix_results, output_dir)

    # Plot 6: Flow Scenario Sensitivity
    print("    - Flow scenario sensitivity...")
    plot_flow_scenario_sensitivity(cmix_results, output_dir)

    # Plot 7: Multi-scenario category breakdown
    print("    - Category scenario breakdown...")
    plot_multi_scenario_breakdown(segment_flux, cmix_results, output_dir)

    # Plot 7: Substance Detail Treemap
    print("    - Substance contribution treemap...")
    plot_substance_treemap(segment_flux, output_dir)

    print(f"  Analytical plots saved to {output_dir}/")


def plot_category_impact_overview(
    site_flux: pd.DataFrame,
    segment_flux: pd.DataFrame,
    cmix_results: pd.DataFrame,
    output_dir: Path,
) -> None:
    """Multi-metric category comparison."""

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
    fig.suptitle('Category Impact Overview - Multiple Metrics', fontsize=16, fontweight='bold')

    categories = df['Category'].values

    # Plot 1: Affected Rivers
    ax1 = axes[0, 0]
    ax1.barh(categories, df['Affected_Rivers'], color='steelblue')
    ax1.set_xlabel('Number of Affected River Segments')
    ax1.set_title('River Segment Impact')
    ax1.invert_yaxis()

    # Plot 2: Total Flux (log scale)
    ax2 = axes[0, 1]
    ax2.barh(categories, df['Total_Flux_kg'], color='darkgreen')
    ax2.set_xlabel('Total Flux (kg/year, log scale)')
    ax2.set_xscale('log')
    ax2.set_title('Pollution Flux')
    ax2.invert_yaxis()

    # Plot 3: Exceedance Count
    ax3 = axes[1, 0]
    ax3.barh(categories, df['Exceedance_Count'], color='darkred')
    ax3.set_xlabel('Number of MKK Exceedances')
    ax3.set_title('Regulatory Exceedances')
    ax3.invert_yaxis()

    # Plot 4: Median Exceedance Ratio
    ax4 = axes[1, 1]
    ax4.barh(categories, df['Median_Exceedance_Ratio'], color='darkorange')
    ax4.set_xlabel('Median Exceedance Ratio (Cmix/MKK)')
    ax4.set_xscale('log')
    ax4.set_title('Exceedance Severity')
    ax4.invert_yaxis()

    plt.tight_layout()
    plt.savefig(output_dir / 'category_impact_overview.png', dpi=300, bbox_inches='tight')
    plt.close()


def plot_top_polluting_sites(site_flux: pd.DataFrame, output_dir: Path) -> None:
    """Top 20 sites by total flux."""

    site_totals = site_flux.groupby(['Lokalitet_ID', 'Qualifying_Category']).agg({
        'Pollution_Flux_kg_per_year': 'sum',
        'Nearest_River_ov_id': 'nunique'
    }).reset_index()

    site_totals = site_totals.rename(columns={'Nearest_River_ov_id': 'Affected_Rivers'})
    top_sites = site_totals.nlargest(20, 'Pollution_Flux_kg_per_year')

    fig, ax = plt.subplots(figsize=(12, 10))

    # Create bars colored by category
    categories = top_sites['Qualifying_Category'].unique()
    colors = plt.cm.tab20(np.linspace(0, 1, len(categories)))
    color_map = dict(zip(categories, colors))

    bars = ax.barh(
        range(len(top_sites)),
        top_sites['Pollution_Flux_kg_per_year'],
        color=[color_map[cat] for cat in top_sites['Qualifying_Category']]
    )

    ax.set_yticks(range(len(top_sites)))
    ax.set_yticklabels(top_sites['Lokalitet_ID'])
    ax.set_xlabel('Total Pollution Flux (kg/year, log scale)')
    ax.set_xscale('log')
    ax.set_title('Top 20 Polluting Sites', fontsize=14, fontweight='bold')
    ax.invert_yaxis()

    # Add annotations
    for i, (idx, row) in enumerate(top_sites.iterrows()):
        ax.text(
            row['Pollution_Flux_kg_per_year'] * 1.1,
            i,
            f"{row['Affected_Rivers']} rivers",
            va='center',
            fontsize=8,
            color='gray'
        )

    # Add legend
    handles = [plt.Rectangle((0,0),1,1, color=color_map[cat]) for cat in categories[:10]]  # Limit legend
    ax.legend(handles, categories[:10], loc='lower right', fontsize=8, title='Category')

    plt.tight_layout()
    plt.savefig(output_dir / 'top_polluting_sites.png', dpi=300, bbox_inches='tight')
    plt.close()


def plot_top_affected_rivers(segment_flux: pd.DataFrame, output_dir: Path) -> None:
    """Top 20 river segments by total flux, stacked by category."""

    river_totals = segment_flux.groupby(['Nearest_River_ov_id', 'River_Segment_Name']).agg({
        'Total_Flux_kg_per_year': 'sum'
    }).reset_index()

    top_rivers = river_totals.nlargest(20, 'Total_Flux_kg_per_year')

    # Get category breakdown for these rivers
    top_river_ids = top_rivers['Nearest_River_ov_id'].values
    category_breakdown = segment_flux[segment_flux['Nearest_River_ov_id'].isin(top_river_ids)]

    # Pivot for stacked bar
    pivot = category_breakdown.pivot_table(
        index=['Nearest_River_ov_id', 'River_Segment_Name'],
        columns='Qualifying_Category',
        values='Total_Flux_kg_per_year',
        aggfunc='sum',
        fill_value=0
    )

    # Sort by total
    pivot['_total'] = pivot.sum(axis=1)
    pivot = pivot.sort_values('_total', ascending=True).tail(20)
    pivot = pivot.drop('_total', axis=1)

    fig, ax = plt.subplots(figsize=(12, 10))

    pivot.plot(kind='barh', stacked=True, ax=ax, width=0.8)

    ax.set_xlabel('Total Pollution Flux (kg/year, log scale)')
    ax.set_xscale('log')
    ax.set_ylabel('River Segment')
    ax.set_title('Top 20 Most Affected River Segments', fontsize=14, fontweight='bold')
    ax.legend(title='Category', bbox_to_anchor=(1.05, 1), loc='upper left', fontsize=8)

    # Use river names for labels
    labels = [f"{idx[1][:30]}..." if len(idx[1]) > 30 else idx[1] for idx in pivot.index]
    ax.set_yticklabels(labels)

    plt.tight_layout()
    plt.savefig(output_dir / 'top_affected_rivers.png', dpi=300, bbox_inches='tight')
    plt.close()


def plot_exceedance_analysis(cmix_results: pd.DataFrame, output_dir: Path) -> None:
    """Exceedance frequency and severity by category."""

    exceedances = cmix_results[cmix_results['Exceedance_Flag'] == True]

    if exceedances.empty:
        print("    Warning: No exceedances found for exceedance analysis plot")
        return

    # Aggregate by category
    category_exc = exceedances.groupby('Qualifying_Category').agg({
        'Exceedance_Flag': 'count',
        'Exceedance_Ratio': 'mean'
    }).reset_index()

    category_exc.columns = ['Category', 'Count', 'Mean_Ratio']
    category_exc = category_exc.sort_values('Count', ascending=False)

    fig, ax1 = plt.subplots(figsize=(14, 8))

    # Bar plot for counts
    x = np.arange(len(category_exc))
    bars = ax1.bar(x, category_exc['Count'], color='darkred', alpha=0.7, label='Exceedance Count')
    ax1.set_xlabel('Category', fontsize=12)
    ax1.set_ylabel('Number of Exceedances', fontsize=12, color='darkred')
    ax1.tick_params(axis='y', labelcolor='darkred')
    ax1.set_xticks(x)
    ax1.set_xticklabels(category_exc['Category'], rotation=45, ha='right')

    # Line plot for mean ratio
    ax2 = ax1.twinx()
    line = ax2.plot(x, category_exc['Mean_Ratio'], color='darkorange', marker='o',
                    linewidth=2, markersize=8, label='Mean Exceedance Ratio')
    ax2.set_ylabel('Mean Exceedance Ratio (Cmix/MKK, log scale)', fontsize=12, color='darkorange')
    ax2.tick_params(axis='y', labelcolor='darkorange')
    ax2.set_yscale('log')

    # Title and legend
    ax1.set_title('MKK Exceedance Analysis: Frequency vs Severity', fontsize=14, fontweight='bold')

    # Combine legends
    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2, loc='upper right')

    plt.tight_layout()
    plt.savefig(output_dir / 'exceedance_analysis.png', dpi=300, bbox_inches='tight')
    plt.close()


def plot_gvfk_summary(
    site_flux: pd.DataFrame,
    segment_summary: pd.DataFrame,
    cmix_results: pd.DataFrame,
    output_dir: Path,
) -> None:
    """GVFK-level summary scatter plot."""

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
        s=df['Site_Count'] * 20,  # Size by site count
        c=df['Max_Exceedance_Ratio'],
        cmap='YlOrRd',
        alpha=0.6,
        edgecolors='black',
        linewidth=0.5,
        norm=plt.matplotlib.colors.LogNorm()
    )

    ax.set_xlabel('Number of Affected River Segments', fontsize=12)
    ax.set_ylabel('Total Pollution Flux (kg/year, log scale)', fontsize=12)
    ax.set_yscale('log')
    ax.set_title('GVFK Summary: Impact and Severity', fontsize=14, fontweight='bold')
    ax.grid(True, alpha=0.3)

    # Colorbar
    cbar = plt.colorbar(scatter, ax=ax)
    cbar.set_label('Max Exceedance Ratio', fontsize=10)

    # Add legend for size
    for size in [1, 5, 10, 20]:
        ax.scatter([], [], s=size*20, c='gray', alpha=0.5, edgecolors='black',
                  label=f'{size} sites')
    ax.legend(scatterpoints=1, frameon=True, labelspacing=1, title='Site Count', loc='upper left')

    # Annotate top 5 GVFKs
    top5 = df.nlargest(5, 'Total_Flux_kg')
    for _, row in top5.iterrows():
        ax.annotate(
            row['GVFK'],
            (row['River_Segment_Count'], row['Total_Flux_kg']),
            xytext=(5, 5),
            textcoords='offset points',
            fontsize=8,
            bbox=dict(boxstyle='round,pad=0.3', facecolor='yellow', alpha=0.5)
        )

    plt.tight_layout()
    plt.savefig(output_dir / 'gvfk_summary.png', dpi=300, bbox_inches='tight')
    plt.close()


def plot_flow_scenario_sensitivity(cmix_results: pd.DataFrame, output_dir: Path) -> None:
    """Box plot showing Cmix/MKK ratio distribution by scenario and category."""

    if cmix_results.empty or 'Flow_Scenario' not in cmix_results.columns:
        print("    Warning: No flow scenario data for sensitivity plot")
        return

    # Filter to only exceedances
    exc = cmix_results[cmix_results['Exceedance_Flag'] == True].copy()

    if exc.empty:
        print("    Warning: No exceedances for flow scenario sensitivity plot")
        return

    # Select top 8 categories by exceedance count
    top_cats = exc['Qualifying_Category'].value_counts().head(8).index
    exc_filtered = exc[exc['Qualifying_Category'].isin(top_cats)]

    fig, ax = plt.subplots(figsize=(16, 10))

    # Create box plot
    exc_filtered_sorted = exc_filtered.sort_values('Qualifying_Category')

    sns.boxplot(
        data=exc_filtered_sorted,
        x='Qualifying_Category',
        y='Exceedance_Ratio',
        hue='Flow_Scenario',
        ax=ax,
        palette='Set2'
    )

    ax.set_yscale('log')
    ax.set_xlabel('Category', fontsize=12)
    ax.set_ylabel('Exceedance Ratio (Cmix/MKK, log scale)', fontsize=12)
    ax.set_title('Flow Scenario Sensitivity: Exceedance Ratios by Category', fontsize=14, fontweight='bold')
    ax.legend(title='Flow Scenario', loc='upper right')
    plt.xticks(rotation=45, ha='right')

    plt.tight_layout()
    plt.savefig(output_dir / 'flow_scenario_sensitivity.png', dpi=300, bbox_inches='tight')
    plt.close()


def plot_substance_treemap(segment_flux: pd.DataFrame, output_dir: Path) -> None:
    """Treemap showing category > substance hierarchy by flux."""

    # Use squarify for treemap
    try:
        import squarify
    except ImportError:
        print("    Warning: squarify not installed, skipping treemap. Install with: pip install squarify")
        return

    # Aggregate by category and substance
    substance_flux = segment_flux.groupby(['Qualifying_Category', 'Qualifying_Substance']).agg({
        'Total_Flux_kg_per_year': 'sum'
    }).reset_index()

    # Get top substances per category (top 3)
    top_substances = []
    for cat in substance_flux['Qualifying_Category'].unique():
        cat_data = substance_flux[substance_flux['Qualifying_Category'] == cat]
        top_3 = cat_data.nlargest(3, 'Total_Flux_kg_per_year')
        top_substances.append(top_3)

    df = pd.concat(top_substances)

    # Create labels
    df['Label'] = df.apply(
        lambda x: f"{x['Qualifying_Category']}\n{x['Qualifying_Substance'][:20]}\n{x['Total_Flux_kg_per_year']:.1f} kg/y",
        axis=1
    )

    fig, ax = plt.subplots(figsize=(16, 12))

    # Create treemap
    colors = plt.cm.tab20(np.linspace(0, 1, len(df)))

    squarify.plot(
        sizes=df['Total_Flux_kg_per_year'],
        label=df['Label'],
        color=colors,
        alpha=0.7,
        text_kwargs={'fontsize': 8, 'weight': 'bold'},
        ax=ax
    )

    ax.set_title('Substance Contribution Treemap: Top 3 per Category', fontsize=14, fontweight='bold')
    ax.axis('off')

    plt.tight_layout()
    plt.savefig(output_dir / 'substance_treemap.png', dpi=300, bbox_inches='tight')
    plt.close()


def plot_multi_scenario_breakdown(
    segment_flux: pd.DataFrame,
    cmix_results: pd.DataFrame,
    output_dir: Path,
) -> None:
    """Highlight categories with multiple scenario modelstoffer."""

    flux_df = segment_flux.copy()
    flux_df["Scenario_Modelstof"] = flux_df["Qualifying_Substance"].apply(_extract_scenario_name)
    scenario_counts = (
        flux_df.dropna(subset=["Scenario_Modelstof"])
        .groupby("Qualifying_Category")["Scenario_Modelstof"]
        .nunique()
    )
    multi_categories = scenario_counts[scenario_counts > 1].index.tolist()

    if not multi_categories:
        print("    Warning: No categories with multiple scenarios found for breakdown plot")
        return

    category_order = sorted(multi_categories)
    flux_filtered = flux_df[
        flux_df["Qualifying_Category"].isin(category_order)
        & flux_df["Scenario_Modelstof"].notna()
    ]

    flux_summary = (
        flux_filtered.groupby(["Qualifying_Category", "Scenario_Modelstof"])["Total_Flux_kg_per_year"]
        .sum()
        .reset_index()
    )
    flux_summary["Qualifying_Category"] = pd.Categorical(
        flux_summary["Qualifying_Category"], categories=category_order, ordered=True
    )

    exceedances = cmix_results.copy()
    exceedances["Scenario_Modelstof"] = exceedances["Qualifying_Substance"].apply(
        _extract_scenario_name
    )
    exc_filtered = exceedances[
        (exceedances["Qualifying_Category"].isin(category_order))
        & (exceedances["Scenario_Modelstof"].notna())
        & (exceedances.get("Exceedance_Flag", False) == True)
    ]

    fig = plt.figure(figsize=(18, 12))
    gs = fig.add_gridspec(2, 1, height_ratios=[2.2, 1.0], hspace=0.35)
    ax_flux = fig.add_subplot(gs[0])
    ax_heat = fig.add_subplot(gs[1])

    sns.barplot(
        data=flux_summary,
        x="Qualifying_Category",
        y="Total_Flux_kg_per_year",
        hue="Scenario_Modelstof",
        ax=ax_flux,
    )
    ax_flux.set_yscale("log")
    ax_flux.set_xlabel("Category", fontsize=12)
    ax_flux.set_ylabel("Total Flux (kg/year, log scale)", fontsize=12)
    ax_flux.set_title("Scenario Contribution per Category (Flux)", fontsize=14, fontweight="bold")
    ax_flux.legend(title="Scenario / Modelstof", bbox_to_anchor=(1.02, 1), loc="upper left")
    plt.setp(ax_flux.get_xticklabels(), rotation=30, ha="right")

    if not exc_filtered.empty:
        heatmap_data = (
            exc_filtered.groupby(["Scenario_Modelstof", "Qualifying_Category"])["Exceedance_Ratio"]
            .max()
            .unstack()
            .reindex(columns=category_order)
        )
        mask = heatmap_data.isna()
        sns.heatmap(
            heatmap_data,
            ax=ax_heat,
            cmap="Reds",
            annot=True,
            fmt=".2f",
            cbar_kws={"label": "Max exceedance ratio"},
            mask=mask,
        )
        ax_heat.set_title("Scenario Exceedance Severity (max Cmix/MKK)", fontsize=14, fontweight="bold")
        ax_heat.set_xlabel("Category")
        ax_heat.set_ylabel("Scenario / Modelstof")
    else:
        ax_heat.axis("off")
        ax_heat.text(
            0.5,
            0.5,
            "No MKK exceedances were observed for multi-scenario categories.",
            ha="center",
            va="center",
            fontsize=12,
            fontweight="bold",
        )

    plt.tight_layout()
    plt.savefig(output_dir / "category_scenario_breakdown.png", dpi=300, bbox_inches="tight")
    plt.close()


def _extract_scenario_name(substance: str) -> str | None:
    """Return the scenario/modelstof part from 'Category__via_Modelstof' labels."""
    if not isinstance(substance, str):
        return None
    marker = "__via_"
    if marker in substance:
        return substance.split(marker, 1)[1]
    return None
