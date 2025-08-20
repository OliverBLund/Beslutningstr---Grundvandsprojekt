"""
Step 5: Comprehensive Risk Assessment and Analysis of High-Risk V1/V2 Sites

Includes general assessment, compound-specific assessment, category analysis, and visualizations.
"""

import pandas as pd
import geopandas as gpd
import numpy as np
import os
from config import (get_output_path, ensure_results_directory, GRUNDVAND_PATH, 
                   WORKFLOW_SETTINGS, COMPOUND_RISK_DISTANCES)

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
    general_results = run_general_risk_assessment(distance_results)
    compound_results = run_compound_specific_assessment(distance_results)
    
    # Print summary
    _print_assessment_summary(general_results, compound_results, len(distance_results))
    
    return general_results, compound_results

def run_general_risk_assessment(distance_results):
    """General risk assessment using universal distance threshold."""
    risk_threshold_m = WORKFLOW_SETTINGS['risk_threshold_m']
    
    high_risk_sites = distance_results[
        distance_results['Final_Distance_m'] <= risk_threshold_m
    ].copy()
    
    if high_risk_sites.empty:
        return high_risk_sites, {}
    
    # Analyze and save results
    analysis_summary = _analyze_contamination_characteristics(high_risk_sites, risk_threshold_m)
    _save_step5_results(high_risk_sites, analysis_summary, risk_threshold_m)
    
    return high_risk_sites, analysis_summary

def run_compound_specific_assessment(distance_results):
    """Compound-specific risk assessment using tailored thresholds."""
    compound_high_risk_sites = _apply_compound_specific_filtering(distance_results)
    
    if compound_high_risk_sites.empty:
        return compound_high_risk_sites, {}
    
    # Analyze and save results
    compound_analysis_summary = _analyze_compound_specific_characteristics(compound_high_risk_sites)
    _save_compound_specific_results(compound_high_risk_sites, compound_analysis_summary)
    
    return compound_high_risk_sites, compound_analysis_summary

def _apply_compound_specific_filtering(distance_results):
    """Apply compound-specific distance filtering."""
    high_risk_rows = []
    compound_assignments = []
    
    # Handle sites ID column robustly
    site_id_col = _resolve_site_id_col(distance_results)
    
    for _, row in distance_results.iterrows():
        substances_str = str(row.get('Lokalitetensstoffer', ''))
        if pd.isna(substances_str) or substances_str.strip() == '' or substances_str == 'nan':
            continue
            
        substances = [s.strip() for s in substances_str.split(';') if s.strip()]
        site_distance = row['Final_Distance_m']
        site_is_high_risk = False
        
        for substance in substances:
            # Find matching compound and its threshold
            matched_compound = None
            compound_threshold = COMPOUND_RISK_DISTANCES.get('default', 300)
            
            for compound_name, threshold in COMPOUND_RISK_DISTANCES.items():
                if compound_name == 'default':
                    continue
                if compound_name.lower() in substance.lower() or substance.lower() in compound_name.lower():
                    matched_compound = compound_name
                    compound_threshold = threshold
                    break
            
            # Check if site is within this compound's threshold
            if site_distance <= compound_threshold:
                site_is_high_risk = True
                compound_assignments.append({
                    site_id_col: row[site_id_col],
                    'Substance': substance,
                    'Matched_Compound': matched_compound or 'default',
                    'Applied_Threshold_m': compound_threshold,
                    'Site_Distance_m': site_distance,
                    'Within_Threshold': True
                })
        
        if site_is_high_risk:
            high_risk_rows.append(row)
    
    # Save compound assignments
    if compound_assignments:
        assignments_df = pd.DataFrame(compound_assignments)
        assignment_path = get_output_path('step5_compound_distance_mapping')
        assignments_df.to_csv(assignment_path, index=False)
    
    return pd.DataFrame(high_risk_rows) if high_risk_rows else pd.DataFrame()

def _analyze_compound_specific_characteristics(compound_high_risk_sites):
    """Analyze characteristics of compound-specific high-risk sites."""
    analysis = {
        'total_sites': len(compound_high_risk_sites),
        'distance_stats': {},
        'site_type_distribution': {},
        'contamination_analysis': {}
    }
    
    # Distance statistics
    if 'Final_Distance_m' in compound_high_risk_sites.columns:
        distances = compound_high_risk_sites['Final_Distance_m']
        analysis['distance_stats'] = {
            'min': float(distances.min()),
            'max': float(distances.max()),
            'mean': float(distances.mean()),
            'median': float(distances.median())
        }
    
    # Site type distribution
    if 'Site_Type' in compound_high_risk_sites.columns:
        site_type_counts = compound_high_risk_sites['Site_Type'].value_counts()
        analysis['site_type_distribution'] = site_type_counts.to_dict()
    
    # Contamination analysis
    for col in ['Lokalitetensbranche', 'Lokalitetensaktivitet', 'Lokalitetensstoffer']:
        if col in compound_high_risk_sites.columns:
            analysis['contamination_analysis'][col] = _analyze_contamination_column(
                compound_high_risk_sites, col, len(compound_high_risk_sites)
            )
    
    return analysis

def _analyze_contamination_characteristics(high_risk_sites, threshold_m):
    """Analyze contamination characteristics of high-risk sites."""
    analysis = {
        'threshold_m': threshold_m,
        'total_sites': len(high_risk_sites),
        'distance_stats': {},
        'contamination_analysis': {}
    }
    
    # Distance statistics
    if 'Final_Distance_m' in high_risk_sites.columns:
        distances = high_risk_sites['Final_Distance_m']
        analysis['distance_stats'] = {
            'min': float(distances.min()),
            'max': float(distances.max()),
            'mean': float(distances.mean()),
            'median': float(distances.median())
        }
    
    # Contamination analysis
    for col in ['Lokalitetensbranche', 'Lokalitetensaktivitet', 'Lokalitetensstoffer']:
        if col in high_risk_sites.columns:
            analysis['contamination_analysis'][col] = _analyze_contamination_column(
                high_risk_sites, col, len(high_risk_sites)
            )
    
    return analysis

def _analyze_contamination_column(sites_df, col, total_sites):
    """Analyze a contamination column (handles semicolon-separated values)."""
    data = sites_df[col].dropna()
    if data.empty:
        return {'total_with_data': 0, 'unique_values': 0, 'top_values': []}
    
    # Handle semicolon-separated values
    all_values = []
    for value in data:
        if pd.isna(value) or str(value).strip() == '' or str(value) == 'nan':
            continue
        values = [v.strip() for v in str(value).split(';') if v.strip()]
        all_values.extend(values)
    
    value_counts = pd.Series(all_values).value_counts()
    
    return {
        'total_with_data': len(data),
        'percentage_with_data': (len(data) / total_sites * 100) if total_sites > 0 else 0,
        'unique_values': len(value_counts),
        'total_occurrences': len(all_values),
        'top_values': value_counts.head(10).to_dict()
    }

def _save_step5_results(high_risk_sites, analysis_summary, threshold_m):
    """Save general assessment results."""
    # Save high-risk sites
    sites_path = get_output_path('step5_high_risk_sites', threshold_m)
    high_risk_sites.to_csv(sites_path, index=False)
    
    # Save analysis summary
    summary_path = get_output_path('step5_analysis_summary', threshold_m)
    summary_df = pd.DataFrame([analysis_summary])
    summary_df.to_csv(summary_path, index=False)
    
    # Save contamination breakdown
    breakdown_path = get_output_path('step5_contamination_breakdown', threshold_m)
    breakdown_data = []
    for col, analysis in analysis_summary.get('contamination_analysis', {}).items():
        for value, count in analysis.get('top_values', {}).items():
            breakdown_data.append({
                'Column': col,
                'Value': value,
                'Count': count,
                'Percentage': (count / analysis_summary['total_sites'] * 100) if analysis_summary['total_sites'] > 0 else 0
            })
    
    if breakdown_data:
        breakdown_df = pd.DataFrame(breakdown_data)
        breakdown_df.to_csv(breakdown_path, index=False)
    
    # Create high-risk GVFK shapefile
    _create_high_risk_gvfk_shapefile(high_risk_sites, threshold_m)

def _save_compound_specific_results(compound_high_risk_sites, compound_analysis_summary):
    """Save compound-specific assessment results."""
    # Save high-risk sites
    sites_path = get_output_path('step5_compound_specific_sites')
    compound_high_risk_sites.to_csv(sites_path, index=False)
    
    # Save analysis summary
    summary_path = get_output_path('step5_compound_analysis_summary')
    summary_df = pd.DataFrame([compound_analysis_summary])
    summary_df.to_csv(summary_path, index=False)
    
    # Save contamination breakdown
    breakdown_path = get_output_path('step5_compound_breakdown')
    breakdown_data = []
    for col, analysis in compound_analysis_summary.get('contamination_analysis', {}).items():
        for value, count in analysis.get('top_values', {}).items():
            breakdown_data.append({
                'Column': col,
                'Value': value,
                'Count': count,
                'Percentage': (count / compound_analysis_summary['total_sites'] * 100) if compound_analysis_summary['total_sites'] > 0 else 0
            })
    
    if breakdown_data:
        breakdown_df = pd.DataFrame(breakdown_data)
        breakdown_df.to_csv(breakdown_path, index=False)
    
    # Create compound-specific GVFK shapefile
    _create_compound_specific_gvfk_shapefile(compound_high_risk_sites)

def _create_high_risk_gvfk_shapefile(high_risk_sites, threshold_m):
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
    site_id_col = _resolve_site_id_col(grundvand_gdf)
    high_risk_gvfk_polygons = grundvand_gdf[
        grundvand_gdf[site_id_col].isin(high_risk_gvfk_names)
    ].copy()
    
    if not high_risk_gvfk_polygons.empty:
        output_path = get_output_path('step5_gvfk_high_risk', threshold_m)
        high_risk_gvfk_polygons.to_file(output_path)
    
    return high_risk_gvfk_names

def _create_compound_specific_gvfk_shapefile(compound_high_risk_sites):
    """Create shapefile of compound-specific high-risk GVFK polygons."""
    grundvand_gdf = gpd.read_file(GRUNDVAND_PATH)
    
    # Get high-risk GVFK names
    high_risk_gvfk_names = set()
    for _, row in compound_high_risk_sites.iterrows():
        gvfk_list = str(row.get('All_Affected_GVFKs', ''))
        if gvfk_list and gvfk_list != 'nan':
            gvfks = [g.strip() for g in gvfk_list.split(';') if g.strip()]
            high_risk_gvfk_names.update(gvfks)
        elif 'Closest_GVFK' in row:
            closest_gvfk = str(row['Closest_GVFK'])
            if closest_gvfk and closest_gvfk != 'nan':
                high_risk_gvfk_names.add(closest_gvfk)
    
    # Filter GVFK polygons
    site_id_col = _resolve_site_id_col(grundvand_gdf)
    high_risk_gvfk_polygons = grundvand_gdf[
        grundvand_gdf[site_id_col].isin(high_risk_gvfk_names)
    ].copy()
    
    if not high_risk_gvfk_polygons.empty:
        output_path = get_output_path('step5_compound_gvfk_high_risk')
        high_risk_gvfk_polygons.to_file(output_path)
    
    return high_risk_gvfk_names

def _resolve_site_id_col(df):
    """Resolve the site ID column name in the dataframe."""
    possible_cols = ['DGU_nr', 'Lokalitet_ID', 'LOKALITET_ID', 'lokalitet_id', 'ID']
    for col in possible_cols:
        if col in df.columns:
            return col
    return df.columns[0]  # Fallback to first column

def _print_assessment_summary(general_results, compound_results, total_sites):
    """Print concise summary of both assessments."""
    general_sites, _ = general_results
    compound_sites, _ = compound_results
    
    general_count = len(general_sites) if general_sites is not None else 0
    compound_count = len(compound_sites) if compound_sites is not None else 0
    
    print(f"\nAssessment Results:")
    print(f"  General assessment (≤{WORKFLOW_SETTINGS['risk_threshold_m']}m): {general_count} sites ({general_count/total_sites*100:.1f}%)")
    print(f"  Compound-specific assessment: {compound_count} sites ({compound_count/total_sites*100:.1f}%)")

def run_comprehensive_step5():
    """
    Execute comprehensive Step 5 analysis including all components:
    1. General and compound-specific risk assessments
    2. Category-based threshold analysis with professional visualizations  
    3. All Step 5 visualizations
    """
    print(f"\nStep 5: COMPREHENSIVE RISK ASSESSMENT & ANALYSIS")
    print("=" * 70)
    
    comprehensive_results = {
        'general_results': (None, None),
        'compound_results': (None, None),
        'category_results': None,
        'success': False,
        'error_message': None
    }
    
    # Run standard assessments
    general_results, compound_results = run_step5()
    comprehensive_results['general_results'] = general_results
    comprehensive_results['compound_results'] = compound_results
    
    gen_sites, _ = general_results
    if gen_sites is None:
        raise ValueError("General risk assessment failed")
    
    # Run category-based analysis
    print("\nRunning category-based threshold analysis...")
    from step5_compound_threshold_counts import run_step5_category_thresholds
    category_results = run_step5_category_thresholds()
    comprehensive_results['category_results'] = category_results
    print("✓ Category-based analysis completed")
    
    # Run visualizations
    print("\nCreating Step 5 visualizations...")
    from step5_visualizations import create_step5_visualizations
    threshold_m = WORKFLOW_SETTINGS['risk_threshold_m']
    create_step5_visualizations(threshold_m=threshold_m)
    print("✓ Step 5 visualizations completed")
    
    comprehensive_results['success'] = True
    print(f"\n✓ COMPREHENSIVE STEP 5 ANALYSIS COMPLETED")
    
    return comprehensive_results

if __name__ == "__main__":
    # Allow running this step independently
    general_results, compound_results = run_step5()
    gen_sites, _ = general_results
    if gen_sites is not None:
        print(f"Step 5 completed. Found {len(gen_sites)} high-risk sites (general).")
        # Run category-based analysis
        try:
            from step5_compound_threshold_counts import run_step5_category_thresholds
            print("\nRunning category-based threshold analysis...")
            run_step5_category_thresholds()
            print("Category-based analysis completed successfully.")
        except Exception as e:
            print(f"Category-based analysis failed: {e}")
    else:
        print("Step 5 failed. Check that Step 4 has been completed first.")
