"""
Step 5 Visualizations: Professional Risk Assessment Plots

Creates clean, professional visualizations for contamination risk assessment:
- Broad analysis using 500m threshold
- Compound-specific analysis using category-based thresholds
- Proper handling of "ANDRE" category
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
    
    # 2. Key Result Visualizations - REMOVED UNNECESSARY PLOTS
    
    # 3. Compound-Specific Analysis (INCLUDING OTHER)
    print("\nCreating compound-specific analysis...")
    create_compound_boxplot_comparison(figures_path)
    create_category_sites_distribution(figures_path)  # Keep this - shows sites per category
    
    # 4. Per Compound Group Details
    print("\nCreating detailed compound-specific plots...")
    create_essential_compound_plots(figures_path)
    
    print(f"\nâœ“ All Step 5 visualizations completed in: {figures_path}")

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
    ax.set_title('Distance Distribution: High-Risk Sites (â‰¤500m)', fontsize=14, pad=15)
    
    # Add statistics text box
    stats_text = f'Median: {median_dist:.0f}m\nMean: {mean_dist:.0f}m\nTotal: {high_risk_sites['Lokalitet_ID'].nunique():,} sites'
    
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
    ax.set_title('Top 15 lokalitetsaktiviteter (hÃ¸jrisiko-lokaliteter)')
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
    ax.set_title('Top 15 lokalitetsbrancher (hÃ¸jrisiko-lokaliteter)')
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
# COMPOUND-SPECIFIC VISUALIZATIONS
# ============================================================================

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
            if category == 'ANDRE':
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
            if cat == 'ANDRE':
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
â€¢ Total unique sites: {total_sites:,}
â€¢ Total occurrences: {total_occurrences:,}
â€¢ Average substances/site: {avg_substances_per_site:.1f}
â€¢ Categories: {len(categories)}'''
        
        fig.text(0.5, 0.02, summary_text, ha='center', fontsize=11,
                bbox=dict(boxstyle='round', facecolor=COLORS['light_gray'], alpha=0.8))
        
        plt.suptitle('Category Impact Analysis: Sites and Occurrences', fontsize=16, fontweight='bold', y=1.02)
        plt.tight_layout()
        safe_save_figure(figures_path, "08_category_sites_distribution")
        
        print(f"âœ“ Category sites distribution created")
        
    except Exception as e:
        print(f"Error creating category sites distribution: {e}")

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
            
        print(f"âœ“ Created {len(top_categories) * 3} compound-specific detail plots")
        
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
    
    # Use gray color for ANDRE, category color for others
    color = COLORS['other'] if category == 'ANDRE' else COLORS['primary']
    
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
    color = COLORS['other'] if category == 'ANDRE' else COLORS['secondary']
    
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
    color = COLORS['other'] if category == 'ANDRE' else COLORS['success']
    
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
                print(f"âœ“ {description}: Found")
            else:
                print(f"âœ— {description}: Missing - {file_path}")
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
