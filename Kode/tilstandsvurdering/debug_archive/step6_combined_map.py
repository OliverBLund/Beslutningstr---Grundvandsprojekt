"""
Step 6 Combined Impact Map
===========================

Creates interactive maps showing:
1. Contamination site polygons (colored by flux)
2. River segments (colored by MKK exceedance)
3. Connection lines from sites to rivers (showing pollution pathways)

DATA FLOW DOCUMENTATION:
========================

INPUT DATA SOURCES:
-------------------

1. site_flux DataFrame (from step6_flux_site_segment.csv)
   - Origin: Step 6 _calculate_flux() output
   - Key columns:
     * Lokalitet_ID - Site identifier
     * GVFK - Groundwater body
     * Distance_to_River_m - **FROM STEP 4** (preserved through Step 5 → Step 6)
     * Nearest_River_FID - River segment index (for geometry lookup)
     * Nearest_River_ov_id - River ID
     * Nearest_River_ov_navn - River name
     * Qualifying_Substance - Specific compound (e.g., "Benzen")
     * Qualifying_Category - Substance category (e.g., "BTXER", "LOSSEPLADS")
     * Pollution_Flux_kg_per_year - Calculated flux for this site-substance-river combo

   - Structure: One row per (site, GVFK, substance, river) combination
   - Example: Site "101-00002" with 3 substances → 3 rows, SAME distance, SAME river

2. segment_summary DataFrame (from step6_segment_summary.csv)
   - Origin: Step 6 _build_segment_summary() output
   - Key columns:
     * Nearest_River_ov_id - River segment ID
     * Max_Exceedance_Ratio - Worst MKK exceedance across all scenarios/substances
     * Total_Flux_kg_per_year - Total pollution flux to this river segment
   - Used for: Coloring river segments by environmental impact

3. Site geometries (from step3_v1v2_sites.shp)
   - Origin: Step 3 output (V1/V2 sites intersected with GVFKs)
   - Key columns:
     * Lokalitet_ - Site ID (NOTE: underscore suffix, not "Lokalitet_ID")
     * geometry - Polygon boundaries of contamination site
   - Used for: Drawing site polygons and calculating centroids for connection lines

4. River geometries (from RIVERS_PATH shapefile)
   - Origin: Input data (Rivers_gvf_rev20230825_kontakt.shp)
   - Key columns:
     * FID - Feature ID (row index, used in Nearest_River_FID)
     * ov_id - National river segment ID
     * ov_navn - River segment name
     * geometry - LineString of river segment
   - Used for: Drawing river segments and finding nearest point for connections

CONNECTION LOGIC:
-----------------

Each connection line represents a unique (Lokalitet_ID, GVFK, Nearest_River_FID) combination:

- Site "A" in GVFK "X" → River segment "R1" = ONE connection line
- Site "A" in GVFK "Y" → River segment "R2" = DIFFERENT connection line
- Same site can have MULTIPLE connection lines if it affects multiple GVFKs

Within each connection, multiple SUBSTANCES may exist:
- Site "A" → River "R1" with BTXER (flux: 10 kg/yr)
- Site "A" → River "R1" with PAH (flux: 5 kg/yr)
→ These are the SAME CONNECTION, but shown in different filtered maps

Distance value is from Step 4:
- Step 4 calculates: Lokalitet + GVFK → nearest river segment + distance
- Step 5 inherits: Filters by substance thresholds, keeps distance
- Step 6 inherits: Calculates flux, keeps distance
→ Distance displayed = EXACTLY the same as Step 4 distance calculation

MAP TYPES:
----------

1. Overall Map (combined_impact_overall.html)
   - Shows ALL substances combined
   - River color = worst exceedance across all substances
   - Site color = total flux across all substances
   - Line color = total flux on that connection

2. Category Maps (combined_impact_BTXER.html, etc.)
   - Shows only sites/rivers affected by that category
   - Rivers not affected by this category = grayed out
   - Connection lines only for this category
   - Top 5 categories generated

3. Future: Substance-specific maps
   - Same logic but filter by specific compound
"""

from __future__ import annotations

import sys
from pathlib import Path
import pandas as pd
import geopandas as gpd
import folium
import numpy as np
from shapely.ops import nearest_points

# Ensure repository root is importable
REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from Kode.config import RIVERS_PATH, get_visualization_path, get_output_path, STEP6_MAP_SETTINGS


def create_combined_impact_maps(site_flux: pd.DataFrame, segment_summary: pd.DataFrame) -> None:
    """
    Generate combined impact maps showing sites, rivers, and connections.

    Creates 4 versions of maps based on different river metrics:
    1. Cmix % of MKK (Q95 scenario)
    2. Absolute Cmix (µg/L, Q95 scenario)
    3. MKK Exceedance Ratio
    4. Total Flux (kg/year)

    Args:
        site_flux: DataFrame from step6_flux_site_segment.csv
        segment_summary: DataFrame from step6_segment_summary.csv
    """

    print("  Creating combined impact maps (sites + rivers + connections)...")

    # Load geometries
    print("    Loading geometries...")
    sites_gdf = gpd.read_file(get_output_path("step3_v1v2_sites"), encoding='utf-8')
    sites_web = sites_gdf.to_crs('EPSG:4326')

    rivers = gpd.read_file(RIVERS_PATH, encoding='utf-8')
    rivers_web = rivers.to_crs('EPSG:4326')

    # Load Cmix data for Q95 scenario
    print("    Loading Cmix data (Q95 scenario)...")
    cmix_path = get_output_path("step6_cmix_results")
    cmix_results = pd.read_csv(cmix_path, encoding='utf-8')
    cmix_q95 = cmix_results[cmix_results['Flow_Scenario'] == 'Q95'].copy()

    # Prepare connection data
    print("    Preparing connection data...")
    connection_data = site_flux.groupby(
        ['Lokalitet_ID', 'GVFK', 'Nearest_River_FID', 'Nearest_River_ov_id',
         'Distance_to_River_m', 'Nearest_River_ov_navn']
    ).agg({
        'Pollution_Flux_kg_per_year': 'sum',
        'Qualifying_Category': lambda x: ', '.join(x.unique()[:3]),
        'Qualifying_Substance': 'count'
    }).reset_index()

    connection_data.columns = [
        'Lokalitet_ID', 'GVFK', 'Nearest_River_FID', 'Nearest_River_ov_id',
        'Distance_to_River_m', 'Nearest_River_ov_navn', 'Total_Flux_kg_per_year',
        'Categories', 'Substance_Count'
    ]

    print(f"    Found {len(connection_data)} unique site-river connections")

    # Prepare river data with worst-case Cmix per segment
    print("    Preparing river metrics from Q95 scenario...")
    river_metrics = _prepare_river_metrics(cmix_q95, segment_summary)

    # Create 4 versions of overall map (one for each river metric)
    print("    Creating overall maps with different river metrics...")

    river_metrics_to_generate = STEP6_MAP_SETTINGS.get('river_metrics_overall', ['cmix_pct_mkk'])
    metric_suffix_map = {
        'cmix_pct_mkk': 'cmix_pct',
        'cmix_absolute': 'cmix_absolute',
        'exceedance_ratio': 'exceedance',
        'total_flux': 'flux'
    }

    for metric in river_metrics_to_generate:
        suffix = metric_suffix_map.get(metric, metric)
        _create_overall_map(sites_web, rivers_web, connection_data, river_metrics, site_flux,
                           river_metric=metric, map_suffix=suffix)

    # Create category-specific maps (ALL categories, not just top 5)
    if STEP6_MAP_SETTINGS.get('generate_category_maps', True):
        print("    Creating category-specific maps...")
        categories = site_flux['Qualifying_Category'].dropna().unique()
        default_metric = STEP6_MAP_SETTINGS.get('river_metric_filtered', 'cmix_pct_mkk')

        print(f"      Generating maps for {len(categories)} categories...")
        for category in sorted(categories):
            _create_filtered_map(
                sites_web, rivers_web, site_flux, river_metrics,
                filter_col='Qualifying_Category',
                filter_value=category,
                river_metric=default_metric
            )

    # Create compound-specific maps
    if STEP6_MAP_SETTINGS.get('generate_compound_maps', True):
        print("    Creating compound-specific maps...")
        compounds_to_map = STEP6_MAP_SETTINGS.get('compounds_to_map', [])
        default_metric = STEP6_MAP_SETTINGS.get('river_metric_filtered', 'cmix_pct_mkk')

        # Filter to only compounds that exist in the data
        available_compounds = site_flux['Qualifying_Substance'].dropna().unique()
        compounds_found = [c for c in compounds_to_map if c in available_compounds]
        compounds_missing = [c for c in compounds_to_map if c not in available_compounds]

        if compounds_missing:
            print(f"      WARNING: Compounds not found in data: {', '.join(compounds_missing)}")

        print(f"      Generating maps for {len(compounds_found)} compounds...")
        for compound in compounds_found:
            _create_filtered_map(
                sites_web, rivers_web, site_flux, river_metrics,
                filter_col='Qualifying_Substance',
                filter_value=compound,
                river_metric=default_metric
            )


def _prepare_river_metrics(cmix_q95: pd.DataFrame, segment_summary: pd.DataFrame) -> pd.DataFrame:
    """
    Prepare river segment metrics by aggregating worst-case values per segment.

    For each river segment, finds the worst substance in terms of:
    - Cmix (absolute concentration)
    - Cmix as % of MKK
    - Exceedance ratio
    Also includes total flux from segment_summary.

    Returns DataFrame with one row per river segment.
    """

    # Filter out rows with NaN values before aggregation
    cmix_valid = cmix_q95[cmix_q95['Cmix_ug_L'].notna()].copy()

    if cmix_valid.empty:
        # No valid Cmix data, return segment_summary with NaN columns
        river_metrics = segment_summary[['Nearest_River_ov_id', 'River_Segment_Name', 'Total_Flux_kg_per_year']].copy()
        river_metrics['Cmix_ug_L'] = np.nan
        river_metrics['MKK_ug_L'] = np.nan
        river_metrics['Qualifying_Substance'] = ''
        river_metrics['Exceedance_Ratio'] = np.nan
        river_metrics['Cmix_pct_MKK'] = np.nan
        return river_metrics

    # Get worst Cmix per segment (highest concentration)
    worst_cmix_idx = cmix_valid.groupby('Nearest_River_ov_id')['Cmix_ug_L'].idxmax()
    worst_cmix = cmix_valid.loc[worst_cmix_idx]

    # Get worst exceedance per segment (highest ratio, excluding NaN)
    cmix_with_exceedance = cmix_valid[cmix_valid['Exceedance_Ratio'].notna()].copy()
    if not cmix_with_exceedance.empty:
        worst_exceedance_idx = cmix_with_exceedance.groupby('Nearest_River_ov_id')['Exceedance_Ratio'].idxmax()
        worst_exceedance = cmix_with_exceedance.loc[worst_exceedance_idx]
    else:
        worst_exceedance = pd.DataFrame(columns=['Nearest_River_ov_id', 'Exceedance_Ratio'])

    # Combine metrics
    river_metrics = segment_summary[['Nearest_River_ov_id', 'River_Segment_Name', 'Total_Flux_kg_per_year']].copy()

    # Add worst Cmix
    river_metrics = river_metrics.merge(
        worst_cmix[['Nearest_River_ov_id', 'Cmix_ug_L', 'MKK_ug_L', 'Qualifying_Substance']],
        on='Nearest_River_ov_id',
        how='left',
        suffixes=('', '_cmix')
    )

    # Add worst exceedance
    river_metrics = river_metrics.merge(
        worst_exceedance[['Nearest_River_ov_id', 'Exceedance_Ratio']],
        on='Nearest_River_ov_id',
        how='left',
        suffixes=('', '_exc')
    )

    # Calculate Cmix as % of MKK
    river_metrics['Cmix_pct_MKK'] = np.where(
        river_metrics['MKK_ug_L'].notna() & (river_metrics['MKK_ug_L'] > 0),
        (river_metrics['Cmix_ug_L'] / river_metrics['MKK_ug_L']) * 100,
        np.nan
    )

    return river_metrics


def _create_overall_map(
    sites_web: gpd.GeoDataFrame,
    rivers_web: gpd.GeoDataFrame,
    connection_data: pd.DataFrame,
    river_metrics: pd.DataFrame,
    site_flux: pd.DataFrame,
    river_metric: str = 'cmix_pct_mkk',
    map_suffix: str = 'overall'
) -> None:
    """
    Create overall combined map with all substances.

    Args:
        river_metric: Which metric to use for river coloring
            - 'cmix_pct_mkk': Cmix as % of MKK (traffic light)
            - 'cmix_absolute': Absolute Cmix (µg/L)
            - 'exceedance_ratio': MKK exceedance ratio
            - 'total_flux': Total pollution flux (kg/year)
        map_suffix: Suffix for output filename
    """

    print(f"      Creating overall map (rivers by {river_metric})...")

    # Map center
    bounds = sites_web.total_bounds
    center_lat = (bounds[1] + bounds[3]) / 2
    center_lon = (bounds[0] + bounds[2]) / 2

    m = folium.Map(location=[center_lat, center_lon], zoom_start=8, tiles='OpenStreetMap')

    # Add rivers with specified metric
    rivers_enriched = rivers_web.merge(
        river_metrics,
        left_on="ov_id",
        right_on="Nearest_River_ov_id",
        how="left"
    )

    for idx, river in rivers_enriched.iterrows():
        color = _get_river_color(river, river_metric)
        weight = 6  # Increased width for better visibility

        popup = _create_river_popup(river, river_metric)

        folium.GeoJson(
            river.geometry,
            style_function=lambda x, c=color, w=weight: {'color': c, 'weight': w, 'opacity': 0.8},
            popup=folium.Popup(popup, max_width=300)
        ).add_to(m)

    # Add sites
    site_totals = site_flux.groupby('Lokalitet_ID').agg({
        'Pollution_Flux_kg_per_year': 'sum',
        'Qualifying_Category': lambda x: ', '.join(x.unique()[:3]),
        'Lokalitetsnavn': 'first'
    }).reset_index()

    sites_enriched = sites_web.merge(site_totals, left_on='Lokalitet_', right_on='Lokalitet_ID', how='inner')

    for idx, site in sites_enriched.iterrows():
        color = _get_site_color(site['Pollution_Flux_kg_per_year'])

        popup = f"""
        <b>Site: {site.get('Lokalitetsnavn', 'Unknown')}</b><br>
        ID: {site['Lokalitet_ID']}<br>
        Total Flux: {site['Pollution_Flux_kg_per_year']:.2f} kg/year<br>
        Categories: {site['Qualifying_Category']}
        """

        folium.GeoJson(
            site.geometry,
            style_function=lambda x, c=color: {'fillColor': c, 'color': 'black', 'weight': 1, 'fillOpacity': 0.6},
            popup=folium.Popup(popup, max_width=250)
        ).add_to(m)

    # Add connection lines
    for idx, conn in connection_data.iterrows():
        _add_connection_line(m, conn, sites_web, rivers_web)

    _add_legend(m, river_metric)

    # Save to overall subfolder
    output_dir = get_visualization_path("step6") / "overall"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"combined_impact_{map_suffix}.html"
    m.save(str(output_path))
    print(f"      Saved: {output_path}")


def _create_filtered_map(
    sites_web: gpd.GeoDataFrame,
    rivers_web: gpd.GeoDataFrame,
    site_flux: pd.DataFrame,
    river_metrics: pd.DataFrame,
    filter_col: str,
    filter_value: str,
    river_metric: str = 'cmix_pct_mkk'
) -> None:
    """Create filtered map for specific category/substance."""

    print(f"        Creating map for {filter_value}...")

    filtered_flux = site_flux[site_flux[filter_col] == filter_value].copy()

    if filtered_flux.empty:
        print(f"          No data for {filter_value}, skipping...")
        return

    connection_data = filtered_flux.groupby(
        ['Lokalitet_ID', 'GVFK', 'Nearest_River_FID', 'Nearest_River_ov_id',
         'Distance_to_River_m', 'Nearest_River_ov_navn']
    ).agg({'Pollution_Flux_kg_per_year': 'sum'}).reset_index()

    bounds = sites_web.total_bounds
    center_lat = (bounds[1] + bounds[3]) / 2
    center_lon = (bounds[0] + bounds[2]) / 2

    m = folium.Map(location=[center_lat, center_lon], zoom_start=8, tiles='OpenStreetMap')

    # Add rivers (colored by metric, gray out unaffected ones)
    affected_rivers = filtered_flux['Nearest_River_ov_id'].unique()

    # Merge rivers with metrics
    rivers_enriched = rivers_web.merge(
        river_metrics,
        left_on="ov_id",
        right_on="Nearest_River_ov_id",
        how="left"
    )

    for idx, river in rivers_enriched.iterrows():
        if river.get('ov_id') in affected_rivers:
            color = _get_river_color(river, river_metric)
            weight = 6  # Increased for better visibility
            opacity = 0.8
            popup = _create_river_popup(river, river_metric)
        else:
            color = 'lightgray'
            weight = 2  # Slightly thicker even for unaffected rivers
            opacity = 0.3
            popup = f"<b>{river.get('ov_navn', 'Unknown')}</b><br>Not affected by {filter_value}"

        folium.GeoJson(
            river.geometry,
            style_function=lambda x, c=color, w=weight, o=opacity: {'color': c, 'weight': w, 'opacity': o},
            popup=folium.Popup(popup, max_width=300)
        ).add_to(m)

    # Add sites
    affected_sites = filtered_flux['Lokalitet_ID'].unique()
    site_totals = filtered_flux.groupby('Lokalitet_ID').agg({
        'Pollution_Flux_kg_per_year': 'sum',
        'Lokalitetsnavn': 'first'
    }).reset_index()

    sites_enriched = sites_web[sites_web['Lokalitet_'].isin(affected_sites)].merge(
        site_totals, left_on='Lokalitet_', right_on='Lokalitet_ID', how='inner'
    )

    for idx, site in sites_enriched.iterrows():
        color = _get_site_color(site['Pollution_Flux_kg_per_year'])

        popup = f"""
        <b>{filter_value}</b><br>
        Site: {site.get('Lokalitetsnavn', 'Unknown')}<br>
        Flux: {site['Pollution_Flux_kg_per_year']:.2f} kg/year
        """

        folium.GeoJson(
            site.geometry,
            style_function=lambda x, c=color: {'fillColor': c, 'color': 'black', 'weight': 1, 'fillOpacity': 0.6},
            popup=folium.Popup(popup, max_width=250)
        ).add_to(m)

    # Add connection lines
    for idx, conn in connection_data.iterrows():
        _add_connection_line(m, conn, sites_web, rivers_web)

    # Add title
    filter_type = "Category" if filter_col == "Qualifying_Category" else "Compound"
    title_html = f'''
    <div style="position: fixed; top: 10px; left: 50px; width: 300px;
                background-color: white; border:2px solid grey; z-index:9999;
                font-size:16px; padding: 10px">
    <b>{filter_type}: {filter_value}</b><br>
    <span style="font-size:12px;">Sites: {len(affected_sites)}, Rivers: {len(affected_rivers)}</span>
    </div>
    '''
    m.get_root().html.add_child(folium.Element(title_html))

    _add_legend(m, river_metric)

    # Create safe filename (remove special characters)
    safe_name = filter_value.replace('/', '_').replace('\\', '_').replace(' ', '_').replace('(', '').replace(')', '')

    # Save to appropriate subfolder
    if filter_col == "Qualifying_Category":
        output_dir = get_visualization_path("step6") / "categories"
    else:  # Qualifying_Substance
        output_dir = get_visualization_path("step6") / "compounds"

    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"combined_impact_{safe_name}.html"
    m.save(str(output_path))
    print(f"          Saved: {output_path}")


def _add_connection_line(m, conn, sites_web, rivers_web):
    """
    Add connection line from site to river.

    CRITICAL: Uses edge-to-edge geometry (same as Step 4) not centroid-to-edge.
    This ensures visual line length matches the numerical distance value.
    """

    # Get site polygon (NOT centroid - we need edge-to-edge like Step 4)
    site_geom = sites_web[sites_web['Lokalitet_'] == conn['Lokalitet_ID']]
    if site_geom.empty:
        return
    site_polygon = site_geom.iloc[0].geometry

    # Get river geometry
    river_geom = rivers_web[rivers_web.index == conn['Nearest_River_FID']]
    if river_geom.empty:
        return
    river_line = river_geom.iloc[0].geometry

    # Find nearest points between site EDGE and river (same as Step 4)
    closest_point_on_site, closest_point_on_river = nearest_points(site_polygon, river_line)

    # Create line from edge to edge
    line_coords = [
        [closest_point_on_site.y, closest_point_on_site.x],
        [closest_point_on_river.y, closest_point_on_river.x]
    ]

    # Use 'Total_Flux_kg_per_year' from connection_data aggregation
    flux_value = conn.get('Total_Flux_kg_per_year', conn.get('Pollution_Flux_kg_per_year', 0))

    # New color scheme: Orange/red gradient (warm = pathway)
    line_color = _get_line_color(flux_value)
    line_weight = _get_line_weight(flux_value)

    popup = f"""
    <b>Connection</b><br>
    Site: {conn['Lokalitet_ID']}<br>
    → River: {conn['Nearest_River_ov_navn']}<br>
    <b>Distance: {conn['Distance_to_River_m']:.1f} m</b> (from Step 4)<br>
    Flux: {flux_value:.2f} kg/year<br>
    Substances: {conn.get('Substance_Count', 'N/A')}
    """

    # Add line with black outline for visibility
    folium.PolyLine(
        line_coords,
        color='black',  # Outline
        weight=line_weight + 2,
        opacity=0.8,
        popup=folium.Popup(popup, max_width=250)
    ).add_to(m)

    folium.PolyLine(
        line_coords,
        color=line_color,  # Main line
        weight=line_weight,
        opacity=0.9
    ).add_to(m)


def _get_river_style(exceedance_ratio, flux_kg_per_year):
    """Determine river segment color and weight."""

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

    if pd.isna(flux_kg_per_year) or flux_kg_per_year <= 0:
        weight = 2
    else:
        weight = min(10, 2 + np.log10(max(0.01, flux_kg_per_year)))

    return color, weight


def _get_site_color(flux_kg_per_year):
    """
    Determine color for site polygons based on flux.
    Uses BLUE gradient (cool color = source).
    """
    if pd.isna(flux_kg_per_year) or flux_kg_per_year <= 0:
        return 'lightgray'
    elif flux_kg_per_year < 1:
        return '#B3D9FF'  # Light blue
    elif flux_kg_per_year < 10:
        return '#4DA6FF'  # Medium blue
    elif flux_kg_per_year < 100:
        return '#0066CC'  # Dark blue
    else:
        return '#003366'  # Navy


def _get_line_color(flux_kg_per_year):
    """
    Determine color for connection lines based on flux.
    Uses ORANGE/RED gradient (warm color = pathway).
    """
    if pd.isna(flux_kg_per_year) or flux_kg_per_year <= 0:
        return '#CCCCCC'  # Light gray
    elif flux_kg_per_year < 1:
        return '#FFB366'  # Light orange
    elif flux_kg_per_year < 10:
        return '#FF8C1A'  # Orange
    elif flux_kg_per_year < 100:
        return '#E64D1A'  # Red-orange
    else:
        return '#B30000'  # Dark red


def _get_line_weight(flux_kg_per_year):
    """
    Determine line weight based on flux magnitude (log scale).
    """
    if pd.isna(flux_kg_per_year) or flux_kg_per_year <= 0:
        return 2
    elif flux_kg_per_year < 1:
        return 2
    elif flux_kg_per_year < 10:
        return 3
    elif flux_kg_per_year < 100:
        return 5
    else:
        return 7


def _get_river_color(river_row, metric: str):
    """
    Get color for river segment based on specified metric.
    Uses traffic light gradient (green → yellow → red).
    """
    if metric == 'cmix_pct_mkk':
        # Cmix as % of MKK (traffic light)
        value = river_row.get('Cmix_pct_MKK')
        if pd.isna(value):
            return '#CCCCCC'  # Gray for no data
        elif value < 25:
            return '#006400'  # Dark green (safe)
        elif value < 50:
            return '#90EE90'  # Light green (acceptable)
        elif value < 100:
            return '#FFFF00'  # Yellow (approaching limit)
        elif value < 200:
            return '#FFA500'  # Orange (exceedance)
        elif value < 500:
            return '#FF4500'  # Red-orange (significant)
        else:
            return '#8B0000'  # Dark red (severe)

    elif metric == 'cmix_absolute':
        # Absolute Cmix (µg/L)
        value = river_row.get('Cmix_ug_L')
        if pd.isna(value):
            return '#CCCCCC'
        elif value < 1:
            return '#006400'  # Dark green
        elif value < 10:
            return '#90EE90'  # Light green
        elif value < 50:
            return '#FFFF00'  # Yellow
        elif value < 100:
            return '#FFA500'  # Orange
        elif value < 500:
            return '#FF4500'  # Red-orange
        else:
            return '#8B0000'  # Dark red

    elif metric == 'exceedance_ratio':
        # MKK Exceedance Ratio
        value = river_row.get('Exceedance_Ratio')
        if pd.isna(value):
            return '#CCCCCC'
        elif value < 0.5:
            return '#006400'
        elif value < 1:
            return '#90EE90'
        elif value < 2:
            return '#FFFF00'
        elif value < 5:
            return '#FFA500'
        elif value < 10:
            return '#FF4500'
        else:
            return '#8B0000'

    elif metric == 'total_flux':
        # Total flux (kg/year)
        value = river_row.get('Total_Flux_kg_per_year')
        if pd.isna(value) or value <= 0:
            return '#CCCCCC'
        elif value < 1:
            return '#006400'
        elif value < 10:
            return '#90EE90'
        elif value < 50:
            return '#FFFF00'
        elif value < 100:
            return '#FFA500'
        elif value < 500:
            return '#FF4500'
        else:
            return '#8B0000'

    return '#CCCCCC'  # Default gray


def _create_river_popup(river_row, metric: str):
    """Create popup HTML for river segment based on metric."""

    river_name = river_row.get('ov_navn', 'Unknown')
    river_id = river_row.get('ov_id', 'N/A')
    gvfk = river_row.get('GVForekom', 'N/A')

    base_html = f"<b>River: {river_name}</b><br>ID: {river_id}<br><b>GVFK: {gvfk}</b><br><hr style='margin:3px 0;'>"

    if metric == 'cmix_pct_mkk':
        value_pct = river_row.get('Cmix_pct_MKK')
        value_abs = river_row.get('Cmix_ug_L')
        mkk_value = river_row.get('MKK_ug_L')
        substance = river_row.get('Qualifying_Substance', 'Unknown')
        if pd.notna(value_pct):
            base_html += f"<b>Cmix: {value_pct:.1f}% of MKK</b><br>"
            base_html += f"Cmix: {value_abs:.2f} µg/L<br>"
            base_html += f"MKK: {mkk_value:.2f} µg/L<br>"
            base_html += f"Substance: {substance}<br>"
            base_html += f"(Q95 scenario, worst case)"
        else:
            base_html += "No Cmix data available"

    elif metric == 'cmix_absolute':
        value = river_row.get('Cmix_ug_L')
        substance = river_row.get('Qualifying_Substance', 'Unknown')
        if pd.notna(value):
            base_html += f"<b>Cmix: {value:.2f} µg/L</b><br>"
            base_html += f"Substance: {substance}<br>"
            base_html += f"(Q95 scenario, worst case)"
        else:
            base_html += "No Cmix data available"

    elif metric == 'exceedance_ratio':
        value = river_row.get('Exceedance_Ratio')
        if pd.notna(value):
            base_html += f"<b>Exceedance: {value:.2f}x MKK</b><br>"
            if value > 1:
                base_html += f"<span style='color:red;'>Above standard</span>"
            else:
                base_html += f"<span style='color:green;'>Below standard</span>"
        else:
            base_html += "No exceedance data"

    elif metric == 'total_flux':
        value = river_row.get('Total_Flux_kg_per_year')
        if pd.notna(value):
            base_html += f"<b>Total Flux: {value:.2f} kg/year</b>"
        else:
            base_html += "No flux data"

    return base_html


def _add_legend(m, river_metric: str = 'cmix_pct_mkk'):
    """Add legend to map based on river metric."""

    # River legend varies by metric
    if river_metric == 'cmix_pct_mkk':
        river_legend = '''
        <p style="margin:0; font-weight:bold;">Rivers (Cmix % of MKK)</p>
        <p style="margin:2px 0; font-size:11px;"><span style="color:#006400;">━━</span> <25% <span style="color:#90EE90;">━━</span> 25-50% <span style="color:#FFFF00;">━━</span> 50-100%</p>
        <p style="margin:2px 0; font-size:11px;"><span style="color:#FFA500;">━━</span> 100-200% <span style="color:#FF4500;">━━</span> 200-500% <span style="color:#8B0000;">━━</span> >500%</p>
        '''
    elif river_metric == 'cmix_absolute':
        river_legend = '''
        <p style="margin:0; font-weight:bold;">Rivers (Cmix µg/L)</p>
        <p style="margin:2px 0; font-size:11px;"><span style="color:#006400;">━━</span> <1 <span style="color:#90EE90;">━━</span> 1-10 <span style="color:#FFFF00;">━━</span> 10-50</p>
        <p style="margin:2px 0; font-size:11px;"><span style="color:#FFA500;">━━</span> 50-100 <span style="color:#FF4500;">━━</span> 100-500 <span style="color:#8B0000;">━━</span> >500</p>
        '''
    elif river_metric == 'exceedance_ratio':
        river_legend = '''
        <p style="margin:0; font-weight:bold;">Rivers (Exceedance Ratio)</p>
        <p style="margin:2px 0; font-size:11px;"><span style="color:#006400;">━━</span> <0.5x <span style="color:#90EE90;">━━</span> 0.5-1x <span style="color:#FFFF00;">━━</span> 1-2x</p>
        <p style="margin:2px 0; font-size:11px;"><span style="color:#FFA500;">━━</span> 2-5x <span style="color:#FF4500;">━━</span> 5-10x <span style="color:#8B0000;">━━</span> >10x</p>
        '''
    else:  # total_flux
        river_legend = '''
        <p style="margin:0; font-weight:bold;">Rivers (Total Flux kg/yr)</p>
        <p style="margin:2px 0; font-size:11px;"><span style="color:#006400;">━━</span> <1 <span style="color:#90EE90;">━━</span> 1-10 <span style="color:#FFFF00;">━━</span> 10-50</p>
        <p style="margin:2px 0; font-size:11px;"><span style="color:#FFA500;">━━</span> 50-100 <span style="color:#FF4500;">━━</span> 100-500 <span style="color:#8B0000;">━━</span> >500</p>
        '''

    legend_html = f'''
    <div style="position: fixed; bottom: 50px; right: 50px; width: 240px; height: 280px;
                background-color: white; border:2px solid grey; z-index:9999;
                font-size:13px; padding: 10px">
    <p style="margin:0; font-weight:bold;">Sites (Pollution Flux)</p>
    <p style="margin:2px 0; font-size:11px;"><span style="background:#B3D9FF; padding:2px 8px;">  </span> <1 kg/yr</p>
    <p style="margin:2px 0; font-size:11px;"><span style="background:#4DA6FF; padding:2px 8px;">  </span> 1-10 kg/yr</p>
    <p style="margin:2px 0; font-size:11px;"><span style="background:#0066CC; padding:2px 8px;">  </span> 10-100 kg/yr</p>
    <p style="margin:2px 0; font-size:11px;"><span style="background:#003366; padding:2px 8px;">  </span> >100 kg/yr</p>
    <hr style="margin: 5px 0;">
    {river_legend}
    <hr style="margin: 5px 0;">
    <p style="margin:0; font-weight:bold;">Lines (Pathway Flux)</p>
    <p style="margin:2px 0; font-size:11px;">Width & color by flux magnitude</p>
    <p style="margin:2px 0; font-size:10px;"><i>Black outline for visibility</i></p>
    </div>
    '''
    m.get_root().html.add_child(folium.Element(legend_html))
