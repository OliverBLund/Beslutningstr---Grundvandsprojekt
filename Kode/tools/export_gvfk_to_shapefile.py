"""
Export GVFK (Grundvandsforekomst) layer from geodatabase to shapefile.

This script extracts the groundwater body layer from the Grunddata geodatabase
and saves it as a standalone shapefile for easier use in other applications.
"""

import geopandas as gpd
import sys
from pathlib import Path

# Add parent directory to path for config import
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config import (
    GRUNDVAND_GDB_PATH,
    GRUNDVAND_LAYER_NAME,
    SHAPE_DIR,
)


def export_gvfk_to_shapefile(output_path: Path | None = None) -> Path:
    """
    Export the GVFK layer from geodatabase to shapefile.

    Args:
        output_path: Optional custom output path. Defaults to SHAPE_DIR/gvfk.shp

    Returns:
        Path to the created shapefile
    """
    # Default output path
    if output_path is None:
        output_path = SHAPE_DIR / "gvfk.shp"

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"Reading GVFK layer from: {GRUNDVAND_GDB_PATH}")
    print(f"Layer name: {GRUNDVAND_LAYER_NAME}")

    # Read the layer from geodatabase
    gdf = gpd.read_file(GRUNDVAND_GDB_PATH, layer=GRUNDVAND_LAYER_NAME)

    print(f"Loaded {len(gdf):,} features")
    print(f"CRS: {gdf.crs}")
    print(f"Columns: {list(gdf.columns)}")

    # Save to shapefile
    print(f"\nExporting to: {output_path}")
    gdf.to_file(output_path)

    print(f"Done! Shapefile saved with {len(gdf):,} features.")

    return output_path


if __name__ == "__main__":
    export_gvfk_to_shapefile()
