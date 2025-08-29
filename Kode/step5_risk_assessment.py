"""
Step 5: Risk Assessment of High-Risk V1/V2 Sites

Two-fold approach:
1. General Risk Assessment: Universal 500m threshold 
2. Compound-Specific Assessment: Uses compound-specific thresholds
"""

import pandas as pd
import geopandas as gpd
import numpy as np
import os

from config import get_output_path, ensure_results_directory, GRUNDVAND_PATH, WORKFLOW_SETTINGS
from compound_categorization import categorize_contamination_substance

def run_step5():
    """Execute Step 5: Two-part risk assessment of V1/V2 localities."""
    print(f"\nStep 5: Risk Assessment of High-Risk V1/V2 Sites")
    print("=" * 60)
    
    ensure_results_directory()
    
    # Load Step 4 results
    step4_file = get_output_path('step4_final_distances_for_risk_assessment')
    if not os.path.exists(step4_file):
        raise FileNotFoundError("Step 4 results not found. Please run Step 4 first.")
    
    distance_results = pd.read_csv(step4_file)
    print(f"Loaded {len(distance_results)} localities from Step 4")
    
    # Run both assessments
    general_results = _run_general_assessment(distance_results)
    compound_results = _run_compound_assessment(distance_results)
    
    # Print summary
    _print_summary(general_results, compound_results, len(distance_results))
    
    return general_results, compound_results

def _run_general_assessment(distance_results):
    """General risk assessment using universal distance threshold."""
    risk_threshold_m = WORKFLOW_SETTINGS['risk_threshold_m']
    
    high_risk_sites = distance_results[
        distance_results['Final_Distance_m'] <= risk_threshold_m
    ].copy()
    
    if high_risk_sites.empty:
        return high_risk_sites, {}
    
    # Analyze and save results
    analysis = _analyze_sites(high_risk_sites, risk_threshold_m)
    _save_general_results(high_risk_sites, analysis, risk_threshold_m)
    
    return high_risk_sites, analysis

def _run_compound_assessment(distance_results):
    """Compound-specific risk assessment using tailored thresholds."""
    high_risk_sites = _apply_compound_filtering(distance_results)
    
    if high_risk_sites.empty:
        return high_risk_sites, {}
    
    # Analyze and save results
    analysis = _analyze_sites(high_risk_sites)
    _save_compound_results(high_risk_sites, analysis)
    
    return high_risk_sites, analysis

def _apply_compound_filtering(distance_results):
    """Apply compound-specific distance filtering."""
    high_risk_rows = []
    
    for _, row in distance_results.iterrows():
        substances_str = str(row.get('Lokalitetensstoffer', ''))
        if pd.isna(substances_str) or substances_str.strip() == '' or substances_str == 'nan':
            continue
            
        substances = [s.strip() for s in substances_str.split(';') if s.strip()]
        site_distance = row['Final_Distance_m']
        
        for substance in substances:
            category, compound_threshold = categorize_contamination_substance(substance)
            
            if compound_threshold is None:
                compound_threshold = WORKFLOW_SETTINGS.get('risk_threshold_m', 500)
            
            # Check if site is within this compound's threshold
            if site_distance <= compound_threshold:
                high_risk_rows.append(row)
                break  # Site qualifies, no need to check other substances
    
    return pd.DataFrame(high_risk_rows) if high_risk_rows else pd.DataFrame()

def _analyze_sites(sites_df, threshold_m=None):
    """Analyze characteristics of high-risk sites."""
    analysis = {
        'total_sites': len(sites_df),
        'distance_stats': {},
        'contamination_summary': {}
    }
    
    if threshold_m:
        analysis['threshold_m'] = threshold_m
    
    # Distance statistics
    if 'Final_Distance_m' in sites_df.columns:
        distances = sites_df['Final_Distance_m']
        analysis['distance_stats'] = {
            'min': float(distances.min()),
            'max': float(distances.max()),
            'mean': float(distances.mean()),
            'median': float(distances.median())
        }
    
    # Contamination analysis (simplified)
    for col in ['Lokalitetensbranche', 'Lokalitetensaktivitet', 'Lokalitetensstoffer']:
        if col in sites_df.columns:
            data = sites_df[col].dropna()
            if not data.empty:
                # Handle semicolon-separated values
                all_values = []
                for value in data:
                    if pd.isna(value) or str(value).strip() == '':
                        continue
                    values = [v.strip() for v in str(value).split(';') if v.strip()]
                    all_values.extend(values)
                
                if all_values:
                    value_counts = pd.Series(all_values).value_counts()
                    analysis['contamination_summary'][col] = {
                        'total_entries': len(data),
                        'unique_values': len(value_counts),
                        'top_3': value_counts.head(3).to_dict()
                    }
    
    return analysis

def _save_general_results(high_risk_sites, analysis, threshold_m):
    """Save general assessment results."""
    # Save high-risk sites
    sites_path = get_output_path('step5_high_risk_sites')
    high_risk_sites.to_csv(sites_path, index=False)
    
    # Create high-risk GVFK shapefile
    _create_gvfk_shapefile(high_risk_sites, 'step5_gvfk_high_risk')
    
    print(f"General assessment: {len(high_risk_sites)} sites saved")

def _save_compound_results(compound_high_risk_sites, analysis):
    """Save compound-specific assessment results."""
    # Save high-risk sites
    sites_path = get_output_path('step5_compound_specific_sites')
    compound_high_risk_sites.to_csv(sites_path, index=False)
    
    # Create compound-specific GVFK shapefile
    _create_gvfk_shapefile(compound_high_risk_sites, 'step5_compound_gvfk_high_risk')
    
    print(f"Compound-specific assessment: {len(compound_high_risk_sites)} sites saved")

def _create_gvfk_shapefile(high_risk_sites, output_key):
    """Create shapefile of high-risk GVFK polygons."""
    grundvand_gdf = gpd.read_file(GRUNDVAND_PATH)
    
    # Get high-risk GVFK names
    high_risk_gvfk_names = set()
    for _, row in high_risk_sites.iterrows():
        gvfk_list = str(row.get('All_Affected_GVFKs', ''))
        if gvfk_list and gvfk_list != 'nan':
            gvfks = [g.strip() for g in gvfk_list.split(';') if g.strip()]
            high_risk_gvfk_names.update(gvfks)
        elif 'Closest_GVFK' in row:
            closest_gvfk = str(row['Closest_GVFK'])
            if closest_gvfk and closest_gvfk != 'nan':
                high_risk_gvfk_names.add(closest_gvfk)
    
    # Filter GVFK polygons
    if 'Navn' in grundvand_gdf.columns:
        id_col = 'Navn'
    else:
        id_col = grundvand_gdf.columns[0]  # Fallback
    
    high_risk_gvfk_polygons = grundvand_gdf[
        grundvand_gdf[id_col].isin(high_risk_gvfk_names)
    ].copy()
    
    if not high_risk_gvfk_polygons.empty:
        output_path = get_output_path(output_key)
        high_risk_gvfk_polygons.to_file(output_path)

def _print_summary(general_results, compound_results, total_sites):
    """Print concise summary of both assessments."""
    general_sites, _ = general_results
    compound_sites, _ = compound_results
    
    general_count = len(general_sites) if general_sites is not None else 0
    compound_count = len(compound_sites) if compound_sites is not None else 0
    
    print(f"\nAssessment Results:")
    print(f"  General assessment (≤{WORKFLOW_SETTINGS['risk_threshold_m']}m): {general_count} sites ({general_count/total_sites*100:.1f}%)")
    print(f"  Compound-specific assessment: {compound_count} sites ({compound_count/total_sites*100:.1f}%)")

def run_step5_category_analysis():
    """
    Run category-based analysis for compound-specific visualizations.
    Creates the files needed by step5_visualizations.py
    """
    step4_file = get_output_path('step4_final_distances_for_risk_assessment')
    if not os.path.exists(step4_file):
        return
    
    df = pd.read_csv(step4_file)
    if 'Final_Distance_m' not in df.columns or 'Lokalitetensstoffer' not in df.columns:
        return
    
    # Create category flags by analyzing each substance
    rows = []
    for _, row in df.iterrows():
        substances_str = str(row.get('Lokalitetensstoffer', ''))
        if pd.isna(substances_str) or substances_str.strip() == '' or substances_str == 'nan':
            continue
            
        substances = [s.strip() for s in substances_str.split(';') if s.strip()]
        for substance in substances:
            category, threshold = categorize_contamination_substance(substance)
            within_threshold = False
            if threshold is not None:
                within_threshold = float(row['Final_Distance_m']) <= float(threshold)
            
            rows.append({
                'Site_ID': row['Lokalitet_ID'],
                'Substance': substance,
                'Category': category,
                'Category_Distance_m': threshold,
                'Final_Distance_m': row['Final_Distance_m'],
                'Within_Threshold': within_threshold
            })
    
    if not rows:
        return
        
    # Save category flags
    flags_df = pd.DataFrame(rows)
    flags_df.to_csv(get_output_path('step5_category_flags'), index=False)
    
    # Create category summary
    category_summary = flags_df.groupby('Category').agg({
        'Within_Threshold': ['sum', 'count']
    }).reset_index()
    category_summary.columns = ['Category', 'within_tokens', 'total_tokens']
    category_summary['within_pct'] = (category_summary['within_tokens'] / category_summary['total_tokens'] * 100)
    category_summary.to_csv(get_output_path('step5_category_summary'), index=False)
    
    # Create substance summary
    substance_summary = flags_df.groupby(['Category', 'Substance']).agg({
        'Within_Threshold': ['sum', 'count']
    }).reset_index()
    substance_summary.columns = ['Category', 'Substance', 'within', 'total']
    substance_summary['within_pct'] = (substance_summary['within'] / substance_summary['total'] * 100)
    substance_summary.to_csv(get_output_path('step5_category_substance_summary'), index=False)

def run_comprehensive_step5():
    """
    Execute comprehensive Step 5 analysis including both assessments and visualizations.
    """
    print(f"\nStep 5: COMPREHENSIVE RISK ASSESSMENT & ANALYSIS")
    print("=" * 70)
    
    try:
        # Run standard assessments
        general_results, compound_results = run_step5()
        
        # Run category analysis for visualizations
        run_step5_category_analysis()
        
        # Run visualizations if available
        print("\nCreating Step 5 visualizations...")
        try:
            from step5_visualizations import create_step5_visualizations, create_compound_specific_visualizations
            create_step5_visualizations()
            create_compound_specific_visualizations()
            print("✓ Step 5 visualizations completed")
        except ImportError:
            print("Warning: step5_visualizations module not found, skipping visualizations")
        except Exception as e:
            print(f"Warning: Could not create visualizations - {e}")
        
        print(f"\n✓ COMPREHENSIVE STEP 5 ANALYSIS COMPLETED")
        
        return {
            'general_results': general_results,
            'compound_results': compound_results,
            'success': True,
            'error_message': None
        }
        
    except Exception as e:
        print(f"Step 5 failed: {e}")
        return {
            'general_results': (None, None),
            'compound_results': (None, None),
            'success': False,
            'error_message': str(e)
        }

if __name__ == "__main__":
    # Allow running this step independently
    general_results, compound_results = run_step5()
    gen_sites, _ = general_results
    if gen_sites is not None:
        print(f"Step 5 completed. Found {len(gen_sites)} high-risk sites (general).")
    else:
        print("Step 5 failed. Check that Step 4 has been completed first.")