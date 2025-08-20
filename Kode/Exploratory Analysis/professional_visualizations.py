"""
Professional Visualizations for Groundwater Contamination Analysis
================================================================

This script creates clean, professional visualizations for the compound-specific
distance threshold methodology and categorization results.

Created: August 2025
Author: Oliver Lund, DTU
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from matplotlib.patches import Rectangle
import matplotlib.patches as mpatches
from collections import Counter
import warnings
import os
warnings.filterwarnings('ignore')

# Create plots directory if it doesn't exist
PLOTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Plots")
os.makedirs(PLOTS_DIR, exist_ok=True)

# Import our analysis functions
from v1v2_exploration import (
    load_data, 
    COMPOUND_DISTANCE_MAPPING, 
    categorize_contamination_substance,
    analyze_contamination_categorization
)

# Set professional styling
plt.style.use('default')
sns.set_palette("husl")

# Professional color scheme
COLORS = {
    'primary': '#2E86AB',      # Professional blue
    'secondary': '#A23B72',    # Professional purple
    'accent': '#F18F01',       # Professional orange
    'success': '#C73E1D',      # Professional red
    'neutral': '#7A7A7A',      # Professional gray
    'light': '#E8F4F8',       # Light blue background
}

# Risk level colors based on distance
RISK_COLORS = {
    30: '#C73E1D',    # High risk - Red (PAH)
    50: '#F18F01',    # Medium-high risk - Orange (BTX)
    100: '#F4A261',   # Medium risk - Light orange (Polar)
    150: '#E9C46A',   # Medium-low risk - Yellow (Inorganic)
    200: '#2A9D8F',   # Low-medium risk - Teal (Chlorinated)
    300: '#264653',   # Low risk - Dark green (Phenols)
    500: '#1D3557'    # Very low risk - Dark blue (Pesticides)
}

def setup_professional_figure(figsize=(12, 8), title="", subtitle=""):
    """Create a professionally styled figure."""
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

def create_categorization_summary_dashboard():
    """Create a comprehensive dashboard showing categorization results."""
    
    # Load and analyze data
    v1, v2 = load_data()
    
    if v1.empty or v2.empty:
        print("Cannot create dashboard - missing data")
        return
    
    # Analyze both datasets
    print("Analyzing V1 data...")
    v1_results = analyze_contamination_categorization(v1, "V1")
    print("Analyzing V2 data...")
    v2_results = analyze_contamination_categorization(v2, "V2")
    
    if v1_results is None or v2_results is None:
        print("Error in categorization analysis")
        return
    
    # Create 2x2 subplot dashboard
    fig = plt.figure(figsize=(16, 14))  # Increased height for better spacing
    fig.suptitle('Groundwater Contamination Analysis: Compound-Specific Distance Thresholds', 
                 fontsize=18, fontweight='bold', y=0.96)  # Adjusted y position
    
    # 1. Categorization Success Rate (Top Left)
    ax1 = plt.subplot(2, 2, 1)
    
    # Calculate success rates
    v1_categorized = len(v1_results[v1_results['category'] != 'UNCATEGORIZED'])
    v1_total = len(v1_results)
    v2_categorized = len(v2_results[v2_results['category'] != 'UNCATEGORIZED'])
    v2_total = len(v2_results)
    
    success_rates = [
        v1_categorized / v1_total * 100,
        v2_categorized / v2_total * 100
    ]
    
    bars = ax1.bar(['V1 Dataset', 'V2 Dataset'], success_rates, 
                   color=[COLORS['primary'], COLORS['secondary']], alpha=0.8)
    
    # Add percentage labels on bars
    for bar, rate in zip(bars, success_rates):
        height = bar.get_height()
        ax1.text(bar.get_x() + bar.get_width()/2., height + 1,
                f'{rate:.1f}%', ha='center', va='bottom', fontweight='bold')
    
    ax1.set_ylabel('Categorization Success Rate (%)')
    ax1.set_title('A. Substance Categorization Success', fontweight='bold', pad=20)
    ax1.set_ylim(0, 100)
    ax1.grid(True, alpha=0.3)
    
    # 2. Distance Threshold Distribution (Top Right)
    ax2 = plt.subplot(2, 2, 2)
    
    # Get distance distribution from both datasets
    all_results = pd.concat([v1_results, v2_results])
    distance_counts = all_results.groupby('distance_m').size().sort_values(ascending=True)
    
    # Remove None values
    distance_counts = distance_counts.dropna()
    
    # Create horizontal bar chart
    colors = [RISK_COLORS.get(int(d), COLORS['neutral']) for d in distance_counts.index]
    bars = ax2.barh(range(len(distance_counts)), list(distance_counts.values), color=colors, alpha=0.8)
    
    ax2.set_yticks(range(len(distance_counts)))
    ax2.set_yticklabels([f'{int(d)}m' for d in distance_counts.index])
    ax2.set_xlabel('Number of Contamination Records')
    ax2.set_title('B. Distance Threshold Distribution', fontweight='bold', pad=20)
    ax2.grid(True, alpha=0.3)
    
    # Add count labels on bars
    for i, (bar, count) in enumerate(zip(bars, distance_counts.values)):
        ax2.text(count + max(distance_counts.values) * 0.01, i,
                f'{count}', va='center', fontweight='bold')
    
    # 3. Top Categories by Frequency (Bottom Left)
    ax3 = plt.subplot(2, 2, 3)
    
    # Get top categories (excluding uncategorized)
    category_counts = all_results[all_results['category'] != 'UNCATEGORIZED']['category'].value_counts().head(8)
    
    # Create pie chart
    pie_result = ax3.pie(list(category_counts.values), 
                        labels=list(category_counts.index),
                        autopct='%1.1f%%',
                        startangle=90)
    
    # Handle the variable unpacking
    if len(pie_result) == 3:
        wedges, texts, autotexts = pie_result
        # Style the text
        for autotext in autotexts:
            autotext.set_color('white')
            autotext.set_fontweight('bold')
    else:
        wedges, texts = pie_result
    
    for text in texts:
        text.set_fontsize(9)
    
    ax3.set_title('C. Most Common Contamination Categories', fontweight='bold', pad=20)
    
    # 4. Methodology Overview (Bottom Right)
    ax4 = plt.subplot(2, 2, 4)
    ax4.axis('off')
    
    # Create methodology flowchart
    methodology_text = """
METHODOLOGY OVERVIEW

Step 1: General Risk Assessment
└── Apply 500m universal threshold
└── Identify all potentially affected areas

Step 2: Compound-Specific Refinement
└── Categorize contamination substances
└── Apply specific distance thresholds:
    • PAH compounds: 30m (low mobility)
    • BTX compounds: 50m (moderate mobility)
    • Polar solvents: 100m (high mobility)
    • Pesticides: 500m (very high mobility)
    • ... and 12 other categories

Result: More accurate risk assessment
        based on scientific evidence
"""
    
    ax4.text(0.05, 0.95, methodology_text, transform=ax4.transAxes,
             fontsize=11, verticalalignment='top', fontfamily='monospace',
             bbox=dict(boxstyle="round,pad=0.5", facecolor=COLORS['light'], alpha=0.8))
    
    ax4.set_title('D. Two-Part Assessment Methodology', fontweight='bold', pad=20)
    
    # Adjust layout with better spacing
    plt.subplots_adjust(left=0.08, bottom=0.08, right=0.92, top=0.88, wspace=0.3, hspace=0.4)
    
    # Save the figure
    plt.savefig(os.path.join(PLOTS_DIR, 'contamination_analysis_dashboard.png'), dpi=300, bbox_inches='tight')
    
    print("✓ Dashboard saved as 'contamination_analysis_dashboard.png' in Plots folder")
    plt.show()
    
    return fig

def create_distance_threshold_comparison():
    """Create a visualization comparing distance thresholds by category."""
    
    fig, ax = setup_professional_figure(figsize=(14, 10), 
                                       title="Compound-Specific Distance Thresholds",
                                       subtitle="Scientific basis for risk assessment distances")
    
    # Prepare data
    categories = []
    distances = []
    examples = []
    
    for category, info in COMPOUND_DISTANCE_MAPPING.items():
        if category != 'UNCATEGORIZED':
            categories.append(category.replace('_', ' ').title())
            distances.append(info['distance_m'])
            examples.append(', '.join(info['examples'][:3]))  # First 3 examples
    
    # Sort by distance
    sorted_data = sorted(zip(categories, distances, examples), key=lambda x: x[1])
    categories, distances, examples = zip(*sorted_data)
    
    # Create horizontal bar chart
    y_pos = np.arange(len(categories))
    colors = [RISK_COLORS.get(d, COLORS['neutral']) for d in distances]
    
    bars = ax.barh(y_pos, distances, color=colors, alpha=0.8, height=0.7)
    
    # Customize the chart
    ax.set_yticks(y_pos)
    ax.set_yticklabels(categories)
    ax.set_xlabel('Distance Threshold (meters)', fontsize=12, fontweight='bold')
    ax.set_title('')  # We set it in setup_professional_figure
    
    # Add distance labels and examples
    for i, (bar, distance, example) in enumerate(zip(bars, distances, examples)):
        # Distance label
        ax.text(distance + max(distances) * 0.01, i, f'{distance}m',
                va='center', fontweight='bold', fontsize=10)
        
        # Example substances (on the left side of bars)
        ax.text(5, i, f'{example}...', va='center', fontsize=8, 
                color='white', fontweight='bold')
    
    # Add legend for risk levels
    legend_elements = [
        mpatches.Patch(color=RISK_COLORS[30], label='30m - Very Low Mobility'),
        mpatches.Patch(color=RISK_COLORS[50], label='50m - Low Mobility'),
        mpatches.Patch(color=RISK_COLORS[100], label='100m - Moderate Mobility'),
        mpatches.Patch(color=RISK_COLORS[200], label='200m - High Mobility'),
        mpatches.Patch(color=RISK_COLORS[500], label='500m - Very High Mobility')
    ]
    
    ax.legend(handles=legend_elements, loc='lower right', frameon=True, 
              fancybox=True, shadow=True)
    
    # Add explanatory text
    explanatory_text = ("Distance thresholds based on compound mobility, persistence, and toxicity.\n"
                       "Shorter distances for compounds with limited groundwater transport potential.\n"
                       "Longer distances for highly mobile compounds that can travel far from source.")
    
    fig.text(0.02, 0.02, explanatory_text, fontsize=10, style='italic', 
             color='#666666', wrap=True)
    
    plt.tight_layout()
    plt.savefig(os.path.join(PLOTS_DIR, 'distance_threshold_comparison.png'), dpi=300, bbox_inches='tight')
    
    print("✓ Distance comparison saved as 'distance_threshold_comparison.png' in Plots folder")
    plt.show()
    
    return fig

def create_methodology_flowchart():
    """Create a professional methodology flowchart."""
    
    fig, ax = plt.subplots(figsize=(12, 14))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 14)
    ax.axis('off')
    
    # Title
    fig.suptitle('Groundwater Risk Assessment Methodology\nTwo-Part Compound-Specific Approach', 
                 fontsize=16, fontweight='bold', y=0.95)
    
    # Helper function to create boxes
    def create_box(ax, x, y, width, height, text, color, text_color='black'):
        rect = Rectangle((x, y), width, height, linewidth=2, 
                        edgecolor='black', facecolor=color, alpha=0.8)
        ax.add_patch(rect)
        ax.text(x + width/2, y + height/2, text, ha='center', va='center',
                fontsize=10, fontweight='bold', color=text_color, wrap=True)
    
    # Helper function to create arrows
    def create_arrow(ax, x1, y1, x2, y2):
        ax.annotate('', xy=(x2, y2), xytext=(x1, y1),
                   arrowprops=dict(arrowstyle='->', lw=2, color='black'))
    
    # Step 1: Data Input
    create_box(ax, 1, 12, 8, 1, 'INPUT: V1/V2 Contamination Data\n(Lokalitetensstoffer)', 
               COLORS['light'], 'black')
    
    # Arrow down
    create_arrow(ax, 5, 12, 5, 11)
    
    # Step 2: General Assessment
    create_box(ax, 1, 10, 8, 1, 'STEP 1: General Risk Assessment\nApply 500m universal threshold', 
               COLORS['primary'], 'white')
    
    # Arrow down
    create_arrow(ax, 5, 10, 5, 9)
    
    # Step 3: Categorization
    create_box(ax, 1, 8, 8, 1, 'STEP 2: Substance Categorization\nMap to 16 compound-specific categories', 
               COLORS['secondary'], 'white')
    
    # Arrow down
    create_arrow(ax, 5, 8, 5, 7)
    
    # Step 4: Distance Assignment (split into multiple boxes)
    categories_text = [
        "PAH: 30m\nBTX: 50m\nPolar: 100m",
        "Inorganic: 150m\nChlorinated: 200m\nSpecialty: 200m",
        "Phenols: 300m\nPesticides: 500m\nGases: 500m"
    ]
    
    box_width = 2.5
    start_x = 1
    
    for i, text in enumerate(categories_text):
        create_box(ax, start_x + i * 2.75, 5.5, box_width, 1.5, text, 
                   COLORS['accent'], 'black')
    
    # Arrows from categorization to distance boxes
    for i in range(3):
        create_arrow(ax, 3 + i * 2, 7, 2.25 + i * 2.75, 7)
    
    # Convergence arrows
    for i in range(3):
        create_arrow(ax, 2.25 + i * 2.75, 5.5, 5, 4.5)
    
    # Step 5: Refined Assessment
    create_box(ax, 1, 3.5, 8, 1, 'STEP 3: Compound-Specific Risk Assessment\nApply tailored distance thresholds', 
               COLORS['success'], 'white')
    
    # Arrow down
    create_arrow(ax, 5, 3.5, 5, 2.5)
    
    # Final output
    create_box(ax, 1, 1.5, 8, 1, 'OUTPUT: Enhanced Risk Assessment\nScientifically-based protection zones', 
               '#2E7D32', 'white')
    
    # Add benefits box
    benefits_text = ("BENEFITS:\n"
                    "• Science-based approach\n"
                    "• Reduced false positives\n"
                    "• Optimized resource allocation\n"
                    "• Improved decision support")
    
    ax.text(10.5, 7, benefits_text, fontsize=11, 
            bbox=dict(boxstyle="round,pad=0.5", facecolor='#E8F5E8', alpha=0.8),
            verticalalignment='center')
    
    plt.tight_layout()
    plt.savefig(os.path.join(PLOTS_DIR, 'methodology_flowchart.png'), dpi=300, bbox_inches='tight')
    
    print("✓ Methodology flowchart saved as 'methodology_flowchart.png' in Plots folder")
    plt.show()
    
    return fig

def create_substance_frequency_analysis():
    """Create visualization of most common substances by category."""
    
    # Load and analyze data
    v1, v2 = load_data()
    if v1.empty or v2.empty:
        print("Cannot create analysis - missing data")
        return
    
    # Combine datasets
    all_data = pd.concat([v1, v2])
    substances = all_data['Lokalitetensstoffer'].dropna()
    
    # Categorize all substances
    categorized_substances = []
    for substance in substances:
        category, distance = categorize_contamination_substance(substance)
        if category != 'UNCATEGORIZED':
            categorized_substances.append({
                'substance': substance,
                'category': category,
                'distance': distance
            })
    
    df = pd.DataFrame(categorized_substances)
    
    # Create figure with subplots
    fig = plt.figure(figsize=(18, 12))  # Increased size for better spacing
    fig.suptitle('Contamination Substance Analysis by Category', 
                 fontsize=16, fontweight='bold', y=0.95)  # Adjusted y position
    
    # Get top 6 categories by frequency
    top_categories = df['category'].value_counts().head(6)
    
    for i, (category, count) in enumerate(top_categories.items()):
        ax = plt.subplot(2, 3, i + 1)
        
        # Get top substances in this category
        category_data = df[df['category'] == category]
        top_substances = category_data['substance'].value_counts().head(8)
        
        # Create horizontal bar chart
        category_str = str(category)
        distance = COMPOUND_DISTANCE_MAPPING[category_str]['distance_m']
        color = RISK_COLORS.get(distance, COLORS['neutral'])
        
        bars = ax.barh(range(len(top_substances)), list(top_substances.values), 
                       color=color, alpha=0.8)
        
        # Customize
        ax.set_yticks(range(len(top_substances)))
        ax.set_yticklabels([s[:30] + '...' if len(s) > 30 else s 
                           for s in top_substances.index], fontsize=8)
        ax.set_xlabel('Frequency')
        ax.set_title(f'{category_str.replace("_", " ").title()}\n({distance}m threshold)', 
                     fontweight='bold', fontsize=10, pad=15)  # Added padding
        ax.grid(True, alpha=0.3)
        
        # Add frequency labels
        for j, (bar, freq) in enumerate(zip(bars, top_substances.values)):
            ax.text(freq + max(top_substances.values) * 0.02, j, 
                   str(freq), va='center', fontsize=8, fontweight='bold')
    
    # Use subplots_adjust instead of tight_layout for better control
    plt.subplots_adjust(left=0.08, bottom=0.1, right=0.95, top=0.88, wspace=0.35, hspace=0.5)
    plt.savefig(os.path.join(PLOTS_DIR, 'substance_frequency_analysis.png'), dpi=300, bbox_inches='tight')
    
    print("✓ Substance frequency analysis saved as 'substance_frequency_analysis.png' in Plots folder")
    plt.show()
    
    return fig

def create_all_visualizations():
    """Create all professional visualizations."""
    print("Creating comprehensive visualization suite...")
    print("="*60)
    
    try:
        print("\n1. Creating categorization dashboard...")
        create_categorization_summary_dashboard()
        
        print("\n2. Creating distance threshold comparison...")
        create_distance_threshold_comparison()
        
        print("\n3. Creating methodology flowchart...")
        create_methodology_flowchart()
        
        print("\n4. Creating substance frequency analysis...")
        create_substance_frequency_analysis()
        
        print("\n" + "="*60)
        print("✓ All visualizations created successfully!")
        print("Files saved in Plots folder:")
        print("  • contamination_analysis_dashboard.png")
        print("  • distance_threshold_comparison.png")
        print("  • methodology_flowchart.png")
        print("  • substance_frequency_analysis.png")
        print("="*60)
        
    except Exception as e:
        print(f"Error creating visualizations: {e}")
        import traceback
        traceback.print_exc()

def create_uncategorized_substances_plot():
    """Create a detailed plot of uncategorized substances and their frequencies."""
    
    # Load and analyze data
    v1, v2 = load_data()
    if v1.empty or v2.empty:
        print("Cannot create uncategorized plot - missing data")
        return
    
    # Combine datasets and categorize
    all_data = pd.concat([v1, v2])
    substances = all_data['Lokalitetensstoffer'].dropna()
    
    uncategorized_substances = []
    for substance in substances:
        category, distance = categorize_contamination_substance(substance)
        if category == 'UNCATEGORIZED':
            uncategorized_substances.append(substance)
    
    if not uncategorized_substances:
        print("No uncategorized substances found!")
        return
    
    # Count frequencies
    substance_counts = pd.Series(uncategorized_substances).value_counts()
    
    # Create figure - use regular matplotlib for better spacing control
    fig, ax = plt.subplots(figsize=(14, 10))
    
    # Set title directly on the figure
    fig.suptitle("Uncategorized Contamination Substances", 
                 fontsize=16, fontweight='bold', y=0.95)
    
    # Add subtitle as axis title
    ax.set_title(f"Analysis of {len(substance_counts)} unique uncategorized substances",
                 fontsize=12, color='#666666', pad=15)
    
    # Style the plot
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_color('#CCCCCC')
    ax.spines['bottom'].set_color('#CCCCCC')
    ax.grid(True, alpha=0.3, linestyle='-', linewidth=0.5)
    ax.set_axisbelow(True)
    
    # Create horizontal bar chart
    y_pos = np.arange(len(substance_counts))
    bars = ax.barh(y_pos, list(substance_counts.values), color=COLORS['accent'], alpha=0.8)
    
    # Customize
    ax.set_yticks(y_pos)
    # Truncate long substance names for readability
    labels = [s[:50] + '...' if len(s) > 50 else s for s in substance_counts.index]
    ax.set_yticklabels(labels, fontsize=9)
    ax.set_xlabel('Frequency in Dataset', fontsize=12, fontweight='bold')
    
    # Add frequency labels on bars
    for i, (bar, count) in enumerate(zip(bars, substance_counts.values)):
        ax.text(count + max(substance_counts.values) * 0.01, i,
                str(count), va='center', fontweight='bold', fontsize=9)
    
    # Add summary statistics
    total_uncategorized = len(uncategorized_substances)
    unique_uncategorized = len(substance_counts)
    
    summary_text = (f"Summary:\n"
                   f"• Total uncategorized records: {total_uncategorized}\n"
                   f"• Unique uncategorized substances: {unique_uncategorized}\n"
                   f"• Most common: '{substance_counts.index[0]}' ({substance_counts.iloc[0]} times)\n"
                   f"• Average frequency: {total_uncategorized/unique_uncategorized:.1f}")
    
    ax.text(0.98, 0.02, summary_text, transform=ax.transAxes,
            bbox=dict(boxstyle="round,pad=0.5", facecolor=COLORS['light'], alpha=0.9),
            verticalalignment='bottom', horizontalalignment='right', fontsize=10)
    
    # Use subplots_adjust for better spacing control
    plt.subplots_adjust(left=0.25, bottom=0.1, right=0.75, top=0.88)
    plt.savefig(os.path.join(PLOTS_DIR, 'uncategorized_substances_analysis.png'), dpi=300, bbox_inches='tight')
    
    print("✓ Uncategorized substances plot saved as 'uncategorized_substances_analysis.png' in Plots folder")
    plt.show()
    
    return fig

def create_individual_category_plots():
    """Create detailed plots for each compound category showing all substances."""
    
    # Load and analyze data
    v1, v2 = load_data()
    if v1.empty or v2.empty:
        print("Cannot create category plots - missing data")
        return
    
    # Combine datasets and categorize all substances
    all_data = pd.concat([v1, v2])
    substances = all_data['Lokalitetensstoffer'].dropna()
    
    categorized_data = []
    for substance in substances:
        category, distance = categorize_contamination_substance(substance)
        if category != 'UNCATEGORIZED':
            categorized_data.append({
                'substance': substance,
                'category': category,
                'distance': distance
            })
    
    df = pd.DataFrame(categorized_data)
    
    if df.empty:
        print("No categorized data found")
        return
    
    # Get categories ordered by frequency
    category_counts = df['category'].value_counts()
    
    # Create individual plots for each category
    figures = []
    
    for category in category_counts.index:
        category_data = df[df['category'] == category]
        substance_counts = category_data['substance'].value_counts()
        
        # Skip categories with very few substances
        if len(substance_counts) < 3:
            continue
        
        # Get category info
        category_info = COMPOUND_DISTANCE_MAPPING.get(str(category), {})
        distance = category_info.get('distance_m', 'Unknown')
        description = category_info.get('description', 'No description')
        
        # Create figure - use regular matplotlib instead of setup_professional_figure to avoid spacing issues
        fig, ax = plt.subplots(figsize=(12, max(10, len(substance_counts) * 0.5)))
        
        # Set title directly on the figure for better control
        fig.suptitle(f"{str(category).replace('_', ' ').title()} Category Analysis", 
                     fontsize=14, fontweight='bold', y=0.95)
        
        # Add subtitle as axis title
        ax.set_title(f"{description} | Distance threshold: {distance}m | {len(substance_counts)} unique substances",
                     fontsize=11, color='#666666', pad=15)
        
        # Style the plot
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.spines['left'].set_color('#CCCCCC')
        ax.spines['bottom'].set_color('#CCCCCC')
        ax.grid(True, alpha=0.3, linestyle='-', linewidth=0.5)
        ax.set_axisbelow(True)
        
        # Create horizontal bar chart
        y_pos = np.arange(len(substance_counts))
        color = RISK_COLORS.get(distance, COLORS['primary'])
        bars = ax.barh(y_pos, list(substance_counts.values), color=color, alpha=0.8)
        
        # Customize
        ax.set_yticks(y_pos)
        # Truncate long substance names
        labels = [s[:60] + '...' if len(s) > 60 else s for s in substance_counts.index]
        ax.set_yticklabels(labels, fontsize=10)
        ax.set_xlabel('Frequency in Dataset', fontsize=12, fontweight='bold')
        
        # Add frequency labels on bars
        for i, (bar, count) in enumerate(zip(bars, substance_counts.values)):
            ax.text(count + max(substance_counts.values) * 0.01, i,
                    str(count), va='center', fontweight='bold', fontsize=9)
        
        # Add category statistics
        total_records = len(category_data)
        unique_substances = len(substance_counts)
        
        stats_text = (f"Statistics:\n"
                     f"• Total records: {total_records}\n"
                     f"• Unique substances: {unique_substances}\n"
                     f"• Most common: '{substance_counts.index[0]}'\n"
                     f"• Appears {substance_counts.iloc[0]} times ({substance_counts.iloc[0]/total_records*100:.1f}%)")
        
        ax.text(0.98, 0.98, stats_text, transform=ax.transAxes,
                bbox=dict(boxstyle="round,pad=0.5", facecolor=COLORS['light'], alpha=0.9),
                verticalalignment='top', horizontalalignment='right', fontsize=10)
        
        # Use subplots_adjust with better spacing for individual plots
        plt.subplots_adjust(left=0.25, bottom=0.1, right=0.75, top=0.88)
        
        # Save individual category plot
        filename_base = f"category_{str(category).lower()}_analysis"
        plt.savefig(os.path.join(PLOTS_DIR, f'{filename_base}.png'), dpi=300, bbox_inches='tight')
        
        print(f"✓ {category} category plot saved as '{filename_base}.png' in Plots folder")
        figures.append(fig)
        plt.show()
    
    return figures

def create_category_overview_grid():
    """Create a grid overview of all categories with their top substances."""
    
    # Load and analyze data
    v1, v2 = load_data()
    if v1.empty or v2.empty:
        print("Cannot create category overview - missing data")
        return
    
    # Combine datasets and categorize
    all_data = pd.concat([v1, v2])
    substances = all_data['Lokalitetensstoffer'].dropna()
    
    categorized_data = []
    for substance in substances:
        category, distance = categorize_contamination_substance(substance)
        if category != 'UNCATEGORIZED':
            categorized_data.append({
                'substance': substance,
                'category': category,
                'distance': distance
            })
    
    df = pd.DataFrame(categorized_data)
    
    if df.empty:
        print("No categorized data found")
        return
    
    # Get top categories
    category_counts = df['category'].value_counts().head(12)  # Top 12 categories
    
    # Create 4x3 grid
    fig = plt.figure(figsize=(22, 18))  # Increased size for better spacing
    fig.suptitle('Compound Categories Overview: Top Substances by Category', 
                 fontsize=18, fontweight='bold', y=0.96)  # Adjusted y position
    
    for i, (category, total_count) in enumerate(category_counts.items()):
        if i >= 12:  # Limit to 12 subplots
            break
            
        ax = plt.subplot(4, 3, i + 1)
        
        # Get top substances in this category
        category_data = df[df['category'] == category]
        top_substances = category_data['substance'].value_counts().head(8)
        
        # Get category info
        category_info = COMPOUND_DISTANCE_MAPPING.get(str(category), {})
        distance = category_info.get('distance_m', 'Unknown')
        
        # Create mini bar chart
        color = RISK_COLORS.get(distance, COLORS['neutral'])
        bars = ax.barh(range(len(top_substances)), list(top_substances.values), 
                       color=color, alpha=0.8, height=0.7)
        
        # Customize
        ax.set_yticks(range(len(top_substances)))
        # Truncate substance names for grid view
        labels = [s[:25] + '...' if len(s) > 25 else s for s in top_substances.index]
        ax.set_yticklabels(labels, fontsize=8)
        ax.set_xlabel('Count', fontsize=9)
        
        # Title with category and distance
        category_title = str(category).replace('_', ' ').title()
        ax.set_title(f'{category_title}\n({distance}m threshold)', 
                     fontweight='bold', fontsize=10, pad=15)  # Added padding
        
        # Add count labels on bars
        max_count = max(top_substances.values)
        for j, (bar, count) in enumerate(zip(bars, top_substances.values)):
            ax.text(count + max_count * 0.02, j, str(count), 
                   va='center', fontsize=7, fontweight='bold')
        
        # Remove gridlines for cleaner look in grid
        ax.grid(False)
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
    
    # Use subplots_adjust for better spacing control
    plt.subplots_adjust(left=0.06, bottom=0.08, right=0.95, top=0.90, wspace=0.3, hspace=0.5)
    plt.savefig(os.path.join(PLOTS_DIR, 'category_overview_grid.png'), dpi=300, bbox_inches='tight')
    
    print("✓ Category overview grid saved as 'category_overview_grid.png' in Plots folder")
    plt.show()
    
    return fig

def quick_categorization_summary():
    """Quick summary of categorization success without creating plots."""
    
    # Load and analyze data
    v1, v2 = load_data()
    if v1.empty or v2.empty:
        print("Cannot analyze - missing data")
        return
    
    # Combine datasets and categorize
    all_data = pd.concat([v1, v2])
    substances = all_data['Lokalitetensstoffer'].dropna()
    
    categorized_counts = {}
    uncategorized_count = 0
    
    for substance in substances:
        category, distance = categorize_contamination_substance(substance)
        if category == 'UNCATEGORIZED':
            uncategorized_count += 1
        else:
            categorized_counts[category] = categorized_counts.get(category, 0) + 1
    
    total_substances = len(substances)
    total_categorized = sum(categorized_counts.values())
    success_rate = (total_categorized / total_substances) * 100
    
    print(f"\n{'='*60}")
    print(f"CATEGORIZATION SUMMARY")
    print(f"{'='*60}")
    print(f"Total contamination records: {total_substances}")
    print(f"Successfully categorized: {total_categorized} ({success_rate:.1f}%)")
    print(f"Uncategorized: {uncategorized_count} ({100-success_rate:.1f}%)")
    
    print(f"\nTop categories:")
    sorted_categories = sorted(categorized_counts.items(), key=lambda x: x[1], reverse=True)
    for category, count in sorted_categories[:8]:
        distance = COMPOUND_DISTANCE_MAPPING.get(str(category), {}).get('distance_m', 'Unknown')
        pct = (count / total_substances) * 100
        print(f"  {category}: {count} records ({pct:.1f}%) - {distance}m threshold")
    
    print(f"{'='*60}")
    
    return {
        'total': total_substances,
        'categorized': total_categorized,
        'uncategorized': uncategorized_count,
        'success_rate': success_rate,
        'categories': categorized_counts
    }

def create_comprehensive_substance_analysis():
    """Create all substance analysis visualizations."""
    print("Creating comprehensive substance analysis visualizations...")
    print("="*70)
    
    try:
        print("\n1. Creating uncategorized substances analysis...")
        create_uncategorized_substances_plot()
        
        print("\n2. Creating category overview grid...")
        create_category_overview_grid()
        
        print("\n3. Creating individual category plots...")
        create_individual_category_plots()
        
        print("\n" + "="*70)
        print("✓ All substance analysis visualizations created successfully!")
        print("Files saved in Plots folder:")
        print("  • uncategorized_substances_analysis.png")
        print("  • category_overview_grid.png")
        print("  • category_[name]_analysis.png (for each major category)")
        print("="*70)
        
    except Exception as e:
        print(f"Error creating visualizations: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    # You can run either the full suite or just the substance analysis
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "substances":
        create_comprehensive_substance_analysis()
    else:
        create_all_visualizations()
