"""
3-Panel Geographic Data Overview Plot for Report

Creates a 3-panel figure showing:
1. GVD (Grundvandsdannelse) - The infiltration raster data
2. GVF (Grundvandsforekomster) - Aquifer polygons with 3 overlapping highlighted
3. V1/V2 sites + rivers - Contamination sites and river network

Purpose: Help readers understand the geographic data used in the risk assessment.
"""

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.colors import LinearSegmentedColormap
import geopandas as gpd
import rasterio
from rasterio.plot import show as rasterio_show
import numpy as np
from pathlib import Path
import sys

# Add parent directories for imports
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from config import (
    GRUNDVAND_PATH,
    GRUNDVAND_LAYER_NAME,
    RIVERS_PATH,
    RIVERS_LAYER_NAME,
    V1_SHP_PATH,
    V2_SHP_PATH,
    GVD_RASTER_DIR,
    WORKFLOW_SUMMARY_DIR,
    get_visualization_path,
)


def find_overlapping_gvfks(gvfk_polygons: gpd.GeoDataFrame, n_highlight: int = 3):
    """
    Find GVFKs that actually overlap geometrically (share the same geographic space).
    
    This finds GVFKs representing different aquifer layers at the same location,
    not just adjacent GVFKs.
    
    Returns the n_highlight GVFKs with the largest mutual overlap area.
    """
    print("  Searching for GVFKs with actual geometric overlap...")
    
    # Build spatial index for efficient overlap detection
    sindex = gvfk_polygons.sindex
    
    # Find all overlapping pairs and calculate overlap area
    overlap_pairs = []
    
    for idx, row in gvfk_polygons.iterrows():
        geom = row.geometry
        gvfk_id = row['GVForekom']
        
        # Find candidates for overlap
        possible_matches_idx = list(sindex.intersection(geom.bounds))
        possible_matches = gvfk_polygons.iloc[possible_matches_idx]
        
        for other_idx, other_row in possible_matches.iterrows():
            if idx < other_idx:  # Avoid counting pairs twice
                other_geom = other_row.geometry
                if geom.intersects(other_geom):
                    try:
                        intersection = geom.intersection(other_geom)
                        overlap_area = intersection.area
                        if overlap_area > 0:
                            overlap_pairs.append({
                                'gvfk1': gvfk_id,
                                'gvfk2': other_row['GVForekom'],
                                'area': overlap_area,
                                'intersection': intersection
                            })
                    except Exception:
                        continue
    
    if not overlap_pairs:
        print("  Warning: No overlapping GVFKs found!")
        # Fallback to first 3 GVFKs
        top_gvfks = gvfk_polygons['GVForekom'].head(n_highlight).tolist()
        selected_polys = gvfk_polygons[gvfk_polygons['GVForekom'].isin(top_gvfks)]
        return top_gvfks, selected_polys.total_bounds
    
    # Sort by overlap area (largest first)
    overlap_pairs.sort(key=lambda x: x['area'], reverse=True)
    
    print(f"  Found {len(overlap_pairs)} overlapping GVFK pairs")
    print(f"  Top 5 by overlap area (m²):")
    for i, pair in enumerate(overlap_pairs[:5]):
        print(f"    {i+1}. {pair['gvfk1']} ∩ {pair['gvfk2']}: {pair['area']:,.0f} m²")
    
    # Find a cluster of n_highlight GVFKs that all overlap with each other
    # Start with the pair with largest overlap
    best_group = [overlap_pairs[0]['gvfk1'], overlap_pairs[0]['gvfk2']]
    best_intersection = overlap_pairs[0]['intersection']
    
    # Try to add more GVFKs that overlap with the existing intersection
    for pair in overlap_pairs[1:]:
        if len(best_group) >= n_highlight:
            break
            
        # Check if either GVFK in this pair overlaps with the current intersection
        for gvfk_id in [pair['gvfk1'], pair['gvfk2']]:
            if gvfk_id not in best_group:
                gvfk_geom = gvfk_polygons[gvfk_polygons['GVForekom'] == gvfk_id].geometry.iloc[0]
                try:
                    if gvfk_geom.intersects(best_intersection):
                        new_intersection = gvfk_geom.intersection(best_intersection)
                        if new_intersection.area > 0:
                            best_group.append(gvfk_id)
                            best_intersection = new_intersection
                            if len(best_group) >= n_highlight:
                                break
                except Exception:
                    continue
    
    print(f"  Selected {len(best_group)} overlapping GVFKs: {best_group}")
    if best_intersection.area > 0:
        print(f"  Common overlap area: {best_intersection.area:,.0f} m²")
    
    # Get the combined bounds focused on the overlap area
    selected_polys = gvfk_polygons[gvfk_polygons['GVForekom'].isin(best_group)]
    
    # Use the intersection centroid to focus the view
    try:
        center = best_intersection.centroid
        # Create bounds around the center, sized to fit the overlapping polygons
        poly_bounds = selected_polys.total_bounds
        width = poly_bounds[2] - poly_bounds[0]
        height = poly_bounds[3] - poly_bounds[1]
        
        # Return bounds focused on the overlap area
        combined_bounds = [
            center.x - width * 0.6,
            center.y - height * 0.6,
            center.x + width * 0.6,
            center.y + height * 0.6,
        ]
    except Exception:
        combined_bounds = selected_polys.total_bounds
    
    return best_group, combined_bounds


def find_suitable_gvd_raster(raster_dir: Path, gvfk_bounds: tuple):
    """Find a GVD raster that covers the area of interest."""
    print("  Searching for GVD raster covering the area...")
    
    tif_files = list(raster_dir.glob("*.tif"))
    if not tif_files:
        print(f"  Warning: No .tif files found in {raster_dir}")
        return None
    
    # Try each raster to find one covering the bounds
    for tif_path in tif_files[:20]:  # Check first 20
        try:
            with rasterio.open(tif_path) as src:
                raster_bounds = src.bounds
                # Check if raster overlaps with our area
                if (raster_bounds.left <= gvfk_bounds[2] and 
                    raster_bounds.right >= gvfk_bounds[0] and
                    raster_bounds.bottom <= gvfk_bounds[3] and 
                    raster_bounds.top >= gvfk_bounds[1]):
                    print(f"  Found suitable raster: {tif_path.name}")
                    return tif_path
        except Exception as e:
            continue
    
    # Fallback: just use the first raster
    print(f"  Using fallback raster: {tif_files[0].name}")
    return tif_files[0]


def create_3panel_overview(output_path: Path = None, figsize: tuple = (18, 6)):
    """
    Create a 3-panel figure showing the geographic data overview.
    """
    print("=" * 70)
    print("CREATING 3-PANEL GEOGRAPHIC DATA OVERVIEW")
    print("=" * 70)
    
    # =========================================================================
    # PHASE 1: Load all data
    # =========================================================================
    print("\n[PHASE 1] Loading geographic data...")
    
    # Load GVFK polygons
    print("  Loading GVF polygons...")
    gvfk_polygons = gpd.read_file(GRUNDVAND_PATH, layer=GRUNDVAND_LAYER_NAME)
    print(f"    → {len(gvfk_polygons)} GVFK polygons loaded")
    
    # Load rivers (all rivers in this layer already have groundwater contact)
    print("  Loading river network...")
    rivers = gpd.read_file(RIVERS_PATH, layer=RIVERS_LAYER_NAME)
    rivers_with_contact = rivers  # All rivers in the layer have contact
    print(f"    → {len(rivers_with_contact)} river segments with groundwater contact")
    
    # Load V1/V2 sites
    print("  Loading V1/V2 contamination sites...")
    v1_sites = gpd.read_file(V1_SHP_PATH)
    v2_sites = gpd.read_file(V2_SHP_PATH)
    print(f"    → {len(v1_sites)} V1 sites, {len(v2_sites)} V2 sites")
    
    # =========================================================================
    # PHASE 2: Find overlapping GVFKs for highlighting
    # =========================================================================
    print("\n[PHASE 2] Finding overlapping GVFKs...")
    highlight_gvfks, focus_bounds = find_overlapping_gvfks(gvfk_polygons, n_highlight=3)
    
    # Expand bounds slightly for better visualization (10% buffer for tighter zoom)
    buffer = 0.1
    width = focus_bounds[2] - focus_bounds[0]
    height = focus_bounds[3] - focus_bounds[1]
    view_bounds = [
        focus_bounds[0] - width * buffer,
        focus_bounds[1] - height * buffer,
        focus_bounds[2] + width * buffer,
        focus_bounds[3] + height * buffer,
    ]
    
    print(f"  View area: {view_bounds}")
    
    # Find V1/V2 sites that overlap with the highlighted GVFKs
    print("\n[PHASE 2b] Finding sites overlapping with highlighted GVFKs...")
    highlighted_gvfk_polys = gvfk_polygons[gvfk_polygons['GVForekom'].isin(highlight_gvfks)]
    highlight_union = highlighted_gvfk_polys.unary_union
    
    # Find overlapping V1 sites
    v1_overlapping = v1_sites[v1_sites.geometry.intersects(highlight_union)]
    v2_overlapping = v2_sites[v2_sites.geometry.intersects(highlight_union)]
    print(f"    → {len(v1_overlapping)} V1 sites overlap highlighted GVFKs")
    print(f"    → {len(v2_overlapping)} V2 sites overlap highlighted GVFKs")
    
    # =========================================================================
    # PHASE 3: Find suitable GVD raster
    # =========================================================================
    print("\n[PHASE 3] Finding GVD raster...")
    gvd_raster_path = find_suitable_gvd_raster(GVD_RASTER_DIR, focus_bounds)
    
    # =========================================================================
    # PHASE 4: Create both horizontal and vertical 3-panel figures
    # =========================================================================
    print("\n[PHASE 4] Creating figures (horizontal and vertical variants)...")
    
    # Define colors for highlighted GVFKs
    highlight_colors = ['#e41a1c', '#377eb8', '#4daf4a']  # Red, Blue, Green
    background_color = '#d9d9d9'  # Light gray for non-highlighted
    
    # Filter data to view area (once, reused for both layouts)
    gvfk_in_view = gvfk_polygons.cx[view_bounds[0]:view_bounds[2], view_bounds[1]:view_bounds[3]]
    rivers_in_view = rivers_with_contact.cx[view_bounds[0]:view_bounds[2], view_bounds[1]:view_bounds[3]]
    v1_in_view = v1_sites.cx[view_bounds[0]:view_bounds[2], view_bounds[1]:view_bounds[3]]
    v2_in_view = v2_sites.cx[view_bounds[0]:view_bounds[2], view_bounds[1]:view_bounds[3]]
    
    def plot_panels(axes, is_vertical=False):
        """Plot all 3 panels on the given axes array."""
        
        # --- Panel 1: GVD Raster (Infiltration) ---
        ax1 = axes[0]
        ax1.set_title("A) Grundvandsdannelse (GVD)", fontsize=14, fontweight='bold')
        
        if gvd_raster_path and gvd_raster_path.exists():
            try:
                with rasterio.open(gvd_raster_path) as src:
                    cmap = LinearSegmentedColormap.from_list(
                        'infiltration',
                        ['#d73027', '#f7f7f7', '#4575b4'],
                        N=256
                    )
                    rasterio_show(src, ax=ax1, cmap=cmap, vmin=-100, vmax=750)
                    
                    # Colorbar
                    sm = plt.cm.ScalarMappable(cmap=cmap, norm=plt.Normalize(vmin=-100, vmax=750))
                    sm.set_array([])
                    orientation = 'horizontal' if is_vertical else 'vertical'
                    cbar = plt.colorbar(sm, ax=ax1, shrink=0.6, label='Infiltration (mm/år)', orientation=orientation)
                    
                    ax1.set_xlim(view_bounds[0], view_bounds[2])
                    ax1.set_ylim(view_bounds[1], view_bounds[3])
            except Exception as e:
                ax1.text(0.5, 0.5, f"Kunne ikke indlæse\nGVD raster", 
                         ha='center', va='center', transform=ax1.transAxes, fontsize=10)
        
        # Remove axis ticks and labels
        ax1.set_xticks([])
        ax1.set_yticks([])
        ax1.set_xlabel('')
        ax1.set_ylabel('')
        
        # --- Panel 2: GVF Polygons (Aquifers) ---
        ax2 = axes[1]
        ax2.set_title("B) Grundvandsforekomster (GVF)", fontsize=14, fontweight='bold')
        
        # Plot non-highlighted GVFKs in gray
        background_gvfks = gvfk_in_view[~gvfk_in_view['GVForekom'].isin(highlight_gvfks)]
        background_gvfks.plot(ax=ax2, color=background_color, edgecolor='#969696', linewidth=0.5, alpha=0.7)
        
        # Plot highlighted GVFKs with distinct colors
        legend_handles = []
        for i, gvfk_id in enumerate(highlight_gvfks):
            gvfk_poly = gvfk_polygons[gvfk_polygons['GVForekom'] == gvfk_id]
            if not gvfk_poly.empty:
                gvfk_poly.plot(ax=ax2, color=highlight_colors[i], edgecolor='black', 
                              linewidth=1.5, alpha=0.6)
                legend_handles.append(mpatches.Patch(color=highlight_colors[i], 
                                                      label=f"GVFK: {gvfk_id}", alpha=0.6))
        
        legend_handles.append(mpatches.Patch(color=background_color, label="Øvrige GVFKs", alpha=0.7))
        ax2.legend(handles=legend_handles, loc='upper right', fontsize=9)
        
        ax2.set_xlim(view_bounds[0], view_bounds[2])
        ax2.set_ylim(view_bounds[1], view_bounds[3])
        ax2.set_xticks([])
        ax2.set_yticks([])
        ax2.set_xlabel('')
        ax2.set_ylabel('')
        
        # --- Panel 3: V1/V2 Sites + Rivers ---
        ax3 = axes[2]
        ax3.set_title("C) V1/V2 Lokaliteter + Vandløb", fontsize=14, fontweight='bold')
        
        # Background GVFKs
        gvfk_in_view.plot(ax=ax3, color='#f0f0f0', edgecolor='#cccccc', linewidth=0.3, alpha=0.5)
        
        # Rivers (lighter and thinner)
        if not rivers_in_view.empty:
            rivers_in_view.plot(ax=ax3, color='#6baed6', linewidth=0.6)
        
        # V1 (blue) and V2 (red) sites
        if not v1_in_view.empty:
            v1_in_view.plot(ax=ax3, color='#2171b5', edgecolor='#084594', linewidth=0.5, 
                            alpha=0.7, markersize=12)
        if not v2_in_view.empty:
            v2_in_view.plot(ax=ax3, color='#d73027', edgecolor='#7f0000', linewidth=0.5, 
                            alpha=0.7, markersize=12)
        
        legend_handles_panel3 = [
            mpatches.Patch(color='#2171b5', label='V1 lokaliteter', alpha=0.7),
            mpatches.Patch(color='#d73027', label='V2 lokaliteter', alpha=0.7),
            plt.Line2D([0], [0], color='#6baed6', linewidth=2, label='Vandløb'),
        ]
        
        ax3.set_xlim(view_bounds[0], view_bounds[2])
        ax3.set_ylim(view_bounds[1], view_bounds[3])
        ax3.set_xticks([])
        ax3.set_yticks([])
        ax3.set_xlabel('')
        ax3.set_ylabel('')
        ax3.legend(handles=legend_handles_panel3, loc='upper right', fontsize=9)
    
    # Determine output directory
    if output_path is None:
        output_dir = get_visualization_path('workflow_summary')
    else:
        output_dir = output_path.parent
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # =========================================================================
    # Option B: Generate 3 INDIVIDUAL panel images
    # =========================================================================
    print("  Creating individual panel images...")
    
    panel_size = (10, 8)  # Good size for individual panels
    
    # Panel A: GVD
    fig_a, ax_a = plt.subplots(1, 1, figsize=panel_size, dpi=150)
    ax_a.set_title("A) Grundvandsdannelse (GVD)", fontsize=14, fontweight='bold')
    if gvd_raster_path and gvd_raster_path.exists():
        try:
            with rasterio.open(gvd_raster_path) as src:
                cmap = LinearSegmentedColormap.from_list('infiltration', ['#d73027', '#f7f7f7', '#4575b4'], N=256)
                rasterio_show(src, ax=ax_a, cmap=cmap, vmin=-100, vmax=750)
                sm = plt.cm.ScalarMappable(cmap=cmap, norm=plt.Normalize(vmin=-100, vmax=750))
                sm.set_array([])
                cbar = plt.colorbar(sm, ax=ax_a, shrink=0.7, label='Infiltration (mm/år)')
                ax_a.set_xlim(view_bounds[0], view_bounds[2])
                ax_a.set_ylim(view_bounds[1], view_bounds[3])
        except Exception:
            ax_a.text(0.5, 0.5, "Kunne ikke indlæse GVD raster", ha='center', va='center', transform=ax_a.transAxes)
    ax_a.set_xticks([])
    ax_a.set_yticks([])
    plt.tight_layout()
    path_a = output_dir / 'panel_A_GVD.png'
    plt.savefig(path_a, dpi=400, bbox_inches='tight', facecolor='white')
    plt.savefig(path_a.with_suffix('.pdf'), dpi=400, bbox_inches='tight', facecolor='white')
    print(f"    Saved: {path_a}")
    plt.close()
    
    # Panel B: GVF
    fig_b, ax_b = plt.subplots(1, 1, figsize=panel_size, dpi=150)
    ax_b.set_title("B) Grundvandsforekomster (GVF)", fontsize=14, fontweight='bold')
    background_gvfks = gvfk_in_view[~gvfk_in_view['GVForekom'].isin(highlight_gvfks)]
    background_gvfks.plot(ax=ax_b, color=background_color, edgecolor='#969696', linewidth=0.5, alpha=0.7)
    legend_handles = []
    for i, gvfk_id in enumerate(highlight_gvfks):
        gvfk_poly = gvfk_polygons[gvfk_polygons['GVForekom'] == gvfk_id]
        if not gvfk_poly.empty:
            gvfk_poly.plot(ax=ax_b, color=highlight_colors[i], edgecolor='black', linewidth=1.5, alpha=0.6)
            legend_handles.append(mpatches.Patch(color=highlight_colors[i], label=f"GVFK: {gvfk_id}", alpha=0.6))
    legend_handles.append(mpatches.Patch(color=background_color, label="Øvrige GVFKs", alpha=0.7))
    ax_b.legend(handles=legend_handles, loc='upper right', fontsize=9)
    ax_b.set_xlim(view_bounds[0], view_bounds[2])
    ax_b.set_ylim(view_bounds[1], view_bounds[3])
    ax_b.set_xticks([])
    ax_b.set_yticks([])
    plt.tight_layout()
    path_b = output_dir / 'panel_B_GVF.png'
    plt.savefig(path_b, dpi=400, bbox_inches='tight', facecolor='white')
    plt.savefig(path_b.with_suffix('.pdf'), dpi=400, bbox_inches='tight', facecolor='white')
    print(f"    Saved: {path_b}")
    plt.close()
    
    # Panel C: V1/V2 + Rivers
    fig_c, ax_c = plt.subplots(1, 1, figsize=panel_size, dpi=150)
    ax_c.set_title("C) V1/V2 Lokaliteter + Vandløb", fontsize=14, fontweight='bold')
    gvfk_in_view.plot(ax=ax_c, color='#f0f0f0', edgecolor='#cccccc', linewidth=0.3, alpha=0.5)
    if not rivers_in_view.empty:
        rivers_in_view.plot(ax=ax_c, color='#6baed6', linewidth=0.6)
    if not v1_in_view.empty:
        v1_in_view.plot(ax=ax_c, color='#2171b5', edgecolor='#084594', linewidth=0.5, alpha=0.7, markersize=12)
    if not v2_in_view.empty:
        v2_in_view.plot(ax=ax_c, color='#d73027', edgecolor='#7f0000', linewidth=0.5, alpha=0.7, markersize=12)
    legend_handles_c = [
        mpatches.Patch(color='#2171b5', label='V1 lokaliteter', alpha=0.7),
        mpatches.Patch(color='#d73027', label='V2 lokaliteter', alpha=0.7),
        plt.Line2D([0], [0], color='#6baed6', linewidth=2, label='Vandløb'),
    ]
    ax_c.legend(handles=legend_handles_c, loc='upper right', fontsize=9)
    ax_c.set_xlim(view_bounds[0], view_bounds[2])
    ax_c.set_ylim(view_bounds[1], view_bounds[3])
    ax_c.set_xticks([])
    ax_c.set_yticks([])
    plt.tight_layout()
    path_c = output_dir / 'panel_C_V1V2.png'
    plt.savefig(path_c, dpi=400, bbox_inches='tight', facecolor='white')
    plt.savefig(path_c.with_suffix('.pdf'), dpi=400, bbox_inches='tight', facecolor='white')
    print(f"    Saved: {path_c}")
    plt.close()
    
    # =========================================================================
    # Option C: 2+1 Layout (GVF + V1V2 on top, GVD on bottom spanning full width)
    # =========================================================================
    print("  Creating 2+1 combined layout...")
    
    fig = plt.figure(figsize=(16, 14), dpi=150)
    
    # Top row: Panel B (GVF) and Panel C (V1/V2)
    ax_b_combined = fig.add_subplot(2, 2, 1)  # Top-left
    ax_c_combined = fig.add_subplot(2, 2, 2)  # Top-right
    ax_a_combined = fig.add_subplot(2, 1, 2)  # Bottom (full width) - GVD
    
    # Panel B: GVF (top-left)
    ax_b_combined.set_title("B) Grundvandsforekomster (GVF)", fontsize=16, fontweight='bold')
    background_gvfks.plot(ax=ax_b_combined, color=background_color, edgecolor='#969696', linewidth=0.5, alpha=0.7)
    for i, gvfk_id in enumerate(highlight_gvfks):
        gvfk_poly = gvfk_polygons[gvfk_polygons['GVForekom'] == gvfk_id]
        if not gvfk_poly.empty:
            gvfk_poly.plot(ax=ax_b_combined, color=highlight_colors[i], edgecolor='black', linewidth=1.5, alpha=0.6)
    ax_b_combined.legend(handles=legend_handles, loc='upper right', fontsize=11)
    ax_b_combined.set_xlim(view_bounds[0], view_bounds[2])
    ax_b_combined.set_ylim(view_bounds[1], view_bounds[3])
    ax_b_combined.set_xticks([])
    ax_b_combined.set_yticks([])
    
    # Panel C: V1/V2 + Rivers (top-right)
    ax_c_combined.set_title("C) V1/V2 Lokaliteter + Vandløb", fontsize=16, fontweight='bold')
    gvfk_in_view.plot(ax=ax_c_combined, color='#f0f0f0', edgecolor='#cccccc', linewidth=0.3, alpha=0.5)
    if not rivers_in_view.empty:
        rivers_in_view.plot(ax=ax_c_combined, color='#6baed6', linewidth=0.6)
    if not v1_in_view.empty:
        v1_in_view.plot(ax=ax_c_combined, color='#2171b5', edgecolor='#084594', linewidth=0.5, alpha=0.7, markersize=12)
    if not v2_in_view.empty:
        v2_in_view.plot(ax=ax_c_combined, color='#d73027', edgecolor='#7f0000', linewidth=0.5, alpha=0.7, markersize=12)
    ax_c_combined.legend(handles=legend_handles_c, loc='upper right', fontsize=11)
    ax_c_combined.set_xlim(view_bounds[0], view_bounds[2])
    ax_c_combined.set_ylim(view_bounds[1], view_bounds[3])
    ax_c_combined.set_xticks([])
    ax_c_combined.set_yticks([])
    
    # Panel A: GVD (bottom, full width)
    ax_a_combined.set_title("A) Grundvandsdannelse (GVD)", fontsize=16, fontweight='bold')
    if gvd_raster_path and gvd_raster_path.exists():
        try:
            with rasterio.open(gvd_raster_path) as src:
                cmap = LinearSegmentedColormap.from_list('infiltration', ['#d73027', '#f7f7f7', '#4575b4'], N=256)
                rasterio_show(src, ax=ax_a_combined, cmap=cmap, vmin=-100, vmax=750)
                sm = plt.cm.ScalarMappable(cmap=cmap, norm=plt.Normalize(vmin=-100, vmax=750))
                sm.set_array([])
                cbar = plt.colorbar(sm, ax=ax_a_combined, shrink=0.5, label='Infiltration (mm/år)', orientation='horizontal', pad=0.02)
                cbar.ax.tick_params(labelsize=11)
                cbar.set_label('Infiltration (mm/år)', fontsize=12)
                ax_a_combined.set_xlim(view_bounds[0], view_bounds[2])
                ax_a_combined.set_ylim(view_bounds[1], view_bounds[3])
        except Exception:
            pass
    ax_a_combined.set_xticks([])
    ax_a_combined.set_yticks([])
    
    plt.tight_layout()
    combined_path = output_dir / 'data_overview_2plus1.png'
    plt.savefig(combined_path, dpi=400, bbox_inches='tight', facecolor='white')
    plt.savefig(combined_path.with_suffix('.pdf'), dpi=400, bbox_inches='tight', facecolor='white')
    print(f"    Saved: {combined_path}")
    plt.close()
    
    print("\n" + "=" * 70)
    print("3-PANEL OVERVIEW COMPLETE!")
    print(f"  Individual panels: {path_a.name}, {path_b.name}, {path_c.name}")
    print(f"  Combined 2+1:      {combined_path.name}")
    print("=" * 70)
    
    return path_a, path_b, path_c, combined_path


if __name__ == "__main__":
    create_3panel_overview()


