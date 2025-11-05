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
import numpy as np

# Ensure repository root is importable
REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from Kode.config import RIVERS_PATH, get_visualization_path, get_output_path


def analyze_and_visualize_step6(
    site_flux: pd.DataFrame,
    segment_flux: pd.DataFrame,
    cmix_results: pd.DataFrame,
    segment_summary: pd.DataFrame,
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

    # Create combined impact map (sites + rivers + connection lines)
    print("\nGenerating combined impact maps...")
    try:
        from .step6_combined_map import create_combined_impact_maps
    except ImportError:
        from step6_combined_map import create_combined_impact_maps
    create_combined_impact_maps(site_flux, segment_summary)

    print("Maps saved to Resultater/Figures/step6/")


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
