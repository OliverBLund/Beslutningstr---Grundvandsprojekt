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

# Global variables to cache Excel-based categorization data
_CATEGORIZATION_CACHE = None
_DEFAULT_OTHER_DISTANCE = 500

def _load_categorization_from_excel():
    """Load compound categorization data from Excel file."""
    global _CATEGORIZATION_CACHE
    
    if _CATEGORIZATION_CACHE is not None:
        return _CATEGORIZATION_CACHE
    
    # Path to Excel file (created by refined_compound_analysis.py)
    excel_path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)), 
        "compound_categorization_review.xlsx"
    )
    
    try:
        # Load summary sheet to get category distances
        summary_df = pd.read_excel(excel_path, sheet_name='Summary')
        
        # Build category → distance mapping
        category_distances = {}
        for _, row in summary_df.iterrows():
            category = row['Category']
            distance = row['Distance_m']
            if distance != 'TBD' and pd.notna(distance):
                category_distances[category] = float(distance)
            else:
                category_distances[category] = _DEFAULT_OTHER_DISTANCE
        
        # Load individual category sheets to build substance → category mapping
        substance_to_category = {}
        
        # Get all sheet names
        xl_file = pd.ExcelFile(excel_path)
        category_sheets = [sheet for sheet in xl_file.sheet_names 
                          if sheet not in ['Summary', 'Raw_Data']]
        
        for sheet_name in category_sheets:
            try:
                sheet_df = pd.read_excel(excel_path, sheet_name=sheet_name)
                
                if 'Substance' in sheet_df.columns:
                    substances = sheet_df['Substance'].dropna()
                    category = sheet_name.replace('_substances', '').upper()
                    
                    # Map each substance to its category
                    for substance in substances:
                        if pd.notna(substance):
                            substance_to_category[str(substance).lower().strip()] = category
                            
            except Exception as e:
                print(f"Warning: Could not load sheet {sheet_name}: {e}")
                continue
        
        _CATEGORIZATION_CACHE = {
            'category_distances': category_distances,
            'substance_to_category': substance_to_category
        }
        
        print(f"Loaded categorization for {len(category_distances)} categories, {len(substance_to_category)} substances")
        return _CATEGORIZATION_CACHE
        
    except Exception as e:
        print(f"Warning: Could not load Excel categorization: {e}")
        print("Using default 500m threshold for all compounds")
        return {
            'category_distances': {'OTHER': _DEFAULT_OTHER_DISTANCE},
            'substance_to_category': {}
        }

def categorize_contamination_substance(substance_text):
    """
    Categorize a contamination substance using Excel-based categorization.
    
    Args:
        substance_text (str): The contamination substance text
        
    Returns:
        tuple: (category_name, distance_m) 
    """
    if pd.isna(substance_text) or not isinstance(substance_text, str):
        return 'OTHER', _DEFAULT_OTHER_DISTANCE
    
    # Load categorization data
    cat_data = _load_categorization_from_excel()
    
    substance_lower = substance_text.lower().strip()
    
    # Check for exact match first
    category = cat_data['substance_to_category'].get(substance_lower)
    
    if category:
        distance = cat_data['category_distances'].get(category, _DEFAULT_OTHER_DISTANCE)
        return category, distance
    
    # If no exact match, check if substance contains any of the categorized substances
    for known_substance, known_category in cat_data['substance_to_category'].items():
        if known_substance in substance_lower or substance_lower in known_substance:
            distance = cat_data['category_distances'].get(known_category, _DEFAULT_OTHER_DISTANCE)
            return known_category, distance
    
    # Default to OTHER category
    return 'OTHER', _DEFAULT_OTHER_DISTANCE

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

def _load_fractile_thresholds_from_python():
    """Load fractile threshold data directly from refined_compound_analysis.py"""
    try:
        import sys
        import os
        exploratory_path = os.path.join(os.path.dirname(__file__), 'Exploratory Analysis')
        sys.path.append(exploratory_path)
        
        from refined_compound_analysis import LITERATURE_COMPOUND_MAPPING
        
        fractile_data = {}
        for category, info in LITERATURE_COMPOUND_MAPPING.items():
            fractile_data[category] = {
                'fractile_60_m': info.get('fractile_60_m', info.get('distance_m', 500) * 0.3),
                'fractile_75_m': info.get('fractile_75_m', info.get('distance_m', 500) * 0.5),
                'fractile_90_m': info.get('fractile_90_m', info.get('distance_m', 500) * 0.8),
                'maksimal_m': info.get('maksimal_m', info.get('distance_m', 500)),
                'keywords': info.get('keywords', []),
                'description': info.get('description', ''),
                'literature_basis': info.get('literature_basis', '')
            }
        
        return fractile_data
        
    except Exception as e:
        print(f"Warning: Could not load fractile data from Python: {e}")
        return {}

def run_multi_threshold_analysis(distance_results):
    """
    Comprehensive multi-threshold analysis for all compound categories.
    
    Args:
        distance_results: DataFrame from Step 4 with Final_Distance_m and substances
        
    Returns:
        dict: Comprehensive analysis results for visualization
    """
    print("\nRunning multi-threshold analysis...")
    
    # Load fractile threshold data
    fractile_data = _load_fractile_thresholds_from_python()
    if not fractile_data:
        print("Warning: No fractile data available, using defaults")
        return {}
    
    # Analysis results storage
    analysis_results = {
        'threshold_effectiveness': {},  # Sites captured at each threshold per category
        'site_risk_levels': [],         # Individual site risk classifications  
        'category_statistics': {},      # Distance stats per category
        'threshold_comparison': {},     # Cross-threshold comparison data
        'waterfall_data': {},          # Data for waterfall charts
        'sensitivity_matrix': {}       # Data for sensitivity heatmaps
    }
    
    threshold_levels = ['fractile_60_m', 'fractile_75_m', 'fractile_90_m', 'maksimal_m']
    threshold_names = ['60%', '75%', '90%', 'Maximum']
    
    # Process each site and substance combination
    site_substance_data = []
    for _, row in distance_results.iterrows():
        substances_str = str(row.get('Lokalitetensstoffer', ''))
        if pd.isna(substances_str) or substances_str.strip() == '' or substances_str == 'nan':
            continue
            
        substances = [s.strip() for s in substances_str.split(';') if s.strip()]
        site_distance = float(row['Final_Distance_m'])
        
        for substance in substances:
            category, _ = categorize_contamination_substance(substance)
            
            if category not in fractile_data:
                category = 'OTHER'
                # Use default thresholds for OTHER category
                thresholds = {'fractile_60_m': 150, 'fractile_75_m': 250, 
                             'fractile_90_m': 400, 'maksimal_m': 500}
            else:
                thresholds = fractile_data[category]
            
            # Classify site risk level for this substance (CORRECTED - closer = higher risk!)
            risk_level = 'Outside'
            risk_color = 'gray'
            
            if site_distance <= thresholds['fractile_60_m']:
                risk_level = 'Very High Risk (≤60%)'  # Closest = highest risk
                risk_color = 'red'
            elif site_distance <= thresholds['fractile_75_m']:
                risk_level = 'High Risk (60-75%)'
                risk_color = 'orange'  
            elif site_distance <= thresholds['fractile_90_m']:
                risk_level = 'Medium Risk (75-90%)'
                risk_color = 'yellow'
            elif site_distance <= thresholds['maksimal_m']:
                risk_level = 'Low Risk (90-Max)'  # Furthest = lowest risk
                risk_color = 'green'
                
            site_substance_data.append({
                'Site_ID': row['Lokalitet_ID'],
                'Substance': substance,
                'Category': category,
                'Final_Distance_m': site_distance,
                'Risk_Level': risk_level,
                'Risk_Color': risk_color,
                **{f'Within_{level}': site_distance <= thresholds[level] for level in threshold_levels},
                **{f'Threshold_{level}': thresholds[level] for level in threshold_levels}
            })
    
    if not site_substance_data:
        print("Warning: No substance data found for analysis")
        return analysis_results
        
    # Convert to DataFrame for analysis
    analysis_df = pd.DataFrame(site_substance_data)
    
    # 1. THRESHOLD EFFECTIVENESS ANALYSIS
    for category in analysis_df['Category'].unique():
        cat_data = analysis_df[analysis_df['Category'] == category]
        effectiveness = {}
        
        for i, level in enumerate(threshold_levels):
            within_col = f'Within_{level}'
            sites_captured = cat_data[within_col].sum()
            total_sites = len(cat_data)
            percentage = (sites_captured / total_sites * 100) if total_sites > 0 else 0
            
            effectiveness[threshold_names[i]] = {
                'sites_captured': int(sites_captured),
                'total_sites': int(total_sites),
                'percentage': round(percentage, 1),
                'threshold_value': float(cat_data[f'Threshold_{level}'].iloc[0])
            }
            
        analysis_results['threshold_effectiveness'][category] = effectiveness
    
    # 2. CATEGORY DISTANCE STATISTICS  
    for category in analysis_df['Category'].unique():
        cat_distances = analysis_df[analysis_df['Category'] == category]['Final_Distance_m']
        
        analysis_results['category_statistics'][category] = {
            'count': len(cat_distances),
            'mean': float(cat_distances.mean()),
            'median': float(cat_distances.median()),
            'std': float(cat_distances.std()),
            'min': float(cat_distances.min()),
            'max': float(cat_distances.max()),
            'percentile_25': float(cat_distances.quantile(0.25)),
            'percentile_75': float(cat_distances.quantile(0.75))
        }
    
    # 3. WATERFALL DATA (cumulative capture)
    for category in analysis_df['Category'].unique():
        cat_data = analysis_df[analysis_df['Category'] == category]
        waterfall = []
        
        for i, level in enumerate(threshold_levels):
            within_col = f'Within_{level}'
            cumulative_sites = cat_data[within_col].sum()
            
            if i == 0:
                new_sites = cumulative_sites
            else:
                prev_level = threshold_levels[i-1]
                prev_within = f'Within_{prev_level}'
                prev_cumulative = cat_data[prev_within].sum()
                new_sites = cumulative_sites - prev_cumulative
                
            waterfall.append({
                'threshold': threshold_names[i],
                'cumulative_sites': int(cumulative_sites),
                'new_sites': int(new_sites),
                'threshold_value': float(cat_data[f'Threshold_{level}'].iloc[0])
            })
            
        analysis_results['waterfall_data'][category] = waterfall
    
    # 4. SENSITIVITY MATRIX (for heatmap)
    sensitivity_matrix = []
    for category in analysis_df['Category'].unique():
        cat_data = analysis_df[analysis_df['Category'] == category]
        row_data = {'Category': category}
        
        for i, level in enumerate(threshold_levels):
            within_col = f'Within_{level}'
            sites_captured = cat_data[within_col].sum()
            row_data[threshold_names[i]] = int(sites_captured)
            
        sensitivity_matrix.append(row_data)
        
    analysis_results['sensitivity_matrix'] = sensitivity_matrix
    
    # 5. INDIVIDUAL SITE RISK LEVELS
    analysis_results['site_risk_levels'] = analysis_df.to_dict('records')
    
    # Save detailed results to files
    analysis_df.to_csv(get_output_path('step5_multi_threshold_analysis'), index=False)
    
    # Save summary statistics
    summary_data = []
    for category, stats in analysis_results['category_statistics'].items():
        summary_data.append({'Category': category, **stats})
    pd.DataFrame(summary_data).to_csv(get_output_path('step5_category_distance_statistics'), index=False)
    
    # Save threshold effectiveness
    effectiveness_data = []
    for category, thresholds in analysis_results['threshold_effectiveness'].items():
        for threshold_name, data in thresholds.items():
            effectiveness_data.append({
                'Category': category,
                'Threshold': threshold_name, 
                **data
            })
    pd.DataFrame(effectiveness_data).to_csv(get_output_path('step5_threshold_effectiveness'), index=False)
    
    print(f"✓ Multi-threshold analysis completed for {len(analysis_df['Category'].unique())} categories")
    print(f"✓ Analyzed {len(analysis_df)} substance-site combinations")
    
    return analysis_results

def run_comprehensive_step5():
    """
    Execute comprehensive Step 5 analysis including multi-threshold analysis and visualizations.
    """
    print(f"\nStep 5: COMPREHENSIVE RISK ASSESSMENT & MULTI-THRESHOLD ANALYSIS")
    print("=" * 80)
    
    try:
        # Run standard assessments
        general_results, compound_results = run_step5()
        
        # Load Step 4 data for multi-threshold analysis
        step4_file = get_output_path('step4_final_distances_for_risk_assessment')
        multi_threshold_results = {}
        if os.path.exists(step4_file):
            distance_results = pd.read_csv(step4_file)
            
            # Run comprehensive multi-threshold analysis
            multi_threshold_results = run_multi_threshold_analysis(distance_results)
            
        # Run category analysis for visualizations
        run_step5_category_analysis()
        
        # Run visualizations if available
        print("\nCreating Step 5 visualizations...")
        try:
            from step5_visualizations import create_step5_visualizations, create_enhanced_compound_specific_visualizations
            create_step5_visualizations()
            create_enhanced_compound_specific_visualizations()
            print("✓ Step 5 visualizations completed")
        except ImportError:
            print("Warning: step5_visualizations module not found, skipping visualizations")
        except Exception as e:
            print(f"Warning: Could not create visualizations - {e}")
        
        print(f"\n✓ COMPREHENSIVE STEP 5 ANALYSIS COMPLETED")
        
        return {
            'general_results': general_results,
            'compound_results': compound_results,
            'multi_threshold_results': multi_threshold_results,
            'success': True,
            'error_message': None
        }
        
    except Exception as e:
        print(f"Step 5 failed: {e}")
        return {
            'general_results': (None, None),
            'compound_results': (None, None),
            'multi_threshold_results': {},
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