"""
MKK Scenario Sensitivity Analysis
==================================

Standalone analysis script to evaluate how different model scenarios
(concentration × MKK combinations) affect the final assessment results.

This analyzes:
1. Concentration sensitivity: How different modelstof concentrations drive flux
2. MKK sensitivity: How different threshold values affect exceedance counts
3. Combined effect: Which categories/scenarios dominate the results

Run independently after main_workflow.py completes:
    python tools/scenario_sensitivity_analysis.py

Outputs:
- Console summary with key findings
- Plots saved to Resultater/sensitivity_analysis/
- CSV with detailed breakdown
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
import sys

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import (
    get_output_path,
    MKK_THRESHOLDS,
    CATEGORY_SCENARIOS,
    STANDARD_CONCENTRATIONS,
    RESULTS_DIR,
)

# Professional plot styling (consistent with other plots)
plt.style.use('default')
plt.rcParams.update({
    'font.family': ['Arial', 'DejaVu Sans', 'sans-serif'],
    'font.size': 12,
    'axes.titlesize': 14,
    'axes.labelsize': 12,
    'xtick.labelsize': 10,
    'ytick.labelsize': 10,
    'figure.dpi': 100,
    'savefig.dpi': 300,
    'savefig.bbox': 'tight',
    'savefig.facecolor': 'white',
    'figure.facecolor': 'white',
    'axes.facecolor': 'white',
    'axes.grid': False,
})


def load_cmix_results():
    """Load the cmix results from Step 6."""
    cmix_path = get_output_path("step6_cmix_results")
    if not cmix_path.exists():
        raise FileNotFoundError(f"Cmix results not found: {cmix_path}\nRun main_workflow.py first.")
    return pd.read_csv(cmix_path)


def get_scenario_parameters():
    """Build a table of all scenario parameters (concentration + MKK)."""
    records = []
    
    for category, modelstoffer in CATEGORY_SCENARIOS.items():
        if not modelstoffer:
            continue  # Skip categories without scenarios
            
        for modelstof in modelstoffer:
            # Get concentration
            scenario_key = f"{category}__via_{modelstof}"
            conc = STANDARD_CONCENTRATIONS["category"].get(scenario_key)
            if conc is None or conc == -1:
                conc = STANDARD_CONCENTRATIONS["compound"].get(modelstof)
            
            # Get MKK
            mkk = MKK_THRESHOLDS.get(modelstof)
            if mkk is None:
                mkk = MKK_THRESHOLDS.get(category)
            
            records.append({
                "Category": category,
                "Modelstof": modelstof,
                "Scenario": scenario_key,
                "Concentration_ug_L": conc,
                "MKK_ug_L": mkk,
                "C_over_MKK": conc / mkk if (conc and mkk) else None,
            })
    
    return pd.DataFrame(records)


def analyze_scenario_sensitivity(cmix: pd.DataFrame, output_dir: Path):
    """Main analysis function."""
    
    print("=" * 80)
    print("MKK SCENARIO SENSITIVITY ANALYSIS")
    print("=" * 80)
    
    # 1. Get scenario parameters
    params = get_scenario_parameters()
    print("\n### Scenario Parameters (Concentration / MKK) ###\n")
    print(params.to_string(index=False))
    params.to_csv(output_dir / "scenario_parameters.csv", index=False)
    
    # 2. Exceedance counts per scenario
    exceeds = cmix[cmix["Exceedance_Flag"] == True].copy()
    
    scenario_summary = []
    for cat in exceeds["Qualifying_Category"].unique():
        cat_data = exceeds[exceeds["Qualifying_Category"] == cat]
        
        for substance in cat_data["Qualifying_Substance"].unique():
            sub_data = cat_data[cat_data["Qualifying_Substance"] == substance]
            
            # Extract modelstof from substance name
            if "__via_" in substance:
                modelstof = substance.split("__via_")[-1]
            else:
                modelstof = substance
            
            # Get parameters
            mkk = sub_data["MKK_ug_L"].iloc[0] if "MKK_ug_L" in sub_data.columns else None
            conc = params[params["Scenario"] == substance]["Concentration_ug_L"].values
            conc = conc[0] if len(conc) > 0 else None
            
            scenario_summary.append({
                "Category": cat,
                "Scenario": substance,
                "Modelstof": modelstof,
                "Concentration_ug_L": conc,
                "MKK_ug_L": mkk,
                "Exceedance_Count": len(sub_data),
                "Unique_GVFKs": sub_data["River_Segment_GVFK"].nunique(),
                "Unique_Segments": sub_data["Nearest_River_FID"].nunique() if "Nearest_River_FID" in sub_data.columns else None,
                "Max_Exceedance_Ratio": sub_data["Exceedance_Ratio"].max(),
                "Median_Exceedance_Ratio": sub_data["Exceedance_Ratio"].median(),
            })
    
    summary_df = pd.DataFrame(scenario_summary)
    summary_df = summary_df.sort_values("Exceedance_Count", ascending=False)
    
    print("\n### Exceedances by Scenario ###\n")
    print(summary_df.to_string(index=False))
    summary_df.to_csv(output_dir / "scenario_exceedance_summary.csv", index=False)
    
    # 3. Analyze multi-scenario categories
    print("\n### Multi-Scenario Category Analysis ###\n")
    
    multi_scenario_cats = {k: v for k, v in CATEGORY_SCENARIOS.items() if len(v) > 1}
    
    category_analysis = []
    for cat, scenarios in multi_scenario_cats.items():
        cat_exceeds = exceeds[exceeds["Qualifying_Category"] == cat]
        if cat_exceeds.empty:
            continue
        
        # All GVFKs affected by this category (any scenario)
        all_gvfks = set(cat_exceeds["River_Segment_GVFK"].unique())
        
        # Per-scenario GVFK sets
        scenario_gvfks = {}
        for substance in cat_exceeds["Qualifying_Substance"].unique():
            sub_gvfks = set(cat_exceeds[cat_exceeds["Qualifying_Substance"] == substance]["River_Segment_GVFK"])
            scenario_gvfks[substance] = sub_gvfks
        
        # Find GVFKs that exceed in ALL scenarios vs ONLY some
        if scenario_gvfks:
            common_gvfks = set.intersection(*scenario_gvfks.values()) if scenario_gvfks else set()
            
            print(f"\n{cat}:")
            print(f"  Total GVFKs affected: {len(all_gvfks)}")
            print(f"  GVFKs exceeding ALL scenarios: {len(common_gvfks)}")
            
            for scenario, gvfks in scenario_gvfks.items():
                other_gvfks = [g for s, g in scenario_gvfks.items() if s != scenario]
                if other_gvfks:
                    only_this = gvfks - set.union(*other_gvfks)
                else:
                    only_this = gvfks
                print(f"  {scenario}: {len(gvfks)} GVFKs ({len(only_this)} unique to this scenario)")
            
            category_analysis.append({
                "Category": cat,
                "Total_GVFKs": len(all_gvfks),
                "GVFKs_All_Scenarios": len(common_gvfks),
                "Scenario_Count": len(scenario_gvfks),
            })
    
    # 4. Create visualizations
    create_sensitivity_plots(summary_df, params, exceeds, output_dir)
    
    # 5. Key findings summary
    print("\n" + "=" * 80)
    print("KEY FINDINGS")
    print("=" * 80)
    
    total_gvfks = exceeds["River_Segment_GVFK"].nunique()
    print(f"\nTotal GVFKs in poor status: {total_gvfks}")
    
    # Top drivers
    print("\nTop 5 scenarios by GVFK count:")
    top5 = summary_df.nlargest(5, "Unique_GVFKs")
    for _, row in top5.iterrows():
        print(f"  {row['Scenario']}: {row['Unique_GVFKs']} GVFKs ({row['Exceedance_Count']} exceedances)")
    
    # Concentration vs MKK impact
    print("\n\nConcentration vs MKK impact analysis:")
    print("  (Higher C/MKK ratio = more likely to exceed)")
    params_with_exc = params.merge(
        summary_df[["Scenario", "Exceedance_Count", "Unique_GVFKs"]], 
        on="Scenario", 
        how="left"
    ).fillna(0)
    params_with_exc = params_with_exc.sort_values("C_over_MKK", ascending=False)
    print(params_with_exc[["Scenario", "Concentration_ug_L", "MKK_ug_L", "C_over_MKK", "Unique_GVFKs"]].head(10).to_string(index=False))
    
    params_with_exc.to_csv(output_dir / "scenario_impact_analysis.csv", index=False)
    
    return summary_df


def create_sensitivity_plots(summary_df: pd.DataFrame, params: pd.DataFrame, exceeds: pd.DataFrame, output_dir: Path):
    """Create visualization plots for sensitivity analysis."""
    
    # --- PLOT 1: Scenario Comparison (Exceedances vs GVFKs) ---
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 8))
    
    # Sort by GVFK count
    plot_data = summary_df.sort_values("Unique_GVFKs", ascending=True).tail(15)
    
    # Left: Exceedance count
    colors1 = plt.cm.Blues(np.linspace(0.3, 0.9, len(plot_data)))
    bars1 = ax1.barh(range(len(plot_data)), plot_data["Exceedance_Count"], color=colors1)
    ax1.set_yticks(range(len(plot_data)))
    ax1.set_yticklabels([s.replace("__via_", "\n→ ") for s in plot_data["Scenario"]], fontsize=9)
    ax1.set_xlabel("Number of Exceedances", fontweight="bold")
    ax1.set_title("Exceedances per Scenario", fontsize=14, fontweight="bold")
    
    for bar, val in zip(bars1, plot_data["Exceedance_Count"]):
        ax1.text(val + 5, bar.get_y() + bar.get_height()/2, f"{int(val)}", 
                 va="center", fontsize=9, fontweight="bold")
    
    # Right: GVFK count
    colors2 = plt.cm.Oranges(np.linspace(0.3, 0.9, len(plot_data)))
    bars2 = ax2.barh(range(len(plot_data)), plot_data["Unique_GVFKs"], color=colors2)
    ax2.set_yticks(range(len(plot_data)))
    ax2.set_yticklabels([s.replace("__via_", "\n→ ") for s in plot_data["Scenario"]], fontsize=9)
    ax2.set_xlabel("Number of GVFKs in Poor Status", fontweight="bold")
    ax2.set_title("GVFKs Affected per Scenario", fontsize=14, fontweight="bold")
    
    for bar, val in zip(bars2, plot_data["Unique_GVFKs"]):
        ax2.text(val + 1, bar.get_y() + bar.get_height()/2, f"{int(val)}", 
                 va="center", fontsize=9, fontweight="bold")
    
    plt.suptitle("Scenario Sensitivity: Impact on Exceedances and GVFKs", fontsize=16, fontweight="bold", y=1.02)
    plt.tight_layout()
    plt.savefig(output_dir / "scenario_comparison.png", facecolor="white", bbox_inches="tight")
    plt.close()
    
    # --- PLOT 2: Concentration vs MKK Scatter ---
    fig, ax = plt.subplots(figsize=(12, 8))
    
    # Merge params with exceedance data
    plot_params = params.merge(
        summary_df[["Scenario", "Unique_GVFKs"]], 
        on="Scenario", 
        how="left"
    ).fillna(0)
    
    # Filter to valid data
    plot_params = plot_params[plot_params["Concentration_ug_L"].notna() & plot_params["MKK_ug_L"].notna()]
    
    # Scatter with size = GVFKs
    scatter = ax.scatter(
        plot_params["Concentration_ug_L"],
        plot_params["MKK_ug_L"],
        s=plot_params["Unique_GVFKs"] * 20 + 50,  # Size by impact
        c=plot_params["Unique_GVFKs"],
        cmap="YlOrRd",
        alpha=0.7,
        edgecolors="black",
        linewidths=1,
    )
    
    # Add annotations
    for _, row in plot_params.iterrows():
        if row["Unique_GVFKs"] > 5:  # Only label significant points
            ax.annotate(
                row["Modelstof"][:15],
                (row["Concentration_ug_L"], row["MKK_ug_L"]),
                fontsize=8,
                ha="left",
                va="bottom",
            )
    
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("Standard Concentration (µg/L)", fontsize=12, fontweight="bold")
    ax.set_ylabel("MKK Threshold (µg/L)", fontsize=12, fontweight="bold")
    ax.set_title("Concentration vs MKK: Bubble Size = GVFKs Affected", fontsize=14, fontweight="bold")
    
    # Add colorbar
    cbar = plt.colorbar(scatter, ax=ax)
    cbar.set_label("GVFKs in Poor Status", fontweight="bold")
    
    # Add diagonal reference lines (C/MKK ratio)
    x_range = np.logspace(0, 5, 100)
    for ratio, label in [(10, "C/MKK = 10"), (100, "C/MKK = 100"), (1000, "C/MKK = 1000")]:
        ax.plot(x_range, x_range / ratio, "--", alpha=0.3, color="gray")
        ax.text(x_range[-1] * 0.7, x_range[-1] / ratio * 0.7, label, fontsize=8, color="gray")
    
    plt.tight_layout()
    plt.savefig(output_dir / "concentration_vs_mkk.png", facecolor="white")
    plt.close()
    
    # --- PLOT 3: Category Breakdown with Scenario Split ---
    fig, ax = plt.subplots(figsize=(14, 8))
    
    # Group by category and scenario
    cat_scenario = summary_df.groupby("Category").agg({
        "Unique_GVFKs": "max",  # Max across scenarios
        "Exceedance_Count": "sum",
        "Scenario": "count"
    }).rename(columns={"Scenario": "Scenario_Count"})
    cat_scenario = cat_scenario.sort_values("Unique_GVFKs", ascending=True)
    
    # Create stacked bar showing scenario breakdown
    categories = cat_scenario.index.tolist()
    y_pos = range(len(categories))
    
    scenario_colors = plt.cm.tab10(np.linspace(0, 1, 10))
    
    for cat_idx, cat in enumerate(categories):
        cat_scenarios = summary_df[summary_df["Category"] == cat].sort_values("Unique_GVFKs", ascending=False)
        left = 0
        for scen_idx, (_, row) in enumerate(cat_scenarios.iterrows()):
            width = row["Unique_GVFKs"]
            ax.barh(cat_idx, width, left=left, color=scenario_colors[scen_idx % 10], 
                   edgecolor="white", linewidth=0.5, label=row["Modelstof"] if cat_idx == 0 else None)
            if width > 3:
                ax.text(left + width/2, cat_idx, row["Modelstof"][:8], 
                       ha="center", va="center", fontsize=8, color="white", fontweight="bold")
            left += width
    
    ax.set_yticks(y_pos)
    ax.set_yticklabels(categories, fontsize=10)
    ax.set_xlabel("Number of GVFKs (stacked by scenario)", fontsize=12, fontweight="bold")
    ax.set_title("GVFKs per Category: Scenario Contribution", fontsize=14, fontweight="bold")
    
    plt.tight_layout()
    plt.savefig(output_dir / "category_scenario_breakdown.png", facecolor="white")
    plt.close()
    
    print(f"\nPlots saved to: {output_dir}")


def main():
    """Run the complete sensitivity analysis."""
    
    # Create output directory
    output_dir = RESULTS_DIR / "sensitivity_analysis"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Load data
    print("\nLoading cmix results...")
    cmix = load_cmix_results()
    print(f"  Loaded {len(cmix):,} rows, {cmix['Exceedance_Flag'].sum():,} exceedances")
    
    # Run analysis
    summary = analyze_scenario_sensitivity(cmix, output_dir)
    
    print("\n" + "=" * 80)
    print(f"Analysis complete. Results saved to: {output_dir}")
    print("=" * 80)


if __name__ == "__main__":
    main()
