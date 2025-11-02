import pandas as pd
import matplotlib.pyplot as plt

combinations_file = r"C:\Users\olive\OneDrive - Danmarks Tekniske Universitet\Poul Løgstrup Bjergs filer - Work_Projects_Oliver Lund\Beslutningstræ - Grundvands projekt\Resultater\step4_valid_distances.csv"
df = pd.read_csv(combinations_file)

site_analysis = (
    df.groupby("Lokalitet_ID")
    .agg(
        {
            "GVFK": "count",
            "Distance_to_River_m": ["min", "max", lambda x: (x <= 500).sum()],
        }
    )
    .reset_index()
)
site_analysis.columns = [
    "Lokalitet_ID",
    "Num_GVFKs",
    "Min_Distance",
    "Max_Distance",
    "Num_Within_500m",
]

multi_gvfk_sites = site_analysis[site_analysis["Num_GVFKs"] > 1]
single_gvfk_sites = site_analysis[site_analysis["Num_GVFKs"] == 1]

fig = plt.figure(figsize=(16, 10))
ax1 = plt.subplot(2, 2, 1)

none_within = multi_gvfk_sites[multi_gvfk_sites["Num_Within_500m"] == 0]
exactly_one = multi_gvfk_sites[
    (multi_gvfk_sites["Num_Within_500m"] == 1) & (multi_gvfk_sites["Num_GVFKs"] > 1)
]
all_within = multi_gvfk_sites[
    multi_gvfk_sites["Num_Within_500m"] == multi_gvfk_sites["Num_GVFKs"]
]
some_but_not_all = multi_gvfk_sites[
    (multi_gvfk_sites["Num_Within_500m"] >= 2)
    & (multi_gvfk_sites["Num_Within_500m"] < multi_gvfk_sites["Num_GVFKs"])
]

categories = [
    "No GVFKs\nwith rivers\n≤500m",
    "Exactly 1 GVFK\nwith rivers ≤500m\n(others further)",
    "ALL GVFKs\nhave rivers\n≤500m",
    "2+ GVFKs\nhave rivers ≤500m\n(but not all)",
]
counts = [len(none_within), len(exactly_one), len(all_within), len(some_but_not_all)]
colors = ["#CCCCCC", "#FFD700", "#FF6347", "#FF8C42"]

bars = ax1.bar(
    categories, counts, color=colors, edgecolor="black", linewidth=1.5, alpha=0.8
)

for bar, count in zip(bars, counts):
    height = bar.get_height()
    pct = (count / len(multi_gvfk_sites)) * 100
    ax1.text(
        bar.get_x() + bar.get_width() / 2.0,
        height,
        f"{count:,}\n({pct:.1f}%)",
        ha="center",
        va="bottom",
        fontweight="bold",
        fontsize=10,
    )

ax1.set_ylabel("Antal lokaliteter", fontsize=12, fontweight="bold")
ax1.set_title(
    f"Multi-GVFK Sites (n={len(multi_gvfk_sites):,}): River Proximity at 500m Threshold",
    fontsize=13,
    fontweight="bold",
    pad=15,
)
ax1.grid(axis="y", alpha=0.3)
plt.setp(ax1.xaxis.get_majorticklabels(), fontsize=9, fontweight="bold")

ax2 = plt.subplot(2, 2, 2)
single_within_500 = single_gvfk_sites[single_gvfk_sites["Num_Within_500m"] >= 1]
multi_impact = len(all_within) + len(some_but_not_all)
risk_categories = [
    "Single GVFK\nwith rivers ≤500m",
    "Multiple GVFKs\nwith rivers ≤500m",
]
risk_counts = [len(single_within_500), multi_impact]
risk_colors = ["#66B3FF", "#FF6347"]

bars2 = ax2.bar(
    risk_categories,
    risk_counts,
    color=risk_colors,
    edgecolor="black",
    linewidth=1.5,
    alpha=0.8,
)

total_at_risk = len(single_within_500) + multi_impact
for bar, count in zip(bars2, risk_counts):
    height = bar.get_height()
    pct = (count / total_at_risk) * 100
    ax2.text(
        bar.get_x() + bar.get_width() / 2.0,
        height,
        f"{count:,}\n({pct:.1f}%)",
        ha="center",
        va="bottom",
        fontweight="bold",
        fontsize=11,
    )

ax2.set_ylabel("Antal lokaliteter", fontsize=12, fontweight="bold")
ax2.set_title(
    f"Sites with ≥1 GVFK having rivers ≤500m (n={total_at_risk:,})",
    fontsize=13,
    fontweight="bold",
    pad=15,
)
ax2.grid(axis="y", alpha=0.3)
plt.setp(ax2.xaxis.get_majorticklabels(), fontsize=10, fontweight="bold")

ax3 = plt.subplot(2, 2, 3)
gvfk_distribution = site_analysis["Num_GVFKs"].value_counts().sort_index()
x_vals = gvfk_distribution.index.tolist()
y_vals = gvfk_distribution.values.tolist()

bars3 = ax3.bar(
    x_vals, y_vals, color="#1f77b4", edgecolor="black", linewidth=1.5, alpha=0.8
)

for bar, x, y in zip(bars3, x_vals, y_vals):
    pct = (y / len(site_analysis)) * 100
    ax3.text(
        bar.get_x() + bar.get_width() / 2.0,
        bar.get_height(),
        f"{y:,}\n({pct:.1f}%)",
        ha="center",
        va="bottom",
        fontweight="bold",
        fontsize=9,
    )

ax3.set_xlabel("Antal GVFKs per lokalitet", fontsize=12, fontweight="bold")
ax3.set_ylabel("Antal lokaliteter", fontsize=12, fontweight="bold")
ax3.set_title(
    f"GVFK Distribution (n={len(site_analysis):,} sites)",
    fontsize=13,
    fontweight="bold",
    pad=15,
)
ax3.grid(axis="y", alpha=0.3)
ax3.set_xticks(x_vals)

ax4 = plt.subplot(2, 2, 4)
multi_impact_sites = multi_gvfk_sites[multi_gvfk_sites["Num_Within_500m"] >= 2]
if len(multi_impact_sites) > 0:
    impact_distribution = (
        multi_impact_sites["Num_Within_500m"].value_counts().sort_index()
    )
    x_impact = impact_distribution.index.tolist()
    y_impact = impact_distribution.values.tolist()
    bars4 = ax4.bar(
        x_impact, y_impact, color="#E31A1C", edgecolor="black", linewidth=1.5, alpha=0.8
    )
    for bar, x, y in zip(bars4, x_impact, y_impact):
        pct = (y / len(multi_impact_sites)) * 100
        ax4.text(
            bar.get_x() + bar.get_width() / 2.0,
            bar.get_height(),
            f"{y:,}\n({pct:.1f}%)",
            ha="center",
            va="bottom",
            fontweight="bold",
            fontsize=10,
        )
    ax4.set_xlabel("Antal GVFKs med floder ≤500m", fontsize=12, fontweight="bold")
    ax4.set_ylabel("Antal lokaliteter", fontsize=12, fontweight="bold")
    ax4.set_title(
        f"Sites with 2+ GVFKs having rivers ≤500m (n={len(multi_impact_sites):,})",
        fontsize=13,
        fontweight="bold",
        pad=15,
    )
    ax4.grid(axis="y", alpha=0.3)
    ax4.set_xticks(x_impact)

plt.suptitle(
    "Multi-GVFK Impact Analysis at 500m Threshold\n35,728 unique sites across 69,627 lokalitet-GVFK combinations",
    fontsize=16,
    fontweight="bold",
    y=0.995,
)
plt.tight_layout()
output_path = r"../../../Resultater/Figures/step4/multi_gvfk_impact_analysis_500m.png"
plt.savefig(output_path, dpi=300, bbox_inches="tight")
print(f"[OK] Saved: {output_path}")
