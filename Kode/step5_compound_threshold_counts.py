"""
Step 5 (Category-based): Per-substance/category within-threshold flags and summaries

This module joins Step 4 distance results with a keyword-based categorization
to compute, for each site-substance token, whether the site is within the
category-specific distance threshold.

Outputs (saved under Resultater/ via config.get_output_path):
- step5_category_flags.csv: Long table with one row per site-substance token
- step5_category_summary.csv: Aggregated by category
- step5_category_substance_summary.csv: Aggregated by (category, substance)
- step5_category_overview.png: Compact bar chart of within-threshold counts per category
"""

import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from typing import Optional
from matplotlib.patches import Rectangle
import matplotlib.patches as mpatches

from config import get_output_path, ensure_results_directory

# Professional styling and colors from professional_visualizations.py
plt.style.use('default')
sns.set_palette("husl")

COLORS = {
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


# Local copy of the keyword-based mapping to avoid importing analysis scripts with side effects
COMPOUND_DISTANCE_MAPPING = {
    'BTXER': {
        'distance_m': 50,
        'keywords': ['btx', 'btex', 'benzen', 'toluene', 'toluen', 'xylen', 'xylene', 'benzin', 'olie-benzen',
                    'aromater', 'aromat', 'c5-c10', 'c10-c25', 'kulbrintefraktion', 'monocyk', 'bicyk',
                    'tex (sum)', 'styren'],
    },
    'CHLORINATED_SOLVENTS': {
        'distance_m': 500,
        'keywords': ['1,1,1-tca', 'tce', 'tetrachlorethylen', 'trichlorethylen', 'trichlor', 'tetrachlor',
                    'vinylchlorid', 'dichlorethylen', 'dichlorethan', 'chlorerede', 'opl.midl', 'opløsningsmidl',
                    'cis-1,2-dichlorethyl', 'trans-1,2-dichloreth', 'chlorethan'],
    },
    'POLARE': {
        'distance_m': 100,
        'keywords': ['mtbe', 'methyl tert-butyl ether', 'acetone', 'keton'],
    },
    'PHENOLER': {
        'distance_m': 300,
        'keywords': ['phenol', 'fenol', 'cod', 'klorofenol'],
    },
    'KLOREDE_KULBRINTER': {
        'distance_m': 200,
        'keywords': ['chloroform', 'kloroform', 'kulbrinter', 'klorede', 'bromoform', 'dibromethane', 'bromerede'],
    },
    'CHLORPHENOLER': {
        'distance_m': 200,
        'keywords': ['dichlorophenol', 'chlorphenol', 'diklorofenol', 'klorofenol'],
    },
    'PAHER': {
        'distance_m': 30,
        'keywords': ['pah', 'fluoranthen', 'benzo', 'naftalen', 'naphtalen', 'naphthalen', 'pyren', 'anthracen', 'antracen',
                    'tjære', 'tar', 'phenanthren', 'fluoren', 'acenaphthen', 'acenaphthylen', 'chrysen', 'chrysene',
                    'benzfluranthen', 'methylnaphthalen', 'benz(ghi)perylen'],
    },
    'PESTICIDER': {
        'distance_m': 500,
        'keywords': ['pesticid', 'herbicid', 'fungicid', 'mechlorprop', 'mcpp', 'atrazin', 'glyphosat',
                    'perfluor', 'pfos', 'pfoa', 'perfluoroctansulfonsyre', 'pfas', 'mcpa', 'dichlorprop',
                    '2,4-d', 'diuron', 'simazin', 'fluazifop', 'ampa', 'ddt', 'triazol', 'dichlorbenzamid',
                    'desphenyl chloridazon', 'chloridazon', 'dde', 'ddd', 'bentazon', 'dithiocarbamat',
                    'dithiocarbamater', '4-cpp', '2-(2,6-dichlorphenoxy)', 'hexazinon', 'isoproturon',
                    'lenacil', 'malathion', 'parathion', 'terbuthylazin', 'metribuzin', 'deltamethrin',
                    'cypermethrin', 'dieldrin', 'aldrin', 'clopyralid', 'tebuconazol', 'propiconazol',
                    'dichlobenil', 'triadimenol', 'dimethachlor', 'pirimicarb', 'dimethoat', 'phenoxysyrer',
                    'tfmp', 'propachlor', 'gamma lindan', 'thiamethoxam', 'clothianidin', 'metazachlor',
                    'diflufenican', 'monuron', 'metamitron', 'propyzamid', 'azoxystrobin', 'alachlor',
                    'chlorothalonil', 'asulam', 'metsulfuron', 'boscalid', 'glufosinat', 'carbofuran',
                    'picloram', 'sulfosulfuron', 'epoxiconazol', 'clomazon', 'prothioconazol', 'aminopyralid',
                    'metalaxyl', 'dichlorvos', 'dicamba', 'triadimefon', 'haloxyfop', 'quintozen', 'endosulfan',
                    'dichlorfluanid', 'florasulam', 'aldicarb', 'imidacloprid', 'pendimethalin', 'dinoseb',
                    'dinoterb', 'amitrol', 'ethofumesat', 'benazolin', 'deet'],
    },
    'UORGANISKE_FORBINDELSER': {
        'distance_m': 150,
        'keywords': ['arsen', 'arsenic', 'cyanid', 'cyanide', 'tungmetal', 'bly', 'cadmium', 'krom', 'chrom',
                    'nikkel', 'zink', 'kobber', 'kviksølv', 'jern', 'mangan', 'aluminium', 'sølv', 'barium',
                    'kobolt', 'metaller', 'tributyltin', 'tbt', 'tin', 'molybden', 'antimon', 'calcium',
                    'natrium', 'kalium', 'magnesium', 'thallium', 'bor', 'chlorid', 'sulfat', 'nitrat',
                    'fluorid', 'fluor', 'ammoniak', 'ammonium', 'phosphor', 'tributhyltinacetat',
                    'tributhyltinnaphth', 'nitrit'],
    },
    'OLIEPRODUKTER': {
        'distance_m': 200,
        'keywords': ['olie', 'diesel', 'fyring', 'olieprodukter', 'fedt', 'petroleum', 'smøreolie',
                    'c25-c35', 'kulbrintefraktion', 'terpentin', 'white spirit', 'methyl-napthalen', 'naphthacen'],
    },
    'KOMPLEKS_AFFALD': {
        'distance_m': 500,
        'keywords': ['kompleks', 'olie', 'affald', 'diverse', 'øvrige', 'sjældne', 'restgruppe',
                    'lægemidler', 'medicin', 'farmakologi', 'vandige', 'opløsning', 'udefinerbar',
                    'uidentificer', 'blandet', 'lossepladsperkolat', 'perkolat', 'deponi', 'pcb', 'asbeststøv', 'asbest'],
    },
    'POLARE_OPLØSNINGSMIDLER': {
        'distance_m': 100,
        'keywords': ['methanol', 'propanol', 'isopropanol', 'ethanol', 'glykoler', 'glycol', 'dioxan',
                    'diethylether', 'ether', 'dimethylsulfamid', 'dms', 'alkoholer', 'ethylenglykol',
                    'propylenglykol', 'ethylacetat', 'n-butyl-acetat', 'tetrahydrofuran', 'butanol',
                    'benzylalkohol', 'anilin', 'dimethylamin', 'pyridin'],
    },
    'SPECIALKEMIKALIER': {
        'distance_m': 200,
        'keywords': ['phthalater', 'phthalate', 'cresoler', 'cresol', 'kimtal', 'heterocy', 'cykl',
                    'fluorcarbon', 'fluorid', 'fluoranthen', 'formaldehyd', 'malathion',
                    'pftba', 'pfas', 'pfos', 'pfoa', 'acetonitril', 'dmso', 'dimethylsulfoxid',
                    'toluensulfonamid', 'epichlorhydrin', 'dichlorpropanol', 'phthalat', 'succinsyre',
                    'adipinsyre', 'glutarsyre', 'fumarsyre', 'hydrogensulfid', 'hydrogen sulfid',
                    'carbontetrachlorid', 'carbon tetrachlorid', 'tetrachlorcarbon'],
    },
    'GASSER': {
        'distance_m': 500,
        'keywords': ['methan', 'methane', 'carbondioxid', 'co2', 'hydrogen', 'gas'],
    },
    'HALOGENEREDE_FORBINDELSER': {
        'distance_m': 200,
        'keywords': ['monobromdichlormet', 'bromdichlormethan', 'brommethan', 'dichlormethan'],
    },
}


def categorize_contamination_substance(substance_text: str):
    """Return (category, distance_m) for a given free-text substance token."""
    if pd.isna(substance_text) or not isinstance(substance_text, str):
        return 'UNCATEGORIZED', None
    s = substance_text.lower().strip()
    for category, info in COMPOUND_DISTANCE_MAPPING.items():
        for kw in info['keywords']:
            if kw in s:
                return category, info['distance_m']
    return 'UNCATEGORIZED', None


def setup_professional_figure(figsize=(12, 8), title="", subtitle=""):
    """Create a professionally styled figure matching professional_visualizations.py."""
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


def create_category_threshold_dashboard(cat_summary, sub_summary, long_df):
    """Create a comprehensive dashboard showing category-based threshold analysis."""
    
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
            colors.append(RISK_COLORS.get(distance, COLORS['neutral']))
        else:
            colors.append(COLORS['neutral'])
    
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
            colors2.append(RISK_COLORS.get(distance, COLORS['neutral']))
        else:
            colors2.append(COLORS['neutral'])
    
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
                'distance': distance,
                'within_sites': row['within_tokens'],
                'total_sites': row['total_tokens']
            })
    
    dist_df = pd.DataFrame(distance_data)
    if not dist_df.empty:
        dist_summary = dist_df.groupby('distance').agg({
            'within_sites': 'sum',
            'total_sites': 'sum'
        }).reset_index()
        
        # Create scatter plot
        for _, row in dist_summary.iterrows():
            distance = row['distance']
            color = RISK_COLORS.get(distance, COLORS['neutral'])
            ax3.scatter(distance, row['within_sites'], 
                       s=row['total_sites']*10, color=color, alpha=0.7)
        
        ax3.set_xlabel('Distance Threshold (meters)')
        ax3.set_ylabel('Within-Threshold Sites')
        ax3.set_title('C. Threshold vs. Success Rate\n(bubble size = total sites)', 
                      fontweight='bold', pad=20)
        ax3.grid(True, alpha=0.3)
    
    # 4. Top substances within threshold (Bottom Right)
    ax4 = plt.subplot(2, 2, 4)
    
    # Get top substances that are within threshold
    within_substances = long_df[long_df['Within_Threshold'] == True]
    if not within_substances.empty:
        top_substances = within_substances['Substance'].value_counts().head(8)
        
        bars4 = ax4.barh(range(len(top_substances)), list(top_substances.values), 
                         color=COLORS['accent'], alpha=0.8)
        
        ax4.set_yticks(range(len(top_substances)))
        labels = [s[:30] + '...' if len(s) > 30 else s for s in top_substances.index]
        ax4.set_yticklabels(labels, fontsize=9)
        ax4.set_xlabel('Number of Within-Threshold Sites')
        ax4.set_title('D. Most Common Within-Threshold Substances', 
                      fontweight='bold', pad=20)
        ax4.grid(True, alpha=0.3)
        
        # Add count labels
        for i, (bar, count) in enumerate(zip(bars4, top_substances.values)):
            ax4.text(count + max(top_substances.values) * 0.01, i,
                    f'{count}', va='center', fontweight='bold', fontsize=9)
    
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
    
    return fig


def create_category_detailed_analysis(sub_summary, long_df):
    """Create detailed analysis of top categories with substance breakdowns."""
    
    # Get top 6 categories by within-threshold count
    cat_within_counts = long_df[long_df['Within_Threshold'] == True]['Category'].value_counts().head(6)
    
    if cat_within_counts.empty:
        return None
    
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
            continue
            
        substance_counts = cat_data['Substance'].value_counts().head(10)
        
        # Get category info
        distance = COMPOUND_DISTANCE_MAPPING.get(category, {}).get('distance_m', 'Unknown')
        color = RISK_COLORS.get(distance, COLORS['neutral'])
        
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
    
    return fig


def _resolve_site_id_col(df: pd.DataFrame) -> str:
    """Return the available site id column name (Lokalitet_ID or Lokalitet_)."""
    if 'Lokalitet_ID' in df.columns:
        return 'Lokalitet_ID'
    if 'Lokalitet_' in df.columns:
        return 'Lokalitet_'
    # Fallback: try case-insensitive match
    for c in df.columns:
        if c.lower() in {'lokalitet_id', 'lokalitet_'}:
            return c
    raise KeyError("No site id column found (expected 'Lokalitet_ID' or 'Lokalitet_')")


def run_step5_category_thresholds(step4_csv_path: Optional[str] = None):
    """
    Compute per-substance/category within-threshold flags using Step 4 distances.

    Args:
        step4_csv_path: Optional explicit path; when None, use config.get_output_path('step4_final_distances_for_risk_assessment')

    Returns:
        dict with paths to created artifacts
    """
    ensure_results_directory()

    if step4_csv_path is None:
        step4_csv_path = get_output_path('step4_final_distances_for_risk_assessment')
    if not os.path.exists(step4_csv_path):
        print(f"Step 4 file not found: {step4_csv_path}")
        return {}

    df = pd.read_csv(step4_csv_path)
    if 'Final_Distance_m' not in df.columns:
        print("Missing 'Final_Distance_m' column in Step 4 results")
        return {}

    if 'Lokalitetensstoffer' not in df.columns:
        print("Missing 'Lokalitetensstoffer' in Step 4 results; cannot categorize by substance")
        return {}

    site_id_col = _resolve_site_id_col(df)

    # Explode substances per site
    rows = []
    for _, r in df.iterrows():
        subs_raw = r['Lokalitetensstoffer']
        if pd.isna(subs_raw) or str(subs_raw).strip() == '':
            # Still record a None token for completeness
            tokens = []
        else:
            s = str(subs_raw).replace(';', ',')
            tokens = [t.strip() for t in s.split(',') if t.strip()]

        if not tokens:
            # Represent absence explicitly
            rows.append({
                'Site_ID': r[site_id_col],
                'Closest_GVFK': r.get('Closest_GVFK', None),
                'Site_Type': r.get('Site_Type', None),
                'Final_Distance_m': r['Final_Distance_m'],
                'Substance': None,
                'Category': 'UNCATEGORIZED',
                'Category_Distance_m': np.nan,
                'Within_Threshold': False,
            })
            continue

        for tok in tokens:
            category, dist = categorize_contamination_substance(tok)
            within = False
            if dist is not None:
                try:
                    within = float(r['Final_Distance_m']) <= float(dist)
                except Exception:
                    within = False

            rows.append({
                'Site_ID': r[site_id_col],
                'Closest_GVFK': r.get('Closest_GVFK', None),
                'Site_Type': r.get('Site_Type', None),
                'Final_Distance_m': r['Final_Distance_m'],
                'Substance': tok,
                'Category': category,
                'Category_Distance_m': dist,
                'Within_Threshold': within,
            })

    long_df = pd.DataFrame(rows)

    # Save flags table
    flags_path = get_output_path('step5_category_flags')
    long_df.to_csv(flags_path, index=False)
    print(f"Saved per-substance flags: {flags_path} ({len(long_df)} rows)")

    # Aggregate by category
    cat_summary = (long_df
                   .assign(has_substance=long_df['Substance'].notna())
                   .groupby('Category', dropna=False)
                   .agg(total_tokens=('has_substance', 'sum'),
                        within_tokens=('Within_Threshold', 'sum'))
                   .reset_index())
    # Avoid division by zero
    cat_summary['within_pct'] = np.where(cat_summary['total_tokens'] > 0,
                                         100 * cat_summary['within_tokens'] / cat_summary['total_tokens'], 0.0)

    cat_summary_path = get_output_path('step5_category_summary')
    cat_summary.to_csv(cat_summary_path, index=False)
    print(f"Saved category summary: {cat_summary_path}")

    # Aggregate by (category, substance)
    sub_summary = (long_df[long_df['Substance'].notna()]
                   .groupby(['Category', 'Substance'])
                   .agg(total=('Substance', 'size'),
                        within=('Within_Threshold', 'sum'))
                   .reset_index())
    sub_summary['within_pct'] = np.where(sub_summary['total'] > 0,
                                         100 * sub_summary['within'] / sub_summary['total'], 0.0)

    sub_summary_path = get_output_path('step5_category_substance_summary')
    sub_summary.to_csv(sub_summary_path, index=False)
    print(f"Saved category-substance summary: {sub_summary_path}")

    # Create professional visualizations
    print("Creating professional visualizations...")
    
    # 1. Main dashboard
    try:
        dashboard_fig = create_category_threshold_dashboard(cat_summary, sub_summary, long_df)
        dashboard_path = get_output_path('step5_category_dashboard_png')
        dashboard_fig.savefig(dashboard_path, dpi=300, bbox_inches='tight')
        plt.close(dashboard_fig)
        print(f"Saved category dashboard: {dashboard_path}")
    except Exception as e:
        print(f"Dashboard creation failed: {e}")
    
    # 2. Detailed category analysis
    try:
        detailed_fig = create_category_detailed_analysis(sub_summary, long_df)
        if detailed_fig:
            detailed_path = get_output_path('step5_category_detailed_png')
            detailed_fig.savefig(detailed_path, dpi=300, bbox_inches='tight')
            plt.close(detailed_fig)
            print(f"Saved detailed analysis: {detailed_path}")
    except Exception as e:
        print(f"Detailed analysis creation failed: {e}")
    
    # 3. Simple overview plot (keeping the original as backup)
    try:
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
                colors.append(RISK_COLORS.get(distance, COLORS['neutral']))
            else:
                colors.append(COLORS['neutral'])
        
        bars = ax.barh(range(len(plot_df)), plot_df['within_tokens'], color=colors, alpha=0.8)
        
        # Customize
        ax.set_yticks(range(len(plot_df)))
        ax.set_yticklabels([cat.replace('_', ' ').title() for cat in plot_df['Category']])
        ax.set_xlabel('Within-threshold substance tokens (count)')
        ax.invert_yaxis()
        
        # Add count and percentage labels
        for i, category in enumerate(plot_df.index):
            # Use direct array access to avoid Scalar type issues
            count = plot_df['within_tokens'].iloc[i]
            total = plot_df['total_tokens'].iloc[i]
            pct = (count / total * 100) if total > 0 else 0
            
            ax.text(count + max(plot_df['within_tokens']) * 0.01, i,
                   f'{count} ({pct:.1f}%)', va='center', fontweight='bold', fontsize=10)
        
        # Add risk level legend
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
        plot_path = get_output_path('step5_category_overview_png')
        overview_fig.savefig(plot_path, dpi=300, bbox_inches='tight')
        plt.close(overview_fig)
        print(f"Saved category overview plot: {plot_path}")
        
    except Exception as e:
        print(f"Overview plot generation failed: {e}")

    return {
        'flags_csv': flags_path,
        'category_summary_csv': cat_summary_path,
        'substance_summary_csv': sub_summary_path,
    }


if __name__ == '__main__':
    run_step5_category_thresholds()
