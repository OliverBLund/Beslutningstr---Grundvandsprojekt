import geopandas as gpd
import matplotlib.pyplot as plt
import os
import numpy as np
import pandas as pd
from matplotlib.patches import FancyArrowPatch
from config import WORKFLOW_SETTINGS, get_output_path

def create_distance_histogram_with_thresholds(results_path):
    """
    Create a specialized histogram with distance thresholds highlighted.
    Uses the most advanced color palette and styling.
    Uses unique locations data when available.
    """
    print("Creating distance histogram with thresholds...")
    
    # Use config-based path for Step 4 visualizations
    from config import get_visualization_path, get_output_path
    figures_path = get_visualization_path('step4')
    
    # Define paths for both unique locations and all geometries files using config
    unique_distance_file = get_output_path('unique_lokalitet_distances')
    all_distance_file = get_output_path('step4_valid_distances')
    
    # Prioritize using unique locations data
    if os.path.exists(unique_distance_file):
        distance_df_path = unique_distance_file
        analysis_type = "unikke lokaliteter"
        print("Using unique locations dataset for threshold visualization")
    elif os.path.exists(all_distance_file):
        distance_df_path = all_distance_file
        analysis_type = "alle geometrier"
        print("Unique locations file not found. Using all geometries dataset for threshold visualization.")
    else:
        print("Required files for distance analysis not found.")
        print("Run the step4_calculate_distances() function in workflow.py first to generate these files.")
        return
    
    try:
        # Load the data
        distance_df = pd.read_csv(distance_df_path)
        
        # Cap distances at 20,000m - anything above gets grouped into 20000+ category
        original_max_distance = distance_df['Distance_to_River_m'].max()
        distances_over_20k = (distance_df['Distance_to_River_m'] > 20000).sum()
        print(f"Original max distance: {original_max_distance:.1f}m")
        print(f"Sites with distances > 20,000m: {distances_over_20k} ({distances_over_20k/len(distance_df)*100:.1f}%)")
        
        # Cap the distances at 20,000m
        distance_df['Distance_to_River_m'] = distance_df['Distance_to_River_m'].clip(upper=20000)
        
        # If using all geometries but Lokalitetsnr column available, deduplicate
        if analysis_type == "alle geometrier" and 'Lokalitetsnr' in distance_df.columns and not distance_df['Lokalitetsnr'].isna().all():
            unique_count = distance_df['Lokalitetsnr'].nunique()
            print(f"Found {unique_count} unique locations in distance analysis file")
            
            if unique_count > 0:
                # Get minimum distance for each unique Lokalitetsnr
                unique_distance_df = distance_df.loc[distance_df.groupby('Lokalitetsnr')['Distance'].idxmin()]
                print(f"After selecting minimum distance per location: {len(unique_distance_df)} records")
                distance_df = unique_distance_df
                analysis_type = "unikke lokaliteter"
        
        print(f"Analyzing {len(distance_df)} {analysis_type} for threshold visualization")
        
        if 'Distance_to_River_m' in distance_df.columns:
            # Prepare the data
            if 'Site_Type' in distance_df.columns:
                # Define masks for V1, V2, and both
                v1_mask = distance_df['Site_Type'].str.contains('V1', case=False, na=False)
                v2_mask = distance_df['Site_Type'].str.contains('V2', case=False, na=False)
                
                # Count by type for the legend
                v1_count = sum(v1_mask & ~v2_mask)
                v2_count = sum(v2_mask & ~v1_mask)
                both_count = sum(v1_mask & v2_mask)
                
                # Create type labels with counts
                type_labels = [
                    f'V1-kortlagt (n={v1_count})',
                    f'V2-kortlagt (n={v2_count})',
                    f'V1 og V2-kortlagt (n={both_count})'
                ]
            else:
                # Generic label if no type info
                type_labels = ['Alle lokaliteter']
            
            # Use configurable thresholds from config
            thresholds = WORKFLOW_SETTINGS['additional_thresholds_m']
            
            # Calculate percentage of sites within each threshold
            percentages = []
            for t in thresholds:
                within = (distance_df['Distance_to_River_m'] <= t).sum()
                pct = within / len(distance_df) * 100
                percentages.append(pct)
                print(f"Lokaliteter indenfor {t}m: {within} ({pct:.1f}%)")
                
            # Create a more beautiful histogram with thresholds
            plt.figure(figsize=(15, 10))
        
            # Define color palette
            colors = {
                'v1': '#1f4e79',      # Dark blue for V1 only
                'v2': '#E31A1C',      # Red for V2 only  
                'v1v2': '#6A3D9A',    # Purple for V1 and V2
                'bar': '#1f77b4'      # Default blue for bars
            }
            
            # Create separate data for each site type if we have type information
            if 'Site_Type' in distance_df.columns:
                # Separate data by site type
                v1_only_data = distance_df[v1_mask & ~v2_mask]['Distance_to_River_m']
                v2_only_data = distance_df[v2_mask & ~v1_mask]['Distance_to_River_m']
                both_data = distance_df[v1_mask & v2_mask]['Distance_to_River_m']
                
                # Create bins at 500m intervals from 0 to 20000
                bins = range(0, 20500, 500)  # 500m intervals up to 20000m
                plt.hist([v1_only_data, v2_only_data, both_data], 
                        bins=bins,
                        color=[colors['v1'], colors['v2'], colors['v1v2']], 
                        alpha=0.75,
                        edgecolor='black',
                        linewidth=0.5,
                        label=[f'V1 kun (n={len(v1_only_data)})', 
                              f'V2 kun (n={len(v2_only_data)})', 
                              f'V1 og V2 (n={len(both_data)})'],
                        stacked=True)
            else:
                # Create single histogram if no type info - bins at 500m intervals
                bins = range(0, 20500, 500)  # 500m intervals up to 20000m
                n, bins, patches = plt.hist(
                    distance_df['Distance_to_River_m'],
                    bins=bins, 
                    color=colors['bar'], 
                    alpha=0.75,
                    edgecolor='black',
                    linewidth=0.5
                )
            
            # Add colorful vertical lines for thresholds with improved styling
            threshold_colors = ['#006400', '#32CD32', '#FFD700', '#FF6347', '#FF0000']  # Green to red gradient
        
            # Add shaded regions for thresholds
            xmin = distance_df['Distance_to_River_m'].min()
            prev_threshold = xmin
            
            for i, threshold in enumerate(thresholds):
                # Add vertical line
                plt.axvline(threshold, color=threshold_colors[i], linestyle='-', 
                          alpha=0.8, linewidth=2,
                          label=f'{threshold}m: {percentages[i]:.1f}%')
                
                # Add percentage label directly on the line - horizontal text, positioned to avoid overlap
                label_y_position = plt.ylim()[1] * (0.95 - i * 0.08)  # Stagger vertically to avoid overlap
                plt.text(threshold + 100, label_y_position, 
                        f'{threshold}m: {percentages[i]:.1f}%',
                        rotation=0, verticalalignment='center', horizontalalignment='left',
                        color=threshold_colors[i], fontweight='bold', fontsize=10,
                        bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.9, edgecolor=threshold_colors[i]))
                
                # Add shaded region
                plt.axvspan(prev_threshold, threshold, 
                          color=threshold_colors[i], alpha=0.1)
                
                prev_threshold = threshold
            
            # Add compact statistics panel
            all_stats = {
                'Count': len(distance_df),
                'Min': distance_df['Distance_to_River_m'].min(),
                'Max': distance_df['Distance_to_River_m'].max(),
                'Mean': distance_df['Distance_to_River_m'].mean(),
                'Median': distance_df['Distance_to_River_m'].median(),
            }
            
            # Create compact statistics text box
            if analysis_type == "unikke lokaliteter":
                stats_text = (
                    f'Afstandsstatistik (unique locations):\n'
                    f'Antal lokaliteter: {all_stats["Count"]}\n'
                    f'Min: {all_stats["Min"]:.0f}m, Max: {all_stats["Max"]:.0f}m*\n'
                    f'Median: {all_stats["Median"]:.0f}m, Gennemsnit: {all_stats["Mean"]:.0f}m\n'
                    f'*Afstande >20km grupperet som 20km'
                )
            else:
                stats_text = (
                    f'Afstandsstatistik:\n'
                    f'Antal lokaliteter: {all_stats["Count"]}\n'
                    f'Min: {all_stats["Min"]:.0f}m, Max: {all_stats["Max"]:.0f}m*\n'
                    f'Median: {all_stats["Median"]:.0f}m, Gennemsnit: {all_stats["Mean"]:.0f}m\n'
                    f'*Afstande >20km grupperet som 20km'
                )
            
            # Add smaller text box with essential statistics. Change to bottom right.
            plt.text(0.99, 0.85, stats_text,
                    transform=plt.gca().transAxes,
                    verticalalignment='top',
                    horizontalalignment='right',
                    bbox=dict(boxstyle='round', facecolor='white', alpha=0.9),
                    fontsize=9)
            
            # Create the note text about unique locations
            note_text = ""
            if analysis_type == "unikke lokaliteter":
                note_text += "\nKun den korteste afstand for hver unik lokalitet er medtaget."
            note_text += f"\nAfstande >20km ({distances_over_20k} lokaliteter) grupperet som 20km."
            
            # Add note about unique locations
            plt.text(0.02, 0.02, note_text,
                    transform=plt.gca().transAxes,
                    verticalalignment='bottom',
                    horizontalalignment='left',
                    bbox=dict(boxstyle='round', facecolor='white', alpha=0.9),
                    fontsize=10)
        
            # Add second y-axis with percentages
            ax1 = plt.gca()
            ax2 = ax1.twinx()
            ax2.set_ylim(ax1.get_ylim())
            ax2.set_ylabel('Procent af lokaliteter', fontsize=12)
            ax2.yaxis.set_major_formatter(plt.FuncFormatter(lambda y, _: '{:.1%}'.format(y/len(distance_df))))
            
            # Set title and labels with analysis type details
            title_suffix = "unikke lokaliteter" if analysis_type == "unikke lokaliteter" else "V1/V2-lokaliteter"
            plt.title(f'Afstande mellem {title_suffix} og nærmeste kontaktzone\nmed fremhævede tærskelværdier (afstande >20km grupperet)',
                     fontsize=14, pad=20)
            ax1.set_xlabel('Afstand (meter) - maksimum 20.000m', fontsize=12)
            ax1.set_ylabel(f'Antal {title_suffix}', fontsize=12)
            
            plt.grid(True, alpha=0.3)
            
            # Improved legend - combine threshold and site type legends
            handles, labels = ax1.get_legend_handles_labels()
            by_label = dict(zip(labels, handles))
            
            # Create two separate legends - one for thresholds, one for site types
            threshold_legend = ax1.legend(by_label.values(), by_label.keys(), 
                                        loc='upper center', ncol=3, framealpha=0.9, fontsize=10,
                                        bbox_to_anchor=(0.5, -0.05), title="Afstandsgrænser")
            
            # Add site type legend if we have type information
            if 'Site_Type' in distance_df.columns:
                from matplotlib.patches import Patch
                site_type_elements = [
                    Patch(facecolor=colors['v1'], label=f'V1 kun (n={len(v1_only_data)})'),
                    Patch(facecolor=colors['v2'], label=f'V2 kun (n={len(v2_only_data)})'),
                    Patch(facecolor=colors['v1v2'], label=f'V1 og V2 (n={len(both_data)})')
                ]
                site_legend = ax1.legend(handles=site_type_elements, loc='upper right', 
                                       framealpha=0.9, fontsize=10, title="Lokalitetstyper")
                ax1.add_artist(threshold_legend)  # Add back the threshold legend
            
            plt.tight_layout()
            plt.savefig(os.path.join(figures_path, "distance_histogram_thresholds.png"), 
                       dpi=300, bbox_inches='tight')
            plt.savefig(os.path.join(figures_path, "distance_histogram_thresholds.png"), dpi=300, 
                       bbox_inches='tight')
            plt.close()
            
            print(f"Created threshold histogram in {figures_path}")
            
            # Also create a cumulative distribution function (CDF) with thresholds
            plt.figure(figsize=(15, 10))
            
            # Create the CDF
            sorted_distances = np.sort(distance_df['Distance_to_River_m'])
            cumulative = np.arange(1, len(sorted_distances) + 1) / len(sorted_distances)
            plt.plot(sorted_distances, cumulative, 'k-', linewidth=3, label='Kumulativ fordeling')
            
            # Add vertical lines for thresholds
            for i, threshold in enumerate(thresholds):
                plt.axvline(threshold, color=threshold_colors[i], linestyle='-', 
                          alpha=0.8, linewidth=2,
                          label=f'{threshold}m: {percentages[i]:.1f}%')
                
                # Add horizontal line to show percentage
                y_val = (distance_df['Distance_to_River_m'] <= threshold).sum() / len(distance_df)
                plt.axhline(y_val, color=threshold_colors[i], linestyle=':', alpha=0.5)
                
                # Add text to show percentage at each threshold
                plt.text(threshold*1.05, y_val, f'{y_val*100:.1f}%', 
                        verticalalignment='bottom', horizontalalignment='left',
                        color=threshold_colors[i], fontweight='bold')
            
            plt.grid(True, alpha=0.3)
            
            # Add title and labels
            plt.title(f'Kumulativ fordeling af afstande for {title_suffix}\nmed tærskelværdier',
                     fontsize=14, pad=20)
            plt.xlabel('Afstand (meter)', fontsize=12)
            plt.ylabel('Kumulativ andel af lokaliteter', fontsize=12)
            
            # Add the note text
            plt.text(0.02, 0.02, note_text,
                    transform=plt.gca().transAxes,
                    verticalalignment='bottom',
                    horizontalalignment='left',
                    bbox=dict(boxstyle='round', facecolor='white', alpha=0.9),
                    fontsize=10)
            
            # Improved legend
            handles, labels = plt.gca().get_legend_handles_labels()
            by_label = dict(zip(labels, handles))
            plt.legend(by_label.values(), by_label.keys(), 
                      loc='lower right', framealpha=0.9, fontsize=11)
            
            plt.tight_layout()
            plt.savefig(os.path.join(figures_path, "distance_cdf_thresholds.png"), 
                       dpi=300, bbox_inches='tight')
            plt.savefig(os.path.join(figures_path, "distance_cdf_thresholds.png"), dpi=300, 
                       bbox_inches='tight')
            plt.close()
            
            print(f"Created CDF with thresholds in {figures_path}")
        else:
            print("No 'Distance' column found in the distance analysis file.")
    
    except Exception as e:
        print(f"Error creating threshold histogram: {e}")
        import traceback
        traceback.print_exc()

def create_progression_plot(figures_path, required_files):
    """Create a plot showing the progression of GVFK filtering."""
    try:
        # Load data if available
        datasets = {}
        for name, path in required_files.items():
            if os.path.exists(path) and name in ["all_gvfk", "river_gvfk", "v1v2_gvfk", "high_risk_gvfk"]:
                try:
                    datasets[name] = gpd.read_file(path)
                except Exception as e:
                    print(f"Could not load {name}: {e}")
        
        if len(datasets) < 2:
            print("Not enough data files available for progression plot")
            return
        
        # Create figure
        fig, axes = plt.subplots(1, len(datasets), figsize=(5*len(datasets), 8))
        if len(datasets) == 1:
            axes = [axes]
        
        colors = {
            'all_gvfk': '#E6E6E6',
            'river_gvfk': '#66B3FF',
            'v1v2_gvfk': '#FF6666',
            'high_risk_gvfk': '#FF3333'
        }
        
        titles = {
            'all_gvfk': 'All GVFKs',
            'river_gvfk': 'GVFKs with River Contact',
            'v1v2_gvfk': 'GVFKs with V1/V2 Sites',
            'high_risk_gvfk': f'High-Risk GVFKs (≤{WORKFLOW_SETTINGS["risk_threshold_m"]}m)'
        }
        
        for i, (name, data) in enumerate(datasets.items()):
            ax = axes[i]
            data.plot(ax=ax, color=colors.get(name, 'gray'), alpha=0.8, 
                     edgecolor='black', linewidth=0.5)
            ax.set_title(f"{titles.get(name, name)}\n({len(data)})", 
                        fontsize=14, fontweight='bold')
            ax.set_xticks([])
            ax.set_yticks([])
            ax.axis('equal')
        
        plt.suptitle('GVFK Analysis Progression', fontsize=16, fontweight='bold')
        plt.tight_layout()
        plt.savefig(os.path.join(figures_path, "gvfk_progression.png"), dpi=300, bbox_inches='tight')
        plt.close()
        
        print("Progression plot created successfully")
        
    except Exception as e:
        print(f"Error creating progression plot: {e}")


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
        "river_gvfk": get_output_path('step2_river_gvfk'),
        "v1v2_gvfk": get_output_path('step3_gvfk_polygons'),
        "high_risk_gvfk": get_output_path('step5_gvfk_high_risk')
    }
    figures_path = get_visualization_path('workflow')
    create_progression_plot(figures_path, required_files)

    print(f"\nSelected visualizations have been created successfully.")
    print(f"Check step-specific folders in: {os.path.join(results_path, 'Step*_*', 'Figures')}") 