from __future__ import annotations

from pathlib import Path
from typing import Set, Tuple

import geopandas as gpd
import pandas as pd

from config import (
    COLUMN_MAPPINGS,
    DATA_DIR,
    GRUNDVAND_GDB_PATH,
    GRUNDVAND_LAYER_NAME,
    SHAPE_DIR,
    V1_CSV_PATH,
    V2_CSV_PATH,
    V1_SHP_PATH,
    V2_SHP_PATH,
)
import warnings

warnings.filterwarnings(
    "ignore",
    message=r"organizePolygons\(\) received a polygon with more than 100 parts",
    module="pyogrio.raw",
)

LEGACY_PATTERN = "VP3Genbesøg_grundvand_geometri.shp"
GVFK_COLUMN = COLUMN_MAPPINGS["grundvand"]["gvfk_id"]


def _locate_legacy_shapefile() -> Path:
    """Locate the legacy GVFK shapefile, falling back to glob search if needed."""
    direct = SHAPE_DIR / LEGACY_PATTERN
    if direct.exists():
        return direct

    # Try globbing locally (handles casing/encoding quirks on synced folders)
    candidates = sorted(SHAPE_DIR.glob(LEGACY_PATTERN))
    if not candidates:
        candidates = sorted(SHAPE_DIR.glob("VP3Genbesog*.shp"))
    if not candidates:
        candidates = sorted(SHAPE_DIR.rglob(LEGACY_PATTERN))
    if not candidates:
        candidates = sorted(SHAPE_DIR.rglob("VP3Genbesog*.shp"))
    if candidates:
        print(f"Using legacy GVFK shapefile: {candidates[0]}")
        return candidates[0]

    raise FileNotFoundError(
        f"Could not find legacy GVFK shapefile under {SHAPE_DIR} "
        f"(looked for {LEGACY_PATTERN})"
    )


def load_gvfk_names() -> Tuple[Set[str], Set[str]]:
    """Return sets of GVFK names from the legacy shapefile and new GDB layer."""
    legacy_path = _locate_legacy_shapefile()
    if not GRUNDVAND_GDB_PATH.exists():
        raise FileNotFoundError(f"Grunddata geodatabase not found: {GRUNDVAND_GDB_PATH}")

    old_gdf = gpd.read_file(legacy_path)
    new_gdf = gpd.read_file(GRUNDVAND_GDB_PATH, layer=GRUNDVAND_LAYER_NAME)

    def _extract_column(frame, primary: str, fallback: Tuple[str, ...] = ()) -> gpd.GeoSeries:
        candidates = (primary,) + fallback
        lower_map = {col.lower(): col for col in frame.columns}
        for candidate in candidates:
            if candidate in frame.columns:
                return frame[candidate]
            cand_lower = candidate.lower()
            if cand_lower in lower_map:
                return frame[lower_map[cand_lower]]
        raise KeyError(
            f"Columns {candidates} not found in dataset. Available: {frame.columns.tolist()}"
        )

    def normalize(values) -> Set[str]:
        return {
            str(name).strip()
            for name in values
            if isinstance(name, str) and name.strip()
        }

    old_series = _extract_column(old_gdf, GVFK_COLUMN, ("Navn",))
    new_series = _extract_column(new_gdf, GVFK_COLUMN, ("Navn",))

    return normalize(old_series), normalize(
        new_series
    )

def compare_gvfk_sets() -> None:
    old_names, new_names = load_gvfk_names()

    shared = sorted(old_names & new_names)
    only_old = sorted(old_names - new_names)
    only_new = sorted(new_names - old_names)

    print("=== GVFK Coverage Comparison ===")
    print(f"Legacy shapefile GVFK count: {len(old_names)}")
    print(f"New Grunddata GVFK count:   {len(new_names)}")
    print(f"Shared GVFK count:         {len(shared)}")
    print(f"Legacy-only GVFK count:    {len(only_old)}")
    print(f"New-only GVFK count:       {len(only_new)}")
    print()

    if only_old:
        print("--- GVFK present only in legacy file ---")
        for name in only_old:
            print(f"  {name}")
        print()

    if only_new:
        print("--- GVFK present only in new Grunddata layer ---")
        for name in only_new:
            print(f"  {name}")
        print()

    if shared:
        print("Example shared GVFKs:")
        for name in shared[:20]:
            print(f"  {name}")


def compare_site_gvfk_mappings() -> None:
    """
    Compare site-GVFK mappings between existing CSV files and fresh spatial overlay.
    
    This does a full spatial analysis to check if the existing V1/V2 CSV mappings
    (based on the legacy GVFK shapefile) would differ significantly if we used
    the new Grunddata GVFK layer instead.
    """
    print("\n" + "=" * 60)
    print("SITE-GVFK MAPPING COMPARISON")
    print("Comparing existing CSV mappings vs. new GVFK spatial overlay")
    print("=" * 60 + "\n")
    
    # Column names
    site_id_col = "Lokalitets"  # Truncated in shapefile from Lokalitetsnr
    csv_site_col = COLUMN_MAPPINGS["contamination_csv"]["site_id"]  # Lokalitetsnr
    csv_gvfk_col = COLUMN_MAPPINGS["contamination_csv"]["gvfk_id"]  # Navn
    new_gvfk_col = GVFK_COLUMN  # GVForekom
    
    # Load new GVFK polygons
    print("Loading new GVFK polygons from Grunddata...")
    new_gvfk = gpd.read_file(GRUNDVAND_GDB_PATH, layer=GRUNDVAND_LAYER_NAME)
    print(f"  Loaded {len(new_gvfk)} GVFK polygons")
    
    results = {}
    
    for version, csv_path, shp_path in [
        ("V1", V1_CSV_PATH, V1_SHP_PATH),
        ("V2", V2_CSV_PATH, V2_SHP_PATH),
    ]:
        print(f"\n--- {version} Analysis ---")
        
        # Load existing CSV mappings
        csv_df = pd.read_csv(csv_path)
        existing_pairs = set(
            zip(csv_df[csv_site_col].astype(str), csv_df[csv_gvfk_col].astype(str))
        )
        existing_sites = set(csv_df[csv_site_col].astype(str))
        print(f"  Existing CSV: {len(csv_df)} rows, {len(existing_sites)} unique sites, {len(existing_pairs)} unique site-GVFK pairs")
        
        # Load site geometries
        print(f"  Loading {version} site geometries...")
        sites_gdf = gpd.read_file(shp_path)
        sites_gdf = sites_gdf.to_crs(new_gvfk.crs)
        print(f"  Loaded {len(sites_gdf)} site polygons")
        
        # Perform spatial overlay
        print("  Performing spatial overlay (this may take a moment)...")
        overlay = gpd.overlay(
            sites_gdf[[site_id_col, "geometry"]],
            new_gvfk[[new_gvfk_col, "geometry"]],
            how="intersection",
            keep_geom_type=False,
        )
        
        # Extract new site-GVFK pairs
        new_pairs = set(
            zip(overlay[site_id_col].astype(str), overlay[new_gvfk_col].astype(str))
        )
        new_sites_with_gvfk = set(overlay[site_id_col].astype(str))
        print(f"  New overlay: {len(overlay)} intersections, {len(new_sites_with_gvfk)} unique sites, {len(new_pairs)} unique site-GVFK pairs")
        
        # Compare
        matching_pairs = existing_pairs & new_pairs
        only_in_existing = existing_pairs - new_pairs
        only_in_new = new_pairs - existing_pairs
        
        # Site-level analysis
        sites_lost = existing_sites - new_sites_with_gvfk  # Had GVFK before, none now
        sites_gained = new_sites_with_gvfk - existing_sites  # No GVFK before, has now
        
        print(f"\n  PAIR-LEVEL COMPARISON:")
        print(f"    Matching pairs:      {len(matching_pairs):,}")
        print(f"    Only in existing:    {len(only_in_existing):,}")
        print(f"    Only in new overlay: {len(only_in_new):,}")
        
        if len(existing_pairs) > 0:
            match_pct = 100.0 * len(matching_pairs) / len(existing_pairs)
            print(f"    Match rate:          {match_pct:.1f}%")
        
        print(f"\n  SITE-LEVEL COMPARISON:")
        print(f"    Sites that would LOSE all GVFK connections: {len(sites_lost):,}")
        print(f"    Sites that would GAIN new GVFK connections: {len(sites_gained):,}")
        
        if sites_lost:
            print(f"\n  Sample sites losing GVFK (first 10):")
            for site in sorted(sites_lost)[:10]:
                # Find which GVFK they had
                old_gvfks = [g for s, g in existing_pairs if s == site]
                print(f"    {site} -> was in: {', '.join(old_gvfks[:3])}{'...' if len(old_gvfks) > 3 else ''}")
        
        results[version] = {
            "existing_pairs": len(existing_pairs),
            "new_pairs": len(new_pairs),
            "matching": len(matching_pairs),
            "only_existing": len(only_in_existing),
            "only_new": len(only_in_new),
            "sites_lost": len(sites_lost),
            "sites_gained": len(sites_gained),
        }
    
    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    for version, stats in results.items():
        match_pct = 100.0 * stats["matching"] / stats["existing_pairs"] if stats["existing_pairs"] > 0 else 0
        print(f"\n{version}:")
        print(f"  Pair match rate: {match_pct:.1f}%")
        print(f"  Sites losing GVFK: {stats['sites_lost']}")
        print(f"  Sites gaining GVFK: {stats['sites_gained']}")
    
    return results


def generate_updated_csvs() -> Tuple[Path, Path]:
    """
    Generate new V1/V2 CSV files with GVFK mappings from the new Grunddata layer.
    
    This performs a spatial overlay between site polygons and the new GVFK polygons,
    then creates CSV files with the same structure as the originals but with updated
    'Navn' column values based on the new spatial relationships.
    
    The original CSV has one row per (site × GVFK × substance). This function:
    1. Gets unique (site, substance, other metadata) combinations from original
    2. Computes new site-GVFK mappings via spatial overlay
    3. Joins to create new rows with updated GVFK assignments
    
    Returns:
        Tuple of paths to the generated V1 and V2 CSV files
    """
    print("\n" + "=" * 60)
    print("GENERATING UPDATED V1/V2 CSV FILES")
    print("Using new Grunddata GVFK spatial overlay")
    print("=" * 60 + "\n")
    
    # Column names
    site_id_shp = "Lokalitets"  # Truncated in shapefile
    csv_site_col = COLUMN_MAPPINGS["contamination_csv"]["site_id"]  # Lokalitetsnr
    csv_gvfk_col = COLUMN_MAPPINGS["contamination_csv"]["gvfk_id"]  # Navn
    new_gvfk_col = GVFK_COLUMN  # GVForekom
    
    # Load new GVFK polygons
    print("Loading new GVFK polygons from Grunddata...")
    new_gvfk = gpd.read_file(GRUNDVAND_GDB_PATH, layer=GRUNDVAND_LAYER_NAME)
    print(f"  Loaded {len(new_gvfk)} GVFK polygons")
    
    output_paths = []
    
    for version, csv_path, shp_path in [
        ("V1", V1_CSV_PATH, V1_SHP_PATH),
        ("V2", V2_CSV_PATH, V2_SHP_PATH),
    ]:
        print(f"\n--- Processing {version} ---")
        
        # Load existing CSV
        csv_df = pd.read_csv(csv_path)
        print(f"  Existing CSV: {len(csv_df)} rows, {csv_df[csv_site_col].nunique()} unique sites")
        
        # Get unique site-level rows (drop GVFK-related columns, keep everything else)
        # This gives us unique (site, substance, other metadata) combinations
        # Note: 'ID' column also contains GVFK info (e.g. "203_dkms_3645_ks")
        gvfk_related_cols = [csv_gvfk_col, 'ID']
        cols_except_gvfk = [c for c in csv_df.columns if c not in gvfk_related_cols]
        site_rows = csv_df[cols_except_gvfk].drop_duplicates()
        print(f"  Unique (site, substance, metadata) combinations: {len(site_rows)}")
        
        # Load site geometries
        print(f"  Loading {version} site geometries...")
        sites_gdf = gpd.read_file(shp_path)
        sites_gdf = sites_gdf.to_crs(new_gvfk.crs)
        print(f"  Loaded {len(sites_gdf)} site polygons")
        
        # Perform spatial overlay to find all site-GVFK intersections
        print("  Performing spatial overlay...")
        overlay = gpd.overlay(
            sites_gdf[[site_id_shp, "geometry"]],
            new_gvfk[[new_gvfk_col, "geometry"]],
            how="intersection",
            keep_geom_type=False,
        )
        
        # Create site-GVFK mapping dataframe
        site_gvfk_map = overlay[[site_id_shp, new_gvfk_col]].drop_duplicates()
        site_gvfk_map = site_gvfk_map.rename(columns={
            site_id_shp: csv_site_col,
            new_gvfk_col: csv_gvfk_col
        })
        print(f"  Found {len(site_gvfk_map)} unique site-GVFK pairs from new overlay")
        
        # Join: site_rows × new GVFK mappings
        # This creates one row per (site, substance, GVFK) combination
        new_csv = site_rows.merge(site_gvfk_map, on=csv_site_col, how="left")
        
        # Reorder columns to match original
        col_order = list(csv_df.columns)
        new_csv = new_csv[[c for c in col_order if c in new_csv.columns]]
        
        # Stats
        nan_count = new_csv[csv_gvfk_col].isna().sum()
        print(f"  New CSV: {len(new_csv)} rows")
        print(f"  Rows with valid GVFK: {len(new_csv) - nan_count}")
        print(f"  Rows with nan GVFK: {nan_count}")
        
        # Compare to old
        old_row_count = len(csv_df)
        diff = len(new_csv) - old_row_count
        diff_pct = 100.0 * diff / old_row_count if old_row_count > 0 else 0
        print(f"  Row count change: {diff:+,} ({diff_pct:+.1f}%)")
        
        # Save to new file
        output_path = DATA_DIR / f"{version.lower()}_gvfk_forurening_NEW.csv"
        new_csv.to_csv(output_path, index=False)
        print(f"  Saved to: {output_path}")
        output_paths.append(output_path)
    
    print("\n" + "=" * 60)
    print("DONE - New CSV files generated")
    print("=" * 60)
    print("\nTo use new mappings, update config.py:")
    print(f'  V1_CSV_PATH = DATA_DIR / "v1_gvfk_forurening_NEW.csv"')
    print(f'  V2_CSV_PATH = DATA_DIR / "v2_gvfk_forurening_NEW.csv"')
    
    return tuple(output_paths)


if __name__ == "__main__":
    compare_gvfk_sets()
    compare_site_gvfk_mappings()
    generate_updated_csvs()

