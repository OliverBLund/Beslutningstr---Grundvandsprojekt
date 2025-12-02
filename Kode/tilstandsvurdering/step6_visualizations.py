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

import folium
import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import rasterio
from affine import Affine
from branca.colormap import LinearColormap
from folium.plugins import FloatImage
from matplotlib.colors import TwoSlopeNorm
from PIL import Image
from rasterio.enums import Resampling
from shapely.geometry import box

# Ensure repository root is importable
REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from Kode.config import (
    GRUNDVAND_PATH,
    GVD_RASTER_DIR,
    RIVERS_PATH,
    STEP6_MAP_SETTINGS,
    get_output_path,
    get_visualization_path,
)


def analyze_and_visualize_step6(
    site_flux: pd.DataFrame,
    segment_flux: pd.DataFrame,
    cmix_results: pd.DataFrame,
    segment_summary: pd.DataFrame,
    *,
    negative_infiltration: pd.DataFrame | None = None,
    site_geometries: gpd.GeoDataFrame | None = None,
    site_exceedances: pd.DataFrame | None = None,
    gvfk_exceedances: pd.DataFrame | None = None,
    pixel_data_records: list | None = None,
    enriched_results: pd.DataFrame | None = None,
) -> None:
    """Print compact diagnostics covering the main Step 6 deliverables."""

    print("\nSTEP 6: TILSTANDSVURDERING – SUMMARY")
    print("=" * 60)

    _print_site_level_overview(site_flux)
    _print_segment_overview(segment_flux)
    _print_cmix_overview(cmix_results)
    _print_segment_summary(segment_summary)
    _print_exceedance_focus(site_exceedances, gvfk_exceedances)

    print("=" * 60)
    print("End of Step 6 summary")
    print("=" * 60)

    # Create pixel distribution visualizations FIRST (before any map issues)
    if pixel_data_records is not None and enriched_results is not None:
        print("\nGenerating pixel distribution visualizations...")
        _create_pixel_distribution_plots(pixel_data_records, enriched_results, negative_infiltration)

    # NOTE: Negative infiltration map moved to Step 5c (upward flux visualization)
    # Sites with upward flux are now filtered in Step 5c before reaching Step 6
    # The map in Step 5c shows which sites are excluded BEFORE filtering

    scenario_flag = STEP6_MAP_SETTINGS.get("generate_combined_maps", True)
    overall_flag = STEP6_MAP_SETTINGS.get("generate_overall_maps", True)
    if scenario_flag or overall_flag:
        print("\nGenerating combined/overall impact maps...")
        try:
            from .step6_combined_map import create_combined_impact_maps
        except ImportError:
            from step6_combined_map import create_combined_impact_maps
        create_combined_impact_maps(site_flux, segment_summary, gvfk_exceedances)
    else:
        print(
            "\nSkipping combined impact maps (all Step 6 map flags disabled)."
        )

    # Create analytical plots
    print("\nGenerating analytical plots...")
    try:
        from .step6_analytical_plots import create_analytical_plots
    except ImportError:
        from step6_analytical_plots import create_analytical_plots
    create_analytical_plots(site_flux, segment_flux, cmix_results, segment_summary)

    print("All visualizations saved to Resultater/step6_tilstandsvurdering/figures/")


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

    top_segments = segment_flux.sort_values(
        "Total_Flux_kg_per_year", ascending=False
    ).head(5)[
        [
            "Nearest_River_ov_id",
            "River_Segment_Name",
            "Qualifying_Substance",
            "Total_Flux_kg_per_year",
            "Contributing_Site_Count",
        ]
    ]

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
    scenarios = [str(s) for s in cmix_results["Flow_Scenario"].dropna().unique()]
    print(f"Scenarios considered: {', '.join(sorted(scenarios))}")

    available = cmix_results[cmix_results["Has_Flow_Data"]]
    if available.empty:
        print("All scenario rows are missing flow values – nothing further to report.")
        return

    worst = available.sort_values("Cmix_ug_L", ascending=False).head(5)[
        [
            "Nearest_River_ov_id",
            "River_Segment_Name",
            "Qualifying_Substance",
            "Flow_Scenario",
            "Cmix_ug_L",
        ]
    ]

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
            for _, row in (
                exceedances.sort_values("Exceedance_Ratio", ascending=False)
                .head(5)
                .iterrows()
            ):
                print(
                    f"  {row['Nearest_River_ov_id']} - {row['Qualifying_Substance']} "
                    f"({row['Flow_Scenario']}): {row['Exceedance_Ratio']:.2f}x MKK"
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
        for _, row in (
            failing.sort_values("Max_Exceedance_Ratio", ascending=False)
            .head(5)
            .iterrows()
        ):
            print(
                f"  {row['Nearest_River_ov_id']} ({row['River_Segment_Name']}): "
                f"{row['Max_Exceedance_Ratio']:.2f}x MKK "
                f"(scenarios: {row['Failing_Scenarios'] or 'n/a'})"
            )


def _print_exceedance_focus(
    site_exceedances: pd.DataFrame | None, gvfk_exceedances: pd.DataFrame | None
) -> None:
    print("\n5. Confirmed MKK exceedances (filtered views)")
    print("-" * 60)

    if site_exceedances is None or site_exceedances.empty:
        print("No MKK exceedances were observed in the current run.")
        return

    total_sites = site_exceedances["Lokalitet_ID"].nunique()
    total_segments = site_exceedances["Nearest_River_ov_id"].nunique()
    scenarios = site_exceedances["Flow_Scenario"].nunique()

    print(f"Rows in site-level exceedance view: {len(site_exceedances):,}")
    print(f"  -> {total_sites:,} unique sites across {total_segments:,} river segments")
    print(f"  -> Flow scenarios represented: {scenarios}")

    if gvfk_exceedances is not None and not gvfk_exceedances.empty:
        exceeding_gvfk = gvfk_exceedances["GVFK"].nunique()
        print(f"GVFK with >=1 exceedance: {exceeding_gvfk:,}")

        preview = gvfk_exceedances.sort_values(
            "Max_Exceedance_Ratio", ascending=False
        ).head(5)
        for _, row in preview.iterrows():
            print(
                f"  {row['GVFK']} -> {row['River_Segment_Name']} "
                f"({row['Nearest_River_ov_id']}): {row['Max_Exceedance_Ratio']:.2f}x "
                f"MKK (sites: {row['Site_IDs']})"
            )
    else:
        print(
            "No GVFK summaries available for exceedances (data filtered to zero rows)."
        )


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

    neg_gdf_proj = gpd.GeoDataFrame(
        joined, geometry="geometry", crs=site_geometries.crs
    )
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
                value = (
                    feature["properties"].get("Display_Infiltration_mm_per_year", 0)
                    or 0
                )
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
    output_dir.mkdir(parents=True, exist_ok=True)  # Ensure directory exists

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
        _add_raster_overlay_for_layer(
            layer, feature_group, output_dir, neg_gdf_proj.crs
        )

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
        [WARNING] VALIDATION CHECK:<br>
        Removed sites should be on RED areas!
      </p>
      <hr style="margin: 8px 0;">
      <p style="margin: 3px 0; font-size: 9px; color: #666;">
        <em>Use layer control (top-right) to toggle modellags.<br>
        If site polygons overlap BLUE areas -> potential bug!</em>
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

    # Handle OneDrive placeholder files that appear in directory but can't be accessed
    # This happens when OneDrive shows a file in Explorer but hasn't synced it yet
    import os
    import time

    # Check if it's a OneDrive placeholder (shows in dir but exists() returns False)
    try:
        # Force delete any existing file/placeholder
        if map_path.exists():
            os.remove(str(map_path))
        else:
            # Try to remove placeholder that doesn't register as existing
            try:
                os.remove(str(map_path))
                print(f"  Removed OneDrive placeholder: {map_path.name}")
            except:
                pass
        time.sleep(0.1)  # Brief pause for filesystem
    except Exception as e:
        print(f"  Note: Could not remove existing file: {e}")

    # Save HTML directly with proper encoding
    try:
        html_str = fmap.get_root().render()
        with open(str(map_path), 'w', encoding='utf-8') as f:
            f.write(html_str)
        print(f"  Map saved successfully: {map_path.name}")
    except Exception as e:
        print(f"  ERROR: Could not save map: {e}")
        print(f"  This may be a OneDrive sync issue. Try pausing OneDrive and rerunning.")

    geojson_path = output_dir / "step6_negative_infiltration_sites.geojson"
    neg_gdf.to_file(geojson_path, driver="GeoJSON")

    summary_path = output_dir / "step6_negative_infiltration_summary.csv"
    gvfk_summary.to_csv(summary_path, index=False)

    _export_negative_infiltration_stats(neg_gdf_proj, output_dir)

    # PROGRAMMATIC VERIFICATION: Check if filtered sites actually have negative infiltration
    print("\n" + "=" * 60)
    print("PROGRAMMATIC VERIFICATION OF NEGATIVE INFILTRATION")
    print("=" * 60)
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
    return layer.strip().lower()


def _resolve_visualization_raster_filename(layer: str) -> str:
    """Return raster filename for visualization overlays."""
    prefix = "dk7" if layer.startswith("lag") else "dk16"
    return f"{prefix}_gvd_{layer}.tif"


def _add_raster_overlay_for_layer(
    layer: str,
    feature_group: folium.FeatureGroup,
    output_dir: Path,
    source_crs,
) -> bool:
    """Add GVD raster overlay for the specified modellag to the feature group."""
    normalized_layer = _normalize_layer_name(layer)
    raster_filename = _resolve_visualization_raster_filename(normalized_layer)
    raster_path = Path(GVD_RASTER_DIR) / raster_filename

    if not raster_path.exists() and not raster_filename.startswith("dk16_"):
        fallback = Path(GVD_RASTER_DIR) / f"dk16_gvd_{normalized_layer}.tif"
        if fallback.exists():
            raster_path = fallback

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

            transform = src.transform * Affine.scale(
                width / out_width, height / out_height
            )
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
            print(
                f"      All values: min={valid.min():.1f}, max={valid.max():.1f}, mean={valid.mean():.1f} mm/år"
            )

            negative_count = (valid < 0).sum()
            positive_count = (valid >= 0).sum()
            print(
                f"      Negative pixels: {negative_count:,} ({100 * negative_count / len(valid):.1f}%)"
            )
            print(
                f"      Positive pixels: {positive_count:,} ({100 * positive_count / len(valid):.1f}%)"
            )

            if negative_count > 0:
                negative_vals = valid[valid < 0]
                print(
                    f"      Negative range: {negative_vals.min():.1f} to {negative_vals.max():.1f} mm/år"
                )

            if positive_count > 0:
                positive_vals = valid[valid >= 0]
                print(
                    f"      Positive range: {positive_vals.min():.1f} to {positive_vals.max():.1f} mm/år"
                )

            # Use diverging colormap centered at 0
            # Red = negative (discharge), Blue/Green = positive (recharge)
            vmin = float(valid.min())
            vmax = float(valid.max())

            # Use percentile-based clipping to handle extreme outliers
            # This prevents extreme values from washing out the color scale
            vmin_p = np.percentile(valid, 1)  # 1st percentile
            vmax_p = np.percentile(valid, 99)  # 99th percentile

            print(f"      Percentile range (1-99%): {vmin_p:.1f} to {vmax_p:.1f} mm/år")
            print(
                f"      Using this range for colormap to avoid extreme outlier washing"
            )

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
            cmap = plt.get_cmap(
                "RdBu_r"
            )  # Red-Blue reversed: Red=negative, Blue=positive
            rgba = cmap(np.nan_to_num(normalized, nan=0.5))
            rgba[..., 3] = np.where(nodata_mask, 0, 0.85)  # High opacity for visibility

            image = Image.fromarray((rgba * 255).astype(np.uint8))

            # Convert bounds to WGS84 for web map
            bounds_geom = box(*bounds)
            print(f"      Bounds box before transformation: {bounds_geom.bounds}")

            bounds_wgs = (
                gpd.GeoSeries([bounds_geom], crs=src.crs).to_crs(epsg=4326).total_bounds
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

            print(f"    [OK] Added raster overlay for {layer}")
            return True

    except Exception as e:
        print(f"    Error creating raster overlay for {layer}: {e}")
        return False


def _verify_negative_infiltration_sites(
    neg_gdf_proj: gpd.GeoDataFrame, output_dir: Path
) -> None:
    """Programmatically verify that filtered sites actually have negative infiltration."""

    required_cols = [
        "Infiltration_mm_per_year",
        "Polygon_Infiltration_mm_per_year",
        "Centroid_Infiltration_mm_per_year",
    ]
    missing = [col for col in required_cols if col not in neg_gdf_proj.columns]
    if missing:
        print(f"  [WARNING] Cannot verify: missing columns {missing}")
        return

    # Check the main infiltration value used
    infiltration_vals = neg_gdf_proj["Infiltration_mm_per_year"].dropna()

    if infiltration_vals.empty:
        print("  [WARNING] No infiltration values to verify!")
        return

    total_sites = len(neg_gdf_proj)
    negative_count = (infiltration_vals < 0).sum()
    positive_count = (infiltration_vals >= 0).sum()
    zero_count = (infiltration_vals == 0).sum()

    print(f"\nInfiltration Value Distribution:")
    print(f"  Total rows: {total_sites:,}")
    print(
        f"  Negative (< 0): {negative_count:,} ({100 * negative_count / len(infiltration_vals):.1f}%)"
    )
    print(
        f"  Zero (= 0): {zero_count:,} ({100 * zero_count / len(infiltration_vals):.1f}%)"
    )
    print(
        f"  Positive (> 0): {positive_count:,} ({100 * positive_count / len(infiltration_vals):.1f}%)"
    )

    print(f"\nInfiltration Statistics:")
    print(f"  Min: {infiltration_vals.min():.2f} mm/år")
    print(f"  Max: {infiltration_vals.max():.2f} mm/år")
    print(f"  Mean: {infiltration_vals.mean():.2f} mm/år")
    print(f"  Median: {infiltration_vals.median():.2f} mm/år")

    # Check for potential issues
    if positive_count > 0:
        print(f"\n[WARNING] WARNING: {positive_count} rows have POSITIVE infiltration!")
        print(f"  These should NOT have been filtered out!")
        positive_sites = neg_gdf_proj[neg_gdf_proj["Infiltration_mm_per_year"] > 0]
        print(
            f"  Positive value range: {positive_sites['Infiltration_mm_per_year'].min():.2f} to {positive_sites['Infiltration_mm_per_year'].max():.2f} mm/år"
        )

        # Save problematic rows
        problem_path = output_dir / "PROBLEM_positive_infiltration_sites.csv"
        positive_sites[
            [
                "Lokalitet_ID",
                "GVFK",
                "Sampled_Layers",
                "Infiltration_mm_per_year",
                "Polygon_Infiltration_mm_per_year",
                "Centroid_Infiltration_mm_per_year",
            ]
        ].to_csv(problem_path, index=False)
        print(f"  [WARNING] Saved problematic rows to: {problem_path}")
    else:
        print(
            f"\n[OK] VERIFICATION PASSED: All filtered sites have negative or zero infiltration"
        )

    # Compare polygon vs centroid sampling
    polygon_vals = neg_gdf_proj["Polygon_Infiltration_mm_per_year"].dropna()
    centroid_vals = neg_gdf_proj["Centroid_Infiltration_mm_per_year"].dropna()

    if not polygon_vals.empty and not centroid_vals.empty:
        print(f"\nPolygon vs Centroid Sampling Comparison:")
        print(f"  Polygon mean: {polygon_vals.mean():.2f} mm/år")
        print(f"  Centroid mean: {centroid_vals.mean():.2f} mm/år")

        # Find rows where methods disagree on sign
        both_valid = neg_gdf_proj[
            neg_gdf_proj["Polygon_Infiltration_mm_per_year"].notna()
            & neg_gdf_proj["Centroid_Infiltration_mm_per_year"].notna()
        ]

        if not both_valid.empty:
            poly_neg = both_valid["Polygon_Infiltration_mm_per_year"] < 0
            cent_neg = both_valid["Centroid_Infiltration_mm_per_year"] < 0
            disagreement = poly_neg != cent_neg
            disagreement_count = disagreement.sum()

            print(
                f"  Sign disagreement: {disagreement_count:,}/{len(both_valid):,} ({100 * disagreement_count / len(both_valid):.1f}%)"
            )

            if disagreement_count > 0:
                print(f"    -> Polygon sampling captures spatial variability better")


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


def _create_pixel_distribution_plots(
    pixel_data_records: list,
    enriched_results: pd.DataFrame,
    negative_infiltration: pd.DataFrame | None = None,
) -> None:
    """
    Create distribution plots of all sampled infiltration pixel values.

    Creates:
    1. Overall distribution of all pixels sampled
    2. Distribution split by positive vs negative infiltration sites
    3. Summary statistics table
    """
    if not pixel_data_records:
        print("  No pixel data available for distribution plots.")
        return

    output_dir = get_visualization_path("step6", "pixel_distributions")
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"  Processing {len(pixel_data_records)} pixel data records...")

    # Flatten all pixel values and track site association
    all_pixels = []
    site_pixel_map = {}  # Map lokalitet_id to list of pixel values

    for record in pixel_data_records:
        lokalitet_id = record["Lokalitet_ID"]
        pixel_values = record["Pixel_Values"]

        if pixel_values:
            all_pixels.extend(pixel_values)

            if lokalitet_id not in site_pixel_map:
                site_pixel_map[lokalitet_id] = []
            site_pixel_map[lokalitet_id].extend(pixel_values)

    if not all_pixels:
        print("  No valid pixel values found.")
        return

    all_pixels = np.array(all_pixels)

    # Determine which sites have negative vs positive infiltration
    negative_site_ids = set()
    if negative_infiltration is not None and not negative_infiltration.empty:
        negative_site_ids = set(negative_infiltration["Lokalitet_ID"].unique())

    positive_site_ids = set(enriched_results["Lokalitet_ID"].unique())

    # Collect pixels by site type
    positive_pixels = []
    negative_pixels = []

    for lokalitet_id, pixels in site_pixel_map.items():
        if lokalitet_id in negative_site_ids:
            negative_pixels.extend(pixels)
        elif lokalitet_id in positive_site_ids:
            positive_pixels.extend(pixels)

    positive_pixels = np.array(positive_pixels) if positive_pixels else np.array([])
    negative_pixels = np.array(negative_pixels) if negative_pixels else np.array([])

    # Print summary statistics
    print("\n" + "=" * 80)
    print("PIXEL DISTRIBUTION SUMMARY")
    print("=" * 80)
    print(f"\nTotal pixels sampled: {len(all_pixels):,}")
    print(f"  From positive infiltration sites: {len(positive_pixels):,}")
    print(f"  From negative infiltration sites: {len(negative_pixels):,}")

    print(f"\nOverall Statistics (mm/år):")
    print(f"  Min:    {np.min(all_pixels):>10.2f}")
    print(f"  Q1:     {np.percentile(all_pixels, 25):>10.2f}")
    print(f"  Median: {np.median(all_pixels):>10.2f}")
    print(f"  Mean:   {np.mean(all_pixels):>10.2f}")
    print(f"  Q3:     {np.percentile(all_pixels, 75):>10.2f}")
    print(f"  Max:    {np.max(all_pixels):>10.2f}")
    print(f"  Std:    {np.std(all_pixels):>10.2f}")

    # Count negative vs positive pixels
    neg_pixel_count = (all_pixels < 0).sum()
    pos_pixel_count = (all_pixels >= 0).sum()
    print(f"\nPixel value distribution:")
    print(f"  Negative (< 0):  {neg_pixel_count:>10,} ({100*neg_pixel_count/len(all_pixels):>5.1f}%)")
    print(f"  Positive (>= 0): {pos_pixel_count:>10,} ({100*pos_pixel_count/len(all_pixels):>5.1f}%)")

    if len(positive_pixels) > 0:
        print(f"\nPositive Site Pixels (mm/år):")
        print(f"  Min:    {np.min(positive_pixels):>10.2f}")
        print(f"  Median: {np.median(positive_pixels):>10.2f}")
        print(f"  Mean:   {np.mean(positive_pixels):>10.2f}")
        print(f"  Max:    {np.max(positive_pixels):>10.2f}")

    if len(negative_pixels) > 0:
        print(f"\nNegative Site Pixels (mm/år):")
        print(f"  Min:    {np.min(negative_pixels):>10.2f}")
        print(f"  Median: {np.median(negative_pixels):>10.2f}")
        print(f"  Mean:   {np.mean(negative_pixels):>10.2f}")
        print(f"  Max:    {np.max(negative_pixels):>10.2f}")

    print("=" * 80 + "\n")

    # Create visualizations
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))

    # 1. Overall histogram - FULL DATA RANGE
    ax1 = axes[0, 0]
    bins = np.linspace(np.min(all_pixels), np.max(all_pixels), 50)
    ax1.hist(all_pixels, bins=bins, alpha=0.7, color='steelblue', edgecolor='black')
    ax1.axvline(0, color='red', linestyle='--', linewidth=2, label='Zero infiltration')
    ax1.axvline(np.median(all_pixels), color='orange', linestyle='--', linewidth=2, label=f'Median: {np.median(all_pixels):.1f}')
    ax1.set_xlabel('Infiltration (mm/år)', fontsize=12)
    ax1.set_ylabel('Pixel Count', fontsize=12)
    ax1.set_title(f'Overall Pixel Distribution (Full Range)\n{len(all_pixels):,} total pixels\nMin: {np.min(all_pixels):.1f}, Max: {np.max(all_pixels):.1f}', fontsize=14, fontweight='bold')
    ax1.legend()
    ax1.grid(True, alpha=0.3)

    # 2. Cumulative distribution
    ax2 = axes[0, 1]
    sorted_pixels = np.sort(all_pixels)
    cumulative = np.arange(1, len(sorted_pixels) + 1) / len(sorted_pixels) * 100
    ax2.plot(sorted_pixels, cumulative, linewidth=2, color='steelblue')
    ax2.axvline(0, color='red', linestyle='--', linewidth=2, label='Zero infiltration')
    ax2.axhline(50, color='orange', linestyle='--', linewidth=1, alpha=0.5, label='Median')
    ax2.set_xlabel('Infiltration (mm/år)', fontsize=12)
    ax2.set_ylabel('Cumulative Percentage (%)', fontsize=12)
    ax2.set_title('Cumulative Distribution Function', fontsize=14, fontweight='bold')
    ax2.legend()
    ax2.grid(True, alpha=0.3)

    # 3. Positive vs Negative sites comparison
    ax3 = axes[1, 0]

    if len(positive_pixels) > 0 and len(negative_pixels) > 0:
        bins_pos_neg = np.linspace(
            min(np.min(positive_pixels), np.min(negative_pixels)),
            max(np.max(positive_pixels), np.max(negative_pixels)),
            50
        )
        ax3.hist(positive_pixels, bins=bins_pos_neg, alpha=0.6, color='green',
                 label=f'Positive sites ({len(positive_pixels):,} pixels)', edgecolor='black')
        ax3.hist(negative_pixels, bins=bins_pos_neg, alpha=0.6, color='red',
                 label=f'Negative sites ({len(negative_pixels):,} pixels)', edgecolor='black')
        ax3.axvline(0, color='black', linestyle='--', linewidth=2, label='Zero infiltration')
        ax3.set_xlabel('Infiltration (mm/år)', fontsize=12)
        ax3.set_ylabel('Pixel Count', fontsize=12)
        ax3.set_title(f'Distribution by Site Type (Full Range)\nPositive: {np.min(positive_pixels):.1f} to {np.max(positive_pixels):.1f}\nNegative: {np.min(negative_pixels):.1f} to {np.max(negative_pixels):.1f}', fontsize=14, fontweight='bold')
        ax3.legend()
        ax3.grid(True, alpha=0.3)
    else:
        ax3.text(0.5, 0.5, 'Insufficient data for comparison',
                ha='center', va='center', transform=ax3.transAxes, fontsize=12)
        ax3.set_title('Distribution by Site Type', fontsize=14, fontweight='bold')

    # 4. Box plot comparison
    ax4 = axes[1, 1]

    data_to_plot = []
    labels_to_plot = []
    colors_to_plot = []

    if len(positive_pixels) > 0:
        data_to_plot.append(positive_pixels)
        labels_to_plot.append(f'Positive Sites\n(n={len(positive_pixels):,})')
        colors_to_plot.append('green')

    if len(negative_pixels) > 0:
        data_to_plot.append(negative_pixels)
        labels_to_plot.append(f'Negative Sites\n(n={len(negative_pixels):,})')
        colors_to_plot.append('red')

    data_to_plot.append(all_pixels)
    labels_to_plot.append(f'All Sites\n(n={len(all_pixels):,})')
    colors_to_plot.append('steelblue')

    if data_to_plot:
        bp = ax4.boxplot(data_to_plot, labels=labels_to_plot, patch_artist=True,
                         showfliers=True, widths=0.6,
                         flierprops=dict(marker='o', markersize=2, alpha=0.3))

        for patch, color in zip(bp['boxes'], colors_to_plot):
            patch.set_facecolor(color)
            patch.set_alpha(0.6)

        ax4.axhline(0, color='black', linestyle='--', linewidth=2, alpha=0.5, label='Zero infiltration')
        ax4.set_ylabel('Infiltration (mm/år)', fontsize=12)
        ax4.set_title('Box Plot Comparison (All Data Including Outliers)', fontsize=14, fontweight='bold')
        ax4.grid(True, alpha=0.3, axis='y')
        ax4.legend()

    plt.tight_layout()

    # Save figure
    plot_path = output_dir / "step6_pixel_distribution_analysis.png"
    plt.savefig(plot_path, dpi=300, bbox_inches='tight')
    plt.close()

    print(f"  Pixel distribution plots saved to: {plot_path}")

    # Export statistics to CSV
    stats_df = pd.DataFrame({
        'Category': ['Overall', 'Positive Sites', 'Negative Sites'],
        'Pixel_Count': [len(all_pixels), len(positive_pixels), len(negative_pixels)],
        'Min_mm_per_year': [
            np.min(all_pixels),
            np.min(positive_pixels) if len(positive_pixels) > 0 else np.nan,
            np.min(negative_pixels) if len(negative_pixels) > 0 else np.nan
        ],
        'Q25_mm_per_year': [
            np.percentile(all_pixels, 25),
            np.percentile(positive_pixels, 25) if len(positive_pixels) > 0 else np.nan,
            np.percentile(negative_pixels, 25) if len(negative_pixels) > 0 else np.nan
        ],
        'Median_mm_per_year': [
            np.median(all_pixels),
            np.median(positive_pixels) if len(positive_pixels) > 0 else np.nan,
            np.median(negative_pixels) if len(negative_pixels) > 0 else np.nan
        ],
        'Mean_mm_per_year': [
            np.mean(all_pixels),
            np.mean(positive_pixels) if len(positive_pixels) > 0 else np.nan,
            np.mean(negative_pixels) if len(negative_pixels) > 0 else np.nan
        ],
        'Q75_mm_per_year': [
            np.percentile(all_pixels, 75),
            np.percentile(positive_pixels, 75) if len(positive_pixels) > 0 else np.nan,
            np.percentile(negative_pixels, 75) if len(negative_pixels) > 0 else np.nan
        ],
        'Max_mm_per_year': [
            np.max(all_pixels),
            np.max(positive_pixels) if len(positive_pixels) > 0 else np.nan,
            np.max(negative_pixels) if len(negative_pixels) > 0 else np.nan
        ],
        'Std_mm_per_year': [
            np.std(all_pixels),
            np.std(positive_pixels) if len(positive_pixels) > 0 else np.nan,
            np.std(negative_pixels) if len(negative_pixels) > 0 else np.nan
        ],
    })

    stats_path = output_dir / "step6_pixel_distribution_statistics.csv"
    stats_df.to_csv(stats_path, index=False)
    print(f"  Pixel distribution statistics saved to: {stats_path}")
