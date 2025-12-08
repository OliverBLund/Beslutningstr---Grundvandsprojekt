"""
Step 5c: Infiltration-Based Site Filtering
===========================================

Filters sites based on groundwater flow direction using pixel-level majority voting.

This step analyzes infiltration rasters to determine if a site has predominantly
upward (negative) or downward (positive) groundwater flow. Sites with upward flow
(opstrømningszoner) are removed from the risk assessment.

Method:
1. Sample infiltration rasters for each site using GVD layers
2. For each pixel: Convert infiltration to binary (< 0 → 0, > 0 → 1)
3. Use majority rule across all pixels to determine flow direction
4. Remove sites with upward gradient (majority = 0)
5. Update step5 output files with filtered results

Input:
- Step 5 compound-specific results (step5_compound_detailed_combinations.csv)
- Site geometries from Step 3
- GVFK layer mapping
- GVD infiltration rasters

Output:
- Filtered step5_compound_detailed_combinations.csv (overwrites original)
- Filtering report showing removed sites and statistics
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Dict, List, Tuple

import geopandas as gpd
import numpy as np
import pandas as pd
import rasterio
from rasterio.mask import mask
from shapely.geometry import mapping

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from config import GVD_RASTER_DIR, get_output_path
from data_loaders import load_gvfk_layer_mapping


def filter_sites_by_infiltration_direction(
    step5_results: pd.DataFrame,
    site_geometries: gpd.GeoDataFrame,
    layer_mapping: pd.DataFrame,
    verbose: bool = True,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Filter sites based on groundwater flow direction using majority voting.

    Args:
        step5_results: DataFrame from step5_risk_assessment (compound detailed combinations)
        site_geometries: GeoDataFrame with site polygons
        layer_mapping: DataFrame mapping GVFK to DK-modellag
        verbose: Whether to print detailed progress information

    Returns:
        Tuple of (filtered_results, removed_sites_df)
        - filtered_results: Sites with downward flow (kept for analysis)
        - removed_sites_df: Sites with upward flow (removed)
    """
    if verbose:
        print("\n" + "=" * 80)
        print("STEP 5c: INFILTRATION-BASED SITE FILTERING")
        print("=" * 80)
        print("Analyzing groundwater flow direction using pixel-level majority voting")
        print("=" * 80 + "\n")

    # Get initial statistics
    initial_combinations = len(step5_results)
    initial_sites = step5_results["Lokalitet_ID"].nunique()
    initial_gvfks = step5_results["GVFK"].nunique()

    if verbose:
        print(f"INPUT from Step 5b:")
        print(f"  {initial_combinations:,} site-GVFK-substance combinations")
        print(f"  {initial_sites:,} unique sites")
        print(f"  {initial_gvfks:,} unique GVFKs\n")

    # Merge layer mapping info
    layer_columns = ["GVForekom", "dkmlag", "dknr"]
    enriched = step5_results.merge(
        layer_mapping[layer_columns],
        left_on="GVFK",
        right_on="GVForekom",
        how="left",
    )
    enriched = enriched.rename(columns={"dkmlag": "DK-modellag", "dknr": "Model_Region"})
    enriched["Model_Region"] = enriched["Model_Region"].fillna("dk16")

    # Filter out rows with missing modellag (like Step 6 does)
    # This prevents trying to sample infiltration for GVFKs without layer mapping
    missing_modellag_count = enriched["DK-modellag"].isna().sum()
    if missing_modellag_count > 0 and verbose:
        missing_gvfks = enriched.loc[enriched["DK-modellag"].isna(), "GVFK"].unique()
        print(f"Note: Skipping {missing_modellag_count} rows with missing DK-modellag for GVFK(s): {', '.join(sorted(missing_gvfks))}")
        print(f"      These rows will be analyzed at site-level using other GVFKs with layer mapping\n")

    enriched = enriched[enriched["DK-modellag"].notna()].copy()

    # Create lookups from geometries
    geometry_lookup = dict(zip(site_geometries["Lokalitet_"], site_geometries["geometry"]))

    # Analyze infiltration direction for each site-GVFK pair
    if verbose:
        print("Analyzing infiltration direction for each site-GVFK combination...")

    site_gvfk_flow_directions = _analyze_site_gvfk_flow_directions(
        enriched, geometry_lookup, verbose=verbose
    )

    # Create filter masks based on site-GVFK pairs
    def get_flow_direction(row):
        key = (row["Lokalitet_ID"], row["GVFK"])
        return site_gvfk_flow_directions.get(key, "no_data")

    # Apply flow direction to original step5_results
    step5_with_direction = step5_results.copy()
    step5_with_direction["Flow_Direction"] = step5_with_direction.apply(get_flow_direction, axis=1)

    # Separate by flow direction
    filtered_results = step5_with_direction[
        (step5_with_direction["Flow_Direction"] == "downward") |
        (step5_with_direction["Flow_Direction"] == "no_data")
    ].drop(columns=["Flow_Direction"]).copy()

    removed_results = step5_with_direction[
        step5_with_direction["Flow_Direction"] == "upward"
    ].drop(columns=["Flow_Direction"]).copy()

    no_data_results = step5_with_direction[
        step5_with_direction["Flow_Direction"] == "no_data"
    ].drop(columns=["Flow_Direction"]).copy()

    # Calculate final statistics (based on analyzed combinations only)
    analyzed_combinations = initial_combinations - missing_modellag_count if missing_modellag_count > 0 else initial_combinations

    final_combinations = len(filtered_results)
    final_sites = filtered_results["Lokalitet_ID"].nunique() if not filtered_results.empty else 0
    final_gvfks = filtered_results["GVFK"].nunique() if not filtered_results.empty else 0

    removed_combinations = len(removed_results)
    removed_sites_count = removed_results["Lokalitet_ID"].nunique() if not removed_results.empty else 0
    removed_gvfks = removed_results["GVFK"].nunique() if not removed_results.empty else 0

    no_data_combinations = len(no_data_results)
    no_data_sites_count = no_data_results["Lokalitet_ID"].nunique() if not no_data_results.empty else 0

    # Count how many kept vs removed
    kept_analyzed = len([d for d in site_gvfk_flow_directions.values() if d in ["downward", "no_data"]])
    removed_analyzed = len([d for d in site_gvfk_flow_directions.values() if d == "upward"])

    # Print summary
    if verbose:
        def pct(part: int | float, total: int | float) -> float:
            return (part / total * 100) if total else 0.0

        print("\n" + "=" * 80)
        print("INFILTRATION FILTERING SUMMARY")
        print("=" * 80)
        print(f"\nDownward flow (KEPT):")
        print(f"  {final_combinations:,} combinations ({pct(final_combinations, initial_combinations):.1f}%)")
        print(f"  {final_sites:,} sites ({pct(final_sites, initial_sites):.1f}%)")
        print(f"  {final_gvfks:,} GVFKs")

        print(f"\nUpward flow - REMOVED (opstrømningszoner):")
        print(f"  {removed_combinations:,} combinations ({pct(removed_combinations, initial_combinations):.1f}%)")
        print(f"  {removed_sites_count:,} sites ({pct(removed_sites_count, initial_sites):.1f}%)")
        print(f"  {removed_gvfks:,} GVFKs affected")

        if no_data_sites_count > 0:
            print(f"\nNo infiltration data available (KEPT by default):")
            print(f"  {no_data_combinations:,} combinations")
            print(f"  {no_data_sites_count:,} sites")
            print(f"  (Sites outside raster coverage - proceeding with caution)")

        print("\n" + "=" * 80 + "\n")

    # filtered_results already includes no_data rows, so no need to concatenate
    return filtered_results, removed_results


def _analyze_site_gvfk_flow_directions(
    enriched: pd.DataFrame,
    geometry_lookup: Dict,
    verbose: bool = True,
) -> Dict[tuple, str]:
    """
    Analyze flow direction for each site-GVFK pair using majority voting on pixels.

    Args:
        enriched: DataFrame with site-GVFK combinations and DK-modellag
        geometry_lookup: Dict mapping Lokalitet_ID to geometry
        verbose: Whether to print progress

    Returns:
        Dict mapping (Lokalitet_ID, GVFK) tuple to flow direction ("upward", "downward", or "no_data")
    """
    # Get unique site-GVFK pairs
    site_gvfk_pairs = enriched[
        ["Lokalitet_ID", "GVFK", "DK-modellag", "Model_Region"]
    ].drop_duplicates()

    site_gvfk_flow_directions = {}
    total_pairs = len(site_gvfk_pairs)

    if verbose:
        print(f"Analyzing {total_pairs:,} unique site-GVFK pairs...\n")

    processed = 0
    for _, row in site_gvfk_pairs.iterrows():
        processed += 1
        lokalitet_id = row["Lokalitet_ID"]
        gvfk = row["GVFK"]
        dk_modellag = row["DK-modellag"]
        model_region = row["Model_Region"]

        key = (lokalitet_id, gvfk)
        geometry = geometry_lookup.get(lokalitet_id)

        if geometry is None:
            site_gvfk_flow_directions[key] = "no_data"
            continue

        # Collect pixel values for this specific GVFK's layers
        all_pixel_values = []
        layers = _parse_dk_modellag(dk_modellag)

        # Get centroid for fallback sampling
        centroid = geometry.centroid if geometry is not None else None

        for layer in layers:
            pixel_values = _sample_infiltration_pixels(layer, model_region, geometry, centroid)
            if pixel_values is not None and len(pixel_values) > 0:
                all_pixel_values.extend(pixel_values)

        # Determine flow direction using majority voting
        if len(all_pixel_values) == 0:
            flow_direction = "no_data"
        else:
            # Convert to binary: < 0 → 0 (upward), ≥ 0 → 1 (downward)
            binary_values = [1 if v >= 0 else 0 for v in all_pixel_values]
            majority_vote = sum(binary_values) / len(binary_values)

            # Majority rule: > 0.5 means more downward pixels
            if majority_vote > 0.5:
                flow_direction = "downward"
            else:
                flow_direction = "upward"

        site_gvfk_flow_directions[key] = flow_direction

        # Progress indicator
        if verbose and processed % 100 == 0:
            print(f"  Processed {processed}/{total_pairs} site-GVFK pairs...")

    if verbose:
        print(f"  Completed analysis for {total_pairs} site-GVFK pairs\n")

        # Print distribution
        upward_count = sum(1 for d in site_gvfk_flow_directions.values() if d == "upward")
        downward_count = sum(1 for d in site_gvfk_flow_directions.values() if d == "downward")
        no_data_count = sum(1 for d in site_gvfk_flow_directions.values() if d == "no_data")

        if total_pairs > 0:
            print("Flow direction distribution:")
            print(f"  Downward (positive infiltration): {downward_count:,} site-GVFK pairs ({downward_count/total_pairs*100:.1f}%)")
            print(f"  Upward (negative infiltration):   {upward_count:,} site-GVFK pairs ({upward_count/total_pairs*100:.1f}%)")
            print(f"  No data:                          {no_data_count:,} site-GVFK pairs ({no_data_count/total_pairs*100:.1f}%)\n")
        else:
            print("Flow direction distribution: No analyzed site-GVFK pairs\n")

    return site_gvfk_flow_directions


def _parse_dk_modellag(dk_modellag: str) -> List[str]:
    """Parse DK-modellag string to list of layer codes."""
    if pd.isna(dk_modellag) or not dk_modellag:
        return []

    layers = []
    parts = [p.strip() for p in str(dk_modellag).split(";")]

    for part in parts:
        if ":" in part:
            layer_code = part.split(":")[1].strip().lower()
        else:
            layer_code = part.strip().lower()

        if layer_code and layer_code not in layers:
            layers.append(layer_code)

    return layers


def _sample_infiltration_pixels(
    layer: str,
    model_region: str,
    geometry,
    centroid,
    source_crs: str = "EPSG:25832",
) -> List[float] | None:
    """
    Sample all pixel values from infiltration raster for given geometry.
    Uses polygon sampling with centroid fallback (same strategy as Step 6).

    Args:
        layer: GVD layer code (e.g., "ks", "kalk")
        model_region: Regional code (dk16 mainland, dk7 Bornholm, etc.)
        geometry: Site polygon geometry
        centroid: Site centroid (for fallback if polygon fails)
        source_crs: CRS of the geometry

    Returns:
        List of pixel values, or None if no data available
    """
    normalized_layer = str(layer).lower()
    raster_filename = _build_raster_filename(normalized_layer, model_region)
    if raster_filename is None:
        return None

    raster_file = GVD_RASTER_DIR / raster_filename

    # Fallback to mainland raster if regional file missing (dk16 covers most of Denmark)
    if not raster_file.exists() and not raster_filename.startswith("dk16_"):
        fallback = GVD_RASTER_DIR / f"dk16_gvd_{normalized_layer}.tif"
        if fallback.exists():
            raster_file = fallback

    if not raster_file.exists():
        return None

    try:
        with rasterio.open(raster_file) as src:
            nodata = src.nodata

            # Try polygon sampling first
            polygon_values = None
            if geometry is not None:
                try:
                    geom_geojson = [mapping(geometry)]
                    masked_data, _ = mask(src, geom_geojson, crop=True, all_touched=False)
                    valid_data = masked_data[
                        (masked_data != nodata) & (~np.isnan(masked_data))
                    ]

                    if valid_data.size > 0:
                        polygon_values = valid_data.flatten().tolist()
                except Exception:
                    pass

            # If polygon sampling succeeded, return those values
            if polygon_values is not None:
                return polygon_values

            # Fallback: Try centroid sampling
            if centroid is not None:
                try:
                    coords = [(centroid.x, centroid.y)]
                    sampled = list(src.sample(coords))
                    if sampled and sampled[0][0] != nodata:
                        centroid_value = float(sampled[0][0])
                        return [centroid_value]  # Return as list for consistency
                except Exception:
                    pass

            return None

    except Exception:
        return None


def _build_raster_filename(layer: str, model_region: str | None) -> str | None:
    """Construct raster filename using dk16/dk7 prefixes."""
    if not layer:
        return None

    normalized_layer = str(layer).lower()
    region = (model_region or "").lower()
    if region.startswith("dk7"):
        prefix = "dk7"
    else:
        prefix = "dk16"

    return f"{prefix}_gvd_{normalized_layer}.tif"


def run_step5c_filtering(verbose: bool = True) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Run Step 5c infiltration filtering on Step 5 results.

    Returns:
        Tuple of (filtered_results, removed_sites)
    """
    # Load required data
    if verbose:
        print("\nLoading data for infiltration filtering...")

    # Load Step 5 results
    step5_path = get_output_path("step5_compound_detailed_combinations")
    step5_results = pd.read_csv(step5_path, encoding='utf-8')

    # Load site geometries
    from data_loaders import load_site_geometries
    site_geometries = load_site_geometries()

    # Load layer mapping from Grunddata geodatabase
    layer_mapping = load_gvfk_layer_mapping(columns=["GVForekom", "dkmlag", "dknr"])

    # Run filtering
    filtered_results, removed_sites = filter_sites_by_infiltration_direction(
        step5_results, site_geometries, layer_mapping, verbose=verbose
    )

    # Save filtered results (overwrite original)
    if verbose:
        print("Saving filtered results...")

    filtered_results.to_csv(step5_path, index=False, encoding="utf-8")

    # Note: Removed sites are not saved to file (considered dead-end data)
    # They are returned for in-memory analysis if needed

    if verbose:
        print(f"  - Saved: {step5_path.name}")

    # Create visualization of removed sites (upward flux zones)
    if not removed_sites.empty:
        _create_upward_flux_map(removed_sites, site_geometries, verbose=verbose)

    return filtered_results, removed_sites


if __name__ == "__main__":
    # Run standalone filtering
    filtered, removed = run_step5c_filtering(verbose=True)
    print("\n- Step 5c infiltration filtering completed")
    print(f"  Final results: {len(filtered):,} combinations, {filtered['Lokalitet_ID'].nunique():,} sites")
    print(f"  Removed: {removed['Lokalitet_ID'].nunique():,} sites with upward flow")


def _create_upward_flux_map(
    removed_df: pd.DataFrame,
    site_geometries: gpd.GeoDataFrame,
    verbose: bool = True,
) -> None:
    """
    Create interactive map showing sites excluded for upward groundwater flux.

    This visualization shows sites BEFORE they are filtered out, helping validate
    the infiltration-based filtering logic.
    """
    if verbose:
        print("\nCreating upward flux zone visualization...")

    if removed_df.empty:
        if verbose:
            print("  No sites with upward flux - skipping map.")
        return

    if site_geometries is None or site_geometries.empty:
        if verbose:
            print("  Site geometries unavailable - cannot create map.")
        return

    try:
        import folium
        import numpy as np
    except ImportError:
        if verbose:
            print("  Folium not available - skipping map.")
        return

    # Prepare geometries
    geometry_df = site_geometries.rename(columns={"Lokalitet_": "Lokalitet_ID"})[
        ["Lokalitet_ID", "geometry"]
    ]
    joined = removed_df.merge(geometry_df, on="Lokalitet_ID", how="left")
    joined = joined.dropna(subset=["geometry"])

    if joined.empty:
        if verbose:
            print("  Removed sites missing geometries - skipping map.")
        return

    removed_gdf = gpd.GeoDataFrame(joined, geometry="geometry", crs=site_geometries.crs)
    if removed_gdf.crs is None:
        if verbose:
            print("  CRS undefined - cannot create map.")
        return

    removed_gdf = removed_gdf.to_crs(epsg=4326)

    # Calculate map center
    bounds = removed_gdf.total_bounds
    if np.any(~np.isfinite(bounds)):
        if verbose:
            print("  Invalid geometry bounds - skipping map.")
        return

    center_lat = (bounds[1] + bounds[3]) / 2
    center_lon = (bounds[0] + bounds[2]) / 2

    # Create map
    fmap = folium.Map(
        location=[center_lat, center_lon],
        zoom_start=7,
        tiles="CartoDB positron",
        control_scale=True,
    )

    # Group sites by unique lokalitet for cleaner visualization
    unique_sites = removed_gdf.drop_duplicates(subset=["Lokalitet_ID"])

    # Add excluded sites to map
    for _, row in unique_sites.iterrows():
        popup_html = f"""
        <div style="font-family: Arial; width: 200px;">
            <b>Site Excluded (Upward Flux)</b><br>
            <hr style="margin: 5px 0;">
            Site ID: {row['Lokalitet_ID']}<br>
            GVFK: {row.get('GVFK', 'N/A')}<br>
            <br>
            <i>This site was filtered in Step 5c<br>
            due to majority upward groundwater flow</i>
        </div>
        """

        folium.CircleMarker(
            location=[row.geometry.centroid.y, row.geometry.centroid.x],
            radius=6,
            popup=folium.Popup(popup_html, max_width=250),
            color='#d32f2f',
            fillColor='#ef5350',
            fillOpacity=0.7,
            weight=2,
        ).add_to(fmap)

    # Add title
    title_html = '''
    <div style="position: fixed;
                top: 10px; left: 50px; width: 400px; height: 90px;
                background-color: white; border:2px solid grey; z-index:9999;
                font-size:14px; padding: 10px;">
    <h4 style="margin:0;">Step 5c: Upward Flux Zones</h4>
    <p style="margin:5px 0; font-size:12px;">
    Sites excluded due to upward groundwater flow (opstrømningszoner)<br>
    Red markers = Sites NOT included in further analysis
    </p>
    </div>
    '''
    fmap.get_root().html.add_child(folium.Element(title_html))

    # Save map
    from config import get_visualization_path
    output_dir = get_visualization_path("step5c")
    output_file = output_dir / "upward_flux_excluded_sites.html"
    fmap.save(str(output_file))

    if verbose:
        print(f"  ✓ Map created: {output_file.name}")
        print(f"    Showing {len(unique_sites)} excluded sites")
