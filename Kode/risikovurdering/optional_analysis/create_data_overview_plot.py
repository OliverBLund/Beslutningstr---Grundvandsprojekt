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
import matplotlib.colors as mcolors
from mpl_toolkits.axes_grid1.inset_locator import inset_axes, mark_inset
import geopandas as gpd
import pandas as pd
import rasterio
from rasterio.plot import show as rasterio_show
import numpy as np
from pathlib import Path
import sys

# Add parent directories for imports
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from config import (
    COLUMN_MAPPINGS,
    GRUNDVAND_PATH,
    GRUNDVAND_LAYER_NAME,
    RIVERS_PATH,
    RIVERS_LAYER_NAME,
    V1_SHP_PATH,
    V2_SHP_PATH,
    GVD_RASTER_DIR,
    WORKFLOW_SUMMARY_DIR,
    WORKFLOW_SETTINGS,
    get_visualization_path,
    RIVER_FLOW_POINTS_PATH,
    RIVER_FLOW_POINTS_LAYER,
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

    tif_files = [
        f
        for f in raster_dir.glob("*.tif")
        if "_gvd_" in f.name.lower() and "downwardflux" not in f.name.lower()
    ]
    if not tif_files:
        print(f"  Warning: No GVD .tif files found in {raster_dir}")
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

    # Load rivers and split by contact/GVFK presence (mirrors Step 2 logic)
    print("  Loading river network...")
    rivers = gpd.read_file(RIVERS_PATH, layer=RIVERS_LAYER_NAME)
    contact_col = COLUMN_MAPPINGS["rivers"].get("contact")
    river_gvfk_col = COLUMN_MAPPINGS["rivers"].get("gvfk_id")

    if river_gvfk_col and river_gvfk_col in rivers.columns:
        rivers[river_gvfk_col] = rivers[river_gvfk_col].astype(str).str.strip()
        valid_gvfk_mask = rivers[river_gvfk_col] != ""
    else:
        valid_gvfk_mask = None

    if contact_col and contact_col in rivers.columns:
        contact_value = WORKFLOW_SETTINGS["contact_filter_value"]
        contact_mask = rivers[contact_col] == contact_value
        if valid_gvfk_mask is not None:
            contact_mask = contact_mask & valid_gvfk_mask
        rivers_with_contact = rivers[contact_mask]
        rivers_without_contact = rivers[~contact_mask]
    else:
        # New Grunddata format: GVFK presence is the contact indicator
        if valid_gvfk_mask is not None:
            rivers_with_contact = rivers[valid_gvfk_mask]
            rivers_without_contact = rivers[~valid_gvfk_mask]
        else:
            rivers_with_contact = rivers
            rivers_without_contact = rivers.iloc[0:0]
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
    rivers_no_contact_in_view = rivers_without_contact.cx[view_bounds[0]:view_bounds[2], view_bounds[1]:view_bounds[3]]
    v1_in_view = v1_sites.cx[view_bounds[0]:view_bounds[2], view_bounds[1]:view_bounds[3]]
    v2_in_view = v2_sites.cx[view_bounds[0]:view_bounds[2], view_bounds[1]:view_bounds[3]]

    def _pick_site_point():
        if not v2_in_view.empty:
            geom = v2_in_view.geometry.iloc[0]
        elif not v1_in_view.empty:
            geom = v1_in_view.geometry.iloc[0]
        else:
            return None

        if geom is None or geom.is_empty:
            return None
        if geom.geom_type == "Point":
            return geom
        return geom.representative_point()

    site_point = _pick_site_point()

    def _pick_site_polygon():
        """Pick a site polygon that shows mixed infiltration (both positive and negative pixels)."""
        if gvd_raster_path is None or not gvd_raster_path.exists():
            # Fallback to largest site if no raster available
            for gdf in (v2_in_view, v1_in_view):
                if gdf.empty:
                    continue
                geom_types = gdf.geometry.geom_type
                polys = gdf[geom_types.isin(["Polygon", "MultiPolygon"])]
                if polys.empty:
                    continue
                polys = polys.copy()
                polys["__area"] = polys.geometry.area
                return polys.loc[polys["__area"].idxmax()].geometry
            return None

        # Try to find a site with mixed infiltration values
        best_site = None
        best_score = -1  # Score based on having both positive and negative pixels

        with rasterio.open(gvd_raster_path) as src:
            for gdf in (v2_in_view, v1_in_view):
                if gdf.empty:
                    continue
                geom_types = gdf.geometry.geom_type
                polys = gdf[geom_types.isin(["Polygon", "MultiPolygon"])]
                if polys.empty:
                    continue

                for idx, row in polys.iterrows():
                    geom = row.geometry
                    if geom is None or geom.is_empty:
                        continue

                    # Get bounds for this site with buffer
                    minx, miny, maxx, maxy = geom.bounds
                    width = maxx - minx
                    height = maxy - miny
                    buffer_m = max(width, height) * 0.2
                    buffer_m = max(buffer_m, 200.0)
                    site_bounds = [minx - buffer_m, miny - buffer_m, maxx + buffer_m, maxy + buffer_m]

                    try:
                        # Sample pixels for this site
                        window = rasterio.windows.from_bounds(*site_bounds, transform=src.transform)
                        data_window = src.read(1, window=window, masked=True)

                        if np.ma.is_masked(data_window):
                            valid_pixels = data_window.compressed()
                        else:
                            valid_pixels = data_window.ravel()

                        if valid_pixels.size < 10:  # Need at least 10 pixels
                            continue

                        # Calculate mix score
                        positive_count = (valid_pixels > 0).sum()
                        negative_count = (valid_pixels < 0).sum()
                        total_count = len(valid_pixels)

                        # Good mix means 20-80% positive (not too skewed)
                        positive_ratio = positive_count / total_count if total_count > 0 else 0

                        # Score: prefer sites with 30-70% positive, penalize too uniform sites
                        if 0.2 <= positive_ratio <= 0.8:
                            # How close to 50/50 mix? (1.0 = perfect mix, 0.0 = all one color)
                            mix_quality = 1.0 - abs(positive_ratio - 0.5) * 2
                            # Also favor larger sites (more pixels)
                            size_factor = min(total_count / 100, 1.0)
                            score = mix_quality * 0.7 + size_factor * 0.3

                            if score > best_score:
                                best_score = score
                                best_site = geom
                    except Exception:
                        continue

        # If no mixed site found, fallback to largest site
        if best_site is None:
            for gdf in (v2_in_view, v1_in_view):
                if gdf.empty:
                    continue
                geom_types = gdf.geometry.geom_type
                polys = gdf[geom_types.isin(["Polygon", "MultiPolygon"])]
                if polys.empty:
                    continue
                polys = polys.copy()
                polys["__area"] = polys.geometry.area
                return polys.loc[polys["__area"].idxmax()].geometry

        return best_site

    def _site_inset_bounds(geom):
        if geom is None or geom.is_empty:
            return None
        minx, miny, maxx, maxy = geom.bounds
        width = maxx - minx
        height = maxy - miny
        buffer_m = max(width, height) * 0.2
        buffer_m = max(buffer_m, 200.0)
        return [
            minx - buffer_m,
            miny - buffer_m,
            maxx + buffer_m,
            maxy + buffer_m,
        ]

    def _gvd_binary_style():
        """Create binary colormap: red for negative (upward), green for positive (downward)."""
        cmap = mcolors.ListedColormap(['#d73027', '#1a9850'])  # Red, Green
        norm = mcolors.BoundaryNorm([float('-inf'), 0, float('inf')], cmap.N)
        return cmap, norm

    site_geom = _pick_site_polygon()
    site_inset_bounds = _site_inset_bounds(site_geom)

    def plot_panels(axes, is_vertical=False):
        """Plot all 3 panels on the given axes array."""

        # --- Panel 1: GVD Raster (Infiltration) ---
        ax1 = axes[0]
        gvd_name = gvd_raster_path.name if gvd_raster_path else "ikke fundet"
        ax1.set_title(f"A) Grundvandsdannelse (GVD) – {gvd_name}", fontsize=14, fontweight='bold')

        if gvd_raster_path and gvd_raster_path.exists():
            try:
                with rasterio.open(gvd_raster_path) as src:
                    data = src.read(1, masked=True)
                    valid = data.compressed() if np.ma.is_masked(data) else data.ravel()
                    if valid.size > 0:
                        vmin, vmax = np.percentile(valid, [2, 98])
                        if vmin == vmax:
                            vmin = float(valid.min())
                            vmax = float(valid.max())
                    else:
                        vmin, vmax = None, None

                    rasterio_show(
                        data,
                        transform=src.transform,
                        ax=ax1,
                        cmap="Greys",
                        vmin=vmin,
                        vmax=vmax,
                    )

                    orientation = "horizontal" if is_vertical else "vertical"
                    if ax1.images:
                        plt.colorbar(
                            ax1.images[-1],
                            ax=ax1,
                            shrink=0.6,
                            label="Infiltration (mm/år)",
                            orientation=orientation,
                        )

                    # Add legend for binary classification shown in inset
                    legend_handles_gvd = [
                        mpatches.Patch(color='#1a9850', label='Positiv (nedadgående)', alpha=0.8),
                        mpatches.Patch(color='#d73027', label='Negativ (opadgående)', alpha=0.8),
                        mpatches.Patch(facecolor='none', edgecolor='#111111', linewidth=1.5, label='Lokalitet'),
                    ]
                    ax1.legend(handles=legend_handles_gvd, loc='upper left', fontsize=9)

                    if site_geom is not None and site_inset_bounds is not None:
                        window = rasterio.windows.from_bounds(
                            *site_inset_bounds, transform=src.transform
                        )
                        data_window = src.read(1, window=window, masked=True)
                        valid_window = (
                            data_window.compressed()
                            if np.ma.is_masked(data_window)
                            else data_window.ravel()
                        )
                        if valid_window.size > 0:
                            # Use binary classification for inset
                            cmap_w, norm_w = _gvd_binary_style()
                            axins = inset_axes(
                                ax1,
                                width="40%",
                                height="40%",
                                loc="lower right",
                                borderpad=1,
                            )
                            rasterio_show(
                                data_window,
                                transform=src.window_transform(window),
                                ax=axins,
                                cmap=cmap_w,
                                norm=norm_w,
                            )
                            gpd.GeoSeries([site_geom]).boundary.plot(
                                ax=axins, color="#111111", linewidth=1.5
                            )
                            axins.set_xlim(site_inset_bounds[0], site_inset_bounds[2])
                            axins.set_ylim(site_inset_bounds[1], site_inset_bounds[3])
                            axins.set_xticks([])
                            axins.set_yticks([])

                            mark_inset(
                                ax1,
                                axins,
                                loc1=2,
                                loc2=4,
                                fc="none",
                                ec="#666666",
                                lw=0.8,
                            )

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

        # Rivers (only show rivers with GVF contact in main panel)
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
            plt.Line2D([0], [0], color='#d73027', linewidth=2, linestyle='--', label='Vandløb med GVF-kontakt (indsats)'),
        ]

        ax3.set_xlim(view_bounds[0], view_bounds[2])
        ax3.set_ylim(view_bounds[1], view_bounds[3])
        ax3.set_xticks([])
        ax3.set_yticks([])
        ax3.set_xlabel('')
        ax3.set_ylabel('')
        ax3.legend(handles=legend_handles_panel3, loc='upper right', fontsize=9)

        # Inset zoom for a denser area
        if not v2_in_view.empty:
            base_bounds = v2_in_view.total_bounds
        elif not v1_in_view.empty:
            base_bounds = v1_in_view.total_bounds
        elif not rivers_in_view.empty:
            base_bounds = rivers_in_view.total_bounds
        else:
            base_bounds = view_bounds

        inset_bounds = None
        if base_bounds is not None:
            xmin, ymin, xmax, ymax = base_bounds
            width = xmax - xmin
            height = ymax - ymin
            if width > 0 and height > 0:
                # Zoom in very tight: higher factor = smaller area shown (0.48 shows ~4% of original area)
                inset_bounds = [
                    xmin + width * 0.48,
                    ymin + height * 0.48,
                    xmax - width * 0.48,
                    ymax - height * 0.48,
                ]

        if inset_bounds:
            axins = inset_axes(ax3, width="36%", height="36%", loc="lower left", borderpad=1)
            gvfk_in_view.plot(ax=axins, color='#f0f0f0', edgecolor='#cccccc', linewidth=0.3, alpha=0.5)
            # Thicker lines for rivers with GVF contact
            if not rivers_in_view.empty:
                rivers_in_view.plot(ax=axins, color='#d73027', linewidth=1.5, linestyle='--')
            # Show rivers without contact in background
            if not rivers_no_contact_in_view.empty:
                rivers_no_contact_in_view.plot(ax=axins, color='#9ecae1', linewidth=1.0)
            if not v1_in_view.empty:
                v1_in_view.plot(ax=axins, color='#2171b5', edgecolor='#084594', linewidth=0.5,
                                alpha=0.7, markersize=18)
            if not v2_in_view.empty:
                v2_in_view.plot(ax=axins, color='#d73027', edgecolor='#7f0000', linewidth=0.5,
                                alpha=0.7, markersize=18)
            axins.set_xlim(inset_bounds[0], inset_bounds[2])
            axins.set_ylim(inset_bounds[1], inset_bounds[3])
            axins.set_xticks([])
            axins.set_yticks([])
            mark_inset(ax3, axins, loc1=2, loc2=4, fc="none", ec="#666666", lw=0.8)

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
    gvd_name = gvd_raster_path.name if gvd_raster_path else "ikke fundet"
    ax_a.set_title(f"A) Grundvandsdannelse (GVD) – {gvd_name}", fontsize=14, fontweight='bold')
    if gvd_raster_path and gvd_raster_path.exists():
        try:
            with rasterio.open(gvd_raster_path) as src:
                data = src.read(1, masked=True)
                valid = data.compressed() if np.ma.is_masked(data) else data.ravel()
                if valid.size > 0:
                    vmin, vmax = np.percentile(valid, [2, 98])
                    if vmin == vmax:
                        vmin = float(valid.min())
                        vmax = float(valid.max())
                else:
                    vmin, vmax = None, None

                rasterio_show(
                    data,
                    transform=src.transform,
                    ax=ax_a,
                    cmap="Greys",
                    vmin=vmin,
                    vmax=vmax,
                )
                if ax_a.images:
                    plt.colorbar(
                        ax_a.images[-1],
                        ax=ax_a,
                        shrink=0.7,
                        label="Infiltration (mm/år)",
                    )

                # Add legend for binary classification shown in inset
                legend_handles_gvd = [
                    mpatches.Patch(color='#1a9850', label='Positiv (nedadgående)', alpha=0.8),
                    mpatches.Patch(color='#d73027', label='Negativ (opadgående)', alpha=0.8),
                    mpatches.Patch(facecolor='none', edgecolor='#111111', linewidth=1.5, label='Lokalitet'),
                ]
                ax_a.legend(handles=legend_handles_gvd, loc='upper left', fontsize=9)
                if site_geom is not None and site_inset_bounds is not None:
                    window = rasterio.windows.from_bounds(
                        *site_inset_bounds, transform=src.transform
                    )
                    data_window = src.read(1, window=window, masked=True)
                    valid_window = (
                        data_window.compressed()
                        if np.ma.is_masked(data_window)
                        else data_window.ravel()
                    )
                    if valid_window.size > 0:
                        # Use binary classification for inset
                        cmap_w, norm_w = _gvd_binary_style()
                        axins = inset_axes(
                            ax_a,
                            width="40%",
                            height="40%",
                            loc="lower right",
                            borderpad=1,
                        )
                        rasterio_show(
                            data_window,
                            transform=src.window_transform(window),
                            ax=axins,
                            cmap=cmap_w,
                            norm=norm_w,
                        )
                        gpd.GeoSeries([site_geom]).boundary.plot(
                            ax=axins, color="#111111", linewidth=1.5
                        )
                        axins.set_xlim(site_inset_bounds[0], site_inset_bounds[2])
                        axins.set_ylim(site_inset_bounds[1], site_inset_bounds[3])
                        axins.set_xticks([])
                        axins.set_yticks([])

                        mark_inset(
                            ax_a,
                            axins,
                            loc1=2,
                            loc2=4,
                            fc="none",
                            ec="#666666",
                            lw=0.8,
                        )
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
    # Only show rivers with GVF contact in main panel
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
        plt.Line2D([0], [0], color='#d73027', linewidth=2, linestyle='--', label='Vandløb med GVF-kontakt (indsats)'),
    ]
    ax_c.legend(handles=legend_handles_c, loc='upper right', fontsize=9)
    ax_c.set_xlim(view_bounds[0], view_bounds[2])
    ax_c.set_ylim(view_bounds[1], view_bounds[3])
    ax_c.set_xticks([])
    ax_c.set_yticks([])
    # Inset zoom for a denser area
    if not v2_in_view.empty:
        base_bounds = v2_in_view.total_bounds
    elif not v1_in_view.empty:
        base_bounds = v1_in_view.total_bounds
    elif not rivers_in_view.empty:
        base_bounds = rivers_in_view.total_bounds
    else:
        base_bounds = view_bounds

    inset_bounds = None
    if base_bounds is not None:
        xmin, ymin, xmax, ymax = base_bounds
        width = xmax - xmin
        height = ymax - ymin
        if width > 0 and height > 0:
            # Zoom in much more: higher factor = smaller area shown (0.42 shows ~15% of original area)
            inset_bounds = [
                xmin + width * 0.42,
                ymin + height * 0.42,
                xmax - width * 0.42,
                ymax - height * 0.42,
            ]

    if inset_bounds:
        axins = inset_axes(ax_c, width="36%", height="36%", loc="lower left", borderpad=1)
        gvfk_in_view.plot(ax=axins, color='#f0f0f0', edgecolor='#cccccc', linewidth=0.3, alpha=0.5)
        # Thicker lines for rivers with GVF contact
        if not rivers_in_view.empty:
            rivers_in_view.plot(ax=axins, color='#d73027', linewidth=1.5, linestyle='--')
        # Show rivers without contact in background
        if not rivers_no_contact_in_view.empty:
            rivers_no_contact_in_view.plot(ax=axins, color='#9ecae1', linewidth=1.0)
        if not v1_in_view.empty:
            v1_in_view.plot(ax=axins, color='#2171b5', edgecolor='#084594', linewidth=0.5,
                            alpha=0.7, markersize=18)
        if not v2_in_view.empty:
            v2_in_view.plot(ax=axins, color='#d73027', edgecolor='#7f0000', linewidth=0.5,
                            alpha=0.7, markersize=18)
        axins.set_xlim(inset_bounds[0], inset_bounds[2])
        axins.set_ylim(inset_bounds[1], inset_bounds[3])
        axins.set_xticks([])
        axins.set_yticks([])
        mark_inset(ax_c, axins, loc1=2, loc2=4, fc="none", ec="#666666", lw=0.8)
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

    # Panel B: GVF (top-left) - Changed from "B)" to "A)"
    ax_b_combined.set_title("A) Grundvandsforekomster (GVF)", fontsize=16, fontweight='bold')
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

    # Panel C: V1/V2 + Rivers (top-right) - Changed from "C)" to "B)"
    ax_c_combined.set_title("B) V1/V2 Lokaliteter + Vandløb", fontsize=16, fontweight='bold')
    gvfk_in_view.plot(ax=ax_c_combined, color='#f0f0f0', edgecolor='#cccccc', linewidth=0.3, alpha=0.5)
    # Only show rivers with GVF contact in main panel
    if not rivers_in_view.empty:
        rivers_in_view.plot(ax=ax_c_combined, color='#6baed6', linewidth=0.6)
    if not v1_in_view.empty:
        v1_in_view.plot(ax=ax_c_combined, color='#2171b5', edgecolor='#084594', linewidth=0.5, alpha=0.7, markersize=12)
    if not v2_in_view.empty:
        v2_in_view.plot(ax=ax_c_combined, color='#d73027', edgecolor='#7f0000', linewidth=0.5, alpha=0.7, markersize=12)

    # Update legend to include inset explanation
    legend_handles_c_combined = [
        mpatches.Patch(color='#2171b5', label='V1 lokaliteter', alpha=0.7),
        mpatches.Patch(color='#d73027', label='V2 lokaliteter', alpha=0.7),
        plt.Line2D([0], [0], color='#6baed6', linewidth=2, label='Vandløb'),
        plt.Line2D([0], [0], color='#d73027', linewidth=2, linestyle='--', label='Vandløb med GVF-kontakt (indsats)'),
    ]
    ax_c_combined.legend(handles=legend_handles_c_combined, loc='upper right', fontsize=11)
    ax_c_combined.set_xlim(view_bounds[0], view_bounds[2])
    ax_c_combined.set_ylim(view_bounds[1], view_bounds[3])
    ax_c_combined.set_xticks([])
    ax_c_combined.set_yticks([])
    # Inset zoom for a denser area
    if not v2_in_view.empty:
        base_bounds = v2_in_view.total_bounds
    elif not v1_in_view.empty:
        base_bounds = v1_in_view.total_bounds
    elif not rivers_in_view.empty:
        base_bounds = rivers_in_view.total_bounds
    else:
        base_bounds = view_bounds

    inset_bounds = None
    if base_bounds is not None:
        xmin, ymin, xmax, ymax = base_bounds
        width = xmax - xmin
        height = ymax - ymin
        if width > 0 and height > 0:
            # Zoom in much more: higher factor = smaller area shown (0.42 shows ~15% of original area)
            inset_bounds = [
                xmin + width * 0.42,
                ymin + height * 0.42,
                xmax - width * 0.42,
                ymax - height * 0.42,
            ]

    if inset_bounds:
        axins = inset_axes(ax_c_combined, width="36%", height="36%", loc="lower left", borderpad=1)
        gvfk_in_view.plot(ax=axins, color='#f0f0f0', edgecolor='#cccccc', linewidth=0.3, alpha=0.5)
        # Thicker lines for rivers with GVF contact
        if not rivers_in_view.empty:
            rivers_in_view.plot(ax=axins, color='#d73027', linewidth=1.5, linestyle='--')
        # Show rivers without contact in background
        if not rivers_no_contact_in_view.empty:
            rivers_no_contact_in_view.plot(ax=axins, color='#9ecae1', linewidth=1.0)
        if not v1_in_view.empty:
            v1_in_view.plot(ax=axins, color='#2171b5', edgecolor='#084594', linewidth=0.5,
                            alpha=0.7, markersize=18)
        if not v2_in_view.empty:
            v2_in_view.plot(ax=axins, color='#d73027', edgecolor='#7f0000', linewidth=0.5,
                            alpha=0.7, markersize=18)
        axins.set_xlim(inset_bounds[0], inset_bounds[2])
        axins.set_ylim(inset_bounds[1], inset_bounds[3])
        axins.set_xticks([])
        axins.set_yticks([])
        mark_inset(ax_c_combined, axins, loc1=2, loc2=4, fc="none", ec="#666666", lw=0.8)

    # Panel A: GVD (bottom, full width) - Changed from "A)" to "C)"
    gvd_name = gvd_raster_path.name if gvd_raster_path else "ikke fundet"
    ax_a_combined.set_title(f"C) Grundvandsdannelse (GVD) – {gvd_name}", fontsize=16, fontweight='bold')
    if gvd_raster_path and gvd_raster_path.exists():
        try:
            with rasterio.open(gvd_raster_path) as src:
                data = src.read(1, masked=True)
                valid = data.compressed() if np.ma.is_masked(data) else data.ravel()
                if valid.size > 0:
                    vmin, vmax = np.percentile(valid, [2, 98])
                    if vmin == vmax:
                        vmin = float(valid.min())
                        vmax = float(valid.max())
                else:
                    vmin, vmax = None, None

                rasterio_show(
                    data,
                    transform=src.transform,
                    ax=ax_a_combined,
                    cmap="Greys",
                    vmin=vmin,
                    vmax=vmax,
                )
                if ax_a_combined.images:
                    cbar = plt.colorbar(
                        ax_a_combined.images[-1],
                        ax=ax_a_combined,
                        shrink=0.5,
                        label="Infiltration (mm/år)",
                        orientation="horizontal",
                        pad=0.02,
                    )
                    cbar.ax.tick_params(labelsize=11)
                    cbar.set_label("Infiltration (mm/år)", fontsize=12)

                # Add legend for binary classification shown in inset
                legend_handles_gvd = [
                    mpatches.Patch(color='#1a9850', label='Positiv (nedadgående)', alpha=0.8),
                    mpatches.Patch(color='#d73027', label='Negativ (opadgående)', alpha=0.8),
                    mpatches.Patch(facecolor='none', edgecolor='#111111', linewidth=1.5, label='Lokalitet'),
                ]
                ax_a_combined.legend(handles=legend_handles_gvd, loc='upper left', fontsize=11)

                if site_geom is not None and site_inset_bounds is not None:
                    window = rasterio.windows.from_bounds(
                        *site_inset_bounds, transform=src.transform
                    )
                    data_window = src.read(1, window=window, masked=True)
                    valid_window = (
                        data_window.compressed()
                        if np.ma.is_masked(data_window)
                        else data_window.ravel()
                    )
                    if valid_window.size > 0:
                        # Use binary classification for inset
                        cmap_w, norm_w = _gvd_binary_style()
                        axins = inset_axes(
                            ax_a_combined,
                            width="40%",
                            height="40%",
                            loc="lower right",
                            borderpad=1,
                        )
                        rasterio_show(
                            data_window,
                            transform=src.window_transform(window),
                            ax=axins,
                            cmap=cmap_w,
                            norm=norm_w,
                        )
                        gpd.GeoSeries([site_geom]).boundary.plot(
                            ax=axins, color="#111111", linewidth=1.5
                        )
                        axins.set_xlim(site_inset_bounds[0], site_inset_bounds[2])
                        axins.set_ylim(site_inset_bounds[1], site_inset_bounds[3])
                        axins.set_xticks([])
                        axins.set_yticks([])

                        mark_inset(
                            ax_a_combined,
                            axins,
                            loc1=2,
                            loc2=4,
                            fc="none",
                            ec="#666666",
                            lw=0.8,
                        )
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


def create_qpoint_illustration(output_path: Path = None, figsize: tuple = (14, 10)):
    """
    Create a visualization showing Q-point selection for a contaminated site.

    Shows:
    - A contaminated site with contact to multiple GVFKs
    - River segments (some with GVF contact, some without)
    - Q points color-coded:
      - Gray: Q points on segments without GVF contact to this site
      - Green: Q points on segments with GVF contact to this site
      - Yellow: The selected/used Q point for calculation
    """
    print("=" * 70)
    print("CREATING Q-POINT ILLUSTRATION")
    print("=" * 70)

    # Load data
    print("\n[PHASE 1] Loading data...")
    print("  Loading Q-points...")
    qpoints = gpd.read_file(RIVER_FLOW_POINTS_PATH, layer=RIVER_FLOW_POINTS_LAYER)
    print(f"    → {len(qpoints)} Q-points loaded")

    print("  Loading rivers...")
    rivers = gpd.read_file(RIVERS_PATH, layer=RIVERS_LAYER_NAME)
    river_gvfk_col = COLUMN_MAPPINGS["rivers"].get("gvfk_id")
    print(f"    → {len(rivers)} river segments loaded")

    print("  Loading GVFKs...")
    gvfk_polygons = gpd.read_file(GRUNDVAND_PATH, layer=GRUNDVAND_LAYER_NAME)
    print(f"    → {len(gvfk_polygons)} GVFK polygons loaded")

    print("  Loading V1/V2 sites...")
    v1_sites = gpd.read_file(V1_SHP_PATH)
    v2_sites = gpd.read_file(V2_SHP_PATH)
    all_sites = pd.concat([v1_sites, v2_sites], ignore_index=True)
    print(f"    → {len(all_sites)} total sites loaded")

    # Find a good example site
    print("\n[PHASE 2] Finding suitable example site...")
    # We need a site that:
    # 1. Overlaps with multiple GVFKs
    # 2. Has river segments with Q points nearby
    # 3. Has enough Q points in the area (10-15 total)

    # For each site, count overlapping GVFKs and nearby Q points
    best_site = None
    best_score = -1
    best_site_info = None

    for idx, site in all_sites.iterrows():
        if idx % 100 == 0:
            print(f"    Checking site {idx}/{len(all_sites)}...")

        geom = site.geometry
        if geom is None or geom.is_empty:
            continue

        # Find overlapping GVFKs
        overlapping_gvfks = gvfk_polygons[gvfk_polygons.intersects(geom)]
        if len(overlapping_gvfks) < 2:
            continue

        # Buffer site to find nearby Q points
        buffer_dist = 2000  # 2km buffer
        site_buffer = geom.buffer(buffer_dist)

        nearby_qpoints = qpoints[qpoints.geometry.within(site_buffer)]
        if len(nearby_qpoints) < 10:
            continue

        # Find rivers in the area
        nearby_rivers = rivers[rivers.geometry.intersects(site_buffer)]

        # Count rivers with and without GVF contact to this site
        gvfk_ids = set(overlapping_gvfks['GVForekom'].values)
        rivers_with_contact = nearby_rivers[nearby_rivers[river_gvfk_col].isin(gvfk_ids)]

        # Score: prefer sites with more Q points, multiple GVFKs, and good river coverage
        score = (
            len(nearby_qpoints) * 1.0 +
            len(overlapping_gvfks) * 5.0 +
            len(rivers_with_contact) * 2.0
        )

        if score > best_score:
            best_score = score
            best_site = site
            best_site_info = {
                'geometry': geom,
                'gvfks': overlapping_gvfks,
                'qpoints': nearby_qpoints,
                'rivers': nearby_rivers,
                'rivers_with_contact': rivers_with_contact,
                'buffer': site_buffer,
            }

    if best_site is None:
        print("  ERROR: Could not find a suitable example site!")
        return None

    print(f"  Found site with:")
    print(f"    - {len(best_site_info['gvfks'])} overlapping GVFKs")
    print(f"    - {len(best_site_info['qpoints'])} nearby Q-points")
    print(f"    - {len(best_site_info['rivers_with_contact'])} river segments with GVF contact")

    # Create visualization
    print("\n[PHASE 3] Creating visualization...")

    fig, ax = plt.subplots(1, 1, figsize=figsize, dpi=150)
    ax.set_title("Q-punkt udvælgelse for tilstandsvurdering", fontsize=16, fontweight='bold')

    # Plot GVFKs
    best_site_info['gvfks'].plot(ax=ax, color='#f0f0f0', edgecolor='#999999', linewidth=0.8, alpha=0.6)

    # Plot rivers
    # Rivers without contact: light gray
    rivers_no_contact = best_site_info['rivers'][
        ~best_site_info['rivers'][river_gvfk_col].isin(
            set(best_site_info['gvfks']['GVForekom'].values)
        )
    ]
    if not rivers_no_contact.empty:
        rivers_no_contact.plot(ax=ax, color='#cccccc', linewidth=1.5, alpha=0.5)

    # Rivers with contact: blue
    if not best_site_info['rivers_with_contact'].empty:
        best_site_info['rivers_with_contact'].plot(ax=ax, color='#3182bd', linewidth=2.0)

    # Plot site
    gpd.GeoSeries([best_site_info['geometry']]).plot(
        ax=ax, color='#d73027', edgecolor='#7f0000', linewidth=2, alpha=0.7
    )

    # Plot Q points
    # TODO: Implement Q point classification logic
    # For now, plot all Q points
    best_site_info['qpoints'].plot(ax=ax, color='gray', markersize=50, alpha=0.7)

    # Set bounds
    bounds = best_site_info['buffer'].bounds
    ax.set_xlim(bounds[0], bounds[2])
    ax.set_ylim(bounds[1], bounds[3])
    ax.set_xticks([])
    ax.set_yticks([])

    # Save
    if output_path is None:
        output_dir = get_visualization_path('workflow_summary')
    else:
        output_dir = output_path.parent
    output_dir.mkdir(parents=True, exist_ok=True)

    output_file = output_dir / 'qpoint_illustration.png'
    plt.tight_layout()
    plt.savefig(output_file, dpi=400, bbox_inches='tight', facecolor='white')
    plt.savefig(output_file.with_suffix('.pdf'), dpi=400, bbox_inches='tight', facecolor='white')
    print(f"\n  Saved: {output_file}")
    plt.close()

    print("\n" + "=" * 70)
    print("Q-POINT ILLUSTRATION COMPLETE!")
    print("=" * 70)

    return output_file


if __name__ == "__main__":
    create_3panel_overview()
    create_qpoint_illustration()
