"""
Workflow Summary Visualizations
===============================

Creates progression plots showing how GVFKs and sites are filtered through all
workflow stages (Steps 1-6). These visualizations span the entire workflow
and provide a high-level summary of the assessment funnel.

Plots generated:
- gvfk_progression.png: GVFK counts from Step 1 → Step 6
- sites_progression.png: Site counts from Step 3 → Step 6

Output directory: Resultater/workflow_summary/
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os
from pathlib import Path

# Reset any previously applied styles and apply professional settings
plt.style.use('default')
plt.rcParams.update({
    'font.family': ['Arial', 'DejaVu Sans', 'sans-serif'],
    'font.size': 14,           # Bigger base font for PowerPoint
    'axes.titlesize': 18,      # Bigger titles
    'axes.labelsize': 16,      # Bigger axis labels
    'xtick.labelsize': 12,     # Readable tick labels
    'ytick.labelsize': 12,
    'figure.dpi': 100,
    'savefig.dpi': 300,
    'savefig.bbox': 'tight',
    'savefig.facecolor': 'white',
    'figure.facecolor': 'white',
    'axes.facecolor': 'white',
    'axes.grid': False,        # No grid by default
})


def create_workflow_summary_plots():
    """
    Create workflow-level summary visualizations.
    Called from main_workflow.py after all steps complete.
    """
    from config import (
        WORKFLOW_SUMMARY_DIR, GRUNDVAND_PATH, GRUNDVAND_LAYER_NAME,
        COLUMN_MAPPINGS, get_output_path
    )
    import geopandas as gpd

    print("\n" + "="*60)
    print("WORKFLOW SUMMARY VISUALIZATIONS")
    print("="*60)

    WORKFLOW_SUMMARY_DIR.mkdir(parents=True, exist_ok=True)
    figures_path = str(WORKFLOW_SUMMARY_DIR)

    # Create GVFK progression plot
    try:
        create_gvfk_progression_plot(figures_path)
        print("  ✓ GVFK progression plot created")
    except Exception as e:
        print(f"  ⚠ Error creating GVFK progression: {e}")

    # Create sites progression plot
    try:
        create_sites_progression_plot(figures_path)
        print("  ✓ Sites progression plot created")
    except Exception as e:
        print(f"  ⚠ Error creating sites progression: {e}")

    # Create GVFK area/volume progression plot
    try:
        create_gvfk_area_volume_plot(figures_path)
        print("  ✓ GVFK area/volume progression plot created")
    except Exception as e:
        print(f"  ⚠ Error creating area/volume progression: {e}")

    print(f"\nWorkflow summary plots saved to: {figures_path}")


def create_gvfk_progression_plot(figures_path):
    """
    Create GVFK progression plot showing filtering through all workflow steps.
    
    Shows the funnel from all GVFKs in Denmark down to those with MKK exceedances.
    """
    from config import (
        GRUNDVAND_PATH, GRUNDVAND_LAYER_NAME, COLUMN_MAPPINGS, get_output_path
    )
    import geopandas as gpd

    gvfk_col = COLUMN_MAPPINGS['grundvand']['gvfk_id']

    # Step 1: All GVFKs in Denmark
    try:
        all_gvfk_df = gpd.read_file(GRUNDVAND_PATH, layer=GRUNDVAND_LAYER_NAME)
        total_gvfks = all_gvfk_df[gvfk_col].nunique()
    except Exception as e:
        print(f"    Warning: Could not load total GVFKs: {e}")
        total_gvfks = 0

    # Step 2: GVFKs with river contact
    river_gvfks = 0
    river_path = get_output_path("step2_river_gvfk")
    if river_path.exists():
        try:
            river_df = gpd.read_file(river_path)
            river_gvfks = river_df[gvfk_col].nunique()
        except:
            pass

    # Step 3: GVFKs with V1/V2 sites
    v1v2_gvfks = 0
    v1v2_path = get_output_path("step3_gvfk_polygons")
    if v1v2_path.exists():
        try:
            v1v2_df = gpd.read_file(v1v2_path)
            v1v2_gvfks = v1v2_df[gvfk_col].nunique()
        except:
            pass

    # Step 3b: After infiltration filter (EARLY filtering of upward flow sites)
    step3b_gvfks = 0
    step3b_path = get_output_path("step3b_filtered_sites")
    if step3b_path.exists():
        try:
            step3b_df = gpd.read_file(step3b_path)
            gvfk_col_3b = "Navn"  # GVFK column in shapefile
            step3b_gvfks = step3b_df[gvfk_col_3b].nunique()
        except:
            pass

    # Step 5a: General risk (≤500m) - use CSV instead of shapefile
    step5a_gvfks = 0
    step5a_path = get_output_path("step5_high_risk_sites")
    if step5a_path.exists():
        try:
            step5a_df = pd.read_csv(step5a_path)
            step5a_gvfks = step5a_df["GVFK"].nunique()
        except:
            pass

    # Step 5b: Compound-specific risk (final output - Step 5c is now obsolete)
    step5b_gvfks = 0
    step5b_path = get_output_path("step5b_compound_combinations")
    if step5b_path.exists():
        try:
            step5b_df = pd.read_csv(step5b_path)
            step5b_gvfks = step5b_df["GVFK"].nunique()
        except:
            pass

    # NOTE: Step 6 (MKK exceedances) is NOT included here - this plot is for
    # risikovurdering (risk assessment) only. Tilstandsvurdering (Step 6) has
    # its own separate analysis with MKK scenario sensitivity.

    # Build data - Risikovurdering progression
    stages = [
        "Alle GVFK\n(Danmark)",
        "Vandløbskontakt",
        "V1/V2 lokaliteter",
        "Infiltrationsfilter",
        "Generel risiko\n(≤500m)",
        "Stofspecifik risiko",
    ]
    counts = [total_gvfks, river_gvfks, v1v2_gvfks, step3b_gvfks, step5a_gvfks, step5b_gvfks]
    
    # Professional color gradient (blue to orange - now includes green for 3b)
    colors = ["#4A90D9", "#5BA3E0", "#78B7E8", "#66BB6A", "#F5A623", "#E57C23"]

    # Create figure
    fig, ax = plt.subplots(figsize=(14, 8))

    bars = ax.bar(range(len(stages)), counts, color=colors, edgecolor="white", linewidth=2)

    # Add count labels on top of bars
    for bar, count in zip(bars, counts):
        height = bar.get_height()
        if height > 0:
            ax.text(bar.get_x() + bar.get_width() / 2.0, height * 1.02,
                   f"{count:,}", ha="center", va="bottom", fontsize=16, fontweight="bold")

    # Add percentage labels inside bars (relative to Step 1)
    if total_gvfks > 0:
        for bar, count in zip(bars, counts):
            height = bar.get_height()
            if height > 0 and height < counts[0]:  # Don't show 100% for first bar
                pct = count / total_gvfks * 100
                ax.text(bar.get_x() + bar.get_width() / 2.0, height * 0.5,
                       f"({pct:.1f}%)", ha="center", va="center", fontsize=14,
                       color="white", fontweight="bold")

    ax.set_xticks(range(len(stages)))
    ax.set_xticklabels(stages, fontsize=14, fontweight="bold")
    ax.set_ylabel("Antal GVFK", fontsize=18, fontweight="bold")
    # ax.set_title("GVFK Progression Through Workflow", fontsize=20, fontweight="bold", pad=20)

    # Set y-axis to start at 0
    ax.set_ylim(bottom=0)

    plt.tight_layout()
    plt.savefig(os.path.join(figures_path, "gvfk_progression.png"), facecolor="white")
    plt.close()


def create_sites_progression_plot(figures_path):
    """
    Create sites progression plot showing filtering through workflow steps.
    
    Shows the funnel from V1/V2 sites through risk assessment to MKK exceedances.
    """
    from config import get_output_path, COLUMN_MAPPINGS
    import geopandas as gpd

    sites_counts = []
    stages = []

    # Step 3: V1/V2 sites (from shapefile)
    step3_path = get_output_path("step3_v1v2_sites")
    if step3_path.exists():
        try:
            step3_df = gpd.read_file(step3_path)
            site_id_col = COLUMN_MAPPINGS['contamination_shp']['site_id']
            if site_id_col in step3_df.columns:
                step3_sites = step3_df[site_id_col].nunique()
            elif "Lokalitetsnr" in step3_df.columns:
                step3_sites = step3_df["Lokalitetsnr"].nunique()
            else:
                step3_sites = len(step3_df)
            sites_counts.append(step3_sites)
            stages.append("V1/V2 lokaliteter\n(Trin 3)")
        except Exception as e:
            print(f"    Warning: Could not load Step 3 sites: {e}")

    # Step 3b: After infiltration filter
    step3b_path = get_output_path("step3b_filtered_sites")
    if step3b_path.exists():
        try:
            step3b_df = gpd.read_file(step3b_path)
            site_id_col_3b = "Lokalitet_"  # Site ID column in shapefile
            step3b_sites = step3b_df[site_id_col_3b].nunique()
            sites_counts.append(step3b_sites)
            stages.append("Infiltrationsfilter\n(Trin 3b)")
        except:
            pass

    # Step 5a: High-risk sites (general)
    step5a_path = get_output_path("step5_high_risk_sites")
    if step5a_path.exists():
        try:
            step5a_df = pd.read_csv(step5a_path)
            step5a_sites = step5a_df["Lokalitet_ID"].nunique()
            sites_counts.append(step5a_sites)
            stages.append("Generel risiko\n(Trin 5a: ≤500m)")
        except:
            pass

    # Step 5b: Compound-specific sites (final output)
    step5b_path = get_output_path("step5b_compound_combinations")
    if step5b_path.exists():
        try:
            step5b_df = pd.read_csv(step5b_path)
            step5b_sites = step5b_df["Lokalitet_ID"].nunique()
            sites_counts.append(step5b_sites)
            stages.append("Stofspecifik risiko\n(Trin 5b)")
        except:
            pass

    # NOTE: Step 6 (MKK exceedances) is NOT included here - this plot is for
    # risikovurdering (risk assessment) only.

    if len(sites_counts) < 2:
        print("    Insufficient data for sites progression plot")
        return

    # Professional color gradient (5 stages: Step 3, 3b, 5a, 5b)
    colors = ["#4A90D9", "#66BB6A", "#F5A623", "#E57C23"][:len(stages)]

    # Create figure
    fig, ax = plt.subplots(figsize=(12, 8))
    bars = ax.bar(range(len(stages)), sites_counts, color=colors, edgecolor="white", linewidth=2)

    # Add labels inside bars
    for bar, count in zip(bars, sites_counts):
        height = bar.get_height()
        percentage = (count / sites_counts[0]) * 100 if sites_counts[0] > 0 else 0

        # Count on top
        ax.text(bar.get_x() + bar.get_width() / 2.0, height * 1.02,
               f"{count:,}", ha="center", va="bottom", fontsize=14, fontweight="bold")

        # Percentage inside bar (skip first one which is 100%)
        if height < sites_counts[0] and height > 0:
            ax.text(bar.get_x() + bar.get_width() / 2.0, height * 0.5,
                   f"({percentage:.1f}%)", ha="center", va="center", fontsize=12,
                   fontweight="bold", color="white")

    ax.set_xticks(range(len(stages)))
    ax.set_xticklabels(stages, fontsize=12, fontweight="bold")
    ax.set_ylabel("Antal lokaliteter", fontsize=16, fontweight="bold")
    # ax.set_title("Sites Progression Through Workflow", fontsize=20, fontweight="bold", pad=20)

    # Set y-axis to start at 0
    ax.set_ylim(bottom=0)

    plt.tight_layout()
    plt.savefig(os.path.join(figures_path, "sites_progression.png"), facecolor="white")
    plt.close()


def create_gvfk_area_volume_plot(figures_path):
    """
    Create GVFK area and volume progression plot.
    
    Shows how the total area (km²) and volume (km³) of groundwater bodies
    changes as the workflow filters down to critical exceedances.
    """
    from config import (
        GRUNDVAND_GDB_PATH, GRUNDVAND_LAYER_NAME, COLUMN_MAPPINGS, get_output_path
    )
    import geopandas as gpd

    gvfk_col = COLUMN_MAPPINGS['grundvand']['gvfk_id']

    # Load base GVFK layer with area and thickness
    try:
        all_gvfk_df = gpd.read_file(GRUNDVAND_GDB_PATH, layer=GRUNDVAND_LAYER_NAME)
        # Create lookup dictionaries for area and volume by GVFK ID
        all_gvfk_df['Volume_m3'] = all_gvfk_df['Area_mag'] * all_gvfk_df['Tyk_mag'].fillna(0)
        area_lookup = dict(zip(all_gvfk_df[gvfk_col], all_gvfk_df['Area_mag']))
        volume_lookup = dict(zip(all_gvfk_df[gvfk_col], all_gvfk_df['Volume_m3']))
        
        total_area_km2 = all_gvfk_df['Area_mag'].sum() / 1e6
        total_volume_km3 = all_gvfk_df['Volume_m3'].sum() / 1e9
    except Exception as e:
        print(f"    Warning: Could not load GVFK area/volume data: {e}")
        return

    def calc_area_volume(gvfk_ids):
        """Calculate total area (km²) and volume (km³) for a set of GVFK IDs."""
        area = sum(area_lookup.get(gid, 0) for gid in gvfk_ids) / 1e6
        volume = sum(volume_lookup.get(gid, 0) for gid in gvfk_ids) / 1e9
        return area, volume

    # Collect area/volume at each stage
    stages = []
    areas = []
    volumes = []

    # Step 1: All GVFKs
    stages.append("Alle GVFK\n(Danmark)")
    areas.append(total_area_km2)
    volumes.append(total_volume_km3)

    # Step 2: River contact
    river_path = get_output_path("step2_river_gvfk")
    if river_path.exists():
        try:
            river_df = gpd.read_file(river_path)
            gvfk_ids = river_df[gvfk_col].unique()
            area, volume = calc_area_volume(gvfk_ids)
            stages.append("Vandløbskontakt\n(Trin 2)")
            areas.append(area)
            volumes.append(volume)
        except:
            pass

    # Step 3: V1/V2 sites
    v1v2_path = get_output_path("step3_gvfk_polygons")
    if v1v2_path.exists():
        try:
            v1v2_df = gpd.read_file(v1v2_path)
            gvfk_ids = v1v2_df[gvfk_col].unique()
            area, volume = calc_area_volume(gvfk_ids)
            stages.append("V1/V2 lokaliteter\n(Trin 3)")
            areas.append(area)
            volumes.append(volume)
        except:
            pass

    # Step 5b: Compound-specific risk
    step5b_path = get_output_path("step5b_compound_combinations")
    if step5b_path.exists():
        try:
            step5b_df = pd.read_csv(step5b_path)
            gvfk_ids = step5b_df["GVFK"].unique()
            area, volume = calc_area_volume(gvfk_ids)
            stages.append("Stofspecifik risiko\n(Trin 5b)")
            areas.append(area)
            volumes.append(volume)
        except:
            pass

    # Step 5c: After infiltration filter
    step5c_path = get_output_path("step5c_filtered_combinations")
    if step5c_path.exists():
        try:
            step5c_df = pd.read_csv(step5c_path)
            gvfk_ids = step5c_df["GVFK"].unique()
            area, volume = calc_area_volume(gvfk_ids)
            stages.append("Infiltrationsfilter\n(Trin 5c)")
            areas.append(area)
            volumes.append(volume)
        except:
            pass

    # Step 6: MKK exceedances
    step6_path = get_output_path("step6_site_mkk_exceedances")
    if step6_path.exists():
        try:
            step6_df = pd.read_csv(step6_path)
            gvfk_ids = step6_df["GVFK"].unique()
            area, volume = calc_area_volume(gvfk_ids)
            stages.append("MKK overskridelser\n(Trin 6)")
            areas.append(area)
            volumes.append(volume)
        except:
            pass

    if len(stages) < 2:
        print("    Insufficient data for area/volume plot")
        return

    # Create dual-axis figure
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 8))

    # Color gradient (blue to red)
    colors = ["#4A90D9", "#5BA3E0", "#78B7E8", "#E57C23", "#D14545", "#A82828"][:len(stages)]

    # Left: Area progression
    bars1 = ax1.bar(range(len(stages)), areas, color=colors, edgecolor="white", linewidth=2)
    
    for bar, area in zip(bars1, areas):
        height = bar.get_height()
        if height > 0:
            ax1.text(bar.get_x() + bar.get_width() / 2.0, height * 1.02,
                    f"{area:,.0f}", ha="center", va="bottom", fontsize=12, fontweight="bold")
            # Percentage inside bar
            if area < areas[0]:
                pct = area / areas[0] * 100
                ax1.text(bar.get_x() + bar.get_width() / 2.0, height * 0.5,
                        f"({pct:.1f}%)", ha="center", va="center", fontsize=11,
                        color="white", fontweight="bold")

    ax1.set_xticks(range(len(stages)))
    ax1.set_xticklabels(stages, fontsize=10, fontweight="bold")
    ax1.set_ylabel("Areal (km²)", fontsize=14, fontweight="bold")
    # ax1.set_title("GVFK Areal gennem Workflow", fontsize=16, fontweight="bold", pad=15)
    ax1.set_ylim(bottom=0)

    # Right: Volume progression
    bars2 = ax2.bar(range(len(stages)), volumes, color=colors, edgecolor="white", linewidth=2)
    
    for bar, vol in zip(bars2, volumes):
        height = bar.get_height()
        if height > 0:
            ax2.text(bar.get_x() + bar.get_width() / 2.0, height * 1.02,
                    f"{vol:,.1f}", ha="center", va="bottom", fontsize=12, fontweight="bold")
            # Percentage inside bar
            if vol < volumes[0]:
                pct = vol / volumes[0] * 100
                ax2.text(bar.get_x() + bar.get_width() / 2.0, height * 0.5,
                        f"({pct:.1f}%)", ha="center", va="center", fontsize=11,
                        color="white", fontweight="bold")

    ax2.set_xticks(range(len(stages)))
    ax2.set_xticklabels(stages, fontsize=10, fontweight="bold")
    ax2.set_ylabel("Volumen (km³)", fontsize=14, fontweight="bold")
    # ax2.set_title("GVFK Volumen gennem Workflow", fontsize=16, fontweight="bold", pad=15)
    ax2.set_ylim(bottom=0)

    # Add summary text at bottom
    if len(areas) > 1 and len(volumes) > 1:
        final_area_pct = areas[-1] / areas[0] * 100 if areas[0] > 0 else 0
        final_vol_pct = volumes[-1] / volumes[0] * 100 if volumes[0] > 0 else 0
        summary = (
            f"Samlet: {areas[0]:,.0f} km² → {areas[-1]:,.0f} km² ({final_area_pct:.1f}%)  |  "
            f"{volumes[0]:,.1f} km³ → {volumes[-1]:,.1f} km³ ({final_vol_pct:.1f}%)"
        )
        fig.text(0.5, 0.02, summary, ha='center', fontsize=13, fontweight='bold',
                bbox=dict(boxstyle='round', facecolor='lightyellow', edgecolor='orange', alpha=0.9))

    plt.tight_layout(rect=[0, 0.06, 1, 1])
    plt.savefig(os.path.join(figures_path, "gvfk_area_volume_progression.png"), facecolor="white")
    plt.close()


if __name__ == "__main__":
    create_workflow_summary_plots()
