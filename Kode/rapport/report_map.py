"""
Report Map — All GVFKs vs Risk GVFKs (Trin 5b)
================================================

Two-panel landscape map, both colored by region.

  Map 1 — All 2,049 GVFKs colored by region (the starting point).
  Map 2 — Only the 187 Trin 5b risk GVFKs colored by region (the result).

Region assignment: each GVFK is assigned to the region with the greatest
spatial overlap (>50% rule; if no region exceeds 50%, the largest overlap wins).

Bornholm excluded for visual clarity.

Run from Kode/ directory:  python report_map.py
Output: Resultater/workflow_summary/report/report_denmark_map.png
"""

import os, sys
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from pathlib import Path

# Must be set before pyogrio/geopandas loads the GDB
os.environ["GDAL_ORGANIZE_POLYGONS"] = "SKIP"

BASE = Path(__file__).parent.parent
sys.path.insert(0, str(Path(__file__).parent))
OUT_DIR = BASE / "Resultater" / "workflow_summary" / "report"

plt.rcParams.update({
    "font.family":       ["Arial", "DejaVu Sans", "sans-serif"],
    "font.size":          13,
    "figure.facecolor":  "white",
    "savefig.dpi":        250,
    "savefig.bbox":      "tight",
    "savefig.facecolor": "white",
})

# ColorBrewer Blues — 5 distinct shades (darkest → lightest)
# All clearly blue against the white Denmark backdrop
REGION_COLORS = {
    "Region Hovedstaden": "#084594",
    "Region Midtjylland": "#2171b5",
    "Region Nordjylland": "#4292c6",
    "Region Sjælland":    "#6baed6",
    "Region Syddanmark":  "#9ecae1",
}
REGION_SHORT = {
    "Region Hovedstaden": "Hovedstaden",
    "Region Midtjylland": "Midtjylland",
    "Region Nordjylland": "Nordjylland",
    "Region Sjælland":    "Sjælland",
    "Region Syddanmark":  "Syddanmark",
}
BORNHOLM_XMAX = 840_000   # UTM32N metres — everything east of this is Bornholm


def clip_bornholm(gdf):
    from shapely.geometry import box
    return gdf.clip(box(0, 0, BORNHOLM_XMAX, 9_999_999))


def _pick_existing_column(columns, candidates):
    """Return the first column name from candidates that exists in columns."""
    for col in candidates:
        if col in columns:
            return col
    return None


def _load_step6_q95(get_output_path):
    """
    Load Step 6 site exceedances and keep Q95 only.
    Falls back to all rows if Flow_Scenario is unavailable.
    """
    step6 = pd.read_csv(get_output_path("step6_site_mkk_exceedances"))
    if "Flow_Scenario" in step6.columns:
        q95 = step6[step6["Flow_Scenario"] == "Q95"].copy()
        if not q95.empty:
            return q95
    return step6


def assign_regions(gvfk_gdf, regions_gdf, gvfk_col):
    """
    Spatial join: assign each GVFK to the region it overlaps most.
    Returns the gvfk_gdf with an added 'Region' column.
    """
    import geopandas as gpd

    # Compute intersection areas
    gvfk_simple = gvfk_gdf[[gvfk_col, "geometry"]].copy()
    gvfk_simple["orig_area"] = gvfk_simple.geometry.area

    overlaps = gpd.overlay(
        gvfk_simple, regions_gdf[["Region", "geometry"]], how="intersection"
    )
    overlaps["overlap_area"] = overlaps.geometry.area

    # For each GVFK, keep the region with the largest overlap
    best = (
        overlaps.sort_values("overlap_area", ascending=False)
        .drop_duplicates(subset=gvfk_col)[[gvfk_col, "Region"]]
    )
    return gvfk_gdf.merge(best, on=gvfk_col, how="left")


def draw_panel(ax, gdf, regions, denmark, bounds,
               alpha_poly, edge_color, edge_width, badge_text):
    """Render one map panel."""
    xmin, ymin, xmax, ymax = bounds
    px = (xmax - xmin) * 0.02
    py = (ymax - ymin) * 0.02

    # Backdrop: white Denmark fill + region borders + outer border
    # White = no GVFK coverage; blue = GVFK present
    denmark.plot(ax=ax, color="#FFFFFF", edgecolor="none")
    regions.boundary.plot(ax=ax, color="#333333", linewidth=0.4)
    denmark.boundary.plot(ax=ax, color="#111111", linewidth=0.8)

    # GVFK polygons — colored by region
    for region, color in REGION_COLORS.items():
        subset = gdf[gdf["Region"] == region]
        if len(subset):
            subset.plot(ax=ax, color=color,
                        alpha=alpha_poly,
                        edgecolor=edge_color,
                        linewidth=edge_width)

    ax.set_xlim(xmin - px, xmax + px)
    ax.set_ylim(ymin - py, ymax + py)
    ax.set_aspect("equal")
    ax.axis("off")

    ax.text(0.50, 0.01, badge_text,
            transform=ax.transAxes, ha="center", va="top", fontsize=17,
            bbox=dict(boxstyle="round,pad=0.5", facecolor="white",
                      edgecolor="#cccccc", alpha=0.92))


def create_denmark_map():
    import geopandas as gpd
    from config import (
        GRUNDVAND_PATH, GRUNDVAND_LAYER_NAME,
        COLUMN_MAPPINGS, get_output_path, DATA_DIR,
    )

    print("\n" + "=" * 55)
    print("REPORT MAP — All GVFKs vs Trin 5b Results")
    print("=" * 55)

    gvfk_col = COLUMN_MAPPINGS["grundvand"]["gvfk_id"]

    # ── Regions ────────────────────────────────────────────────────────────────
    print("\n[1/4] Regions...")
    regions = gpd.read_file(DATA_DIR / "regionsinddeling" / "regionsinddeling.shp")
    crs = regions.crs
    for col in ["Regionsnavn", "regionsnavn", "REGIONNAVN", "Navn", "navn"]:
        if col in regions.columns:
            regions = regions.rename(columns={col: "Region"})
            break
    regions = clip_bornholm(regions)[["Region", "geometry"]].copy()
    denmark = regions.dissolve()
    bounds  = denmark.total_bounds

    # ── All 2049 GVFKs from GDB ────────────────────────────────────────────────
    print("[2/4] All GVFKs from GDB (this may take ~1 min)...")
    all_gvfk = gpd.read_file(GRUNDVAND_PATH, layer=GRUNDVAND_LAYER_NAME)
    all_gvfk = all_gvfk.to_crs(crs)
    print(f"      {all_gvfk[gvfk_col].nunique()} unique GVFKs  — simplifying...")
    all_gvfk["geometry"] = all_gvfk.geometry.simplify(50, preserve_topology=True)
    total_gvfk_count = all_gvfk[gvfk_col].nunique()   # count BEFORE clipping
    all_gvfk = clip_bornholm(all_gvfk)

    print("      Assigning regions (spatial overlay)...")
    all_gvfk = assign_regions(all_gvfk, regions, gvfk_col)
    print(f"      Region distribution:\n{all_gvfk['Region'].value_counts().to_string()}")

    # ── Step 5b risk GVFKs ────────────────────────────────────────────────────
    print("[3/4] Step 5b risk GVFKs...")
    p3_gdf = gpd.read_file(get_output_path("step3_gvfk_polygons")).to_crs(crs)
    p3_gdf["geometry"] = p3_gdf.geometry.simplify(50, preserve_topology=True)

    df5b  = pd.read_csv(get_output_path("step5b_compound_combinations"))
    ids5b = set(df5b["GVFK"])
    gdf5b = clip_bornholm(p3_gdf[p3_gdf[gvfk_col].isin(ids5b)].copy())

    print("      Assigning regions (spatial overlay)...")
    gdf5b = assign_regions(gdf5b, regions, gvfk_col)
    print(f"      Region distribution:\n{gdf5b['Region'].value_counts().to_string()}")

    # ── Draw ──────────────────────────────────────────────────────────────────
    print("\n[4/4] Drawing...")
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(17, 10))
    fig.subplots_adjust(wspace=0.05)

    draw_panel(
        ax1, all_gvfk, regions, denmark, bounds,
        alpha_poly=0.40,
        edge_color="white",
        edge_width=0.10,
        badge_text=f"Alle {total_gvfk_count:,} GVF (udgangspunkt)",
    )

    draw_panel(
        ax2, gdf5b, regions, denmark, bounds,
        alpha_poly=1.0,
        edge_color="white",
        edge_width=0.5,
        badge_text=f"{len(ids5b)} GVF med stofspecifik risiko",
    )

    # ── Legend — show (Map1 count / Map2 count) per region ────────────────────
    # Load counts from the existing regional summary CSV for consistency
    summary_csv = BASE / "Resultater" / "workflow_summary" / "regional_summary_transposed.csv"
    reg_counts1 = {}   # Trin 1 GVFK counts
    reg_counts2 = {}   # Trin 5b GVFK counts
    try:
        sdf = pd.read_csv(summary_csv)
        gvfk_df = sdf[sdf["Metric"] == "GVFK"]
        row1 = gvfk_df[gvfk_df["Step"] == "Trin 1 (Alle)"].iloc[0]
        row5 = gvfk_df[gvfk_df["Step"] == "Trin 5b (Stof. Risiko)"].iloc[0]
        for r in REGION_COLORS:
            reg_counts1[r] = int(row1[r])
            reg_counts2[r] = int(row5[r])
    except Exception:
        pass   # fallback: labels without counts

    handles = []
    for r, c in REGION_COLORS.items():
        if reg_counts1 and reg_counts2:
            label = f"{REGION_SHORT[r]}  ({reg_counts1[r]} / {reg_counts2[r]})"
        else:
            label = REGION_SHORT[r]
        handles.append(mpatches.Patch(facecolor=c, edgecolor="white", label=label))

    fig.legend(handles=handles, loc="lower center", ncol=5,
               bbox_to_anchor=(0.5, -0.06),
               fontsize=17, frameon=True,
               facecolor="white", edgecolor="#cccccc",
               title="Region  (antal GVF: udgangspunkt / risiko)",
               title_fontsize=17)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUT_DIR / "report_denmark_map.png"
    plt.savefig(out)
    plt.close()
    print(f"\n  Saved: {out}")


# ── Shared helpers for hex-overlay variants ────────────────────────────────

def _load_region_counts():
    """Load Trin 1 and Trin 5b GVFK counts per region from the summary CSV."""
    summary_csv = BASE / "Resultater" / "workflow_summary" / "regional_summary_transposed.csv"
    reg_counts1, reg_counts2 = {}, {}
    try:
        sdf = pd.read_csv(summary_csv)
        gvfk_df = sdf[sdf["Metric"] == "GVFK"]
        row1 = gvfk_df[gvfk_df["Step"] == "Trin 1 (Alle)"].iloc[0]
        row5 = gvfk_df[gvfk_df["Step"] == "Trin 5b (Stof. Risiko)"].iloc[0]
        for r in REGION_COLORS:
            reg_counts1[r] = int(row1[r])
            reg_counts2[r] = int(row5[r])
    except Exception:
        pass
    return reg_counts1, reg_counts2


def _add_legend(fig, reg_counts1, reg_counts2):
    """Add the region colour legend to a figure."""
    handles = []
    for r, c in REGION_COLORS.items():
        if reg_counts1 and reg_counts2:
            label = f"{REGION_SHORT[r]}  ({reg_counts1[r]} / {reg_counts2[r]})"
        else:
            label = REGION_SHORT[r]
        handles.append(mpatches.Patch(facecolor=c, edgecolor="white", label=label))
    fig.legend(handles=handles, loc="lower center", ncol=5,
               bbox_to_anchor=(0.5, -0.02),
               fontsize=17, frameon=False,
               title="Region  (antal GVF: udgangspunkt / risiko)",
               title_fontsize=17)


def _load_map_data():
    """
    Load all spatial layers needed by the hex-overlay map variants.
    Returns a plain dict so callers can unpack what they need.
    """
    import geopandas as gpd
    from config import (
        GRUNDVAND_PATH, GRUNDVAND_LAYER_NAME,
        COLUMN_MAPPINGS, get_output_path, DATA_DIR,
    )

    gvfk_col = COLUMN_MAPPINGS["grundvand"]["gvfk_id"]

    print("\n[1/5] Regions...")
    regions = gpd.read_file(DATA_DIR / "regionsinddeling" / "regionsinddeling.shp")
    crs = regions.crs
    for col in ["Regionsnavn", "regionsnavn", "REGIONNAVN", "Navn", "navn"]:
        if col in regions.columns:
            regions = regions.rename(columns={col: "Region"})
            break
    regions = clip_bornholm(regions)[["Region", "geometry"]].copy()
    denmark = regions.dissolve()
    bounds  = denmark.total_bounds

    print("[2/5] All GVFKs from GDB (this may take ~1 min)...")
    all_gvfk = gpd.read_file(GRUNDVAND_PATH, layer=GRUNDVAND_LAYER_NAME)
    all_gvfk = all_gvfk.to_crs(crs)
    all_gvfk["geometry"] = all_gvfk.geometry.simplify(50, preserve_topology=True)
    total_gvfk_count = all_gvfk[gvfk_col].nunique()
    all_gvfk = clip_bornholm(all_gvfk)
    print("      Assigning regions...")
    all_gvfk = assign_regions(all_gvfk, regions, gvfk_col)

    print("[3/5] V1/V2 sites...")
    sites_gdf = gpd.read_file(get_output_path("step3_v1v2_sites")).to_crs(crs)
    sites_gdf = clip_bornholm(sites_gdf)
    print(f"      {len(sites_gdf):,} sites loaded.")

    print("[4/5] Trin 5b GVFKs...")
    p3_gdf = gpd.read_file(get_output_path("step3_gvfk_polygons")).to_crs(crs)
    p3_gdf["geometry"] = p3_gdf.geometry.simplify(50, preserve_topology=True)
    df5b  = pd.read_csv(get_output_path("step5b_compound_combinations"))
    ids5b = set(df5b["GVFK"])
    gdf5b = clip_bornholm(p3_gdf[p3_gdf[gvfk_col].isin(ids5b)].copy())
    gdf5b = assign_regions(gdf5b, regions, gvfk_col)

    return dict(
        regions=regions, denmark=denmark, bounds=bounds, crs=crs,
        all_gvfk=all_gvfk, total_gvfk_count=total_gvfk_count,
        sites_gdf=sites_gdf,
        gdf5b=gdf5b, ids5b=ids5b,
        gvfk_col=gvfk_col,
    )


def draw_hex_panel(ax, sites_gdf, regions, denmark, bounds,
                   badge_text, gridsize=38, cmap="Greys"):
    """Render a standalone hexbin site-density panel."""
    xmin, ymin, xmax, ymax = bounds
    px = (xmax - xmin) * 0.02
    py = (ymax - ymin) * 0.02

    denmark.plot(ax=ax, color="#FFFFFF", edgecolor="none")
    regions.boundary.plot(ax=ax, color="#333333", linewidth=0.4)
    denmark.boundary.plot(ax=ax, color="#111111", linewidth=0.8)

    centroids = sites_gdf.geometry.centroid
    xs = centroids.x.values
    ys = centroids.y.values
    ax.hexbin(xs, ys, gridsize=gridsize, cmap=cmap,
              mincnt=1, alpha=0.88, linewidths=0.15)

    ax.set_xlim(xmin - px, xmax + px)
    ax.set_ylim(ymin - py, ymax + py)
    ax.set_aspect("equal")
    ax.axis("off")

    ax.text(0.50, 0.01, badge_text,
            transform=ax.transAxes, ha="center", va="top", fontsize=17,
            bbox=dict(boxstyle="round,pad=0.5", facecolor="white",
                      edgecolor="#cccccc", alpha=0.92))


# ── New map variants ────────────────────────────────────────────────────────

def create_denmark_map_hexoverlay():
    """
    2-panel map — same layout as create_denmark_map() but panel 1
    also shows a hexbin density layer of the 34k V1/V2 sites.

    Output: Resultater/workflow_summary/report/report_denmark_map_hexoverlay.png
    """
    print("\n" + "=" * 55)
    print("REPORT MAP — Hex Overlay Variant")
    print("=" * 55)

    d = _load_map_data()
    regions = d["regions"]; denmark = d["denmark"]; bounds = d["bounds"]
    all_gvfk = d["all_gvfk"]; total_gvfk_count = d["total_gvfk_count"]
    sites_gdf = d["sites_gdf"]
    gdf5b = d["gdf5b"]; ids5b = d["ids5b"]

    xmin, ymin, xmax, ymax = bounds
    px = (xmax - xmin) * 0.02
    py = (ymax - ymin) * 0.02

    print("\n[5/5] Drawing...")
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(17, 10))
    fig.subplots_adjust(wspace=0.05)

    # Panel 1 — GVFKs (lower alpha to let hex show through) + hex overlay
    draw_panel(
        ax1, all_gvfk, regions, denmark, bounds,
        alpha_poly=0.25,
        edge_color="white",
        edge_width=0.10,
        badge_text=f"Alle {total_gvfk_count:,} GVF + lokalitetstæthed (V1/V2)",
    )
    centroids = sites_gdf.geometry.centroid
    xs = centroids.x.values
    ys = centroids.y.values
    ax1.hexbin(xs, ys, gridsize=38, cmap="Greys",
               mincnt=1, alpha=0.75, linewidths=0.15)
    # Reset limits — hexbin can silently expand them
    ax1.set_xlim(xmin - px, xmax + px)
    ax1.set_ylim(ymin - py, ymax + py)

    # Panel 2 — Trin 5b
    draw_panel(
        ax2, gdf5b, regions, denmark, bounds,
        alpha_poly=1.0,
        edge_color="white",
        edge_width=0.5,
        badge_text=f"{len(ids5b)} GVF med stofspecifik risiko",
    )

    reg_counts1, reg_counts2 = _load_region_counts()
    _add_legend(fig, reg_counts1, reg_counts2)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUT_DIR / "report_denmark_map_hexoverlay.png"
    plt.savefig(out)
    plt.close()
    print(f"\n  Saved: {out}")


def create_denmark_map_3panel():
    """
    3-panel landscape map.

      Panel 1 — All 2,049 GVFKs colored by region (starting point).
      Panel 2 — Hexbin density of the 34k V1/V2 contamination sites.
      Panel 3 — 187 Trin 5b risk GVFKs colored by region (result).

    Output: Resultater/workflow_summary/report/report_denmark_map_3panel.png
    """
    print("\n" + "=" * 55)
    print("REPORT MAP — 3-Panel Variant")
    print("=" * 55)

    d = _load_map_data()
    regions = d["regions"]; denmark = d["denmark"]; bounds = d["bounds"]
    all_gvfk = d["all_gvfk"]; total_gvfk_count = d["total_gvfk_count"]
    sites_gdf = d["sites_gdf"]
    gdf5b = d["gdf5b"]; ids5b = d["ids5b"]

    print("\n[5/5] Drawing...")
    fig, (ax1, ax2, ax3) = plt.subplots(1, 3, figsize=(25, 10))
    fig.subplots_adjust(wspace=0.04)

    draw_panel(
        ax1, all_gvfk, regions, denmark, bounds,
        alpha_poly=0.40,
        edge_color="white",
        edge_width=0.10,
        badge_text=f"Alle {total_gvfk_count:,} GVF (udgangspunkt)",
    )

    draw_hex_panel(
        ax2, sites_gdf, regions, denmark, bounds,
        badge_text=f"{len(sites_gdf):,} V1/V2 lokaliteter — tæthed",
        gridsize=38,
        cmap="Greys",
    )

    draw_panel(
        ax3, gdf5b, regions, denmark, bounds,
        alpha_poly=1.0,
        edge_color="white",
        edge_width=0.5,
        badge_text=f"{len(ids5b)} GVF med stofspecifik risiko",
    )

    reg_counts1, reg_counts2 = _load_region_counts()
    _add_legend(fig, reg_counts1, reg_counts2)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUT_DIR / "report_denmark_map_3panel.png"
    plt.savefig(out)
    plt.close()
    print(f"\n  Saved: {out}")


def create_denmark_map_step6():
    """
    Single-panel map: Step 6 GVFKs (Q95) colored by region.

    Intended for the Step 6 report section. The reader can refer to the
    two-panel maps for the full Denmark context.

    Output: Resultater/workflow_summary/report/report_denmark_map_step6.png
    """
    import geopandas as gpd
    from config import (
        COLUMN_MAPPINGS, get_output_path, DATA_DIR,
    )

    print("\n" + "=" * 55)
    print("REPORT MAP — Step 6 (Tilstandsvurdering)")
    print("=" * 55)

    gvfk_col = COLUMN_MAPPINGS["grundvand"]["gvfk_id"]

    # Regions
    print("\n[1/3] Regions...")
    regions = gpd.read_file(DATA_DIR / "regionsinddeling" / "regionsinddeling.shp")
    crs = regions.crs
    for col in ["Regionsnavn", "regionsnavn", "REGIONNAVN", "Navn", "navn"]:
        if col in regions.columns:
            regions = regions.rename(columns={col: "Region"})
            break
    regions = clip_bornholm(regions)[["Region", "geometry"]].copy()
    denmark = regions.dissolve()
    bounds  = denmark.total_bounds

    # Step 6 GVFK polygons (Q95, robust fallback to site exceedance file)
    print("[2/3] Step 6 GVFKs...")
    p3_gdf = gpd.read_file(get_output_path("step3_gvfk_polygons")).to_crs(crs)
    p3_gdf["geometry"] = p3_gdf.geometry.simplify(50, preserve_topology=True)
    site_q95 = _load_step6_q95(get_output_path)
    ids6 = set(site_q95["GVFK"].dropna().astype(str))
    p3_gdf[gvfk_col] = p3_gdf[gvfk_col].astype(str)
    gdf6  = clip_bornholm(p3_gdf[p3_gdf[gvfk_col].isin(ids6)].copy())
    print(f"      {len(ids6)} GVFKs in Step 6.")

    print("      Assigning regions...")
    gdf6 = assign_regions(gdf6, regions, gvfk_col)
    print(f"      Region distribution:\n{gdf6['Region'].value_counts().to_string()}")

    # Draw single panel
    print("\n[3/3] Drawing...")
    fig, ax = plt.subplots(1, 1, figsize=(11, 13))
    fig.subplots_adjust(bottom=0.12)

    draw_panel(
        ax, gdf6, regions, denmark, bounds,
        alpha_poly=1.0,
        edge_color="white",
        edge_width=0.5,
        badge_text=f"{len(ids6)} GVF – Tilstandsvurdering",
    )

    # Legend with Trin 6 counts per region
    summary_csv = BASE / "Resultater" / "workflow_summary" / "regional_summary_transposed.csv"
    handles = []
    try:
        sdf = pd.read_csv(summary_csv)
        for r, c in REGION_COLORS.items():
            count = int((gdf6["Region"] == r).sum())
            label = f"{REGION_SHORT[r]}  ({count})"
            handles.append(mpatches.Patch(facecolor=c, edgecolor="white", label=label))
    except Exception:
        for r, c in REGION_COLORS.items():
            handles.append(mpatches.Patch(facecolor=c, edgecolor="white",
                                          label=REGION_SHORT[r]))

    fig.legend(handles=handles, loc="lower center", ncol=5,
               bbox_to_anchor=(0.5, 0.01),
               fontsize=17, frameon=False,
               title="Region  (antal GVF)",
               title_fontsize=17)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUT_DIR / "report_denmark_map_step6.png"
    plt.savefig(out)
    plt.close()
    print(f"\n  Saved: {out}")


def create_denmark_map_step6_3panel():
    """
    Step 6 (Q95) three-panel Denmark map:
      1) Affected GVF by region
      2) Contributing V1/V2 sites as points
      3) River network with affected segments highlighted

    Output: Resultater/workflow_summary/report/report_denmark_map_step6_3panel.png
    """
    import geopandas as gpd
    from config import (
        COLUMN_MAPPINGS,
        DATA_DIR,
        RIVERS_LAYER_NAME,
        RIVERS_PATH,
        get_output_path,
    )

    print("\n" + "=" * 55)
    print("REPORT MAP — Step 6 (Q95) 3-Panel")
    print("=" * 55)

    gvfk_col = COLUMN_MAPPINGS["grundvand"]["gvfk_id"]

    print("\n[1/4] Regions...")
    regions = gpd.read_file(DATA_DIR / "regionsinddeling" / "regionsinddeling.shp")
    crs = regions.crs
    for col in ["Regionsnavn", "regionsnavn", "REGIONNAVN", "Navn", "navn"]:
        if col in regions.columns:
            regions = regions.rename(columns={col: "Region"})
            break
    regions = clip_bornholm(regions)[["Region", "geometry"]].copy()
    denmark = regions.dissolve()
    bounds = denmark.total_bounds

    print("[2/4] Step 6 Q95 data...")
    step6 = _load_step6_q95(get_output_path)
    if step6.empty:
        print("      No Step 6 rows found. Skipping 3-panel map.")
        return

    # IDs from Step 6 (Q95)
    gvfk_ids = set(step6["GVFK"].dropna().astype(str))
    site_ids = set(step6["Lokalitet_ID"].dropna().astype(str))
    ov_ids = set(step6["Nearest_River_ov_id"].dropna().astype(str))

    step6_seg = pd.to_numeric(step6.get("Nearest_River_FID"), errors="coerce")
    seg_ids = set(step6_seg.dropna().astype(int))

    print("[3/4] Loading geometries...")
    # Panel 1: GVF
    gvf = gpd.read_file(get_output_path("step3_gvfk_polygons")).to_crs(crs)
    gvf[gvfk_col] = gvf[gvfk_col].astype(str)
    gdf6 = gvf[gvf[gvfk_col].isin(gvfk_ids)].copy()
    gdf6["geometry"] = gdf6.geometry.simplify(50, preserve_topology=True)
    gdf6 = clip_bornholm(gdf6)
    gdf6 = assign_regions(gdf6, regions, gvfk_col)

    # Panel 2: V1/V2 polygons as points
    sites = gpd.read_file(get_output_path("step3_v1v2_sites")).to_crs(crs)
    site_id_col = _pick_existing_column(
        sites.columns, ["Lokalitet_", "Lokalitetsnr", "site_id", "Lokalitet_ID"]
    )
    if site_id_col is None:
        raise KeyError("Could not find a site ID column in step3_v1v2_sites.")
    sites["_site_id"] = sites[site_id_col].astype(str)
    sites6 = sites[sites["_site_id"].isin(site_ids)].copy()
    site_points = sites6.copy()
    site_points["geometry"] = site_points.geometry.centroid
    site_points = clip_bornholm(site_points)

    # Panel 3: River network + affected segments
    rivers = gpd.read_file(RIVERS_PATH, layer=RIVERS_LAYER_NAME).to_crs(crs)
    rivers = clip_bornholm(rivers)
    river_ov_col = _pick_existing_column(rivers.columns, ["ov_id", "OV_ID", "river_id"])
    if river_ov_col is None:
        raise KeyError("Could not find river ov_id column in river layer.")
    river_seg_col = _pick_existing_column(rivers.columns, ["River_FID", "FID", "fid"])

    rivers["_ov_id"] = rivers[river_ov_col].astype(str)
    if river_seg_col is not None:
        rivers["_seg_id"] = pd.to_numeric(rivers[river_seg_col], errors="coerce")
        affected_rivers = rivers[
            rivers["_ov_id"].isin(ov_ids) | rivers["_seg_id"].isin(seg_ids)
        ].copy()
    else:
        affected_rivers = rivers[rivers["_ov_id"].isin(ov_ids)].copy()

    print("\n[4/4] Drawing...")
    fig, (ax1, ax2, ax3) = plt.subplots(1, 3, figsize=(25, 10))
    fig.subplots_adjust(wspace=0.04)

    # Shared base
    xmin, ymin, xmax, ymax = bounds
    px = (xmax - xmin) * 0.02
    py = (ymax - ymin) * 0.02

    for ax in (ax1, ax2, ax3):
        denmark.plot(ax=ax, color="#FFFFFF", edgecolor="none")
        regions.boundary.plot(ax=ax, color="#333333", linewidth=0.4)
        denmark.boundary.plot(ax=ax, color="#111111", linewidth=0.8)
        ax.set_xlim(xmin - px, xmax + px)
        ax.set_ylim(ymin - py, ymax + py)
        ax.set_aspect("equal")
        ax.axis("off")

    # Panel 1: GVF by region
    for region, color in REGION_COLORS.items():
        subset = gdf6[gdf6["Region"] == region]
        if len(subset):
            subset.plot(
                ax=ax1, color=color, alpha=1.0, edgecolor="white", linewidth=0.4
            )
    ax1.text(
        0.50, 0.01, f"{len(gvfk_ids)} påvirkede GVF (Q95)",
        transform=ax1.transAxes, ha="center", va="top", fontsize=14,
        bbox=dict(boxstyle="round,pad=0.45", facecolor="white", edgecolor="#cccccc", alpha=0.92),
    )

    # Panel 2: Step 6 sites as points, colored by region
    site_points = assign_regions(site_points, regions, "_site_id")
    for region, color in REGION_COLORS.items():
        subset = site_points[site_points["Region"] == region]
        if len(subset):
            subset.plot(
                ax=ax2, color=color, markersize=18, alpha=0.85, linewidth=0.3,
                edgecolor="white"
            )
    ax2.text(
        0.50, 0.01, f"{len(site_ids):,} bidragende lokaliteter (Q95)",
        transform=ax2.transAxes, ha="center", va="top", fontsize=14,
        bbox=dict(boxstyle="round,pad=0.45", facecolor="white", edgecolor="#cccccc", alpha=0.92),
    )

    # Panel 3: Rivers
    rivers.plot(ax=ax3, color="#d0d0d0", linewidth=0.15, alpha=0.7)
    if not affected_rivers.empty:
        affected_rivers.plot(ax=ax3, color="#cc1f1a", linewidth=1.2, alpha=1.0)
    ax3.text(
        0.50, 0.01, f"{len(ov_ids):,} berørte vandløb (Q95)",
        transform=ax3.transAxes, ha="center", va="top", fontsize=14,
        bbox=dict(boxstyle="round,pad=0.45", facecolor="white", edgecolor="#cccccc", alpha=0.92),
    )

    # Region legend (panel 1 reference)
    handles = [
        mpatches.Patch(facecolor=c, edgecolor="white", label=REGION_SHORT[r])
        for r, c in REGION_COLORS.items()
    ]
    fig.legend(
        handles=handles,
        loc="lower center",
        ncol=5,
        bbox_to_anchor=(0.5, -0.04),
        fontsize=14,
        frameon=True,
        facecolor="white",
        edgecolor="#cccccc",
        title="Region",
        title_fontsize=14,
    )

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUT_DIR / "report_denmark_map_step6_3panel.png"
    plt.savefig(out)
    plt.close()
    print(f"\n  Saved: {out}")


if __name__ == "__main__":
    create_denmark_map()
    #create_denmark_map_hexoverlay()
    #create_denmark_map_3panel()
    create_denmark_map_step6()
    create_denmark_map_step6_3panel()
