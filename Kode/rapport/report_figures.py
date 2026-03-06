"""
Report Figures
==============

Creates publication-quality figures for the non-technical report:

  1. Stacked bar charts  — GVFK Area (km²) and Volume (km³) broken down by region
                           across all risikovurdering steps (Trin 1 → 5b)

  2. Count table figure  — GVFK count and Site count by step × region,
                           rendered as a clean image for easy insertion in Word

  3. Paired absolute + normalized charts (grayscale)

  4. Step 6 figures      — Trin 6 only (bars + table)

Reads from:
  Resultater/workflow_summary/regional_summary_transposed.csv

Output (Resultater/workflow_summary/report/):
  report_area_volume_stacked_*.png
  report_area_volume_paired.png
  report_count_table.png / .xlsx
  report_step6_regional_metrics.png / .xlsx

Run from the Kode/ directory:
  python report_figures.py
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from pathlib import Path

# ── Paths ─────────────────────────────────────────────────────────────────────
BASE      = Path(__file__).parent.parent
DATA_FILE = BASE / "Resultater" / "workflow_summary" / "regional_summary_transposed.csv"
OUT_DIR   = BASE / "Resultater" / "workflow_summary" / "report"

# ── Steps (Trin 6 excluded — separate section in report) ──────────────────────
STEPS = [
    "Trin 1 (Alle)",
    "Trin 2 (Kontakt)",
    "Trin 3 (V1/V2)",
    "Trin 3b (Infilter)",
    "Trin 5a (Gen. Risiko)",
    "Trin 5b (Stof. Risiko)",
]

# X-axis labels on bar charts
STEP_LABELS_CHART = [
    "ALLE\nGVF",
    "VANDLØBS-\nKONTAKT",
    "V1/V2\nLOKALITETER",
    "INFILTRATIONS-\nFILTER",
    "GENEREL RISIKO\n≤ 500 M",
    "STOFSPECIFIK\nRISIKO",
]

# Row labels in the table
STEP_LABELS_TABLE = [
    "Trin 1 – Alle GVF",
    "Trin 2 – Vandløbskontakt",
    "Trin 3 – V1/V2 lokaliteter",
    "Trin 3b – Infiltrationsfilter",
    "Trin 5a – Generel risiko (≤500 m)",
    "Trin 5b – Stofspecifik risiko",
]

# ── Step 6 labels ──────────────────────────────────────────────────────────────
STEPS_6 = ["Trin 6 (Tilstand)"]
STEP_LABELS_6_CHART = [
    "TILSTANDS-\nVURDERING",
]
STEP_LABELS_6_TABLE = [
    "Trin 6 – Tilstandsvurdering",
]

REGIONS = [
    "Region Hovedstaden",
    "Region Midtjylland",
    "Region Nordjylland",
    "Region Sjælland",
    "Region Syddanmark",
]

# Clean names used in legend and table headers (no hyphens, no line breaks)
REGION_LABELS = [
    "Hovedstaden",
    "Midtjylland",
    "Nordjylland",
    "Sjælland",
    "Syddanmark",
]

# ── Color schemes ──────────────────────────────────────────────────────────────

# Option A: ColorBrewer Set2 — muted, academic-standard, print-safe
SCHEME_A = dict(
    colors  = ["#66C2A5", "#FC8D62", "#8DA0CB", "#E78AC3", "#A6D854"],
    hatches = [None] * 5,
    suffix  = "A_set2",
    edge    = "white",
)

# Option C: Grayscale — formal, prints perfectly in B&W, shades alone are sufficient
SCHEME_C = dict(
    colors  = ["#1a1a1a", "#555555", "#888888", "#aaaaaa", "#d4d4d4"],
    hatches = [None] * 5,
    suffix  = "C_grayscale",
    edge    = "white",
)

# Grayscale colors reused in the paired chart and step 6
GRAY5 = ["#1a1a1a", "#555555", "#888888", "#aaaaaa", "#d4d4d4"]

# ── Global style ───────────────────────────────────────────────────────────────
plt.rcParams.update({
    "font.family":       ["Arial", "DejaVu Sans", "sans-serif"],
    "font.size":          16,
    "axes.titlesize":     18,
    "axes.labelsize":     18,
    "xtick.labelsize":    17,
    "ytick.labelsize":    16,
    "figure.facecolor":  "white",
    "axes.facecolor":    "white",
    "savefig.dpi":        300,
    "savefig.bbox":      "tight",
    "savefig.facecolor": "white",
})


# ── Helpers ────────────────────────────────────────────────────────────────────
def get_metric(df: pd.DataFrame, metric: str) -> pd.DataFrame:
    """Return a step × region DataFrame for one metric (steps in STEPS order)."""
    mask = (df["Metric"] == metric) & (df["Step"].isin(STEPS))
    return df[mask].set_index("Step")[REGIONS].reindex(STEPS)


def _get_metric_6(df: pd.DataFrame, metric: str) -> pd.DataFrame:
    """Step × region DataFrame restricted to Trin 6."""
    mask = (df["Metric"] == metric) & (df["Step"].isin(STEPS_6))
    return df[mask].set_index("Step")[REGIONS].reindex(STEPS_6)


# ══════════════════════════════════════════════════════════════════════════════
# 1.  STACKED BAR CHARTS  ── Area (km²) and Volume (km³)
# ══════════════════════════════════════════════════════════════════════════════
def create_stacked_bar_charts(df: pd.DataFrame, out_dir: Path, scheme: dict) -> None:
    """
    Landscape figure: two stacked bar charts (Area + Volume) side by side.
    Bars stacked by region. Total + % of Trin 1 shown above each bar.
    No titles. Large fonts.

    scheme: one of SCHEME_A or SCHEME_C defined at module level.
    """
    colors  = scheme["colors"]
    hatches = scheme["hatches"]
    suffix  = scheme["suffix"]
    edge    = scheme["edge"]

    metrics = [
        ("Areal (km2)",   "Samlet grundvandsareal (km²)"),
        ("Volumen (km3)", "Samlet grundvandsvolumen (km³)"),
    ]

    fig, axes = plt.subplots(1, 2, figsize=(24, 12))
    x = np.arange(len(STEPS))
    bar_width = 0.62

    for ax, (metric, ylabel) in zip(axes, metrics):
        data    = get_metric(df, metric)
        totals  = data.sum(axis=1).values
        t1      = totals[0]
        bottoms = np.zeros(len(STEPS))

        for region, color, hatch, label in zip(REGIONS, colors, hatches, REGION_LABELS):
            values = data[region].values
            ax.bar(x, values, bottom=bottoms, color=color,
                   hatch=hatch, width=bar_width,
                   edgecolor=edge, linewidth=1.0, label=label)
            bottoms += values

        # Label above each bar: total (bold) + % of Trin 1
        for xi, total in enumerate(totals):
            pct    = total / t1 * 100 if t1 > 0 else 0
            offset = totals.max() * 0.025

            ax.text(xi, total + offset,
                    f"{total:,.0f}",
                    ha="center", va="bottom",
                    fontsize=20, fontweight="bold", color="#111111")

            pct_label = "100 %" if xi == 0 else f"{pct:.0f} %"
            ax.text(xi, total + offset * 4.2,
                    pct_label,
                    ha="center", va="bottom",
                    fontsize=17, color="#444444")

        ax.set_xticks(x)
        ax.set_xticklabels(STEP_LABELS_CHART, fontsize=14, linespacing=1.3,
                           rotation=20, ha="right")
        ax.set_ylabel(ylabel, fontsize=19, fontweight="bold", labelpad=12)
        ax.set_ylim(0, totals.max() * 1.38)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.yaxis.grid(True, linestyle="--", linewidth=0.5, alpha=0.5, color="#bbbbbb")
        ax.set_axisbelow(True)

    # Shared legend
    handles = [
        mpatches.Patch(facecolor=c, hatch=h, edgecolor="white" if h is None else "#555555",
                       label=l)
        for c, h, l in zip(colors, hatches, REGION_LABELS)
    ]
    fig.legend(handles=handles,
               loc="lower center", ncol=5,
               bbox_to_anchor=(0.5, -0.03),
               fontsize=22, frameon=False)

    plt.tight_layout(rect=[0, 0.15, 1, 1])
    out = out_dir / f"report_area_volume_stacked_{suffix}.png"
    plt.savefig(out)
    plt.close()
    print(f"  Saved: {out.name}")


# ══════════════════════════════════════════════════════════════════════════════
# 2.  COUNT TABLE  ── GVFK count + Sites count  (image + Excel)
# ══════════════════════════════════════════════════════════════════════════════
def create_count_table(df: pd.DataFrame, out_dir: Path) -> None:
    """
    Formatted table:
      Section A – antal GVFK        (all 6 steps)
      Section B – antal lokaliteter (steps 3, 3b, 5a, 5b only)

    Total column shows absolute number + % of baseline in parentheses.
    Saves PNG + Excel.
    """
    gvfk  = get_metric(df, "GVFK")
    sites = get_metric(df, "Sites")

    def get_totals(metric):
        mask = (df["Metric"] == metric) & (df["Step"].isin(STEPS))
        return df[mask].set_index("Step")["Total"].reindex(STEPS)

    gvfk_total  = get_totals("GVFK")
    sites_total = get_totals("Sites")

    col_names = REGION_LABELS + ["Total"]

    def fmt_num(v):
        return f"{int(v):,}".replace(",", ".") if pd.notna(v) and v > 0 else "-"

    def make_section(data, totals, baseline_val, step_list, label_list):
        """Return list of (row_label, [cell strings]) with % in Total column."""
        rows = []
        for step, row_label in zip(step_list, label_list):
            cells = [fmt_num(data.loc[step, r]) for r in REGIONS]
            total = totals.loc[step]
            if total <= 0:
                cells.append("-")
            else:
                pct = total / baseline_val * 100 if baseline_val > 0 else 0
                if abs(pct - 100) < 0.5:
                    cells.append(fmt_num(total))
                else:
                    cells.append(f"{fmt_num(total)}\n({pct:.0f} %)")
            rows.append((row_label, cells))
        return rows

    gvfk_baseline  = gvfk_total.iloc[0]
    sites_nonzero  = sites_total[sites_total > 0]
    sites_baseline = sites_nonzero.iloc[0] if not sites_nonzero.empty else 1

    gvfk_rows  = make_section(gvfk,  gvfk_total,  gvfk_baseline,
                               STEPS, STEP_LABELS_TABLE)
    sites_rows = [(lbl, cells) for lbl, cells in
                  make_section(sites, sites_total, sites_baseline,
                                STEPS, STEP_LABELS_TABLE)
                  if any(c != "-" for c in cells)]

    _save_table_png(gvfk_rows, sites_rows, col_names, out_dir)
    _save_table_excel(gvfk_rows, sites_rows, col_names, out_dir)


def _save_table_png(gvfk_rows, sites_rows, col_names, out_dir,
                    out_name="report_count_table.png"):
    """Render count table as a polished matplotlib figure."""
    n_cols    = len(col_names)
    n_total   = 1 + 1 + len(gvfk_rows) + 1 + len(sites_rows)

    ROW_H     = 0.058
    fig_h     = max(7, n_total * ROW_H * 14 + 1.0)
    fig, ax   = plt.subplots(figsize=(17, fig_h))
    ax.axis("off")

    # ── Colours ──────────────────────────────────────────────────────────────
    HDR_BG    = "#1B2A3B"
    HDR_FG    = "white"
    SEC_BG    = "#4A6FA5"
    SEC_FG    = "white"
    ROW_A     = "#FFFFFF"
    ROW_B     = "#EEF3FA"
    TOT_BG    = "#D9E2F0"
    BORDER    = "#C0C8D8"

    # ── Column layout (fractions of figure width) ─────────────────────────────
    left_margin = 0.03
    step_w      = 0.29
    data_w      = 0.10
    total_w     = 0.11
    col_xs      = [left_margin + step_w + i * data_w for i in range(n_cols - 1)]
    col_xs.append(left_margin + step_w + (n_cols - 1) * data_w)
    col_ws      = [data_w] * (n_cols - 1) + [total_w]

    def draw_cell(ax, x, y, w, h, text, bg, fg, bold=False, size=11, align="center"):
        ax.add_patch(plt.Rectangle(
            (x, y), w, h, transform=ax.transAxes,
            facecolor=bg, edgecolor=BORDER, linewidth=0.6, clip_on=False
        ))
        ha = "left" if align == "left" else "center"
        xpos = x + 0.008 if align == "left" else x + w / 2
        lines = text.split("\n")
        if len(lines) == 1:
            ax.text(xpos, y + h / 2, text, transform=ax.transAxes,
                    ha=ha, va="center", fontsize=size, color=fg,
                    fontweight="bold" if bold else "normal")
        else:
            ax.text(xpos, y + h * 0.62, lines[0], transform=ax.transAxes,
                    ha=ha, va="center", fontsize=size, color=fg,
                    fontweight="bold" if bold else "normal")
            ax.text(xpos, y + h * 0.28, lines[1], transform=ax.transAxes,
                    ha=ha, va="center", fontsize=size - 1.5, color="#555555")

    def draw_row(y, step_label, cells, bg, row_h=ROW_H):
        ax.add_patch(plt.Rectangle(
            (left_margin, y), step_w, row_h, transform=ax.transAxes,
            facecolor=bg, edgecolor=BORDER, linewidth=0.6, clip_on=False
        ))
        ax.text(left_margin + 0.008, y + row_h / 2, step_label,
                transform=ax.transAxes, ha="left", va="center",
                fontsize=11, color="#111111")
        for i, (cx, cw, cell) in enumerate(zip(col_xs, col_ws, cells)):
            is_total = (i == n_cols - 1)
            cell_bg  = TOT_BG if is_total else bg
            draw_cell(ax, cx, y, cw, row_h, cell, cell_bg,
                      "#111111", bold=is_total, size=11)

    y = 0.97 - ROW_H

    def draw_section(section_label, data_rows):
        nonlocal y
        full_w = step_w + sum(col_ws)
        ax.add_patch(plt.Rectangle(
            (left_margin, y), full_w, ROW_H, transform=ax.transAxes,
            facecolor=SEC_BG, edgecolor=BORDER, linewidth=0.6, clip_on=False
        ))
        ax.text(left_margin + 0.008, y + ROW_H / 2, section_label,
                transform=ax.transAxes, ha="left", va="center",
                fontsize=12, color=SEC_FG, fontweight="bold")
        y -= ROW_H

        for i, (step_lbl, cells) in enumerate(data_rows):
            bg = ROW_A if i % 2 == 0 else ROW_B
            draw_row(y, step_lbl, cells, bg)
            y -= ROW_H

        y -= ROW_H * 0.35

    # Column header row
    ax.add_patch(plt.Rectangle(
        (left_margin, y), step_w, ROW_H, transform=ax.transAxes,
        facecolor=HDR_BG, edgecolor=BORDER, linewidth=0.6, clip_on=False
    ))
    ax.text(left_margin + 0.008, y + ROW_H / 2, "",
            transform=ax.transAxes, ha="left", va="center",
            fontsize=11, color=HDR_FG, fontweight="bold")
    for cx, cw, label in zip(col_xs, col_ws, col_names):
        draw_cell(ax, cx, y, cw, ROW_H, label, HDR_BG, HDR_FG, bold=True, size=11)
    y -= ROW_H

    draw_section("Antal GVF", gvfk_rows)
    draw_section("Antal lokaliteter", sites_rows)

    out = out_dir / out_name
    plt.savefig(out, dpi=200)
    plt.close()
    print(f"  Saved: {out.name}")


def _save_table_excel(gvfk_rows, sites_rows, col_names, out_dir,
                      out_name="report_count_table.xlsx"):
    """Write a formatted Excel workbook for paste-into-Word use."""
    out = out_dir / out_name
    try:
        with pd.ExcelWriter(out, engine="xlsxwriter") as writer:
            wb = writer.book
            ws = wb.add_worksheet("Tabel")
            writer.sheets["Tabel"] = ws

            def fmt(**kw):
                base = {"border": 1, "font_size": 10, "valign": "vcenter"}
                base.update(kw)
                return wb.add_format(base)

            hdr  = fmt(bold=True, bg_color="#1B2A3B", font_color="white",  align="center")
            sec  = fmt(bold=True, bg_color="#4A6FA5", font_color="white",  align="left")
            step = fmt(align="left",   font_size=10)
            num  = fmt(align="center", font_size=10)
            numa = fmt(align="center", font_size=10, bg_color="#EEF3FA")
            tot  = fmt(align="center", font_size=10, bold=True, bg_color="#D9E2F0")

            ws.set_column(0, 0, 34)
            ws.set_column(1, len(col_names) - 1, 14)
            ws.set_column(len(col_names), len(col_names), 14)

            row = 0
            ws.set_row(row, 22)
            ws.write(row, 0, "", hdr)
            for c, name in enumerate(col_names, 1):
                ws.write(row, c, name, hdr)
            row += 1

            def write_section(label, data_rows):
                nonlocal row
                ws.set_row(row, 18)
                ws.merge_range(row, 0, row, len(col_names), label, sec)
                row += 1
                for i, (step_lbl, cells) in enumerate(data_rows):
                    ws.set_row(row, 20)
                    ws.write(row, 0, step_lbl, step)
                    alt = i % 2 == 1
                    for c, val in enumerate(cells, 1):
                        is_total = (c == len(col_names))
                        f = tot if is_total else (numa if alt else num)
                        ws.write(row, c, val, f)
                    row += 1
                row += 1

            write_section("Antal GVF", gvfk_rows)
            write_section("Antal lokaliteter", sites_rows)

        print(f"  Saved: {out.name}")
    except Exception as e:
        print(f"  Could not save Excel: {e}")


# X-axis labels for the paired chart (same style, slightly condensed)
_STEP_LABELS_PAIRED = [
    "ALLE\nGVF",
    "VANDLØBS-\nKONTAKT",
    "V1/V2\nLOKALITETER",
    "INFILTRATIONS-\nFILTER",
    "GENEREL RISIKO\n≤ 500 M",
    "STOFSPECIFIK\nRISIKO",
]


# ══════════════════════════════════════════════════════════════════════════════
# 3.  PAIRED CHART  ── Absolute + Normalized (100%) side by side, 2×2 grid
# ══════════════════════════════════════════════════════════════════════════════
def create_paired_normalized_charts(df: pd.DataFrame, out_dir: Path) -> None:
    """
    2×2 landscape figure (very large canvas — intended for a full landscape page):
      Left column  — absolute stacked bars (grayscale, no hatching)
      Right column — 100% normalized stacked bars showing regional composition
    """
    metrics = [
        ("Areal (km2)",   "Samlet grundvandsareal (km²)",    "Andel af samlet areal (%)"),
        ("Volumen (km3)", "Samlet grundvandsvolumen (km³)",  "Andel af samlet volumen (%)"),
    ]

    # Large canvas so each of the four subplots gets real estate
    fig, axes = plt.subplots(2, 2, figsize=(34, 24))
    fig.subplots_adjust(left=0.07, right=0.97, top=0.97,
                        bottom=0.17, hspace=0.25, wspace=0.18)

    x          = np.arange(len(STEPS))
    bar_width  = 0.64
    txt_colors = ["white", "white", "#111111", "#111111", "#111111"]

    FS_TICK   = 26   # x / y tick labels
    FS_LABEL  = 28   # axis labels (ylabel)
    FS_TOTAL  = 30   # bold total above bar
    FS_PCT    = 25   # % of Trin 1 above bar
    FS_IN     = 21   # % inside bar segment
    FS_LEGEND = 32

    for row_idx, (metric, abs_ylabel, norm_ylabel) in enumerate(metrics):
        ax_abs  = axes[row_idx, 0]
        ax_norm = axes[row_idx, 1]

        data    = get_metric(df, metric)
        totals  = data.sum(axis=1).values
        t1      = totals[0]

        # ── Left: absolute ────────────────────────────────────────────────────
        bottoms = np.zeros(len(STEPS))
        for region, color, label in zip(REGIONS, GRAY5, REGION_LABELS):
            values = data[region].values
            ax_abs.bar(x, values, bottom=bottoms, color=color,
                       width=bar_width, edgecolor="white", linewidth=1.2, label=label)
            bottoms += values

        for xi, total in enumerate(totals):
            pct    = total / t1 * 100 if t1 > 0 else 0
            offset = totals.max() * 0.025
            ax_abs.text(xi, total + offset,
                        f"{total:,.0f}",
                        ha="center", va="bottom",
                        fontsize=FS_TOTAL, fontweight="bold", color="#111111")
            pct_lbl = "100 %" if xi == 0 else f"{pct:.0f} %"
            ax_abs.text(xi, total + offset * 4.5,
                        pct_lbl,
                        ha="center", va="bottom",
                        fontsize=FS_PCT, color="#555555")

        ax_abs.set_xticks(x)
        ax_abs.set_xticklabels(_STEP_LABELS_PAIRED, fontsize=21, linespacing=1.25,
                               rotation=20, ha="right")
        ax_abs.set_ylabel(abs_ylabel, fontsize=FS_LABEL, fontweight="bold", labelpad=14)
        ax_abs.tick_params(axis="y", labelsize=FS_TICK)
        ax_abs.set_ylim(0, totals.max() * 1.45)
        ax_abs.spines["top"].set_visible(False)
        ax_abs.spines["right"].set_visible(False)
        ax_abs.yaxis.grid(True, linestyle="--", linewidth=0.6, alpha=0.45, color="#bbbbbb")
        ax_abs.set_axisbelow(True)

        # ── Right: normalized (100%) ──────────────────────────────────────────
        norm_data = data.div(data.sum(axis=1), axis=0) * 100

        bottoms = np.zeros(len(STEPS))
        for region, color, tc in zip(REGIONS, GRAY5, txt_colors):
            values = norm_data[region].values
            ax_norm.bar(x, values, bottom=bottoms, color=color,
                        width=bar_width, edgecolor="white", linewidth=1.2)

            for xi, (val, bot) in enumerate(zip(values, bottoms)):
                if val >= 7:
                    ax_norm.text(xi, bot + val / 2,
                                 f"{val:.0f} %",
                                 ha="center", va="center",
                                 fontsize=FS_IN, fontweight="bold", color=tc)
            bottoms += values

        ax_norm.set_xticks(x)
        ax_norm.set_xticklabels(_STEP_LABELS_PAIRED, fontsize=21, linespacing=1.25,
                                rotation=20, ha="right")
        ax_norm.set_ylabel(norm_ylabel, fontsize=FS_LABEL, fontweight="bold", labelpad=14)
        ax_norm.set_ylim(0, 108)
        ax_norm.set_yticks([0, 25, 50, 75, 100])
        ax_norm.set_yticklabels(["0 %", "25 %", "50 %", "75 %", "100 %"],
                                 fontsize=FS_TICK)
        ax_norm.spines["top"].set_visible(False)
        ax_norm.spines["right"].set_visible(False)
        ax_norm.yaxis.grid(True, linestyle="--", linewidth=0.6, alpha=0.45, color="#bbbbbb")
        ax_norm.set_axisbelow(True)

    handles = [mpatches.Patch(facecolor=c, edgecolor="white", label=l)
               for c, l in zip(GRAY5, REGION_LABELS)]
    fig.legend(handles=handles, loc="lower center", ncol=5,
               bbox_to_anchor=(0.5, 0.01),
               fontsize=FS_LEGEND, frameon=False)

    out = out_dir / "report_area_volume_paired.png"
    plt.savefig(out)
    plt.close()
    print(f"  Saved: {out.name}")


# ══════════════════════════════════════════════════════════════════════════════
# 4.  STEP 6 FIGURES  ── Trin 6 only
# ══════════════════════════════════════════════════════════════════════════════
def create_step6_figures(df: pd.DataFrame, out_dir: Path) -> None:
    """
    Step 6 section figures (same visual style as the main charts):
      1. Stacked bar chart — Area + Volume, Trin 6 only.
      2. Count table      — GVFK and Sites for Trin 6 only.
    """
    _create_step6_bars(df, out_dir)
    _create_step6_table(df, out_dir)


def _create_step6_bars(df: pd.DataFrame, out_dir: Path) -> None:
    """Single-bar stacked chart: Trin 6 only for Area and Volume."""
    metrics = [
        ("Areal (km2)",   "Samlet grundvandsareal (km²)"),
        ("Volumen (km3)", "Samlet grundvandsvolumen (km³)"),
    ]

    # Single bar (Trin 6 only)
    fig, axes = plt.subplots(1, 2, figsize=(16, 12))
    x = np.arange(len(STEPS_6))
    bar_width = 0.45

    for ax, (metric, ylabel) in zip(axes, metrics):
        data    = _get_metric_6(df, metric)
        totals  = data.sum(axis=1).values
        t1      = totals[0]
        bottoms = np.zeros(len(STEPS_6))

        for region, color, label in zip(REGIONS, GRAY5, REGION_LABELS):
            values = data[region].values
            ax.bar(x, values, bottom=bottoms, color=color,
                   width=bar_width, edgecolor="white", linewidth=1.0, label=label)
            bottoms += values

        for xi, total in enumerate(totals):
            pct    = total / t1 * 100 if t1 > 0 else 0
            offset = totals.max() * 0.025

            ax.text(xi, total + offset,
                    f"{total:,.0f}",
                    ha="center", va="bottom",
                    fontsize=22, fontweight="bold", color="#111111")

            pct_lbl = "100 %" if xi == 0 else f"{pct:.0f} %"
            ax.text(xi, total + offset * 4.2,
                    pct_lbl,
                    ha="center", va="bottom",
                    fontsize=18, color="#444444")

        ax.set_xticks(x)
        ax.set_xticklabels(STEP_LABELS_6_CHART, fontsize=15, linespacing=1.3,
                           rotation=20, ha="right")
        ax.set_ylabel(ylabel, fontsize=20, fontweight="bold", labelpad=12)
        ax.set_ylim(0, totals.max() * 1.38)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.yaxis.grid(True, linestyle="--", linewidth=0.5, alpha=0.5, color="#bbbbbb")
        ax.set_axisbelow(True)

    handles = [mpatches.Patch(facecolor=c, edgecolor="white", label=l)
               for c, l in zip(GRAY5, REGION_LABELS)]
    fig.legend(handles=handles, loc="lower center", ncol=5,
               bbox_to_anchor=(0.5, -0.03),
               fontsize=23, frameon=False)

    plt.tight_layout(rect=[0, 0.15, 1, 1])
    out = out_dir / "report_step6_area_volume.png"
    plt.savefig(out)
    plt.close()
    print(f"  Saved: {out.name}")


def _create_step6_table(df: pd.DataFrame, out_dir: Path) -> None:
    """Count table for Trin 6 only — PNG + Excel."""
    gvfk  = _get_metric_6(df, "GVFK")
    sites = _get_metric_6(df, "Sites")

    def get_totals_6(metric):
        mask = (df["Metric"] == metric) & (df["Step"].isin(STEPS_6))
        return df[mask].set_index("Step")["Total"].reindex(STEPS_6)

    gvfk_total  = get_totals_6("GVFK")
    sites_total = get_totals_6("Sites")

    col_names = REGION_LABELS + ["Total"]

    def fmt_num(v):
        return f"{int(v):,}".replace(",", ".") if pd.notna(v) and v > 0 else "-"

    def make_rows_6(data, totals, baseline_val):
        rows = []
        for step, row_label in zip(STEPS_6, STEP_LABELS_6_TABLE):
            cells = [fmt_num(data.loc[step, r]) for r in REGIONS]
            total = totals.loc[step]
            if total <= 0:
                cells.append("-")
            else:
                pct = total / baseline_val * 100 if baseline_val > 0 else 0
                if abs(pct - 100) < 0.5:
                    cells.append(fmt_num(total))
                else:
                    cells.append(f"{fmt_num(total)}\n({pct:.0f} %)")
            rows.append((row_label, cells))
        return rows

    gvfk_baseline  = gvfk_total.iloc[0]
    sites_nonzero  = sites_total[sites_total > 0]
    sites_baseline = sites_nonzero.iloc[0] if not sites_nonzero.empty else 1

    gvfk_rows  = make_rows_6(gvfk,  gvfk_total,  gvfk_baseline)
    sites_rows = [(lbl, cells) for lbl, cells in
                  make_rows_6(sites, sites_total, sites_baseline)
                  if any(c != "-" for c in cells)]

    _save_table_png(gvfk_rows, sites_rows, col_names, out_dir,
                    out_name="report_step6_count_table.png")
    _save_table_excel(gvfk_rows, sites_rows, col_names, out_dir,
                      out_name="report_step6_count_table.xlsx")


def create_step6_regional_metrics_table(df: pd.DataFrame, out_dir: Path) -> None:
    """
    Step 6 regional results table (Q95), with only:
      - GVF
      - Sites
      - Rivers
      - Area
      - Volume

    Data sources:
      - Step 6 outputs: step6_site_mkk_exceedances (GVF, sites, rivers)
      - Step 6 summary rows in regional_summary_transposed.csv (area, volume)
    """
    import geopandas as gpd
    from config import (
        COLUMN_MAPPINGS,
        DATA_DIR,
        RIVERS_LAYER_NAME,
        RIVERS_PATH,
        get_output_path,
    )

    def _pick_col(cols, candidates):
        for c in candidates:
            if c in cols:
                return c
        return None

    def _assign_region_by_overlap(gdf, regions, id_col):
        # Assign each geometry to the region with largest overlap area.
        overlaps = gpd.overlay(
            gdf[[id_col, "geometry"]], regions[["Region", "geometry"]], how="intersection"
        )
        if overlaps.empty:
            out = gdf[[id_col]].copy()
            out["Region"] = np.nan
            return out
        overlaps["overlap_measure"] = overlaps.geometry.area
        # Line intersections have zero area; fall back to geometric length.
        if float(overlaps["overlap_measure"].fillna(0).max()) == 0.0:
            overlaps["overlap_measure"] = overlaps.geometry.length
        return (
            overlaps.sort_values("overlap_measure", ascending=False)
            .drop_duplicates(subset=id_col)[[id_col, "Region"]]
        )

    # Load Step 6 and filter to Q95
    step6 = pd.read_csv(get_output_path("step6_site_mkk_exceedances"))
    if "Flow_Scenario" in step6.columns:
        q95 = step6[step6["Flow_Scenario"] == "Q95"].copy()
        if not q95.empty:
            step6 = q95

    if step6.empty:
        print("  Step 6 regional metrics skipped: no Step 6 rows found.")
        return

    # Regions layer
    regions = gpd.read_file(DATA_DIR / "regionsinddeling" / "regionsinddeling.shp")
    for c in ["Regionsnavn", "regionsnavn", "REGIONNAVN", "Navn", "navn"]:
        if c in regions.columns:
            regions = regions.rename(columns={c: "Region"})
            break
    regions = regions[["Region", "geometry"]].copy()
    crs = regions.crs

    # 1) GVF counts per region (from Step 6 output)
    gvfk_col = COLUMN_MAPPINGS["grundvand"]["gvfk_id"]
    gvf = gpd.read_file(get_output_path("step3_gvfk_polygons")).to_crs(crs)
    gvf[gvfk_col] = gvf[gvfk_col].astype(str)
    gvf_ids = set(step6["GVFK"].dropna().astype(str))
    gvf_sel = gvf[gvf[gvfk_col].isin(gvf_ids)].copy()
    gvf_reg = _assign_region_by_overlap(gvf_sel, regions, gvfk_col)
    gvf_counts = gvf_reg["Region"].value_counts()

    # 2) Site counts per region (from Step 6 output, point-in-region using centroids)
    sites = gpd.read_file(get_output_path("step3_v1v2_sites")).to_crs(crs)
    site_id_col = _pick_col(sites.columns, ["Lokalitet_", "Lokalitetsnr", "site_id", "Lokalitet_ID"])
    if site_id_col is None:
        raise KeyError("Could not identify site ID column in step3_v1v2_sites.")
    sites["_site_id"] = sites[site_id_col].astype(str)
    site_ids = set(step6["Lokalitet_ID"].dropna().astype(str))
    sites_sel = sites[sites["_site_id"].isin(site_ids)].copy()
    sites_sel["geometry"] = sites_sel.geometry.centroid
    sites_reg = gpd.sjoin(sites_sel[["_site_id", "geometry"]], regions, how="left", predicate="intersects")
    site_counts = sites_reg.groupby("Region")["_site_id"].nunique()

    # 3) Rivers per region (from Step 6 output; ov_id dissolved and region-assigned by overlap)
    rivers = gpd.read_file(RIVERS_PATH, layer=RIVERS_LAYER_NAME).to_crs(crs)
    ov_col = _pick_col(rivers.columns, ["ov_id", "OV_ID", "river_id"])
    if ov_col is None:
        raise KeyError("Could not identify river ov_id column in river layer.")

    rivers["_ov_id"] = rivers[ov_col].astype(str)

    ov_ids = set(step6["Nearest_River_ov_id"].dropna().astype(str))

    rivers_ov = rivers[rivers["_ov_id"].isin(ov_ids)].copy()
    if not rivers_ov.empty:
        ov_geom = rivers_ov.dissolve(by="_ov_id").reset_index()[["_ov_id", "geometry"]]
        ov_reg = _assign_region_by_overlap(ov_geom, regions, "_ov_id")
        river_counts = ov_reg["Region"].value_counts()
    else:
        river_counts = pd.Series(dtype=float)

    # 4) Area + Volume by region from Step 6 rows in summary data
    def _metric_row(metric_name: str) -> pd.Series:
        m = (df["Metric"] == metric_name) & (df["Step"] == "Trin 6 (Tilstand)")
        if not m.any():
            return pd.Series(dtype=float)
        row = df.loc[m].iloc[0]
        vals = {r: pd.to_numeric(row.get(r), errors="coerce") for r in REGIONS}
        return pd.Series(vals)

    area_vals = _metric_row("Areal (km2)")
    vol_vals = _metric_row("Volumen (km3)")

    # Assemble output table
    rows = [
        ("GVF i ringe tilstand (antal)", gvf_counts, "int"),
        ("Bidragende lokaliteter (antal)", site_counts, "int"),
        ("Berørte vandløb (antal)", river_counts, "int"),
        ("Areal (km²)", area_vals, "float_sum"),
        ("Volumen (km³)", vol_vals, "float_sum"),
    ]

    def _fmt(v, kind):
        if pd.isna(v):
            return "-"
        if kind == "int":
            return f"{int(round(float(v))):,}".replace(",", ".")
        return f"{float(v):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

    table = []
    for label, s, kind in rows:
        vals = [s.get(r, np.nan) for r in REGIONS]
        if kind in {"int", "float_sum"}:
            total = np.nansum(vals)
        elif len(vals) == 0 or np.all(pd.isna(vals)):
            total = np.nan
        else:
            total = np.nanmax(vals) if "Maks" in label else np.nanmedian(vals)
        row_cells = [_fmt(v, kind) for v in vals] + [_fmt(total, kind)]
        table.append((label, row_cells))

    col_names = REGION_LABELS + ["Total"]
    _save_step6_metrics_png(table, col_names, out_dir)
    _save_step6_metrics_excel(table, col_names, out_dir)


def _save_step6_metrics_png(rows, col_names, out_dir):
    """Render Step 6 regional metrics table as PNG."""
    n_cols = len(col_names)
    row_h = 0.075
    fig_h = max(6.5, (len(rows) + 2) * row_h * 8.5)
    fig, ax = plt.subplots(figsize=(17, fig_h))
    ax.axis("off")

    hdr_bg = "#1B2A3B"
    hdr_fg = "white"
    row_a = "#FFFFFF"
    row_b = "#EEF3FA"
    tot_bg = "#D9E2F0"
    border = "#C0C8D8"

    left = 0.03
    metric_w = 0.35
    data_w = 0.095
    total_w = 0.115
    col_xs = [left + metric_w + i * data_w for i in range(n_cols - 1)] + [left + metric_w + (n_cols - 1) * data_w]
    col_ws = [data_w] * (n_cols - 1) + [total_w]

    def cell(x, y, w, h, text, bg, fg="#111", bold=False, align="center"):
        ax.add_patch(plt.Rectangle((x, y), w, h, transform=ax.transAxes, facecolor=bg, edgecolor=border, linewidth=0.6, clip_on=False))
        ha = "left" if align == "left" else "center"
        xpos = x + 0.008 if align == "left" else x + w / 2
        ax.text(xpos, y + h / 2, text, transform=ax.transAxes, ha=ha, va="center", fontsize=11, color=fg, fontweight="bold" if bold else "normal")

    y = 0.94
    cell(left, y, metric_w, row_h, "Metrik (Q95)", hdr_bg, hdr_fg, bold=True, align="left")
    for cx, cw, label in zip(col_xs, col_ws, col_names):
        cell(cx, y, cw, row_h, label, hdr_bg, hdr_fg, bold=True)
    y -= row_h

    for i, (label, vals) in enumerate(rows):
        bg = row_a if i % 2 == 0 else row_b
        cell(left, y, metric_w, row_h, label, bg, align="left")
        for j, (cx, cw, val) in enumerate(zip(col_xs, col_ws, vals)):
            is_total = j == (len(vals) - 1)
            cell(cx, y, cw, row_h, val, tot_bg if is_total else bg, bold=is_total)
        y -= row_h

    out = out_dir / "report_step6_regional_metrics.png"
    plt.savefig(out, dpi=220)
    plt.close()
    print(f"  Saved: {out.name}")


def _save_step6_metrics_excel(rows, col_names, out_dir):
    """Write Step 6 regional metrics table to Excel."""
    out = out_dir / "report_step6_regional_metrics.xlsx"
    try:
        with pd.ExcelWriter(out, engine="xlsxwriter") as writer:
            wb = writer.book
            ws = wb.add_worksheet("Step6_Metrics")
            writer.sheets["Step6_Metrics"] = ws

            def fmt(**kw):
                base = {"border": 1, "font_size": 10, "valign": "vcenter"}
                base.update(kw)
                return wb.add_format(base)

            hdr = fmt(bold=True, bg_color="#1B2A3B", font_color="white", align="center")
            txt = fmt(align="left")
            num = fmt(align="center")
            num_alt = fmt(align="center", bg_color="#EEF3FA")
            num_tot = fmt(align="center", bold=True, bg_color="#D9E2F0")

            ws.set_column(0, 0, 44)
            ws.set_column(1, len(col_names), 16)

            ws.write(0, 0, "Metrik (Q95)", hdr)
            for c, name in enumerate(col_names, 1):
                ws.write(0, c, name, hdr)

            for r, (label, vals) in enumerate(rows, 1):
                ws.write(r, 0, label, txt)
                alt = r % 2 == 0
                for c, v in enumerate(vals, 1):
                    is_total = c == len(vals)
                    f = num_tot if is_total else (num_alt if alt else num)
                    ws.write(r, c, v, f)
        print(f"  Saved: {out.name}")
    except Exception as e:
        print(f"  Could not save Excel: {e}")


# ══════════════════════════════════════════════════════════════════════════════
# Main
# ══════════════════════════════════════════════════════════════════════════════
def main():
    print("=" * 55)
    print("REPORT FIGURES")
    print("=" * 55)

    if not DATA_FILE.exists():
        print(f"  Data file not found:\n    {DATA_FILE}")
        print("  Run the main workflow first to generate the CSV.")
        return

    df = pd.read_csv(DATA_FILE)
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    print("\n[1/5] Stacked bar charts – Option A (Set2 colours)...")
    try:
        create_stacked_bar_charts(df, OUT_DIR, SCHEME_A)
    except Exception as e:
        print(f"  Error: {e}")
        import traceback; traceback.print_exc()

    print("\n[2/5] Stacked bar charts – Option C (grayscale)...")
    try:
        create_stacked_bar_charts(df, OUT_DIR, SCHEME_C)
    except Exception as e:
        print(f"  Error: {e}")
        import traceback; traceback.print_exc()

    print("\n[3/5] Paired absolute + normalized charts (grayscale)...")
    try:
        create_paired_normalized_charts(df, OUT_DIR)
    except Exception as e:
        print(f"  Error: {e}")
        import traceback; traceback.print_exc()

    print("\n[4/5] Count table (GVFK + Sites)...")
    try:
        create_count_table(df, OUT_DIR)
    except Exception as e:
        print(f"  Error: {e}")
        import traceback; traceback.print_exc()

    print("\n[5/5] Step 6 results table (Q95)...")
    try:
        create_step6_regional_metrics_table(df, OUT_DIR)
    except Exception as e:
        print(f"  Error: {e}")
        import traceback; traceback.print_exc()

    print(f"\nAll outputs saved to:\n  {OUT_DIR}")


if __name__ == "__main__":
    main()
