"""
Tool to compare infiltration filter statistics between:
1. Current method (all_touched=False + Centroid Fallback)
2. Proposed method (all_touched=True)

Usage:
    python Kode/tools/compare_infiltration_methods.py
"""

from pathlib import Path
import sys
import numpy as np
import pandas as pd
import geopandas as gpd
import rasterio
from rasterio.mask import mask
from shapely.geometry import mapping

# Add Kode directory to path
KODE_DIR = Path(__file__).resolve().parents[1] 
if str(KODE_DIR) not in sys.path:
    sys.path.insert(0, str(KODE_DIR))

from config import GVD_RASTER_DIR
from risikovurdering.step2_river_contact import run_step2
from risikovurdering.step3_v1v2_sites import run_step3
from risikovurdering.step3b_infiltration_filter import (
    _build_raster_filename, _parse_dk_modellag, load_gvfk_layer_mapping
)

def sample_pixels(layer, model_region, geometry, centroid, all_touched=False):
    """
    Generic sampling function that toggles between methods.
    """
    normalized_layer = str(layer).lower()
    raster_filename = _build_raster_filename(normalized_layer, model_region)
    if raster_filename is None:
        return None
        
    raster_file = GVD_RASTER_DIR / raster_filename
    if not raster_file.exists() and not raster_filename.startswith("dk16_"):
        fallback = GVD_RASTER_DIR / f"dk16_gvd_{normalized_layer}.tif"
        if fallback.exists():
            raster_file = fallback

    if not raster_file.exists():
        return None

    try:
        with rasterio.open(raster_file) as src:
            nodata = src.nodata
            
            # Method 1: Polygon Sampling
            try:
                geom_geojson = [mapping(geometry)]
                masked_data, _ = mask(src, geom_geojson, crop=True, all_touched=all_touched)
                valid_data = masked_data[(masked_data != nodata) & (~np.isnan(masked_data))]
                
                if valid_data.size > 0:
                    return valid_data.flatten().tolist()
            except Exception:
                pass
            
            # Fallback (Only relevant if Method 1 fails, e.g. for all_touched=False)
            # If all_touched=True, it naturally grabs the pixel if it touches anything.
            # But let's keep the fallback for consistency if it returns nothing.
            if centroid is not None:
                try:
                    coords = [(centroid.x, centroid.y)]
                    sampled = list(src.sample(coords))
                    if sampled and sampled[0][0] != nodata:
                        return [float(sampled[0][0])]
                except Exception:
                    pass
            
            return None
    except Exception:
        return None

def analyze_method(sites_df, layer_mapping, method_name, all_touched_flag):
    print(f"\nAnalyzing with Method: {method_name} (all_touched={all_touched_flag})")
    
    pixel_counts = []
    classifications = [] # "downward", "upward", "no_data"
    
    # Process a subset to save time if needed, or full set
    # Let's do first 1000 sites for speed, or full if user wants. 
    # The user quoted 32k sites, so maybe sampling 2000 is good for a quick test.
    sample_df = sites_df # Process all for accurate stats if possible
    
    processed = 0
    total = len(sample_df)
    
    for idx, row in sample_df.iterrows():
        processed += 1
        if processed % 5000 == 0:
            print(f"  Processed {processed}/{total}...")
            
        lok_id = row["Lokalitet_ID"]
        gvfk = row["GVFK"]
        geometry = row["geometry"]
        centroid = geometry.centroid
        
        # Look up layer info
        layer_info = layer_mapping[layer_mapping["GVForekom"] == gvfk]
        if layer_info.empty:
            continue
            
        dk_modellag = layer_info.iloc[0]["dkmlag"]
        region = str(layer_info.iloc[0]["dknr"] if pd.notna(layer_info.iloc[0]["dknr"]) else "dk16")
        
        layers = _parse_dk_modellag(dk_modellag)
        
        all_vals = []
        for layer in layers:
            vals = sample_pixels(layer, region, geometry, centroid, all_touched=all_touched_flag)
            if vals:
                all_vals.extend(vals)
        
        count = len(all_vals)
        pixel_counts.append(count)
        
        if count == 0:
            classifications.append("no_data")
        else:
            binary = [1 if v >= 0 else 0 for v in all_vals]
            vote = sum(binary) / len(binary)
            if vote > 0.5:
                classifications.append("downward")
            else:
                classifications.append("upward")

    return pixel_counts, classifications

def run_comparison():
    print("Loading data...")
    # Get Step 3 output
    rivers, _, _ = run_step2()
    _, v1v2_sites = run_step3(rivers)
    
    # Prepare data
    v1v2_sites = v1v2_sites[["Lokalitet_", "Navn", "geometry"]].rename(
        columns={"Lokalitet_": "Lokalitet_ID", "Navn": "GVFK"}
    )
    
    # Layer mapping
    mapping_df = load_gvfk_layer_mapping(columns=["GVForekom", "dkmlag", "dknr"])
    
    print(f"Total sites to analyze: {len(v1v2_sites)}")
    
    # Run Method 1: Current (False)
    counts_current, class_current = analyze_method(v1v2_sites, mapping_df, "Current (Center)", False)
    
    # Run Method 2: Proposed (True)
    counts_prop, class_prop = analyze_method(v1v2_sites, mapping_df, "Proposed (All Touched)", True)
    
    # Compare
    c_curr = np.array(counts_current)
    c_prop = np.array(counts_prop)
    
    print("\n=== Comparison Results ===")
    print(f"{'Metric':<25} | {'Current':<15} | {'Proposed':<15} | {'Diff':<10}")
    print("-" * 75)
    print(f"{'Mean Pixels':<25} | {c_curr.mean():<15.2f} | {c_prop.mean():<15.2f} | {c_prop.mean()-c_curr.mean():+.2f}")
    print(f"{'Median Pixels':<25} | {np.median(c_curr):<15.0f} | {np.median(c_prop):<15.0f} | {np.median(c_prop)-np.median(c_curr):+.0f}")
    print(f"{'Sites <= 5 pixels':<25} | {(c_curr<=5).mean()*100:<15.1f}%| {(c_prop<=5).mean()*100:<15.1f}%| {(c_prop<=5).mean()*100-(c_curr<=5).mean()*100:+.1f}%")
    
    # Classification changes
    changes = 0
    to_upward = 0 # Down -> Up (Kept -> Removed)
    to_downward = 0 # Up -> Down (Removed -> Kept)
    
    for i in range(len(class_current)):
        c1 = class_current[i]
        c2 = class_prop[i]
        if c1 != c2:
            changes += 1
            if c1 == "downward" and c2 == "upward":
                to_upward += 1
            elif c1 == "upward" and c2 == "downward":
                to_downward += 1
                
    print(f"\nClassification Stability:")
    print(f"  Total sites changed classification: {changes} ({changes/len(class_current)*100:.2f}%)")
    print(f"  Downward -> Upward (Newly Removed): {to_upward}")
    print(f"  Upward -> Downward (Newly Kept):    {to_downward}")

if __name__ == "__main__":
    run_comparison()
