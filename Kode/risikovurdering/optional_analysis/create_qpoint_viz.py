"""
Q-Point Selection Visualization

Creates a standalone visualization showing how Q-points are selected for a contaminated site.
Shows the spatial relationship between sites, GVFKs, river segments, and Q-points.
"""

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import geopandas as gpd
import pandas as pd
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
    get_visualization_path,
    RIVER_FLOW_POINTS_PATH,
    RIVER_FLOW_POINTS_LAYER,
    get_output_path,
)


def create_qpoint_illustration(output_path: Path = None, figsize: tuple = (14, 10)):
    """
    Create visualization showing Q-point selection for a contaminated site.
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
    river_ov_id_col = COLUMN_MAPPINGS["rivers"].get("river_id", "ov_id")
    print(f"    → {len(rivers)} river segments loaded")

    print("  Loading GVFKs...")
    gvfk_polygons = gpd.read_file(GRUNDVAND_PATH, layer=GRUNDVAND_LAYER_NAME)
    print(f"    → {len(gvfk_polygons)} GVFK polygons loaded")

    print("  Loading step3 results (site-GVFK combinations)...")
    step3_path = get_output_path("step3_v1v2_sites")

    if not step3_path.exists():
        print(f"  ERROR: Step3 results not found at {step3_path}")
        print("  Please run step3 first.")
        return None

    step3_sites = gpd.read_file(step3_path)
    print(f"    → {len(step3_sites)} site-GVFK combinations loaded")

    # Find suitable example site
    print("\n[PHASE 2] Finding suitable example site...")

    lokalitet_col = 'Lokalitet_'
    gvfk_col_step3 = 'Navn'

    # Group by lokalitet to find sites with multiple GVFKs
    sites_grouped = step3_sites.groupby(lokalitet_col).agg({
        gvfk_col_step3: lambda x: list(x.unique()),
        'geometry': 'first'
    }).reset_index()
    sites_grouped.columns = [lokalitet_col, 'gvfks', 'geometry']
    sites_grouped['gvfk_count'] = sites_grouped['gvfks'].apply(len)
    sites_grouped = gpd.GeoDataFrame(sites_grouped, geometry='geometry', crs=step3_sites.crs)

    # Filter to sites with multiple GVFKs
    multi_gvfk_sites = sites_grouped[sites_grouped['gvfk_count'] >= 2].copy()
    print(f"  Found {len(multi_gvfk_sites)} sites with 2+ GVFKs")

    if len(multi_gvfk_sites) == 0:
        print("  ERROR: No sites with multiple GVFKs found!")
        return None

    # Build spatial index
    print("  Building spatial index...")
    qpoints_sindex = qpoints.sindex

    # Find best site
    best_site_info = None
    best_score = -1

    for idx, site_row in multi_gvfk_sites.head(200).iterrows():  # Check first 200
        geom = site_row.geometry

        if geom is None or geom.is_empty:
            continue

        # 2km buffer
        buffer_dist = 2000
        site_buffer = geom.buffer(buffer_dist)

        # Fast Q-point lookup
        possible_idx = list(qpoints_sindex.intersection(site_buffer.bounds))
        nearby_qpoints = qpoints.iloc[possible_idx]
        nearby_qpoints = nearby_qpoints[nearby_qpoints.geometry.within(site_buffer)]

        if len(nearby_qpoints) < 10:
            continue

        # Get GVFKs and rivers
        gvfk_names = site_row['gvfks']
        overlapping_gvfks = gvfk_polygons[gvfk_polygons['GVForekom'].isin(gvfk_names)]
        nearby_rivers = rivers[rivers.geometry.intersects(site_buffer)]
        rivers_with_contact = nearby_rivers[nearby_rivers[river_gvfk_col].isin(gvfk_names)]

        score = len(nearby_qpoints) + len(overlapping_gvfks) * 5 + len(rivers_with_contact) * 2

        if score > best_score:
            best_score = score
            best_site_info = {
                'geometry': geom,
                'lokalitet_id': site_row[lokalitet_col],
                'gvfks': overlapping_gvfks,
                'gvfk_names': gvfk_names,
                'qpoints': nearby_qpoints,
                'rivers': nearby_rivers,
                'rivers_with_contact': rivers_with_contact,
                'buffer': site_buffer,
            }
            print(f"  New best: score={score:.1f}, {len(nearby_qpoints)} Q-points, {len(overlapping_gvfks)} GVFKs")

        if score > 50:
            break

    if best_site_info is None:
        print("  ERROR: Could not find suitable site!")
        return None

    print(f"\n  Selected site: {best_site_info['lokalitet_id']}")
    print(f"    GVFKs: {len(best_site_info['gvfks'])}")
    print(f"    Q-points: {len(best_site_info['qpoints'])}")
    print(f"    Rivers with contact: {len(best_site_info['rivers_with_contact'])}")

    # Classify Q-points
    print("\n[PHASE 3] Classifying Q-points...")

    # Get ov_ids of rivers with GVF contact
    contact_ov_ids = set(best_site_info['rivers_with_contact'][river_ov_id_col].dropna().astype(str))

    # Classify Q-points based on their ov_id
    qpoint_col = 'ov_id'  # Column linking Q-points to rivers

    qpoints_data = best_site_info['qpoints'].copy()
    qpoints_data['classification'] = 'gray'  # Default: not relevant

    if qpoint_col in qpoints_data.columns:
        # Green: Q-points on rivers with GVF contact
        qpoints_data.loc[
            qpoints_data[qpoint_col].astype(str).isin(contact_ov_ids),
            'classification'
        ] = 'green'

        # Yellow: Pick one as "selected" (e.g., first green one)
        green_qpoints = qpoints_data[qpoints_data['classification'] == 'green']
        if not green_qpoints.empty:
            selected_idx = green_qpoints.index[0]
            qpoints_data.loc[selected_idx, 'classification'] = 'yellow'

    gray_qpoints = qpoints_data[qpoints_data['classification'] == 'gray']
    green_qpoints = qpoints_data[qpoints_data['classification'] == 'green']
    yellow_qpoints = qpoints_data[qpoints_data['classification'] == 'yellow']

    print(f"    Gray Q-points: {len(gray_qpoints)}")
    print(f"    Green Q-points: {len(green_qpoints)}")
    print(f"    Yellow Q-points: {len(yellow_qpoints)}")

    # Create visualization
    print("\n[PHASE 4] Creating visualization...")

    fig, ax = plt.subplots(1, 1, figsize=figsize, dpi=150)
    ax.set_title("Q-punkt udvælgelse for tilstandsvurdering", fontsize=18, fontweight='bold')

    # Plot GVFKs
    best_site_info['gvfks'].plot(ax=ax, color='#e0e0e0', edgecolor='#666666', linewidth=1.0, alpha=0.4)

    # Plot rivers
    rivers_no_contact = best_site_info['rivers'][
        ~best_site_info['rivers'][river_ov_id_col].astype(str).isin(contact_ov_ids)
    ]
    if not rivers_no_contact.empty:
        rivers_no_contact.plot(ax=ax, color='#bdbdbd', linewidth=1.0, alpha=0.5, label='Vandløb uden GVF-kontakt')

    if not best_site_info['rivers_with_contact'].empty:
        best_site_info['rivers_with_contact'].plot(
            ax=ax, color='#2171b5', linewidth=2.5, label='Vandløb med GVF-kontakt'
        )

    # Plot site
    gpd.GeoSeries([best_site_info['geometry']]).plot(
        ax=ax, color='#d73027', edgecolor='#a50f15', linewidth=2.5, alpha=0.8, label='Forurenet lokalitet'
    )

    # Plot Q-points
    if not gray_qpoints.empty:
        gray_qpoints.plot(ax=ax, color='#969696', markersize=40, alpha=0.7, label='Q-punkter (ikke relevant)', zorder=3)
    if not green_qpoints.empty:
        green_qpoints.plot(ax=ax, color='#31a354', markersize=60, alpha=0.9, label='Q-punkter (relevant)', zorder=4)
    if not yellow_qpoints.empty:
        yellow_qpoints.plot(ax=ax, color='#ffff00', edgecolor='#ff8c00', linewidth=2, markersize=100, alpha=1.0, label='Valgt Q-punkt', zorder=5)

    # Set bounds
    bounds = best_site_info['buffer'].bounds
    ax.set_xlim(bounds[0], bounds[2])
    ax.set_ylim(bounds[1], bounds[3])
    ax.set_xticks([])
    ax.set_yticks([])

    # Legend
    ax.legend(loc='upper right', fontsize=11, framealpha=0.95)

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
    create_qpoint_illustration()
