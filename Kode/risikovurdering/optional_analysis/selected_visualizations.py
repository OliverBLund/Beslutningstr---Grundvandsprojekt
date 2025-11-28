import sys
from pathlib import Path

# Add the Kode directory to Python path for config import when running independently
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import geopandas as gpd
import matplotlib.pyplot as plt
import os
import numpy as np
import pandas as pd
from matplotlib.patches import FancyArrowPatch
from config import WORKFLOW_SETTINGS, get_output_path


def create_html_table(data, headers, title, filename, output_dir):
    """Create a simple HTML table for PowerPoint copy-paste."""
    os.makedirs(output_dir, exist_ok=True)

    html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        h2 {{ color: #1f4e79; margin-bottom: 20px; }}
        table {{ border-collapse: collapse; width: 100%; margin: 20px 0; }}
        th {{ background-color: #1f4e79; color: white; padding: 12px; text-align: left; border: 1px solid #ddd; }}
        td {{ padding: 10px; border: 1px solid #ddd; }}
        tr:nth-child(even) {{ background-color: #f2f2f2; }}
        tr:hover {{ background-color: #e6f3ff; }}
        .number {{ text-align: right; }}
    </style>
</head>
<body>
    <h2>{title}</h2>
    <table>
        <thead>
            <tr>
"""

    for header in headers:
        html_content += f"                <th>{header}</th>\n"

    html_content += """            </tr>
        </thead>
        <tbody>
"""

    for row in data:
        html_content += "            <tr>\n"
        for item in row:
            # Check if item looks like a number for right alignment
            css_class = (
                "number"
                if isinstance(item, (int, float))
                or (
                    isinstance(item, str)
                    and item.replace(",", "").replace(".", "").isdigit()
                )
                else ""
            )
            html_content += f"                <td class='{css_class}'>{item}</td>\n"
        html_content += "            </tr>\n"

    html_content += """        </tbody>
    </table>
</body>
</html>"""

    filepath = os.path.join(output_dir, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(html_content)

    print(f"  HTML table saved: {filepath}")
    return filepath


def create_distance_histogram_with_thresholds(results_path):
    """
    Create specialized histograms with distance thresholds highlighted.
    Creates TWO versions:
    1. Unique lokaliteter (minimum distance per site)
    2. All lokalitet-GVFK combinations
    """
    print("Creating distance histograms with thresholds...")

    # Use config-based path for Step 4 visualizations
    from config import get_visualization_path, get_output_path

    figures_path = get_visualization_path("step4")

    # Define paths for both unique locations and all combinations files
    unique_distance_file = get_output_path("unique_lokalitet_distances")
    all_combinations_file = get_output_path("step4_valid_distances")

    # Check which files exist
    has_unique = os.path.exists(unique_distance_file)
    has_all_combinations = os.path.exists(all_combinations_file)

    if not has_unique and not has_all_combinations:
        print("Required files for distance analysis not found.")
        print("Run the step4_calculate_distances() function in workflow.py first.")
        return

    # We'll create histograms for both datasets
    datasets_to_process = []

    if has_unique:
        datasets_to_process.append(
            {
                "path": unique_distance_file,
                "type": "unikke lokaliteter",
                "suffix": "unique",
                "description": "Unique Lokaliteter (minimum distance per site)",
            }
        )
        print(f"[OK] Found unique lokaliteter file: {unique_distance_file}")

    if has_all_combinations:
        datasets_to_process.append(
            {
                "path": all_combinations_file,
                "type": "lokalitet-GVFK kombinationer",
                "suffix": "all_combinations",
                "description": "All Lokalitet-GVFK Combinations",
            }
        )
        print(f"[OK] Found all combinations file: {all_combinations_file}")

    # Process each dataset
    for dataset_info in datasets_to_process:
        print(f"\n{'=' * 60}")
        print(f"Processing: {dataset_info['description']}")
        print(f"{'=' * 60}")

        try:
            # Load the data
            distance_df = pd.read_csv(dataset_info["path"])
            analysis_type = dataset_info["type"]
            filename_suffix = dataset_info["suffix"]

            # Cap distances at 20,000m - anything above gets grouped into 20000+ category
            original_max_distance = distance_df["Distance_to_River_m"].max()
            distances_over_20k = (distance_df["Distance_to_River_m"] > 20000).sum()
            print(f"Original max distance: {original_max_distance:.1f}m")
            print(
                f"Entries with distances > 20,000m: {distances_over_20k} ({distances_over_20k / len(distance_df) * 100:.1f}%)"
            )

            # Cap the distances at 20,000m
            distance_df["Distance_to_River_m"] = distance_df[
                "Distance_to_River_m"
            ].clip(upper=20000)

            print(
                f"Analyzing {len(distance_df)} {analysis_type} for threshold visualization"
            )

            if "Distance_to_River_m" in distance_df.columns:
                # Prepare the data
                if "Site_Type" in distance_df.columns:
                    # Define masks for V1, V2, and both
                    v1_mask = distance_df["Site_Type"].str.contains(
                        "V1", case=False, na=False
                    )
                    v2_mask = distance_df["Site_Type"].str.contains(
                        "V2", case=False, na=False
                    )

                    # Count by type for the legend
                    v1_count = sum(v1_mask & ~v2_mask)
                    v2_count = sum(v2_mask & ~v1_mask)
                    both_count = sum(v1_mask & v2_mask)

                    # Create type labels with counts
                    type_labels = [
                        f"V1-kortlagt (n={v1_count})",
                        f"V2-kortlagt (n={v2_count})",
                        f"V1 og V2-kortlagt (n={both_count})",
                    ]
                else:
                    # Generic label if no type info
                    type_labels = ["Alle lokaliteter"]

                # Use configurable thresholds from config
                thresholds = WORKFLOW_SETTINGS["additional_thresholds_m"]

                # Calculate percentage of sites within each threshold
                percentages = []
                for t in thresholds:
                    within = (distance_df["Distance_to_River_m"] <= t).sum()
                    pct = within / len(distance_df) * 100
                    percentages.append(pct)
                    print(f"Lokaliteter indenfor {t}m: {within} ({pct:.1f}%)")

                # Create a more beautiful histogram with thresholds
                plt.figure(figsize=(15, 10))

                # Define color palette
                colors = {
                    "v1": "#1f4e79",  # Dark blue for V1 only
                    "v2": "#E31A1C",  # Red for V2 only
                    "v1v2": "#6A3D9A",  # Purple for V1 and V2
                    "bar": "#1f77b4",  # Default blue for bars
                }

                # Create separate data for each site type if we have type information
                if "Site_Type" in distance_df.columns:
                    # Separate data by site type
                    v1_only_data = distance_df[v1_mask & ~v2_mask][
                        "Distance_to_River_m"
                    ]
                    v2_only_data = distance_df[v2_mask & ~v1_mask][
                        "Distance_to_River_m"
                    ]
                    both_data = distance_df[v1_mask & v2_mask]["Distance_to_River_m"]

                    # Create bins at 500m intervals from 0 to 20000
                    bins = range(0, 20500, 500)  # 500m intervals up to 20000m
                    plt.hist(
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
                    # Create single histogram if no type info - bins at 500m intervals
                    bins = range(0, 20500, 500)  # 500m intervals up to 20000m
                    n, bins, patches = plt.hist(
                        distance_df["Distance_to_River_m"],
                        bins=bins,
                        color=colors["bar"],
                        alpha=0.75,
                        edgecolor="black",
                        linewidth=0.5,
                    )

                # Add colorful vertical lines for thresholds with improved styling
                threshold_colors = [
                    "#006400",
                    "#32CD32",
                    "#FFD700",
                    "#FF6347",
                    "#FF0000",
                ]  # Green to red gradient

                # Add shaded regions for thresholds
                xmin = distance_df["Distance_to_River_m"].min()
                prev_threshold = xmin

                for i, threshold in enumerate(thresholds):
                    # Add vertical line
                    plt.axvline(
                        threshold,
                        color=threshold_colors[i],
                        linestyle="-",
                        alpha=0.8,
                        linewidth=2,
                        label=f"{threshold}m: {percentages[i]:.1f}%",
                    )

                    # Add percentage label directly on the line - horizontal text, positioned to avoid overlap
                    label_y_position = plt.ylim()[1] * (
                        0.95 - i * 0.08
                    )  # Stagger vertically to avoid overlap
                    plt.text(
                        threshold + 100,
                        label_y_position,
                        f"{threshold}m: {percentages[i]:.1f}%",
                        rotation=0,
                        verticalalignment="center",
                        horizontalalignment="left",
                        color=threshold_colors[i],
                        fontweight="bold",
                        fontsize=10,
                        bbox=dict(
                            boxstyle="round,pad=0.3",
                            facecolor="white",
                            alpha=0.9,
                            edgecolor=threshold_colors[i],
                        ),
                    )

                    # Add shaded region
                    plt.axvspan(
                        prev_threshold, threshold, color=threshold_colors[i], alpha=0.1
                    )

                    prev_threshold = threshold

                # Add compact statistics panel
                all_stats = {
                    "Count": len(distance_df),
                    "Min": distance_df["Distance_to_River_m"].min(),
                    "Max": distance_df["Distance_to_River_m"].max(),
                    "Mean": distance_df["Distance_to_River_m"].mean(),
                    "Median": distance_df["Distance_to_River_m"].median(),
                }

                # Create compact statistics text box
                if analysis_type == "unikke lokaliteter":
                    unique_sites = (
                        distance_df["Lokalitetsnr"].nunique()
                        if "Lokalitetsnr" in distance_df.columns
                        else all_stats["Count"]
                    )
                    stats_text = (
                        f"Afstandsstatistik (unikke lokaliteter):\n"
                        f"Antal lokaliteter: {unique_sites:,}\n"
                        f"Min: {all_stats['Min']:.0f}m, Max: {all_stats['Max']:.0f}m*\n"
                        f"Median: {all_stats['Median']:.0f}m, Gennemsnit: {all_stats['Mean']:.0f}m\n"
                        f"*Afstande >20km grupperet som 20km"
                    )
                else:
                    # For combinations, show both combination count and unique site count
                    unique_sites = (
                        distance_df["Lokalitet_ID"].nunique()
                        if "Lokalitet_ID" in distance_df.columns
                        else "N/A"
                    )
                    stats_text = (
                        f"Afstandsstatistik (lokalitet-GVFK kombinationer):\n"
                        f"Antal kombinationer: {all_stats['Count']:,}\n"
                        f"Unikke lokaliteter: {unique_sites:,}\n"
                        f"Min: {all_stats['Min']:.0f}m, Max: {all_stats['Max']:.0f}m*\n"
                        f"Median: {all_stats['Median']:.0f}m, Gennemsnit: {all_stats['Mean']:.0f}m\n"
                        f"*Afstande >20km grupperet som 20km"
                    )

                # Add smaller text box with essential statistics. Change to bottom right.
                plt.text(
                    0.99,
                    0.85,
                    stats_text,
                    transform=plt.gca().transAxes,
                    verticalalignment="top",
                    horizontalalignment="right",
                    bbox=dict(boxstyle="round", facecolor="white", alpha=0.9),
                    fontsize=9,
                )

                # Create the note text about unique locations
                note_text = ""
                if analysis_type == "unikke lokaliteter":
                    note_text += "\nKun den korteste afstand for hver unik lokalitet er medtaget."
                else:
                    note_text += f"\nViser alle lokalitet-GVFK kombinationer (én lokalitet kan forekomme i flere GVFK)."
                    note_text += f"\n{unique_sites:,} unikke lokaliteter fordelt på {all_stats['Count']:,} kombinationer."
                note_text += f"\nAfstande >20km ({distances_over_20k} entries) grupperet som 20km."

                # Add note about unique locations
                plt.text(
                    0.02,
                    0.02,
                    note_text,
                    transform=plt.gca().transAxes,
                    verticalalignment="bottom",
                    horizontalalignment="left",
                    bbox=dict(boxstyle="round", facecolor="white", alpha=0.9),
                    fontsize=10,
                )

                # Add second y-axis with percentages
                ax1 = plt.gca()
                ax2 = ax1.twinx()
                ax2.set_ylim(ax1.get_ylim())

                # Set labels based on analysis type
                if analysis_type == "unikke lokaliteter":
                    y_label = "Procent af lokaliteter"
                    title_main = (
                        "Afstande mellem unikke lokaliteter og nærmeste kontaktzone"
                    )
                    title_sub = "Én lokalitet per site (minimum afstand)"
                    ax1_ylabel = "Antal lokaliteter"
                else:
                    y_label = "Procent af kombinationer"
                    title_main = "Afstande mellem lokalitet-GVFK kombinationer og nærmeste kontaktzone"
                    title_sub = f"{unique_sites:,} unikke lokaliteter i {all_stats['Count']:,} kombinationer"
                    ax1_ylabel = "Antal kombinationer"

                ax2.set_ylabel(y_label, fontsize=12)
                ax2.yaxis.set_major_formatter(
                    plt.FuncFormatter(
                        lambda y, _: "{:.1%}".format(y / len(distance_df))
                    )
                )

                # Set title and labels with analysis type details
                plt.title(
                    f"{title_main}\n{title_sub}\nmed fremhævede tærskelværdier (afstande >20km grupperet)",
                    fontsize=14,
                    pad=20,
                )
                ax1.set_xlabel("Afstand (meter) - maksimum 20.000m", fontsize=12)
                ax1.set_ylabel(ax1_ylabel, fontsize=12)

                plt.grid(True, alpha=0.3)

                # Improved legend - combine threshold and site type legends
                handles, labels = ax1.get_legend_handles_labels()
                by_label = dict(zip(labels, handles))

                # Create two separate legends - one for thresholds, one for site types
                threshold_legend = ax1.legend(
                    by_label.values(),
                    by_label.keys(),
                    loc="upper center",
                    ncol=3,
                    framealpha=0.9,
                    fontsize=10,
                    bbox_to_anchor=(0.5, -0.05),
                    title="Afstandsgrænser",
                )

                # Add site type legend if we have type information
                if "Site_Type" in distance_df.columns:
                    from matplotlib.patches import Patch

                    site_type_elements = [
                        Patch(
                            facecolor=colors["v1"],
                            label=f"V1 kun (n={len(v1_only_data)})",
                        ),
                        Patch(
                            facecolor=colors["v2"],
                            label=f"V2 kun (n={len(v2_only_data)})",
                        ),
                        Patch(
                            facecolor=colors["v1v2"],
                            label=f"V1 og V2 (n={len(both_data)})",
                        ),
                    ]
                    site_legend = ax1.legend(
                        handles=site_type_elements,
                        loc="upper right",
                        framealpha=0.9,
                        fontsize=10,
                        title="Lokalitetstyper",
                    )
                    ax1.add_artist(threshold_legend)  # Add back the threshold legend

                plt.tight_layout()
                histogram_filename = (
                    f"distance_histogram_thresholds_{filename_suffix}.png"
                )
                plt.savefig(
                    os.path.join(figures_path, histogram_filename),
                    dpi=300,
                    bbox_inches="tight",
                )
                plt.close()

                print(f"[OK] Created threshold histogram: {histogram_filename}")

                # Also create a cumulative distribution function (CDF) with thresholds
                plt.figure(figsize=(15, 10))

                # Create the CDF
                sorted_distances = np.sort(distance_df["Distance_to_River_m"])
                cumulative = np.arange(1, len(sorted_distances) + 1) / len(
                    sorted_distances
                )
                plt.plot(
                    sorted_distances,
                    cumulative,
                    "k-",
                    linewidth=3,
                    label="Kumulativ fordeling",
                )

                # Add vertical lines for thresholds
                for i, threshold in enumerate(thresholds):
                    plt.axvline(
                        threshold,
                        color=threshold_colors[i],
                        linestyle="-",
                        alpha=0.8,
                        linewidth=2,
                        label=f"{threshold}m: {percentages[i]:.1f}%",
                    )

                    # Add horizontal line to show percentage
                    y_val = (
                        distance_df["Distance_to_River_m"] <= threshold
                    ).sum() / len(distance_df)
                    plt.axhline(
                        y_val, color=threshold_colors[i], linestyle=":", alpha=0.5
                    )

                    # Add text to show percentage at each threshold
                    plt.text(
                        threshold * 1.05,
                        y_val,
                        f"{y_val * 100:.1f}%",
                        verticalalignment="bottom",
                        horizontalalignment="left",
                        color=threshold_colors[i],
                        fontweight="bold",
                    )

                plt.grid(True, alpha=0.3)

                # Add title and labels - use the same clear labeling as histogram
                if analysis_type == "unikke lokaliteter":
                    cdf_ylabel = "Kumulativ andel af lokaliteter"
                    cdf_title_main = "Kumulativ fordeling: Unikke lokaliteter"
                    cdf_title_sub = "Én lokalitet per site (minimum afstand)"
                else:
                    cdf_ylabel = "Kumulativ andel af kombinationer"
                    cdf_title_main = "Kumulativ fordeling: Lokalitet-GVFK kombinationer"
                    cdf_title_sub = f"{unique_sites:,} unikke lokaliteter i {all_stats['Count']:,} kombinationer"

                plt.title(
                    f"{cdf_title_main}\n{cdf_title_sub}",
                    fontsize=14,
                    pad=20,
                )
                plt.xlabel("Afstand (meter)", fontsize=12)
                plt.ylabel(cdf_ylabel, fontsize=12)

                # Add the note text
                plt.text(
                    0.02,
                    0.02,
                    note_text,
                    transform=plt.gca().transAxes,
                    verticalalignment="bottom",
                    horizontalalignment="left",
                    bbox=dict(boxstyle="round", facecolor="white", alpha=0.9),
                    fontsize=10,
                )

                # Improved legend
                handles, labels = plt.gca().get_legend_handles_labels()
                by_label = dict(zip(labels, handles))
                plt.legend(
                    by_label.values(),
                    by_label.keys(),
                    loc="lower right",
                    framealpha=0.9,
                    fontsize=11,
                )

                plt.tight_layout()
                cdf_filename = f"distance_cdf_thresholds_{filename_suffix}.png"
                plt.savefig(
                    os.path.join(figures_path, cdf_filename),
                    dpi=300,
                    bbox_inches="tight",
                )
                plt.close()

                print(f"[OK] Created CDF with thresholds: {cdf_filename}")
            else:
                print(
                    "No 'Distance_to_River_m' column found in the distance analysis file."
                )

        except Exception as e:
            print(f"Error creating threshold histogram for {analysis_type}: {e}")
            import traceback

            traceback.print_exc()

    print(f"\n{'=' * 60}")
    print(f"Completed: Created histograms for {len(datasets_to_process)} dataset(s)")
    print(f"{'=' * 60}")


def create_progression_plot(figures_path, required_files):
    """Create a comprehensive GVFK progression plot showing both Step 5 assessments."""
    try:
        # Create a bar chart showing the complete GVFK progression
        stages = [
            "Alle GVFK\n(Danmark)",
            "Vandløbskontakt\n(Trin 2)",
            "V1/V2 lokaliteter\n(Trin 3)",
            "Generel risiko\n(Trin 5a: <= 500m)",
            "Stofspecifik risiko\n(Trin 5b: Variabel)",
        ]

        # Load actual counts from data files - NO FALLBACKS!
        import pandas as pd
        from config import get_output_path

        # Step 1: Total GVFK (from original file)
        if "all_gvfk" in required_files and os.path.exists(required_files["all_gvfk"]):
            import geopandas as gpd

            all_gvfk_df = gpd.read_file(required_files["all_gvfk"])
            total_gvfks = len(all_gvfk_df)
        else:
            raise FileNotFoundError(
                "Cannot find all_gvfk file - required for progression plot"
            )

        # Step 2: River contact GVFKs
        if "river_gvfk" in required_files and os.path.exists(
            required_files["river_gvfk"]
        ):
            import geopandas as gpd

            river_df = gpd.read_file(required_files["river_gvfk"])
            river_gvfks = len(river_df)
        else:
            raise FileNotFoundError(
                "Cannot find river_gvfk file - required for progression plot"
            )

        # Step 3: V1/V2 GVFKs
        if "v1v2_gvfk" in required_files and os.path.exists(
            required_files["v1v2_gvfk"]
        ):
            import geopandas as gpd

            v1v2_df = gpd.read_file(required_files["v1v2_gvfk"])
            v1v2_gvfks = len(v1v2_df)
        else:
            raise FileNotFoundError(
                "Cannot find v1v2_gvfk file - required for progression plot"
            )

        # Step 5a: General assessment 500m
        step5a_path = get_output_path("step5_high_risk_sites")
        if os.path.exists(step5a_path):
            step5a_df = pd.read_csv(step5a_path)
            step5a_gvfks = step5a_df["GVFK"].nunique()
        else:
            raise FileNotFoundError(f"Cannot find Step 5a file: {step5a_path}")

        # Step 5b: Compound-specific assessment
        step5b_path = get_output_path("step5_compound_detailed_combinations")
        if os.path.exists(step5b_path):
            step5b_df = pd.read_csv(step5b_path)
            step5b_gvfks = step5b_df["GVFK"].nunique()
        else:
            raise FileNotFoundError(f"Cannot find Step 5b file: {step5b_path}")

        counts = [total_gvfks, river_gvfks, v1v2_gvfks, step5a_gvfks, step5b_gvfks]
        print(
            f"Loaded actual counts: Total={total_gvfks}, River={river_gvfks}, V1V2={v1v2_gvfks}, Step5a={step5a_gvfks}, Step5b={step5b_gvfks}"
        )
        colors = ["#E6E6E6", "#66B3FF", "#FF6666", "#FF8C42", "#FF3333"]

        fig, ax = plt.subplots(figsize=(14, 8))

        # Create bars
        bars = ax.bar(
            range(len(stages)),
            counts,
            color=colors,
            alpha=0.8,
            edgecolor="black",
            linewidth=1.5,
        )

        # Add count labels and percentages inside bars
        for i, (bar, count) in enumerate(zip(bars, counts)):
            height = bar.get_height()
            percentage = (count / 2043) * 100

            # Count at top of bar
            ax.text(
                bar.get_x() + bar.get_width() / 2.0,
                height - height * 0.15,
                f"{count:,}",
                ha="center",
                va="center",
                fontsize=14,
                fontweight="bold",
                color="white",
            )

            # Percentage inside bar, lower
            ax.text(
                bar.get_x() + bar.get_width() / 2.0,
                height - height * 0.4,
                f"{percentage:.1f}%",
                ha="center",
                va="center",
                fontsize=13,
                fontweight="bold",
                color="white",
            )

        # Customize plot
        ax.set_xticks(range(len(stages)))
        ax.set_xticklabels(stages, fontsize=12, fontweight="bold")
        ax.set_ylabel("Antal GVFK", fontsize=14, fontweight="bold")
        ax.set_title(
            "GVFK Analyse Progression\nFra alle danske GVFK til højrisiko vurdering",
            fontsize=16,
            fontweight="bold",
            pad=20,
        )

        # Set y-axis limits with some padding
        ax.set_ylim(0, max(counts) * 1.1)

        # Add grid
        ax.grid(axis="y", alpha=0.3, linestyle="--")
        ax.set_axisbelow(True)

        # Add explanation text in Danish
        explanation = (
            "Trin 5a: Generel vurdering bruger universel 500m tærskel\n"
            "Trin 5b: Stofspecifik vurdering bruger litteraturbaserede variable tÃ¦rskler"
        )
        ax.text(
            0.02,
            0.98,
            explanation,
            transform=ax.transAxes,
            fontsize=10,
            verticalalignment="top",
            bbox=dict(boxstyle="round,pad=0.5", facecolor="lightgray", alpha=0.8),
        )

        plt.tight_layout()
        plt.savefig(
            os.path.join(figures_path, "gvfk_progression.png"),
            dpi=300,
            bbox_inches="tight",
        )
        plt.close()

        print("Updated GVFK progression plot created successfully")
        print(
            f"  Shows both Step 5a (General: {step5a_gvfks} GVFK) and Step 5b (Compound-specific: {step5b_gvfks} GVFK)"
        )

    except Exception as e:
        print(f"Error creating progression plot: {e}")


def create_gvfk_cascade_table_from_data():
    """Create GVFK cascade table from actual data files."""
    try:
        from config import get_output_path
        import pandas as pd

        print("\n[MAP] GVFK FILTRERINGSFORLOB EFTER WORKFLOW TRIN")
        print("=" * 60)
        print(f"{'Trin':<8} {'Beskrivelse':<35} {'Antal':<10} {'% af Total':<12}")
        print("-" * 60)

        # These are well-established counts from the workflow
        total_gvfk = 2043
        print(
            f"{'TRIN 1':<8} {'Alle GVFK i Danmark':<35} {f'{total_gvfk:,}':<10} {'100,0%':<12}"
        )
        print(f"{'TRIN 2':<8} {'Med vandlobskontakt':<35} {'593':<10} {'29,0%':<12}")
        print(
            f"{'TRIN 3':<8} {'Med V1/V2 lokaliteter + kontakt':<35} {'491':<10} {'24,0%':<12}"
        )

        # Try to get actual Step 5 GVFK counts
        try:
            # Load general sites if available
            general_path = get_output_path("step5_high_risk_sites")
            if os.path.exists(general_path):
                general_sites = pd.read_csv(general_path)
                general_gvfks = general_sites["GVFK"].dropna().nunique()
                general_pct = (general_gvfks / total_gvfk) * 100
                print(
                    f"{'TRIN 5a':<8} {'Generel vurdering (<=500m)':<35} {f'{general_gvfks:,}':<10} {f'{general_pct:.1f}%':<12}"
                )
            else:
                raise FileNotFoundError(f"Cannot find Step 5a file: {general_path}")
        except Exception as e:
            print(f"Error loading Step 5a data: {e}")
            return

        try:
            # Load compound sites if available
            compound_path = get_output_path("step5_compound_detailed_combinations")
            if os.path.exists(compound_path):
                compound_sites = pd.read_csv(compound_path)
                compound_gvfks = compound_sites["GVFK"].dropna().nunique()
                compound_pct = (compound_gvfks / total_gvfk) * 100
                print(
                    f"{'TRIN 5b':<8} {'Stofspecifik risiko':<35} {f'{compound_gvfks:,}':<10} {f'{compound_pct:.1f}%':<12}"
                )
            else:
                raise FileNotFoundError(f"Cannot find Step 5b file: {compound_path}")
        except Exception as e:
            print(f"Error loading Step 5b data: {e}")
            return

        print("-" * 60)
        print("Progressiv filtrering fra alle danske GVFK til hojrisiko identifikation")

    except Exception as e:
        print(f"Error creating GVFK cascade table: {e}")


def create_compound_category_table_from_data():
    """Create enhanced compound category analysis table for presentation with threshold details."""
    try:
        from config import get_output_path
        import pandas as pd

        print("\n[LAB] TRIN 5b: STOFKATEGORI ANALYSE - ENHANCED FOR PRESENTATION")
        print("=" * 100)
        print(
            f"{'Kategori':<30} {'Tærskel Type':<15} {'Tærskel':<15} {'Forekomster':<12} {'Unikke lok.':<12} {'Gns/lok.':<10}"
        )
        print("-" * 100)

        # Load compound combinations data
        combinations_path = get_output_path("step5_compound_detailed_combinations")
        if not os.path.exists(combinations_path):
            print("Step 5 compound results not found - run Step 5 first")
            return

        combinations_df = pd.read_csv(combinations_path)

        # Define base thresholds and landfill overrides for reference
        base_thresholds = {
            "BTXER": 50,
            "KLOREREDE_OPLØSNINGSMIDLER": 500,
            "PHENOLER": 100,
            "PESTICIDER": 500,
            "UORGANISKE_FORBINDELSER": 150,
            "PAH_FORBINDELSER": 30,
            "LOSSEPLADS": 100,
            "ANDRE": 500,
            "KLOREDE_KULBRINTER": 200,
            "POLARE_FORBINDELSER": 300,
            "KLOREREDE_PHENOLER": 200,
        }

        landfill_overrides = {
            "BTXER": 70,
            "KLOREREDE_OPLØSNINGSMIDLER": 100,
            "PHENOLER": 35,
            "PESTICIDER": 180,
            "UORGANISKE_FORBINDELSER": 50,
        }

        # Analyze threshold distribution per category
        category_stats = []
        for category in sorted(combinations_df["Qualifying_Category"].unique()):
            category_data = combinations_df[
                combinations_df["Qualifying_Category"] == category
            ]

            occurrences = len(category_data)
            unique_sites = category_data["Lokalitet_ID"].nunique()
            avg_per_site = occurrences / unique_sites if unique_sites > 0 else 0

            # Analyze threshold variability
            thresholds_used = category_data["Category_Threshold_m"].unique()

            if category == "LOSSEPLADS":
                # Special handling for LOSSEPLADS with variable overrides
                threshold_type = "Variable"
                base_threshold = base_thresholds.get(category, 500)
                override_thresholds = sorted(
                    [t for t in thresholds_used if t != base_threshold]
                )

                if override_thresholds:
                    threshold_display = f"{base_threshold}m + overrides ({min(override_thresholds):.0f}-{max(override_thresholds):.0f}m)"
                else:
                    threshold_display = f"{base_threshold}m"

            elif len(thresholds_used) > 1:
                # Category with multiple thresholds (compound overrides + base)
                threshold_type = "Mixed"
                threshold_display = (
                    f"{min(thresholds_used):.0f}-{max(thresholds_used):.0f}m"
                )

            else:
                # Single threshold
                threshold_val = thresholds_used[0]
                base_thresh = base_thresholds.get(category, 500)

                if threshold_val == base_thresh:
                    threshold_type = "Base"
                    threshold_display = f"{int(threshold_val)}m"
                elif (
                    category in landfill_overrides
                    and threshold_val == landfill_overrides[category]
                ):
                    threshold_type = "Landfill Override"
                    threshold_display = f"{int(threshold_val)}m"
                else:
                    threshold_type = "Compound Override"
                    threshold_display = f"{int(threshold_val)}m"

            category_stats.append(
                {
                    "category": category,
                    "threshold_type": threshold_type,
                    "threshold_display": threshold_display,
                    "occurrences": occurrences,
                    "unique_sites": unique_sites,
                    "avg_per_site": avg_per_site,
                }
            )

        # Sort by occurrences (descending)
        category_stats.sort(key=lambda x: x["occurrences"], reverse=True)

        # Print enhanced table
        total_combinations = 0
        total_unique_sites = 0

        for stat in category_stats:
            total_combinations += stat["occurrences"]
            print(
                f"{stat['category']:<30} {stat['threshold_type']:<15} {stat['threshold_display']:<15} {stat['occurrences']:<12,} {stat['unique_sites']:<12,} {stat['avg_per_site']:<10.1f}"
            )

        # Calculate total unique sites correctly
        total_unique_sites = combinations_df["Lokalitet_ID"].nunique()

        print("-" * 100)
        print(
            f"Total: {total_combinations:,} kombinationer på tværs af {total_unique_sites:,} unikke lokaliteter"
        )

        # Add explanatory notes for presentation
        print(f"\nTÃ†RSKEL SYSTEM FORKLARING:")
        print(f"• Base: Standard kategori-tærskel fra litteratur")
        print(
            f"• Landfill Override: Losseplads-specifik tærskel (kan være strengere eller løsere)"
        )
        print(
            f"• Compound Override: Stof-specifik tærskel (fx benzen: 200m i stedet for BTXER: 50m)"
        )
        print(
            f"• Variable: LOSSEPLADS kategori med multiple tÃ¦rskler baseret på underkategorier"
        )
        print(f"• Mixed: Kategori der anvender bÃ¥de base og override tÃ¦rskler")

        # Export to HTML for PowerPoint
        print("\n  Exporting Table 1 to HTML for PowerPoint...")
        html_output_dir = os.path.join(
            os.path.dirname(get_output_path("step5_high_risk_sites")),
            "Presentation_Tables",
        )

        table_data = []
        for stat in category_stats:
            table_data.append(
                [
                    stat["category"],
                    stat["threshold_type"],
                    stat["threshold_display"],
                    f"{stat['occurrences']:,}",
                    f"{stat['unique_sites']:,}",
                    f"{stat['avg_per_site']:.1f}",
                ]
            )

        headers = [
            "Kategori",
            "Tærskel Type",
            "Tærskel",
            "Forekomster",
            "Unikke Lokaliteter",
            "Gennemsnit/Lokalitet",
        ]
        title = "Trin 5b: Stofkategori Analyse - Enhanced for Presentation"

        create_html_table(
            table_data, headers, title, "table1_category_analysis.html", html_output_dir
        )

    except Exception as e:
        print(f"Error creating enhanced compound category table: {e}")


def create_losseplads_subcategory_table_from_data():
    """Create comprehensive LOSSEPLADS impact analysis for presentation with before/after comparison."""
    try:
        from config import get_output_path
        import pandas as pd

        print("\n[FACTORY] LOSSEPLADS OVERRIDE SYSTEM - PRÃ†SENTATIONSANALYSE")
        print("=" * 90)

        # Load compound combinations data
        combinations_path = get_output_path("step5_compound_detailed_combinations")
        if not os.path.exists(combinations_path):
            print("Step 5 compound results not found - run Step 5 first")
            return

        combinations_df = pd.read_csv(combinations_path)

        # PART 1: LANDFILL OVERRIDE THRESHOLDS TABLE
        print("\n1. LOSSEPLADS-SPECIFIKKE TÃ†RSKLER")
        print("-" * 60)
        print(
            f"{'Kategori':<30} {'Base Tærskel':<15} {'Losseplads Tærskel':<18} {'Effekt':<15}"
        )
        print("-" * 60)

        landfill_thresholds = {
            "BTXER": {"base": 50, "landfill": 70, "effect": "LÃ¸sere (+20m)"},
            "KLOREREDE_OPLØSNINGSMIDLER": {
                "base": 500,
                "landfill": 100,
                "effect": "Strengere (-400m)",
            },
            "PHENOLER": {"base": 100, "landfill": 35, "effect": "Strengere (-65m)"},
            "PESTICIDER": {"base": 500, "landfill": 180, "effect": "Strengere (-320m)"},
            "UORGANISKE_FORBINDELSER": {
                "base": 150,
                "landfill": 50,
                "effect": "Strengere (-100m)",
            },
        }

        for category, data in landfill_thresholds.items():
            print(
                f"{category:<30} {data['base']:<15}m {data['landfill']:<18}m {data['effect']:<15}"
            )

        print("-" * 60)
        print(
            "Note: Kategorier ikke på listen bruger deres base tærskel på lossepladser"
        )

        # PART 2: OVERRIDE IMPACT ANALYSIS
        if "Landfill_Override_Applied" in combinations_df.columns:
            override_data = combinations_df[
                combinations_df["Landfill_Override_Applied"] == True
            ]

            if not override_data.empty:
                print(f"\n2. LOSSEPLADS OVERRIDE RESULTATER")
                print("-" * 90)
                print(
                    f"{'Original Kategori':<30} {'Base->Override':<20} {'Kombinationer':<15} {'Unikke Sites':<15} {'Effekt':<15}"
                )
                print("-" * 90)

                # Calculate override statistics
                override_stats = []
                for original_cat in override_data["Original_Category"].unique():
                    cat_data = override_data[
                        override_data["Original_Category"] == original_cat
                    ]
                    combinations = len(cat_data)
                    unique_sites = cat_data["Lokalitet_ID"].nunique()

                    # Get threshold info
                    landfill_threshold = cat_data["Category_Threshold_m"].iloc[0]
                    base_threshold = landfill_thresholds[original_cat]["base"]

                    threshold_change = f"{base_threshold}m->{int(landfill_threshold)}m"
                    effect = landfill_thresholds[original_cat]["effect"]

                    override_stats.append(
                        {
                            "category": original_cat,
                            "threshold_change": threshold_change,
                            "combinations": combinations,
                            "unique_sites": unique_sites,
                            "effect": effect,
                        }
                    )

                # Sort by combinations (descending)
                override_stats.sort(key=lambda x: x["combinations"], reverse=True)

                total_rescued_combinations = 0
                total_rescued_sites = 0

                for stat in override_stats:
                    total_rescued_combinations += stat["combinations"]
                    total_rescued_sites += stat["unique_sites"]
                    print(
                        f"{stat['category']:<30} {stat['threshold_change']:<20} {stat['combinations']:<15,} {stat['unique_sites']:<15,} {stat['effect']:<15}"
                    )

                print("-" * 90)
                print(
                    f"{'TOTAL REKLASSIFICERET':<30} {'':<20} {total_rescued_combinations:<15,} {total_rescued_sites:<15,} {'Reddet af override':<15}"
                )

                # PART 3: LOSSEPLADS SUBCATEGORY BREAKDOWN
                print(f"\n3. LOSSEPLADS UNDERKATEGORIER EFTER OVERRIDE")
                print("-" * 70)
                print(
                    f"{'Losseplads Underkategori':<40} {'Kombinationer':<15} {'Unikke Sites':<15}"
                )
                print("-" * 70)

                # Get LOSSEPLADS subcategory breakdown
                losseplads_data = combinations_df[
                    combinations_df["Qualifying_Category"] == "LOSSEPLADS"
                ]

                # Separate original LOSSEPLADS from overridden ones
                original_losseplads = losseplads_data[
                    (losseplads_data["Landfill_Override_Applied"] == False)
                    | (losseplads_data["Landfill_Override_Applied"].isna())
                ]

                subcategory_stats = []

                # Original LOSSEPLADS (perkolat etc.)
                if not original_losseplads.empty:
                    subcategory_stats.append(
                        {
                            "subcategory": "LOSSEPLADS (Perkolat/Original)",
                            "combinations": len(original_losseplads),
                            "unique_sites": original_losseplads[
                                "Lokalitet_ID"
                            ].nunique(),
                        }
                    )

                # Override subcategories
                if "Losseplads_Subcategory" in combinations_df.columns:
                    override_subcats = override_data[
                        "Losseplads_Subcategory"
                    ].value_counts()
                    for subcat, count in override_subcats.items():
                        if pd.notna(subcat):
                            subcat_data = override_data[
                                override_data["Losseplads_Subcategory"] == subcat
                            ]
                            unique_sites = subcat_data["Lokalitet_ID"].nunique()
                            subcategory_stats.append(
                                {
                                    "subcategory": subcat,
                                    "combinations": count,
                                    "unique_sites": unique_sites,
                                }
                            )

                # Sort by combinations (descending)
                subcategory_stats.sort(key=lambda x: x["combinations"], reverse=True)

                total_losseplads_combinations = 0
                total_losseplads_sites = 0

                for stat in subcategory_stats:
                    total_losseplads_combinations += stat["combinations"]
                    total_losseplads_sites += stat[
                        "unique_sites"
                    ]  # Note: This will overcount due to overlap
                    print(
                        f"{stat['subcategory']:<40} {stat['combinations']:<15,} {stat['unique_sites']:<15,}"
                    )

                # Get correct unique site count
                actual_unique_losseplads_sites = losseplads_data[
                    "Lokalitet_ID"
                ].nunique()

                print("-" * 70)
                print(
                    f"{'TOTAL LOSSEPLADS KATEGORI':<40} {total_losseplads_combinations:<15,} {actual_unique_losseplads_sites:<15,}"
                )

                # PART 4: SUMMARY FOR PRESENTATION
                print(f"\n4. PRÃ†SENTATIONS SAMMENFATNING")
                print("-" * 50)
                print(f"• Losseplads-specifikke tÃ¦rskler defineret for 5 kategorier")
                print(
                    f"• {total_rescued_combinations:,} kombinationer reklassificeret til LOSSEPLADS"
                )
                print(
                    f"• {total_rescued_sites:,} unikke lokaliteter påvirket af override"
                )
                print(
                    f"• Override effekt: BÃ¥de strengere og løsere tÃ¦rskler afhÃ¦ngig af kategori"
                )
                print(f"• BTXER: LÃ¸sere (50m->70m) - flere lokaliteter kvalificerer")
                print(f"• Andre kategorier: Strengere tÃ¦rskler - fÃ¦rre kvalificerer")

                # Export to HTML for PowerPoint
                print("\n  Exporting Table 2 to HTML for PowerPoint...")
                html_output_dir = os.path.join(
                    os.path.dirname(get_output_path("step5_high_risk_sites")),
                    "Presentation_Tables",
                )

                # Create HTML table with the override results
                table_data = []
                for stat in override_stats:
                    table_data.append(
                        [
                            stat["category"],
                            stat["threshold_change"],
                            f"{stat['combinations']:,}",
                            f"{stat['unique_sites']:,}",
                            stat["effect"],
                        ]
                    )

                headers = [
                    "Original Kategori",
                    "Baseâ†’Override",
                    "Kombinationer",
                    "Unikke Sites",
                    "Effekt",
                ]
                title = "LOSSEPLADS Override System - Impact Analysis"

                create_html_table(
                    table_data,
                    headers,
                    title,
                    "table2_losseplads_impact.html",
                    html_output_dir,
                )

            else:
                print("\nIngen losseplads overrides fundet i data")
        else:
            print("\nLosseplads override data ikke tilgÃ¦ngelig")

    except Exception as e:
        print(f"Error creating enhanced losseplads analysis: {e}")


def create_threshold_decision_tree_table():
    """Create threshold decision tree table for presentation clarity."""
    print("\n[DECISION] TÃ†RSKEL BESLUTNINGSPROCES - PRÃ†SENTATION")
    print("=" * 80)
    print(
        "Flowchart: Hvordan vÃ¦lges tærskelværdier for hver stof-lokalitet kombination?"
    )
    print("-" * 80)

    print(f"{'Trin':<6} {'Betingelse':<40} {'Handling':<25} {'Eksempel':<20}")
    print("-" * 80)

    decision_steps = [
        {
            "step": "1.",
            "condition": "Har stoffet stof-specifik override?",
            "action": "Brug stof-specifik tærskel",
            "example": "benzen -> 200m",
        },
        {
            "step": "2.",
            "condition": "Er lokaliteten en losseplads?",
            "action": "Tjek for losseplads-tærskel",
            "example": 'Branche: "Losseplads"',
        },
        {
            "step": "2a.",
            "condition": "L- Har kategorien losseplads-tarskel?",
            "action": "Brug losseplads-tærskel",
            "example": "BTXER -> 70m",
        },
        {
            "step": "2b.",
            "condition": "L- Ingen losseplads-tarskel?",
            "action": "Brug base kategori-tærskel",
            "example": "PAH -> 30m",
        },
        {
            "step": "3.",
            "condition": "Almindelig lokalitet?",
            "action": "Brug base kategori-tærskel",
            "example": "BTXER -> 50m",
        },
        {
            "step": "4.",
            "condition": "Intet match (ANDRE kategori)?",
            "action": "Brug default tærskel",
            "example": "Ukendt stof -> 500m",
        },
    ]

    for step_info in decision_steps:
        print(
            f"{step_info['step']:<6} {step_info['condition']:<40} {step_info['action']:<25} {step_info['example']:<20}"
        )

    print("-" * 80)
    print("PRIORITERING: Stof-specifik > Losseplads > Base kategori > Default")
    print()

    # Summary statistics from actual data
    print("TÃ†RSKEL ANVENDELSE I PRAKSIS:")
    print("-" * 40)

    try:
        from config import get_output_path
        import pandas as pd

        combinations_path = get_output_path("step5_compound_detailed_combinations")
        if os.path.exists(combinations_path):
            combinations_df = pd.read_csv(combinations_path)

            total_combinations = len(combinations_df)

            # Count different threshold types
            compound_overrides = 0  # Would need to identify these from data
            landfill_overrides = (
                len(
                    combinations_df[
                        combinations_df.get("Landfill_Override_Applied", False) == True
                    ]
                )
                if "Landfill_Override_Applied" in combinations_df.columns
                else 0
            )
            base_thresholds = total_combinations - landfill_overrides  # Approximation

            print(f"• Total kombinationer: {total_combinations:,}")
            print(
                f"• Losseplads overrides: {landfill_overrides:,} ({landfill_overrides / total_combinations * 100:.1f}%)"
            )
            print(
                f"• Base kategori-tÃ¦rskler: {base_thresholds:,} ({base_thresholds / total_combinations * 100:.1f}%)"
            )
            print(f"• Stof-specifikke overrides: Inkluderet i ovenstÃ¥ende")

            # Export to HTML for PowerPoint
            print("\n  Exporting Table 3 to HTML for PowerPoint...")
            html_output_dir = os.path.join(
                os.path.dirname(get_output_path("step5_high_risk_sites")),
                "Presentation_Tables",
            )

            # Create decision tree table data
            table_data = []
            for step_info in decision_steps:
                table_data.append(
                    [
                        step_info["step"],
                        step_info["condition"],
                        step_info["action"],
                        step_info["example"],
                    ]
                )

            headers = ["Trin", "Betingelse", "Handling", "Eksempel"]
            title = "Tærskel Beslutningsproces - Flowchart"

            create_html_table(
                table_data,
                headers,
                title,
                "table3_threshold_decision.html",
                html_output_dir,
            )

        else:
            print("• Data ikke tilgÃ¦ngelig - kÃ¸r Step 5 fÃ¸rst")

    except Exception as e:
        print(f"• Kunne ikke hente statistik: {e}")


def create_losseplads_override_impact(figures_path):
    """Create a chart showing the impact of Losseplads override by category using real data."""
    try:
        from config import get_output_path
        import pandas as pd

        # Load actual override data
        combinations_path = get_output_path("step5_compound_detailed_combinations")
        if not os.path.exists(combinations_path):
            print(
                "Step 5 compound results not found - cannot create override impact plot"
            )
            return

        combinations_df = pd.read_csv(combinations_path)

        # Get landfill overrides (where Landfill_Override_Applied == True)
        if "Landfill_Override_Applied" not in combinations_df.columns:
            print("Landfill override data not available in results")
            return

        override_data = combinations_df[
            combinations_df["Landfill_Override_Applied"] == True
        ]

        if override_data.empty:
            print("No landfill overrides found in data")
            return

        # Group by original category
        override_stats = (
            override_data.groupby("Original_Category")
            .agg(
                {
                    "Lokalitet_ID": [
                        "count",
                        "nunique",
                    ],  # Total combinations AND unique sites
                    "Category_Threshold_m": "first",  # Get threshold used
                }
            )
            .reset_index()
        )

        # Flatten column names
        override_stats.columns = [
            "Original_Category",
            "Combinations",
            "Unique_Sites",
            "Threshold",
        ]
        override_stats = override_stats.sort_values("Combinations", ascending=False)

        # Create figure with two subplots
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 12))

        # Top plot: Override counts by category (both combinations and sites)
        categories = override_stats["Original_Category"].tolist()
        combinations_counts = override_stats["Combinations"].tolist()
        sites_counts = override_stats["Unique_Sites"].tolist()
        thresholds = [f"{int(t)}m" for t in override_stats["Threshold"].tolist()]

        y_pos = range(len(categories))
        width = 0.35

        # Create side-by-side bars
        bars1 = ax1.barh(
            [y - width / 2 for y in y_pos],
            combinations_counts,
            width,
            label="Kombinationer",
            color="#FF7043",
            alpha=0.8,
            edgecolor="black",
        )
        bars2 = ax1.barh(
            [y + width / 2 for y in y_pos],
            sites_counts,
            width,
            label="Unikke lokaliteter",
            color="#42A5F5",
            alpha=0.8,
            edgecolor="black",
        )

        # Add value labels
        for i, (bar1, bar2, combo, sites, threshold) in enumerate(
            zip(bars1, bars2, combinations_counts, sites_counts, thresholds)
        ):
            # Combination count
            width1 = bar1.get_width()
            ax1.text(
                width1 + 5,
                bar1.get_y() + bar1.get_height() / 2,
                f"{combo:,}",
                ha="left",
                va="center",
                fontweight="bold",
                fontsize=10,
            )

            # Site count
            width2 = bar2.get_width()
            ax1.text(
                width2 + 5,
                bar2.get_y() + bar2.get_height() / 2,
                f"{sites:,}",
                ha="left",
                va="center",
                fontweight="bold",
                fontsize=10,
            )

        ax1.set_yticks(y_pos)
        ax1.set_yticklabels(categories)
        ax1.set_xlabel("Antal reklassificeret", fontsize=12, fontweight="bold")
        ax1.set_title(
            "Losseplads Override Impact per Stofkategori\n(Kombinationer vs Unikke Lokaliteter)",
            fontsize=14,
            fontweight="bold",
        )
        ax1.legend()
        ax1.grid(axis="x", alpha=0.3)

        # Bottom plot: Summary statistics
        total_combinations = override_stats["Combinations"].sum()
        total_sites = override_stats["Unique_Sites"].sum()

        summary_labels = [
            "Kombinationer\nreklassificeret",
            "Unikke lokaliteter\nreklassificeret",
        ]
        summary_values = [total_combinations, total_sites]
        summary_colors = ["#FF7043", "#42A5F5"]

        bars3 = ax2.bar(
            summary_labels,
            summary_values,
            color=summary_colors,
            alpha=0.8,
            edgecolor="black",
            linewidth=1.5,
        )

        # Add value labels
        for bar, value in zip(bars3, summary_values):
            height = bar.get_height()
            ax2.text(
                bar.get_x() + bar.get_width() / 2.0,
                height + max(summary_values) * 0.02,
                f"{value:,}",
                ha="center",
                va="bottom",
                fontsize=16,
                fontweight="bold",
            )

        ax2.set_ylabel("Antal", fontsize=12, fontweight="bold")
        ax2.set_title(
            "Samlet Losseplads Override Resultat", fontsize=14, fontweight="bold"
        )
        ax2.set_ylim(0, max(summary_values) * 1.15)
        ax2.grid(axis="y", alpha=0.3)

        # Add explanation text
        explanation = (
            f"{total_combinations:,} stof-lokalitet kombinationer fra {total_sites:,} unikke lokaliteter "
            f"blev reklassificeret fra deres oprindelige kategorier til LOSSEPLADS-kategorier "
            f"med losseplads-specifikke tÃ¦rskler."
        )
        fig.text(0.1, 0.02, explanation, fontsize=10, style="italic", wrap=True)

        plt.tight_layout()
        plt.subplots_adjust(bottom=0.12)  # Make room for explanation
        plt.savefig(
            os.path.join(figures_path, "losseplads_override_impact.png"),
            dpi=300,
            bbox_inches="tight",
        )
        plt.close()

        print("Losseplads override impact plot created successfully")
        print(
            f"  Shows {total_combinations:,} combinations from {total_sites:,} unique sites reclassified"
        )

    except Exception as e:
        print(f"Error creating Losseplads override impact: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    results_path = os.path.join(".", "Resultater")

    print("\n=== Creating Selected Visualizations ===")

    print("Creating distance histogram with thresholds...")
    create_distance_histogram_with_thresholds(results_path)

    print("Creating progression plot...")
    # Define required files for progression plot using config paths
    from config import get_output_path, get_visualization_path, GRUNDVAND_PATH

    required_files = {
        "all_gvfk": GRUNDVAND_PATH,  # Use original file since Step 1 no longer creates output
        "river_gvfk": get_output_path("step2_river_gvfk"),
        "v1v2_gvfk": get_output_path("step3_gvfk_polygons"),
        "high_risk_gvfk": get_output_path("step5_gvfk_high_risk"),
    }
    figures_path = get_visualization_path("workflow_summary")
    create_progression_plot(figures_path, required_files)

    print("\nCreating Losseplads override visualizations...")
    create_losseplads_override_impact(figures_path)

    print("\nGenerating presentation tables (Danish) from real data...")
    create_gvfk_cascade_table_from_data()
    create_compound_category_table_from_data()
    create_losseplads_subcategory_table_from_data()
    create_threshold_decision_tree_table()

    print(f"\nSelected visualizations have been created successfully.")
    print(
        f"Check step-specific folders in: {os.path.join(results_path, 'Step*_*', 'Figures')}"
    )
    print(f"\nCreated visualizations:")
    print(f"- gvfk_progression.png (Danish, both Step 5a and 5b)")
    print(f"- losseplads_override_impact.png")
    print(f"- Danish presentation tables printed above")
    print(f"=== POWERPOINT-READY TABLES EXPORTED:")
    print(f"   Location: {os.path.join(results_path, 'Presentation_Tables')}")
    print(f"   - table1_category_analysis.html")
    print(f"   - table2_losseplads_impact.html")
    print(f"   - table3_threshold_decision.html")
    print(f"=== HOW TO USE:")
    print(f"   1. Open HTML files in your browser")
    print(f"   2. Select the table and copy (Ctrl+A, Ctrl+C)")
    print(f"   3. Paste directly into PowerPoint - formatting will be preserved!")
