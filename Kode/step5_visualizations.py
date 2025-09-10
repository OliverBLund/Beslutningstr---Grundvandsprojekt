"""
Step 5 Visualizations: Professional Risk Assessment Plots

Creates clean, professional visualizations for contamination risk assessment:
- Broad analysis using 500m threshold
- Compound-specific analysis using category-based thresholds
- Proper handling of "OTHER" category
"""

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import seaborn as sns
import numpy as np
import os
from collections import Counter

# Professional styling setup
plt.rcParams.update({
    'font.family': ['Arial', 'DejaVu Sans', 'sans-serif'],
    'font.size': 10,
    'axes.titlesize': 14,
    'axes.labelsize': 12,
    'xtick.labelsize': 10,
    'ytick.labelsize': 10,
    'legend.fontsize': 10,
    'figure.titlesize': 16,
    'figure.dpi': 100,
    'savefig.dpi': 300,
    'savefig.bbox': 'tight',
    'axes.spines.top': False,
    'axes.spines.right': False,
    'axes.grid': True,
    'axes.axisbelow': True,
    'grid.alpha': 0.3,
    'grid.linewidth': 0.5
})

# Vibrant, modern color palette
COLORS = {
    'primary': '#1E88E5',      # Vibrant blue
    'secondary': '#FFC107',    # Warm amber
    'accent': '#00ACC1',       # Cyan
    'success': '#43A047',      # Fresh green
    'danger': '#E53935',       # Clear red
    'purple': '#8E24AA',       # Rich purple
    'neutral': '#5A5A5A',      # Medium gray
    'other': '#808080',        # Gray for OTHER category
    'light_gray': '#F5F5F5',   # Light gray for backgrounds
    'categories': ['#1E88E5', '#FFC107', '#00ACC1', '#43A047', '#8E24AA', 
                  '#FF7043', '#AB47BC', '#26A69A', '#66BB6A']
}

def setup_professional_plot(figsize=(10, 6)):
    """Set up a professional-looking plot with clean styling."""
    fig, ax = plt.subplots(figsize=figsize)
    
    # Remove top and right spines
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    
    # Style the remaining spines
    ax.spines['left'].set_color('#CCCCCC')
    ax.spines['bottom'].set_color('#CCCCCC')
    
    # Remove grid
    ax.grid(False)
    
    return fig, ax

def safe_save_figure(figures_path, filename_base):
    """Save figure with professional settings."""
    os.makedirs(figures_path, exist_ok=True)
    png_path = os.path.join(figures_path, f"{filename_base}.png")
    plt.savefig(png_path, dpi=300, bbox_inches='tight', facecolor='white')
    plt.close()

def create_step5_visualizations():
    """Create all professional Step 5 visualizations."""
    print("Creating professional Step 5 visualizations...")
    
    from config import get_visualization_path, get_output_path
    figures_path = get_visualization_path('step5')
    
    # Load high-risk sites data
    high_risk_file = get_output_path('step5_high_risk_sites')
    
    if not os.path.exists(high_risk_file):
        print(f"High-risk sites file not found: {high_risk_file}")
        print("Please run Step 5 first to generate the data.")
        return
    
    try:
        high_risk_sites = pd.read_csv(high_risk_file)
        print(f"Loaded {len(high_risk_sites)} high-risk sites")
    except Exception as e:
        print(f"Error loading high-risk sites data: {e}")
        return
    
    # 1. General Assessment (500m threshold) - 4 plots
    print("Creating general assessment plots (500m threshold)...")
    create_distance_distribution(high_risk_sites, figures_path)
    create_activity_distribution(high_risk_sites, figures_path)
    create_industry_distribution(high_risk_sites, figures_path)
    create_substance_distribution(high_risk_sites, figures_path)
    
    # 2. Key Result Visualizations
    print("\nCreating key result visualizations...")
    create_threshold_cascade_visualization(figures_path)
    create_compound_comparison_summary(figures_path)
    
    # 3. Compound-Specific Analysis (INCLUDING OTHER)
    print("\nCreating compound-specific analysis...")
    create_compound_boxplot_comparison(figures_path)
    create_category_prevalence_chart(figures_path)
    create_category_sites_distribution(figures_path)  # NEW: Sites per category
    create_other_category_analysis(figures_path)
    
    # 4. Per Compound Group Details
    print("\nCreating detailed compound-specific plots...")
    create_essential_compound_plots(figures_path)
    
    print(f"\n✓ All Step 5 visualizations completed in: {figures_path}")

# ============================================================================
# GENERAL ASSESSMENT VISUALIZATIONS (500m threshold)
# ============================================================================

def create_distance_distribution(high_risk_sites, figures_path):
    """Create clean, professional distance distribution plot."""
    if 'Final_Distance_m' not in high_risk_sites.columns:
        print("No distance data found")
        return
    
    fig, ax = setup_professional_plot(figsize=(10, 6))
    
    distances = high_risk_sites['Final_Distance_m']
    
    # Clean histogram with single color
    ax.hist(distances, bins=25, color=COLORS['primary'], alpha=0.7, 
            edgecolor='white', linewidth=0.8)
    
    # Subtle grid
    ax.grid(True, alpha=0.3, linestyle='-', linewidth=0.5)
    ax.set_axisbelow(True)
    
    # Add key statistics as text
    mean_dist = distances.mean()
    median_dist = distances.median()
    
    # Simple vertical lines for statistics
    ax.axvline(median_dist, color=COLORS['neutral'], linestyle='--', 
               linewidth=2, alpha=0.8)
    
    # Clean labels
    ax.set_xlabel('Distance to River (meters)', fontsize=12)
    ax.set_ylabel('Number of Sites', fontsize=12)  # This is correct - one row per site in general assessment
    ax.set_title('Distance Distribution: High-Risk Sites (≤500m)', fontsize=14, pad=15)
    
    # Add statistics text box
    stats_text = f'Median: {median_dist:.0f}m\nMean: {mean_dist:.0f}m\nTotal: {len(distances):,} sites'
    ax.text(0.98, 0.98, stats_text, transform=ax.transAxes, 
            verticalalignment='top', horizontalalignment='right',
            bbox=dict(boxstyle='round,pad=0.4', facecolor='white', alpha=0.8, edgecolor='gray'),
            fontsize=10)
    
    safe_save_figure(figures_path, "01_distance_distribution")

def create_activity_distribution(high_risk_sites, figures_path):
    """Create professional activity distribution plot."""
    if 'Lokalitetensaktivitet' not in high_risk_sites.columns:
        print("No activity data found")
        return
    
    # Process activities
    all_activities = []
    for activities_str in high_risk_sites['Lokalitetensaktivitet'].dropna():
        activities = [act.strip() for act in str(activities_str).split(';') if act.strip()]
        all_activities.extend(activities)
    
    if not all_activities:
        print("No activity data to plot")
        return
    
    # Get top 15 activities
    activity_counts = pd.Series(all_activities).value_counts().head(15)
    
    fig, ax = setup_professional_plot(figsize=(12, 8))
    
    # Create horizontal bar chart
    y_pos = np.arange(len(activity_counts))
    colors = [COLORS['primary'] if i % 2 == 0 else COLORS['accent'] for i in range(len(activity_counts))]
    bars = ax.barh(y_pos, activity_counts.values, color=colors, alpha=0.8, edgecolor='white', linewidth=0.5)
    
    # Add count labels
    for i, (bar, count) in enumerate(zip(bars, activity_counts.values)):
        ax.text(count + max(activity_counts) * 0.01, i, f'{count}', 
                va='center', fontweight='bold', color=COLORS['neutral'])
    
    # Formatting
    ax.set_yticks(y_pos)
    ax.set_yticklabels(activity_counts.index, ha='right')
    ax.set_xlabel('Antal lokaliteter')
    ax.set_title('Top 15 lokalitetsaktiviteter (højrisiko-lokaliteter)')
    ax.invert_yaxis()
    
    # Add total count
    total_activities = len(all_activities)
    ax.text(0.02, 0.98, f'Total: {total_activities:,} aktivitetsforekomster', 
            transform=ax.transAxes, va='top', ha='left',
            bbox=dict(boxstyle='round,pad=0.3', facecolor=COLORS['light_gray'], alpha=0.8))
    
    safe_save_figure(figures_path, "02_activity_distribution")

def create_industry_distribution(high_risk_sites, figures_path):
    """Create professional industry distribution plot."""
    if 'Lokalitetensbranche' not in high_risk_sites.columns:
        print("No industry data found")
        return
    
    # Process industries
    all_industries = []
    for industries_str in high_risk_sites['Lokalitetensbranche'].dropna():
        industries = [ind.strip() for ind in str(industries_str).split(';') if ind.strip()]
        all_industries.extend(industries)
    
    if not all_industries:
        print("No industry data to plot")
        return
    
    # Get top 15 industries
    industry_counts = pd.Series(all_industries).value_counts().head(15)
    
    fig, ax = setup_professional_plot(figsize=(12, 8))
    
    # Create horizontal bar chart
    y_pos = np.arange(len(industry_counts))
    colors = [COLORS['secondary'] if i % 2 == 0 else COLORS['danger'] for i in range(len(industry_counts))]
    bars = ax.barh(y_pos, industry_counts.values, color=colors, alpha=0.8, edgecolor='white', linewidth=0.5)
    
    # Add count labels
    for i, (bar, count) in enumerate(zip(bars, industry_counts.values)):
        ax.text(count + max(industry_counts) * 0.01, i, f'{count}', 
                va='center', fontweight='bold', color=COLORS['neutral'])
    
    # Formatting
    ax.set_yticks(y_pos)
    ax.set_yticklabels(industry_counts.index, ha='right')
    ax.set_xlabel('Antal lokaliteter')
    ax.set_title('Top 15 lokalitetsbrancher (højrisiko-lokaliteter)')
    ax.invert_yaxis()
    
    # Add total count
    total_industries = len(all_industries)
    ax.text(0.02, 0.98, f'Total: {total_industries:,} brancheforekomster', 
            transform=ax.transAxes, va='top', ha='left',
            bbox=dict(boxstyle='round,pad=0.3', facecolor=COLORS['light_gray'], alpha=0.8))
    
    safe_save_figure(figures_path, "03_industry_distribution")

def create_substance_distribution(high_risk_sites, figures_path):
    """Create top 15 substances distribution plot for general assessment."""
    if 'Lokalitetensstoffer' not in high_risk_sites.columns:
        print("No substance data found")
        return
    
    # Collect all substances
    all_substances = []
    for _, row in high_risk_sites.iterrows():
        if pd.notna(row['Lokalitetensstoffer']):
            substances = str(row['Lokalitetensstoffer']).split(';')
            all_substances.extend([s.strip() for s in substances if s.strip()])
    
    # Count frequencies and get top 15
    substance_counts = Counter(all_substances)
    top_15 = substance_counts.most_common(15)
    
    if not top_15:
        print("No substance data to plot")
        return
    
    # Create plot
    fig, ax = setup_professional_plot(figsize=(12, 8))
    
    substances = [item[0] for item in top_15]
    counts = [item[1] for item in top_15]
    
    bars = ax.barh(range(len(substances)), counts, color=COLORS['accent'], alpha=0.8)
    
    # Add value labels
    for i, (bar, count) in enumerate(zip(bars, counts)):
        ax.text(bar.get_width() + max(counts)*0.01, bar.get_y() + bar.get_height()/2, 
               f'{count}', va='center', ha='left', fontweight='bold')
    
    ax.set_yticks(range(len(substances)))
    ax.set_yticklabels(substances)
    ax.set_xlabel('Number of Sites', fontsize=12)
    ax.set_title('Top 15 Substances (General Assessment - 500m threshold)', fontsize=14, pad=15)
    ax.grid(True, alpha=0.3, axis='x')
    ax.invert_yaxis()
    
    plt.tight_layout()
    safe_save_figure(figures_path, "04_top_substances_general")

# ============================================================================
# KEY RESULT VISUALIZATIONS
# ============================================================================

def create_threshold_cascade_visualization(figures_path):
    """Create the key threshold cascade visualization showing the filtering process."""
    from config import get_output_path
    
    try:
        general_file = get_output_path('step5_high_risk_sites')
        compound_file = get_output_path('step5_compound_detailed_combinations')
        
        if not os.path.exists(general_file) or not os.path.exists(compound_file):
            print("Step 5 output files not found - using default values")
            create_threshold_cascade_with_values(figures_path, 16934, 3606, 2097, 2803)
            return
            
        general_df = pd.read_csv(general_file)
        compound_df = pd.read_csv(compound_file)
        
        # Calculate actual values
        step4_input = 16934
        general_sites = len(general_df)
        compound_sites = compound_df['Lokalitet_ID'].nunique()
        compound_combinations = len(compound_df)
        
        create_threshold_cascade_with_values(figures_path, step4_input, general_sites, compound_sites, compound_combinations)
        
    except Exception as e:
        print(f"Error loading Step 5 data: {e}")
        create_threshold_cascade_with_values(figures_path, 16934, 3606, 2097, 2803)

def create_threshold_cascade_with_values(figures_path, step4_input, general_sites, compound_sites, compound_combinations):
    """Create the cascade visualization with specific values."""
    
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 8))
    
    # Left plot: Site filtering cascade
    stages = ['Step 4\nInput Sites', 'General\n(500m)', 'Compound-Specific\n(Variable thresholds)']
    values = [step4_input, general_sites, compound_sites]
    colors = [COLORS['neutral'], COLORS['primary'], COLORS['success']]
    
    bars1 = ax1.bar(stages, values, color=colors, alpha=0.8, edgecolor='white', linewidth=2)
    
    # Add value labels on bars
    for bar, value in zip(bars1, values):
        height = bar.get_height()
        ax1.text(bar.get_x() + bar.get_width()/2., height + height*0.01,
                f'{value:,}', ha='center', va='bottom', fontsize=14, fontweight='bold')
    
    # Add percentage reduction labels
    reduction1 = (step4_input - general_sites) / step4_input * 100
    reduction2 = (general_sites - compound_sites) / general_sites * 100
    
    ax1.annotate(f'-{reduction1:.1f}%', xy=(0.5, (step4_input + general_sites)/2), 
                ha='center', va='center', fontsize=12, color=COLORS['danger'],
                bbox=dict(boxstyle='round,pad=0.3', facecolor='white', edgecolor=COLORS['danger']))
    
    ax1.annotate(f'-{reduction2:.1f}%', xy=(1.5, (general_sites + compound_sites)/2),
                ha='center', va='center', fontsize=12, color=COLORS['danger'],
                bbox=dict(boxstyle='round,pad=0.3', facecolor='white', edgecolor=COLORS['danger']))
    
    ax1.set_ylabel('Number of Sites', fontsize=12, fontweight='bold')
    ax1.set_title('Site Filtering Cascade', fontsize=14, fontweight='bold')
    ax1.grid(True, alpha=0.3)
    ax1.set_ylim(0, step4_input * 1.1)
    
    # Right plot: Multi-substance analysis
    avg_substances = compound_combinations / compound_sites if compound_sites > 0 else 0
    
    categories = ['Unique Sites', 'Total Combinations', 'Avg. Substances\nper Site']
    values2 = [compound_sites, compound_combinations, avg_substances]
    colors2 = [COLORS['success'], COLORS['accent'], COLORS['purple']]
    
    bars2 = ax2.bar(categories, values2, color=colors2, alpha=0.8, edgecolor='white', linewidth=2)
    
    # Add value labels
    for bar, value in zip(bars2, values2):
        height = bar.get_height()
        if value == avg_substances:
            label = f'{value:.1f}'
        else:
            label = f'{value:,}'
        ax2.text(bar.get_x() + bar.get_width()/2., height + height*0.01,
                label, ha='center', va='bottom', fontsize=14, fontweight='bold')
    
    ax2.set_ylabel('Count / Average', fontsize=12, fontweight='bold')
    ax2.set_title('Multi-Substance Analysis', fontsize=14, fontweight='bold')
    ax2.grid(True, alpha=0.3)
    
    # Overall title
    key_result = f"KEY RESULT: {compound_sites:,} sites qualify with literature-based thresholds"
    fig.suptitle(f'Step 5: Compound-Specific Risk Assessment Results\n{key_result}', fontsize=16, fontweight='bold')
    
    plt.tight_layout()
    safe_save_figure(figures_path, "05_threshold_cascade_overview")

def create_compound_comparison_summary(figures_path):
    """Create stacked bar chart comparing compound distributions: 500m vs compound-specific thresholds."""
    from config import get_output_path
    from step5_risk_assessment import categorize_contamination_substance
    
    try:
        # Load the general 500m results
        general_file = get_output_path('step5_high_risk_sites')
        general_df = pd.read_csv(general_file)
        
        # Load the compound-specific results  
        compound_file = get_output_path('step5_compound_detailed_combinations')
        compound_df = pd.read_csv(compound_file)
        
        print(f"Loaded: {len(general_df)} general sites, {len(compound_df)} compound-specific combinations")
        
        # Count compound groups for 500m threshold
        general_compound_counts = {}
        for _, row in general_df.iterrows():
            if pd.notna(row.get('Lokalitetensstoffer')):
                substances = str(row['Lokalitetensstoffer']).split(';')
                site_compounds = set()
                for substance in substances:
                    substance = substance.strip()
                    if substance:
                        result = categorize_contamination_substance(substance)
                        if isinstance(result, tuple):
                            category = result[0]
                        else:
                            category = result
                        site_compounds.add(category)  # Include ALL categories including OTHER
                for compound in site_compounds:
                    general_compound_counts[compound] = general_compound_counts.get(compound, 0) + 1
        
        # Count compound groups for compound-specific threshold
        compound_compound_counts = {}
        for _, row in compound_df.iterrows():
            category = row.get('Qualifying_Category', 'Unknown')
            compound_compound_counts[category] = compound_compound_counts.get(category, 0) + 1
        
        # Ensure all categories are present in both
        all_categories = set(list(general_compound_counts.keys()) + list(compound_compound_counts.keys()))
        for cat in all_categories:
            if cat not in general_compound_counts:
                general_compound_counts[cat] = 0
            if cat not in compound_compound_counts:
                compound_compound_counts[cat] = 0
        
        # Sort categories by general count (descending)
        sorted_categories = sorted(all_categories, key=lambda x: general_compound_counts[x], reverse=True)
        
        # Create the comparison plot
        fig, ax = plt.subplots(figsize=(12, 8))
        
        x_pos = [0, 1.5]
        bar_width = 0.6
        
        # Updated colors for each compound category
        category_colors = {
            'PAHER': COLORS['danger'],
            'BTXER': COLORS['primary'],
            'CHLORINATED_SOLVENTS': COLORS['success'],
            'PESTICIDER': COLORS['secondary'],
            'UORGANISKE_FORBINDELSER': COLORS['purple'],
            'KLOREDE_KULBRINTER': COLORS['accent'],
            'PHENOLER': '#FF7043',
            'POLARE': '#26A69A',
            'OTHER': COLORS['other']  # Use specific gray for OTHER
        }
        
        # Create legend labels with cleaner names
        category_labels = {
            'PAHER': 'PAH',
            'BTXER': 'BTEX',
            'CHLORINATED_SOLVENTS': 'Chlorinated Solvents',
            'PESTICIDER': 'Pesticides',
            'UORGANISKE_FORBINDELSER': 'Inorganic Compounds',
            'KLOREDE_KULBRINTER': 'Chlorinated Hydrocarbons',
            'PHENOLER': 'Phenols',
            'POLARE': 'Polar Compounds',
            'OTHER': 'Other/Unidentified'
        }
        
        # Create stacked bars
        general_bottom = 0
        compound_bottom = 0
        
        legend_handles = []
        
        for category in sorted_categories:
            general_count = general_compound_counts[category]
            compound_count = compound_compound_counts[category]
            
            color = category_colors.get(category, COLORS['neutral'])
            label = category_labels.get(category, category.replace('_', ' ').title())
            
            # General threshold bar (left)
            if general_count > 0:
                ax.bar(x_pos[0], general_count, bar_width, bottom=general_bottom, 
                      color=color, alpha=0.8, edgecolor='white', linewidth=1)
                
                if general_count > 50:
                    ax.text(x_pos[0], general_bottom + general_count/2, f'{general_count}',
                           ha='center', va='center', fontweight='bold', color='white', fontsize=10)
                general_bottom += general_count
            
            # Compound-specific bar (right)  
            if compound_count > 0:
                ax.bar(x_pos[1], compound_count, bar_width, bottom=compound_bottom,
                      color=color, alpha=0.8, edgecolor='white', linewidth=1)
                
                if compound_count > 30:
                    ax.text(x_pos[1], compound_bottom + compound_count/2, f'{compound_count}',
                           ha='center', va='center', fontweight='bold', color='white', fontsize=10)
                compound_bottom += compound_count
            
            # Add to legend
            if general_count > 0 or compound_count > 0:
                legend_handles.append(plt.Rectangle((0,0), 1, 1, facecolor=color, alpha=0.8, label=label))
        
        # Customize the plot
        ax.set_xticks(x_pos)
        ax.set_xticklabels(['500m Universal\nThreshold', 'Compound-Specific\nThresholds'], fontsize=12, fontweight='bold')
        ax.set_ylabel('Number of Site-Compound Combinations', fontsize=12, fontweight='bold')
        ax.set_title('Compound Distribution Comparison: Universal vs Literature-Based Thresholds', 
                     fontsize=14, pad=20, fontweight='bold')
        
        # Add total counts above bars
        ax.text(x_pos[0], general_bottom + max(general_bottom, compound_bottom) * 0.02, 
               f'Total: {len(general_df):,} sites', 
               ha='center', va='bottom', fontsize=12, fontweight='bold')
        ax.text(x_pos[1], compound_bottom + max(general_bottom, compound_bottom) * 0.02, 
               f'Total: {compound_df["Lokalitet_ID"].nunique():,} sites\n({len(compound_df):,} combinations)', 
               ha='center', va='bottom', fontsize=12, fontweight='bold')
        
        # Add legend
        ax.legend(handles=legend_handles, loc='upper right', frameon=True, 
                 facecolor='white', edgecolor='gray', framealpha=0.9)
        
        # Grid for better readability
        ax.grid(True, alpha=0.3, axis='y', linestyle='--')
        ax.set_axisbelow(True)
        
        # Add summary text box
        reduction_pct = (1 - compound_df['Lokalitet_ID'].nunique() / len(general_df)) * 100
        
        # Calculate OTHER percentage
        other_general = general_compound_counts.get('OTHER', 0)
        other_compound = compound_compound_counts.get('OTHER', 0)
        other_pct_general = (other_general / sum(general_compound_counts.values()) * 100) if sum(general_compound_counts.values()) > 0 else 0
        other_pct_compound = (other_compound / sum(compound_compound_counts.values()) * 100) if sum(compound_compound_counts.values()) > 0 else 0
        
        textstr = f'''Key Results:
• {reduction_pct:.1f}% reduction in qualifying sites
• "OTHER" category: {other_pct_general:.1f}% (500m) vs {other_pct_compound:.1f}% (compound-specific)
• {len(compound_df) - compound_df["Lokalitet_ID"].nunique()} sites have multiple qualifying compounds'''
        
        ax.text(0.02, 0.98, textstr, transform=ax.transAxes, fontsize=10,
               verticalalignment='top', ha='left',
               bbox=dict(boxstyle='round,pad=0.5', facecolor=COLORS['light_gray'], 
                        edgecolor='gray', alpha=0.9))
        
        plt.tight_layout()
        safe_save_figure(figures_path, "06_compound_distribution_comparison")
        
        print(f"✓ Compound distribution comparison created")
        
    except Exception as e:
        print(f"Error creating compound comparison: {e}")
        import traceback
        traceback.print_exc()

# ============================================================================
# COMPOUND-SPECIFIC VISUALIZATIONS (INCLUDING OTHER)
# ============================================================================

def create_compound_boxplot_comparison(figures_path):
    """Create single plot with boxplots for ALL compound groups INCLUDING OTHER, colored by occurrence count."""
    from config import get_output_path
    import matplotlib.cm as cm
    
    try:
        # Load compound-specific results
        compound_file = get_output_path('step5_compound_detailed_combinations')
        if not os.path.exists(compound_file):
            print("Compound-specific results not found")
            return
            
        compound_df = pd.read_csv(compound_file)
        
        # Group data by compound category - INCLUDING OTHER
        category_distances = {}
        category_unique_sites = {}  # Track unique sites per category
        
        for _, row in compound_df.iterrows():
            category = row.get('Qualifying_Category', 'Unknown')
            distance = row.get('Final_Distance_m')
            site_id = row.get('Lokalitet_ID')
            
            if pd.notna(distance):  # No exclusion of OTHER
                if category not in category_distances:
                    category_distances[category] = []
                    category_unique_sites[category] = set()
                category_distances[category].append(distance)
                if pd.notna(site_id):
                    category_unique_sites[category].add(site_id)
        
        if not category_distances:
            print("No valid compound distance data found")
            return
        
        # Sort categories by median distance (highest first)
        category_items = [(cat, data) for cat, data in category_distances.items()]
        category_items.sort(key=lambda x: np.median(x[1]), reverse=True)
        
        categories = [item[0] for item in category_items]
        distances = [item[1] for item in category_items]
        category_counts = [len(data) for data in distances]  # Total occurrences
        unique_site_counts = [len(category_unique_sites.get(cat, set())) for cat in categories]
        
        # Create labels with both occurrence and site counts
        labels_with_counts = [f"{cat}\n({sites} sites, {occur} occur.)" 
                             for cat, sites, occur in zip(categories, unique_site_counts, category_counts)]
        
        # Create boxplot
        fig, ax = plt.subplots(figsize=(14, 8))
        
        # Create boxplots with category-specific colors
        box_plot = ax.boxplot(distances, labels=labels_with_counts, patch_artist=True)
        
        # Create color map based on occurrence count
        max_count = max(category_counts)
        min_count = min(category_counts)
        norm = plt.Normalize(vmin=min_count, vmax=max_count)
        cmap = cm.get_cmap('YlOrRd')  # Yellow to Orange to Red gradient
        
        # Color boxes based on occurrence count
        for i, (patch, category, count) in enumerate(zip(box_plot['boxes'], categories, category_counts)):
            if category == 'OTHER':
                patch.set_facecolor(COLORS['other'])
                patch.set_alpha(0.9)
                patch.set_edgecolor('black')
                patch.set_linewidth(2)
            else:
                # Color based on count using colormap
                color = cmap(norm(count))
                patch.set_facecolor(color)
                patch.set_alpha(0.8)
                patch.set_edgecolor('black')
                patch.set_linewidth(1.5)
        
        # Style other elements
        for element in ['whiskers', 'fliers', 'medians', 'caps']:
            for item in box_plot[element]:
                item.set_color('black')
        
        # Add colorbar for occurrence count
        sm = plt.cm.ScalarMappable(cmap=cmap, norm=norm)
        sm.set_array([])
        cbar = plt.colorbar(sm, ax=ax, pad=0.02, fraction=0.05)
        cbar.set_label('Number of Occurrences', rotation=270, labelpad=20)
        
        ax.set_ylabel('Distance to River (meters)', fontsize=12)
        ax.set_title('Distance Distribution by Compound Category (Colored by Occurrence Count)', fontsize=14, pad=15)
        ax.tick_params(axis='x', rotation=45)
        ax.grid(True, alpha=0.3, axis='y')
        
        # Add summary statistics
        total_unique_sites = len(set().union(*category_unique_sites.values())) if category_unique_sites else 0
        stats_text = f'Categories: {len(categories)}\nUnique sites: {total_unique_sites:,}\nTotal occurrences: {sum(category_counts):,}\nAvg occurrences/site: {sum(category_counts)/total_unique_sites:.1f}'
        ax.text(0.02, 0.98, stats_text, transform=ax.transAxes,
               verticalalignment='top', horizontalalignment='left',
               bbox=dict(boxstyle='round', facecolor='white', alpha=0.8, edgecolor='gray'))
        
        plt.tight_layout()
        safe_save_figure(figures_path, "07_compound_boxplot_with_other")
        
    except Exception as e:
        print(f"Error creating compound boxplot: {e}")

def create_category_prevalence_chart(figures_path):
    """Create donut chart showing the true distribution of ALL compound categories."""
    from config import get_output_path
    
    try:
        # Load compound-specific results
        compound_file = get_output_path('step5_compound_detailed_combinations')
        if not os.path.exists(compound_file):
            print("Compound-specific results not found")
            return
            
        compound_df = pd.read_csv(compound_file)
        
        # Count all categories INCLUDING OTHER
        category_counts = compound_df['Qualifying_Category'].value_counts()
        
        # Create figure with two subplots
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 8))
        
        # Left: Pie chart with all categories
        colors = []
        for cat in category_counts.index:
            if cat == 'OTHER':
                colors.append(COLORS['other'])
            else:
                colors.append(COLORS['categories'][len(colors) % len(COLORS['categories'])])
        
        wedges, texts, autotexts = ax1.pie(category_counts.values, 
                                            labels=category_counts.index,
                                            colors=colors,
                                            autopct='%1.1f%%',
                                            startangle=90)
        
        # Highlight OTHER category if it exists
        for i, cat in enumerate(category_counts.index):
            if cat == 'OTHER':
                wedges[i].set_edgecolor('black')
                wedges[i].set_linewidth(2)
        
        ax1.set_title('All Compound Categories Distribution\n(Including "OTHER")', 
                      fontsize=14, fontweight='bold')
        
        # Right: Bar chart comparing counts
        ax2.bar(range(len(category_counts)), category_counts.values, 
                color=colors, alpha=0.8)
        ax2.set_xticks(range(len(category_counts)))
        ax2.set_xticklabels(category_counts.index, rotation=45, ha='right')
        ax2.set_ylabel('Number of Site-Compound Combinations')
        ax2.set_title('Compound Category Counts\n(Absolute Numbers)', 
                      fontsize=14, fontweight='bold')
        
        # Add value labels on bars
        for i, (cat, count) in enumerate(category_counts.items()):
            ax2.text(i, count + max(category_counts)*0.01, f'{count:,}', 
                    ha='center', fontweight='bold')
        
        # Add summary statistics
        other_count = category_counts.get('OTHER', 0)
        other_pct = (other_count / category_counts.sum() * 100) if other_count > 0 else 0
        identified_count = category_counts.sum() - other_count
        
        summary_text = f'''Key Insights:
• Total categories: {len(category_counts)}
• "OTHER" compounds: {other_count:,} ({other_pct:.1f}%)
• Identified compounds: {identified_count:,} ({100-other_pct:.1f}%)
• Most common: {category_counts.index[0]} ({category_counts.values[0]:,})'''
        
        fig.text(0.5, 0.02, summary_text, ha='center', fontsize=11,
                bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))
        
        plt.tight_layout()
        safe_save_figure(figures_path, "09_category_prevalence_with_other")
        
        print(f"✓ Category prevalence chart created - OTHER: {other_pct:.1f}%")
        
    except Exception as e:
        print(f"Error creating category prevalence chart: {e}")

def create_category_sites_distribution(figures_path):
    """Create bar chart showing number of unique sites affected by each category."""
    from config import get_output_path
    
    try:
        # Load compound-specific results
        compound_file = get_output_path('step5_compound_detailed_combinations')
        if not os.path.exists(compound_file):
            print("Compound-specific results not found")
            return
            
        compound_df = pd.read_csv(compound_file)
        
        # Count unique sites per category
        category_sites = {}
        category_occurrences = {}
        
        for category in compound_df['Qualifying_Category'].unique():
            cat_data = compound_df[compound_df['Qualifying_Category'] == category]
            unique_sites = cat_data['Lokalitet_ID'].nunique()
            total_occurrences = len(cat_data)
            category_sites[category] = unique_sites
            category_occurrences[category] = total_occurrences
        
        # Sort by number of sites (descending)
        sorted_categories = sorted(category_sites.items(), key=lambda x: x[1], reverse=True)
        
        categories = [cat for cat, _ in sorted_categories]
        site_counts = [count for _, count in sorted_categories]
        occurrence_counts = [category_occurrences[cat] for cat in categories]
        
        # Create figure with two subplots
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 8))
        
        # Left plot: Sites per category
        colors1 = []
        for cat in categories:
            if cat == 'OTHER':
                colors1.append(COLORS['other'])
            else:
                colors1.append(COLORS['categories'][len(colors1) % len(COLORS['categories'])])
        
        bars1 = ax1.bar(range(len(categories)), site_counts, color=colors1, alpha=0.8, edgecolor='black', linewidth=1)
        
        # Add value labels
        for i, (bar, count) in enumerate(zip(bars1, site_counts)):
            ax1.text(bar.get_x() + bar.get_width()/2, bar.get_height() + max(site_counts)*0.01,
                    f'{count}', ha='center', va='bottom', fontweight='bold')
        
        ax1.set_xticks(range(len(categories)))
        ax1.set_xticklabels(categories, rotation=45, ha='right')
        ax1.set_ylabel('Number of Unique Sites', fontsize=12)
        ax1.set_title('Unique Sites Affected by Each Category', fontsize=14, fontweight='bold')
        ax1.grid(True, alpha=0.3, axis='y')
        
        # Right plot: Occurrences vs Sites comparison
        x = np.arange(len(categories))
        width = 0.35
        
        bars2a = ax2.bar(x - width/2, site_counts, width, label='Unique Sites', 
                        color=COLORS['primary'], alpha=0.8)
        bars2b = ax2.bar(x + width/2, occurrence_counts, width, label='Total Occurrences',
                        color=COLORS['secondary'], alpha=0.8)
        
        # Add value labels
        for bar, count in zip(bars2a, site_counts):
            if count > 0:
                ax2.text(bar.get_x() + bar.get_width()/2, bar.get_height() + max(occurrence_counts)*0.01,
                        f'{count}', ha='center', va='bottom', fontsize=9)
        
        for bar, count in zip(bars2b, occurrence_counts):
            if count > 0:
                ax2.text(bar.get_x() + bar.get_width()/2, bar.get_height() + max(occurrence_counts)*0.01,
                        f'{count}', ha='center', va='bottom', fontsize=9)
        
        ax2.set_xlabel('Category')
        ax2.set_ylabel('Count')
        ax2.set_title('Sites vs Occurrences by Category', fontsize=14, fontweight='bold')
        ax2.set_xticks(x)
        ax2.set_xticklabels(categories, rotation=45, ha='right')
        ax2.legend()
        ax2.grid(True, alpha=0.3, axis='y')
        
        # Add summary statistics
        total_sites = compound_df['Lokalitet_ID'].nunique()
        total_occurrences = len(compound_df)
        avg_substances_per_site = total_occurrences / total_sites if total_sites > 0 else 0
        
        summary_text = f'''Summary Statistics:
• Total unique sites: {total_sites:,}
• Total occurrences: {total_occurrences:,}
• Average substances/site: {avg_substances_per_site:.1f}
• Categories: {len(categories)}'''
        
        fig.text(0.5, 0.02, summary_text, ha='center', fontsize=11,
                bbox=dict(boxstyle='round', facecolor=COLORS['light_gray'], alpha=0.8))
        
        plt.suptitle('Category Impact Analysis: Sites and Occurrences', fontsize=16, fontweight='bold', y=1.02)
        plt.tight_layout()
        safe_save_figure(figures_path, "08_category_sites_distribution")
        
        print(f"✓ Category sites distribution created")
        
    except Exception as e:
        print(f"Error creating category sites distribution: {e}")

def create_other_category_analysis(figures_path):
    """Analyze and visualize the composition of the OTHER category."""
    from config import get_output_path
    
    try:
        compound_file = get_output_path('step5_compound_detailed_combinations')
        if not os.path.exists(compound_file):
            print("Compound-specific results not found")
            return
            
        compound_df = pd.read_csv(compound_file)
        
        # Filter for OTHER category only
        other_df = compound_df[compound_df['Qualifying_Category'] == 'OTHER']
        
        if other_df.empty:
            print("No OTHER category data found")
            return
        
        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(16, 12))
        
        # 1. Distance distribution for OTHER
        distances = other_df['Final_Distance_m']
        ax1.hist(distances, bins=30, color=COLORS['other'], alpha=0.7, edgecolor='black')
        ax1.axvline(distances.mean(), color='black', linestyle='--', 
                    label=f'Mean: {distances.mean():.0f}m')
        ax1.axvline(distances.median(), color='red', linestyle='--',
                    label=f'Median: {distances.median():.0f}m')
        ax1.set_xlabel('Distance to River (m)')
        ax1.set_ylabel('Count')
        ax1.set_title(f'OTHER Category: Distance Distribution (n={len(distances)})')
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        
        # 2. Top substances in OTHER category
        substances = other_df['Qualifying_Substance'].value_counts().head(15)
        if not substances.empty:
            ax2.barh(range(len(substances)), substances.values, color=COLORS['other'], alpha=0.8)
            ax2.set_yticks(range(len(substances)))
            ax2.set_yticklabels(substances.index, fontsize=9)
            ax2.set_xlabel('Count')
            ax2.set_title('Top 15 Substances in OTHER Category')
            ax2.invert_yaxis()
            
            # Add count labels
            for i, count in enumerate(substances.values):
                ax2.text(count + max(substances)*0.01, i, f'{count}', 
                        va='center', fontweight='bold')
        
        # 3. Activities associated with OTHER
        if 'Lokalitetensaktivitet' in other_df.columns:
            activities = []
            for act_str in other_df['Lokalitetensaktivitet'].dropna():
                activities.extend([a.strip() for a in str(act_str).split(';') if a.strip()])
            
            if activities:
                act_counts = pd.Series(activities).value_counts().head(10)
                
                ax3.barh(range(len(act_counts)), act_counts.values, color='#A0A0A0', alpha=0.8)
                ax3.set_yticks(range(len(act_counts)))
                ax3.set_yticklabels(act_counts.index, fontsize=9)
                ax3.set_xlabel('Count')
                ax3.set_title('Top 10 Activities Associated with OTHER Compounds')
                ax3.invert_yaxis()
        
        # 4. Distance comparison: OTHER vs all other categories
        non_other_df = compound_df[compound_df['Qualifying_Category'] != 'OTHER']
        
        if not non_other_df.empty:
            other_distances = other_df['Final_Distance_m'].dropna()
            non_other_distances = non_other_df['Final_Distance_m'].dropna()
            
            bp = ax4.boxplot([other_distances, non_other_distances], 
                              labels=['OTHER\nCompounds', 'Identified\nCompounds'],
                              patch_artist=True)
            bp['boxes'][0].set_facecolor(COLORS['other'])
            bp['boxes'][1].set_facecolor(COLORS['success'])
            
            ax4.set_ylabel('Distance to River (m)')
            ax4.set_title('Distance Comparison: OTHER vs Identified Compounds')
            ax4.grid(True, alpha=0.3)
            
            # Add statistics annotation
            stats_text = f'OTHER median: {other_distances.median():.0f}m\nIdentified median: {non_other_distances.median():.0f}m\nOTHER sites: {len(other_distances):,}\nIdentified sites: {len(non_other_distances):,}'
            ax4.text(0.02, 0.98, stats_text, transform=ax4.transAxes,
                     verticalalignment='top', 
                     bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))
        
        plt.suptitle('Deep Dive: "OTHER" Category Analysis', fontsize=16, fontweight='bold')
        plt.tight_layout()
        safe_save_figure(figures_path, "10_other_category_deep_dive")
        
        print(f"✓ OTHER category analysis created - {len(other_df)} combinations analyzed")
        
    except Exception as e:
        print(f"Error creating OTHER category analysis: {e}")

def create_essential_compound_plots(figures_path):
    """Create essential plots for each compound group INCLUDING OTHER."""
    from config import get_output_path
    
    try:
        # Load compound-specific results
        compound_file = get_output_path('step5_compound_detailed_combinations')
        if not os.path.exists(compound_file):
            print("Compound-specific results not found")
            return
            
        compound_df = pd.read_csv(compound_file)
        
        # Get all unique categories INCLUDING OTHER
        categories = compound_df['Qualifying_Category'].unique()
        
        # Process top 5 categories by occurrence count
        category_counts = compound_df['Qualifying_Category'].value_counts()
        top_categories = category_counts.head(5).index.tolist()
        
        for category in top_categories:
            category_data = compound_df[compound_df['Qualifying_Category'] == category]
            
            # Create 3 plots for each category
            create_compound_distance_histogram(category_data, category, figures_path)
            create_compound_activity_distribution(category_data, category, figures_path)
            create_compound_industry_distribution(category_data, category, figures_path)
            
        print(f"✓ Created {len(top_categories) * 3} compound-specific detail plots")
        
    except Exception as e:
        print(f"Error creating essential compound plots: {e}")

def create_compound_distance_histogram(category_data, category, figures_path):
    """Create distance histogram for specific compound category."""
    distances = category_data['Final_Distance_m'].dropna()
    if len(distances) == 0:
        return
    
    # Count unique sites vs occurrences
    unique_sites = category_data['Lokalitet_ID'].nunique()
    total_occurrences = len(distances)
    
    fig, ax = plt.subplots(figsize=(10, 6))
    
    # Use gray color for OTHER, category color for others
    color = COLORS['other'] if category == 'OTHER' else COLORS['primary']
    
    ax.hist(distances, bins=30, color=color, alpha=0.7, edgecolor='white', linewidth=0.5)
    
    ax.set_xlabel('Distance to River (meters)', fontsize=12)
    ax.set_ylabel('Number of Occurrences', fontsize=12)
    ax.set_title(f'{category}: Distance Distribution ({unique_sites:,} unique sites, {total_occurrences:,} occurrences)', fontsize=14)
    ax.grid(True, alpha=0.3)
    
    # Add statistics
    mean_dist = distances.mean()
    median_dist = distances.median()
    ax.axvline(mean_dist, color='red', linestyle='--', alpha=0.8, label=f'Mean: {mean_dist:.0f}m')
    ax.axvline(median_dist, color='orange', linestyle='--', alpha=0.8, label=f'Median: {median_dist:.0f}m')
    ax.legend()
    
    plt.tight_layout()
    safe_filename = category.replace(' ', '_').replace('/', '_').lower()
    safe_save_figure(figures_path, f"11_{safe_filename}_distance_histogram")

def create_compound_activity_distribution(category_data, category, figures_path):
    """Create top activities for specific compound category."""
    if 'Lokalitetensaktivitet' not in category_data.columns:
        return
        
    activities = category_data['Lokalitetensaktivitet'].dropna()
    
    # Split semicolon-separated values
    activity_list = []
    for activity_string in activities:
        individual_activities = [act.strip() for act in str(activity_string).split(';') if act.strip()]
        activity_list.extend(individual_activities)
    
    if len(activity_list) == 0:
        return
    
    # Count occurrences and get top 10
    from collections import Counter
    activity_counts = Counter(activity_list)
    top_activities = dict(activity_counts.most_common(10))
    
    if len(top_activities) == 0:
        return
    
    fig, ax = plt.subplots(figsize=(12, 6))
    
    # Use appropriate color
    color = COLORS['other'] if category == 'OTHER' else COLORS['secondary']
    
    # Create horizontal bar chart
    y_pos = range(len(top_activities))
    bars = ax.barh(y_pos, list(top_activities.values()), color=color, alpha=0.8)
    
    # Add value labels
    for i, (bar, count) in enumerate(zip(bars, top_activities.values())):
        ax.text(bar.get_width() + max(top_activities.values())*0.01, bar.get_y() + bar.get_height()/2, 
               f'{count}', va='center', ha='left', fontweight='bold')
    
    ax.set_yticks(y_pos)
    ax.set_yticklabels(list(top_activities.keys()))
    ax.set_xlabel('Antal forekomster', fontsize=12)
    
    unique_sites = len(activities)
    unique_activities = len(activity_counts)
    ax.set_title(f'{category}: Top Aktiviteter ({unique_sites:,} sites, {unique_activities:,} unikke aktiviteter)', fontsize=14)
    ax.grid(True, alpha=0.3, axis='x')
    ax.invert_yaxis()
    
    plt.tight_layout()
    safe_filename = category.replace(' ', '_').replace('/', '_').lower()
    safe_save_figure(figures_path, f"12_{safe_filename}_activities")

def create_compound_industry_distribution(category_data, category, figures_path):
    """Create top industries for specific compound category."""
    if 'Lokalitetensbranche' not in category_data.columns:
        return
        
    industries = category_data['Lokalitetensbranche'].dropna()
    
    # Split semicolon-separated values
    industry_list = []
    for industry_string in industries:
        individual_industries = [ind.strip() for ind in str(industry_string).split(';') if ind.strip()]
        industry_list.extend(individual_industries)
    
    if len(industry_list) == 0:
        return
    
    # Count occurrences and get top 10
    from collections import Counter
    industry_counts = Counter(industry_list)
    top_industries = dict(industry_counts.most_common(10))
    
    if len(top_industries) == 0:
        return
    
    fig, ax = plt.subplots(figsize=(12, 6))
    
    # Use appropriate color
    color = COLORS['other'] if category == 'OTHER' else COLORS['success']
    
    # Create horizontal bar chart
    y_pos = range(len(top_industries))
    bars = ax.barh(y_pos, list(top_industries.values()), color=color, alpha=0.8)
    
    # Add value labels
    for i, (bar, count) in enumerate(zip(bars, top_industries.values())):
        ax.text(bar.get_width() + max(top_industries.values())*0.01, bar.get_y() + bar.get_height()/2, 
               f'{count}', va='center', ha='left', fontweight='bold')
    
    ax.set_yticks(y_pos)
    ax.set_yticklabels(list(top_industries.keys()))
    ax.set_xlabel('Antal forekomster', fontsize=12)
    
    unique_sites = len(industries)
    unique_industries = len(industry_counts)
    ax.set_title(f'{category}: Top Brancher ({unique_sites:,} sites, {unique_industries:,} unikke brancher)', fontsize=14)
    ax.grid(True, alpha=0.3, axis='x')
    ax.invert_yaxis()
    
    plt.tight_layout()
    safe_filename = category.replace(' ', '_').replace('/', '_').lower()
    safe_save_figure(figures_path, f"13_{safe_filename}_industries")

if __name__ == "__main__":
    """Main execution block - run this file directly to create all Step 5 visualizations."""
    import sys
    from pathlib import Path
    
    print("=" * 60)
    print("STEP 5 VISUALIZATIONS - Direct Execution")
    print("=" * 60)
    
    try:
        from config import get_output_path, get_visualization_path
        
        # Check if required data files exist
        required_files = [
            ('step5_high_risk_sites', 'General high-risk sites (500m threshold)'),
            ('step5_compound_detailed_combinations', 'Compound-specific combinations'),
            ('step5_compound_specific_sites', 'Compound-specific filtered sites')
        ]
        
        print("Checking required data files...")
        missing_files = []
        
        for file_key, description in required_files:
            file_path = get_output_path(file_key)
            if os.path.exists(file_path):
                print(f"✓ {description}: Found")
            else:
                print(f"✗ {description}: Missing - {file_path}")
                missing_files.append((file_key, description))
        
        if missing_files:
            print("\n" + "=" * 60)
            print("ERROR: Missing required data files!")
            print("Please run the main workflow first to generate the data:")
            print("  python main_workflow.py")
            print("\nMissing files:")
            for file_key, desc in missing_files:
                print(f"  - {desc}")
            print("=" * 60)
            sys.exit(1)
        
        print("\n" + "=" * 60)
        print("All required files found! Creating visualizations...")
        print("=" * 60)
        
        # Create all Step 5 visualizations
        create_step5_visualizations()
        
        print("\n" + "=" * 60)
        print("SUCCESS: All Step 5 visualizations completed!")
        print(f"Files saved to: {get_visualization_path('step5')}")
        print("=" * 60)
        
    except ImportError as e:
        print(f"\nERROR: Missing required modules - {e}")
        print("Make sure you're running from the correct directory with all dependencies installed.")
        sys.exit(1)
        
    except Exception as e:
        print(f"\nERROR: Failed to create visualizations - {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)