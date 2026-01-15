"""
Experiment: 3x3 Neighborhood Sampling for Small Sites
======================================================
Tests whether using neighborhood sampling (9 pixels) instead of single-pixel
centroid fallback would change infiltration filter classifications.
"""

import sys
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Tuple
import numpy as np
import pandas as pd
import rasterio
from shapely.geometry import mapping

# Add parent directory (Kode) to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config import GVD_RASTER_DIR

# Pixel size in the DK-modellag rasters (500m x 500m)
PIXEL_SIZE = 100.0


def _build_raster_filename(layer: str, model_region: str | None) -> str | None:
    """Build raster filename with dk16/dk7 prefix."""
    if not layer:
        return None
    region = (model_region or "").lower()
    prefix = "dk7" if region.startswith("dk7") else "dk16"
    return f"{prefix}_gvd_{layer}.tif"


def _sample_neighborhood(
    raster_file: Path,
    centroid_x: float,
    centroid_y: float,
    neighborhood_size: int = 3,  # 3x3 = 9 pixels
) -> List[float]:
    """
    Sample a neighborhood of pixels around the centroid.

    Args:
        raster_file: Path to raster file
        centroid_x, centroid_y: Centroid coordinates
        neighborhood_size: Size of neighborhood (3 = 3x3, 5 = 5x5, etc.)

    Returns:
        List of valid pixel values in the neighborhood
    """
    with rasterio.open(raster_file) as src:
        nodata = src.nodata

        # Get pixel resolution
        pixel_width = abs(src.transform[0])
        pixel_height = abs(src.transform[4])

        # Generate sample points in a grid around centroid
        half_size = neighborhood_size // 2
        sample_points = []

        for dx in range(-half_size, half_size + 1):
            for dy in range(-half_size, half_size + 1):
                x = centroid_x + dx * pixel_width
                y = centroid_y + dy * pixel_height
                sample_points.append((x, y))

        # Sample all points
        pixel_values = []
        for sampled in src.sample(sample_points):
            val = sampled[0]
            if val != nodata and not np.isnan(val):
                pixel_values.append(float(val))

        return pixel_values


def run_neighborhood_experiment(sample_fraction: float = 1.0):
    """
    Compare single-pixel vs neighborhood sampling for small sites.

    Args:
        sample_fraction: Fraction of data to analyze (0.0-1.0). Use 0.1 for 10% sampling.
    """
    import geopandas as gpd

    print("="*80)
    print("EXPERIMENT: 3x3 Neighborhood Sampling for Small Sites")
    print("="*80)

    if sample_fraction < 1.0:
        print(f"NOTE: Running with {sample_fraction*100:.0f}% sample for faster testing")

    # Load from saved outputs (FAST) instead of running workflow (SLOW)
    from config import get_output_path

    print("\nLoading site data from saved outputs...")
    v1v2_path = get_output_path("step3_v1v2_sites")
    v1v2_sites = gpd.read_file(v1v2_path)
    print(f"  Loaded {len(v1v2_sites):,} site-GVFK combinations")

    # Build geometry lookup (uses Lokalitet_ column from step3)
    site_id_col = "Lokalitet_"
    gvfk_col = "Navn"

    geometry_lookup = {}
    for _, row in v1v2_sites.iterrows():
        lokalitet_id = row[site_id_col]
        if lokalitet_id not in geometry_lookup and row.geometry is not None:
            geometry_lookup[lokalitet_id] = row.geometry

    # Load layer mapping for GVFK -> DK-modellag
    from data_loaders import load_gvfk_layer_mapping
    layer_mapping = load_gvfk_layer_mapping(columns=["GVForekom", "dkmlag", "dknr"])

    # Create analysis DataFrame with normalized column names
    analysis_df = pd.DataFrame({
        "Lokalitet_ID": v1v2_sites[site_id_col].values,
        "GVFK": v1v2_sites[gvfk_col].values,
    })

    # Merge layer mapping info
    enriched = analysis_df.merge(
        layer_mapping[["GVForekom", "dkmlag", "dknr"]],
        left_on="GVFK",
        right_on="GVForekom",
        how="left",
    ).rename(columns={"dkmlag": "DK-modellag", "dknr": "Model_Region"})
    enriched["Model_Region"] = enriched["Model_Region"].fillna("dk16")

    # Filter to rows with valid modellag
    site_gvfk_pairs = enriched[enriched["DK-modellag"].notna()][
        ["Lokalitet_ID", "GVFK", "DK-modellag", "Model_Region"]
    ].drop_duplicates()

    # Apply downsampling if requested
    if sample_fraction < 1.0:
        n_sample = max(1, int(len(site_gvfk_pairs) * sample_fraction))
        site_gvfk_pairs = site_gvfk_pairs.sample(n=n_sample, random_state=42)
        print(f"Downsampled to {len(site_gvfk_pairs):,} pairs ({sample_fraction*100:.0f}%)")

    print(f"Analyzing {len(site_gvfk_pairs):,} site-GVFK pairs...")

    # Parse DK-modellag
    def parse_layers(dk_modellag):
        if not dk_modellag or str(dk_modellag) == "nan":
            return []
        return [l.strip().lower() for l in str(dk_modellag).split(",")]

    # Collect comparison data
    single_pixel_results = []  # Sites classified with just 1 pixel

    processed = 0
    for _, row in site_gvfk_pairs.iterrows():
        processed += 1
        if processed % 5000 == 0:
            print(f"  Processed {processed:,}/{len(site_gvfk_pairs):,}...")

        lokalitet_id = row["Lokalitet_ID"]
        gvfk = row["GVFK"]
        dk_modellag = row["DK-modellag"]
        model_region = row["Model_Region"]

        geometry = geometry_lookup.get(lokalitet_id)
        if geometry is None:
            continue

        centroid = geometry.centroid
        layers = parse_layers(dk_modellag)

        # Sample each layer
        for layer in layers:
            raster_filename = _build_raster_filename(layer, model_region)
            if not raster_filename:
                continue

            raster_file = GVD_RASTER_DIR / raster_filename
            if not raster_file.exists():
                # Try fallback
                fallback = GVD_RASTER_DIR / f"dk16_gvd_{layer}.tif"
                if fallback.exists():
                    raster_file = fallback
                else:
                    continue

            # Current approach: sample polygon, count pixels
            try:
                with rasterio.open(raster_file) as src:
                    nodata = src.nodata
                    geom_geojson = [mapping(geometry)]
                    from rasterio.mask import mask
                    masked_data, _ = mask(src, geom_geojson, crop=True, all_touched=False)
                    valid_data = masked_data[
                        (masked_data != nodata) & (~np.isnan(masked_data))
                    ]
                    original_pixel_count = valid_data.size

                    if original_pixel_count == 0:
                        # Centroid fallback - this is where we'd use 1 pixel
                        coords = [(centroid.x, centroid.y)]
                        sampled = list(src.sample(coords))
                        if sampled and sampled[0][0] != nodata:
                            original_pixel_count = 1
                            original_values = [float(sampled[0][0])]
                        else:
                            continue
                    else:
                        original_values = valid_data.flatten().tolist()
            except Exception:
                continue

            # Only analyze sites with few pixels (1-3)
            if original_pixel_count > 3:
                continue

            # Calculate original classification
            original_positive = sum(1 for v in original_values if v >= 0)
            original_vote = original_positive / len(original_values) if original_values else 0
            original_direction = "downward" if original_vote > 0.5 else "upward"

            # Sample 3x3 neighborhood around centroid
            neighborhood_values = _sample_neighborhood(
                raster_file, centroid.x, centroid.y, neighborhood_size=3
            )

            if not neighborhood_values:
                continue

            # Calculate neighborhood classification
            neighborhood_positive = sum(1 for v in neighborhood_values if v >= 0)
            neighborhood_vote = neighborhood_positive / len(neighborhood_values)
            neighborhood_direction = "downward" if neighborhood_vote > 0.5 else "upward"

            single_pixel_results.append({
                "lokalitet_id": lokalitet_id,
                "gvfk": gvfk,
                "layer": layer,
                "original_pixel_count": original_pixel_count,
                "original_vote": original_vote,
                "original_direction": original_direction,
                "neighborhood_pixels": len(neighborhood_values),
                "neighborhood_vote": neighborhood_vote,
                "neighborhood_direction": neighborhood_direction,
                "would_flip": original_direction != neighborhood_direction,
            })

    # Analyze results
    print("\n" + "="*80)
    print("RESULTS")
    print("="*80)

    total = len(single_pixel_results)
    print(f"\nTotal site-GVFK-layer combinations with ≤3 pixels: {total:,}")

    if total == 0:
        print("No small-site data to analyze.")
        return

    # Count by original pixel count
    by_count = defaultdict(list)
    for r in single_pixel_results:
        by_count[r["original_pixel_count"]].append(r)

    for count in sorted(by_count.keys()):
        results = by_count[count]
        flips = sum(1 for r in results if r["would_flip"])
        flips_down_to_up = sum(1 for r in results if r["would_flip"] and r["original_direction"] == "downward")
        flips_up_to_down = sum(1 for r in results if r["would_flip"] and r["original_direction"] == "upward")

        print(f"\n{count}-pixel sites: {len(results):,}")
        print(f"  Would flip classification: {flips:,} ({flips/len(results)*100:.1f}%)")
        print(f"    downward → upward: {flips_down_to_up:,}")
        print(f"    upward → downward: {flips_up_to_down:,}")

    # Overall summary
    total_flips = sum(1 for r in single_pixel_results if r["would_flip"])
    total_down_to_up = sum(1 for r in single_pixel_results if r["would_flip"] and r["original_direction"] == "downward")
    total_up_to_down = sum(1 for r in single_pixel_results if r["would_flip"] and r["original_direction"] == "upward")

    print(f"\n" + "-"*60)
    print(f"OVERALL: {total_flips:,} / {total:,} would flip ({total_flips/total*100:.1f}%)")
    print(f"  downward → upward (would be NEWLY EXCLUDED): {total_down_to_up:,}")
    print(f"  upward → downward (would be NEWLY INCLUDED): {total_up_to_down:,}")

    # Risk assessment impact
    print(f"\n" + "="*80)
    print("RISK ASSESSMENT IMPACT")
    print("="*80)
    if total_down_to_up > total_up_to_down:
        print(f"Net effect: {total_down_to_up - total_up_to_down:,} MORE sites would be excluded")
        print("→ Slightly MORE conservative (fewer sites in risk assessment)")
    else:
        print(f"Net effect: {total_up_to_down - total_down_to_up:,} MORE sites would be included")
        print("→ Slightly LESS conservative (more sites in risk assessment)")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Test neighborhood sampling for small sites")
    parser.add_argument("--sample", type=float, default=1.0,
                        help="Fraction of data to sample (e.g., 0.1 for 10%%)")
    args = parser.parse_args()
    run_neighborhood_experiment(sample_fraction=args.sample)

