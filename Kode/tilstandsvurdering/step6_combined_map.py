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

import hashlib
import os
import sys
import time
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Tuple

import folium
import geopandas as gpd
import numpy as np
import pandas as pd
from branca.colormap import LinearColormap
from shapely.ops import nearest_points

# Ensure repository root is importable
REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from Kode.config import (
    GRUNDVAND_LAYER_NAME,
    GRUNDVAND_PATH,
    RIVER_FLOW_POINTS_LAYER,
    RIVER_FLOW_POINTS_PATH,
    RIVERS_LAYER_NAME,
    RIVERS_PATH,
    STEP6_MAP_SETTINGS,
    get_output_path,
    get_visualization_path,
)


def create_combined_impact_maps(
    site_flux: pd.DataFrame,
    segment_summary: pd.DataFrame,
    gvfk_exceedances: pd.DataFrame | None = None,
) -> None:
    """
    Generate combined impact maps.

    Args:
        site_flux: DataFrame from step6_flux_site_segment.csv
        segment_summary: DataFrame from step6_segment_summary.csv
        gvfk_exceedances: DataFrame from step6_gvfk_exceedances.csv (site-level GVFK)
    """

    print("  Creating combined impact maps (sites + Q-points + rivers)...")

    # Load geometries
    print("    Loading geometries...")
    sites_gdf = gpd.read_file(get_output_path("step3_v1v2_sites"), encoding="utf-8")
    sites_web = sites_gdf.to_crs("EPSG:4326")

    # Load rivers and filter to GVFK contact segments (same logic as Step 4)
    from Kode.config import COLUMN_MAPPINGS, WORKFLOW_SETTINGS

    rivers_all = gpd.read_file(RIVERS_PATH, layer=RIVERS_LAYER_NAME)
    river_gvfk_col = COLUMN_MAPPINGS["rivers"]["gvfk_id"]
    contact_col = COLUMN_MAPPINGS["rivers"]["contact"]

    # Clean GVFK column
    rivers_all[river_gvfk_col] = rivers_all[river_gvfk_col].astype(str).str.strip()
    valid_gvfk_mask = rivers_all[river_gvfk_col] != ""

    # Filter for river-GVFK contact (matches Step 4 logic)
    if contact_col in rivers_all.columns:
        contact_value = WORKFLOW_SETTINGS["contact_filter_value"]
        rivers = rivers_all[
            (rivers_all[contact_col] == contact_value) & valid_gvfk_mask
        ]
    else:
        # New Grunddata format: GVFK presence IS the contact indicator
        rivers = rivers_all[valid_gvfk_mask]

    print(f"      Filtered to {len(rivers)} river segments with GVFK contact (from {len(rivers_all)} total)")

    rivers_web = rivers.to_crs("EPSG:4326")

    # Keep all rivers for display context (but connections only to GVFK segments)
    rivers_all_web = rivers_all.to_crs("EPSG:4326")

    # Load Q-points with geometries
    qpoints = gpd.read_file(
        RIVER_FLOW_POINTS_PATH, layer=RIVER_FLOW_POINTS_LAYER
    )

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

    scenario_enabled = STEP6_MAP_SETTINGS.get("generate_combined_maps", True)
    if scenario_enabled:
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
    else:
        print("    Skipping per-scenario maps (disabled in config).")

    if STEP6_MAP_SETTINGS.get("generate_overall_maps", True):
        print("    Generating overall GVFK exceedance maps...")
        _create_overall_exceedance_maps(
            rivers_web,
            segment_summary,
            site_flux,
            sites_web,
            qpoint_lookup,
            gvfk_exceedances,
        )
    else:
        print("    Skipping overall GVFK exceedance maps (disabled in config).")

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
        key = str(row["ov_id"])
        lookup[key] = (row["Q95"], row.geometry)

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

    # Add rivers (display all for context, color only GVFK segments with data)
    _add_rivers(m, rivers_web, scenario_cmix, rivers_all_web)

    # Add Q-points for affected segments
    affected_segments = scenario_flux["Nearest_River_ov_id"].unique()
    _add_qpoints(m, affected_segments, qpoint_lookup)

    # Add sites
    _add_sites(m, scenario_flux, sites_web)

    # Add connection lines (site edge → river segment)
    _add_connections(m, scenario_flux, sites_web, qpoint_lookup, rivers_web)

    # Add title and legend
    _add_title(m, scenario, len(scenario_flux), len(affected_segments))
    _add_legend(m)

    # Save map
    safe_name = (
        scenario.replace("/", "_")
        .replace("\\", "_")
        .replace(" ", "_")
        .replace(",", "_")  # Commas not allowed in Windows filenames
        .replace("(", "")
        .replace(")", "")
        .replace(":", "")
    )
    output_dir = get_visualization_path("step6", "combined", "scenarios")
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = _build_output_path(output_dir, safe_name)

    _prepare_output_file(output_path)

    # Save with proper encoding
    html_str = m.get_root().render()
    with open(str(output_path), 'w', encoding='utf-8') as f:
        f.write(html_str)


def _create_overall_exceedance_maps(
    rivers_web: gpd.GeoDataFrame,
    segment_summary: pd.DataFrame,
    site_flux: pd.DataFrame,
    sites_web: gpd.GeoDataFrame,
    qpoint_lookup: Dict[str, Tuple],
    gvfk_exceedances: pd.DataFrame | None = None,
) -> None:
    """Create GVFK-focused overview maps showing segments with exceedances."""

    if segment_summary is None or segment_summary.empty:
        print("      Segment summary is empty; skipping overall GVFK maps.")
        return

    if "Max_Exceedance_Ratio" not in segment_summary.columns:
        print("      Segment summary lacks exceedance metrics; skipping overall GVFK maps.")
        return

    exceed_segments = segment_summary[
        segment_summary["Max_Exceedance_Ratio"].notna()
        & (segment_summary["Max_Exceedance_Ratio"] > 1.0)
    ].copy()

    if exceed_segments.empty:
        print("      No river segments exceed MKK; skipping overall GVFK maps.")
        return

    gvfk_data = _load_gvfk_geodata()
    if gvfk_data is None:
        print("      GVFK polygon dataset unavailable; skipping overall GVFK maps.")
        return

    gvfk_gdf, gvfk_id_column = gvfk_data

    aggregation = _aggregate_gvfk_exceedances(exceed_segments, gvfk_exceedances)
    if aggregation is None:
        print("      Unable to aggregate GVFK exceedances; skipping overall GVFK maps.")
        return

    methods = STEP6_MAP_SETTINGS.get(
        "overall_map_count_methods", ["unique_segments", "scenario_occurrences"]
    )

    if not methods:
        print("      No overall map methods defined; skipping overall GVFK maps.")
        return

    method_configs = {
        "unique_segments": {
            "series": aggregation["unique_segment_counts"],
            "filename": "overall_gvfk_unique_segments",
            "title": "GVFK Impact Overview – Unique Segments",
            "subtitle": "Each GVFK is colored by the number of unique river segments with ≥1 MKK exceedance.",
            "legend": "Unique segments with ≥1 exceedance",
            "metric_label": "Unique segments exceeding MKK",
        },
        "scenario_occurrences": {
            "series": aggregation["scenario_occurrence_counts"],
            "filename": "overall_gvfk_scenario_occurrences",
            "title": "GVFK Impact Overview – Scenario Count",
            "subtitle": "Each GVFK is colored by the total number of exceedances across all flow scenarios.",
            "legend": "Scenario exceedance count",
            "metric_label": "Scenario exceedance count",
        },
    }

    river_geoms = {}
    if rivers_web is not None and not rivers_web.empty and "ov_id" in rivers_web.columns:
        for _, row in rivers_web.iterrows():
            seg_id = _normalize_segment_id(row.get("ov_id"))
            if seg_id and row.geometry is not None:
                river_geoms[seg_id] = row.geometry

    scenario_counts_map = aggregation["scenario_occurrence_counts"].to_dict()
    details_by_gvfk = aggregation["details_by_gvfk"]
    segment_lookup = aggregation["segment_lookup"]

    gvfk_gdf = gvfk_gdf.copy()
    gvfk_gdf["__gvfk_norm"] = gvfk_gdf[gvfk_id_column].apply(_normalize_gvfk_id)

    bounds = gvfk_gdf.total_bounds
    if np.any(~np.isfinite(bounds)):
        bounds = None
    if bounds is not None:
        center_lat = (bounds[1] + bounds[3]) / 2
        center_lon = (bounds[0] + bounds[2]) / 2
    else:
        center_lat, center_lon = 56.0, 10.0

    output_dir = get_visualization_path("step6", "combined", "overall")
    affected_segment_ids = (
        exceed_segments["Nearest_River_ov_id"].dropna().map(str).unique()
    )
    if site_flux is not None and not site_flux.empty and len(affected_segment_ids) > 0:
        flux_segment_ids = site_flux["Nearest_River_ov_id"].astype(str)
        mask = flux_segment_ids.isin(affected_segment_ids)
        overall_flux = site_flux[mask].copy()
        overall_flux["Nearest_River_ov_id"] = flux_segment_ids[mask]
    else:
        overall_flux = pd.DataFrame()

    exceed_segment_ids = set(segment_lookup.keys())

    def _add_river_basemap(fmap: folium.Map) -> None:
        if rivers_web is None or rivers_web.empty:
            return
        base_group = folium.FeatureGroup(name="All river segments", show=True)
        folium.GeoJson(
            rivers_web,
            style_function=lambda x: {
                "color": "#1f77b4",  # Clear blue instead of gray
                "weight": 2.0,  # Increased from 1.2
                "opacity": 0.6,  # Increased from 0.35
            },
        ).add_to(base_group)
        base_group.add_to(fmap)

    for method in methods:
        config = method_configs.get(method)
        if not config:
            print(f"      Warning: Unknown overall map method '{method}' – skipping.")
            continue

        series = config["series"]
        if series is None or series.empty:
            print(f"      No GVFK data for method '{method}' – skipping map.")
            continue

        counts_map = {key: value for key, value in series.items() if value > 0}
        if not counts_map:
            print(f"      Method '{method}' produced zero-impact GVFKs – skipping map.")
            continue

        working_gdf = gvfk_gdf.copy()
        working_gdf["__metric"] = working_gdf["__gvfk_norm"].map(counts_map).fillna(0)

        # Filter to only show GVFK with exceedances (metric > 0) to reduce clutter
        working_gdf = working_gdf[working_gdf["__metric"] > 0].copy()

        if working_gdf.empty:
            print(f"      Method '{method}' has no GVFK with exceedances – skipping map.")
            continue

        # Count UNIQUE GVFK, not polygon features (some GVFK have multiple disconnected areas)
        unique_gvfk_count = working_gdf["__gvfk_norm"].nunique()
        polygon_count = len(working_gdf)
        print(f"      Showing {unique_gvfk_count} GVFK with exceedances on map ({polygon_count} polygon features)")

        max_value = working_gdf["__metric"].max()
        if not np.isfinite(max_value) or max_value <= 0:
            print(f"      Method '{method}' has no positive values – skipping map.")
            continue

        colormap = LinearColormap(
            colors=["#ffffcc", "#ffeda0", "#feb24c", "#f03b20", "#bd0026"],
            vmin=1,
            vmax=float(max_value),
        )
        colormap.caption = config["legend"]

        working_gdf["__popup_html"] = working_gdf.apply(
            lambda row: _prepare_gvfk_popup(
                display_name=row[gvfk_id_column],
                norm_id=row["__gvfk_norm"],
                metric_value=row["__metric"],
                metric_label=config["metric_label"],
                scenario_count=scenario_counts_map.get(row["__gvfk_norm"], 0),
                segment_details=details_by_gvfk.get(row["__gvfk_norm"], []),
            ),
            axis=1,
        )

        m = folium.Map(
            location=[center_lat, center_lon],
            zoom_start=7,
            tiles="CartoDB positron",
            control_scale=True,
        )

        def style_fn(feature: dict) -> dict:
            value = feature["properties"].get("__metric", 0)
            return {
                "fillColor": colormap(value),
                "color": "#333333",
                "weight": 1.0,
                "fillOpacity": 0.6,
            }

        # Layer 1 (bottom): GVFK polygons
        folium.GeoJson(
            working_gdf,
            style_function=style_fn,
            tooltip=folium.GeoJsonTooltip(
                fields=[gvfk_id_column, "__metric"],
                aliases=["GVFK", config["metric_label"]],
                localize=True,
            ),
            popup=folium.GeoJsonPopup(
                fields=["__popup_html"],
                aliases=[""],
                labels=False,
                parse_html=True,
                max_width=400,
            ),
            name="GVFK impact",
        ).add_to(m)

        # Layer 2: River basemap (all segments, faint)
        _add_river_basemap(m)

        # Layer 3: Exceeding segments (highlighted)
        # Combine all exceeding segments into a single GeoDataFrame to avoid legend clutter
        if exceed_segment_ids:
            exceeding_features = []
            for seg_id, info in segment_lookup.items():
                geom = river_geoms.get(seg_id)
                if geom is None:
                    continue

                max_ratio = info.get("max_ratio")
                if isinstance(max_ratio, (int, float)) and np.isfinite(max_ratio):
                    ratio_text = f"{max_ratio:.2f}x MKK"
                else:
                    ratio_text = "n/a"

                popup_html = f"""
                <b>Segment {seg_id}</b><br>
                {info.get('segment_name', 'Unknown')}<br>
                GVFK: {info.get('segment_gvfk', 'N/A')}<br>
                Scenarios: {info.get('scenarios', 'n/a')}<br>
                Max exceedance: {ratio_text}<br>
                Sites: {info.get('site_count', 0)} ({info.get('site_ids', '')})
                """

                exceeding_features.append({
                    'geometry': geom,
                    'properties': {
                        'segment_id': seg_id,
                        'popup_html': popup_html
                    }
                })

            if exceeding_features:
                # Create GeoDataFrame from features
                exceeding_gdf = gpd.GeoDataFrame.from_features(exceeding_features, crs="EPSG:4326")

                # Add as single GeoJson layer (prevents legend clutter)
                folium.GeoJson(
                    exceeding_gdf,
                    style_function=lambda x: {
                        "color": "#FF0000",  # Bright red for maximum visibility
                        "weight": 5,  # Increased from 4
                        "opacity": 1.0,  # Full opacity
                    },
                    popup=folium.GeoJsonPopup(
                        fields=["popup_html"],
                        aliases=[""],
                        labels=False,
                        parse_html=True,
                        max_width=350,
                    ),
                    name="Exceeding segments (MKK violations)",
                ).add_to(m)

        # Layer 4: Q-points
        if not overall_flux.empty and sites_web is not None and not sites_web.empty:
            affected_segments = (
                overall_flux["Nearest_River_ov_id"].dropna().astype(str).unique()
            )
            if len(affected_segments) > 0:
                _add_qpoints(m, affected_segments, qpoint_lookup)

            # Layer 5: Sites (V1/V2 polygons)
            _add_sites(m, overall_flux, sites_web)

            # Layer 6 (top): Connections
            _add_connections_basic(m, overall_flux, sites_web, qpoint_lookup, rivers_web)

        colormap.add_to(m)
        folium.LayerControl(collapsed=False).add_to(m)
        _add_overall_title(m, config["title"], config["subtitle"])

        safe_stub = config["filename"]
        output_path = _build_output_path(
            output_dir,
            safe_stub,
            prefix="",
            suffix=".html",
        )
        _prepare_output_file(output_path)
        html_str = m.get_root().render()
        with open(str(output_path), "w", encoding="utf-8") as f:
            f.write(html_str)

        print(f"      Saved overall GVFK map ({method}) to {output_path}")


def _aggregate_gvfk_exceedances(
    exceed_segments: pd.DataFrame,
    gvfk_exceedances: pd.DataFrame | None = None,
) -> Dict[str, object] | None:
    """
    Aggregate exceedance counts per GVFK using site-level GVFK assignments.

    Uses gvfk_exceedances (site-level) instead of splitting River_Segment_GVFK
    to avoid inflating count with boundary aquifers.
    """

    required_columns = [
        "Nearest_River_ov_id",
        "River_Segment_GVFK",
        "Failing_Scenarios",
    ]
    for col in required_columns:
        if col not in exceed_segments.columns:
            print(f"      Required column '{col}' missing from segment summary.")
            return None

    records = []
    details_by_gvfk: Dict[str, List[Dict[str, object]]] = defaultdict(list)
    segment_lookup: Dict[str, Dict[str, object]] = {}

    # Build segment lookup for details
    for _, row in exceed_segments.iterrows():
        segment_id = _normalize_segment_id(row.get("Nearest_River_ov_id"))
        if not segment_id:
            continue

        if segment_id not in segment_lookup:
            segment_lookup[segment_id] = {
                "segment_name": row.get("River_Segment_Name"),
                "segment_gvfk": row.get("River_Segment_GVFK"),
                "scenarios": row.get("Failing_Scenarios", ""),
                "max_ratio": row.get("Max_Exceedance_Ratio"),
                "site_count": row.get("Site_Count")
                or row.get("Contributing_Site_Count"),
                "site_ids": row.get("Site_IDs") or row.get("Contributing_Site_IDs"),
            }

    # Use site-level GVFK from gvfk_exceedances if available
    if gvfk_exceedances is not None and not gvfk_exceedances.empty:
        # DEBUG: Check what GVFK columns are available
        print(f"      DEBUG: gvfk_exceedances columns: {list(gvfk_exceedances.columns)}")
        print(f"      DEBUG: Unique site GVFK: {gvfk_exceedances['GVFK'].nunique()}")
        if 'River_Segment_GVFK' in gvfk_exceedances.columns:
            print(f"      DEBUG: Unique River_Segment_GVFK (before split): {gvfk_exceedances['River_Segment_GVFK'].nunique()}")

        # Group by GVFK and segment to get unique GVFK-segment pairs
        for _, gvfk_row in gvfk_exceedances.iterrows():
            gvfk_value = gvfk_row.get("GVFK")
            segment_id = _normalize_segment_id(gvfk_row.get("Nearest_River_ov_id"))

            if not gvfk_value or not segment_id:
                continue

            norm_gvfk = _normalize_gvfk_id(gvfk_value)
            if not norm_gvfk:
                continue

            # Get segment details from lookup
            segment_info = segment_lookup.get(segment_id, {})
            scenario_count = max(_count_unique_values(segment_info.get("scenarios", "")), 1)

            records.append(
                {
                    "GVFK": norm_gvfk,
                    "Segment_ID": segment_id,
                    "Scenario_Count": scenario_count,
                }
            )

            # Only add to details if not already present
            existing = details_by_gvfk.get(norm_gvfk, [])
            if not any(d.get("segment_id") == segment_id for d in existing):
                details_by_gvfk[norm_gvfk].append(
                    {
                        "segment_id": segment_id,
                        "segment_name": segment_info.get("segment_name", ""),
                        "scenarios": segment_info.get("scenarios", ""),
                        "max_ratio": segment_info.get("max_ratio"),
                        "site_count": segment_info.get("site_count"),
                        "site_ids": segment_info.get("site_ids", ""),
                        "categories": segment_info.get("categories", ""),
                    }
                )
    else:
        # Fallback: split River_Segment_GVFK (old behavior)
        print("      Warning: Using fallback GVFK aggregation (may show inflated count)")
        for _, row in exceed_segments.iterrows():
            segment_id = _normalize_segment_id(row.get("Nearest_River_ov_id"))
            if not segment_id:
                continue

            gvfk_values = _split_multi_value(row.get("River_Segment_GVFK"))
            if not gvfk_values:
                continue

            scenario_count = max(_count_unique_values(row.get("Failing_Scenarios")), 1)

            for gvfk_value in gvfk_values:
                norm_gvfk = _normalize_gvfk_id(gvfk_value)
                if not norm_gvfk:
                    continue

                records.append(
                    {
                        "GVFK": norm_gvfk,
                        "Segment_ID": segment_id,
                        "Scenario_Count": scenario_count,
                    }
                )
                details_by_gvfk[norm_gvfk].append(
                    {
                        "segment_id": segment_id,
                        "segment_name": row.get("River_Segment_Name"),
                        "scenarios": row.get("Failing_Scenarios", ""),
                        "max_ratio": row.get("Max_Exceedance_Ratio"),
                        "site_count": row.get("Site_Count")
                        or row.get("Contributing_Site_Count"),
                        "site_ids": row.get("Site_IDs") or row.get("Contributing_Site_IDs"),
                        "categories": row.get("Categories", ""),
                    }
                )

    if not records:
        return None

    link_df = pd.DataFrame.from_records(records)

    # DEBUG: Show what we're aggregating
    print(f"      DEBUG: Created {len(records)} GVFK-segment records from iteration")
    print(f"      DEBUG: Unique GVFK in records: {link_df['GVFK'].nunique()}")

    segment_counts = (
        link_df.groupby("GVFK")["Segment_ID"].nunique().sort_values(ascending=False)
    )
    segment_counts.name = "unique_segment_count"

    scenario_counts = link_df.groupby("GVFK")["Scenario_Count"].sum().sort_values(
        ascending=False
    )
    scenario_counts.name = "scenario_exceedance_count"

    return {
        "unique_segment_counts": segment_counts,
        "scenario_occurrence_counts": scenario_counts,
        "details_by_gvfk": details_by_gvfk,
        "segment_lookup": segment_lookup,
    }


def _load_gvfk_geodata() -> Tuple[gpd.GeoDataFrame, str] | None:
    """Load GVFK polygons, returning GeoDataFrame in WGS84 and ID column."""

    candidate_sources = [
        (get_output_path("step3_gvfk_polygons"), None),
        (GRUNDVAND_PATH, GRUNDVAND_LAYER_NAME),
    ]

    for path, layer in candidate_sources:
        path = Path(path)
        if not path.exists():
            continue
        try:
            if layer and path.suffix.lower() == ".gdb":
                gvfk_gdf = gpd.read_file(path, layer=layer)
            else:
                gvfk_gdf = gpd.read_file(path)
        except Exception as exc:
            print(f"      Warning: Failed to load GVFK polygons from {path}: {exc}")
            continue

        id_column = _find_gvfk_id_column(gvfk_gdf.columns)
        if not id_column:
            print(
                f"      Warning: Could not identify GVFK ID column in dataset {path}."
            )
            continue

        if gvfk_gdf.crs is None:
            gvfk_gdf = gvfk_gdf.set_crs("EPSG:25832", allow_override=True)

        gvfk_gdf = gvfk_gdf.to_crs("EPSG:4326")
        return gvfk_gdf, id_column

    return None


def _find_gvfk_id_column(columns: List[str]) -> str | None:
    """Identify the GVFK identifier column from a list of column names."""
    normalized = {col.lower(): col for col in columns}
    preferred = [
        "gvfk",
        "gvforekom",
        "gv_forekom",
        "gvfk_id",
        "magasinid",
        "navn",
        "name",
    ]

    for key in preferred:
        if key in normalized:
            return normalized[key]
    return None


def _prepare_gvfk_popup(
    display_name: str | None,
    norm_id: str,
    metric_value: float,
    metric_label: str,
    scenario_count: float | int,
    segment_details: List[Dict[str, object]],
) -> str:
    """Create HTML popup for a GVFK polygon."""

    name = display_name or norm_id or "Ukendt GVFK"

    if isinstance(metric_value, (int, float)) and np.isfinite(metric_value):
        if abs(metric_value - int(metric_value)) < 1e-6:
            metric_text = f"{int(metric_value)}"
        else:
            metric_text = f"{metric_value:.1f}"
    else:
        metric_text = "0"

    if isinstance(scenario_count, (int, float)) and np.isfinite(scenario_count):
        scenario_text = f"{int(scenario_count)}"
    else:
        scenario_text = "0"

    html = [
        f"<b>{name}</b>",
        f"{metric_label}: {metric_text}",
        f"Scenario exceedances: {scenario_text}",
    ]

    if segment_details:
        html.append("<hr><b>Segments with exceedance:</b><ul>")
        for detail in segment_details[:5]:
            seg_id = detail.get("segment_id", "N/A")
            seg_name = detail.get("segment_name", "Unknown")
            scenarios = detail.get("scenarios", "n/a")
            categories = detail.get("categories", "")
            site_count = detail.get("site_count") or 0
            html.append(
                f"<li><b>{seg_id}</b> ({seg_name}) – Scenarios: {scenarios or 'n/a'}; "
                f"Sites: {site_count}; Categories: {categories or 'n/a'}</li>"
            )
        if len(segment_details) > 5:
            html.append(f"<li>...and {len(segment_details) - 5} more segments</li>")
        html.append("</ul>")

    return "<br>".join(html)


def _split_multi_value(value: object) -> List[str]:
    """Split comma-separated fields into cleaned tokens."""
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return []
    tokens = [token.strip() for token in str(value).split(",")]
    return [token for token in tokens if token]


def _normalize_gvfk_id(value: object) -> str:
    """Normalize GVFK identifier strings for consistent lookup."""
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return ""
    return str(value).strip()


def _normalize_segment_id(value: object) -> str:
    """Normalize river segment identifiers for consistent lookup."""
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return ""
    return str(value).strip()


def _count_unique_values(value: object) -> int:
    """Count unique, non-empty values in a comma-separated string."""
    tokens = _split_multi_value(value)
    return len(set(tokens))


def _add_overall_title(m: folium.Map, title: str, subtitle: str) -> None:
    """Add contextual title box for overall GVFK maps."""
    title_html = f"""
    <div style="position: fixed; top: 10px; left: 50px; width: 420px;
                background-color: rgba(255, 255, 255, 0.92); border:2px solid #333;
                z-index:9999; font-size:14px; padding: 10px; border-radius: 5px;">
    <b style="font-size:16px;">{title}</b><br>
    <span style="font-size:12px;">{subtitle}</span>
    </div>
    """
    m.get_root().html.add_child(folium.Element(title_html))


def _prepare_output_file(output_path: Path) -> None:
    """Remove existing OneDrive placeholder to avoid sync conflicts."""
    try:
        if output_path.exists():
            os.remove(str(output_path))
        else:
            try:
                os.remove(str(output_path))
            except Exception:
                pass
        time.sleep(0.05)
    except Exception:
        pass


def _build_output_path(
    output_dir: Path,
    safe_name: str,
    max_total_length: int = 240,
    *,
    prefix: str = "scenario_",
    suffix: str = ".html",
) -> Path:
    """
    Build an output path that stays within Windows path-length limits.

    Args:
        output_dir: Directory where the file should be written
        safe_name: Sanitized base label
        max_total_length: Maximum allowed total path length
        prefix: Filename prefix (default "scenario_")
        suffix: Filename suffix/extension (default ".html")
    """
    base_filename = f"{prefix}{safe_name}{suffix}"
    candidate = output_dir / base_filename
    candidate_str = str(candidate)
    if len(candidate_str) <= max_total_length:
        return candidate

    hash_suffix = hashlib.sha1(safe_name.encode("utf-8")).hexdigest()[:8]
    hash_segment = f"_{hash_suffix}"
    dynamic_suffix = f"{hash_segment}{suffix}"
    available = (
        max_total_length
        - len(str(output_dir))
        - 1
        - len(prefix)
        - len(dynamic_suffix)
    )
    trimmed = safe_name[: max(0, available)]
    filename = f"{prefix}{trimmed}{dynamic_suffix}"
    fallback_candidate = output_dir / filename

    if len(str(fallback_candidate)) <= max_total_length:
        return fallback_candidate

    # Worst case: drop trimmed portion entirely and rely on hash
    return output_dir / f"{prefix}{hash_suffix}{suffix}"


def _add_rivers(
    m: folium.Map, rivers_web: gpd.GeoDataFrame, scenario_cmix: pd.DataFrame, rivers_all_web: gpd.GeoDataFrame = None
) -> None:
    """Add river segments colored by Cmix % of MKK.

    Args:
        rivers_web: River segments with GVFK contact (for coloring based on data)
        scenario_cmix: Cmix calculation results
        rivers_all_web: ALL river segments (for context display, optional)
    """

    # Use all rivers for display if provided, otherwise use GVFK rivers only
    display_rivers = rivers_all_web if rivers_all_web is not None else rivers_web

    # Merge river geometries with Cmix data
    rivers_enriched = display_rivers.merge(
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

    # Create a single FeatureGroup for all Q-points to prevent legend clutter
    qpoint_group = folium.FeatureGroup(name="Q-points (flow measurement)", show=True)

    for ov_id in affected_segments:
        key = str(ov_id)
        if key not in qpoint_lookup:
            continue

        q95_value, qpoint_geom = qpoint_lookup[key]

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
        ).add_to(qpoint_group)

    qpoint_group.add_to(m)


def _add_sites(
    m: folium.Map, scenario_flux: pd.DataFrame, sites_web: gpd.GeoDataFrame
) -> None:
    """Add site polygons colored by V1/V2 classification."""

    # Create a single FeatureGroup for all sites to prevent legend clutter
    sites_group = folium.FeatureGroup(name="Contaminated sites (V1/V2)", show=True)

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
        ).add_to(sites_group)

    sites_group.add_to(m)


def _add_connections(
    m: folium.Map,
    scenario_flux: pd.DataFrame,
    sites_web: gpd.GeoDataFrame,
    qpoint_lookup: Dict[str, Tuple],
    rivers_web: gpd.GeoDataFrame,
) -> None:
    """Add two types of connection lines:
    1. Site → River segment (contamination pathway, colored by flux)
    2. Site → Q-point (measurement location, cyan dashed)

    Draws ONE connection line per unique (Site + GVFK) combination.
    """

    # Deduplicate: One connection per (Site + GVFK) combination
    unique_connections = scenario_flux[['Lokalitet_ID', 'GVFK', 'Nearest_River_ov_id']].drop_duplicates()

    # For flux display, aggregate total flux per connection
    flux_agg = scenario_flux.groupby(['Lokalitet_ID', 'GVFK', 'Nearest_River_ov_id'], dropna=False)['Pollution_Flux_kg_per_year'].sum().reset_index()

    # Merge to get both unique connections and aggregated flux
    connections = unique_connections.merge(flux_agg, on=['Lokalitet_ID', 'GVFK', 'Nearest_River_ov_id'], how='left')

    for _, row in connections.iterrows():
        site_id = row["Lokalitet_ID"]
        river_id = str(row["Nearest_River_ov_id"])
        gvfk_id = row["GVFK"]
        flux_kg = row["Pollution_Flux_kg_per_year"]

        # Get site geometry
        site_geom = sites_web[sites_web["Lokalitet_"] == site_id]
        if site_geom.empty:
            continue
        site_polygon = site_geom.iloc[0].geometry

        # Get river segment geometry - filter by BOTH ov_id AND GVFK
        # (same ov_id can have multiple segments, some with/without GVFK contact)
        river_segment = rivers_web[
            (rivers_web["ov_id"] == river_id) &
            (rivers_web["GVForekom"] == gvfk_id)
        ]
        if river_segment.empty:
            # Fallback: try just ov_id if GVFK filter fails
            river_segment = rivers_web[rivers_web["ov_id"] == river_id]
            if river_segment.empty:
                continue
        river_geom = river_segment.iloc[0].geometry

        # CONNECTION 1: Site → River segment (contamination pathway)
        closest_point_on_site_river, closest_point_on_river = nearest_points(site_polygon, river_geom)

        river_line_coords = [
            [closest_point_on_site_river.y, closest_point_on_site_river.x],
            [closest_point_on_river.y, closest_point_on_river.x],
        ]

        # Determine line style based on flux
        line_color, line_weight = _get_connection_style(flux_kg)

        # Get Q-point info for popup
        q95_value = "N/A"
        qpoint_geom = None
        if river_id in qpoint_lookup:
            q95_value = f"{qpoint_lookup[river_id][0]:.4f}"
            qpoint_geom = qpoint_lookup[river_id][1]

        popup_html = f"""
        <b>Contamination Pathway</b><br>
        Site: {site_id}<br>
        GVFK: {row.get('GVFK', 'N/A')}<br>
        → River: {river_id}<br>
        Total Flux: {flux_kg:.2f} kg/year<br>
        Q95: {q95_value} m³/s
        """

        # Add outline for visibility
        folium.PolyLine(
            river_line_coords,
            color="#000000",  # Black outline
            weight=line_weight + 1,
            opacity=0.6,
        ).add_to(m)

        # Add main line (river pathway)
        folium.PolyLine(
            river_line_coords,
            color=line_color,
            weight=line_weight,
            opacity=0.9,
            popup=folium.Popup(popup_html, max_width=250),
        ).add_to(m)

        # CONNECTION 2: Site → Q-point (measurement location)
        if qpoint_geom is not None:
            closest_point_on_site_qpoint, _ = nearest_points(site_polygon, qpoint_geom)

            qpoint_line_coords = [
                [closest_point_on_site_qpoint.y, closest_point_on_site_qpoint.x],
                [qpoint_geom.y, qpoint_geom.x],
            ]

            qpoint_popup_html = f"""
            <b>Q-point Measurement Link</b><br>
            Site: {site_id}<br>
            → Q-point on: {river_id}<br>
            Q95 flow: {q95_value} m³/s
            """

            # Add dashed cyan line to Q-point
            folium.PolyLine(
                qpoint_line_coords,
                color="#00FFFF",  # Cyan
                weight=2,
                opacity=0.7,
                dash_array="5, 10",  # Dashed pattern
                popup=folium.Popup(qpoint_popup_html, max_width=250),
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


def _add_connections_basic(
    m: folium.Map,
    scenario_flux: pd.DataFrame,
    sites_web: gpd.GeoDataFrame,
    qpoint_lookup: Dict[str, Tuple],
    rivers_web: gpd.GeoDataFrame,
) -> None:
    """Add two types of simplified connection lines for overview maps:
    1. Site → River segment (contamination pathway, blue)
    2. Site → Q-point (measurement location, cyan dashed)

    Draws ONE connection line per unique (Site + GVFK) combination.
    """

    # Create FeatureGroups for different connection types
    river_connections_group = folium.FeatureGroup(name="Site → River (contamination pathway)", show=True)
    qpoint_connections_group = folium.FeatureGroup(name="Site → Q-point (measurement)", show=True)

    # Deduplicate: One connection per (Site + GVFK) combination
    unique_connections = scenario_flux[['Lokalitet_ID', 'GVFK', 'Nearest_River_ov_id']].drop_duplicates()

    for _, row in unique_connections.iterrows():
        site_id = row["Lokalitet_ID"]
        river_id = row["Nearest_River_ov_id"]
        gvfk_id = row["GVFK"]

        site_geom = sites_web[sites_web["Lokalitet_"] == site_id]
        if site_geom.empty:
            continue
        site_polygon = site_geom.iloc[0].geometry

        # Get river segment geometry - filter by BOTH ov_id AND GVFK
        # (same ov_id can have multiple segments, some with/without GVFK contact)
        river_segment = rivers_web[
            (rivers_web["ov_id"] == river_id) &
            (rivers_web["GVForekom"] == gvfk_id)
        ]
        if river_segment.empty:
            # Fallback: try just ov_id if GVFK filter fails
            river_segment = rivers_web[rivers_web["ov_id"] == river_id]
            if river_segment.empty:
                continue
        river_geom = river_segment.iloc[0].geometry

        # CONNECTION 1: Site → River segment
        closest_point_on_site_river, closest_point_on_river = nearest_points(site_polygon, river_geom)

        river_line_coords = [
            [closest_point_on_site_river.y, closest_point_on_site_river.x],
            [closest_point_on_river.y, closest_point_on_river.x],
        ]

        folium.PolyLine(
            river_line_coords,
            color="#00BFFF",  # Blue
            weight=2,
            opacity=0.65,
        ).add_to(river_connections_group)

        # CONNECTION 2: Site → Q-point
        lookup_key = str(river_id)
        if lookup_key in qpoint_lookup:
            qpoint_geom = qpoint_lookup[lookup_key][1]

            closest_point_on_site_qpoint, _ = nearest_points(site_polygon, qpoint_geom)

            qpoint_line_coords = [
                [closest_point_on_site_qpoint.y, closest_point_on_site_qpoint.x],
                [qpoint_geom.y, qpoint_geom.x],
            ]

            folium.PolyLine(
                qpoint_line_coords,
                color="#00FFFF",  # Cyan
                weight=2,
                opacity=0.5,
                dash_array="5, 10",  # Dashed pattern
            ).add_to(qpoint_connections_group)

    river_connections_group.add_to(m)
    qpoint_connections_group.add_to(m)


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
    <p style="margin:2px 0; font-size:11px;"><span style="color:#FFB366;">━━</span> Site → River (contamination pathway)</p>
    <p style="margin:2px 0; font-size:11px;"><span style="color:#00FFFF;">╌╌</span> Site → Q-point (measurement link)</p>
    <p style="margin:2px 0; font-size:10px; font-style:italic;">Solid: Color/width by flux magnitude</p>
    <p style="margin:2px 0; font-size:10px; font-style:italic;">Dashed: Shows Q-point location</p>

    <hr style="margin:5px 0;">
    <p style="margin:3px 0; font-weight:bold;">Q-points</p>
    <p style="margin:2px 0;"><span style="color:#00BFFF; font-size:16px;">●</span> Q95 flow measurement point</p>
    <p style="margin:2px 0; font-size:10px; font-style:italic;">(May be upstream/downstream from entry)</p>
    </div>
    """
    m.get_root().html.add_child(folium.Element(legend_html))
