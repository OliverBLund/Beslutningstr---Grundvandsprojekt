"""
Propose fallback infiltration values for sites in nodata zones.

Strategy:
1. Try alternative layers if site has multiple modellag assignments
2. Calculate layer-specific median infiltration from valid pixels
3. Calculate GVFK-level median infiltration (from sites in same aquifer)
4. Use conservative Denmark-wide default as last resort

Output:
  - CSV with proposed fallback values: nodata_fallback_proposals.csv
  - Summary report of fallback quality and confidence levels
"""

from pathlib import Path
from typing import Dict, List, Optional
import sys

import geopandas as gpd
import numpy as np
import pandas as pd
import rasterio
from shapely.geometry import Point

# Ensure repo root on path
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from config import GVD_RASTER_DIR, get_output_path, WORKFLOW_SETTINGS


def parse_dk_modellag(dk_modellag: str) -> List[str]:
    """Parse DK-modellag string to list of layer codes."""
    if pd.isna(dk_modellag) or not dk_modellag:
        return []

    layers = []
    parts = [p.strip() for p in str(dk_modellag).split("/")]

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


def sample_centroid(raster_path: Path, centroid: Point) -> Optional[float]:
    """Sample raster at centroid point, applying GVD cleaning rules."""
    if not raster_path.exists():
        return None

    try:
        with rasterio.open(raster_path) as src:
            nodata = src.nodata
            coords = [(centroid.x, centroid.y)]
            sampled = list(src.sample(coords))

            if sampled and sampled[0][0] != nodata:
                value = float(sampled[0][0])

                # Apply GVD cleaning: zero negative, cap positive
                gvd_cap = WORKFLOW_SETTINGS.get("gvd_max_infiltration_cap", 750)
                if value < 0:
                    return 0.0
                elif value > gvd_cap:
                    return gvd_cap
                else:
                    return value

            return None

    except Exception:
        return None


def calculate_layer_median(layer: str, model_region: str) -> Optional[float]:
    """Calculate median infiltration from all valid pixels in a layer raster."""
    filename = build_raster_filename(layer, model_region)
    if not filename:
        return None

    raster_path = Path(GVD_RASTER_DIR) / filename
    if not raster_path.exists():
        return None

    try:
        with rasterio.open(raster_path) as src:
            data = src.read(1)
            nodata = src.nodata

            # Get valid data
            valid_data = data[(data != nodata) & (~np.isnan(data))]

            if valid_data.size == 0:
                return None

            # Apply GVD cleaning
            gvd_cap = WORKFLOW_SETTINGS.get("gvd_max_infiltration_cap", 750)
            cleaned_data = np.where(valid_data < 0, 0, valid_data)
            cleaned_data = np.where(cleaned_data > gvd_cap, gvd_cap, cleaned_data)

            return float(np.median(cleaned_data))

    except Exception as e:
        print(f"WARNING: Could not calculate median for {filename}: {e}")
        return None


def calculate_gvfk_median(gvfk: str, step5_results: pd.DataFrame) -> Optional[float]:
    """Calculate median infiltration from other sites in the same GVFK."""
    gvfk_sites = step5_results[step5_results["GVFK"] == gvfk]

    if gvfk_sites.empty:
        return None

    # This would require re-running step6 preparation to get infiltration values
    # For now, return None (not implemented)
    return None


def propose_fallback(
    lokalitet_id: str,
    gvfk: str,
    dk_modellag: str,
    model_region: str,
    centroid: Point,
) -> Dict:
    """
    Propose fallback infiltration value for a site in nodata zone.

    Fallback hierarchy:
    1. Try alternative layers (if site has multiple)
    2. Layer-specific median (from valid pixels in that layer)
    3. Conservative default (100 mm/year for limestone/chalk layers)
    """
    layers = parse_dk_modellag(dk_modellag)

    result = {
        "Lokalitet_ID": lokalitet_id,
        "GVFK": gvfk,
        "DK_modellag": dk_modellag,
        "Model_Region": model_region,
        "Layers": ", ".join(layers),
    }

    # Strategy 1: Try alternative layers
    for layer in layers:
        filename = build_raster_filename(layer, model_region)
        if not filename:
            continue

        raster_path = Path(GVD_RASTER_DIR) / filename
        value = sample_centroid(raster_path, centroid)

        if value is not None:
            result["Fallback_Value_mm_yr"] = value
            result["Fallback_Method"] = f"Alternative layer: {layer}"
            result["Confidence"] = "High"
            return result

    # Strategy 2: Layer-specific median
    layer_medians = {}
    for layer in layers:
        median = calculate_layer_median(layer, model_region)
        if median is not None:
            layer_medians[layer] = median

    if layer_medians:
        # Use median of all layer medians
        fallback_value = np.median(list(layer_medians.values()))
        result["Fallback_Value_mm_yr"] = fallback_value
        result["Fallback_Method"] = f"Layer median (n={len(layer_medians)} layers)"
        result["Confidence"] = "Medium"
        result["Layer_Medians"] = ", ".join([f"{k}:{v:.1f}" for k, v in layer_medians.items()])
        return result

    # Strategy 3: Conservative default based on geology
    # Limestone/chalk (kvs, kalk) typically have moderate infiltration
    # Use conservative estimate of 100 mm/year
    if any(layer.startswith("kvs") or layer.startswith("kalk") for layer in layers):
        result["Fallback_Value_mm_yr"] = 100.0
        result["Fallback_Method"] = "Conservative default (limestone/chalk)"
        result["Confidence"] = "Low"
    else:
        # Generic conservative default
        result["Fallback_Value_mm_yr"] = 150.0
        result["Fallback_Method"] = "Conservative default (generic)"
        result["Confidence"] = "Low"

    return result


def main() -> None:
    # Load filtering audit
    audit_path = get_output_path("step6_filtering_audit")
    audit = pd.read_csv(audit_path, encoding="utf-8")

    # Filter to missing infiltration sites
    missing = audit[audit["Filter_Stage"] == "Filter_3_Missing_Infiltration"].copy()

    if missing.empty:
        print("No missing-infiltration sites found in audit.")
        return

    print(f"\nProposing fallback infiltration values for {missing['Lokalitet_ID'].nunique()} sites")

    # Extract layer info from Additional_Info column
    missing["DK_modellag_extracted"] = missing["Additional_Info"].apply(
        lambda x: x.split("layers: ")[-1] if pd.notna(x) and "layers:" in x else ""
    )

    # Load site geometries
    sites_path = get_output_path("step3_v1v2_sites")
    sites = gpd.read_file(sites_path)
    sites = sites.to_crs(epsg=25832)
    sites["Centroid"] = sites.geometry.centroid

    # Merge with geometries
    missing_with_geom = missing.merge(
        sites[["Lokalitet_", "Centroid"]],
        left_on="Lokalitet_ID",
        right_on="Lokalitet_",
        how="left",
    )

    # Drop duplicates
    missing_unique = missing_with_geom.drop_duplicates(subset=["Lokalitet_ID"])

    # Propose fallbacks
    proposals = []
    for idx, row in missing_unique.iterrows():
        proposal = propose_fallback(
            lokalitet_id=row["Lokalitet_ID"],
            gvfk=row["GVFK"],
            dk_modellag=row["DK_modellag_extracted"],
            model_region=row.get("Model_Region", "dk16"),
            centroid=row["Centroid"],
        )
        proposals.append(proposal)

        if (idx + 1) % 20 == 0:
            print(f"  Processed {idx + 1}/{len(missing_unique)} sites...")

    # Convert to DataFrame
    proposals_df = pd.DataFrame(proposals)

    # Save proposals
    output_csv = get_output_path("step6_site_mkk_exceedances").with_name(
        "nodata_fallback_proposals.csv"
    )
    proposals_df.to_csv(output_csv, index=False, encoding="utf-8")
    print(f"\nProposals saved: {output_csv}")

    # Print summary
    print("\n" + "=" * 80)
    print("FALLBACK PROPOSAL SUMMARY")
    print("=" * 80)
    print(f"Total sites: {len(proposals_df)}")
    print()

    print("By confidence level:")
    for confidence in ["High", "Medium", "Low"]:
        count = (proposals_df["Confidence"] == confidence).sum()
        if count > 0:
            print(f"  {confidence}: {count} sites ({count/len(proposals_df)*100:.1f}%)")

    print()
    print("By fallback method:")
    method_counts = proposals_df["Fallback_Method"].value_counts()
    for method, count in method_counts.items():
        print(f"  {method}: {count} sites")

    print()
    print("Fallback value statistics:")
    print(f"  Min: {proposals_df['Fallback_Value_mm_yr'].min():.1f} mm/year")
    print(f"  Median: {proposals_df['Fallback_Value_mm_yr'].median():.1f} mm/year")
    print(f"  Mean: {proposals_df['Fallback_Value_mm_yr'].mean():.1f} mm/year")
    print(f"  Max: {proposals_df['Fallback_Value_mm_yr'].max():.1f} mm/year")

    print()
    print("Top 5 GVFKs affected:")
    gvfk_counts = proposals_df["GVFK"].value_counts().head(5)
    for gvfk, count in gvfk_counts.items():
        median_fallback = proposals_df[proposals_df["GVFK"] == gvfk]["Fallback_Value_mm_yr"].median()
        print(f"  {gvfk}: {count} sites (median fallback: {median_fallback:.1f} mm/year)")

    print("=" * 80 + "\n")


if __name__ == "__main__":
    main()
