"""Quick check of raster pixel size"""
import sys
sys.path.insert(0, '.')
import rasterio
from config import GVD_RASTER_DIR

files = list(GVD_RASTER_DIR.glob('*.tif'))[:3]
for f in files:
    src = rasterio.open(f)
    print(f"File: {f.name}")
    print(f"  Pixel width: {abs(src.transform[0]):.1f} meters")
    print(f"  Pixel height: {abs(src.transform[4]):.1f} meters")
    print(f"  CRS: {src.crs}")
    src.close()
    print()
