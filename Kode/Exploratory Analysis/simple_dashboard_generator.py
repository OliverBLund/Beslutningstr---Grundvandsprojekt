"""
Simple Interactive Dashboard Generator for Compound Categorization
=================================================================

Creates a clean, interactive dashboard showing all compound categories
with substance breakdowns. Designed for boss presentation.

Author: Dashboard for Boss Discussion
Date: January 2025
"""

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.offline as pyo
import os
import sys

# Add parent directory to path to import config
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import V1_CSV_PATH, V2_CSV_PATH

# Import the refined categorization
from refined_compound_analysis import LITERATURE_COMPOUND_MAPPING, categorize_contamination_substance_refined

def load_categorization_data():
    """Load and process the compound categorization data."""
    print("Loading compound categorization data...")
    
    # Load data
    v1_data = pd.read_csv(V1_CSV_PATH, encoding='utf-8')
    v2_data = pd.read_csv(V2_CSV_PATH, encoding='utf-8')
    
    # Combine datasets
    v1_data['dataset'] = 'V1'
    v2_data['dataset'] = 'V2'
    combined_data = pd.concat([v1_data, v2_data], ignore_index=True)
    
    # Get contamination substances and count occurrences
    substances = combined_data['Lokalitetensstoffer'].dropna()
    
    # Count how many times each substance appears in original data
    substance_counts = substances.value_counts()
    print(f"Found {len(substance_counts):,} unique substances from {len(substances):,} total records")
    
    # Categorize each unique substance and preserve original counts
    results = []
    for idx, (substance, count) in enumerate(substance_counts.items()):
        if idx % 5000 == 0:
            print(f"Processing... {idx:,}/{len(substance_counts):,}")
            
        category, distance = categorize_contamination_substance_refined(substance)
        results.append({
            'substance': substance,
            'category': category,
            'distance_m': distance,
            'count': count  # Preserve original occurrence count
        })
    
    results_df = pd.DataFrame(results)
    print(f"Processed {len(results_df):,} unique substances with original occurrence counts")
    
    return results_df

def create_dashboard(results_df):
    """Create dashboard with all categories as separate plots stacked vertically."""
    print("Creating scrollable dashboard with all categories...")
    
    # Get category summary for unique compounds
    category_counts = results_df['category'].value_counts()
    total_unique_compounds = len(results_df)
    
    # Calculate total occurrences across all records
    total_all_occurrences = results_df['count'].sum()
    category_total_counts = results_df.groupby('category')['count'].sum()
    
    # Sort categories by total occurrence percentage (highest to lowest)
    category_occurrence_pcts = {}
    for category in category_counts.index:
        category_total_count = category_total_counts[category]
        category_occurrence_pct = category_total_count / total_all_occurrences * 100
        category_occurrence_pcts[category] = category_occurrence_pct
    
    # Sort categories by occurrence percentage (descending)
    existing_categories = sorted(category_occurrence_pcts.keys(), 
                               key=lambda x: category_occurrence_pcts[x], 
                               reverse=True)
    num_categories = len(existing_categories)
    
    # Color mapping for consistency
    colors = {
        'BTXER': '#2E86AB',
        'UORGANISKE_FORBINDELSER': '#A23B72', 
        'CHLORINATED_SOLVENTS': '#F18F01',
        'PAHER': '#C73E1D',
        'PESTICIDER': '#5B8A3A',
        'OTHER': '#8E44AD',
        'PHENOLER': '#E67E22',
        'POLARE': '#34495E',
        'KLOREDE_KULBRINTER': '#95A5A6'
    }
    
    # Create subplot titles
    subplot_titles = []
    for category in existing_categories:
        category_count = category_counts[category]
        category_unique_pct = category_count / total_unique_compounds * 100
        category_total_count = category_total_counts[category]
        category_occurrence_pct = category_total_count / total_all_occurrences * 100
        
        if category in LITERATURE_COMPOUND_MAPPING:
            distance = LITERATURE_COMPOUND_MAPPING[category]['distance_m']
            title = f"{category}<br>{category_count:,} compounds ({category_unique_pct:.1f}%) | {category_occurrence_pct:.1f}% of all records | {distance}m"
        else:
            title = f"{category}<br>{category_count:,} compounds ({category_unique_pct:.1f}%) | {category_occurrence_pct:.1f}% of all records | TBD"
        
        subplot_titles.append(title)
    
    # Create subplots - one row per category
    fig = make_subplots(
        rows=num_categories, cols=1,
        subplot_titles=subplot_titles,
        vertical_spacing=0.02,  # Much less whitespace between plots
        specs=[[{"type": "bar"}] for _ in range(num_categories)]
    )
    
    # Add traces for each category
    for idx, category in enumerate(existing_categories):
        row = idx + 1
        
        # Get ALL substances for this category with their original counts
        category_data = results_df[results_df['category'] == category].copy()
        category_data = category_data.sort_values('count', ascending=False)  # Sort by count
        
        # Calculate percentages within this category AND total dataset
        total_category_count = category_data['count'].sum()
        category_data['category_percentage'] = (category_data['count'] / total_category_count * 100).round(1)
        category_data['total_percentage'] = (category_data['count'] / total_all_occurrences * 100).round(2)
        
        # Create horizontal bar chart showing ALL substances with actual counts
        fig.add_trace(
            go.Bar(
                y=category_data['substance'][::-1],  # Reverse for better display (most common at top)
                x=category_data['count'][::-1],
                orientation='h',
                marker_color=colors[category],
                name=category,
                showlegend=False,
                width=0.8,  # Make bars thicker (default is 0.8, but being explicit)
                hovertemplate='<b>%{y}</b><br>Count: %{x:,}<br>' +
                             'Within Category: ' + category_data['category_percentage'][::-1].astype(str) + '%<br>' +
                             'Of All Records: ' + category_data['total_percentage'][::-1].astype(str) + '%<br>' +
                             'Category: ' + category + '<extra></extra>'
            ),
            row=row, col=1
        )
        
        # Update x-axis for this subplot
        fig.update_xaxes(title_text="Count (Number of Occurrences)", row=row, col=1)
        fig.update_yaxes(title_text="", row=row, col=1)
    
    # Calculate dynamic height based on number of compounds per category
    total_height = 100  # Base height for title
    category_heights = []
    
    for category in existing_categories:
        category_data = results_df[results_df['category'] == category]
        num_compounds = len(category_data)
        # More generous sizing: minimum 400px + 30px per compound for better visibility
        category_height = max(400, num_compounds * 30)
        category_heights.append(category_height)
        total_height += category_height + 20  # Much less spacing between plots
    
    # Update layout with dynamic height
    fig.update_layout(
        title={
            'text': "<b>Compound Categorization Dashboard</b><br><sub>Categories sorted by total occurrence percentage (highest to lowest)</sub>",
            'x': 0.5,
            'xanchor': 'center',
            'font': {'size': 20}
        },
        height=total_height,
        width=1600,  # Wider dashboard for better compound name display
        showlegend=False,
        margin=dict(t=100, b=50, l=500, r=100)  # Even more left margin for long compound names
    )
    
    return fig

def add_summary_info(results_df):
    """Create summary information for the dashboard."""
    category_counts = results_df['category'].value_counts()
    total_unique_compounds = len(results_df)
    
    literature_based = sum(count for cat, count in category_counts.items() 
                          if cat in LITERATURE_COMPOUND_MAPPING)
    other_count = category_counts.get('OTHER', 0)
    
    summary_text = f"""
    <div style="text-align: center; padding: 20px; background-color: #f8f9fa; border-radius: 10px; margin: 20px;">
        <h3>Compound Categorization Summary</h3>
        <p><strong>Total UNIQUE compounds analyzed:</strong> {total_unique_compounds:,}</p>
        <p><strong>Literature-based categorization:</strong> {literature_based:,} compounds ({(literature_based/total_unique_compounds)*100:.1f}%)</p>
        <p><strong>Requiring decisions (OTHER):</strong> {other_count:,} compounds ({(other_count/total_unique_compounds)*100:.1f}%)</p>
        <p><strong>Categories with literature support:</strong> {len(LITERATURE_COMPOUND_MAPPING)}</p>
    </div>
    """
    return summary_text

def generate_dashboard():
    """Main function to generate the complete dashboard."""
    print("GENERATING COMPOUND CATEGORIZATION DASHBOARD")
    print("=" * 50)
    
    # Load data
    results_df = load_categorization_data()
    
    # Create dashboard
    fig = create_dashboard(results_df)
    
    # Generate HTML in the Exploratory Analysis folder
    html_file = os.path.join(os.path.dirname(__file__), "compound_categorization_dashboard.html")
    
    # Create custom HTML with summary
    summary_html = add_summary_info(results_df)
    
    # Convert plotly figure to HTML
    plot_html = pyo.plot(fig, output_type='div', include_plotlyjs=True)
    
    # Combine into complete HTML page
    complete_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Compound Categorization Dashboard</title>
        <meta charset="utf-8">
        <style>
            body {{ font-family: Arial, sans-serif; margin: 20px; }}
            .header {{ text-align: center; padding: 20px; }}
            .content {{ max-width: 1700px; margin: 0 auto; }}
        </style>
    </head>
    <body>
        <div class="content">
            <div class="header">
                <h1>Compound Categorization Analysis Dashboard</h1>
                <p>Interactive exploration of UNIQUE contamination compounds by category</p>
            </div>
            {summary_html}
            {plot_html}
            <div style="text-align: center; margin-top: 30px; padding: 20px; background-color: #e9ecef; border-radius: 10px;">
                <h4>Usage Instructions</h4>
                <p>• <strong>Select Category:</strong> Use dropdown menu to choose which category to view</p>
                <p>• <strong>Hover:</strong> Over bars to see detailed compound information</p>
                <p>• <strong>Scroll/Zoom:</strong> Use mouse wheel to scroll through long lists, zoom to focus on specific compounds</p>
                <p>• <strong>All Compounds:</strong> Each category shows ALL unique compounds, not just top ones</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    # Write to file
    with open(html_file, 'w', encoding='utf-8') as f:
        f.write(complete_html)
    
    print(f"\n[SUCCESS] Dashboard created: {html_file}")
    print(f"[INFO] Ready for boss presentation!")
    print(f"[INFO] Open the HTML file in any web browser")
    
    # Print summary stats
    category_counts = results_df['category'].value_counts()
    print(f"\nDashboard includes:")
    for category, count in category_counts.items():
        pct = count / len(results_df) * 100
        if category in LITERATURE_COMPOUND_MAPPING:
            distance = LITERATURE_COMPOUND_MAPPING[category]['distance_m']
            print(f"  • {category}: {count:,} substances ({pct:.1f}%) - {distance}m")
        else:
            print(f"  • {category}: {count:,} substances ({pct:.1f}%) - TBD")
    
    return html_file

if __name__ == "__main__":
    dashboard_file = generate_dashboard()