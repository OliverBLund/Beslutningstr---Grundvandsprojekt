"""
Map missing-infiltration sites with their GVFK polygons and raster footprints.

- Reads step6_filtering_audit for Filter_3_Missing_Infiltration.
- Joins to step3_v1v2_sites for geometries.
- Loads GVFK polygons for the affected GVFKs.
- Draws raster footprints for the modellag in use (e.g. dk16_gvd_kvs_0200.tif).
- Saves HTML map to Resultater/step6_tilstandsvurdering/figures/missing_infiltration_map.html
"""

import sys
from pathlib import Path

import folium
import geopandas as gpd
import pandas as pd
import rasterio
from shapely.geometry import box

# Make repo root importable
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from config import (
    GVD_RASTER_DIR,
    GRUNDVAND_LAYER_NAME,
    GRUNDVAND_PATH,
    get_output_path,
)
from data_loaders import load_gvfk_layer_mapping

SITE_ID_COL = "Lokalitet_"
GVFK_COL = "GVFK"


def load_raster_footprints(modellag_codes):
    feats = []
    for code in modellag_codes:
        for region in ["dk16", "dk7"]:
            tif = GVD_RASTER_DIR / f"{region}_gvd_{code}.tif"
            if not tif.exists():
                continue
            try:
                with rasterio.open(tif) as src:
                    feats.append(
                        {
                            "modellag": code,
                            "region": region,
                            "path": str(tif),
                            "geometry": box(*src.bounds),
                            "crs": src.crs,
                        }
                    )
            except Exception as exc:
                print(f"WARN: cannot read {tif} ({exc})")
    return gpd.GeoDataFrame(feats) if feats else gpd.GeoDataFrame(columns=["modellag", "region", "path", "geometry"])


def main():
    audit = pd.read_csv(get_output_path("step6_filtering_audit"), encoding="utf-8")
    miss = audit[audit["Filter_Stage"] == "Filter_3_Missing_Infiltration"].copy()
    if miss.empty:
        print("No missing infiltration rows.")
        return

    sites = gpd.read_file(get_output_path("step3_v1v2_sites"))
    sites = sites[sites[SITE_ID_COL].isin(miss["Lokalitet_ID"])]
    if sites.empty:
        print("No site geometries found for missing rows.")
        return

    # Affected GVFKs
    affected_gvfk = miss[GVFK_COL].dropna().unique().tolist()
    gvfk_gdf = gpd.read_file(GRUNDVAND_PATH, layer=GRUNDVAND_LAYER_NAME)
    # Normalize GVFK id column
    if "GVFK" in gvfk_gdf.columns:
        gvfk_gdf = gvfk_gdf.rename(columns={"GVFK": "GVFK_ID"})
    elif "GVForekom" in gvfk_gdf.columns:
        gvfk_gdf = gvfk_gdf.rename(columns={"GVForekom": "GVFK_ID"})
    elif "Navn" in gvfk_gdf.columns:
        gvfk_gdf = gvfk_gdf.rename(columns={"Navn": "GVFK_ID"})
    else:
        raise KeyError("Could not find GVFK column in Grundvand layer (expected GVFK/GVForekom/Navn)")

    gvfk_sel = gvfk_gdf[gvfk_gdf["GVFK_ID"].isin(affected_gvfk)].to_crs("EPSG:4326")

    # Collect modellag codes from layer mapping for affected GVFKs
    modellag_codes = []
    try:
        layer_map = load_gvfk_layer_mapping(columns=["GVForekom", "dkmlag", "dknr"])
        layer_map = layer_map.rename(columns={"GVForekom": "GVFK_ID", "dkmlag": "DK-modellag"})
        modellag_codes = (
            layer_map[layer_map["GVFK_ID"].isin(affected_gvfk)]["DK-modellag"]
            .dropna()
            .astype(str)
            .str.split("/")
            .explode()
            .str.strip()
            .unique()
            .tolist()
        )
    except Exception as exc:
        print(f"WARN: could not load GVFK layer mapping for modellag codes ({exc})")

    raster_gdf = load_raster_footprints(modellag_codes)
    if not raster_gdf.empty and raster_gdf.crs is not None:
        raster_gdf = raster_gdf.to_crs("EPSG:4326")

    # Project sites to web CRS
    sites_web = sites.to_crs("EPSG:4326")

    bounds = sites_web.total_bounds
    center_lat = (bounds[1] + bounds[3]) / 2
    center_lon = (bounds[0] + bounds[2]) / 2

    m = folium.Map(location=[center_lat, center_lon], zoom_start=7, tiles="OpenStreetMap", control_scale=True)

    # Raster footprints
    if not raster_gdf.empty:
        for _, r in raster_gdf.iterrows():
            folium.GeoJson(
                r.geometry.__geo_interface__,
                style_function=lambda x, col="#888888": {"color": col, "weight": 2, "fill": False, "opacity": 0.5},
                popup=folium.Popup(f"Raster: {Path(r['path']).name}<br>Modellag: {r['modellag']}", max_width=250),
            ).add_to(m)

    # GVFK polygons
    for _, g in gvfk_sel.iterrows():
        folium.GeoJson(
            g.geometry.__geo_interface__,
            style_function=lambda x, col="#0000FF": {"color": col, "weight": 2, "fill": False, "opacity": 0.5},
            popup=folium.Popup(f"GVFK: {g.get('GVFK_ID','?')}", max_width=200),
        ).add_to(m)

    # Missing sites
    for _, s in sites_web.iterrows():
        folium.GeoJson(
            s.geometry.__geo_interface__,
            style_function=lambda x, col="#FF0000": {"color": col, "weight": 2, "fill": True, "fillOpacity": 0.6},
            popup=folium.Popup(f"Site: {s[SITE_ID_COL]}", max_width=200),
        ).add_to(m)

    out_path = get_output_path("step6_site_mkk_exceedances").with_name("step6_missing_infiltration_map.html")
    m.save(out_path)
    print(f"Map saved: {out_path}")


if __name__ == "__main__":
    main()
