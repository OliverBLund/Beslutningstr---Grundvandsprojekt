"""
Step 6 – Reporting Helpers
==========================

The functions in this module summarise the Step 6 outputs. The focus is on
transparent, easy-to-read console output rather than polished figures. Plotting
hooks can be added later once the numerical pipeline has been validated end-to-end.
"""

from __future__ import annotations

import sys
from pathlib import Path
import pandas as pd
import geopandas as gpd
import folium
from folium.plugins import FloatImage
import numpy as np
import rasterio
from rasterio.enums import Resampling
from shapely.geometry import box
import matplotlib.pyplot as plt
from matplotlib.colors import TwoSlopeNorm
from PIL import Image
from affine import Affine
from branca.colormap import LinearColormap

# Ensure repository root is importable
REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from Kode.config import (
    RIVERS_PATH,
    GVD_RASTER_DIR,
    GRUNDVAND_PATH,
    get_visualization_path,
    get_output_path,
)


def analyze_and_visualize_step6(
    site_flux: pd.DataFrame,
    segment_flux: pd.DataFrame,
    cmix_results: pd.DataFrame,
    segment_summary: pd.DataFrame,
    *,
    negative_infiltration: pd.DataFrame | None = None,
    site_geometries: gpd.GeoDataFrame | None = None,
) -> None:
    """Print compact diagnostics covering the main Step 6 deliverables."""

    print("\nSTEP 6: TILSTANDSVURDERING – SUMMARY")
    print("=" * 60)

    _print_site_level_overview(site_flux)
    _print_segment_overview(segment_flux)
    _print_cmix_overview(cmix_results)
    _print_segment_summary(segment_summary)

    print("=" * 60)
    print("End of Step 6 summary")
    print("=" * 60)

    # Create interactive maps
    print("\nGenerating interactive maps...")
    _create_interactive_maps(site_flux, cmix_results, segment_summary)

    # Diagnostics for negative infiltration removals
    _create_negative_infiltration_map(negative_infiltration, site_geometries)

    # Create combined impact map (sites + rivers + connection lines)
    print("\nGenerating combined impact maps...")
    try:
        from .step6_combined_map import create_combined_impact_maps
    except ImportError:
        from step6_combined_map import create_combined_impact_maps
    create_combined_impact_maps(site_flux, segment_summary)

    # Create analytical plots
    print("\nGenerating analytical plots...")
    try:
        from .step6_analytical_plots import create_analytical_plots
    except ImportError:
        from step6_analytical_plots import create_analytical_plots
    create_analytical_plots(site_flux, segment_flux, cmix_results, segment_summary)

    print("All visualizations saved to Resultater/Figures/step6/")


# ---------------------------------------------------------------------------
# Section printing helpers
# ---------------------------------------------------------------------------#

def _print_site_level_overview(site_flux: pd.DataFrame) -> None:
    print("\n1. Site-level flux calculations")
    print("-" * 60)

    if site_flux.empty:
        print("No site combinations were available after preprocessing.")
        return

    unique_sites = site_flux["Lokalitet_ID"].nunique()
    unique_segments = site_flux["Nearest_River_ov_id"].nunique()
    unique_categories = site_flux["Qualifying_Category"].nunique()

    print(f"Rows processed: {len(site_flux):,}")
    print(f"Unique sites: {unique_sites:,}")
    print(f"Unique river segments (nearest): {unique_segments:,}")
    print(f"Contamination categories: {unique_categories:,}")

    flux_stats = site_flux["Pollution_Flux_kg_per_year"].describe()
    print(
        "Flux (kg/year) – min/median/mean/max: "
        f"{flux_stats['min']:.2e} / {flux_stats['50%']:.2e} / "
        f"{flux_stats['mean']:.2e} / {flux_stats['max']:.2e}"
    )


def _print_segment_overview(segment_flux: pd.DataFrame) -> None:
    print("\n2. Segment-level aggregation")
    print("-" * 60)

    if segment_flux.empty:
        print("No aggregated segment rows were produced.")
        return

    print(f"Segment-substance combinations: {len(segment_flux):,}")
    print(
        f"Segments represented: {segment_flux['Nearest_River_ov_id'].nunique():,} "
        f"(categories: {segment_flux['Qualifying_Category'].nunique():,})"
    )

    top_segments = (
        segment_flux.sort_values("Total_Flux_kg_per_year", ascending=False)
        .head(5)[
            [
                "Nearest_River_ov_id",
                "River_Segment_Name",
                "Qualifying_Substance",
                "Total_Flux_kg_per_year",
                "Contributing_Site_Count",
            ]
        ]
    )

    if not top_segments.empty:
        print("\nTop 5 segment/substance fluxes (kg/year):")
        for _, row in top_segments.iterrows():
            print(
                f"  {row['Nearest_River_ov_id']} ({row['River_Segment_Name']}), "
                f"{row['Qualifying_Substance']}: {row['Total_Flux_kg_per_year']:.2e} kg/yr "
                f"(sites: {row['Contributing_Site_Count']})"
            )


def _print_cmix_overview(cmix_results: pd.DataFrame) -> None:
    print("\n3. Cmix scenarios")
    print("-" * 60)

    if cmix_results.empty:
        print("Flow data not available or no segments retained; Cmix not computed.")
        return

    total_rows = len(cmix_results)
    with_flow = cmix_results["Has_Flow_Data"].sum()

    print(f"Scenario rows: {total_rows:,} (with discharge data: {with_flow:,})")
    scenarios = [str(s) for s in cmix_results['Flow_Scenario'].dropna().unique()]
    print(f"Scenarios considered: {', '.join(sorted(scenarios))}")

    available = cmix_results[cmix_results["Has_Flow_Data"]]
    if available.empty:
        print("All scenario rows are missing flow values – nothing further to report.")
        return

    worst = (
        available.sort_values("Cmix_ug_L", ascending=False)
        .head(5)[
            [
                "Nearest_River_ov_id",
                "River_Segment_Name",
                "Qualifying_Substance",
                "Flow_Scenario",
                "Cmix_ug_L",
            ]
        ]
    )

    print("\nTop 5 Cmix values (µg/L):")
    for _, row in worst.iterrows():
        print(
            f"  {row['Nearest_River_ov_id']} ({row['River_Segment_Name']}), "
            f"{row['Qualifying_Substance']} @ {row['Flow_Scenario']}: "
            f"{row['Cmix_ug_L']:.2f} µg/L"
        )

    if "Exceedance_Flag" in available.columns:
        exceedances = available[available["Exceedance_Flag"]]
        count = len(exceedances)
        print(f"\nExceedances flagged (where MKK data available): {count:,}")
        if count:
            for _, row in exceedances.sort_values("Exceedance_Ratio", ascending=False).head(5).iterrows():
                print(
                    f"  {row['Nearest_River_ov_id']} - {row['Qualifying_Substance']} "
                    f"({row['Flow_Scenario']}): {row['Exceedance_Ratio']:.2f}× MKK"
                )


def _print_segment_summary(segment_summary: pd.DataFrame) -> None:
    print("\n4. Segment summary overview")
    print("-" * 60)

    if segment_summary.empty:
        print("No segment summary rows were generated.")
        return

    print(f"Segments in summary: {len(segment_summary):,}")

    failing = segment_summary[
        segment_summary["Max_Exceedance_Ratio"].notna()
        & (segment_summary["Max_Exceedance_Ratio"] > 1)
    ]

    print(f"Segments exceeding MKK in any scenario: {len(failing):,}")
    if not failing.empty:
        for _, row in failing.sort_values("Max_Exceedance_Ratio", ascending=False).head(5).iterrows():
            print(
                f"  {row['Nearest_River_ov_id']} ({row['River_Segment_Name']}): "
                f"{row['Max_Exceedance_Ratio']:.2f}× MKK "
                f"(scenarios: {row['Failing_Scenarios'] or 'n/a'})"
            )


# ---------------------------------------------------------------------------
# Interactive Map Creation
# ---------------------------------------------------------------------------

def _create_interactive_maps(
    site_flux: pd.DataFrame,
    cmix_results: pd.DataFrame,
    segment_summary: pd.DataFrame
) -> None:
    """Generate interactive HTML maps for Step 6 results."""

    # Create output directory
    map_dir = get_visualization_path("step6")

    # Map 1: Overall exceedance map (worst case across all substances)
    _create_overall_exceedance_map(segment_summary, map_dir)

    # Map 2: Substance-specific exceedance map with dropdown
    _create_substance_exceedance_map(cmix_results, map_dir)

    # Map 3: Contamination sites with flux
    _create_site_flux_map(site_flux, map_dir)


def _create_overall_exceedance_map(segment_summary: pd.DataFrame, output_dir: Path) -> None:
    """Create map showing worst-case MKK exceedance per river segment."""

    print("  Creating overall exceedance map...")

    # Load river shapefile
    rivers = gpd.read_file(RIVERS_PATH, encoding='utf-8')

    # Convert to WGS84 for web mapping
    rivers_web = rivers.to_crs('EPSG:4326')

    # Join with segment summary
    rivers_enriched = rivers_web.merge(
        segment_summary,
        left_on="ov_id",
        right_on="Nearest_River_ov_id",
        how="left"
    )

    # Get map center
    bounds = rivers_web.total_bounds
    center_lat = (bounds[1] + bounds[3]) / 2
    center_lon = (bounds[0] + bounds[2]) / 2

    # Create map
    m = folium.Map(
        location=[center_lat, center_lon],
        zoom_start=8,
        tiles='OpenStreetMap'
    )

    # Add river segments
    for idx, row in rivers_enriched.iterrows():
        color, weight = _get_segment_style(row.get('Max_Exceedance_Ratio'), row.get('Total_Flux_kg_per_year'))
        popup_html = _create_overall_popup(row)

        folium.GeoJson(
            row.geometry,
            style_function=lambda x, c=color, w=weight: {
                'color': c,
                'weight': w,
                'opacity': 0.8
            },
            popup=folium.Popup(popup_html, max_width=300)
        ).add_to(m)

    # Add legend
    _add_exceedance_legend(m)

    # Save
    output_path = output_dir / "river_segments_overall_exceedance.html"
    m.save(str(output_path))
    print(f"    Saved: {output_path}")


def _create_substance_exceedance_map(cmix_results: pd.DataFrame, output_dir: Path) -> None:
    """Create map with dropdown to select specific substance/category."""

    print("  Creating substance-specific exceedance map...")

    # Load river shapefile
    rivers = gpd.read_file(RIVERS_PATH, encoding='utf-8')
    rivers_web = rivers.to_crs('EPSG:4326')

    # Get unique substances/categories
    substances = sorted(cmix_results['Qualifying_Substance'].dropna().unique())

    # Use Q95 scenario (most conservative)
    cmix_q95 = cmix_results[cmix_results['Flow_Scenario'] == 'Q95'].copy()

    # Get map center
    bounds = rivers_web.total_bounds
    center_lat = (bounds[1] + bounds[3]) / 2
    center_lon = (bounds[0] + bounds[2]) / 2

    # Create base map
    m = folium.Map(
        location=[center_lat, center_lon],
        zoom_start=8,
        tiles='OpenStreetMap'
    )

    # Create layer for each substance
    for substance in substances[:10]:  # Limit to top 10 to avoid too many layers
        substance_data = cmix_q95[cmix_q95['Qualifying_Substance'] == substance]

        rivers_enriched = rivers_web.merge(
            substance_data,
            left_on="ov_id",
            right_on="Nearest_River_ov_id",
            how="left"
        )

        feature_group = folium.FeatureGroup(name=substance, show=False)

        for idx, row in rivers_enriched.iterrows():
            if pd.notna(row.get('Exceedance_Ratio')):
                color, weight = _get_segment_style(row.get('Exceedance_Ratio'), row.get('Total_Flux_kg_per_year'))
                popup_html = _create_substance_popup(row, substance)

                folium.GeoJson(
                    row.geometry,
                    style_function=lambda x, c=color, w=weight: {
                        'color': c,
                        'weight': w,
                        'opacity': 0.8
                    },
                    popup=folium.Popup(popup_html, max_width=300)
                ).add_to(feature_group)

        feature_group.add_to(m)

    # Add layer control
    folium.LayerControl(collapsed=False).add_to(m)

    # Add legend
    _add_exceedance_legend(m)

    # Save
    output_path = output_dir / "river_segments_by_substance.html"
    m.save(str(output_path))
    print(f"    Saved: {output_path}")


def _create_site_flux_map(site_flux: pd.DataFrame, output_dir: Path) -> None:
    """Create map showing contamination sites as polygons colored by flux."""

    print("  Creating site flux map...")

    # Load site geometries
    sites_gdf = gpd.read_file(get_output_path("step3_v1v2_sites"), encoding='utf-8')
    sites_web = sites_gdf.to_crs('EPSG:4326')

    # Aggregate flux by site (sum across all substances)
    site_totals = site_flux.groupby('Lokalitet_ID').agg({
        'Pollution_Flux_kg_per_year': 'sum',
        'Qualifying_Category': lambda x: ', '.join(x.unique()[:3]),  # Top 3 categories
        'Lokalitetsnavn': 'first',
        'Nearest_River_ov_navn': 'first',
        'Distance_to_River_m': 'first'
    }).reset_index()

    # Join with geometries (Step 3 shapefile uses 'Lokalitet_' not 'Lokalitet_ID')
    sites_enriched = sites_web.merge(
        site_totals,
        left_on='Lokalitet_',
        right_on='Lokalitet_ID',
        how='inner'
    )

    # Get map center
    bounds = sites_enriched.total_bounds
    center_lat = (bounds[1] + bounds[3]) / 2
    center_lon = (bounds[0] + bounds[2]) / 2

    # Create map
    m = folium.Map(
        location=[center_lat, center_lon],
        zoom_start=8,
        tiles='OpenStreetMap'
    )

    # Add site polygons
    for idx, row in sites_enriched.iterrows():
        color = _get_flux_color(row['Pollution_Flux_kg_per_year'])
        popup_html = _create_site_popup(row)

        folium.GeoJson(
            row.geometry,
            style_function=lambda x, c=color: {
                'fillColor': c,
                'color': 'black',
                'weight': 1,
                'fillOpacity': 0.6
            },
            popup=folium.Popup(popup_html, max_width=300)
        ).add_to(m)

    # Add flux legend
    _add_flux_legend(m)

    # Save
    output_path = output_dir / "contamination_sites_flux.html"
    m.save(str(output_path))
    print(f"    Saved: {output_path}")


# ---------------------------------------------------------------------------
# Helper functions for styling and popups
# ---------------------------------------------------------------------------

def _get_segment_style(exceedance_ratio, flux_kg_per_year):
    """Determine color and line weight for river segment."""

    # Determine color based on exceedance
    if pd.isna(exceedance_ratio):
        color = 'gray'
    elif exceedance_ratio < 1:
        color = 'green'
    elif exceedance_ratio < 10:
        color = 'yellow'
    elif exceedance_ratio < 100:
        color = 'orange'
    else:
        color = 'red'

    # Determine line weight based on flux (log scale)
    if pd.isna(flux_kg_per_year) or flux_kg_per_year <= 0:
        weight = 2
    else:
        weight = min(10, 2 + np.log10(max(0.01, flux_kg_per_year)))

    return color, weight


def _get_flux_color(flux_kg_per_year):
    """Determine color for site based on flux."""
    if pd.isna(flux_kg_per_year) or flux_kg_per_year <= 0:
        return 'lightgray'
    elif flux_kg_per_year < 1:
        return 'lightgreen'
    elif flux_kg_per_year < 10:
        return 'yellow'
    elif flux_kg_per_year < 100:
        return 'orange'
    else:
        return 'red'


def _create_overall_popup(row):
    """Create popup HTML for overall exceedance map."""
    exceedance = row.get('Max_Exceedance_Ratio', 'N/A')
    flux = row.get('Total_Flux_kg_per_year', 'N/A')

    return f"""
    <b>River Segment</b><br>
    <b>Name:</b> {row.get('ov_navn', 'Unknown')}<br>
    <b>ID:</b> {row.get('ov_id', 'Unknown')}<br>
    <b>GVFK:</b> {row.get('River_Segment_GVFK', 'N/A')}<br>
    <b>Max Exceedance:</b> {f'{exceedance:.1f}x MKK' if pd.notna(exceedance) else 'No data'}<br>
    <b>Total Flux:</b> {f'{flux:.2f} kg/year' if pd.notna(flux) else 'N/A'}<br>
    <b>Contributing Sites:</b> {row.get('Contributing_Site_Count', 'N/A')}<br>
    <b>Failing Scenarios:</b> {row.get('Failing_Scenarios', 'None')}
    """


def _create_substance_popup(row, substance):
    """Create popup HTML for substance-specific map."""
    exceedance = row.get('Exceedance_Ratio', 'N/A')
    flux = row.get('Total_Flux_kg_per_year', 'N/A')
    cmix = row.get('Cmix_ug_L', 'N/A')

    return f"""
    <b>River Segment - {substance}</b><br>
    <b>Name:</b> {row.get('ov_navn', 'Unknown')}<br>
    <b>ID:</b> {row.get('ov_id', 'Unknown')}<br>
    <b>Exceedance:</b> {f'{exceedance:.1f}x MKK' if pd.notna(exceedance) else 'Below MKK'}<br>
    <b>Cmix:</b> {f'{cmix:.2f} ug/L' if pd.notna(cmix) else 'N/A'}<br>
    <b>Flux:</b> {f'{flux:.2f} kg/year' if pd.notna(flux) else 'N/A'}<br>
    <b>Sites:</b> {row.get('Contributing_Site_Count', 'N/A')}
    """


def _create_site_popup(row):
    """Create popup HTML for site flux map."""
    return f"""
    <b>Contamination Site</b><br>
    <b>ID:</b> {row['Lokalitet_ID']}<br>
    <b>Name:</b> {row.get('Lokalitetsnavn', 'Unknown')}<br>
    <b>Total Flux:</b> {row['Pollution_Flux_kg_per_year']:.2f} kg/year<br>
    <b>Categories:</b> {row['Qualifying_Category']}<br>
    <b>Nearest River:</b> {row['Nearest_River_ov_navn']}<br>
    <b>Distance:</b> {row['Distance_to_River_m']:.0f} m
    """


# ---------------------------------------------------------------------------
# Negative infiltration diagnostics
# ---------------------------------------------------------------------------

def _create_negative_infiltration_map(
    negative_df: pd.DataFrame | None,
    site_geometries: gpd.GeoDataFrame | None,
) -> None:
    """Generate validation map with layer-specific site filtering and raster overlays."""
    print("\nPreparing negative infiltration validation map...")

    if negative_df is None or negative_df.empty:
        print("  No negative infiltration combinations detected – skipping map.")
        return

    if site_geometries is None or site_geometries.empty:
        print("  Site geometries unavailable – cannot map negative infiltration rows.")
        return

    geometry_df = site_geometries.rename(columns={"Lokalitet_": "Lokalitet_ID"})[
        ["Lokalitet_ID", "geometry"]
    ]
    joined = negative_df.merge(geometry_df, on="Lokalitet_ID", how="left")
    joined = joined.dropna(subset=["geometry"])
    if joined.empty:
        print("  Negative infiltration rows are missing site geometries; skipping map.")
        return

    neg_gdf_proj = gpd.GeoDataFrame(joined, geometry="geometry", crs=site_geometries.crs)
    if neg_gdf_proj.crs is None:
        print("  Site geometry CRS undefined; cannot create validation map.")
        return

    neg_gdf = neg_gdf_proj.to_crs(epsg=4326)
    neg_gdf["Display_Infiltration_mm_per_year"] = pd.to_numeric(
        neg_gdf["Infiltration_mm_per_year"], errors="coerce"
    )

    bounds = neg_gdf.total_bounds
    if np.any(~np.isfinite(bounds)):
        print("  Invalid geometry bounds; skipping negative infiltration map.")
        return

    center_lat = (bounds[1] + bounds[3]) / 2
    center_lon = (bounds[0] + bounds[2]) / 2

    # Use dark basemap for better raster visibility
    fmap = folium.Map(
        location=[center_lat, center_lon],
        zoom_start=7,
        tiles="CartoDB dark_matter",
        control_scale=True,
    )

    valid_vals = neg_gdf["Display_Infiltration_mm_per_year"].dropna()
    if valid_vals.empty:
        print("  No valid infiltration values to visualize.")
        return

    vmin = float(valid_vals.min())
    vmax = float(valid_vals.max())
    if vmax > 0:
        vmax = 0.0

    # Blue color scale for negative infiltration
    color_scale = LinearColormap(
        colors=["#08519c", "#3182bd", "#9ecae1"],
        vmin=vmin,
        vmax=vmax,
    )
    color_scale.caption = "Infiltration (mm/år) – negative values"

    # Orange color for multi-layer sites
    multi_layer_color = "#ff7f00"

    def create_style_fn(is_multi_layer=False):
        """Create style function for single or multi-layer sites."""
        def style_fn(feature: dict) -> dict:
            if is_multi_layer:
                return {
                    "fillColor": multi_layer_color,
                    "color": "#000000",
                    "weight": 1,
                    "fillOpacity": 0.7,
                }
            else:
                value = feature["properties"].get("Display_Infiltration_mm_per_year", 0) or 0
                return {
                    "fillColor": color_scale(value),
                    "color": "#000000",
                    "weight": 0.5,
                    "fillOpacity": 0.7,
                }
        return style_fn

    # Extract all unique layers from the data
    all_layers = set()
    for layers_str in neg_gdf["Sampled_Layers"].dropna():
        for layer in str(layers_str).split(","):
            layer = layer.strip()
            if layer:
                all_layers.add(layer)

    all_layers = sorted(all_layers)
    print(f"  Found {len(all_layers)} unique modellags: {', '.join(all_layers)}")

    # Categorize sites: single-layer vs multi-layer
    neg_gdf["Is_Multi_Layer"] = neg_gdf["Sampled_Layers"].str.contains(",", na=False)

    single_layer_sites = neg_gdf[~neg_gdf["Is_Multi_Layer"]].copy()
    multi_layer_sites = neg_gdf[neg_gdf["Is_Multi_Layer"]].copy()

    output_dir = get_visualization_path("step6", "negative_infiltration")

    # Create layer groups for each modellag (single-layer sites only)
    for layer in all_layers:
        # Filter sites that have ONLY this layer
        layer_sites = single_layer_sites[
            single_layer_sites["Sampled_Layers"].str.strip() == layer
        ].copy()

        if layer_sites.empty:
            continue

        print(f"  Creating layer group for {layer}: {len(layer_sites)} sites")

        # Create feature group for this layer
        feature_group = folium.FeatureGroup(name=f"GVD {layer}", show=False)

        # Add raster overlay for this layer
        _add_raster_overlay_for_layer(layer, feature_group, output_dir, neg_gdf_proj.crs)

        # Add sites for this layer
        tooltip = folium.features.GeoJsonTooltip(
            fields=[
                "Lokalitet_ID",
                "GVFK",
                "Infiltration_mm_per_year",
            ],
            aliases=[
                "Lokalitet ID",
                "GVFK",
                "Infiltration (mm/år)",
            ],
            sticky=True,
        )

        popup = folium.features.GeoJsonPopup(
            fields=[
                "Lokalitet_ID",
                "GVFK",
                "Sampled_Layers",
                "Infiltration_mm_per_year",
                "Centroid_Infiltration_mm_per_year",
                "Polygon_Infiltration_mm_per_year",
                "Qualifying_Category",
                "Qualifying_Substance",
            ],
            aliases=[
                "Lokalitet ID",
                "GVFK",
                "Modellag",
                "Infiltration (mm/år)",
                "Centroid infiltration",
                "Polygon infiltration",
                "Forureningskategori",
                "Stof",
            ],
            labels=True,
            max_width=300,
        )

        folium.GeoJson(
            layer_sites[
                [
                    "Lokalitet_ID",
                    "GVFK",
                    "Sampled_Layers",
                    "Infiltration_mm_per_year",
                    "Display_Infiltration_mm_per_year",
                    "Centroid_Infiltration_mm_per_year",
                    "Polygon_Infiltration_mm_per_year",
                    "Qualifying_Category",
                    "Qualifying_Substance",
                    "geometry",
                ]
            ],
            style_function=create_style_fn(is_multi_layer=False),
            tooltip=tooltip,
            popup=popup,
        ).add_to(feature_group)

        # Add centroid markers for easy identification
        for idx, row in layer_sites.iterrows():
            centroid = row.geometry.centroid
            infiltration = row.get("Display_Infiltration_mm_per_year", 0) or 0
            marker_color = color_scale(infiltration) if infiltration else "#08519c"

            folium.CircleMarker(
                location=[centroid.y, centroid.x],
                radius=4,
                color="#000000",
                weight=1,
                fill=True,
                fillColor=marker_color,
                fillOpacity=0.9,
                tooltip=f"Site {row['Lokalitet_ID']}: {infiltration:.1f} mm/år",
            ).add_to(feature_group)

        feature_group.add_to(fmap)

    # Create multi-layer group
    if not multi_layer_sites.empty:
        print(f"  Creating multi-layer group: {len(multi_layer_sites)} sites")

        multi_feature_group = folium.FeatureGroup(name="Multiple Layers", show=False)

        tooltip = folium.features.GeoJsonTooltip(
            fields=[
                "Lokalitet_ID",
                "GVFK",
                "Sampled_Layers",
                "Infiltration_mm_per_year",
            ],
            aliases=[
                "Lokalitet ID",
                "GVFK",
                "Modellag (multiple)",
                "Infiltration (mm/år)",
            ],
            sticky=True,
        )

        popup = folium.features.GeoJsonPopup(
            fields=[
                "Lokalitet_ID",
                "GVFK",
                "Sampled_Layers",
                "Infiltration_mm_per_year",
                "Centroid_Infiltration_mm_per_year",
                "Polygon_Infiltration_mm_per_year",
                "Qualifying_Category",
                "Qualifying_Substance",
            ],
            aliases=[
                "Lokalitet ID",
                "GVFK",
                "Modellag (multiple)",
                "Infiltration (mm/år)",
                "Centroid infiltration",
                "Polygon infiltration",
                "Forureningskategori",
                "Stof",
            ],
            labels=True,
            max_width=300,
        )

        folium.GeoJson(
            multi_layer_sites[
                [
                    "Lokalitet_ID",
                    "GVFK",
                    "Sampled_Layers",
                    "Infiltration_mm_per_year",
                    "Display_Infiltration_mm_per_year",
                    "Centroid_Infiltration_mm_per_year",
                    "Polygon_Infiltration_mm_per_year",
                    "Qualifying_Category",
                    "Qualifying_Substance",
                    "geometry",
                ]
            ],
            style_function=create_style_fn(is_multi_layer=True),
            tooltip=tooltip,
            popup=popup,
        ).add_to(multi_feature_group)

        # Add centroid markers for multi-layer sites
        for idx, row in multi_layer_sites.iterrows():
            centroid = row.geometry.centroid

            folium.CircleMarker(
                location=[centroid.y, centroid.x],
                radius=5,
                color="#000000",
                weight=1,
                fill=True,
                fillColor=multi_layer_color,
                fillOpacity=0.9,
                tooltip=f"Site {row['Lokalitet_ID']} (Multi-layer: {row['Sampled_Layers']})",
            ).add_to(multi_feature_group)

        multi_feature_group.add_to(fmap)

    # Add GVFK boundaries for reference
    _overlay_gvfk_boundaries(negative_df, fmap)

    # Summary statistics box
    gvfk_summary = (
        negative_df.groupby("GVFK")["Lokalitet_ID"]
        .nunique()
        .reset_index()
        .rename(columns={"Lokalitet_ID": "Site_Count"})
        .sort_values("Site_Count", ascending=False)
    )

    total_sites = negative_df["Lokalitet_ID"].nunique()
    total_rows = len(negative_df)
    single_layer_count = single_layer_sites["Lokalitet_ID"].nunique()
    multi_layer_count = multi_layer_sites["Lokalitet_ID"].nunique()

    summary_html = f"""
    <div style="position: fixed; top: 10px; left: 10px;
                background-color: rgba(255, 255, 255, 0.95); padding: 12px;
                border: 2px solid #333; border-radius: 5px;
                max-height: 400px; max-width: 280px; overflow: auto; z-index: 1000;
                box-shadow: 0 0 15px rgba(0,0,0,0.5); font-size: 11px;">
      <h4 style="margin-top:0; font-size: 14px; font-weight: bold;">Validation Map - Negative Infiltration</h4>
      <p style="margin: 3px 0;"><strong>Total sites removed:</strong> {total_sites}</p>
      <p style="margin: 3px 0;"><strong>Total rows removed:</strong> {total_rows:,}</p>
      <p style="margin: 3px 0;"><strong>GVFK affected:</strong> {len(gvfk_summary)}</p>
      <hr style="margin: 8px 0;">
      <p style="margin: 3px 0;"><strong>By layer type:</strong></p>
      <p style="margin: 3px 0; padding-left: 10px;">Single-layer: {single_layer_count}</p>
      <p style="margin: 3px 0; padding-left: 10px;"><span style="color: {multi_layer_color};">●</span> Multi-layer: {multi_layer_count}</p>
      <hr style="margin: 8px 0;">
      <p style="margin: 3px 0; font-size: 11px;"><strong>Site Polygon Legend:</strong></p>
      <p style="margin: 3px 0; font-size: 10px;">
        <span style="color: #08519c; font-size: 16px;">●</span> Dark blue = Most negative infiltration<br>
        <span style="color: #9ecae1; font-size: 16px;">●</span> Light blue = Near zero infiltration<br>
        <span style="color: {multi_layer_color}; font-size: 16px;">●</span> Orange = Multiple modellags
      </p>
      <hr style="margin: 8px 0;">
      <p style="margin: 3px 0; font-size: 11px;"><strong>Raster Legend (GVD layers):</strong></p>
      <p style="margin: 3px 0; font-size: 10px;">
        <span style="color: #d73027; font-size: 16px;">●</span> <strong>RED = NEGATIVE</strong> (discharge zones)<br>
        <span style="color: #f7f7f7; font-size: 16px;">●</span> White = Zero infiltration<br>
        <span style="color: #4575b4; font-size: 16px;">●</span> <strong>BLUE = POSITIVE</strong> (recharge zones)
      </p>
      <hr style="margin: 8px 0;">
      <p style="margin: 3px 0; font-size: 10px; font-weight: bold; color: #d73027;">
        ⚠ VALIDATION CHECK:<br>
        Removed sites should be on RED areas!
      </p>
      <hr style="margin: 8px 0;">
      <p style="margin: 3px 0; font-size: 9px; color: #666;">
        <em>Use layer control (top-right) to toggle modellags.<br>
        If site polygons overlap BLUE areas → potential bug!</em>
      </p>
    </div>
    """

    fmap.get_root().html.add_child(folium.Element(summary_html))

    # Add larger colorbar legend for site polygons at bottom
    color_scale.caption = "Site Polygon Infiltration (mm/år)"
    color_scale.add_to(fmap)

    # Add layer control
    folium.LayerControl(collapsed=False).add_to(fmap)

    # Save outputs
    map_path = output_dir / "step6_negative_infiltration_validation_map.html"
    fmap.save(map_path)

    geojson_path = output_dir / "step6_negative_infiltration_sites.geojson"
    neg_gdf.to_file(geojson_path, driver="GeoJSON")

    summary_path = output_dir / "step6_negative_infiltration_summary.csv"
    gvfk_summary.to_csv(summary_path, index=False)

    _export_negative_infiltration_stats(neg_gdf_proj, output_dir)

    # PROGRAMMATIC VERIFICATION: Check if filtered sites actually have negative infiltration
    print("\n" + "="*60)
    print("PROGRAMMATIC VERIFICATION OF NEGATIVE INFILTRATION")
    print("="*60)
    _verify_negative_infiltration_sites(neg_gdf_proj, output_dir)

    print("  Validation map saved to:", map_path)
    print("  Site GeoJSON saved to:", geojson_path)
    print("  Summary CSV saved to:", summary_path)


def _overlay_gvfk_boundaries(negative_df: pd.DataFrame, fmap: folium.Map) -> None:
    """Add reference GVFK polygons as transparent boundaries."""
    gvfk_ids = sorted(negative_df["GVFK"].dropna().unique())
    if not gvfk_ids:
        return

    candidate_paths = [
        get_output_path("step3_gvfk_polygons"),
        Path(GRUNDVAND_PATH),
    ]
    source_path = None
    for path in candidate_paths:
        path = Path(path)
        if path.exists():
            source_path = path
            break

    if source_path is None:
        print("  GVFK polygon source not found – skipping boundary overlay.")
        return

    gvfk_geo = gpd.read_file(source_path)
    id_column = None
    normalized_cols = {col.lower(): col for col in gvfk_geo.columns}
    preferred_keys = [
        "gvfk",
        "gvforekom",
        "gv_forekom",
        "gv_fk",
        "id",
    ]
    for key in preferred_keys:
        if key in normalized_cols:
            id_column = normalized_cols[key]
            break
    if id_column is None:
        for lower, original in normalized_cols.items():
            if "gvfk" in lower or "gvfore" in lower:
                id_column = original
                break

    if id_column is None:
        print(
            "  GVFK polygon file missing identifier column; available columns: "
            + ", ".join(gvfk_geo.columns)
        )
        return

    subset = gvfk_geo[gvfk_geo[id_column].isin(gvfk_ids)]
    if subset.empty:
        print("  GVFK polygons not found for removed IDs; skipping overlay.")
        return

    subset = subset.to_crs(epsg=4326)
    folium.GeoJson(
        subset[[id_column, "geometry"]],
        name="Grundvandsforekomster (GVFK)",
        style_function=lambda _: {
            "fillOpacity": 0,
            "color": "#2c7bb6",
            "weight": 2,
            "dashArray": "5, 5",
        },
        tooltip=folium.GeoJsonTooltip(fields=[id_column], aliases=["GVFK"]),
    ).add_to(fmap)


def _normalize_layer_name(layer: str) -> str:
    """Normalize layer name for raster file lookup."""
    text = layer.strip()
    if text.lower().startswith("lag"):
        return "lay12"
    return text


def _add_raster_overlay_for_layer(
    layer: str,
    feature_group: folium.FeatureGroup,
    output_dir: Path,
    source_crs,
) -> bool:
    """Add GVD raster overlay for the specified modellag to the feature group."""
    normalized_layer = _normalize_layer_name(layer)
    raster_path = Path(GVD_RASTER_DIR) / f"DKM_gvd_{normalized_layer}.tif"

    if not raster_path.exists():
        print(f"    Warning: Raster not found for {layer} ({raster_path.name})")
        return False

    try:
        with rasterio.open(raster_path) as src:
            # DEBUG: Print CRS information
            print(f"      Raster CRS: {src.crs}")
            print(f"      Raster bounds (native): {src.bounds}")

            # Downsample for web performance
            height, width = src.height, src.width
            max_dim = 2000
            scale = min(1.0, max_dim / height, max_dim / width)
            out_height = max(1, int(height * scale))
            out_width = max(1, int(width * scale))

            data = src.read(
                1,
                out_shape=(out_height, out_width),
                resampling=Resampling.average,
            )

            transform = src.transform * Affine.scale(width / out_width, height / out_height)
            bounds = (
                transform.c,
                transform.f + out_height * transform.e,
                transform.c + out_width * transform.a,
                transform.f,
            )

            # Handle nodata
            nodata_mask = np.zeros_like(data, dtype=bool)
            if src.nodata is not None:
                nodata_mask |= data == src.nodata
            nodata_mask |= ~np.isfinite(data)

            if nodata_mask.all():
                print(f"    Warning: All nodata for {layer}")
                return False

            # Calculate value range for all valid data
            valid = data[~nodata_mask]

            # Print comprehensive diagnostics
            print(f"    Raster {layer} full stats:")
            print(f"      All values: min={valid.min():.1f}, max={valid.max():.1f}, mean={valid.mean():.1f} mm/år")

            negative_count = (valid < 0).sum()
            positive_count = (valid >= 0).sum()
            print(f"      Negative pixels: {negative_count:,} ({100*negative_count/len(valid):.1f}%)")
            print(f"      Positive pixels: {positive_count:,} ({100*positive_count/len(valid):.1f}%)")

            if negative_count > 0:
                negative_vals = valid[valid < 0]
                print(f"      Negative range: {negative_vals.min():.1f} to {negative_vals.max():.1f} mm/år")

            if positive_count > 0:
                positive_vals = valid[valid >= 0]
                print(f"      Positive range: {positive_vals.min():.1f} to {positive_vals.max():.1f} mm/år")

            # Use diverging colormap centered at 0
            # Red = negative (discharge), Blue/Green = positive (recharge)
            vmin = float(valid.min())
            vmax = float(valid.max())

            # Use percentile-based clipping to handle extreme outliers
            # This prevents extreme values from washing out the color scale
            vmin_p = np.percentile(valid, 1)  # 1st percentile
            vmax_p = np.percentile(valid, 99)  # 99th percentile

            print(f"      Percentile range (1-99%): {vmin_p:.1f} to {vmax_p:.1f} mm/år")
            print(f"      Using this range for colormap to avoid extreme outlier washing")

            # Make symmetric around zero using percentiles
            abs_max_p = max(abs(vmin_p), abs(vmax_p))
            vmin_sym = -abs_max_p
            vmax_sym = abs_max_p

            # Create normalized data using TwoSlopeNorm centered at 0
            from matplotlib.colors import TwoSlopeNorm
            norm = TwoSlopeNorm(vmin=vmin_sym, vcenter=0, vmax=vmax_sym)

            # Clip data to percentile range, then normalize
            data_clipped = np.clip(data, vmin_sym, vmax_sym)
            normalized = norm(data_clipped)
            normalized[nodata_mask] = np.nan

            # Apply diverging colormap: Red (negative) -> White (zero) -> Blue (positive)
            cmap = plt.get_cmap("RdBu_r")  # Red-Blue reversed: Red=negative, Blue=positive
            rgba = cmap(np.nan_to_num(normalized, nan=0.5))
            rgba[..., 3] = np.where(nodata_mask, 0, 0.85)  # High opacity for visibility

            image = Image.fromarray((rgba * 255).astype(np.uint8))

            # Convert bounds to WGS84 for web map
            bounds_geom = box(*bounds)
            print(f"      Bounds box before transformation: {bounds_geom.bounds}")

            bounds_wgs = (
                gpd.GeoSeries([bounds_geom], crs=src.crs)
                .to_crs(epsg=4326)
                .total_bounds
            )

            print(f"      Bounds in WGS84: {bounds_wgs}")

            if not np.all(np.isfinite(bounds_wgs)):
                print(f"    Warning: Invalid bounds for {layer}")
                return False

            # Save overlay image
            image_path = output_dir / f"gvd_overlay_{layer.replace('/', '_')}.png"
            image.save(image_path)

            # Add to feature group
            overlay = folium.raster_layers.ImageOverlay(
                name=f"Raster {layer}",
                image=str(image_path),
                bounds=[
                    [bounds_wgs[1], bounds_wgs[0]],
                    [bounds_wgs[3], bounds_wgs[2]],
                ],
                opacity=0.8,  # Higher opacity for visibility
                interactive=False,
                cross_origin=False,
            )
            overlay.add_to(feature_group)

            print(f"    ✓ Added raster overlay for {layer}")
            return True

    except Exception as e:
        print(f"    Error creating raster overlay for {layer}: {e}")
        return False



def _verify_negative_infiltration_sites(
    neg_gdf_proj: gpd.GeoDataFrame, output_dir: Path
) -> None:
    """Programmatically verify that filtered sites actually have negative infiltration."""

    required_cols = ["Infiltration_mm_per_year", "Polygon_Infiltration_mm_per_year", "Centroid_Infiltration_mm_per_year"]
    missing = [col for col in required_cols if col not in neg_gdf_proj.columns]
    if missing:
        print(f"  ⚠ Cannot verify: missing columns {missing}")
        return

    # Check the main infiltration value used
    infiltration_vals = neg_gdf_proj["Infiltration_mm_per_year"].dropna()

    if infiltration_vals.empty:
        print("  ⚠ No infiltration values to verify!")
        return

    total_sites = len(neg_gdf_proj)
    negative_count = (infiltration_vals < 0).sum()
    positive_count = (infiltration_vals >= 0).sum()
    zero_count = (infiltration_vals == 0).sum()

    print(f"\nInfiltration Value Distribution:")
    print(f"  Total rows: {total_sites:,}")
    print(f"  Negative (< 0): {negative_count:,} ({100*negative_count/len(infiltration_vals):.1f}%)")
    print(f"  Zero (= 0): {zero_count:,} ({100*zero_count/len(infiltration_vals):.1f}%)")
    print(f"  Positive (> 0): {positive_count:,} ({100*positive_count/len(infiltration_vals):.1f}%)")

    print(f"\nInfiltration Statistics:")
    print(f"  Min: {infiltration_vals.min():.2f} mm/år")
    print(f"  Max: {infiltration_vals.max():.2f} mm/år")
    print(f"  Mean: {infiltration_vals.mean():.2f} mm/år")
    print(f"  Median: {infiltration_vals.median():.2f} mm/år")

    # Check for potential issues
    if positive_count > 0:
        print(f"\n⚠ WARNING: {positive_count} rows have POSITIVE infiltration!")
        print(f"  These should NOT have been filtered out!")
        positive_sites = neg_gdf_proj[neg_gdf_proj["Infiltration_mm_per_year"] > 0]
        print(f"  Positive value range: {positive_sites['Infiltration_mm_per_year'].min():.2f} to {positive_sites['Infiltration_mm_per_year'].max():.2f} mm/år")

        # Save problematic rows
        problem_path = output_dir / "PROBLEM_positive_infiltration_sites.csv"
        positive_sites[["Lokalitet_ID", "GVFK", "Sampled_Layers", "Infiltration_mm_per_year",
                       "Polygon_Infiltration_mm_per_year", "Centroid_Infiltration_mm_per_year"]].to_csv(problem_path, index=False)
        print(f"  ⚠ Saved problematic rows to: {problem_path}")
    else:
        print(f"\n✓ VERIFICATION PASSED: All filtered sites have negative or zero infiltration")

    # Compare polygon vs centroid sampling
    polygon_vals = neg_gdf_proj["Polygon_Infiltration_mm_per_year"].dropna()
    centroid_vals = neg_gdf_proj["Centroid_Infiltration_mm_per_year"].dropna()

    if not polygon_vals.empty and not centroid_vals.empty:
        print(f"\nPolygon vs Centroid Sampling Comparison:")
        print(f"  Polygon mean: {polygon_vals.mean():.2f} mm/år")
        print(f"  Centroid mean: {centroid_vals.mean():.2f} mm/år")

        # Find rows where methods disagree on sign
        both_valid = neg_gdf_proj[
            neg_gdf_proj["Polygon_Infiltration_mm_per_year"].notna() &
            neg_gdf_proj["Centroid_Infiltration_mm_per_year"].notna()
        ]

        if not both_valid.empty:
            poly_neg = both_valid["Polygon_Infiltration_mm_per_year"] < 0
            cent_neg = both_valid["Centroid_Infiltration_mm_per_year"] < 0
            disagreement = poly_neg != cent_neg
            disagreement_count = disagreement.sum()

            print(f"  Sign disagreement: {disagreement_count:,}/{len(both_valid):,} ({100*disagreement_count/len(both_valid):.1f}%)")

            if disagreement_count > 0:
                print(f"    → Polygon sampling captures spatial variability better")


def _export_negative_infiltration_stats(
    neg_gdf_proj: gpd.GeoDataFrame, output_dir: Path
) -> None:
    """Export detailed comparison table for negative infiltration rows."""
    required_columns = [
        "Lokalitet_ID",
        "GVFK",
        "Sampled_Layers",
        "Infiltration_mm_per_year",
        "Centroid_Infiltration_mm_per_year",
        "Polygon_Infiltration_mm_per_year",
        "Polygon_Infiltration_Min_mm_per_year",
        "Polygon_Infiltration_Max_mm_per_year",
        "Polygon_Infiltration_Pixel_Count",
        "Qualifying_Category",
        "Qualifying_Substance",
    ]

    missing = [col for col in required_columns if col not in neg_gdf_proj.columns]
    if missing:
        print(
            "  Skipping detailed validation export – missing columns: "
            + ", ".join(missing)
        )
        return

    export_df = neg_gdf_proj[required_columns].copy()
    export_df["Polygon_minus_Centroid_mm_per_year"] = (
        export_df["Polygon_Infiltration_mm_per_year"]
        - export_df["Centroid_Infiltration_mm_per_year"]
    )
    export_df["Polygon_to_Centroid_Ratio"] = np.where(
        export_df["Centroid_Infiltration_mm_per_year"].notna()
        & (export_df["Centroid_Infiltration_mm_per_year"] != 0),
        export_df["Polygon_Infiltration_mm_per_year"]
        / export_df["Centroid_Infiltration_mm_per_year"],
        np.nan,
    )

    stats_path = output_dir / "step6_negative_infiltration_validation.csv"
    export_df.to_csv(stats_path, index=False)
    print("  Validation table saved to:", stats_path)


def _add_exceedance_legend(m):
    """Add legend for exceedance colors to map."""
    legend_html = '''
    <div style="position: fixed;
                bottom: 50px; right: 50px; width: 200px; height: 160px;
                background-color: white; border:2px solid grey; z-index:9999;
                font-size:14px; padding: 10px">
    <p style="margin:0; font-weight:bold;">MKK Exceedance</p>
    <p style="margin:5px 0;"><span style="color:green;">━━━</span> Below MKK (<1x)</p>
    <p style="margin:5px 0;"><span style="color:yellow;">━━━</span> 1-10x MKK</p>
    <p style="margin:5px 0;"><span style="color:orange;">━━━</span> 10-100x MKK</p>
    <p style="margin:5px 0;"><span style="color:red;">━━━</span> >100x MKK</p>
    <p style="margin:5px 0;"><span style="color:gray;">━━━</span> No data</p>
    </div>
    '''
    m.get_root().html.add_child(folium.Element(legend_html))


def _add_flux_legend(m):
    """Add legend for flux colors to map."""
    legend_html = '''
    <div style="position: fixed;
                bottom: 50px; right: 50px; width: 200px; height: 140px;
                background-color: white; border:2px solid grey; z-index:9999;
                font-size:14px; padding: 10px">
    <p style="margin:0; font-weight:bold;">Pollution Flux</p>
    <p style="margin:5px 0;"><span style="background:lightgreen; padding:2px 8px;">  </span> <1 kg/year</p>
    <p style="margin:5px 0;"><span style="background:yellow; padding:2px 8px;">  </span> 1-10 kg/year</p>
    <p style="margin:5px 0;"><span style="background:orange; padding:2px 8px;">  </span> 10-100 kg/year</p>
    <p style="margin:5px 0;"><span style="background:red; padding:2px 8px;">  </span> >100 kg/year</p>
    </div>
    '''
    m.get_root().html.add_child(folium.Element(legend_html))
