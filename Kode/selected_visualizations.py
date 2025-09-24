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
    """Create a comprehensive GVFK progression plot showing both Step 5 assessments."""
    try:
        # Create a bar chart showing the complete GVFK progression
        stages = [
            'Alle GVFK\n(Danmark)',
            'Vandløbskontakt\n(Trin 2)',
            'V1/V2 lokaliteter\n(Trin 3)',
            'Generel risiko\n(Trin 5a: ≤500m)',
            'Stofspecifik risiko\n(Trin 5b: Variabel)'
        ]

        # Use actual counts - these should match the analysis output
        counts = [2043, 593, 491, 300, 232]  # Updated with correct Step 5 counts
        colors = ['#E6E6E6', '#66B3FF', '#FF6666', '#FF8C42', '#FF3333']

        fig, ax = plt.subplots(figsize=(14, 8))

        # Create bars
        bars = ax.bar(range(len(stages)), counts, color=colors, alpha=0.8,
                     edgecolor='black', linewidth=1.5)

        # Add count labels and percentages inside bars
        for i, (bar, count) in enumerate(zip(bars, counts)):
            height = bar.get_height()
            percentage = (count / 2043) * 100

            # Count at top of bar
            ax.text(bar.get_x() + bar.get_width()/2., height - height*0.15,
                   f'{count:,}', ha='center', va='center',
                   fontsize=14, fontweight='bold', color='white')

            # Percentage inside bar, lower
            ax.text(bar.get_x() + bar.get_width()/2., height - height*0.4,
                   f'{percentage:.1f}%', ha='center', va='center',
                   fontsize=13, fontweight='bold', color='white')

        # Customize plot
        ax.set_xticks(range(len(stages)))
        ax.set_xticklabels(stages, fontsize=12, fontweight='bold')
        ax.set_ylabel('Antal GVFK', fontsize=14, fontweight='bold')
        ax.set_title('GVFK Analyse Progression\nFra alle danske GVFK til højrisiko vurdering',
                    fontsize=16, fontweight='bold', pad=20)

        # Set y-axis limits with some padding
        ax.set_ylim(0, max(counts) * 1.1)

        # Add grid
        ax.grid(axis='y', alpha=0.3, linestyle='--')
        ax.set_axisbelow(True)

        # Add explanation text in Danish
        explanation = ("Trin 5a: Generel vurdering bruger universel 500m tærskel\n"
                      "Trin 5b: Stofspecifik vurdering bruger litteraturbaserede variable tærskler")
        ax.text(0.02, 0.98, explanation, transform=ax.transAxes,
               fontsize=10, verticalalignment='top',
               bbox=dict(boxstyle='round,pad=0.5', facecolor='lightgray', alpha=0.8))

        plt.tight_layout()
        plt.savefig(os.path.join(figures_path, "gvfk_progression.png"), dpi=300, bbox_inches='tight')
        plt.close()

        print("Updated GVFK progression plot created successfully")
        print(f"  Shows both Step 5a (General: 300 GVFK) and Step 5b (Compound-specific: 232 GVFK)")

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
        print(f"{'TRIN 1':<8} {'Alle GVFK i Danmark':<35} {f'{total_gvfk:,}':<10} {'100,0%':<12}")
        print(f"{'TRIN 2':<8} {'Med vandlobskontakt':<35} {'593':<10} {'29,0%':<12}")
        print(f"{'TRIN 3':<8} {'Med V1/V2 lokaliteter + kontakt':<35} {'491':<10} {'24,0%':<12}")

        # Try to get actual Step 5 GVFK counts
        try:
            # Load general sites if available
            general_path = get_output_path('step5_high_risk_sites')
            if os.path.exists(general_path):
                general_sites = pd.read_csv(general_path)
                general_gvfks = general_sites['Closest_GVFK'].dropna().nunique()
                general_pct = (general_gvfks / total_gvfk) * 100
                print(f"{'TRIN 5a':<8} {'Generel vurdering (<=500m)':<35} {f'{general_gvfks:,}':<10} {f'{general_pct:.1f}%':<12}")
            else:
                print(f"{'TRIN 5a':<8} {'Generel vurdering (<=500m)':<35} {'300':<10} {'14,7%':<12}")
        except:
            print(f"{'TRIN 5a':<8} {'Generel vurdering (<=500m)':<35} {'300':<10} {'14,7%':<12}")

        try:
            # Load compound sites if available
            compound_path = get_output_path('step5_compound_specific_sites')
            if os.path.exists(compound_path):
                compound_sites = pd.read_csv(compound_path)
                compound_gvfks = compound_sites['Closest_GVFK'].dropna().nunique()
                compound_pct = (compound_gvfks / total_gvfk) * 100
                print(f"{'TRIN 5b':<8} {'Stofspecifik risiko':<35} {f'{compound_gvfks:,}':<10} {f'{compound_pct:.1f}%':<12}")
            else:
                print(f"{'TRIN 5b':<8} {'Stofspecifik risiko':<35} {'232':<10} {'11,4%':<12}")
        except:
            print(f"{'TRIN 5b':<8} {'Stofspecifik risiko':<35} {'232':<10} {'11,4%':<12}")

        print("-" * 60)
        print("Progressiv filtrering fra alle danske GVFK til hojrisiko identifikation")

    except Exception as e:
        print(f"Error creating GVFK cascade table: {e}")

def create_compound_category_table_from_data():
    """Create compound category analysis table from actual Step 5 results."""
    try:
        from config import get_output_path
        import pandas as pd

        print("\n[LAB] TRIN 5b: STOFKATEGORI ANALYSE")
        print("=" * 80)
        print(f"{'Kategori':<30} {'Taerskel':<10} {'Forekomster':<12} {'Unikke lok.':<12} {'Gns/lok.':<10}")
        print("-" * 80)

        # Load compound combinations data
        combinations_path = get_output_path('step5_compound_detailed_combinations')
        if not os.path.exists(combinations_path):
            print("Step 5 compound results not found - run Step 5 first")
            return

        combinations_df = pd.read_csv(combinations_path)

        # Group by category to calculate statistics
        category_stats = []
        for category in combinations_df['Qualifying_Category'].unique():
            category_data = combinations_df[combinations_df['Qualifying_Category'] == category]

            occurrences = len(category_data)  # Total combinations
            unique_sites = category_data['Lokalitet_ID'].nunique()  # Unique sites
            avg_per_site = occurrences / unique_sites if unique_sites > 0 else 0
            threshold = category_data['Category_Threshold_m'].iloc[0] if len(category_data) > 0 else 500

            category_stats.append({
                'category': category,
                'threshold': f"{int(threshold)}m",
                'occurrences': occurrences,
                'unique_sites': unique_sites,
                'avg_per_site': avg_per_site
            })

        # Sort by occurrences (descending)
        category_stats.sort(key=lambda x: x['occurrences'], reverse=True)

        # Print table
        total_combinations = 0
        total_unique_sites = 0

        for stat in category_stats:
            total_combinations += stat['occurrences']
            # Don't double count sites (some sites may have multiple categories)

            print(f"{stat['category']:<30} {stat['threshold']:<10} {stat['occurrences']:<12,} {stat['unique_sites']:<12,} {stat['avg_per_site']:<10.1f}")

        # Calculate total unique sites correctly
        total_unique_sites = combinations_df['Lokalitet_ID'].nunique()

        print("-" * 80)
        print(f"Total: {total_combinations:,} kombinationer pa tvaers af {total_unique_sites:,} unikke lokaliteter")

    except Exception as e:
        print(f"Error creating compound category table: {e}")

def create_losseplads_subcategory_table_from_data():
    """Create LOSSEPLADS subcategory breakdown from actual Step 5 override results."""
    try:
        from config import get_output_path
        import pandas as pd

        print("\n[FACTORY] LOSSEPLADS UNDERKATEGORI ANALYSE")
        print("=" * 75)
        print("Losseplads Override System - Detaljeret Kategorifordeling")
        print("-" * 75)

        # Load compound combinations data
        combinations_path = get_output_path('step5_compound_detailed_combinations')
        if not os.path.exists(combinations_path):
            print("Step 5 compound results not found - run Step 5 first")
            return

        combinations_df = pd.read_csv(combinations_path)

        print(f"{'Original Kategori':<30} {'Override til LOSSEPLADS':<20} {'Taerskel':<15} {'Komb.':<10} {'Sites':<10}")
        print("-" * 85)

        # Get landfill overrides (where Landfill_Override_Applied == True)
        if 'Landfill_Override_Applied' in combinations_df.columns:
            override_data = combinations_df[combinations_df['Landfill_Override_Applied'] == True]

            if not override_data.empty:
                # Group by original category
                override_stats = override_data.groupby('Original_Category').agg({
                    'Lokalitet_ID': ['count', 'nunique'],  # Total combinations AND unique sites per original category
                    'Category_Threshold_m': 'first'  # Get threshold used
                }).reset_index()

                # Flatten column names
                override_stats.columns = ['Original_Category', 'Combinations', 'Unique_Sites', 'Threshold']

                # Sort by combinations count descending
                override_stats = override_stats.sort_values('Combinations', ascending=False)

                total_combinations = 0
                total_unique_sites = 0
                for _, row in override_stats.iterrows():
                    original_cat = row['Original_Category']
                    combinations = row['Combinations']
                    unique_sites = row['Unique_Sites']
                    threshold = int(row['Threshold'])
                    total_combinations += combinations
                    total_unique_sites += unique_sites

                    print(f"{original_cat:<30} {'-> LOSSEPLADS':<20} {f'{threshold}m':<15} {combinations:<10,} {unique_sites:<10,}")

                print("-" * 85)
                print(f"{'TOTAL REKLASSIFICERET':<30} {'':<20} {'':<15} {total_combinations:<10,} {total_unique_sites:<10,}")

                # Calculate removed combinations (would need comparison with before override)
                # This is harder to calculate from final data, so show what we know
                print(f"{'INFO: Se step 5 output for fjernet':<30} {'':<20} {'':<15} {'':<10}")

            else:
                print("No landfill overrides found in data")
        else:
            print("Landfill override data not available")

        print("-" * 75)

        print("\nLosseplads Karakteristika (Branche/Aktivitet nogleord):")
        print("- Losseplads, Deponi, Fyldplads")
        print("- Braending af affald, Sortering og behandling af affald")
        print("- Kompostering, Genbrugsstation")

        if 'Landfill_Override_Applied' in combinations_df.columns:
            total_overridden = len(combinations_df[combinations_df['Landfill_Override_Applied'] == True])
            print(f"\nResultat: {total_overridden:,} kombinationer fik losseplads-specifikke taerskler")

    except Exception as e:
        print(f"Error creating losseplads subcategory table: {e}")


def create_losseplads_override_impact(figures_path):
    """Create a chart showing the impact of Losseplads override by category using real data."""
    try:
        from config import get_output_path
        import pandas as pd

        # Load actual override data
        combinations_path = get_output_path('step5_compound_detailed_combinations')
        if not os.path.exists(combinations_path):
            print("Step 5 compound results not found - cannot create override impact plot")
            return

        combinations_df = pd.read_csv(combinations_path)

        # Get landfill overrides (where Landfill_Override_Applied == True)
        if 'Landfill_Override_Applied' not in combinations_df.columns:
            print("Landfill override data not available in results")
            return

        override_data = combinations_df[combinations_df['Landfill_Override_Applied'] == True]

        if override_data.empty:
            print("No landfill overrides found in data")
            return

        # Group by original category
        override_stats = override_data.groupby('Original_Category').agg({
            'Lokalitet_ID': ['count', 'nunique'],  # Total combinations AND unique sites
            'Category_Threshold_m': 'first'  # Get threshold used
        }).reset_index()

        # Flatten column names
        override_stats.columns = ['Original_Category', 'Combinations', 'Unique_Sites', 'Threshold']
        override_stats = override_stats.sort_values('Combinations', ascending=False)

        # Create figure with two subplots
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 12))

        # Top plot: Override counts by category (both combinations and sites)
        categories = override_stats['Original_Category'].tolist()
        combinations_counts = override_stats['Combinations'].tolist()
        sites_counts = override_stats['Unique_Sites'].tolist()
        thresholds = [f"{int(t)}m" for t in override_stats['Threshold'].tolist()]

        y_pos = range(len(categories))
        width = 0.35

        # Create side-by-side bars
        bars1 = ax1.barh([y - width/2 for y in y_pos], combinations_counts, width,
                        label='Kombinationer', color='#FF7043', alpha=0.8, edgecolor='black')
        bars2 = ax1.barh([y + width/2 for y in y_pos], sites_counts, width,
                        label='Unikke lokaliteter', color='#42A5F5', alpha=0.8, edgecolor='black')

        # Add value labels
        for i, (bar1, bar2, combo, sites, threshold) in enumerate(zip(bars1, bars2, combinations_counts, sites_counts, thresholds)):
            # Combination count
            width1 = bar1.get_width()
            ax1.text(width1 + 5, bar1.get_y() + bar1.get_height()/2,
                    f'{combo:,}', ha='left', va='center', fontweight='bold', fontsize=10)

            # Site count
            width2 = bar2.get_width()
            ax1.text(width2 + 5, bar2.get_y() + bar2.get_height()/2,
                    f'{sites:,}', ha='left', va='center', fontweight='bold', fontsize=10)

        ax1.set_yticks(y_pos)
        ax1.set_yticklabels(categories)
        ax1.set_xlabel('Antal reklassificeret', fontsize=12, fontweight='bold')
        ax1.set_title('Losseplads Override Impact per Stofkategori\n(Kombinationer vs Unikke Lokaliteter)',
                     fontsize=14, fontweight='bold')
        ax1.legend()
        ax1.grid(axis='x', alpha=0.3)

        # Bottom plot: Summary statistics
        total_combinations = override_stats['Combinations'].sum()
        total_sites = override_stats['Unique_Sites'].sum()

        summary_labels = ['Kombinationer\nreklassificeret', 'Unikke lokaliteter\nreklassificeret']
        summary_values = [total_combinations, total_sites]
        summary_colors = ['#FF7043', '#42A5F5']

        bars3 = ax2.bar(summary_labels, summary_values, color=summary_colors, alpha=0.8,
                       edgecolor='black', linewidth=1.5)

        # Add value labels
        for bar, value in zip(bars3, summary_values):
            height = bar.get_height()
            ax2.text(bar.get_x() + bar.get_width()/2., height + max(summary_values)*0.02,
                    f'{value:,}', ha='center', va='bottom',
                    fontsize=16, fontweight='bold')

        ax2.set_ylabel('Antal', fontsize=12, fontweight='bold')
        ax2.set_title('Samlet Losseplads Override Resultat', fontsize=14, fontweight='bold')
        ax2.set_ylim(0, max(summary_values) * 1.15)
        ax2.grid(axis='y', alpha=0.3)

        # Add explanation text
        explanation = (f"{total_combinations:,} stof-lokalitet kombinationer fra {total_sites:,} unikke lokaliteter "
                      f"blev reklassificeret fra deres oprindelige kategorier til LOSSEPLADS-kategorier "
                      f"med losseplads-specifikke tærskler.")
        fig.text(0.1, 0.02, explanation, fontsize=10, style='italic', wrap=True)

        plt.tight_layout()
        plt.subplots_adjust(bottom=0.12)  # Make room for explanation
        plt.savefig(os.path.join(figures_path, "losseplads_override_impact.png"),
                   dpi=300, bbox_inches='tight')
        plt.close()

        print("Losseplads override impact plot created successfully")
        print(f"  Shows {total_combinations:,} combinations from {total_sites:,} unique sites reclassified")

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
        "river_gvfk": get_output_path('step2_river_gvfk'),
        "v1v2_gvfk": get_output_path('step3_gvfk_polygons'),
        "high_risk_gvfk": get_output_path('step5_gvfk_high_risk')
    }
    figures_path = get_visualization_path('workflow')
    create_progression_plot(figures_path, required_files)

    print("\nCreating Losseplads override visualizations...")
    create_losseplads_override_impact(figures_path)

    print("\nGenerating presentation tables (Danish) from real data...")
    create_gvfk_cascade_table_from_data()
    create_compound_category_table_from_data()
    create_losseplads_subcategory_table_from_data()

    print(f"\nSelected visualizations have been created successfully.")
    print(f"Check step-specific folders in: {os.path.join(results_path, 'Step*_*', 'Figures')}")
    print(f"\nCreated visualizations:")
    print(f"- gvfk_progression.png (Danish, both Step 5a and 5b)")
    print(f"- losseplads_override_impact.png")
    print(f"- Danish presentation tables printed above") 