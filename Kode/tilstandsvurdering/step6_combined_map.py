"""
Step 6 Combined Impact Map
===========================

Creates interactive maps showing contamination sites, Q-points, and river segments.

KEY DESIGN PRINCIPLES:
- Fluxes are NEVER aggregated across different scenarios (scientifically invalid)
- Each map shows ONE scenario only (e.g., BTXER__via_Benzen)
- Connection lines go from site edge to Q-point (not river segment)
- All sites affecting same segment use the SAME Q-point (max Q95 value)

MAP TYPES:
1. Per-scenario maps: One map per Qualifying_Substance value
2. Category overview maps: Shows worst-case across scenarios within a category
3. Overall exceedance map: Shows problem segments across all categories
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Dict, Tuple

import folium
import geopandas as gpd
import numpy as np
import pandas as pd
from shapely.ops import nearest_points

# Ensure repository root is importable
REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from Kode.config import (
    RIVER_FLOW_POINTS_PATH,
    RIVERS_PATH,
    get_output_path,
    get_visualization_path,
)


def create_combined_impact_maps(
    site_flux: pd.DataFrame, segment_summary: pd.DataFrame
) -> None:
    """
    Generate combined impact maps.

    Args:
        site_flux: DataFrame from step6_flux_site_segment.csv
        segment_summary: DataFrame from step6_segment_summary.csv
    """

    print("  Creating combined impact maps (sites + Q-points + rivers)...")

    # Load geometries
    print("    Loading geometries...")
    sites_gdf = gpd.read_file(get_output_path("step3_v1v2_sites"), encoding="utf-8")
    sites_web = sites_gdf.to_crs("EPSG:4326")

    rivers = gpd.read_file(RIVERS_PATH, encoding="utf-8")
    rivers_web = rivers.to_crs("EPSG:4326")

    # Load Q-points with geometries
    qpoints = gpd.read_file(RIVER_FLOW_POINTS_PATH, encoding="utf-8")

    # Set CRS if not defined (Danish data is EPSG:25832)
    if qpoints.crs is None:
        qpoints = qpoints.set_crs("EPSG:25832")

    qpoints_web = qpoints.to_crs("EPSG:4326")

    # Load Cmix results for Q95 scenario
    print("    Loading Cmix data (Q95 scenario)...")
    cmix_path = get_output_path("step6_cmix_results")
    cmix_results = pd.read_csv(cmix_path, encoding="utf-8")
    cmix_q95 = cmix_results[cmix_results["Flow_Scenario"] == "Q95"].copy()

    # Calculate Cmix as % of MKK if not present
    if "Cmix_pct_MKK" not in cmix_q95.columns:
        cmix_q95["Cmix_pct_MKK"] = np.where(
            cmix_q95["MKK_ug_L"].notna() & (cmix_q95["MKK_ug_L"] > 0),
            (cmix_q95["Cmix_ug_L"] / cmix_q95["MKK_ug_L"]) * 100,
            np.nan,
        )

    # Identify which Q-point to use per river segment (max Q95)
    print("    Identifying max Q95 Q-point per segment...")
    qpoint_lookup = _build_qpoint_lookup(qpoints_web)

    # Generate per-scenario maps
    print("    Generating per-scenario maps...")
    scenarios = site_flux["Qualifying_Substance"].dropna().unique()
    print(f"      Found {len(scenarios)} unique scenarios")

    for scenario in sorted(scenarios):
        _create_scenario_map(
            scenario,
            site_flux,
            sites_web,
            rivers_web,
            qpoints_web,
            qpoint_lookup,
            cmix_q95,
        )

    print(f"  Maps saved to {get_visualization_path('step6', 'combined')}/")


def _build_qpoint_lookup(qpoints_gdf: gpd.GeoDataFrame) -> Dict[str, Tuple]:
    """
    Build lookup table: ov_id → (Q95_max, QPoint_geometry).

    For each river segment, finds the Q-point with maximum Q95 value.

    Returns:
        Dict mapping ov_id to (Q95_value, Point geometry)
    """
    # Remove Q-points with None ov_id
    valid_qpoints = qpoints_gdf[qpoints_gdf["ov_id"].notna()].copy()

    if valid_qpoints.empty:
        print("      WARNING: No Q-points with valid ov_id found!")
        return {}

    # Find max Q95 per segment
    idx_max = valid_qpoints.groupby("ov_id")["Q95"].idxmax()
    max_qpoints = valid_qpoints.loc[idx_max]

    # Build lookup
    lookup = {}
    for _, row in max_qpoints.iterrows():
        lookup[row["ov_id"]] = (row["Q95"], row.geometry)

    print(f"      Built Q-point lookup for {len(lookup)} river segments")
    return lookup


def _create_scenario_map(
    scenario: str,
    site_flux: pd.DataFrame,
    sites_web: gpd.GeoDataFrame,
    rivers_web: gpd.GeoDataFrame,
    qpoints_web: gpd.GeoDataFrame,
    qpoint_lookup: Dict[str, Tuple],
    cmix_q95: pd.DataFrame,
) -> None:
    """Create map for a specific scenario."""

    # Filter data for this scenario
    scenario_flux = site_flux[site_flux["Qualifying_Substance"] == scenario].copy()

    if scenario_flux.empty:
        return

    print(f"        Creating map for {scenario} ({len(scenario_flux)} sites)...")

    # Get Cmix data for this scenario
    scenario_cmix = cmix_q95[cmix_q95["Qualifying_Substance"] == scenario].copy()

    # Map center
    bounds = sites_web.total_bounds
    center_lat = (bounds[1] + bounds[3]) / 2
    center_lon = (bounds[0] + bounds[2]) / 2

    # Create map with dark basemap
    m = folium.Map(
        location=[center_lat, center_lon],
        zoom_start=8,
        tiles="CartoDB dark_matter",
        control_scale=True,
    )

    # Add rivers
    _add_rivers(m, rivers_web, scenario_cmix)

    # Add Q-points for affected segments
    affected_segments = scenario_flux["Nearest_River_ov_id"].unique()
    _add_qpoints(m, affected_segments, qpoint_lookup)

    # Add sites
    _add_sites(m, scenario_flux, sites_web)

    # Add connection lines (site edge → Q-point)
    _add_connections(m, scenario_flux, sites_web, qpoint_lookup)

    # Add title and legend
    _add_title(m, scenario, len(scenario_flux), len(affected_segments))
    _add_legend(m)

    # Save map
    safe_name = (
        scenario.replace("/", "_")
        .replace("\\", "_")
        .replace(" ", "_")
        .replace("(", "")
        .replace(")", "")
        .replace(":", "")
    )
    output_dir = get_visualization_path("step6", "combined", "scenarios")
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"scenario_{safe_name}.html"
    m.save(str(output_path))


def _add_rivers(
    m: folium.Map, rivers_web: gpd.GeoDataFrame, scenario_cmix: pd.DataFrame
) -> None:
    """Add river segments colored by Cmix % of MKK."""

    # Merge river geometries with Cmix data
    rivers_enriched = rivers_web.merge(
        scenario_cmix[["Nearest_River_ov_id", "Cmix_ug_L", "MKK_ug_L", "Cmix_pct_MKK"]],
        left_on="ov_id",
        right_on="Nearest_River_ov_id",
        how="left",
    )

    # Add each river segment
    for _, river in rivers_enriched.iterrows():
        cmix_pct = river.get("Cmix_pct_MKK")

        # Determine color based on Cmix % of MKK
        if pd.isna(cmix_pct):
            color = "#444444"  # Dark gray for no data
            weight = 2
        elif cmix_pct < 50:
            color = "#006400"  # Dark green (safe)
            weight = 2
        elif cmix_pct < 100:
            color = "#FFFF00"  # Yellow (approaching limit)
            weight = 3
        elif cmix_pct < 200:
            color = "#FFA500"  # Orange (exceedance)
            weight = 3
        elif cmix_pct < 500:
            color = "#FF4500"  # Red-orange (significant)
            weight = 4
        else:
            color = "#8B0000"  # Dark red (severe)
            weight = 4

        # Create popup
        popup_html = f"""
        <b>River: {river.get("ov_navn", "Unknown")}</b><br>
        ID: {river.get("ov_id", "N/A")}<br>
        """
        if pd.notna(cmix_pct):
            popup_html += f"""
            <hr style='margin:3px 0;'>
            <b>Cmix: {cmix_pct:.1f}% of MKK</b><br>
            Cmix: {river.get("Cmix_ug_L", 0):.2f} µg/L<br>
            MKK: {river.get("MKK_ug_L", 0):.2f} µg/L<br>
            (Q95 scenario)
            """
        else:
            popup_html += "<br>No exceedance data for this scenario"

        folium.GeoJson(
            river.geometry,
            style_function=lambda x, c=color, w=weight: {
                "color": c,
                "weight": w,
                "opacity": 0.7,
            },
            popup=folium.Popup(popup_html, max_width=300),
        ).add_to(m)


def _add_qpoints(
    m: folium.Map, affected_segments: np.ndarray, qpoint_lookup: Dict[str, Tuple]
) -> None:
    """Add Q-point markers for affected river segments."""

    for ov_id in affected_segments:
        if ov_id not in qpoint_lookup:
            continue

        q95_value, qpoint_geom = qpoint_lookup[ov_id]

        # Create circular marker at Q-point location
        folium.CircleMarker(
            location=[qpoint_geom.y, qpoint_geom.x],
            radius=6,
            color="#FFFFFF",  # White outline
            weight=2,
            fill=True,
            fillColor="#00BFFF",  # Deep sky blue
            fillOpacity=0.9,
            popup=folium.Popup(
                f"<b>Q-point</b><br>River: {ov_id}<br>Q95: {q95_value:.4f} m³/s",
                max_width=200,
            ),
            tooltip=f"Q95: {q95_value:.4f} m³/s",
        ).add_to(m)


def _add_sites(
    m: folium.Map, scenario_flux: pd.DataFrame, sites_web: gpd.GeoDataFrame
) -> None:
    """Add site polygons colored by V1/V2 classification."""

    # Get unique sites in this scenario
    affected_sites = scenario_flux["Lokalitet_ID"].unique()

    # Filter site geometries
    sites_filtered = sites_web[sites_web["Lokalitet_"].isin(affected_sites)].copy()

    for _, site in sites_filtered.iterrows():
        # Determine color based on V1/V2 classification
        v1v2_class = site.get("Lokalite_7", "")

        if "V1" in str(v1v2_class) and "V2" not in str(v1v2_class):
            color = "#0000FF"  # Blue for V1
        elif "V2" in str(v1v2_class):
            color = "#FF0000"  # Red for V2 (or V1 og V2)
        else:
            color = "#808080"  # Gray for unknown

        # Get flux info for popup
        site_flux_info = scenario_flux[
            scenario_flux["Lokalitet_ID"] == site["Lokalitet_"]
        ]
        total_flux = site_flux_info["Pollution_Flux_kg_per_year"].sum()

        popup_html = f"""
        <b>Site: {site["Lokalitet_"]}</b><br>
        Classification: {v1v2_class}<br>
        Flux: {total_flux:.2f} kg/year
        """

        folium.GeoJson(
            site.geometry,
            style_function=lambda x, c=color: {
                "fillColor": c,
                "color": "#000000",
                "weight": 1,
                "fillOpacity": 0.6,
            },
            popup=folium.Popup(popup_html, max_width=250),
        ).add_to(m)


def _add_connections(
    m: folium.Map,
    scenario_flux: pd.DataFrame,
    sites_web: gpd.GeoDataFrame,
    qpoint_lookup: Dict[str, Tuple],
) -> None:
    """Add connection lines from site edge to Q-point."""

    for _, row in scenario_flux.iterrows():
        site_id = row["Lokalitet_ID"]
        river_id = row["Nearest_River_ov_id"]
        flux_kg = row["Pollution_Flux_kg_per_year"]

        # Get site geometry
        site_geom = sites_web[sites_web["Lokalitet_"] == site_id]
        if site_geom.empty:
            continue
        site_polygon = site_geom.iloc[0].geometry

        # Get Q-point location
        if river_id not in qpoint_lookup:
            continue
        q95_value, qpoint_geom = qpoint_lookup[river_id]

        # Find nearest point on site edge to Q-point
        closest_point_on_site, _ = nearest_points(site_polygon, qpoint_geom)

        # Create line from site edge to Q-point
        line_coords = [
            [closest_point_on_site.y, closest_point_on_site.x],
            [qpoint_geom.y, qpoint_geom.x],
        ]

        # Determine line style based on flux
        line_color, line_weight = _get_connection_style(flux_kg)

        popup_html = f"""
        <b>Connection</b><br>
        Site: {site_id}<br>
        → River: {river_id}<br>
        Flux: {flux_kg:.2f} kg/year<br>
        Q95: {q95_value:.4f} m³/s
        """

        # Add outline for visibility
        folium.PolyLine(
            line_coords,
            color="#000000",  # Black outline
            weight=line_weight + 1,
            opacity=0.6,
        ).add_to(m)

        # Add main line
        folium.PolyLine(
            line_coords,
            color=line_color,
            weight=line_weight,
            opacity=0.9,
            popup=folium.Popup(popup_html, max_width=250),
        ).add_to(m)


def _get_connection_style(flux_kg: float) -> Tuple[str, int]:
    """Get line color and weight based on flux magnitude."""

    if pd.isna(flux_kg) or flux_kg <= 0:
        return "#CCCCCC", 1  # Light gray, thin

    if flux_kg < 1:
        return "#FFB366", 1  # Light orange, thin
    elif flux_kg < 10:
        return "#FF8C1A", 2  # Orange, medium
    elif flux_kg < 100:
        return "#E64D1A", 3  # Red-orange, thick
    else:
        return "#B30000", 4  # Dark red, very thick


def _add_title(m: folium.Map, scenario: str, site_count: int, river_count: int) -> None:
    """Add title box to map."""

    title_html = f"""
    <div style="position: fixed; top: 10px; left: 50px; width: 350px;
                background-color: rgba(255, 255, 255, 0.9); border:2px solid #333;
                z-index:9999; font-size:14px; padding: 10px; border-radius: 5px;">
    <b style="font-size:16px;">Scenario: {scenario}</b><br>
    <span style="font-size:12px;">
    Sites: {site_count} | River segments: {river_count}<br>
    Flow scenario: Q95 (low flow, conservative)
    </span>
    </div>
    """
    m.get_root().html.add_child(folium.Element(title_html))


def _add_legend(m: folium.Map) -> None:
    """Add legend to map."""

    legend_html = """
    <div style="position: fixed; bottom: 50px; right: 50px; width: 250px;
                background-color: rgba(255, 255, 255, 0.95); border:2px solid #333;
                z-index:9999; font-size:12px; padding: 10px; border-radius: 5px;">
    <p style="margin:0; font-weight:bold; font-size:14px;">Legend</p>
    <hr style="margin:5px 0;">

    <p style="margin:3px 0; font-weight:bold;">Sites (Polygons)</p>
    <p style="margin:2px 0;"><span style="color:#0000FF; font-size:16px;">■</span> V1 sites</p>
    <p style="margin:2px 0;"><span style="color:#FF0000; font-size:16px;">■</span> V2 sites</p>

    <hr style="margin:5px 0;">
    <p style="margin:3px 0; font-weight:bold;">Rivers (Cmix % MKK)</p>
    <p style="margin:2px 0; font-size:11px;"><span style="color:#006400;">━━</span> <50% (safe)</p>
    <p style="margin:2px 0; font-size:11px;"><span style="color:#FFFF00;">━━</span> 50-100% (approaching)</p>
    <p style="margin:2px 0; font-size:11px;"><span style="color:#FFA500;">━━</span> 100-200% (exceedance)</p>
    <p style="margin:2px 0; font-size:11px;"><span style="color:#FF4500;">━━</span> 200-500% (significant)</p>
    <p style="margin:2px 0; font-size:11px;"><span style="color:#8B0000;">━━</span> >500% (severe)</p>

    <hr style="margin:5px 0;">
    <p style="margin:3px 0; font-weight:bold;">Connection Lines</p>
    <p style="margin:2px 0; font-size:11px;">From site edge → Q-point</p>
    <p style="margin:2px 0; font-size:11px;">Color/width by flux magnitude</p>

    <hr style="margin:5px 0;">
    <p style="margin:3px 0; font-weight:bold;">Q-points</p>
    <p style="margin:2px 0;"><span style="color:#00BFFF; font-size:16px;">●</span> Q95 measurement point</p>
    <p style="margin:2px 0; font-size:10px; font-style:italic;">(Max Q95 value used per segment)</p>
    </div>
    """
    m.get_root().html.add_child(folium.Element(legend_html))
