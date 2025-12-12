"""
Risikovurdering Visualizations - Steps 4-5 Plotting Module
===========================================================

Visualization functions for the risk assessment workflow (Steps 4-5).
Creates publication-ready plots for scientific reports and analysis.

Contents:
1. Step 4: Distance Analysis (histograms, CDFs with thresholds)
2. Step 5: Risk Assessment & Compound Categories
   - Compound category distance boxplot
   - Threshold comparison chart
   - Category frequency chart
   - Landfill analysis
   - Step 5a vs 5b comparison
   - Top activities/branches charts

For workflow summary plots (GVFK/sites progression), see workflow_summary_plots.py
For optional branch analysis, see optional_analysis/step5_branch_analysis.py
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os
from pathlib import Path

# Reset any previously applied styles and apply professional settings
plt.style.use('default')
plt.rcParams.update({
    'font.family': ['Arial', 'DejaVu Sans', 'sans-serif'],
    'font.size': 14,           # Bigger base font for PowerPoint
    'axes.titlesize': 18,      # Bigger titles
    'axes.labelsize': 16,      # Bigger axis labels
    'xtick.labelsize': 12,
    'ytick.labelsize': 12,
    'figure.dpi': 100,
    'savefig.dpi': 300,
    'savefig.bbox': 'tight',
    'savefig.facecolor': 'white',
    'figure.facecolor': 'white',
    'axes.facecolor': 'white',
    'axes.grid': False,        # No grid by default
})


################################################################################
# MAIN ENTRY POINT
################################################################################

def create_all_risikovurdering_plots():
    """
    Create all risk assessment visualizations for Steps 4-5.
    Called from main_workflow.py after Step 5 completes.
    
    Note: Workflow summary plots (GVFK/sites progression) are in workflow_summary_plots.py
    """
    from config import get_output_path, get_visualization_path, WORKFLOW_SETTINGS

    print("\n" + "="*60)
    print("RISIKOVURDERING VISUALIZATIONS (Steps 4-5)")
    print("="*60)

    # Create Step 4 plots
    print("\nStep 4: Distance Analysis")
    create_step4_plots()

    # Create Step 5 plots
    print("\nStep 5: Risk Assessment")
    create_step5_plots()

    print("\n" + "="*60)
    print("RISIKOVURDERING VISUALIZATIONS COMPLETE")
    print("="*60 + "\n")


################################################################################
# STEP 4: DISTANCE ANALYSIS PLOTS
################################################################################

def create_step4_plots():
    """Create Step 4 distance analysis visualizations."""
    from config import get_output_path, get_visualization_path

    figures_path = get_visualization_path("step4")

    # Load data - using the final distances file (other files are now in-memory only)
    all_path = get_output_path("step4_final_distances_for_risk_assessment")

    if not os.path.exists(all_path):
        print("  ⚠ Step 4 data files not found")
        return

    all_df = pd.read_csv(all_path)
    
    # Calculate unique site distances (minimum distance per site)
    # Group by site ID and take the minimum distance
    if 'Lokalitet_ID' in all_df.columns:
        unique_df = all_df.loc[all_df.groupby('Lokalitet_ID')['Distance_to_River_m'].idxmin()].copy()
    else:
        unique_df = all_df.copy()

    # Create histograms with thresholds
    create_distance_histograms(unique_df, all_df, figures_path)
    print("  ✓ Distance histograms created")


def create_distance_histograms(unique_df, all_combinations_df, figures_path):
    """
    Create publication-quality distance histograms with threshold markers.
    Shows both unique sites (minimum distance) and all combinations.
    Includes V1/V2 color coding, threshold shading, and CDF plots.
    """
    from config import WORKFLOW_SETTINGS
    from matplotlib.patches import Patch

    datasets = [
        {"data": unique_df, "type": "unikke lokaliteter", "suffix": "unique",
         "description": "Unique Lokaliteter (minimum distance per site)"},
        {"data": all_combinations_df, "type": "lokalitet-GVFK kombinationer", 
         "suffix": "all_combinations",
         "description": "Alle Lokalitet-GVFK Kombinationer"}
    ]

    # Use configurable thresholds from config
    thresholds = WORKFLOW_SETTINGS.get("additional_thresholds_m", [250, 500, 1000, 1500, 2000])
    threshold_colors = ["#006400", "#32CD32", "#FFD700", "#FF6347", "#FF0000"]
    
    # Color palette for V1/V2 site types
    colors = {
        "v1": "#1f4e79",   # Dark blue for V1 only
        "v2": "#E31A1C",   # Red for V2 only
        "v1v2": "#6A3D9A", # Purple for V1 and V2
        "bar": "#1f77b4",  # Default blue for bars
    }

    for dataset_info in datasets:
        try:
            df = dataset_info["data"].copy()
            analysis_type = dataset_info["type"]
            filename_suffix = dataset_info["suffix"]

            # Cap distances at 20,000m
            distances_over_20k = (df["Distance_to_River_m"] > 20000).sum()
            df["Distance_to_River_m"] = df["Distance_to_River_m"].clip(upper=20000)

            # Calculate percentage of sites within each threshold
            percentages = []
            for t in thresholds:
                within = (df["Distance_to_River_m"] <= t).sum()
                pct = within / len(df) * 100
                percentages.append(pct)

            # Create histogram
            fig, ax1 = plt.subplots(figsize=(15, 10))
            bins = range(0, 20500, 500)  # 500m intervals up to 20000m

            # Check for V1/V2 site type information
            if "Site_Type" in df.columns:
                v1_mask = df["Site_Type"].str.contains("V1", case=False, na=False)
                v2_mask = df["Site_Type"].str.contains("V2", case=False, na=False)
                
                v1_only_data = df[v1_mask & ~v2_mask]["Distance_to_River_m"]
                v2_only_data = df[v2_mask & ~v1_mask]["Distance_to_River_m"]
                both_data = df[v1_mask & v2_mask]["Distance_to_River_m"]
                
                ax1.hist(
                    [v1_only_data, v2_only_data, both_data],
                    bins=bins,
                    color=[colors["v1"], colors["v2"], colors["v1v2"]],
                    alpha=0.75,
                    edgecolor="black",
                    linewidth=0.5,
                    label=[
                        f"V1 kun (n={len(v1_only_data)})",
                        f"V2 kun (n={len(v2_only_data)})",
                        f"V1 og V2 (n={len(both_data)})",
                    ],
                    stacked=True,
                )
            else:
                ax1.hist(df["Distance_to_River_m"], bins=bins, color=colors["bar"],
                        alpha=0.75, edgecolor="black", linewidth=0.5)

            # Add vertical threshold lines with shaded regions
            prev_threshold = df["Distance_to_River_m"].min()
            for i, threshold in enumerate(thresholds):
                ax1.axvline(threshold, color=threshold_colors[i], linestyle="-",
                           alpha=0.8, linewidth=2, label=f"{threshold}m: {percentages[i]:.1f}%")
                
                # Add percentage label
                label_y_position = ax1.get_ylim()[1] * (0.95 - i * 0.08)
                ax1.text(threshold + 100, label_y_position,
                        f"{threshold}m: {percentages[i]:.1f}%",
                        rotation=0, verticalalignment="center", horizontalalignment="left",
                        color=threshold_colors[i], fontweight="bold", fontsize=10,
                        bbox=dict(boxstyle="round,pad=0.3", facecolor="white",
                                 alpha=0.9, edgecolor=threshold_colors[i]))
                
                # Add shaded region
                ax1.axvspan(prev_threshold, threshold, color=threshold_colors[i], alpha=0.1)
                prev_threshold = threshold

            # Statistics text box
            all_stats = {
                "Count": len(df),
                "Min": df["Distance_to_River_m"].min(),
                "Max": df["Distance_to_River_m"].max(),
                "Mean": df["Distance_to_River_m"].mean(),
                "Median": df["Distance_to_River_m"].median(),
            }
            
            unique_sites = df["Lokalitet_ID"].nunique() if "Lokalitet_ID" in df.columns else all_stats["Count"]
            
            if analysis_type == "unikke lokaliteter":
                stats_text = (
                    f"Afstandsstatistik (unikke lokaliteter):\n"
                    f"Antal lokaliteter: {unique_sites:,}\n"
                    f"Min: {all_stats['Min']:.0f}m, Max: {all_stats['Max']:.0f}m*\n"
                    f"Median: {all_stats['Median']:.0f}m, Gennemsnit: {all_stats['Mean']:.0f}m\n"
                    f"*Afstande >20km grupperet som 20km"
                )
                title_main = "Afstande mellem unikke lokaliteter og nærmeste kontaktzone"
                title_sub = "Én lokalitet per site (minimum afstand)"
                ax1_ylabel = "Antal lokaliteter"
            else:
                stats_text = (
                    f"Afstandsstatistik (lokalitet-GVFK kombinationer):\n"
                    f"Antal kombinationer: {all_stats['Count']:,}\n"
                    f"Unikke lokaliteter: {unique_sites:,}\n"
                    f"Min: {all_stats['Min']:.0f}m, Max: {all_stats['Max']:.0f}m*\n"
                    f"Median: {all_stats['Median']:.0f}m, Gennemsnit: {all_stats['Mean']:.0f}m\n"
                    f"*Afstande >20km grupperet som 20km"
                )
                title_main = "Afstande mellem lokalitet-GVFK kombinationer og nærmeste kontaktzone"
                title_sub = f"{unique_sites:,} unikke lokaliteter i {all_stats['Count']:,} kombinationer"
                ax1_ylabel = "Antal kombinationer"

            ax1.text(0.99, 0.85, stats_text, transform=ax1.transAxes,
                    verticalalignment="top", horizontalalignment="right",
                    bbox=dict(boxstyle="round", facecolor="white", alpha=0.9), fontsize=9)

            # Add note about data
            note_text = ""
            if analysis_type == "unikke lokaliteter":
                note_text = "\nKun den korteste afstand for hver unik lokalitet er medtaget."
            else:
                note_text = f"\nViser alle lokalitet-GVFK kombinationer (én lokalitet kan forekomme i flere GVFK)."
                note_text += f"\n{unique_sites:,} unikke lokaliteter fordelt på {all_stats['Count']:,} kombinationer."
            note_text += f"\nAfstande >20km ({distances_over_20k} entries) grupperet som 20km."
            
            ax1.text(0.02, 0.02, note_text, transform=ax1.transAxes,
                    verticalalignment="bottom", horizontalalignment="left",
                    bbox=dict(boxstyle="round", facecolor="white", alpha=0.9), fontsize=10)

            # Add secondary y-axis with percentages
            ax2 = ax1.twinx()
            ax2.set_ylim(ax1.get_ylim())
            ax2.set_ylabel("Procent af lokaliteter" if analysis_type == "unikke lokaliteter" else "Procent af kombinationer", fontsize=12)
            ax2.yaxis.set_major_formatter(plt.FuncFormatter(lambda y, _: "{:.1%}".format(y / len(df))))

    # plt.title(f"{title_main}\n{title_sub}\nmed fremhævede tærskelværdier (afstande >20km grupperet)",
    #              fontsize=14, pad=20)
            ax1.set_xlabel("Afstand (meter) - maksimum 20.000m", fontsize=12)
            ax1.set_ylabel(ax1_ylabel, fontsize=12)
            ax1.grid(True, alpha=0.3)

            # Add site type legend if we have type information
            if "Site_Type" in df.columns:
                site_type_elements = [
                    Patch(facecolor=colors["v1"], label=f"V1 kun (n={len(v1_only_data)})"),
                    Patch(facecolor=colors["v2"], label=f"V2 kun (n={len(v2_only_data)})"),
                    Patch(facecolor=colors["v1v2"], label=f"V1 og V2 (n={len(both_data)})"),
                ]
                ax1.legend(handles=site_type_elements, loc="upper right", framealpha=0.9,
                          fontsize=10, title="Lokalitetstyper")

            plt.tight_layout()
            plt.savefig(os.path.join(figures_path, f'distance_histogram_thresholds_{filename_suffix}.png'),
                       dpi=300, bbox_inches="tight")
            plt.close()

            # Create CDF
            fig, ax = plt.subplots(figsize=(15, 10))
            sorted_distances = np.sort(df["Distance_to_River_m"])
            cumulative = np.arange(1, len(sorted_distances) + 1) / len(sorted_distances)
            
            ax.plot(sorted_distances, cumulative, "k-", linewidth=3, label="Kumulativ fordeling")

            # Add threshold lines to CDF
            for i, threshold in enumerate(thresholds):
                ax.axvline(threshold, color=threshold_colors[i], linestyle="-",
                          alpha=0.8, linewidth=2, label=f"{threshold}m: {percentages[i]:.1f}%")
                y_val = (df["Distance_to_River_m"] <= threshold).sum() / len(df)
                ax.axhline(y_val, color=threshold_colors[i], linestyle=":", alpha=0.5)
                ax.text(threshold * 1.05, y_val, f"{y_val * 100:.1f}%",
                       verticalalignment="bottom", horizontalalignment="left",
                       color=threshold_colors[i], fontweight="bold")

            ax.grid(True, alpha=0.3)
            
            if analysis_type == "unikke lokaliteter":
                cdf_title = "Kumulativ fordeling: Unikke lokaliteter\nÉn lokalitet per site (minimum afstand)"
                cdf_ylabel = "Kumulativ andel af lokaliteter"
            else:
                cdf_title = f"Kumulativ fordeling: Lokalitet-GVFK kombinationer\n{unique_sites:,} unikke lokaliteter i {all_stats['Count']:,} kombinationer"
                cdf_ylabel = "Kumulativ andel af kombinationer"
            
    # ax.set_title(cdf_title, fontsize=14, pad=20)
            ax.set_xlabel("Afstand (meter)", fontsize=12)
            ax.set_ylabel(cdf_ylabel, fontsize=12)
            
            ax.text(0.02, 0.02, note_text, transform=ax.transAxes,
                   verticalalignment="bottom", horizontalalignment="left",
                   bbox=dict(boxstyle="round", facecolor="white", alpha=0.9), fontsize=10)

            handles, labels = ax.get_legend_handles_labels()
            by_label = dict(zip(labels, handles))
            ax.legend(by_label.values(), by_label.keys(), loc="lower right", framealpha=0.9, fontsize=11)

            plt.tight_layout()
            plt.savefig(os.path.join(figures_path, f'distance_cdf_thresholds_{filename_suffix}.png'),
                       dpi=300, bbox_inches="tight")
            plt.close()

        except Exception as e:
            print(f"    ⚠ Error creating histogram for {analysis_type}: {e}")


################################################################################
# STEP 5: RISK ASSESSMENT PLOTS
################################################################################

def create_step5_plots():
    """Create all Step 5 risk assessment visualizations."""
    from config import get_output_path, get_visualization_path

    figures_path = get_visualization_path("step5")

    # Load Step 5b compound-specific results (PRE-filter)
    compound_path = get_output_path("step5b_compound_combinations")
    if not os.path.exists(compound_path):
        print("  ⚠ Step 5b compound data not found")
        return

    compound_df = pd.read_csv(compound_path)

    # 1. Compound category boxplot
    create_compound_category_boxplot(compound_df, figures_path)
    print("  ✓ Compound category boxplot created")

    # 2. Top activities and branches
    create_top_activities_chart(compound_df, figures_path)
    create_top_branches_chart(compound_df, figures_path)
    print("  ✓ Top activities/branches charts created")

    # 3. Threshold comparison
    create_threshold_comparison_chart(compound_df, figures_path)
    print("  ✓ Threshold comparison chart created")

    # 4. Category frequency
    create_category_frequency_chart(compound_df, figures_path)
    print("  ✓ Category frequency chart created")

    # 5. Landfill analysis
    create_landfill_analysis_plots(compound_df, figures_path)
    print("  ✓ Landfill analysis plots created")

    # 6. Step 5a vs 5b comparison
    create_step5_comparison_plot(figures_path)
    print("  ✓ Step 5a vs 5b comparison created")


def create_compound_category_boxplot(compound_df, figures_path):
    """
    Create boxplot showing distance distribution by compound category.
    Colored by occurrence count - reproduces the plot from your report.
    """
    if 'Qualifying_Category' not in compound_df.columns:
        return

    # Calculate statistics per category
    category_stats = compound_df.groupby('Qualifying_Category').agg({
        'Distance_to_River_m': ['count', 'median'],
        'Lokalitet_ID': 'nunique'
    }).reset_index()

    category_stats.columns = ['Category', 'Occurrences', 'Median_Distance', 'Unique_Sites']
    category_stats = category_stats.sort_values('Occurrences', ascending=False)

    # Create figure
    fig, ax = plt.subplots(figsize=(16, 10))

    # Prepare data for boxplot
    categories_ordered = category_stats['Category'].tolist()
    data_to_plot = [compound_df[compound_df['Qualifying_Category'] == cat]['Distance_to_River_m'].values
                    for cat in categories_ordered]

    # Create boxplot
    bp = ax.boxplot(data_to_plot, labels=categories_ordered, patch_artist=True,
                    widths=0.6, showfliers=True, flierprops=dict(marker='o', markersize=3, alpha=0.5))

    # Color by occurrence count
    occurrence_counts = category_stats['Occurrences'].values
    norm = plt.Normalize(vmin=occurrence_counts.min(), vmax=occurrence_counts.max())
    cmap = plt.cm.YlOrRd

    for patch, count in zip(bp['boxes'], occurrence_counts):
        patch.set_facecolor(cmap(norm(count)))
        patch.set_alpha(0.7)

    # Add colorbar
    sm = plt.cm.ScalarMappable(cmap=cmap, norm=norm)
    sm.set_array([])
    cbar = plt.colorbar(sm, ax=ax, pad=0.01)
    cbar.set_label('Antal forekomster', fontweight='bold', fontsize=12)

    # Add labels with site counts and occurrences
    labels_with_counts = [f"{cat}\n({stats['Unique_Sites']} sites, {stats['Occurrences']} occur.)"
                          for cat, (_, stats) in zip(categories_ordered, category_stats.iterrows())]
    ax.set_xticklabels(labels_with_counts, rotation=45, ha='right', fontsize=10)

    # Add summary text box
    total_categories = len(categories_ordered)
    total_sites = compound_df['Lokalitet_ID'].nunique()
    total_occurrences = len(compound_df)
    avg_occur_per_site = total_occurrences / total_sites

    summary_text = f"Kategorier: {total_categories}\n"
    summary_text += f"Unikke sites: {total_sites:,}\n"
    summary_text += f"Total forekomster: {total_occurrences:,}\n"
    summary_text += f"Gns. forekomster/site: {avg_occur_per_site:.1f}"

    ax.text(0.02, 0.98, summary_text, transform=ax.transAxes,
            verticalalignment='top', fontsize=11,
            bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))

    ax.set_ylabel('Afstand til vandløb (meter)', fontweight='bold', fontsize=12)
    # ax.set_title('Distance Distribution by Compound Category (Colored by Occurrence Count)',
    #             fontweight='bold', fontsize=14, pad=15)
    
    # Ensure all spines are visible
    for spine in ax.spines.values():
        spine.set_visible(True)
        spine.set_linewidth(1)

    plt.tight_layout()
    plt.savefig(os.path.join(figures_path, 'compound_category_distance_boxplot.png'), facecolor='white')
    plt.close()


def create_top_activities_chart(compound_df, figures_path):
    """Create horizontal bar chart of top 15 activities (split on semicolons)."""
    if 'Lokalitetensaktivitet' not in compound_df.columns:
        return

    # Split on semicolons and count individual activities
    all_activities = []
    for val in compound_df['Lokalitetensaktivitet'].dropna():
        activities = [a.strip() for a in str(val).split(';') if a.strip()]
        all_activities.extend(activities)
    
    activity_counts = pd.Series(all_activities).value_counts().head(15)
    
    if len(activity_counts) == 0:
        return

    fig, ax = plt.subplots(figsize=(12, 10))

    # Single professional color
    bars = ax.barh(range(len(activity_counts)), activity_counts.values, 
                   color='#4A90D9', edgecolor='white', linewidth=1)

    # Add value labels
    for i, (activity, count) in enumerate(activity_counts.items()):
        ax.text(count, i, f'  {count:,}', va='center', ha='left', fontweight='bold', fontsize=12)

    ax.set_yticks(range(len(activity_counts)))
    ax.set_yticklabels(activity_counts.index, fontsize=11)
    ax.set_xlabel('Antal forekomster', fontweight='bold', fontsize=14)
    # ax.set_title('Top 15 lokalitetsaktiviteter',
    #             fontweight='bold', fontsize=18, pad=15)

    # Add summary
    ax.text(0.98, 0.02, f'Total: {len(all_activities):,} aktivitetsforekomster',
            transform=ax.transAxes, verticalalignment='bottom', horizontalalignment='right',
            bbox=dict(boxstyle='round', facecolor='white', edgecolor='#4A90D9', alpha=0.9), fontsize=11)

    plt.tight_layout()
    plt.savefig(os.path.join(figures_path, 'top_15_activities.png'), facecolor='white')
    plt.close()


def create_top_branches_chart(compound_df, figures_path):
    """Create horizontal bar chart of top 15 branches (split on semicolons)."""
    if 'Lokalitetensbranche' not in compound_df.columns:
        return

    # Split on semicolons and count individual branches
    all_branches = []
    for val in compound_df['Lokalitetensbranche'].dropna():
        branches = [b.strip() for b in str(val).split(';') if b.strip()]
        all_branches.extend(branches)
    
    branch_counts = pd.Series(all_branches).value_counts().head(15)
    
    if len(branch_counts) == 0:
        return

    fig, ax = plt.subplots(figsize=(12, 10))

    # Single professional color (different from activities)
    bars = ax.barh(range(len(branch_counts)), branch_counts.values, 
                   color='#5BA55B', edgecolor='white', linewidth=1)

    # Add value labels
    for i, (branch, count) in enumerate(branch_counts.items()):
        ax.text(count, i, f'  {count:,}', va='center', ha='left', fontweight='bold', fontsize=12)

    ax.set_yticks(range(len(branch_counts)))
    ax.set_yticklabels(branch_counts.index, fontsize=11)
    ax.set_xlabel('Antal forekomster', fontweight='bold', fontsize=14)
    # ax.set_title('Top 15 lokalitetsbrancer',
    #             fontweight='bold', fontsize=18, pad=15)

    # Add summary
    ax.text(0.98, 0.02, f'Total: {len(all_branches):,} brancheforekomster',
            transform=ax.transAxes, verticalalignment='bottom', horizontalalignment='right',
            bbox=dict(boxstyle='round', facecolor='white', edgecolor='#5BA55B', alpha=0.9), fontsize=11)

    plt.tight_layout()
    plt.savefig(os.path.join(figures_path, 'top_15_branches.png'), facecolor='white')
    plt.close()


def create_threshold_comparison_chart(compound_df, figures_path):
    """Create bar chart comparing thresholds used for different categories."""
    if 'Qualifying_Category' not in compound_df.columns or 'Category_Threshold_m' not in compound_df.columns:
        return

    # Get unique category-threshold pairs
    threshold_data = compound_df[['Qualifying_Category', 'Category_Threshold_m']].drop_duplicates()
    threshold_data = threshold_data.sort_values('Category_Threshold_m', ascending=False)

    fig, ax = plt.subplots(figsize=(12, 8))

    colors = ['#FF6B6B' if t < 500 else '#4ECDC4' if t == 500 else '#95E1D3'
              for t in threshold_data['Category_Threshold_m']]

    bars = ax.barh(threshold_data['Qualifying_Category'],
                   threshold_data['Category_Threshold_m'],
                   color=colors, edgecolor='black', linewidth=1.5)

    # Add threshold values
    for i, (cat, thresh) in enumerate(zip(threshold_data['Qualifying_Category'],
                                          threshold_data['Category_Threshold_m'])):
        ax.text(thresh, i, f'  {thresh:.0f}m', va='center', ha='left',
               fontweight='bold', fontsize=10)

    # Add 500m reference line
    ax.axvline(x=500, color='red', linestyle='--', linewidth=2, alpha=0.7,
              label='Generel tærskel (500m)')

    ax.set_xlabel('Afstandstærskel (m)', fontweight='bold', fontsize=12)
    ax.set_ylabel('Stofkategori', fontweight='bold', fontsize=12)
    # ax.set_title('Compound-Specific Distance Thresholds (Step 5b)',
    #             fontweight='bold', fontsize=14, pad=15)
    ax.legend(fontsize=11)
    ax.grid(axis='x', alpha=0.3)

    plt.tight_layout()
    plt.savefig(os.path.join(figures_path, 'threshold_comparison.png'))
    plt.close()


def create_category_frequency_chart(compound_df, figures_path):
    """Create chart showing frequency of each category."""
    if 'Qualifying_Category' not in compound_df.columns:
        return

    category_counts = compound_df['Qualifying_Category'].value_counts()

    fig, ax = plt.subplots(figsize=(12, 8))

    colors = plt.cm.Set3(range(len(category_counts)))
    bars = ax.bar(range(len(category_counts)), category_counts.values,
                  color=colors, edgecolor='black', linewidth=1.5)

    ax.set_xticks(range(len(category_counts)))
    ax.set_xticklabels(category_counts.index, rotation=45, ha='right', fontsize=10)
    ax.set_ylabel('Antal Lokalitet-GVFK-Stof kombinationer', fontweight='bold', fontsize=12)
    # ax.set_title('Compound Category Frequency (Step 5b)',
    #             fontweight='bold', fontsize=14, pad=15)
    ax.grid(axis='y', alpha=0.3)

    # Add value labels on bars
    for bar, count in zip(bars, category_counts.values):
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height,
               f'{count:,}', ha='center', va='bottom', fontweight='bold', fontsize=9)

    plt.tight_layout()
    plt.savefig(os.path.join(figures_path, 'category_frequency.png'))
    plt.close()

def create_landfill_analysis_plots(compound_df, figures_path):
    """Create plots analyzing landfill-specific thresholds and overrides."""
    if 'Landfill_Override_Applied' not in compound_df.columns:
        print("    ⚠ No landfill override data found")
        return

    # Landfill threshold comparison
    landfill_thresholds = {
        "BTXER": (250, 70),
        "KLOREREDE_OPLØSNINGSMIDLER": (500, 100),
        "PHENOLER": (250, 35),
        "PESTICIDER": (500, 180),
        "UORGANISKE_FORBINDELSER": (250, 50),
    }

    fig, ax = plt.subplots(figsize=(12, 8))

    categories = list(landfill_thresholds.keys())
    regular_thresh = [landfill_thresholds[cat][0] for cat in categories]
    landfill_thresh = [landfill_thresholds[cat][1] for cat in categories]

    x = np.arange(len(categories))
    width = 0.35

    bars1 = ax.bar(x - width/2, regular_thresh, width, label='Standard tærskel',
                   color='#4ECDC4', edgecolor='black')
    bars2 = ax.bar(x + width/2, landfill_thresh, width, label='Losseplads tærskel',
                   color='#FF6B6B', edgecolor='black')

    ax.set_xticks(x)
    ax.set_xticklabels(categories, rotation=45, ha='right', fontsize=10)
    ax.set_ylabel('Afstandstærskel (m)', fontweight='bold', fontsize=12)
    # ax.set_title('Landfill-Specific Thresholds vs Regular Thresholds',
    #             fontweight='bold', fontsize=14, pad=15)
    ax.legend(fontsize=11)
    ax.grid(axis='y', alpha=0.3)

    # Add value labels
    for bars in [bars1, bars2]:
        for bar in bars:
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height,
                   f'{height:.0f}m', ha='center', va='bottom', fontsize=9)

    plt.tight_layout()
    plt.savefig(os.path.join(figures_path, 'landfill_threshold_comparison.png'))
    plt.close()

    # Landfill override impact
    override_count = compound_df['Landfill_Override_Applied'].sum()
    no_override_count = (~compound_df['Landfill_Override_Applied']).sum()

    fig, ax = plt.subplots(figsize=(8, 8))

    sizes = [override_count, no_override_count]
    labels = [f'Losseplads-regel\nAnvendt\n({override_count:,})',
              f'Ingen regel\n({no_override_count:,})']
    colors = ['#FF6B6B', '#95E1D3']
    explode = (0.1, 0)

    ax.pie(sizes, explode=explode, labels=labels, colors=colors, autopct='%1.1f%%',
           shadow=True, startangle=90, textprops={'fontsize': 11, 'fontweight': 'bold'})
    # ax.set_title('Landfill Override Impact on Site-GVFK Combinations',
    #             fontweight='bold', fontsize=14, pad=15)

    plt.tight_layout()
    plt.savefig(os.path.join(figures_path, 'landfill_override_impact.png'))
    plt.close()


def create_step5_comparison_plot(figures_path):
    """Create plot comparing Step 5a (general) vs Step 5b (compound-specific)."""
    from config import get_output_path

    # Load both datasets
    step5a_path = get_output_path("step5_high_risk_sites")
    step5b_path = get_output_path("step5b_compound_combinations")

    if not os.path.exists(step5a_path) or not os.path.exists(step5b_path):
        print("    ⚠ Cannot create 5a vs 5b comparison - missing data")
        return

    step5a_df = pd.read_csv(step5a_path)
    step5b_df = pd.read_csv(step5b_path)

    # Calculate statistics
    step5a_sites = step5a_df['Lokalitet_ID'].nunique()
    step5a_gvfk = step5a_df['GVFK'].nunique()
    step5a_combinations = len(step5a_df)

    step5b_sites = step5b_df['Lokalitet_ID'].nunique()
    step5b_gvfk = step5b_df['GVFK'].nunique()
    step5b_combinations = len(step5b_df)

    # Create comparison bar chart
    fig, (ax1, ax2, ax3) = plt.subplots(1, 3, figsize=(15, 6))

    categories = ['Trin 5a\n(Generel ≤500m)', 'Trin 5b\n(Stofspecifik)']

    # Sites comparison
    ax1.bar(categories, [step5a_sites, step5b_sites], color=['#4ECDC4', '#FF6B6B'],
            edgecolor='black', linewidth=2)
    ax1.set_ylabel('Antal lokaliteter', fontweight='bold')
    ax1.set_title('Unikke lokaliteter', fontweight='bold', pad=10)
    ax1.grid(axis='y', alpha=0.3)
    for i, v in enumerate([step5a_sites, step5b_sites]):
        ax1.text(i, v, f'{v:,}', ha='center', va='bottom', fontweight='bold', fontsize=11)

    # GVFKs comparison
    ax2.bar(categories, [step5a_gvfk, step5b_gvfk], color=['#4ECDC4', '#FF6B6B'],
            edgecolor='black', linewidth=2)
    ax2.set_ylabel("Antal GVF'er", fontweight='bold')
    ax2.set_title("Påvirkede GVF'er", fontweight='bold', pad=10)
    ax2.grid(axis='y', alpha=0.3)
    for i, v in enumerate([step5a_gvfk, step5b_gvfk]):
        ax2.text(i, v, f'{v:,}', ha='center', va='bottom', fontweight='bold', fontsize=11)

    # Combinations comparison
    ax3.bar(categories, [step5a_combinations, step5b_combinations],
            color=['#4ECDC4', '#FF6B6B'], edgecolor='black', linewidth=2)
    ax3.set_ylabel('Antal kombinationer', fontweight='bold')
    ax3.set_title('Lokalitet-GVFK kombinationer', fontweight='bold', pad=10)
    ax3.grid(axis='y', alpha=0.3)
    for i, v in enumerate([step5a_combinations, step5b_combinations]):
        ax3.text(i, v, f'{v:,}', ha='center', va='bottom', fontweight='bold', fontsize=11)

    # fig.suptitle('Step 5a (General) vs Step 5b (Compound-Specific) Comparison',
    #             fontweight='bold', fontsize=16, y=1.02)

    plt.tight_layout()
    plt.savefig(os.path.join(figures_path, 'step5a_vs_step5b_comparison.png'))
    plt.close()


################################################################################
# MAIN EXECUTION
################################################################################

if __name__ == "__main__":
    create_all_risikovurdering_plots()

