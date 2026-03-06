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

    # Create regional summary table (Risikovurdering)
    try:
        df_regional = create_regional_summary_tables(figures_path)
        print("  ✓ Regional summary table created")
        
        # Create regional line plots
        try:
            create_regional_line_plots(df_regional, figures_path)
            print("  ✓ Regional line plots created")
        except Exception as e:
            print(f"  ⚠ Error creating regional line plots: {e}")
            import traceback
            traceback.print_exc()
            
    except Exception as e:
        print(f"  ⚠ Error creating regional summary table: {e}")
        import traceback
        traceback.print_exc()

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



def create_regional_summary_tables(output_dir):
    """
    Create regional summary tables for Risikovurdering AND Tilstandsvurdering.
    
    Format:
    - Columns: Regions + Total
    - Rows: Metrics grouped by Step (Gradual filtering)
    
    Generates 'regional_summary_transposed.xlsx'
    """
    print("\n  Generating Regional Summary Table (Transposed)...")
    from config import (
        DATA_DIR, GRUNDVAND_PATH, GRUNDVAND_LAYER_NAME, COLUMN_MAPPINGS, get_output_path
    )
    import geopandas as gpd
    import pandas as pd
    from pathlib import Path
    
    output_dir = Path(output_dir)

    # 1. Load Region Data
    regions_path = DATA_DIR / "regionsinddeling" / "regionsinddeling.shp"
    if not regions_path.exists():
        print(f"    ⚠ Region shapefile not found at {regions_path}")
        return

    try:
        regions_gdf = gpd.read_file(regions_path)
        # Identify region name column
        region_col = None
        candidates = ["Regionsnavn", "regionsnavn", "REGIONNAVN", "Navn", "navn", "Name", "name"]
        for col in regions_gdf.columns:
            if col in candidates:
                region_col = col
                break
        
        if not region_col:
            # Fallback: use first string column
            for col in regions_gdf.columns:
                if regions_gdf[col].dtype == 'object':
                    region_col = col
                    print(f"    ⚠ Could not identify region name column. Using '{col}'")
                    break
        
        if not region_col:
            print("    ⚠ No suitable region name column found.")
            return
            
        print(f"    Using region column: {region_col}")
        regions_gdf = regions_gdf.rename(columns={region_col: "Region"})
        # Simplify to just region name and geometry
        regions_gdf = regions_gdf[['Region', 'geometry']].copy()
        
    except Exception as e:
        print(f"    ⚠ Error loading regions: {e}")
        return

    # 2. Load GVFK Data
    try:
        gvfk_gdf = gpd.read_file(GRUNDVAND_PATH, layer=GRUNDVAND_LAYER_NAME)
        gvfk_col = COLUMN_MAPPINGS['grundvand']['gvfk_id']
        
        # Ensure Area/Volume columns exist
        if 'Area_mag' not in gvfk_gdf.columns:
            gvfk_gdf['Area_mag'] = gvfk_gdf.geometry.area
        
        # Calculate Volume_m3 if missing (Area * Thickness)
        if 'Tyk_mag' in gvfk_gdf.columns:
            gvfk_gdf['Volume_m3'] = gvfk_gdf['Area_mag'] * gvfk_gdf['Tyk_mag'].fillna(0)
        else:
            gvfk_gdf['Volume_m3'] = 0
            
    except Exception as e:
        print(f"    ⚠ Error loading GVFK data: {e}")
        return

    # 3. Pre-compute GVFK -> Region Mapping (50% rule) & Exact Intersections
    print("    Pre-computing spatial intersections (this may take a moment)...")
    
    # Prepare for overlay
    # Keep only necessary columns to speed up overlay
    gvfk_simple = gvfk_gdf[[gvfk_col, 'geometry', 'Volume_m3']].copy()
    gvfk_simple['original_area'] = gvfk_simple.geometry.area
    
    # Calculate Intersections
    # intersection_gdf contains the parts of GVFKs that fall inside Regions
    # Ensure CRS match
    if gvfk_simple.crs != regions_gdf.crs:
        regions_gdf = regions_gdf.to_crs(gvfk_simple.crs)
        
    intersection_gdf = gpd.overlay(gvfk_simple, regions_gdf, how='intersection')
    
    # Calculate new area of intersection parts
    intersection_gdf['intersect_area'] = intersection_gdf.geometry.area
    
    # Calculate volume of intersection parts (proportional to area)
    # Volume_part = Volume_total * (Area_part / Area_original)
    # Handle division by zero if original area is 0 (shouldn't happen for valid polygons)
    intersection_gdf['intersect_volume'] = intersection_gdf.apply(
        lambda row: row['Volume_m3'] * (row['intersect_area'] / row['original_area']) 
        if row['original_area'] > 0 else 0, axis=1
    )
    
    # Determining Primary Region for each GVFK (>50% rule)
    # Group by GVFK and Region to get total overlap per region pair
    overlap_stats = intersection_gdf.groupby([gvfk_col, 'Region'])['intersect_area'].sum().reset_index()
    
    # Get total original area for each GVFK to calculate fraction
    gvfk_areas = gvfk_simple.set_index(gvfk_col)['original_area'].to_dict()
    overlap_stats['fraction'] = overlap_stats.apply(lambda x: x['intersect_area'] / gvfk_areas.get(x[gvfk_col], 1), axis=1)
    
    # Find Primary Region
    # Filter for > 0.5
    primary_regions = overlap_stats[overlap_stats['fraction'] > 0.5].copy()
    
    # Handle cases where no region has > 0.5 (max overlap)
    assigned_ids = set(primary_regions[gvfk_col])
    all_ids = set(gvfk_simple[gvfk_col])
    unassigned = all_ids - assigned_ids
    
    gvfk_to_region = dict(zip(primary_regions[gvfk_col], primary_regions['Region']))
    
    if unassigned:
        # Find max overlap for remaining
        remaining_stats = overlap_stats[overlap_stats[gvfk_col].isin(unassigned)]
        if not remaining_stats.empty:
            # Sort by fraction desc and drop duplicates to keep max
            max_overlap = remaining_stats.sort_values('fraction', ascending=False).drop_duplicates(gvfk_col)
            for _, row in max_overlap.iterrows():
                gvfk_to_region[row[gvfk_col]] = row['Region']
    
    print(f"    Mapped {len(gvfk_to_region)} GVFKs to regions.")

    # 4. Define Steps for Analysis
    steps_data = []
    
    # Step 1: All GVFKs
    steps_data.append({
        "name": "Trin 1 (Alle)",         # Short name for column header
        "gvfk_ids": set(gvfk_gdf[gvfk_col]),
        "sites_gdf": None # No sites in step 1
    })
    
    # Step 2: River Contact
    river_path = get_output_path("step2_river_gvfk")
    if river_path.exists():
        river_df = gpd.read_file(river_path)
        steps_data.append({
            "name": "Trin 2 (Kontakt)",
            "gvfk_ids": set(river_df[gvfk_col]),
            "sites_gdf": None
        })
        
    # Step 3: V1/V2 Sites
    v1v2_polygons_path = get_output_path("step3_gvfk_polygons")
    v1v2_sites_path = get_output_path("step3_v1v2_sites")
    
    # Load base site geometry if available (needed for Step 3 and 5b)
    base_sites_gdf = None
    if v1v2_sites_path.exists():
        base_sites_gdf = gpd.read_file(v1v2_sites_path)
        # Ensure consistent CRS
        if base_sites_gdf.crs != regions_gdf.crs:
            base_sites_gdf = base_sites_gdf.to_crs(regions_gdf.crs)

    if v1v2_polygons_path.exists():
        v1v2_poly_df = gpd.read_file(v1v2_polygons_path)
        steps_data.append({
            "name": "Trin 3 (V1/V2)",
            "gvfk_ids": set(v1v2_poly_df[gvfk_col]),
            "sites_gdf": base_sites_gdf
        })

    # Step 3b: Infiltration Filter
    step3b_path = get_output_path("step3b_filtered_sites")
    if step3b_path.exists():
        step3b_df = gpd.read_file(step3b_path)
        # 3b shapefile has 'Navn' for GVFK and 'Lokalitet_' for site ID
        step3b_gvfks = set(step3b_df['Navn']) if 'Navn' in step3b_df.columns else set()
        
        sites_geom3b = None
        if base_sites_gdf is not None:
             # Identify ID columns
            possible_id_cols = ['Lokalitet_', 'Lokalitetsnr', 'site_id']
            site_id_col = next((c for c in possible_id_cols if c in base_sites_gdf.columns), None)
            
            # In step3b shapefile, site ID is usually 'Lokalitet_'
            s3b_id_col = next((c for c in ['Lokalitet_', 'Lokalitetsnr'] if c in step3b_df.columns), None)
            
            if site_id_col and s3b_id_col:
                step3b_ids = step3b_df[s3b_id_col].unique()
                
                # Verify IDs match format
                if 'temp_id_match' not in base_sites_gdf.columns:
                     base_sites_gdf['temp_id_match'] = base_sites_gdf[site_id_col].astype(str)
                
                step3b_ids_str = [str(i) for i in step3b_ids]
                sites_geom3b = base_sites_gdf[base_sites_gdf['temp_id_match'].isin(step3b_ids_str)].copy()
        
        steps_data.append({
            "name": "Trin 3b (Infilter)",
            "gvfk_ids": step3b_gvfks,
            "sites_gdf": sites_geom3b
        })

    # Step 5a: General Risk (<=500m)
    step5a_path = get_output_path("step5_high_risk_sites")
    if step5a_path.exists():
        step5a_df = pd.read_csv(step5a_path)
        
        sites_geom5a = None
        if base_sites_gdf is not None:
            # Re-use ID matching
            possible_id_cols = ['Lokalitet_', 'Lokalitetsnr', 'site_id']
            site_id_col = next((c for c in possible_id_cols if c in base_sites_gdf.columns), None)
            
            if site_id_col:
                step5a_ids = step5a_df['Lokalitet_ID'].unique()
                if 'temp_id_match' not in base_sites_gdf.columns:
                     base_sites_gdf['temp_id_match'] = base_sites_gdf[site_id_col].astype(str)
                
                step5a_ids_str = [str(i) for i in step5a_ids]
                sites_geom5a = base_sites_gdf[base_sites_gdf['temp_id_match'].isin(step5a_ids_str)].copy()
        
        steps_data.append({
            "name": "Trin 5a (Gen. Risiko)",
            "gvfk_ids": set(step5a_df["GVFK"]),
            "sites_gdf": sites_geom5a
        })
        
    # Step 5b: Compound Risk
    step5b_path = get_output_path("step5b_compound_combinations")
    if step5b_path.exists():
        step5b_df = pd.read_csv(step5b_path)
        # Sites need to be spatial 
        sites_geom = None
        if base_sites_gdf is not None:
             # Identify ID columns
            possible_id_cols = ['Lokalitet_', 'Lokalitetsnr', 'site_id']
            site_id_col = next((c for c in possible_id_cols if c in base_sites_gdf.columns), None)
            
            if site_id_col:
                # Filter base sites to those in Step 5b
                step5_ids = step5b_df['Lokalitet_ID'].unique() # Assuming 'Lokalitet_ID' is in CSV
                
                # Normalize to string for safe comparison
                if 'temp_id_match' not in base_sites_gdf.columns:
                     base_sites_gdf['temp_id_match'] = base_sites_gdf[site_id_col].astype(str)
                step5_ids_str = [str(i) for i in step5_ids]
                
                sites_geom = base_sites_gdf[base_sites_gdf['temp_id_match'].isin(step5_ids_str)].copy()
            
        steps_data.append({
            "name": "Trin 5b (Stof. Risiko)",
            "gvfk_ids": set(step5b_df["GVFK"]),
            "sites_gdf": sites_geom
        })

    # Step 6: Tilstandsvurdering (MKK Exceedances)
    step6_path = get_output_path("step6_site_mkk_exceedances")
    if step6_path.exists():
        step6_df = pd.read_csv(step6_path)
        sites_geom6 = None
        if base_sites_gdf is not None:
            # Link via Site ID
            possible_id_cols = ['Lokalitet_', 'Lokalitetsnr', 'site_id']
            site_id_col = next((c for c in possible_id_cols if c in base_sites_gdf.columns), None)
            
            if site_id_col:
                 step6_ids = step6_df['Lokalitet_ID'].unique()
                 # Reuse temp_id_match if created above, else create
                 if 'temp_id_match' not in base_sites_gdf.columns:
                     base_sites_gdf['temp_id_match'] = base_sites_gdf[site_id_col].astype(str)
                 
                 step6_ids_str = [str(i) for i in step6_ids]
                 sites_geom6 = base_sites_gdf[base_sites_gdf['temp_id_match'].isin(step6_ids_str)].copy()
                 
        steps_data.append({
            "name": "Trin 6 (Tilstand)",
            "gvfk_ids": set(step6_df["GVFK"]),
            "sites_gdf": sites_geom6
        })

    # 5. Calculate Statistics per Region
    results = [] # List of dicts
    unique_regions = sorted(regions_gdf['Region'].unique())
    
    for step in steps_data:
        step_name = step['name']
        valid_gvfks = step['gvfk_ids']
        current_sites_gdf = step['sites_gdf']
        
        # A. GVFK Counts (Assigned Region)
        step_gvfk_regions = [gvfk_to_region.get(gid) for gid in valid_gvfks if gid in gvfk_to_region]
        gvfk_counts = pd.Series(step_gvfk_regions).value_counts()
        
        # B. Area & Volume (Exact Intersection)
        step_intersections = intersection_gdf[intersection_gdf[gvfk_col].isin(valid_gvfks)]
        area_sums = step_intersections.groupby('Region')['intersect_area'].sum() / 1e6 # km2
        vol_sums = step_intersections.groupby('Region')['intersect_volume'].sum() / 1e9 # km3
        
        # C. Site Counts
        site_counts = pd.Series(0, index=unique_regions)
        if current_sites_gdf is not None and not current_sites_gdf.empty:
            sites_in_regions = gpd.sjoin(current_sites_gdf, regions_gdf, how='inner', predicate='intersects')
            
            # Count UNIQUE sites per region (avoid double counting combinations/geometries)
            # Use 'temp_id_match' if available (standardized ID), else fallback to index/row count
            if 'temp_id_match' in sites_in_regions.columns:
                site_counts = sites_in_regions.groupby('Region')['temp_id_match'].nunique()
            else:
                # Attempt to find ID col
                possible_id_cols = ['Lokalitet_', 'Lokalitetsnr', 'site_id']
                id_col = next((c for c in possible_id_cols if c in sites_in_regions.columns), None)
                if id_col:
                    site_counts = sites_in_regions.groupby('Region')[id_col].nunique()
                else:
                    # Fallback to row count if no ID found (shouldn't happen for V1/V2/Risk steps)
                    site_counts = sites_in_regions['Region'].value_counts()
            
        # Assemble Row per Region
        for region in unique_regions:
            row = {
                "Step": step_name,
                "Region": region,
                "GVFK": gvfk_counts.get(region, 0),
                "Sites": site_counts.get(region, 0) if current_sites_gdf is not None else 0,
                "Areal (km2)": area_sums.get(region, 0.0),
                "Volumen (km3)": vol_sums.get(region, 0.0)
            }
            results.append(row)
            
    # 6. Create Formatted Table (Transposed)
    if not results:
        print("    ⚠ No results generated.")
        return

    df_results = pd.DataFrame(results)
    
    # Pivot: Index=Step, Columns=Region, Values=Metrics
    # But we want to group by Metric as primary index row
    
    pivot_df = df_results.pivot(index='Step', columns='Region', values=['GVFK', 'Sites', 'Areal (km2)', 'Volumen (km3)'])
    
    # pivot_df columns are now MultiIndex (Metric, Region)
    # We want Index to be (Metric, Step) and Columns to be (Region)
    
    # 1. Stack Metric level to index
    stack_df = pivot_df.stack(level=0) 
    # Index is now (Step, Metric), Columns are Regions
    
    # 2. Swap index levels to (Metric, Step)
    stack_df.index = stack_df.index.swaplevel(0, 1)
    stack_df.sort_index(level=0, inplace=True)
    
    # Add Total Column
    stack_df['Total'] = stack_df.sum(axis=1)
    
    # Correct Total GVFK counts
    for step in steps_data:
        step_name = step['name']
        true_total = len(step['gvfk_ids'])
        if ('GVFK', step_name) in stack_df.index:
            stack_df.loc[('GVFK', step_name), 'Total'] = true_total

    # Reorder Index Logic
    metric_order = ['GVFK', 'Sites', 'Areal (km2)', 'Volumen (km3)']
    step_order_names = [s['name'] for s in steps_data]
    
    # Create explicit index for sorting
    new_index = pd.MultiIndex.from_product([metric_order, step_order_names], names=['Metric', 'Step'])
    final_df = stack_df.reindex(new_index)
    
    # Save CSV
    out_file = output_dir / "regional_summary_transposed.csv"
    final_df.to_csv(out_file, encoding='utf-8-sig', float_format='%.2f')
    print(f"    Saved transposed summary to: {out_file}")
    
    # Save Excel
    excel_file = output_dir / "regional_summary_transposed.xlsx"
    try:
        with pd.ExcelWriter(excel_file, engine='xlsxwriter') as writer:
            final_df.to_excel(writer, sheet_name='Summary')
            
            workbook = writer.book
            worksheet = writer.sheets['Summary']
            
            # Formatting
            header_fmt = workbook.add_format({'bold': True, 'bg_color': '#D7E4BC', 'border': 1})
            
            # Set column widths
            worksheet.set_column(0, 0, 15) # Metric
            worksheet.set_column(1, 1, 20) # Step
            worksheet.set_column(2, len(final_df.columns)+1, 12) # Regions
            
    except Exception as e:
        print(f"    ⚠ Could not create Excel file: {e}")
        
    return df_results


if __name__ == "__main__":
    create_workflow_summary_plots()
