"""
Investigate sites removed in Step 6 due to missing infiltration data.

Outputs a CSV via get_output_path("step6_missing_infiltration_diagnosis") with:
  - Lokalitet_ID
  - Whether centroid is inside any GVD raster
  - Whether polygon intersects any GVD raster
  - Nearest raster path
  - Distance from centroid to nearest raster extent (meters; in raster CRS)
"""

from pathlib import Path
from typing import Dict, List

import geopandas as gpd
import pandas as pd
import rasterio
from shapely.geometry import box
import sys

# Ensure repo root on path so `config` resolves when run from anywhere
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from config import GVD_RASTER_DIR, get_output_path

# Column name for site id in step3_v1v2_sites
SITE_ID_COL = "Lokalitet_"


def _load_raster_extents() -> List[Dict]:
    """Load raster extents and CRS for all GVD rasters."""
    records: List[Dict] = []
    for tif in Path(GVD_RASTER_DIR).glob("*.tif"):
        try:
            with rasterio.open(tif) as src:
                records.append(
                    {
                        "path": str(tif),
                        "crs": src.crs,
                        "bounds": box(*src.bounds),
                    }
                )
        except Exception as exc:
            print(f"WARNING: failed reading {tif}: {exc}")
    return records


def main() -> None:
    # step6_filtering_audit is the available key (detailed version)
    audit_path = get_output_path("step6_filtering_audit")
    sites_path = get_output_path("step3_v1v2_sites")
    # Fall back to saving in step6_tilstandsvurdering data dir
    output_path = get_output_path("step6_site_mkk_exceedances").with_name(
        "step6_missing_infiltration_diagnosis.csv"
    )

    audit = pd.read_csv(audit_path, encoding="utf-8")
    missing = audit[audit["Filter_Stage"] == "Filter_3_Missing_Infiltration"].copy()
    if missing.empty:
        print("No missing-infiltration rows found.")
        return

    sites = gpd.read_file(sites_path)
    sites = sites[sites[SITE_ID_COL].isin(missing["Lokalitet_ID"])]
    if sites.empty:
        print("No matching site geometries found for missing rows.")
        return

    rasters = _load_raster_extents()
    if not rasters:
        print("No rasters found in GVD_RASTER_DIR.")
        return

    target_crs = rasters[0]["crs"]
    sites = sites.to_crs(target_crs)

    results: List[Dict] = []
    for _, site in sites.iterrows():
        sid = site[SITE_ID_COL]
        poly = site.geometry
        centroid = poly.centroid if poly is not None else None

        any_centroid_inside = False
        any_poly_intersect = False
        min_dist = None
        nearest_raster = None

        for r in rasters:
            bounds = r["bounds"]
            if centroid is not None and bounds.contains(centroid):
                any_centroid_inside = True
            if poly is not None and bounds.intersects(poly):
                any_poly_intersect = True

            if centroid is not None:
                d = centroid.distance(bounds)
                if min_dist is None or d < min_dist:
                    min_dist = d
                    nearest_raster = r["path"]

        results.append(
            {
                "Lokalitet_ID": sid,
                "Centroid_inside_any_raster": any_centroid_inside,
                "Polygon_intersects_any_raster": any_poly_intersect,
                "Nearest_raster": nearest_raster,
                "Distance_to_nearest_raster_m": min_dist,
            }
        )

    df = pd.DataFrame(results)
    df.to_csv(output_path, index=False, encoding="utf-8")
    print(f"Diagnosed {len(df)} sites. Saved: {output_path}")
    print(
        "Counts by centroid-inside:",
        df["Centroid_inside_any_raster"].value_counts(dropna=False).to_dict(),
    )
    print(
        "Counts by poly-intersects:",
        df["Polygon_intersects_any_raster"].value_counts(dropna=False).to_dict(),
    )
    # Deduplicate to site-level and report modellag/region if present in audit
    site_level = missing[["Lokalitet_ID", "GVFK"]].drop_duplicates()
    for col in ["DK-modellag", "Model_Region"]:
        if col in missing.columns:
            site_level[col] = missing.groupby("Lokalitet_ID")[col].first().values
    print(f"\nSite-level (unique Lokalitet_ID) count: {len(site_level)}")
    if "DK-modellag" in site_level.columns:
        print(
            "Top modellag/region combos:",
            site_level[["DK-modellag", "Model_Region"]]
            .value_counts(dropna=False)
            .head(10)
            .to_dict(),
        )
    print("\nTop GVFK among missing-infiltration sites:")
    print(site_level["GVFK"].value_counts().head(20).to_dict())


if __name__ == "__main__":
    main()
