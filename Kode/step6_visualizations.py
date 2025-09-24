"""
Step 6 Visualizations and Analysis
==================================

Creates plots and analysis for the Tilstandsvurdering (flux calculation) results.
"""

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
import os
from config import get_visualization_path

def analyze_and_visualize_step6(flux_results, match_stats):
    """
    Create comprehensive analysis and visualizations for Step 6 results.
    
    Args:
        flux_results (DataFrame): Results from flux calculation
        match_stats (dict): Statistics about data matching
    """
    
    print("\nSTEP 6: TILSTANDSVURDERING - DETAILED ANALYSIS")
    print("=" * 60)
    
    # 1. Data Quality Analysis
    _analyze_data_quality(flux_results, match_stats)
    
    # 2. Flux Distribution Analysis  
    _analyze_flux_distribution(flux_results)
    
    # 3. Category Analysis
    _analyze_by_category(flux_results)
    
    # 4. Spatial Analysis
    _analyze_spatial_patterns(flux_results)
    
    # 5. Generate Visualizations
    _create_visualizations(flux_results)
    
    print("\n" + "=" * 60)
    print("STEP 6 ANALYSIS COMPLETE")
    print("=" * 60)

def _analyze_data_quality(flux_results, match_stats):
    """Analyze data quality and matching success."""
    print("\n1. DATA QUALITY & MATCHING SUCCESS")
    print("-" * 40)
    
    total_combinations = len(flux_results)
    unique_sites = flux_results['Lokalitet_ID'].nunique()
    unique_gvfks = flux_results['Closest_GVFK'].nunique()
    
    print(f"Total site-substance combinations: {total_combinations:,}")
    print(f"Unique contamination sites: {unique_sites:,}")  
    print(f"Unique GVFKs affected: {unique_gvfks:,}")
    print(f"Average substances per site: {total_combinations/unique_sites:.1f}")
    
    print(f"\nMatching Success Rates:")
    print(f"  GVFK → Layer mapping: {match_stats.get('gvfk_match_rate', 0):.1f}%")
    print(f"  Site → Geometry mapping: {match_stats.get('geometry_match_rate', 0):.1f}%")
    print(f"  Layer → Raster availability: {match_stats.get('raster_match_rate', 0):.1f}%")
    
    if 'missing_layers' in match_stats:
        print(f"  Missing raster layers: {', '.join(match_stats['missing_layers'])}")

def _analyze_flux_distribution(flux_results):
    """Analyze pollution flux distribution."""
    print("\n2. POLLUTION FLUX DISTRIBUTION")
    print("-" * 35)
    
    flux_col = 'Pollution_Flux_ug_per_year'
    flux_stats = flux_results[flux_col].describe()
    
    print(f"Flux Statistics (J = A × C × I):")
    print(f"  Count: {flux_stats['count']:,.0f}")
    print(f"  Mean: {flux_stats['mean']:.2e} μg/år ({flux_stats['mean']/1e9:.2e} kg/år)")
    print(f"  Median: {flux_stats['50%']:.2e} μg/år ({flux_stats['50%']/1e9:.2e} kg/år)")
    print(f"  Std Dev: {flux_stats['std']:.2e} μg/år")
    print(f"  Min: {flux_stats['min']:.2e} μg/år")
    print(f"  Max: {flux_stats['max']:.2e} μg/år ({flux_stats['max']/1e9:.2e} kg/år)")
    
    # Percentile analysis
    percentiles = [90, 95, 99]
    print(f"\nHigh-Risk Sites (Flux Percentiles):")
    for p in percentiles:
        threshold = np.percentile(flux_results[flux_col], p)
        count = (flux_results[flux_col] >= threshold).sum()
        print(f"  {p}th percentile: {threshold:.2e} μg/år ({count:,} sites)")

def _analyze_by_category(flux_results):
    """Analyze results by contamination category."""
    print("\n3. CONTAMINATION CATEGORY ANALYSIS")
    print("-" * 40)
    
    flux_col = 'Pollution_Flux_ug_per_year'
    category_stats = flux_results.groupby('Qualifying_Category').agg({
        'Lokalitet_ID': 'nunique',
        flux_col: ['count', 'mean', 'sum'],
        'Area_m2': 'mean',
        'I_Value': 'mean',
        'Standard_Concentration_ug_L': 'first'
    }).round(2)
    
    # Flatten column names
    category_stats.columns = ['Sites', 'Combinations', 'Mean_Flux', 'Total_Flux', 'Mean_Area', 'Mean_I', 'Conc_C']
    category_stats = category_stats.sort_values('Total_Flux', ascending=False)
    
    print(f"{'Category':<25} {'Sites':<8} {'Comb.':<6} {'Mean Flux':<12} {'Total Flux':<12} {'C':<6}")
    print(f"{'─'*25} {'─'*8} {'─'*6} {'─'*12} {'─'*12} {'─'*6}")
    
    for category, row in category_stats.head(8).iterrows():
        print(f"{category:<25} {row['Sites']:<8,} {row['Combinations']:<6,} {row['Mean_Flux']:<12.2e} {row['Total_Flux']:<12.2e} {row['Conc_C']:<6.1f}")
    
    # Category contribution analysis
    total_flux = flux_results[flux_col].sum()
    print(f"\nTop 3 Categories by Total Flux Contribution:")
    for i, (category, row) in enumerate(category_stats.head(3).iterrows()):
        contribution = (row['Total_Flux'] / total_flux) * 100
        print(f"  {i+1}. {category}: {contribution:.1f}% of total flux")

def _analyze_spatial_patterns(flux_results):
    """Analyze spatial patterns in the results."""
    print("\n4. SPATIAL PATTERN ANALYSIS")
    print("-" * 30)
    
    # GVFK-level analysis
    flux_col = 'Pollution_Flux_ug_per_year'
    gvfk_stats = flux_results.groupby('Closest_GVFK').agg({
        'Lokalitet_ID': 'nunique',
        flux_col: 'sum',
        'Area_m2': 'sum'
    }).sort_values(flux_col, ascending=False)
    
    print(f"GVFK Risk Assessment:")
    print(f"  Total GVFKs with contamination: {len(gvfk_stats):,}")
    print(f"  Mean sites per GVFK: {gvfk_stats['Lokalitet_ID'].mean():.1f}")
    print(f"  Mean flux per GVFK: {gvfk_stats[flux_col].mean():.2e} μg/år")
    
    # Top risk GVFKs
    print(f"\nTop 5 GVFKs by Total Flux:")
    for i, (gvfk, row) in enumerate(gvfk_stats.head(5).iterrows()):
        print(f"  {i+1}. {gvfk}: {row[flux_col]:.2e} μg/år ({row['Lokalitet_ID']} sites)")
    
    # Area distribution
    area_stats = flux_results['Area_m2'].describe()
    print(f"\nSite Area Distribution:")
    print(f"  Mean area: {area_stats['mean']:,.0f} m²")
    print(f"  Median area: {area_stats['50%']:,.0f} m²") 
    print(f"  Largest site: {area_stats['max']:,.0f} m²")

def _create_visualizations(flux_results):
    """Create and save visualization plots."""
    print("\n5. GENERATING VISUALIZATIONS")
    print("-" * 30)
    
    viz_path = get_visualization_path('step6')
    
    # Set style
    plt.style.use('seaborn-v0_8-whitegrid')
    fig_size = (12, 8)
    
    # 1. Flux Distribution Histogram
    flux_col = 'Pollution_Flux_ug_per_year'
    plt.figure(figsize=fig_size)
    plt.hist(np.log10(flux_results[flux_col]), bins=50, alpha=0.7, edgecolor='black')
    plt.xlabel('Log10(Pollution Flux - μg/år)')
    plt.ylabel('Number of Sites')
    plt.title('Distribution of Pollution Flux Values (Log Scale)')
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(os.path.join(viz_path, 'flux_distribution.png'), dpi=300, bbox_inches='tight')
    plt.close()
    
    # 2. Category Comparison
    category_summary = flux_results.groupby('Qualifying_Category').agg({
        'Lokalitet_ID': 'nunique',
        flux_col: 'sum'
    }).sort_values(flux_col, ascending=True)
    
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 8))
    
    # Sites per category
    category_summary['Lokalitet_ID'].plot(kind='barh', ax=ax1, color='steelblue')
    ax1.set_xlabel('Number of Unique Sites')
    ax1.set_title('Sites per Contamination Category')
    
    # Total flux per category
    category_summary[flux_col].plot(kind='barh', ax=ax2, color='darkred')
    ax2.set_xlabel('Total Pollution Flux (μg/år)')
    ax2.set_title('Total Flux per Contamination Category')
    ax2.ticklabel_format(style='scientific', axis='x', scilimits=(0,0))
    
    plt.tight_layout()
    plt.savefig(os.path.join(viz_path, 'category_analysis.png'), dpi=300, bbox_inches='tight')
    plt.close()
    
    # 3. Parameter Correlation
    plt.figure(figsize=fig_size)
    
    # Create correlation matrix for key parameters  
    corr_data = flux_results[['Area_m2', 'I_Value', 'Standard_Concentration_ug_L', flux_col]].corr()
    
    sns.heatmap(corr_data, annot=True, cmap='coolwarm', center=0, 
                square=True, cbar_kws={'label': 'Correlation Coefficient'})
    plt.title('Parameter Correlation Matrix\n(A = Area, I = Raster Value, C = Concentration, J = Flux)')
    plt.tight_layout()
    plt.savefig(os.path.join(viz_path, 'parameter_correlation.png'), dpi=300, bbox_inches='tight')
    plt.close()
    
    # 4. Area vs Flux Scatter
    plt.figure(figsize=fig_size)
    
    # Sample points to avoid overplotting
    sample_data = flux_results.sample(min(2000, len(flux_results)))
    
    scatter = plt.scatter(sample_data['Area_m2'], sample_data[flux_col], 
                         c=sample_data['I_Value'], cmap='viridis', alpha=0.6, s=20)
    
    plt.xlabel('Site Area (m²)')
    plt.ylabel('Pollution Flux (μg/år)')
    plt.title('Site Area vs Pollution Flux\n(Color = I Value from Raster)')
    plt.xscale('log')
    plt.yscale('log')
    plt.colorbar(scatter, label='I Value')
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(os.path.join(viz_path, 'area_vs_flux.png'), dpi=300, bbox_inches='tight')
    plt.close()
    
    print(f"Visualizations saved to: {viz_path}")
    print(f"  - flux_distribution.png")
    print(f"  - category_analysis.png") 
    print(f"  - parameter_correlation.png")
    print(f"  - area_vs_flux.png")

if __name__ == "__main__":
    # Test with dummy data
    print("Step 6 visualization module loaded successfully!")