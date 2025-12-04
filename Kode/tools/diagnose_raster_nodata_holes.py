"""
Diagnose nodata holes in infiltration rasters at missing-infiltration site locations.

This script:
1. Loads all sites removed for missing infiltration (Filter_3)
2. For each site, attempts to sample its assigned modellag raster(s)
3. Tests buffer sampling at multiple radii (50m, 100m, 200m, 500m)
4. Reports which sites can be recovered and at what buffer distance
5. Generates a spatial map showing nodata coverage for affected rasters

Output:
  - CSV: Resultater/step6_tilstandsvurdering/data/nodata_buffer_recovery_analysis.csv
  - Map: Resultater/step6_tilstandsvurdering/data/nodata_spatial_coverage_map.html
"""

from pathlib import Path
from typing import Dict, List, Optional, Tuple
import sys

import geopandas as gpd
import numpy as np
import pandas as pd
import rasterio
from rasterio.mask import mask
from shapely.geometry import Point, mapping
import folium
from folium import plugins

# Ensure repo root on path
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from config import GVD_RASTER_DIR, get_output_path


def parse_dk_modellag(dk_modellag: str) -> List[str]:
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


def build_raster_filename(layer: str, model_region: str) -> Optional[str]:
    """Build raster filename for a given layer and region."""
    if not layer:
        return None

    normalized_layer = str(layer).lower()
    region = (model_region or "").lower()

    if region.startswith("dk7"):
        prefix = "dk7"
    else:
        prefix = "dk16"

    return f"{prefix}_gvd_{normalized_layer}.tif"


def sample_with_buffer(
    raster_path: Path,
    centroid: Point,
    buffer_meters: float,
) -> Tuple[Optional[float], int]:
    """
    Sample raster within a buffer around centroid, return mean and pixel count.

    Returns:
        Tuple of (mean_value, pixel_count). Returns (None, 0) if no valid data.
    """
    if not raster_path.exists():
        return None, 0

    try:
        with rasterio.open(raster_path) as src:
            nodata = src.nodata

            # Create buffer polygon
            buffer_geom = centroid.buffer(buffer_meters)
            geom_geojson = [mapping(buffer_geom)]

            # Mask raster to buffer
            masked_data, _ = mask(src, geom_geojson, crop=True, all_touched=False)
            valid_data = masked_data[
                (masked_data != nodata) & (~np.isnan(masked_data))
            ]

            if valid_data.size > 0:
                # Apply same cleaning as in step6: zero negative, cap positive
                from config import WORKFLOW_SETTINGS
                gvd_cap = WORKFLOW_SETTINGS.get("gvd_max_infiltration_cap", 750)

                cleaned_data = np.where(valid_data < 0, 0, valid_data)
                cleaned_data = np.where(cleaned_data > gvd_cap, gvd_cap, cleaned_data)

                return float(np.mean(cleaned_data)), int(cleaned_data.size)

            return None, 0

    except Exception as e:
        print(f"ERROR sampling {raster_path.name} with {buffer_meters}m buffer: {e}")
        return None, 0


def analyze_site(
    lokalitet_id: str,
    gvfk: str,
    dk_modellag: str,
    model_region: str,
    centroid: Point,
    buffer_radii: List[float],
) -> Dict:
    """
    Analyze a single site across multiple buffer radii.

    Returns dict with recovery statistics.
    """
    layers = parse_dk_modellag(dk_modellag)

    result = {
        "Lokalitet_ID": lokalitet_id,
        "GVFK": gvfk,
        "DK_modellag": dk_modellag,
        "Model_Region": model_region,
        "Layers_Attempted": ", ".join(layers),
        "Centroid_X": centroid.x,
        "Centroid_Y": centroid.y,
    }

    # Test centroid (0m buffer)
    for layer in layers:
        filename = build_raster_filename(layer, model_region)
        if not filename:
            continue

        raster_path = Path(GVD_RASTER_DIR) / filename
        if not raster_path.exists():
            continue

        # Sample at centroid
        value, pixel_count = sample_with_buffer(raster_path, centroid, 0)
        result[f"Centroid_{layer}"] = value
        result[f"Centroid_{layer}_pixels"] = pixel_count

        # Test buffer radii
        for radius in buffer_radii:
            value, pixel_count = sample_with_buffer(raster_path, centroid, radius)
            result[f"Buffer_{radius}m_{layer}"] = value
            result[f"Buffer_{radius}m_{layer}_pixels"] = pixel_count

    # Determine recovery status
    # Check if ANY buffer at ANY radius recovered valid data
    recovered_at_radius = {}
    for radius in buffer_radii:
        for layer in layers:
            col = f"Buffer_{radius}m_{layer}"
            if col in result and pd.notna(result[col]):
                recovered_at_radius[radius] = True
                break

    if recovered_at_radius:
        min_radius = min(recovered_at_radius.keys())
        result["Recoverable"] = "Yes"
        result["Min_Recovery_Radius_m"] = min_radius
    else:
        result["Recoverable"] = "No"
        result["Min_Recovery_Radius_m"] = None

    return result


def generate_spatial_map(
    analysis_results: pd.DataFrame,
    sites_gdf: gpd.GeoDataFrame,
    output_path: Path,
) -> None:
    """Generate interactive map showing recoverable vs non-recoverable sites."""
    # Merge with geometries
    merged = analysis_results.merge(
        sites_gdf[["Lokalitet_", "geometry"]],
        left_on="Lokalitet_ID",
        right_on="Lokalitet_",
        how="left",
    )
    merged_gdf = gpd.GeoDataFrame(merged, geometry="geometry", crs=sites_gdf.crs)
    merged_gdf = merged_gdf.to_crs(epsg=4326)

    # Create map centered on sites
    center_lat = merged_gdf.geometry.centroid.y.mean()
    center_lon = merged_gdf.geometry.centroid.x.mean()
    m = folium.Map(location=[center_lat, center_lon], zoom_start=8, tiles="OpenStreetMap")

    # Split by recoverability
    recoverable = merged_gdf[merged_gdf["Recoverable"] == "Yes"]
    non_recoverable = merged_gdf[merged_gdf["Recoverable"] == "No"]

    # Add non-recoverable sites (red)
    if not non_recoverable.empty:
        for _, site in non_recoverable.iterrows():
            folium.CircleMarker(
                location=[site.geometry.centroid.y, site.geometry.centroid.x],
                radius=8,
                popup=f"<b>{site['Lokalitet_ID']}</b><br>GVFK: {site['GVFK']}<br>Layers: {site['Layers_Attempted']}<br><b>NOT RECOVERABLE</b>",
                color="red",
                fill=True,
                fillColor="red",
                fillOpacity=0.7,
            ).add_to(m)

    # Add recoverable sites (color by recovery radius)
    if not recoverable.empty:
        for _, site in recoverable.iterrows():
            radius = site["Min_Recovery_Radius_m"]
            if radius <= 50:
                color = "green"
                label = f"Recoverable at {radius}m (easy)"
            elif radius <= 100:
                color = "yellow"
                label = f"Recoverable at {radius}m (moderate)"
            elif radius <= 200:
                color = "orange"
                label = f"Recoverable at {radius}m (difficult)"
            else:
                color = "purple"
                label = f"Recoverable at {radius}m (very difficult)"

            folium.CircleMarker(
                location=[site.geometry.centroid.y, site.geometry.centroid.x],
                radius=8,
                popup=f"<b>{site['Lokalitet_ID']}</b><br>GVFK: {site['GVFK']}<br>Layers: {site['Layers_Attempted']}<br>{label}",
                color=color,
                fill=True,
                fillColor=color,
                fillOpacity=0.7,
            ).add_to(m)

    # Add legend
    legend_html = """
    <div style="position: fixed;
                bottom: 50px; left: 50px; width: 300px; height: 200px;
                background-color: white; border:2px solid grey; z-index:9999;
                font-size:14px; padding: 10px">
    <p><b>Nodata Recovery Analysis</b></p>
    <p><span style="color:green">●</span> Recoverable ≤50m (easy)</p>
    <p><span style="color:yellow">●</span> Recoverable ≤100m (moderate)</p>
    <p><span style="color:orange">●</span> Recoverable ≤200m (difficult)</p>
    <p><span style="color:purple">●</span> Recoverable >200m (very difficult)</p>
    <p><span style="color:red">●</span> Not recoverable (no valid data within 500m)</p>
    </div>
    """
    m.get_root().html.add_child(folium.Element(legend_html))

    # Save map
    m.save(str(output_path))
    print(f"Spatial map saved: {output_path}")


def main() -> None:
    # Load filtering audit
    audit_path = get_output_path("step6_filtering_audit")
    audit = pd.read_csv(audit_path, encoding="utf-8")

    # Filter to missing infiltration sites
    missing = audit[audit["Filter_Stage"] == "Filter_3_Missing_Infiltration"].copy()

    if missing.empty:
        print("No missing-infiltration sites found in audit.")
        return

    print(f"\nAnalyzing {len(missing)} rows ({missing['Lokalitet_ID'].nunique()} unique sites) with missing infiltration")

    # Load site geometries
    sites_path = get_output_path("step3_v1v2_sites")
    sites = gpd.read_file(sites_path)
    sites = sites.to_crs(epsg=25832)  # Ensure metric CRS

    # Add centroids to sites
    sites["Centroid"] = sites.geometry.centroid

    # Merge missing sites with geometries
    missing_with_geom = missing.merge(
        sites[["Lokalitet_", "Centroid"]],
        left_on="Lokalitet_ID",
        right_on="Lokalitet_",
        how="left",
    )

    # Drop duplicates (one row per site)
    missing_unique = missing_with_geom.drop_duplicates(subset=["Lokalitet_ID"])

    print(f"Unique sites to analyze: {len(missing_unique)}")

    # Define buffer radii to test
    buffer_radii = [50, 100, 200, 500]

    # Analyze each site
    results = []
    for idx, row in missing_unique.iterrows():
        result = analyze_site(
            lokalitet_id=row["Lokalitet_ID"],
            gvfk=row["GVFK"],
            dk_modellag=row.get("Additional_Info", "").split("layers: ")[-1] if "layers:" in row.get("Additional_Info", "") else "",
            model_region=row.get("Model_Region", "dk16"),
            centroid=row["Centroid"],
            buffer_radii=buffer_radii,
        )
        results.append(result)

        if (idx + 1) % 10 == 0:
            print(f"  Processed {idx + 1}/{len(missing_unique)} sites...")

    # Convert to DataFrame
    results_df = pd.DataFrame(results)

    # Save results
    output_csv = get_output_path("step6_site_mkk_exceedances").with_name(
        "nodata_buffer_recovery_analysis.csv"
    )
    results_df.to_csv(output_csv, index=False, encoding="utf-8")
    print(f"\nResults saved: {output_csv}")

    # Print summary
    recoverable_count = (results_df["Recoverable"] == "Yes").sum()
    non_recoverable_count = (results_df["Recoverable"] == "No").sum()

    print("\n" + "=" * 80)
    print("BUFFER RECOVERY ANALYSIS SUMMARY")
    print("=" * 80)
    print(f"Total sites analyzed: {len(results_df)}")
    print(f"Recoverable with buffer sampling: {recoverable_count} ({recoverable_count/len(results_df)*100:.1f}%)")
    print(f"Non-recoverable (no data within 500m): {non_recoverable_count} ({non_recoverable_count/len(results_df)*100:.1f}%)")

    if recoverable_count > 0:
        print("\nRecovery radius breakdown:")
        for radius in buffer_radii:
            count = (results_df["Min_Recovery_Radius_m"] == radius).sum()
            if count > 0:
                print(f"  {radius}m: {count} sites")

    print("=" * 80 + "\n")

    # Generate spatial map
    output_map = get_output_path("step6_site_mkk_exceedances").with_name(
        "nodata_spatial_coverage_map.html"
    )
    generate_spatial_map(results_df, sites, output_map)

    # Print top affected GVFKs
    print("\nTop 10 GVFKs affected by nodata holes:")
    gvfk_counts = results_df["GVFK"].value_counts().head(10)
    for gvfk, count in gvfk_counts.items():
        recoverable = results_df[(results_df["GVFK"] == gvfk) & (results_df["Recoverable"] == "Yes")].shape[0]
        print(f"  {gvfk}: {count} sites ({recoverable} recoverable)")


if __name__ == "__main__":
    main()
