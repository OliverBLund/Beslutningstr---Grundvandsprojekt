import geopandas as gpd
import matplotlib.pyplot as plt
import os
import numpy as np
import pandas as pd
from matplotlib.patches import FancyArrowPatch

def create_site_density_heatmap(results_path):
    """
    Create a high-quality heatmap showing the geographic concentration of unique V1/V2 sites.
    Uses the minimum distance for each unique Lokalitetsnr to avoid duplicate geometries.
    """
    print("Creating enhanced site density heatmap showing unique locations...")
    
    # Create figures directory if it doesn't exist
    figures_path = os.path.join(results_path, "Figures")
    os.makedirs(figures_path, exist_ok=True)
    
    try:
        # Try to load the unique locations with distances first
        unique_distance_file = os.path.join(results_path, "unique_lokalitet_distances.csv")
        all_distances_file = os.path.join(results_path, "step4_valid_distances.csv")
        
        # Check if we have unique data from distance analysis
        if os.path.exists(unique_distance_file):
            print("Using unique locations data from distance analysis")
            unique_sites_df = pd.read_csv(unique_distance_file)
            data_source = "distance_analysis"
        elif os.path.exists(all_distances_file):
            print("Using all geometries from distance analysis and deduplicating")
            distance_df = pd.read_csv(all_distances_file)
            unique_sites_df = distance_df.loc[distance_df.groupby('Site_ID')['Distance_to_River_m'].idxmin()]
            data_source = "distance_analysis"
        else:
            # If distance files don't exist, load from Step3
            print("Distance analysis files not found. Loading from Step3 data...")
            
            # Load V1/V2 sites from step 3
            v1v2_sites = gpd.read_file(os.path.join(results_path, "step3_v1v2_sites.shp"))
            
            if 'Lokalitets' in v1v2_sites.columns:
                # Create a temporary dataframe with unique locations only
                print("Deduplicating based on Lokalitets column...")
                # Get the first geometry for each unique Lokalitetsnr
                unique_indices = v1v2_sites.groupby('Lokalitets').first().index
                unique_sites = v1v2_sites[v1v2_sites['Lokalitets'].isin(unique_indices)]
                data_source = "step3_deduplicated"
            else:
                # If no Lokalitets column, just use all sites
                print("No Lokalitets column found for deduplication. Using all geometries.")
                unique_sites = v1v2_sites
                data_source = "step3_all"
            
            # Create a DataFrame for consistent processing
            if data_source == "step3_deduplicated":
                unique_sites_df = unique_sites.copy()
            else:
                unique_sites_df = v1v2_sites.copy()
        
        # Load Denmark boundary for reference
        gvfk = gpd.read_file(os.path.join(results_path, "step1_all_gvfk.shp"))
        denmark_boundary = gvfk.unary_union
        
        # Create figure with better size for Denmark's shape - make it larger
        fig, ax = plt.subplots(figsize=(18, 24))
        
        # Plot Denmark boundary with improved styling
        gpd.GeoSeries([denmark_boundary]).plot(
            ax=ax, color='#F5F5F5', edgecolor='#CCCCCC', linewidth=0.8, alpha=0.7
        )
        
        # Determine geometry type and process accordingly
        if data_source.startswith("distance_analysis"):
            # Distance analysis produces CSV files without geometry
            # We need to merge with the original sites data to get geometries
            
            v1v2_sites = gpd.read_file(os.path.join(results_path, "step3_v1v2_sites.shp"))
            
            if 'Lokalitets' in v1v2_sites.columns:
                # Rename for consistency
                v1v2_sites = v1v2_sites.rename(columns={'Lokalitets': 'Lokalitetsnr'})
            
            if 'Lokalitetsnr' in unique_sites_df.columns and 'Lokalitetsnr' in v1v2_sites.columns:
                # Get actual geometries for the unique locations
                unique_lokaliteter = unique_sites_df['Lokalitetsnr'].unique()
                print(f"Found {len(unique_lokaliteter)} unique locations for heatmap")
                v1v2_sites_unique = v1v2_sites[v1v2_sites['Lokalitetsnr'].isin(unique_lokaliteter)]
                points = v1v2_sites_unique.geometry.centroid
            else:
                print("Warning: Cannot match unique locations with geometries. Using all geometries instead.")
                points = v1v2_sites.geometry.centroid
        else:
            # If using Step3 data directly, use centroids of existing geometries
            points = unique_sites_df.geometry.centroid
            
        # Extract coordinates
        x = np.array([p.x for p in points if p])
        y = np.array([p.y for p in points if p])
        
        # Add some basic validation to avoid errors
        if len(x) == 0 or len(y) == 0:
            print("Error: No valid geometries found. Cannot create heatmap.")
            return
        
        print(f"Creating heatmap with {len(x)} unique location points")
        
        # Calculate appropriate grid size based on data density
        grid_size = min(200, max(50, int(np.sqrt(len(x)) * 1.5)))
        
        # Create a more appealing 2D histogram with better color scheme
        hb = ax.hexbin(
            x, y, 
            gridsize=grid_size, 
            cmap='YlOrRd', 
            mincnt=1, 
            bins='log',  # Use log scale for better visualization
            alpha=0.85,
            edgecolors='none',
            linewidths=0.2
        )
        
        # Add a smaller, more compact colorbar with better tick labels
        cb = plt.colorbar(hb, ax=ax, orientation='vertical', pad=0.01, shrink=0.4, 
                         aspect=20, fraction=0.05)
        
        # Define custom tick locations and labels for the colorbar
        max_value = hb.get_array().max() if 'hb' in locals() else 100
        
        if max_value > 150:
            tick_locations = [1, 5, 10, 25, 50, 100, int(max_value)]
        elif max_value > 50:
            tick_locations = [1, 5, 10, 25, 50, int(max_value)]
        else:
            tick_locations = [1, 5, 10, 25, int(max_value)] if max_value > 25 else [1, 5, 10, int(max_value)]
        
        # Filter out duplicates and sort
        tick_locations = sorted(list(set(tick_locations)))
        
        # Set the tick locations and labels
        cb.set_ticks(tick_locations)
        cb.set_ticklabels([str(t) for t in tick_locations])
        
        cb.set_label('Antal unikke V1/V2-lokaliteter per celle', fontsize=14, weight='bold')
        cb.ax.tick_params(labelsize=12)
        
        # Set title and remove axes but keep a border
        plt.title('Koncentration af V1/V2-lokaliteter i Danmark', fontsize=18, pad=20, weight='bold')
        ax.set_xticks([])
        ax.set_yticks([])
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.spines['bottom'].set_visible(False)
        ax.spines['left'].set_visible(False)
        
        # Improved north arrow - simpler and cleaner
        
        # Calculate arrow position - better positioned in corner
        x_arrow = ax.get_xlim()[0] + (ax.get_xlim()[1] - ax.get_xlim()[0]) * 0.05
        y_arrow = ax.get_ylim()[0] + (ax.get_ylim()[1] - ax.get_ylim()[0]) * 0.10
        arrow_length = (ax.get_ylim()[1] - ax.get_ylim()[0]) * 0.03
        
        # Add a cleaner north arrow
        north_arrow = FancyArrowPatch(
            (x_arrow, y_arrow), 
            (x_arrow, y_arrow + arrow_length),
            arrowstyle='->', 
            mutation_scale=20,
            linewidth=2,
            color='black'
        )
        ax.add_patch(north_arrow)
        
        # Add 'N' above the arrow
        plt.text(
            x_arrow, 
            y_arrow + arrow_length * 1.2,
            'N', 
            ha='center', va='center', 
            fontsize=12, weight='bold'
        )
        
        # Determine the total count of locations
        if data_source.startswith("distance_analysis"):
            total_geometries = len(unique_sites_df) if 'unique_sites_df' in locals() else len(v1v2_sites)
            unique_lokaliteter_count = len(unique_sites_df) if 'unique_sites_df' in locals() else len(v1v2_sites)
        else:
            total_geometries = len(v1v2_sites)
            unique_lokaliteter_count = unique_sites_df['Lokalitets'].nunique() if 'Lokalitets' in unique_sites_df.columns else "N/A"
        
        # Add annotation box with count information and data source explanation
        info_text = (
            f"Lokaliteter: {unique_lokaliteter_count}"
        )
        
        # Add data source information based on what was used 
        if data_source == "distance_analysis":
            info_text += "\n\nData: Unikke lokaliteter fra afstandsanalyse\n(kun den korteste afstand per lokalitet)"
        elif data_source == "step3_deduplicated":
            info_text += "\n\nData: Deduplikerede lokaliteter fra GVFK-analyse"
        else:
            info_text += "\n\nData: Alle lokaliteter fra GVFK-analyse"
        
        # Add the information box with improved styling
        plt.annotate(
            info_text,
            xy=(0.02, 0.02),
            xycoords='axes fraction',
            bbox=dict(
                boxstyle="round,pad=0.5", 
                fc="white", 
                ec="gray", 
                alpha=0.9,
                lw=0.5
            ),
            fontsize=12
        )
        
        # Try to add hotspots if the necessary libraries are available
        try:
            # Convert hexbin data to numpy array for peak finding
            heatmap_data = hb.get_array()
            heatmap_x = hb.get_offsets()[:, 0]
            heatmap_y = hb.get_offsets()[:, 1]
            
            # Find the indices of hotspots (local maxima)
            # Only label the top 15 hotspots
            max_labels = 15 
            
            if len(heatmap_data) > 10:  # Only if we have enough data points
                # Use simple numpy methods instead of skimage
                # Find top values
                top_indices = np.argsort(heatmap_data)[-max_labels:]
                
                # Label the top hotspots
                for idx in top_indices:
                    if idx < len(heatmap_data):
                        # Get the position of the hotspot
                        x_pos = heatmap_x[idx]
                        y_pos = heatmap_y[idx]
                        
                        # Add a highlighted dot - more subtle. Make bigger
                        ax.plot(x_pos, y_pos, 'o', ms=10, mew=2, mec='black', mfc='none', alpha=0.7)
        except Exception as e:
            print(f"Warning: Could not identify hotspots: {e}")
        
        # Polish the layout
        plt.tight_layout()
        
        # Save with high quality
        heatmap_path = os.path.join(figures_path, "v1v2_density_heatmap_unique.png")
        plt.savefig(heatmap_path, dpi=300, bbox_inches='tight')
        plt.savefig(os.path.join(figures_path, "v1v2_density_heatmap_unique.pdf"), bbox_inches='tight')
        plt.close()
            
        print(f"Created enhanced density heatmap showing {unique_lokaliteter_count} unique locations at {heatmap_path}")
    
    except Exception as e:
        print(f"Error creating enhanced site density heatmap: {e}")
        import traceback
        traceback.print_exc()

def create_distance_histogram_with_thresholds(results_path):
    """
    Create a specialized histogram with distance thresholds highlighted.
    Uses the most advanced color palette and styling.
    Uses unique locations data when available.
    """
    print("Creating distance histogram with thresholds...")
    
    # Define paths
    figures_path = os.path.join(results_path, "Figures", "Step4_Distance_Analysis")
    os.makedirs(figures_path, exist_ok=True)
    
    # Define paths for both unique locations and all geometries files
    unique_distance_file = os.path.join(results_path, "unique_lokalitet_distances.csv")
    all_distance_file = os.path.join(results_path, "step4_valid_distances.csv")
    
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
            
            # Define thresholds in meters - 5 key thresholds
            thresholds = [500, 1000, 1500, 2000, 2500]
            
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
            plt.savefig(os.path.join(figures_path, "distance_histogram_thresholds.pdf"), 
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
            plt.savefig(os.path.join(figures_path, "distance_cdf_thresholds.pdf"), 
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
            'high_risk_gvfk': 'High-Risk GVFKs (≤500m)'
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
    print("Creating site density heatmap...")
    create_site_density_heatmap(results_path)
    
    print("Creating distance histogram with thresholds...")
    create_distance_histogram_with_thresholds(results_path)

    print("Creating progression plot...")
    # Define required files for progression plot
    required_files = {
        "all_gvfk": os.path.join(results_path, "step1_all_gvfk.shp"),
        "river_gvfk": os.path.join(results_path, "step2_gvfk_with_rivers.shp"),
        "v1v2_gvfk": os.path.join(results_path, "step3_gvfk_with_v1v2.shp"),
        "high_risk_gvfk": os.path.join(results_path, "step5_gvfk_high_risk_500m.shp")
    }
    figures_path = os.path.join(results_path, "Figures")
    create_progression_plot(figures_path, required_files)

    print("\nSelected visualizations have been created successfully. Check the 'Resultater/Figures' directory.") 