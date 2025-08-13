"""
Step 5: Two-Part Risk Assessment and Analysis of High-Risk V1/V2 Sites

Part A: General risk assessment using universal distance threshold
Part B: Compound-specific risk assessment using tailored distance thresholds per compound type

This step provides both broad screening and detailed compound-specific risk classification.
"""

import pandas as pd
import geopandas as gpd
import numpy as np
import os
from config import (get_output_path, ensure_results_directory, GRUNDVAND_PATH, 
                   WORKFLOW_SETTINGS, COMPOUND_RISK_DISTANCES)

def run_step5():
    """
    Execute Step 5: Two-part risk assessment of V1/V2 localities.
    
    Part A: General assessment with universal threshold
    Part B: Compound-specific assessment with tailored thresholds
    
    Returns:
        tuple: (general_results, compound_results)
            general_results: (high_risk_sites_df, analysis_summary)
            compound_results: (compound_high_risk_sites_df, compound_analysis_summary)
    """
    print(f"\nStep 5: Two-Part Risk Assessment of High-Risk V1/V2 Sites")
    print("=" * 60)
    
    # Ensure output directory exists
    ensure_results_directory()
    
    # Load Step 4 results once for both analyses
    step4_file = get_output_path('step4_final_distances_for_risk_assessment')
    
    if not os.path.exists(step4_file):
        print(f"ERROR: Step 4 results not found at {step4_file}")
        print("Please run Step 4 first to generate distance data.")
        return (None, None), (None, None)
    
    try:
        distance_results = pd.read_csv(step4_file)
        print(f"Loaded Step 4 results: {len(distance_results)} unique localities")
    except Exception as e:
        print(f"Error loading Step 4 results: {e}")
        return (None, None), (None, None)
    
    # Part A: General Risk Assessment
    print(f"\nPART A: GENERAL RISK ASSESSMENT")
    print("-" * 40)
    general_results = run_general_risk_assessment(distance_results)
    
    # Part B: Compound-Specific Risk Assessment  
    print(f"\nPART B: COMPOUND-SPECIFIC RISK ASSESSMENT")
    print("-" * 40)
    compound_results = run_compound_specific_assessment(distance_results)
    
    # Generate comparison summary
    _generate_comparison_summary(general_results, compound_results)
    
    return general_results, compound_results

def run_general_risk_assessment(distance_results):
    """
    Part A: General risk assessment using universal distance threshold.
    
    Args:
        distance_results (DataFrame): Step 4 distance results
        
    Returns:
        tuple: (high_risk_sites_df, analysis_summary)
    """
    risk_threshold_m = WORKFLOW_SETTINGS['risk_threshold_m']
    print(f"Using universal threshold: {risk_threshold_m}m")
    
    # Apply configurable distance filter
    high_risk_sites = distance_results[
        distance_results['Final_Distance_m'] <= risk_threshold_m
    ].copy()
    
    print(f"\nGeneral risk filtering results:")
    print(f"Total localities with distances: {len(distance_results)}")
    print(f"High-risk localities (≤{risk_threshold_m}m): {len(high_risk_sites)}")
    print(f"Percentage high-risk: {len(high_risk_sites)/len(distance_results)*100:.1f}%")
    
    if high_risk_sites.empty:
        print(f"No high-risk sites found within {risk_threshold_m}m threshold.")
        return high_risk_sites, {}
    
    # Perform contamination analysis
    analysis_summary = _analyze_contamination_characteristics(high_risk_sites, risk_threshold_m)
    
    # Save high-risk sites and create filtered GVFK shapefile
    high_risk_gvfk_names = _save_step5_results(high_risk_sites, analysis_summary, risk_threshold_m)
    
    return high_risk_sites, analysis_summary

def run_compound_specific_assessment(distance_results):
    """
    Part B: Compound-specific risk assessment using tailored distance thresholds.
    
    Args:
        distance_results (DataFrame): Step 4 distance results
        
    Returns:
        tuple: (compound_high_risk_sites_df, compound_analysis_summary)
    """
    print(f"Using compound-specific distance thresholds")
    print(f"Available compound distances: {len(COMPOUND_RISK_DISTANCES)} compounds configured")
    
    # Apply compound-specific distance assessment
    compound_high_risk_sites = _apply_compound_specific_filtering(distance_results)
    
    if compound_high_risk_sites.empty:
        print("No high-risk sites found using compound-specific thresholds.")
        return compound_high_risk_sites, {}
    
    print(f"\nCompound-specific risk filtering results:")
    print(f"Total localities with distances: {len(distance_results)}")
    print(f"High-risk localities (compound-specific): {len(compound_high_risk_sites)}")
    print(f"Percentage high-risk: {len(compound_high_risk_sites)/len(distance_results)*100:.1f}%")
    
    # Perform compound-specific contamination analysis
    compound_analysis_summary = _analyze_compound_specific_characteristics(compound_high_risk_sites)
    
    # Save compound-specific results
    _save_compound_specific_results(compound_high_risk_sites, compound_analysis_summary)
    
    return compound_high_risk_sites, compound_analysis_summary

def _apply_compound_specific_filtering(distance_results):
    """
    Apply compound-specific distance thresholds to identify high-risk sites.
    
    Args:
        distance_results (DataFrame): Step 4 distance results
        
    Returns:
        DataFrame: Sites that exceed compound-specific risk thresholds
    """
    print("Applying compound-specific distance filtering...")
    
    # Initialize results list
    high_risk_records = []
    compound_assignments = []
    
    for idx, row in distance_results.iterrows():
        site_distance = row['Final_Distance_m']
        contamination_substances = row.get('Lokalitetensstoffer', '')
        
        if pd.isna(contamination_substances) or contamination_substances == '':
            continue
            
        # Parse compounds (handle semicolon/comma separation)
        compounds = []
        for sep in [';', ',']:
            if sep in str(contamination_substances):
                compounds = [c.strip() for c in str(contamination_substances).split(sep) if c.strip()]
                break
        else:
            compounds = [str(contamination_substances).strip()]
        
        # Check each compound against its specific threshold
        site_is_high_risk = False
        applied_thresholds = []
        
        for compound in compounds:
            # Get compound-specific threshold (case-insensitive matching)
            compound_threshold = None
            
            # Try exact match first
            if compound in COMPOUND_RISK_DISTANCES:
                compound_threshold = COMPOUND_RISK_DISTANCES[compound]
            else:
                # Try case-insensitive partial matching
                for config_compound, threshold in COMPOUND_RISK_DISTANCES.items():
                    if config_compound.lower() in compound.lower() or compound.lower() in config_compound.lower():
                        compound_threshold = threshold
                        break
                
                # Use default if no match found
                if compound_threshold is None:
                    compound_threshold = COMPOUND_RISK_DISTANCES['default']
            
            applied_thresholds.append(f"{compound}:{compound_threshold}m")
            
            # Check if site exceeds this compound's threshold
            if site_distance <= compound_threshold:
                site_is_high_risk = True
        
        # If site is high-risk for any compound, include it
        if site_is_high_risk:
            # Add compound-specific information to the record
            row_copy = row.copy()
            row_copy['Applied_Compound_Thresholds'] = '; '.join(applied_thresholds)
            row_copy['Compound_Specific_Risk'] = True
            
            high_risk_records.append(row_copy)
            compound_assignments.append({
                'Lokalitet_': row['Lokalitet_'],
                'Compounds': '; '.join(compounds),
                'Applied_Thresholds': '; '.join(applied_thresholds),
                'Distance_m': site_distance
            })
    
    if high_risk_records:
        compound_high_risk_sites = pd.DataFrame(high_risk_records)
        
        # Save compound assignment details
        compound_assignments_df = pd.DataFrame(compound_assignments)
        assignment_path = get_output_path('step5_compound_distance_mapping')
        compound_assignments_df.to_csv(assignment_path, index=False)
        print(f"Saved compound-distance mapping to: {assignment_path}")
        
        return compound_high_risk_sites
    else:
        return pd.DataFrame()

def _generate_comparison_summary(general_results, compound_results):
    """
    Generate a comparison summary between general and compound-specific assessments.
    
    Args:
        general_results (tuple): (high_risk_sites_df, analysis_summary)
        compound_results (tuple): (compound_high_risk_sites_df, compound_analysis_summary)
    """
    print(f"\nCOMPARISON SUMMARY")
    print("=" * 40)
    
    general_sites, general_analysis = general_results
    compound_sites, compound_analysis = compound_results
    
    if general_sites is not None and compound_sites is not None:
        print(f"General assessment ({WORKFLOW_SETTINGS['risk_threshold_m']}m): {len(general_sites)} high-risk sites")
        print(f"Compound-specific assessment: {len(compound_sites)} high-risk sites")
        
        # Sites only in general assessment
        if not general_sites.empty and not compound_sites.empty:
            general_only = set(general_sites['Lokalitet_']) - set(compound_sites['Lokalitet_'])
            compound_only = set(compound_sites['Lokalitet_']) - set(general_sites['Lokalitet_'])
            both = set(general_sites['Lokalitet_']) & set(compound_sites['Lokalitet_'])
            
            print(f"Sites only in general assessment: {len(general_only)}")
            print(f"Sites only in compound-specific assessment: {len(compound_only)}")
            print(f"Sites in both assessments: {len(both)}")
        
        elif not general_sites.empty:
            print("Only general assessment produced results")
        elif not compound_sites.empty:
            print("Only compound-specific assessment produced results")
    else:
        print("One or both assessments failed to produce results")

def _analyze_compound_specific_characteristics(compound_high_risk_sites):
    """
    Analyze characteristics of compound-specific high-risk sites.
    
    Args:
        compound_high_risk_sites (DataFrame): Sites identified through compound-specific filtering
        
    Returns:
        dict: Analysis summary with compound-specific statistics
    """
    print(f"\nAnalyzing compound-specific characteristics for {len(compound_high_risk_sites)} high-risk sites...")
    
    analysis = {
        'assessment_type': 'compound_specific',
        'total_high_risk_sites': len(compound_high_risk_sites),
        'distance_stats': {},
        'compound_threshold_stats': {},
        'site_type_distribution': {},
        'contamination_analysis': {}
    }
    
    # Distance statistics
    if 'Final_Distance_m' in compound_high_risk_sites.columns:
        distances = compound_high_risk_sites['Final_Distance_m']
        analysis['distance_stats'] = {
            'min_distance_m': distances.min(),
            'max_distance_m': distances.max(),
            'mean_distance_m': distances.mean(),
            'median_distance_m': distances.median(),
            'std_distance_m': distances.std()
        }
        
        print(f"Distance statistics for compound-specific high-risk sites:")
        print(f"  Range: {distances.min():.1f}m - {distances.max():.1f}m")
        print(f"  Mean: {distances.mean():.1f}m, Median: {distances.median():.1f}m")
    
    # Compound threshold analysis
    if 'Applied_Compound_Thresholds' in compound_high_risk_sites.columns:
        # Parse applied thresholds to get statistics
        all_compound_thresholds = []
        for threshold_str in compound_high_risk_sites['Applied_Compound_Thresholds'].dropna():
            if pd.notna(threshold_str) and str(threshold_str).strip():
                thresholds = [t.strip() for t in str(threshold_str).split(';') if t.strip()]
                all_compound_thresholds.extend(thresholds)
        
        if all_compound_thresholds:
            # Extract just the compounds and distances
            compounds_used = []
            distances_used = []
            for thresh in all_compound_thresholds:
                if ':' in thresh:
                    compound, dist_str = thresh.split(':', 1)
                    compounds_used.append(compound.strip())
                    try:
                        dist_val = float(dist_str.replace('m', '').strip())
                        distances_used.append(dist_val)
                    except:
                        pass
            
            analysis['compound_threshold_stats'] = {
                'total_compound_applications': len(all_compound_thresholds),
                'unique_compounds_used': len(set(compounds_used)),
                'most_common_compounds': pd.Series(compounds_used).value_counts().head(10).to_dict(),
                'threshold_distances_used': {
                    'min_threshold': min(distances_used) if distances_used else 0,
                    'max_threshold': max(distances_used) if distances_used else 0,
                    'mean_threshold': np.mean(distances_used) if distances_used else 0
                }
            }
            
            print(f"\nCompound threshold statistics:")
            print(f"  Total compound-threshold applications: {len(all_compound_thresholds)}")
            print(f"  Unique compounds used: {len(set(compounds_used))}")
            print(f"  Threshold range: {min(distances_used) if distances_used else 0:.0f}m - {max(distances_used) if distances_used else 0:.0f}m")
            
            print(f"  Top 5 compounds by usage:")
            for compound, count in pd.Series(compounds_used).value_counts().head(5).items():
                print(f"    {compound}: {count} sites")
    
    # Site type distribution (similar to general analysis)
    if 'Site_Type' in compound_high_risk_sites.columns:
        site_type_counts = compound_high_risk_sites['Site_Type'].value_counts()
        analysis['site_type_distribution'] = site_type_counts.to_dict()
        
        print(f"\nSite type distribution:")
        for site_type, count in site_type_counts.items():
            percentage = count / len(compound_high_risk_sites) * 100
            print(f"  {site_type}: {count} ({percentage:.1f}%)")
    
    # Contamination analysis (reuse existing logic but note it's compound-specific)
    contamination_cols = ['Lokalitetensbranche', 'Lokalitetensaktivitet', 'Lokalitetensstoffer']
    
    for col in contamination_cols:
        if col in compound_high_risk_sites.columns:
            analysis['contamination_analysis'][col] = _analyze_contamination_column(
                compound_high_risk_sites, col, len(compound_high_risk_sites)
            )
    
    return analysis

def _save_compound_specific_results(compound_high_risk_sites, compound_analysis_summary):
    """
    Save compound-specific risk assessment results.
    
    Args:
        compound_high_risk_sites (DataFrame): Compound-specific high-risk sites
        compound_analysis_summary (dict): Compound-specific analysis results
    """
    print(f"\nSaving compound-specific results...")
    
    # Save compound-specific high-risk sites
    compound_sites_path = get_output_path('step5_compound_specific_sites')
    compound_high_risk_sites.to_csv(compound_sites_path, index=False)
    print(f"- Compound-specific high-risk sites: {compound_sites_path}")
    
    # Save compound-specific analysis summary
    compound_summary_data = []
    
    # Distance statistics
    if 'distance_stats' in compound_analysis_summary:
        for stat, value in compound_analysis_summary['distance_stats'].items():
            compound_summary_data.append({
                'Category': 'Distance Statistics',
                'Metric': stat,
                'Value': f"{value:.2f}" if isinstance(value, float) else str(value),
                'Unit': 'm' if 'distance' in stat else ''
            })
    
    # Compound threshold statistics
    if 'compound_threshold_stats' in compound_analysis_summary:
        thresh_stats = compound_analysis_summary['compound_threshold_stats']
        
        compound_summary_data.append({
            'Category': 'Compound Threshold Usage',
            'Metric': 'total_applications',
            'Value': str(thresh_stats.get('total_compound_applications', 0)),
            'Unit': 'compound-threshold pairs'
        })
        
        compound_summary_data.append({
            'Category': 'Compound Threshold Usage',
            'Metric': 'unique_compounds',
            'Value': str(thresh_stats.get('unique_compounds_used', 0)),
            'Unit': 'unique compounds'
        })
        
        if 'threshold_distances_used' in thresh_stats:
            thresh_distances = thresh_stats['threshold_distances_used']
            for metric, value in thresh_distances.items():
                compound_summary_data.append({
                    'Category': 'Threshold Distance Statistics',
                    'Metric': metric,
                    'Value': f"{value:.1f}" if isinstance(value, float) else str(value),
                    'Unit': 'm'
                })
    
    # Site type distribution
    if 'site_type_distribution' in compound_analysis_summary:
        for site_type, count in compound_analysis_summary['site_type_distribution'].items():
            percentage = count / compound_analysis_summary['total_high_risk_sites'] * 100
            compound_summary_data.append({
                'Category': 'Site Type Distribution',
                'Metric': site_type,
                'Value': f"{count} ({percentage:.1f}%)",
                'Unit': 'sites'
            })
    
    compound_summary_df = pd.DataFrame(compound_summary_data)
    compound_summary_path = get_output_path('step5_compound_analysis_summary')
    compound_summary_df.to_csv(compound_summary_path, index=False)
    print(f"- Compound-specific analysis summary: {compound_summary_path}")
    
    # Save detailed compound breakdown
    compound_breakdown_data = []
    
    # Compound usage breakdown
    if 'compound_threshold_stats' in compound_analysis_summary:
        thresh_stats = compound_analysis_summary['compound_threshold_stats']
        if 'most_common_compounds' in thresh_stats:
            for compound, count in thresh_stats['most_common_compounds'].items():
                # Get the threshold used for this compound
                compound_threshold = COMPOUND_RISK_DISTANCES.get(compound, COMPOUND_RISK_DISTANCES['default'])
                
                compound_breakdown_data.append({
                    'Compound': compound,
                    'Sites_Count': count,
                    'Threshold_Used_m': compound_threshold,
                    'Percentage_of_Compound_Sites': f"{count/compound_analysis_summary['total_high_risk_sites']*100:.1f}%"
                })
    
    if compound_breakdown_data:
        compound_breakdown_df = pd.DataFrame(compound_breakdown_data)
        compound_breakdown_path = get_output_path('step5_compound_breakdown')
        compound_breakdown_df.to_csv(compound_breakdown_path, index=False)
        print(f"- Compound-specific breakdown: {compound_breakdown_path}")
    
    # Create compound-specific GVFK shapefile
    _create_compound_specific_gvfk_shapefile(compound_high_risk_sites)
    
    print(f"\nCompound-specific analysis completed successfully!")
    print(f"Found {len(compound_high_risk_sites)} compound-specific high-risk sites")

def _create_compound_specific_gvfk_shapefile(compound_high_risk_sites):
    """
    Create a filtered GVFK shapefile for compound-specific high-risk sites.
    
    Args:
        compound_high_risk_sites (DataFrame): Compound-specific high-risk sites
    """
    print(f"\nCreating compound-specific GVFK shapefile...")
    
    # Get unique GVFK names from compound-specific sites
    compound_gvfk_names = set()
    
    if 'All_Affected_GVFKs' in compound_high_risk_sites.columns:
        for gvfk_list in compound_high_risk_sites['All_Affected_GVFKs'].dropna():
            if pd.isna(gvfk_list) or gvfk_list == '':
                continue
            gvfks = [gvfk.strip() for gvfk in str(gvfk_list).split(';') if gvfk.strip()]
            compound_gvfk_names.update(gvfks)
    elif 'Closest_GVFK' in compound_high_risk_sites.columns:
        compound_gvfk_names = set(compound_high_risk_sites['Closest_GVFK'].dropna().unique())
    else:
        print("ERROR: No GVFK name column found in compound-specific high-risk sites data")
        return
    
    print(f"Found {len(compound_gvfk_names)} unique GVFKs containing compound-specific high-risk sites")
    
    # Load and filter GVFK shapefile
    try:
        all_gvfk = gpd.read_file(GRUNDVAND_PATH)
        compound_gvfk_polygons = all_gvfk[all_gvfk['Navn'].isin(compound_gvfk_names)].copy()
        
        # Save compound-specific GVFK shapefile
        compound_gvfk_path = get_output_path('step5_compound_gvfk_high_risk')
        compound_gvfk_polygons.to_file(compound_gvfk_path)
        print(f"Saved compound-specific GVFK shapefile to: {compound_gvfk_path}")
        
    except Exception as e:
        print(f"ERROR: Could not create compound-specific GVFK shapefile: {e}")

def _analyze_contamination_column(sites_df, col, total_sites):
    """
    Helper function to analyze a contamination column with proper separation handling.
    
    Args:
        sites_df (DataFrame): Sites dataframe
        col (str): Column name to analyze
        total_sites (int): Total number of sites for percentage calculations
        
    Returns:
        dict: Analysis results for the column
    """
    non_null_count = sites_df[col].notna().sum()
    
    if non_null_count == 0:
        return {'total_sites_with_data': 0}
    
    # Handle semicolon-separated values
    if col in ['Lokalitetensbranche', 'Lokalitetensaktivitet']:
        all_categories = []
        sites_with_category = {}
        
        for idx, value in sites_df[col].dropna().items():
            if pd.notna(value) and str(value).strip():
                categories = [cat.strip() for cat in str(value).split(';') if cat.strip()]
                all_categories.extend(categories)
                
                for cat in categories:
                    if cat not in sites_with_category:
                        sites_with_category[cat] = set()
                    sites_with_category[cat].add(idx)
        
        category_counts = pd.Series(all_categories).value_counts()
        category_site_counts = {cat: len(sites) for cat, sites in sites_with_category.items()}
        
        return {
            'total_sites_with_data': non_null_count,
            'total_category_instances': len(all_categories),
            'unique_categories': len(category_counts),
            'top_categories_by_occurrence': category_counts.head(10).to_dict(),
            'top_categories_by_sites': dict(sorted(category_site_counts.items(), 
                                                 key=lambda x: x[1], reverse=True)[:10])
        }
    
    else:
        # Handle separated substance values
        if ';' in str(sites_df[col].dropna().iloc[0]) or ',' in str(sites_df[col].dropna().iloc[0]):
            all_substances = []
            sites_with_substance = {}
            
            for idx, value in sites_df[col].dropna().items():
                if pd.notna(value) and str(value).strip():
                    substances = [s.strip() for s in str(value).replace(';', ',').split(',') if s.strip()]
                    all_substances.extend(substances)
                    
                    for substance in substances:
                        if substance not in sites_with_substance:
                            sites_with_substance[substance] = set()
                        sites_with_substance[substance].add(idx)
            
            substance_counts = pd.Series(all_substances).value_counts()
            substance_site_counts = {sub: len(sites) for sub, sites in sites_with_substance.items()}
            
            return {
                'total_sites_with_data': non_null_count,
                'total_substance_instances': len(all_substances),
                'unique_substances': len(substance_counts),
                'top_substances_by_occurrence': substance_counts.head(10).to_dict(),
                'top_substances_by_sites': dict(sorted(substance_site_counts.items(), 
                                                     key=lambda x: x[1], reverse=True)[:10])
            }
        else:
            # Single values
            unique_values = sites_df[col].nunique()
            top_categories = sites_df[col].value_counts().head(10)
            
            return {
                'total_with_data': non_null_count,
                'unique_categories': unique_values,
                'top_categories': top_categories.to_dict()
            }

def _analyze_contamination_characteristics(high_risk_sites, threshold_m):
    """
    Analyze contamination characteristics of high-risk sites.
    
    Args:
        high_risk_sites (DataFrame): Filtered sites within distance threshold
        threshold_m (int): Distance threshold used for filtering
    
    Returns:
        dict: Analysis summary with contamination statistics
    """
    print(f"\nAnalyzing contamination characteristics for {len(high_risk_sites)} high-risk sites...")
    
    analysis = {
        'threshold_m': threshold_m,
        'total_high_risk_sites': len(high_risk_sites),
        'distance_stats': {},
        'site_type_distribution': {},
        'contamination_analysis': {}
    }
    
    # Distance statistics for high-risk sites
    if 'Final_Distance_m' in high_risk_sites.columns:
        distances = high_risk_sites['Final_Distance_m']
        analysis['distance_stats'] = {
            'min_distance_m': distances.min(),
            'max_distance_m': distances.max(),
            'mean_distance_m': distances.mean(),
            'median_distance_m': distances.median(),
            'std_distance_m': distances.std()
        }
        
        print(f"Distance statistics for high-risk sites:")
        print(f"  Range: {distances.min():.1f}m - {distances.max():.1f}m")
        print(f"  Mean: {distances.mean():.1f}m, Median: {distances.median():.1f}m")
    
    # Site type distribution
    if 'Site_Type' in high_risk_sites.columns:
        site_type_counts = high_risk_sites['Site_Type'].value_counts()
        analysis['site_type_distribution'] = site_type_counts.to_dict()
        
        print(f"\nSite type distribution:")
        for site_type, count in site_type_counts.items():
            percentage = count / len(high_risk_sites) * 100
            print(f"  {site_type}: {count} ({percentage:.1f}%)")
    
    # Contamination analysis using helper function
    contamination_cols = ['Lokalitetensbranche', 'Lokalitetensaktivitet', 'Lokalitetensstoffer']
    
    for col in contamination_cols:
        if col in high_risk_sites.columns:
            analysis['contamination_analysis'][col] = _analyze_contamination_column(
                high_risk_sites, col, len(high_risk_sites)
            )
            
            # Print summary for this column
            col_analysis = analysis['contamination_analysis'][col]
            if 'total_sites_with_data' in col_analysis and col_analysis['total_sites_with_data'] > 0:
                non_null_count = col_analysis['total_sites_with_data']
                print(f"\n{col} analysis:")
                print(f"  Sites with data: {non_null_count}/{len(high_risk_sites)} ({non_null_count/len(high_risk_sites)*100:.1f}%)")
                
                # Handle different analysis types
                if 'total_category_instances' in col_analysis:
                    print(f"  Total category instances: {col_analysis['total_category_instances']}")
                    print(f"  Unique categories: {col_analysis['unique_categories']}")
                    print(f"  Average categories per site: {col_analysis['total_category_instances']/non_null_count:.1f}")
                    
                    if 'top_categories_by_occurrence' in col_analysis:
                        print(f"  Top 5 categories by occurrence:")
                        for category, count in list(col_analysis['top_categories_by_occurrence'].items())[:5]:
                            sites_count = col_analysis.get('top_categories_by_sites', {}).get(category, count)
                            print(f"    {category}: {count} instances ({sites_count} sites)")
                
                elif 'total_substance_instances' in col_analysis:
                    print(f"  Total substance instances: {col_analysis['total_substance_instances']}")
                    print(f"  Unique substances: {col_analysis['unique_substances']}")
                    print(f"  Average substances per site: {col_analysis['total_substance_instances']/non_null_count:.1f}")
                    
                    if 'top_substances_by_occurrence' in col_analysis:
                        print(f"  Top 5 substances by occurrence:")
                        for substance, count in list(col_analysis['top_substances_by_occurrence'].items())[:5]:
                            sites_count = col_analysis.get('top_substances_by_sites', {}).get(substance, count)
                            print(f"    {substance}: {count} instances ({sites_count} sites)")
                
                elif 'top_categories' in col_analysis:
                    print(f"  Unique categories: {col_analysis['unique_categories']}")
                    print(f"  Top 5 categories:")
                    for category, count in list(col_analysis['top_categories'].items())[:5]:
                        percentage = count / non_null_count * 100
                        print(f"    {category}: {count} ({percentage:.1f}%)")
    
    # Multi-GVFK analysis
    if 'Total_GVFKs_Affected' in high_risk_sites.columns:
        multi_gvfk_sites = high_risk_sites[high_risk_sites['Total_GVFKs_Affected'] > 1]
        analysis['multi_gvfk_sites'] = len(multi_gvfk_sites)
        
        print(f"\nMulti-GVFK analysis:")
        print(f"  Sites affecting multiple GVFKs: {len(multi_gvfk_sites)}/{len(high_risk_sites)} ({len(multi_gvfk_sites)/len(high_risk_sites)*100:.1f}%)")
        
        if len(multi_gvfk_sites) > 0:
            avg_gvfks = multi_gvfk_sites['Total_GVFKs_Affected'].mean()
            max_gvfks = multi_gvfk_sites['Total_GVFKs_Affected'].max()
            print(f"  Average GVFKs per multi-GVFK site: {avg_gvfks:.1f}")
            print(f"  Maximum GVFKs affected by single site: {max_gvfks}")
    
    return analysis

def _save_step5_results(high_risk_sites, analysis_summary, threshold_m):
    """
    Save Step 5 results and analysis summaries.
    
    Args:
        high_risk_sites (DataFrame): High-risk sites data
        analysis_summary (dict): Analysis results
        threshold_m (int): Distance threshold used
    """
    print(f"\nSaving Step 5 results...")
    
    # Import OUTPUT_FILES to check if step 5 files are configured
    from config import OUTPUT_FILES
    
    # Check if step 5 files are configured, if not add them
    step5_files = {
        'step5_high_risk_sites': f'step5_high_risk_sites_{threshold_m}m.csv',
        'step5_analysis_summary': f'step5_analysis_summary_{threshold_m}m.csv',
        'step5_contamination_breakdown': f'step5_contamination_breakdown_{threshold_m}m.csv'
    }
    
    # Add any missing step 5 files to OUTPUT_FILES
    for key, value in step5_files.items():
        if key not in OUTPUT_FILES:
            OUTPUT_FILES[key] = value
    
    # Save main high-risk sites file
    try:
        high_risk_path = get_output_path('step5_high_risk_sites')
    except:
        high_risk_path = os.path.join("Resultater", f"step5_high_risk_sites_{threshold_m}m.csv")
    
    high_risk_sites.to_csv(high_risk_path, index=False)
    print(f"- High-risk sites: {high_risk_path}")
    
    # Save analysis summary
    summary_data = []
    
    # Distance statistics
    if 'distance_stats' in analysis_summary:
        for stat, value in analysis_summary['distance_stats'].items():
            summary_data.append({
                'Category': 'Distance Statistics',
                'Metric': stat,
                'Value': f"{value:.2f}" if isinstance(value, float) else str(value),
                'Unit': 'm' if 'distance' in stat else ''
            })
    
    # Site type distribution
    if 'site_type_distribution' in analysis_summary:
        for site_type, count in analysis_summary['site_type_distribution'].items():
            percentage = count / analysis_summary['total_high_risk_sites'] * 100
            summary_data.append({
                'Category': 'Site Type Distribution',
                'Metric': site_type,
                'Value': f"{count} ({percentage:.1f}%)",
                'Unit': 'sites'
            })
    
    # Contamination data availability
    for col, data in analysis_summary.get('contamination_analysis', {}).items():
        # Handle both new and legacy data formats
        if 'total_sites_with_data' in data:
            # New format
            sites_with_data = data['total_sites_with_data']
            unique_categories = data.get('unique_categories', data.get('unique_substances', 0))
            total_instances = data.get('total_category_instances', data.get('total_substance_instances', 0))
            
            percentage = sites_with_data / analysis_summary['total_high_risk_sites'] * 100
            summary_data.append({
                'Category': 'Data Availability',
                'Metric': f"{col}_availability",
                'Value': f"{sites_with_data} ({percentage:.1f}%)",
                'Unit': 'sites with data'
            })
            
            summary_data.append({
                'Category': 'Data Diversity',
                'Metric': f"{col}_unique_categories",
                'Value': str(unique_categories),
                'Unit': 'unique categories'
            })
            
            if total_instances > sites_with_data:
                avg_per_site = total_instances / sites_with_data
                summary_data.append({
                    'Category': 'Data Complexity',
                    'Metric': f"{col}_avg_per_site",
                    'Value': f"{avg_per_site:.1f}",
                    'Unit': 'categories per site'
                })
        
        elif 'total_with_data' in data:
            # Legacy format
            percentage = data['total_with_data'] / analysis_summary['total_high_risk_sites'] * 100
            summary_data.append({
                'Category': 'Data Availability',
                'Metric': f"{col}_availability",
                'Value': f"{data['total_with_data']} ({percentage:.1f}%)",
                'Unit': 'sites with data'
            })
            
            summary_data.append({
                'Category': 'Data Diversity',
                'Metric': f"{col}_unique_categories",
                'Value': str(data['unique_categories']),
                'Unit': 'unique categories'
            })
    
    # Multi-GVFK information
    if 'multi_gvfk_sites' in analysis_summary:
        percentage = analysis_summary['multi_gvfk_sites'] / analysis_summary['total_high_risk_sites'] * 100
        summary_data.append({
            'Category': 'Multi-GVFK Analysis',
            'Metric': 'Sites affecting multiple GVFKs',
            'Value': f"{analysis_summary['multi_gvfk_sites']} ({percentage:.1f}%)",
            'Unit': 'sites'
        })
    
    summary_df = pd.DataFrame(summary_data)
    try:
        summary_path = get_output_path('step5_analysis_summary')
    except:
        summary_path = os.path.join("Resultater", f"step5_analysis_summary_{threshold_m}m.csv")
    
    summary_df.to_csv(summary_path, index=False)
    print(f"- Analysis summary: {summary_path}")
    
    # Save detailed contamination breakdown
    contamination_data = []
    
    for col, data in analysis_summary.get('contamination_analysis', {}).items():
        # Handle new data structure with separated values
        if 'top_categories_by_occurrence' in data:
            # New format with separated values
            total_instances = data['total_category_instances'] if 'total_category_instances' in data else data.get('total_substance_instances', 0)
            total_sites = data['total_sites_with_data']
            
            for category, occurrence_count in data['top_categories_by_occurrence'].items():
                sites_count = data.get('top_categories_by_sites', {}).get(category, 
                             data.get('top_substances_by_sites', {}).get(category, occurrence_count))
                
                contamination_data.append({
                    'Contamination_Type': col,
                    'Category': category,
                    'Occurrence_Count': occurrence_count,
                    'Sites_Count': sites_count,
                    'Percentage_of_Occurrences': f"{occurrence_count/total_instances*100:.1f}%",
                    'Percentage_of_Sites': f"{sites_count/total_sites*100:.1f}%",
                    'Percentage_of_All_High_Risk_Sites': f"{sites_count/analysis_summary['total_high_risk_sites']*100:.1f}%"
                })
        
        elif 'top_categories' in data:
            # Legacy format (single values)
            for category, count in data['top_categories'].items():
                percentage = count / data['total_with_data'] * 100
                contamination_data.append({
                    'Contamination_Type': col,
                    'Category': category,
                    'Occurrence_Count': count,
                    'Sites_Count': count,  # Same as occurrence for single values
                    'Percentage_of_Occurrences': f"{percentage:.1f}%",
                    'Percentage_of_Sites': f"{percentage:.1f}%", 
                    'Percentage_of_All_High_Risk_Sites': f"{count/analysis_summary['total_high_risk_sites']*100:.1f}%"
                })
    
    if contamination_data:
        contamination_df = pd.DataFrame(contamination_data)
        try:
            contamination_path = get_output_path('step5_contamination_breakdown')
        except:
            contamination_path = os.path.join("Resultater", f"step5_contamination_breakdown_{threshold_m}m.csv")
        
        contamination_df.to_csv(contamination_path, index=False)
        print(f"- Contamination breakdown: {contamination_path}")
    
    # Create filtered GVFK shapefile with only GVFKs containing high-risk sites
    high_risk_gvfk_names = _create_high_risk_gvfk_shapefile(high_risk_sites, threshold_m)
    
    print(f"\nStep 5 completed successfully!")
    print(f"Found {len(high_risk_sites)} high-risk sites within {threshold_m}m of rivers")
    print(f"These sites are located in {len(high_risk_gvfk_names)} high-risk GVFKs")
    
    return high_risk_gvfk_names

def _create_high_risk_gvfk_shapefile(high_risk_sites, threshold_m):
    """
    Create a filtered GVFK shapefile containing only GVFKs with high-risk sites.
    
    Args:
        high_risk_sites (DataFrame): High-risk sites data
        threshold_m (int): Distance threshold used for filtering
    
    Returns:
        set: Set of GVFK names that contain high-risk sites
    """
    print(f"\nCreating filtered GVFK shapefile for high-risk sites...")
    
    # Get unique GVFK names that contain high-risk sites
    # From Step 4, the GVFK information is in 'All_Affected_GVFKs' (semicolon-separated)
    if 'All_Affected_GVFKs' in high_risk_sites.columns:
        print("Extracting GVFK names from 'All_Affected_GVFKs' column...")
        # Extract all GVFK names from semicolon-separated values
        all_gvfks = set()
        for gvfk_list in high_risk_sites['All_Affected_GVFKs'].dropna():
            if pd.isna(gvfk_list) or gvfk_list == '':
                continue
            # Split by semicolon and clean up
            gvfks = [gvfk.strip() for gvfk in str(gvfk_list).split(';') if gvfk.strip()]
            all_gvfks.update(gvfks)
        high_risk_gvfk_names = all_gvfks
    elif 'Closest_GVFK' in high_risk_sites.columns:
        print("Using 'Closest_GVFK' column for GVFK names...")
        high_risk_gvfk_names = set(high_risk_sites['Closest_GVFK'].dropna().unique())
    else:
        print("ERROR: No GVFK name column found in high-risk sites data")
        available_cols = list(high_risk_sites.columns)
        print(f"Available columns: {available_cols}")
        return set()
    print(f"Found {len(high_risk_gvfk_names)} unique GVFKs containing high-risk sites")
    
    # Load the complete GVFK shapefile
    try:
        all_gvfk = gpd.read_file(GRUNDVAND_PATH)
        print(f"Loaded complete GVFK shapefile: {len(all_gvfk)} total GVFKs")
    except Exception as e:
        print(f"ERROR: Could not load GVFK shapefile from {GRUNDVAND_PATH}: {e}")
        return high_risk_gvfk_names
    
    # Filter to only GVFKs containing high-risk sites
    high_risk_gvfk_polygons = all_gvfk[all_gvfk['Navn'].isin(high_risk_gvfk_names)].copy()
    
    print(f"Filtered GVFK polygons: {len(high_risk_gvfk_polygons)} GVFKs")
    
    # Calculate some statistics
    total_area_all = all_gvfk.geometry.area.sum() / 1_000_000  # Convert to km²
    total_area_high_risk = high_risk_gvfk_polygons.geometry.area.sum() / 1_000_000  # Convert to km²
    area_percentage = (total_area_high_risk / total_area_all) * 100
    
    print(f"Area statistics:")
    print(f"  Total GVFK area: {total_area_all:.1f} km²")
    print(f"  High-risk GVFK area: {total_area_high_risk:.1f} km²")
    print(f"  Percentage of total area: {area_percentage:.1f}%")
    
    # Save the filtered GVFK shapefile
    try:
        # Add to config if needed
        from config import OUTPUT_FILES
        step5_gvfk_key = 'step5_gvfk_high_risk'
        if step5_gvfk_key not in OUTPUT_FILES:
            OUTPUT_FILES[step5_gvfk_key] = f'step5_gvfk_high_risk_{threshold_m}m.shp'
        
        # Get output path
        try:
            output_path = get_output_path(step5_gvfk_key)
        except:
            output_path = os.path.join("Resultater", f"step5_gvfk_high_risk_{threshold_m}m.shp")
        
        high_risk_gvfk_polygons.to_file(output_path)
        print(f"Saved high-risk GVFK shapefile to: {output_path}")
        
    except Exception as e:
        print(f"ERROR: Could not save high-risk GVFK shapefile: {e}")
    
    return high_risk_gvfk_names

if __name__ == "__main__":
    # Allow running this step independently
    high_risk_sites, analysis = run_step5()
    if high_risk_sites is not None:
        print(f"Step 5 completed. Found {len(high_risk_sites)} high-risk sites.")
    else:
        print("Step 5 failed. Check that Step 4 has been completed first.") 