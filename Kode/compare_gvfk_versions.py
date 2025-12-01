from __future__ import annotations

from pathlib import Path
from typing import Set, Tuple

import geopandas as gpd

from config import (
    COLUMN_MAPPINGS,
    GRUNDVAND_GDB_PATH,
    GRUNDVAND_LAYER_NAME,
    SHAPE_DIR,
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


if __name__ == "__main__":
    compare_gvfk_sets()
