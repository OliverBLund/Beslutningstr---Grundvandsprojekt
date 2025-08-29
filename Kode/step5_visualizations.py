"""
Step 5 Visualizations: Analysis of High-Risk V1/V2 Sites (≤500m from rivers)

Creates specialized visualizations for contamination risk assessment of sites
within 500m of rivers, including distance distributions and contamination characteristics.
"""

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import seaborn as sns
import numpy as np
import os
from collections import Counter
import textwrap

# Set matplotlib style for better-looking plots
plt.style.use('default')
sns.set_palette("Set2")

def safe_save_figure(figures_path, filename_base, dpi=300):
    """Save figure with error handling for permission issues."""
    png_path = os.path.join(figures_path, f"{filename_base}.png")
    
    # Save PNG only
    plt.savefig(png_path, dpi=dpi, bbox_inches='tight')

def create_step5_visualizations(results_path="Resultater", threshold_m=500):
    """
    Create all Step 5 visualizations.
    
    Args:
        results_path (str): Path to results directory
        threshold_m (int): Distance threshold used (default 500m)
    """
    print(f"Creating Step 5 visualizations for sites ≤{threshold_m}m from rivers...")
    
    # Use config-based path for Step 5 visualizations
    from config import get_visualization_path, get_output_path
    figures_path = get_visualization_path('step5')
    
    # Load high-risk sites data using config path
    high_risk_file = get_output_path('step5_high_risk_sites', threshold_m)
    
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
    
    # Create visualizations
    create_distance_distribution_plot(high_risk_sites, figures_path, threshold_m)
    create_site_type_analysis(high_risk_sites, figures_path, threshold_m)
    create_contamination_source_analysis(high_risk_sites, figures_path, threshold_m)
    create_contamination_activity_analysis(high_risk_sites, figures_path, threshold_m)
    create_contamination_substances_analysis(high_risk_sites, figures_path, threshold_m)
    create_multi_gvfk_analysis(high_risk_sites, figures_path, threshold_m)
    create_comprehensive_risk_dashboard(high_risk_sites, figures_path, threshold_m)
    
    print(f"All Step 5 visualizations created in: {figures_path}")

def create_distance_distribution_plot(high_risk_sites, figures_path, threshold_m):
    """Create distance distribution plots for high-risk sites."""
    print("Creating distance distribution plots...")
    
    if 'Final_Distance_m' not in high_risk_sites.columns:
        print("No distance data found for distribution plots")
        return
    
    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(16, 12))
    
    distances = high_risk_sites['Final_Distance_m']
    
    # 1. Histogram with detailed bins
    bins = range(0, threshold_m + 50, 50)  # 50m intervals up to threshold
    ax1.hist(distances, bins=bins, color='#2E8B57', alpha=0.7, edgecolor='black', linewidth=0.5)
    ax1.set_title(f'Afstandsfordeling for højrisiko-lokaliteter\n(≤{threshold_m}m fra kontaktzoner)', fontsize=12, fontweight='bold')
    ax1.set_xlabel('Afstand (meter)', fontsize=10)
    ax1.set_ylabel('Antal lokaliteter', fontsize=10)
    ax1.grid(True, alpha=0.3)
    
    # Add statistics
    stats_text = f'Antal: {len(distances)}\nGennemsnit: {distances.mean():.0f}m\nMedian: {distances.median():.0f}m'
    ax1.text(0.98, 0.98, stats_text, transform=ax1.transAxes, 
             verticalalignment='top', horizontalalignment='right',
             bbox=dict(boxstyle='round', facecolor='white', alpha=0.9), fontsize=9)
    
    # 2. Cumulative distribution
    sorted_distances = np.sort(distances)
    cumulative = np.arange(1, len(sorted_distances) + 1) / len(sorted_distances)
    ax2.plot(sorted_distances, cumulative, 'b-', linewidth=2, label='Kumulativ fordeling')
    
    # Add threshold lines
    thresholds = [100, 200, 300, 400, 500]
    colors = ['green', 'yellowgreen', 'gold', 'orange', 'red']
    
    for i, thresh in enumerate(thresholds):
        if thresh <= threshold_m:
            within_count = (distances <= thresh).sum()
            percentage = within_count / len(distances) * 100
            ax2.axvline(thresh, color=colors[i], linestyle='--', alpha=0.7, 
                       label=f'{thresh}m: {percentage:.1f}%')
    
    ax2.set_title(f'Kumulativ afstandsfordeling (≤{threshold_m}m)', fontsize=12, fontweight='bold')
    ax2.set_xlabel('Afstand (meter)', fontsize=10)
    ax2.set_ylabel('Kumulativ andel', fontsize=10)
    ax2.legend(fontsize=8)
    ax2.grid(True, alpha=0.3)
    
    # 3. Box plot by site type (if available)
    if 'Site_Type' in high_risk_sites.columns:
        site_types = high_risk_sites['Site_Type'].unique()
        distance_by_type = [high_risk_sites[high_risk_sites['Site_Type'] == st]['Final_Distance_m'] 
                           for st in site_types]
        
        box_plot = ax3.boxplot(distance_by_type, labels=site_types, patch_artist=True)
        colors = ['#1f77b4', '#ff7f0e', '#2ca02c']
        for patch, color in zip(box_plot['boxes'], colors[:len(site_types)]):
            patch.set_facecolor(color)
            patch.set_alpha(0.7)
        
        ax3.set_title('Afstandsfordeling efter lokalitetstype', fontsize=12, fontweight='bold')
        ax3.set_ylabel('Afstand (meter)', fontsize=10)
        ax3.grid(True, alpha=0.3)
    else:
        ax3.text(0.5, 0.5, 'Ingen lokalitetstypedata\ntilgængelig', 
                 transform=ax3.transAxes, ha='center', va='center', fontsize=12)
        ax3.set_title('Lokalitetstype ikke tilgængelig', fontsize=12)
    
    # 4. Distance intervals breakdown
    interval_labels = ['0-100m', '101-200m', '201-300m', '301-400m', '401-500m']
    interval_counts = []
    
    for i in range(5):
        lower = i * 100
        upper = (i + 1) * 100
        count = ((distances > lower) & (distances <= upper)).sum()
        interval_counts.append(count)
    
    bars = ax4.bar(interval_labels, interval_counts, color=['#006400', '#228B22', '#FFD700', '#FF6347', '#DC143C'])
    ax4.set_title('Lokaliteter efter afstandsintervaller', fontsize=12, fontweight='bold')
    ax4.set_ylabel('Antal lokaliteter', fontsize=10)
    ax4.tick_params(axis='x', rotation=45)
    
    # Add count labels on bars
    for bar, count in zip(bars, interval_counts):
        height = bar.get_height()
        ax4.text(bar.get_x() + bar.get_width()/2., height + 0.5,
                f'{count}', ha='center', va='bottom', fontsize=9)
    
    ax4.grid(True, alpha=0.3)
    
    plt.tight_layout()
    safe_save_figure(figures_path, "step5_distance_analysis")
    plt.close()

def create_site_type_analysis(high_risk_sites, figures_path, threshold_m):
    """Create site type distribution analysis."""
    print("Creating site type analysis...")
    
    if 'Site_Type' not in high_risk_sites.columns:
        print("No site type data available")
        return
    
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
    
    # Site type counts
    type_counts = high_risk_sites['Site_Type'].value_counts()
    
    # Pie chart
    colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728']
    wedges, texts, autotexts = ax1.pie(type_counts.values, labels=type_counts.index, 
                                       autopct='%1.1f%%', colors=colors, startangle=90)
    ax1.set_title(f'Lokalitetstyper blandt højrisiko-lokaliteter\n(≤{threshold_m}m, n={len(high_risk_sites)})', 
                  fontsize=12, fontweight='bold')
    
    # Bar chart with counts
    bars = ax2.bar(type_counts.index, type_counts.values, color=colors[:len(type_counts)])
    ax2.set_title('Antal lokaliteter efter type', fontsize=12, fontweight='bold')
    ax2.set_ylabel('Antal lokaliteter', fontsize=10)
    ax2.tick_params(axis='x', rotation=45)
    
    # Add count labels on bars
    for bar, count in zip(bars, type_counts.values):
        height = bar.get_height()
        ax2.text(bar.get_x() + bar.get_width()/2., height + 0.5,
                f'{count}', ha='center', va='bottom', fontsize=10)
    
    ax2.grid(True, alpha=0.3)
    
    plt.tight_layout()
    safe_save_figure(figures_path, "step5_site_type_analysis")
    plt.close()

def create_contamination_source_analysis(high_risk_sites, figures_path, threshold_m):
    """Create analysis of contamination sources (Lokalitetensbranche)."""
    print("Creating contamination source analysis...")
    
    if 'Lokalitetensbranche' not in high_risk_sites.columns:
        print("No contamination source data available")
        return
    
    # Filter to non-null values
    source_data = high_risk_sites['Lokalitetensbranche'].dropna()
    
    if source_data.empty:
        print("No valid contamination source data")
        return
    
    # Handle semicolon-separated values properly
    all_sources = []
    sites_with_source = {}
    
    for idx, value in source_data.items():
        if pd.notna(value) and str(value).strip():
            # Split by semicolon and clean up
            sources = [src.strip() for src in str(value).split(';') if src.strip()]
            all_sources.extend(sources)
            
            # Track unique sites for each source
            for src in sources:
                if src not in sites_with_source:
                    sites_with_source[src] = set()
                sites_with_source[src].add(idx)
    
    # Count by occurrences (how many times each source appears)
    source_counts = pd.Series(all_sources).value_counts().head(15)  # Top 15 sources
    
    # Also get site counts (how many unique sites have each source)
    source_site_counts = {src: len(sites) for src, sites in sites_with_source.items()}
    top_sources_by_sites = dict(sorted(source_site_counts.items(), key=lambda x: x[1], reverse=True)[:15])
    
    # Create horizontal bar chart showing both occurrences and unique sites
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(20, 10))
    
    # Left plot: Occurrences (how many times each source appears)
    wrapped_labels_occ = [textwrap.fill(label, 30) for label in source_counts.index]
    
    bars1 = ax1.barh(range(len(source_counts)), source_counts.values, 
                     color=plt.cm.Set3(np.linspace(0, 1, len(source_counts))))
    
    ax1.set_yticks(range(len(source_counts)))
    ax1.set_yticklabels(wrapped_labels_occ)
    ax1.set_xlabel('Antal forekomster', fontsize=12)
    ax1.set_title(f'Top forureningskilder - Forekomster\n(≤{threshold_m}m, total: {len(all_sources)} forekomster)', 
                  fontsize=12, fontweight='bold')
    
    # Add count labels on bars
    for i, (bar, count) in enumerate(zip(bars1, source_counts.values)):
        width = bar.get_width()
        ax1.text(width + 0.5, bar.get_y() + bar.get_height()/2.,
                f'{count}', ha='left', va='center', fontsize=10)
    
    # Right plot: Unique sites (how many different sites have each source)
    top_sources_by_sites_series = pd.Series(top_sources_by_sites).head(15)
    wrapped_labels_sites = [textwrap.fill(label, 30) for label in top_sources_by_sites_series.index]
    
    bars2 = ax2.barh(range(len(top_sources_by_sites_series)), top_sources_by_sites_series.values, 
                     color=plt.cm.Spectral(np.linspace(0, 1, len(top_sources_by_sites_series))))
    
    ax2.set_yticks(range(len(top_sources_by_sites_series)))
    ax2.set_yticklabels(wrapped_labels_sites)
    ax2.set_xlabel('Antal unikke lokaliteter', fontsize=12)
    ax2.set_title(f'Top forureningskilder - Unikke lokaliteter\n(≤{threshold_m}m, {len(source_data)} lokaliteter med data)', 
                  fontsize=12, fontweight='bold')
    
    # Add count labels on bars
    for i, (bar, count) in enumerate(zip(bars2, top_sources_by_sites_series.values)):
        width = bar.get_width()
        ax2.text(width + 0.5, bar.get_y() + bar.get_height()/2.,
                f'{count}', ha='left', va='center', fontsize=10)
    
    ax1.grid(True, alpha=0.3, axis='x')
    ax2.grid(True, alpha=0.3, axis='x')
    
    plt.tight_layout()
    safe_save_figure(figures_path, "step5_contamination_sources")
    plt.close()

def create_contamination_activity_analysis(high_risk_sites, figures_path, threshold_m):
    """Create analysis of contamination activities (Lokalitetensaktivitet)."""
    print("Creating contamination activity analysis...")
    
    if 'Lokalitetensaktivitet' not in high_risk_sites.columns:
        print("No contamination activity data available")
        return
    
    # Filter to non-null values
    activity_data = high_risk_sites['Lokalitetensaktivitet'].dropna()
    
    if activity_data.empty:
        print("No valid contamination activity data")
        return
    
    # Handle semicolon-separated values properly
    all_activities = []
    sites_with_activity = {}
    
    for idx, value in activity_data.items():
        if pd.notna(value) and str(value).strip():
            # Split by semicolon and clean up
            activities = [act.strip() for act in str(value).split(';') if act.strip()]
            all_activities.extend(activities)
            
            # Track unique sites for each activity
            for act in activities:
                if act not in sites_with_activity:
                    sites_with_activity[act] = set()
                sites_with_activity[act].add(idx)
    
    # Count by occurrences and unique sites
    activity_counts = pd.Series(all_activities).value_counts().head(15)  # Top 15 activities
    activity_site_counts = {act: len(sites) for act, sites in sites_with_activity.items()}
    top_activities_by_sites = dict(sorted(activity_site_counts.items(), key=lambda x: x[1], reverse=True)[:15])
    
    # Create horizontal bar chart showing both occurrences and unique sites
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(20, 10))
    
    # Left plot: Occurrences
    wrapped_labels_occ = [textwrap.fill(label, 30) for label in activity_counts.index]
    
    bars1 = ax1.barh(range(len(activity_counts)), activity_counts.values, 
                     color=plt.cm.Spectral(np.linspace(0, 1, len(activity_counts))))
    
    ax1.set_yticks(range(len(activity_counts)))
    ax1.set_yticklabels(wrapped_labels_occ)
    ax1.set_xlabel('Antal forekomster', fontsize=12)
    ax1.set_title(f'Top forureningsaktiviteter - Forekomster\n(≤{threshold_m}m, total: {len(all_activities)} forekomster)', 
                  fontsize=12, fontweight='bold')
    
    # Add count labels on bars
    for i, (bar, count) in enumerate(zip(bars1, activity_counts.values)):
        width = bar.get_width()
        ax1.text(width + 0.5, bar.get_y() + bar.get_height()/2.,
                f'{count}', ha='left', va='center', fontsize=10)
    
    # Right plot: Unique sites
    top_activities_by_sites_series = pd.Series(top_activities_by_sites).head(15)
    wrapped_labels_sites = [textwrap.fill(label, 30) for label in top_activities_by_sites_series.index]
    
    bars2 = ax2.barh(range(len(top_activities_by_sites_series)), top_activities_by_sites_series.values, 
                     color=plt.cm.viridis(np.linspace(0, 1, len(top_activities_by_sites_series))))
    
    ax2.set_yticks(range(len(top_activities_by_sites_series)))
    ax2.set_yticklabels(wrapped_labels_sites)
    ax2.set_xlabel('Antal unikke lokaliteter', fontsize=12)
    ax2.set_title(f'Top forureningsaktiviteter - Unikke lokaliteter\n(≤{threshold_m}m, {len(activity_data)} lokaliteter med data)', 
                  fontsize=12, fontweight='bold')
    
    # Add count labels on bars
    for i, (bar, count) in enumerate(zip(bars2, top_activities_by_sites_series.values)):
        width = bar.get_width()
        ax2.text(width + 0.5, bar.get_y() + bar.get_height()/2.,
                f'{count}', ha='left', va='center', fontsize=10)
    
    ax1.grid(True, alpha=0.3, axis='x')
    ax2.grid(True, alpha=0.3, axis='x')
    
    plt.tight_layout()
    safe_save_figure(figures_path, "step5_contamination_activities")
    plt.close()

def create_contamination_substances_analysis(high_risk_sites, figures_path, threshold_m):
    """Create analysis of contamination substances (Lokalitetensstoffer)."""
    print("Creating contamination substances analysis...")
    
    if 'Lokalitetensstoffer' not in high_risk_sites.columns:
        print("No contamination substances data available")
        return
    
    # Filter to non-null values
    substances_data = high_risk_sites['Lokalitetensstoffer'].dropna()
    
    if substances_data.empty:
        print("No valid contamination substances data")
        return
    
    # Parse substances (they might be comma-separated or semicolon-separated)
    all_substances = []
    sites_with_substance = {}
    
    for idx, substances_str in substances_data.items():
        if pd.notna(substances_str):
            # Split by common separators and clean
            substances = [s.strip() for s in str(substances_str).replace(';', ',').split(',') if s.strip()]
            all_substances.extend(substances)
            
            # Track unique sites for each substance
            for substance in substances:
                if substance not in sites_with_substance:
                    sites_with_substance[substance] = set()
                sites_with_substance[substance].add(idx)
    
    substance_counts = pd.Series(all_substances).value_counts().head(20)  # Top 20 substances
    substance_site_counts = {sub: len(sites) for sub, sites in sites_with_substance.items()}
    top_substances_by_sites = dict(sorted(substance_site_counts.items(), key=lambda x: x[1], reverse=True)[:20])
    
    # Create horizontal bar chart showing both occurrences and unique sites
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(20, 12))
    
    # Left plot: Occurrences
    wrapped_labels_occ = [textwrap.fill(label, 25) for label in substance_counts.index]
    
    bars1 = ax1.barh(range(len(substance_counts)), substance_counts.values, 
                     color=plt.cm.tab20(np.linspace(0, 1, len(substance_counts))))
    
    ax1.set_yticks(range(len(substance_counts)))
    ax1.set_yticklabels(wrapped_labels_occ)
    ax1.set_xlabel('Antal forekomster', fontsize=12)
    ax1.set_title(f'Top forureningsstoffer - Forekomster\n(≤{threshold_m}m, total: {len(all_substances)} forekomster)', 
                  fontsize=12, fontweight='bold')
    
    # Add count labels on bars
    for i, (bar, count) in enumerate(zip(bars1, substance_counts.values)):
        width = bar.get_width()
        ax1.text(width + 0.5, bar.get_y() + bar.get_height()/2.,
                f'{count}', ha='left', va='center', fontsize=10)
    
    # Right plot: Unique sites
    top_substances_by_sites_series = pd.Series(top_substances_by_sites).head(20)
    wrapped_labels_sites = [textwrap.fill(label, 25) for label in top_substances_by_sites_series.index]
    
    bars2 = ax2.barh(range(len(top_substances_by_sites_series)), top_substances_by_sites_series.values, 
                     color=plt.cm.plasma(np.linspace(0, 1, len(top_substances_by_sites_series))))
    
    ax2.set_yticks(range(len(top_substances_by_sites_series)))
    ax2.set_yticklabels(wrapped_labels_sites)
    ax2.set_xlabel('Antal unikke lokaliteter', fontsize=12)
    ax2.set_title(f'Top forureningsstoffer - Unikke lokaliteter\n(≤{threshold_m}m, {len(substances_data)} lokaliteter med data)', 
                  fontsize=12, fontweight='bold')
    
    # Add count labels on bars
    for i, (bar, count) in enumerate(zip(bars2, top_substances_by_sites_series.values)):
        width = bar.get_width()
        ax2.text(width + 0.5, bar.get_y() + bar.get_height()/2.,
                f'{count}', ha='left', va='center', fontsize=10)
    
    ax1.grid(True, alpha=0.3, axis='x')
    ax2.grid(True, alpha=0.3, axis='x')
    
    plt.tight_layout()
    safe_save_figure(figures_path, "step5_contamination_substances")
    plt.close()

def create_multi_gvfk_analysis(high_risk_sites, figures_path, threshold_m):
    """Create analysis of sites affecting multiple GVFKs."""
    print("Creating multi-GVFK analysis...")
    
    if 'Total_GVFKs_Affected' not in high_risk_sites.columns:
        print("No multi-GVFK data available")
        return
    
    gvfk_counts = high_risk_sites['Total_GVFKs_Affected'].value_counts().sort_index()
    
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
    
    # Bar chart of GVFK distribution
    bars = ax1.bar(gvfk_counts.index, gvfk_counts.values, 
                   color=plt.cm.viridis(np.linspace(0, 1, len(gvfk_counts))))
    ax1.set_xlabel('Antal påvirkede GVFK pr. lokalitet', fontsize=12)
    ax1.set_ylabel('Antal lokaliteter', fontsize=12)
    ax1.set_title(f'GVFK-påvirkning pr. højrisiko-lokalitet\n(≤{threshold_m}m)', fontsize=12, fontweight='bold')
    
    # Add count labels on bars
    for bar, count in zip(bars, gvfk_counts.values):
        height = bar.get_height()
        ax1.text(bar.get_x() + bar.get_width()/2., height + 0.5,
                f'{count}', ha='center', va='bottom', fontsize=10)
    
    ax1.grid(True, alpha=0.3)
    
    # Pie chart: single vs multiple GVFK sites
    single_gvfk = (high_risk_sites['Total_GVFKs_Affected'] == 1).sum()
    multi_gvfk = (high_risk_sites['Total_GVFKs_Affected'] > 1).sum()
    
    labels = [f'Enkelt GVFK\n({single_gvfk})', f'Flere GVFK\n({multi_gvfk})']
    sizes = [single_gvfk, multi_gvfk]
    colors = ['#3498db', '#e74c3c']
    
    ax2.pie(sizes, labels=labels, autopct='%1.1f%%', colors=colors, startangle=90)
    ax2.set_title('Lokaliteter efter GVFK-påvirkning', fontsize=12, fontweight='bold')
    
    plt.tight_layout()
    safe_save_figure(figures_path, "step5_multi_gvfk_analysis")
    plt.close()

def create_comprehensive_risk_dashboard(high_risk_sites, figures_path, threshold_m):
    """Create a comprehensive risk assessment dashboard."""
    print("Creating comprehensive risk dashboard...")
    
    fig = plt.figure(figsize=(20, 14))
    
    # Create a grid layout
    gs = fig.add_gridspec(3, 4, hspace=0.3, wspace=0.3)
    
    # 1. Distance distribution (top left)
    ax1 = fig.add_subplot(gs[0, 0:2])
    if 'Final_Distance_m' in high_risk_sites.columns:
        distances = high_risk_sites['Final_Distance_m']
        bins = range(0, threshold_m + 50, 50)
        ax1.hist(distances, bins=bins, color='#2E8B57', alpha=0.7, edgecolor='black')
        ax1.set_title(f'Afstandsfordeling (≤{threshold_m}m)', fontweight='bold')
        ax1.set_xlabel('Afstand (m)')
        ax1.set_ylabel('Antal')
        ax1.grid(True, alpha=0.3)
    
    # 2. Site type distribution (top right)
    ax2 = fig.add_subplot(gs[0, 2:4])
    if 'Site_Type' in high_risk_sites.columns:
        type_counts = high_risk_sites['Site_Type'].value_counts()
        colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728']
        ax2.pie(type_counts.values, labels=type_counts.index, autopct='%1.1f%%', 
                colors=colors, startangle=90)
        ax2.set_title('Lokalitetstyper', fontweight='bold')
    
    # 3. Top contamination sources (middle left)
    ax3 = fig.add_subplot(gs[1, 0:2])
    if 'Lokalitetensbranche' in high_risk_sites.columns:
        source_data = high_risk_sites['Lokalitetensbranche'].dropna()
        if not source_data.empty:
            # Handle semicolon-separated values
            all_sources = []
            for value in source_data:
                if pd.notna(value) and str(value).strip():
                    sources = [src.strip() for src in str(value).split(';') if src.strip()]
                    all_sources.extend(sources)
            
            if all_sources:
                source_counts = pd.Series(all_sources).value_counts().head(8)
                wrapped_labels = [textwrap.fill(label, 20) for label in source_counts.index]
                bars = ax3.barh(range(len(source_counts)), source_counts.values, 
                               color=plt.cm.Set3(np.linspace(0, 1, len(source_counts))))
                ax3.set_yticks(range(len(source_counts)))
                ax3.set_yticklabels(wrapped_labels, fontsize=8)
                ax3.set_title('Top forureningskilder (forekomster)', fontweight='bold')
                ax3.grid(True, alpha=0.3, axis='x')
    
    # 4. Top contamination substances (middle right)
    ax4 = fig.add_subplot(gs[1, 2:4])
    if 'Lokalitetensstoffer' in high_risk_sites.columns:
        substances_data = high_risk_sites['Lokalitetensstoffer'].dropna()
        if not substances_data.empty:
            all_substances = []
            for substances_str in substances_data:
                if pd.notna(substances_str):
                    substances = [s.strip() for s in str(substances_str).replace(';', ',').split(',') if s.strip()]
                    all_substances.extend(substances)
            
            if all_substances:
                substance_counts = pd.Series(all_substances).value_counts().head(8)
                wrapped_labels = [textwrap.fill(label, 20) for label in substance_counts.index]
                bars = ax4.barh(range(len(substance_counts)), substance_counts.values, 
                               color=plt.cm.tab10(np.linspace(0, 1, len(substance_counts))))
                ax4.set_yticks(range(len(substance_counts)))
                ax4.set_yticklabels(wrapped_labels, fontsize=8)
                ax4.set_title('Top forureningsstoffer (forekomster)', fontweight='bold')
                ax4.grid(True, alpha=0.3, axis='x')
    
    # 5. Multi-GVFK distribution (bottom left)
    ax5 = fig.add_subplot(gs[2, 0:2])
    if 'Total_GVFKs_Affected' in high_risk_sites.columns:
        gvfk_counts = high_risk_sites['Total_GVFKs_Affected'].value_counts().sort_index()
        bars = ax5.bar(gvfk_counts.index, gvfk_counts.values, 
                       color=plt.cm.viridis(np.linspace(0, 1, len(gvfk_counts))))
        ax5.set_xlabel('Antal påvirkede GVFK')
        ax5.set_ylabel('Antal lokaliteter')
        ax5.set_title('GVFK-påvirkning pr. lokalitet', fontweight='bold')
        ax5.grid(True, alpha=0.3)
    
    # 6. Summary statistics (bottom right)
    ax6 = fig.add_subplot(gs[2, 2:4])
    ax6.axis('off')
    
    # Calculate summary statistics
    summary_text = f"SAMMENFATNING - HØJRISIKO LOKALITETER (≤{threshold_m}m)\n"
    summary_text += "=" * 50 + "\n\n"
    summary_text += f"Total antal højrisiko-lokaliteter: {len(high_risk_sites)}\n\n"
    
    if 'Final_Distance_m' in high_risk_sites.columns:
        distances = high_risk_sites['Final_Distance_m']
        summary_text += f"Afstandsstatistik:\n"
        summary_text += f"  Gennemsnit: {distances.mean():.0f}m\n"
        summary_text += f"  Median: {distances.median():.0f}m\n"
        summary_text += f"  Min-Max: {distances.min():.0f}m - {distances.max():.0f}m\n\n"
    
    if 'Site_Type' in high_risk_sites.columns:
        type_counts = high_risk_sites['Site_Type'].value_counts()
        summary_text += f"Lokalitetstyper:\n"
        for site_type, count in type_counts.items():
            percentage = count / len(high_risk_sites) * 100
            summary_text += f"  {site_type}: {count} ({percentage:.1f}%)\n"
        summary_text += "\n"
    
    # Data availability
    data_cols = ['Lokalitetensbranche', 'Lokalitetensaktivitet', 'Lokalitetensstoffer']
    summary_text += f"Datatilgængelighed:\n"
    for col in data_cols:
        if col in high_risk_sites.columns:
            available = high_risk_sites[col].notna().sum()
            percentage = available / len(high_risk_sites) * 100
            summary_text += f"  {col}: {available} ({percentage:.1f}%)\n"
    
    ax6.text(0.05, 0.95, summary_text, transform=ax6.transAxes,
             verticalalignment='top', horizontalalignment='left',
             fontsize=10, fontfamily='monospace',
             bbox=dict(boxstyle='round', facecolor='lightgray', alpha=0.8))
    
    # Overall title
    fig.suptitle(f'Risikoanalyse Dashboard - Højrisiko V1/V2 Lokaliteter (≤{threshold_m}m fra kontaktzoner)', 
                 fontsize=16, fontweight='bold', y=0.98)
    
    safe_save_figure(figures_path, "step5_risk_dashboard")
    plt.close()


# ============================================================================
# COMPOUND-SPECIFIC VISUALIZATIONS
# ============================================================================

def create_compound_specific_visualizations():
    """
    Create visualizations for compound-specific risk assessment results.
    
    This includes category-based threshold analysis and detailed compound breakdowns.
    """
    print("Creating compound-specific risk assessment visualizations...")
    
    from config import get_visualization_path, get_output_path
    from compound_categorization import COMPOUND_DISTANCE_MAPPING
    import matplotlib.patches as mpatches
    
    figures_path = get_visualization_path('step5')
    
    # Professional color scheme for compound visualizations
    COMPOUND_COLORS = {
        'primary': '#2E86AB',      # Professional blue
        'secondary': '#A23B72',    # Professional purple
        'accent': '#F18F01',       # Professional orange
        'success': '#C73E1D',      # Professional red
        'neutral': '#7A7A7A',      # Professional gray
        'light': '#E8F4F8',       # Light blue background
    }
    
    # Risk level colors based on distance thresholds
    RISK_COLORS = {
        30: '#C73E1D',    # High risk - Red (PAH)
        50: '#F18F01',    # Medium-high risk - Orange (BTX)
        100: '#F4A261',   # Medium risk - Light orange (Polar)
        150: '#E9C46A',   # Medium-low risk - Yellow (Inorganic)
        200: '#2A9D8F',   # Low-medium risk - Teal (Chlorinated)
        300: '#264653',   # Low risk - Dark green (Phenols)
        500: '#1D3557'    # Very low risk - Dark blue (Pesticides)
    }
    
    # Load compound analysis results
    try:
        cat_summary_path = get_output_path('step5_category_summary')
        sub_summary_path = get_output_path('step5_category_substance_summary')
        flags_path = get_output_path('step5_category_flags')
        
        if not all(os.path.exists(p) for p in [cat_summary_path, sub_summary_path, flags_path]):
            print("Compound analysis data not found. Please run compound analysis first.")
            return
        
        cat_summary = pd.read_csv(cat_summary_path)
        sub_summary = pd.read_csv(sub_summary_path)
        long_df = pd.read_csv(flags_path)
        
    except Exception as e:
        print(f"Error loading compound analysis data: {e}")
        return
    
    # Create visualizations
    create_category_threshold_dashboard(cat_summary, sub_summary, long_df, figures_path, RISK_COLORS, COMPOUND_COLORS)
    create_category_detailed_analysis(sub_summary, long_df, figures_path, RISK_COLORS, COMPOUND_COLORS)
    create_category_overview_plot(cat_summary, figures_path, RISK_COLORS, COMPOUND_COLORS)
    
    print(f"✓ Compound-specific visualizations saved to {figures_path}")


def setup_professional_figure(figsize=(12, 8), title="", subtitle=""):
    """Create a professionally styled figure for compound analysis."""
    fig, ax = plt.subplots(figsize=figsize)
    
    # Remove top and right spines
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    
    # Style remaining spines
    ax.spines['left'].set_color('#CCCCCC')
    ax.spines['bottom'].set_color('#CCCCCC')
    
    # Grid styling
    ax.grid(True, alpha=0.3, linestyle='-', linewidth=0.5)
    ax.set_axisbelow(True)
    
    # Title styling
    if title:
        fig.suptitle(title, fontsize=16, fontweight='bold', y=0.98)
    if subtitle:
        ax.set_title(subtitle, fontsize=12, color='#666666', pad=20)
    
    return fig, ax


def create_category_threshold_dashboard(cat_summary, sub_summary, long_df, figures_path, RISK_COLORS, COMPOUND_COLORS):
    """Create a comprehensive dashboard showing category-based threshold analysis."""
    
    from compound_categorization import COMPOUND_DISTANCE_MAPPING
    
    # Create 2x2 subplot dashboard
    fig = plt.figure(figsize=(18, 14))
    fig.suptitle('Category-Based Distance Threshold Analysis Results', 
                 fontsize=18, fontweight='bold', y=0.96)
    
    # 1. Within-threshold counts by category (Top Left)
    ax1 = plt.subplot(2, 2, 1)
    
    # Sort categories by within-threshold count
    plot_data = cat_summary.sort_values('within_tokens', ascending=True)
    
    # Create horizontal bar chart with risk-based colors
    colors = []
    for _, row in plot_data.iterrows():
        category = row['Category']
        if category in COMPOUND_DISTANCE_MAPPING:
            distance = COMPOUND_DISTANCE_MAPPING[category]['distance_m']
            colors.append(RISK_COLORS.get(distance, COMPOUND_COLORS['neutral']))
        else:
            colors.append(COMPOUND_COLORS['neutral'])
    
    bars = ax1.barh(range(len(plot_data)), plot_data['within_tokens'], 
                    color=colors, alpha=0.8, height=0.7)
    
    # Customize
    ax1.set_yticks(range(len(plot_data)))
    ax1.set_yticklabels([cat.replace('_', ' ').title() for cat in plot_data['Category']])
    ax1.set_xlabel('Sites Within Category Threshold')
    ax1.set_title('A. Within-Threshold Sites by Category', fontweight='bold', pad=20)
    ax1.grid(True, alpha=0.3)
    
    # Add count labels
    for i, (bar, count) in enumerate(zip(bars, plot_data['within_tokens'])):
        ax1.text(count + max(plot_data['within_tokens']) * 0.01, i,
                f'{count}', va='center', fontweight='bold', fontsize=9)
    
    # 2. Success rate by category (Top Right)
    ax2 = plt.subplot(2, 2, 2)
    
    # Filter out categories with zero tokens for percentage calculation
    pct_data = cat_summary[cat_summary['total_tokens'] > 0].copy()
    pct_data = pct_data.sort_values('within_pct', ascending=True)
    
    # Create horizontal bar chart
    colors2 = []
    for _, row in pct_data.iterrows():
        category = row['Category']
        if category in COMPOUND_DISTANCE_MAPPING:
            distance = COMPOUND_DISTANCE_MAPPING[category]['distance_m']
            colors2.append(RISK_COLORS.get(distance, COMPOUND_COLORS['neutral']))
        else:
            colors2.append(COMPOUND_COLORS['neutral'])
    
    bars2 = ax2.barh(range(len(pct_data)), pct_data['within_pct'], 
                     color=colors2, alpha=0.8, height=0.7)
    
    ax2.set_yticks(range(len(pct_data)))
    ax2.set_yticklabels([cat.replace('_', ' ').title() for cat in pct_data['Category']])
    ax2.set_xlabel('Percentage Within Threshold (%)')
    ax2.set_title('B. Success Rate by Category', fontweight='bold', pad=20)
    ax2.set_xlim(0, 100)
    ax2.grid(True, alpha=0.3)
    
    # Add percentage labels
    for i, (bar, pct) in enumerate(zip(bars2, pct_data['within_pct'])):
        ax2.text(pct + 2, i, f'{pct:.1f}%', va='center', fontweight='bold', fontsize=9)
    
    # 3. Distance threshold overview (Bottom Left)
    ax3 = plt.subplot(2, 2, 3)
    
    # Get distance distribution from categories with data
    distance_data = []
    for _, row in cat_summary[cat_summary['total_tokens'] > 0].iterrows():
        category = row['Category']
        if category in COMPOUND_DISTANCE_MAPPING:
            distance = COMPOUND_DISTANCE_MAPPING[category]['distance_m']
            distance_data.append({
                'Distance_m': distance,
                'Category': category,
                'Within_Count': row['within_tokens']
            })
    
    dist_df = pd.DataFrame(distance_data)
    if not dist_df.empty:
        # Group by distance and sum within counts
        dist_summary = dist_df.groupby('Distance_m')['Within_Count'].sum().sort_index()
        
        # Create bar chart
        colors3 = [RISK_COLORS.get(dist, COMPOUND_COLORS['neutral']) for dist in dist_summary.index]
        bars3 = ax3.bar(range(len(dist_summary)), list(dist_summary.values), 
                        color=colors3, alpha=0.8)
        
        ax3.set_xticks(range(len(dist_summary)))
        ax3.set_xticklabels([f'{int(d)}m' for d in dist_summary.index])
        ax3.set_ylabel('Within-Threshold Sites')
        ax3.set_title('C. Sites by Distance Threshold', fontweight='bold', pad=20)
        
        # Add count labels
        for bar, count in zip(bars3, dist_summary.values):
            height = bar.get_height()
            ax3.text(bar.get_x() + bar.get_width()/2., height + max(dist_summary.values) * 0.01,
                    f'{count}', ha='center', va='bottom', fontweight='bold', fontsize=9)
    
    ax3.grid(True, alpha=0.3)
    
    # 4. Top substances within threshold (Bottom Right)
    ax4 = plt.subplot(2, 2, 4)
    
    # Get top substances that are within threshold
    within_substances = long_df[long_df['Within_Threshold'] == True]
    if not within_substances.empty:
        top_substances = within_substances['Substance'].value_counts().head(10)
        
        # Create horizontal bar chart
        bars4 = ax4.barh(range(len(top_substances)), list(top_substances.values), 
                         color=COMPOUND_COLORS['primary'], alpha=0.8, height=0.7)
        
        ax4.set_yticks(range(len(top_substances)))
        # Truncate long substance names
        labels = [s[:20] + '...' if len(s) > 20 else s for s in top_substances.index]
        ax4.set_yticklabels(labels, fontsize=9)
        ax4.set_xlabel('Within-Threshold Occurrences')
        ax4.set_title('D. Top Substances Within Thresholds', fontweight='bold', pad=20)
        
        # Add count labels
        for i, (bar, count) in enumerate(zip(bars4, top_substances.values)):
            ax4.text(count + max(top_substances.values) * 0.01, i,
                    f'{count}', va='center', fontweight='bold', fontsize=9)
    
    ax4.grid(True, alpha=0.3)
    
    # Add legend for risk colors
    legend_elements = [
        mpatches.Patch(color=RISK_COLORS[30], label='30m - Very High Risk'),
        mpatches.Patch(color=RISK_COLORS[50], label='50m - High Risk'),
        mpatches.Patch(color=RISK_COLORS[100], label='100m - Medium Risk'),
        mpatches.Patch(color=RISK_COLORS[200], label='200m - Low Risk'),
        mpatches.Patch(color=RISK_COLORS[500], label='500m - Very Low Risk')
    ]
    
    fig.legend(handles=legend_elements, loc='lower center', ncol=5, 
               bbox_to_anchor=(0.5, 0.02), frameon=True, fancybox=True)
    
    # Adjust layout
    plt.subplots_adjust(left=0.08, bottom=0.12, right=0.95, top=0.88, wspace=0.3, hspace=0.4)
    
    # Save figure
    dashboard_path = os.path.join(figures_path, 'step5_category_dashboard.png')
    fig.savefig(dashboard_path, dpi=300, bbox_inches='tight')
    plt.close(fig)
    print(f"✓ Saved category dashboard: {dashboard_path}")


def create_category_detailed_analysis(sub_summary, long_df, figures_path, RISK_COLORS, COMPOUND_COLORS):
    """Create detailed analysis of top categories with substance breakdowns."""
    
    from compound_categorization import COMPOUND_DISTANCE_MAPPING
    
    # Get top 6 categories by within-threshold count
    cat_within_counts = long_df[long_df['Within_Threshold'] == True]['Category'].value_counts().head(6)
    
    if cat_within_counts.empty:
        print("No within-threshold categories found for detailed analysis")
        return
    
    # Create 2x3 grid
    fig = plt.figure(figsize=(20, 14))
    fig.suptitle('Detailed Category Analysis: Top Substances Within Distance Thresholds', 
                 fontsize=18, fontweight='bold', y=0.96)
    
    for i, (category, total_within) in enumerate(cat_within_counts.items()):
        if i >= 6:
            break
            
        ax = plt.subplot(2, 3, i + 1)
        
        # Get substances in this category that are within threshold
        cat_data = long_df[(long_df['Category'] == category) & 
                          (long_df['Within_Threshold'] == True)]
        
        if cat_data.empty:
            ax.text(0.5, 0.5, 'No data', ha='center', va='center', transform=ax.transAxes)
            continue
            
        substance_counts = cat_data['Substance'].value_counts().head(10)
        
        # Get category info
        distance = COMPOUND_DISTANCE_MAPPING.get(category, {}).get('distance_m', 'Unknown')
        color = RISK_COLORS.get(distance, COMPOUND_COLORS['neutral'])
        
        # Create horizontal bar chart
        bars = ax.barh(range(len(substance_counts)), list(substance_counts.values), 
                       color=color, alpha=0.8, height=0.7)
        
        # Customize
        ax.set_yticks(range(len(substance_counts)))
        labels = [s[:25] + '...' if len(s) > 25 else s for s in substance_counts.index]
        ax.set_yticklabels(labels, fontsize=9)
        ax.set_xlabel('Within-Threshold Sites')
        
        category_title = category.replace('_', ' ').title()
        ax.set_title(f'{category_title}\n({distance}m threshold, {total_within} total sites)', 
                     fontweight='bold', fontsize=11, pad=15)
        
        # Add count labels
        for j, (bar, count) in enumerate(zip(bars, substance_counts.values)):
            ax.text(count + max(substance_counts.values) * 0.02, j,
                   f'{count}', va='center', fontweight='bold', fontsize=8)
        
        # Style
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.grid(True, alpha=0.3)
    
    plt.subplots_adjust(left=0.08, bottom=0.08, right=0.95, top=0.88, wspace=0.3, hspace=0.4)
    
    # Save figure
    detailed_path = os.path.join(figures_path, 'step5_category_detailed_analysis.png')
    fig.savefig(detailed_path, dpi=300, bbox_inches='tight')
    plt.close(fig)
    print(f"✓ Saved detailed analysis: {detailed_path}")


def create_category_overview_plot(cat_summary, figures_path, RISK_COLORS, COMPOUND_COLORS):
    """Create simple overview plot of categories."""
    
    from compound_categorization import COMPOUND_DISTANCE_MAPPING
    
    overview_fig, ax = setup_professional_figure(figsize=(12, 8),
                                                title="Category-Based Distance Threshold Overview",
                                                subtitle="Within-threshold substance counts by contamination category")
    
    plot_df = cat_summary.sort_values('within_tokens', ascending=False)
    
    # Use risk-based colors
    colors = []
    for _, row in plot_df.iterrows():
        category = row['Category']
        if category in COMPOUND_DISTANCE_MAPPING:
            distance = COMPOUND_DISTANCE_MAPPING[category]['distance_m']
            colors.append(RISK_COLORS.get(distance, COMPOUND_COLORS['neutral']))
        else:
            colors.append(COMPOUND_COLORS['neutral'])
    
    bars = ax.barh(range(len(plot_df)), plot_df['within_tokens'], color=colors, alpha=0.8)
    
    # Customize
    ax.set_yticks(range(len(plot_df)))
    ax.set_yticklabels([cat.replace('_', ' ').title() for cat in plot_df['Category']])
    ax.set_xlabel('Within-threshold substance tokens (count)')
    ax.invert_yaxis()
    
    # Add count and percentage labels
    for i, (_, row) in enumerate(plot_df.iterrows()):
        count = row['within_tokens']
        total = row['total_tokens']
        pct = (count / total * 100) if total > 0 else 0
        
        ax.text(count + max(plot_df['within_tokens']) * 0.01, i,
               f'{count} ({pct:.1f}%)', va='center', fontweight='bold', fontsize=10)
    
    # Add risk level legend
    import matplotlib.patches as mpatches
    legend_elements = [
        mpatches.Patch(color=RISK_COLORS[30], label='30m threshold'),
        mpatches.Patch(color=RISK_COLORS[50], label='50m threshold'),
        mpatches.Patch(color=RISK_COLORS[100], label='100m threshold'),
        mpatches.Patch(color=RISK_COLORS[200], label='200m threshold'),
        mpatches.Patch(color=RISK_COLORS[500], label='500m threshold')
    ]
    ax.legend(handles=legend_elements, loc='lower right', frameon=True, 
             fancybox=True, shadow=True)
    
    overview_fig.tight_layout()
    plot_path = os.path.join(figures_path, 'step5_category_overview.png')
    overview_fig.savefig(plot_path, dpi=300, bbox_inches='tight')
    plt.close(overview_fig)
    print(f"✓ Saved category overview: {plot_path}")


if __name__ == "__main__":
    # Create all Step 5 visualizations
    create_step5_visualizations()
    create_compound_specific_visualizations()
    print("All Step 5 visualizations completed!") 