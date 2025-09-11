"""
Step 5: Risk Assessment of High-Risk V1/V2 Sites

Core functionality for two-fold risk assessment:
1. General Risk Assessment: Universal 500m threshold 
2. Compound-Specific Assessment: Literature-based thresholds per compound category
"""

import pandas as pd
import geopandas as gpd
import numpy as np
import os

from config import get_output_path, ensure_results_directory, GRUNDVAND_PATH, WORKFLOW_SETTINGS

# Global cache for categorization data
_CATEGORIZATION_CACHE = None
_DEFAULT_OTHER_DISTANCE = 500

def _extract_unique_gvfk_names(df):
    """
    Extract all unique GVFK names from a dataframe.
    Handles both 'All_Affected_GVFKs' (semicolon-separated) and 'Closest_GVFK' columns.
    
    Returns:
        set: Unique GVFK names
    """
    gvfk_names = set()
    
    # First try All_Affected_GVFKs (semicolon-separated list)
    if 'All_Affected_GVFKs' in df.columns:
        for gvfk_list in df['All_Affected_GVFKs'].dropna():
            if str(gvfk_list) != 'nan' and gvfk_list:
                gvfks = [g.strip() for g in str(gvfk_list).split(';') if g.strip()]
                gvfk_names.update(gvfks)
    
    # If no GVFKs found, fall back to Closest_GVFK
    if not gvfk_names and 'Closest_GVFK' in df.columns:
        for gvfk in df['Closest_GVFK'].dropna():
            if str(gvfk) != 'nan' and gvfk:
                gvfk_names.add(str(gvfk).strip())
    
    return gvfk_names

def _load_categorization_from_excel():
    """Load compound categorization data from Excel file."""
    global _CATEGORIZATION_CACHE
    
    if _CATEGORIZATION_CACHE is not None:
        return _CATEGORIZATION_CACHE
    
    # Path to Excel file
    excel_path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)), 
        "compound_categorization_review.xlsx"
    )
    
    # Load summary sheet for category distances
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
    
    # Load individual sheets for substance → category mapping
    substance_to_category = {}
    xl_file = pd.ExcelFile(excel_path)
    category_sheets = [sheet for sheet in xl_file.sheet_names 
                      if sheet not in ['Summary', 'Raw_Data']]
    
    for sheet_name in category_sheets:
        sheet_df = pd.read_excel(excel_path, sheet_name=sheet_name)
        
        if 'Substance' not in sheet_df.columns:
            raise ValueError(f"Sheet '{sheet_name}' missing required 'Substance' column")
        
        substances = sheet_df['Substance'].dropna()
        category = sheet_name.replace('_substances', '').upper()
        
        for substance in substances:
            if pd.notna(substance):
                substance_to_category[str(substance).lower().strip()] = category
    
    _CATEGORIZATION_CACHE = {
        'category_distances': category_distances,
        'substance_to_category': substance_to_category
    }
    
    print(f"Loaded categorization: {len(category_distances)} categories, {len(substance_to_category)} substances")
    return _CATEGORIZATION_CACHE

def categorize_contamination_substance(substance_text):
    """
    Categorize a contamination substance using Excel-based categorization.
    
    Args:
        substance_text (str): The contamination substance text
        
    Returns:
        tuple: (category_name, distance_m) 
    """
    if pd.isna(substance_text) or not isinstance(substance_text, str):
        return 'ANDRE', _DEFAULT_OTHER_DISTANCE
    
    # Load categorization data
    cat_data = _load_categorization_from_excel()
    substance_lower = substance_text.lower().strip()
    
    # Check for exact match first
    category = cat_data['substance_to_category'].get(substance_lower)
    
    if category:
        distance = cat_data['category_distances'].get(category, _DEFAULT_OTHER_DISTANCE)
        return category, distance
    
    # Check if substance contains any categorized substances
    for known_substance, known_category in cat_data['substance_to_category'].items():
        if known_substance in substance_lower or substance_lower in known_substance:
            distance = cat_data['category_distances'].get(known_category, _DEFAULT_OTHER_DISTANCE)
            return known_category, distance
    
    # Default to ANDRE category
    return 'ANDRE', _DEFAULT_OTHER_DISTANCE

def run_step5():
    """Execute Step 5 risk assessment."""
    print(f"\nStep 5: Risk Assessment of High-Risk V1/V2 Sites")
    print("=" * 60)
    
    ensure_results_directory()
    
    # Load Step 4 results
    step4_file = get_output_path('step4_final_distances_for_risk_assessment')
    if not os.path.exists(step4_file):
        raise FileNotFoundError("Step 4 results not found. Please run Step 4 first.")
    
    distance_results = pd.read_csv(step4_file)
    print(f"Loaded {len(distance_results)} localities from Step 4")
    
    # Separate sites with and without substance data
    sites_with_substances, sites_without_substances = _separate_sites_by_substance_data(distance_results)
    
    # Run both assessments on sites with substance data
    general_sites = _run_general_assessment(sites_with_substances)
    compound_combinations, compound_sites = _run_compound_assessment(sites_with_substances)
    
    # Handle sites without substance data separately
    unknown_substance_sites = _handle_unknown_substance_sites(sites_without_substances)
    
    # Branch analysis disabled - no longer needed
    branch_analysis_results = None
    print(f"ⓘ Branch analysis disabled")
    
    # Print summary
    _print_summary(distance_results, general_sites, compound_combinations, compound_sites)
    
    # Generate Step 5 visualizations
    print(f"\nGenerating Step 5 visualizations...")
    try:
        from step5_visualizations import create_step5_visualizations
        create_step5_visualizations()
        print(f"✓ Step 5 visualizations completed")
    except ImportError:
        print(f"⚠ Step 5 visualization module not found")
    except Exception as e:
        print(f"⚠ Could not create Step 5 visualizations: {e}")
    
    print(f"\n✓ STEP 5 ANALYSIS COMPLETED")
    
    # Return format compatible with main_workflow.py
    return {
        'general_results': (general_sites, {'total_sites': len(general_sites)}),
        'compound_results': (compound_sites, {'unique_sites': len(compound_sites),
                                              'total_combinations': len(compound_combinations)}),
        'unknown_substance_results': (unknown_substance_sites, {'total_sites': len(unknown_substance_sites)}),
        'branch_analysis_results': (branch_analysis_results, {'status': 'completed' if branch_analysis_results else 'skipped'}),
        'multi_threshold_results': {},  # Empty for compatibility
        'success': True
    }

def _run_general_assessment(distance_results):
    """
    General risk assessment using universal 500m threshold.
    
    Returns:
        DataFrame: Sites within 500m threshold
    """
    risk_threshold_m = WORKFLOW_SETTINGS['risk_threshold_m']
    
    high_risk_sites = distance_results[
        distance_results['Final_Distance_m'] <= risk_threshold_m
    ].copy()
    
    # Save results
    if not high_risk_sites.empty:
        sites_path = get_output_path('step5_high_risk_sites')
        high_risk_sites.to_csv(sites_path, index=False)
        
        # Create GVFK shapefile
        _create_gvfk_shapefile(high_risk_sites, 'step5_gvfk_high_risk')
        
        # Count unique GVFKs
        unique_gvfks = high_risk_sites['Closest_GVFK'].dropna().nunique()
        print(f"General assessment: {len(high_risk_sites)} sites within {risk_threshold_m}m")
        print(f"  Unique GVFKs affected: {unique_gvfks}")
    
    return high_risk_sites

def _run_compound_assessment(distance_results):
    """
    Compound-specific risk assessment using literature-based thresholds.
    
    Returns:
        tuple: (compound_combinations DataFrame, unique_sites DataFrame)
    """
    compound_combinations = _apply_compound_filtering(distance_results)
    
    if compound_combinations.empty:
        return compound_combinations, pd.DataFrame()
    
    # Get unique sites for summary
    unique_sites = compound_combinations.drop_duplicates(subset=['Lokalitet_ID']).copy()
    
    # Save results
    _save_compound_results(compound_combinations, unique_sites)
    
    # Count unique GVFKs
    unique_gvfks = unique_sites['Closest_GVFK'].dropna().nunique()
    print(f"Compound-specific assessment: {len(unique_sites)} unique sites, {len(compound_combinations)} combinations")
    print(f"  Unique GVFKs affected: {unique_gvfks}")
    
    return compound_combinations, unique_sites

def _apply_compound_filtering(distance_results):
    """
    Apply compound-specific distance filtering.
    
    Returns:
        DataFrame: All qualifying site-substance combinations
    """
    high_risk_combinations = []
    
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
                # Create row for this qualifying combination
                combo_row = row.to_dict()
                combo_row['Qualifying_Substance'] = substance
                combo_row['Qualifying_Category'] = category
                combo_row['Category_Threshold_m'] = compound_threshold
                combo_row['Within_Threshold'] = True
                high_risk_combinations.append(combo_row)
    
    return pd.DataFrame(high_risk_combinations) if high_risk_combinations else pd.DataFrame()

def _save_compound_results(compound_combinations, unique_sites):
    """Save compound-specific assessment results."""
    # Save detailed combinations (all qualifying substance-site pairs)
    detailed_path = get_output_path('step5_compound_detailed_combinations')
    compound_combinations.to_csv(detailed_path, index=False)
    
    # Save unique sites for compatibility
    if not unique_sites.empty:
        sites_path = get_output_path('step5_compound_specific_sites')
        unique_sites.to_csv(sites_path, index=False)
    
    # Create GVFK shapefile
    _create_gvfk_shapefile(compound_combinations, 'step5_compound_gvfk_high_risk')

def _create_gvfk_shapefile(high_risk_sites, output_key):
    """Create shapefile of high-risk GVFK polygons."""
    try:
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
        id_col = 'Navn' if 'Navn' in grundvand_gdf.columns else grundvand_gdf.columns[0]
        
        high_risk_gvfk_polygons = grundvand_gdf[
            grundvand_gdf[id_col].isin(high_risk_gvfk_names)
        ].copy()
        
        if not high_risk_gvfk_polygons.empty:
            output_path = get_output_path(output_key)
            high_risk_gvfk_polygons.to_file(output_path)
            print(f"  Created shapefile: {output_key} ({len(high_risk_gvfk_polygons)} GVFKs)")
            
    except Exception as e:
        print(f"  Warning: Could not create shapefile {output_key}: {e}")

def _print_summary(distance_results, general_sites, compound_combinations, compound_sites):
    """Print comprehensive summary of risk assessment results."""
    total_sites = len(distance_results)
    general_count = len(general_sites)
    compound_unique = len(compound_sites)
    compound_total = len(compound_combinations)
    
    print(f"\n" + "="*80)
    print(f"STEP 5: COMPREHENSIVE RISK ASSESSMENT RESULTS")  
    print(f"="*80)
    print(f"Input: {total_sites:,} sites analyzed from Step 4")
    
    # GENERAL ASSESSMENT
    print(f"\nGENERAL ASSESSMENT (500m universal threshold):")
    print(f"- Sites within 500m: {general_count:,} ({general_count/total_sites*100:.1f}%)")
    
    # Top categories from general assessment
    if not general_sites.empty:
        print(f"\nTop Categories (General Assessment):")
        
        # Industries
        if 'Lokalitetensbranche' in general_sites.columns:
            all_industries = []
            for ind_str in general_sites['Lokalitetensbranche'].dropna():
                industries = [i.strip() for i in str(ind_str).split(';') if i.strip()]
                all_industries.extend(industries)
            if all_industries:
                ind_counts = pd.Series(all_industries).value_counts().head(3)
                ind_str = ', '.join([f'{k} ({v})' for k, v in ind_counts.items()])
                print(f"  Industries: {ind_str}")
        
        # Activities
        if 'Lokalitetensaktivitet' in general_sites.columns:
            all_activities = []
            for act_str in general_sites['Lokalitetensaktivitet'].dropna():
                activities = [a.strip() for a in str(act_str).split(';') if a.strip()]
                all_activities.extend(activities)
            if all_activities:
                act_counts = pd.Series(all_activities).value_counts().head(3)
                act_str = ', '.join([f'{k} ({v})' for k, v in act_counts.items()])
                print(f"  Activities: {act_str}")
        
        # Substances
        if 'Lokalitetensstoffer' in general_sites.columns:
            all_substances = []
            for sub_str in general_sites['Lokalitetensstoffer'].dropna():
                substances = [s.strip() for s in str(sub_str).split(';') if s.strip()]
                all_substances.extend(substances)
            if all_substances:
                sub_counts = pd.Series(all_substances).value_counts().head(3)
                sub_str = ', '.join([f'{k} ({v})' for k, v in sub_counts.items()])
                print(f"  Substances: {sub_str}")
    
    # COMPOUND-SPECIFIC ASSESSMENT
    print(f"\nCOMPOUND-SPECIFIC ASSESSMENT (literature-based thresholds):")
    print(f"- Unique sites qualifying: {compound_unique:,} ({compound_unique/total_sites*100:.1f}%)")
    print(f"- Total site-substance combinations: {compound_total:,}")
    
    if compound_unique > 0:
        avg_substances = compound_total / compound_unique
        print(f"- Average qualifying substances per site: {avg_substances:.1f}")
    
    # Multi-substance distribution
    if not compound_combinations.empty:
        substances_per_site = compound_combinations.groupby('Lokalitet_ID').size()
        
        print(f"\nMulti-Substance Site Distribution:")
        for i in range(1, 4):
            count = (substances_per_site == i).sum()
            if count > 0:
                print(f"  {i} substance{'s' if i > 1 else ''}: {count:,} sites")
        
        # 4+ substances
        count_4plus = (substances_per_site >= 4).sum()
        if count_4plus > 0:
            print(f"  4+ substances: {count_4plus:,} sites")
            max_substances = substances_per_site.max()
            max_site = substances_per_site.idxmax()
            print(f"  Maximum: {max_substances} substances (Site: {max_site})")
    
    # Category breakdown with thresholds
    if not compound_combinations.empty:
        print(f"\nCategory Breakdown (by occurrences):")
        print(f"{'Category':<25} {'Threshold':<10} {'Occur.':<8} {'Sites':<8}")
        print(f"{'-'*25} {'-'*10} {'-'*8} {'-'*8}")
        
        # Get category statistics
        category_stats = {}
        for category in compound_combinations['Qualifying_Category'].unique():
            cat_data = compound_combinations[compound_combinations['Qualifying_Category'] == category]
            threshold = cat_data['Category_Threshold_m'].iloc[0] if not cat_data.empty else 500
            unique_sites = cat_data['Lokalitet_ID'].nunique()
            category_stats[category] = {
                'threshold': threshold,
                'occurrences': len(cat_data),
                'sites': unique_sites
            }
        
        # Sort by occurrences and print
        sorted_cats = sorted(category_stats.items(), key=lambda x: x[1]['occurrences'], reverse=True)
        for category, stats in sorted_cats[:8]:  # Top 8 categories
            threshold_str = f"{stats['threshold']:.1f}m"
            print(f"{category:<25} {threshold_str:<10} {stats['occurrences']:<8,} {stats['sites']:<8,}")
    
    # GVFK CASCADE
    print(f"\nGVFK FILTERING CASCADE:")
    print(f"{'Step':<45} {'GVFK':<8} {'% of Total':<10}")
    print(f"{'-'*45} {'-'*8} {'-'*10}")
    print(f"{'Total GVFK in Denmark':<45} {'2,043':<8} {'100.0%':<10}")
    print(f"{'With river contact (Step 2)':<45} {'593':<8} {'29.0%':<10}")
    print(f"{'With V1/V2 sites (Step 3)':<45} {'432':<8} {'21.1%':<10}")
    
    # Count unique GVFKs at each filtering stage
    # General assessment (500m)
    if not general_sites.empty and 'Closest_GVFK' in general_sites.columns:
        general_gvfks = general_sites['Closest_GVFK'].dropna().nunique()
        general_pct = (general_gvfks / 2043) * 100
        print(f"{'With sites ≤500m (General)':<45} {general_gvfks:<8,} {general_pct:<10.1f}%")
    
    # Compound-specific assessment
    if not compound_sites.empty and 'Closest_GVFK' in compound_sites.columns:
        compound_gvfks = compound_sites['Closest_GVFK'].dropna().nunique()
        compound_pct = (compound_gvfks / 2043) * 100
        print(f"{'With compound-specific risk (Step 5)':<45} {compound_gvfks:<8,} {compound_pct:<10.1f}%")
    
    # Difference explanation
    if general_count > 0:
        reduction = general_count - compound_unique
        print(f"\nDifference Analysis ({general_count:,} → {compound_unique:,} sites):")
        print(f"- {reduction:,} sites excluded due to stricter compound-specific thresholds")
        print(f"- Main exclusions: Sites with PAH (30m), BTEX (50m), or other low-mobility compounds")

def generate_gvfk_risk_summary():
    """
    Generate a summary table of GVFKs at risk with compound breakdown.
    This should be called after run_step5() completes.
    """
    # Load compound results
    compound_file = get_output_path('step5_compound_detailed_combinations')
    if not os.path.exists(compound_file):
        print("No compound-specific results found. Run Step 5 first.")
        return None
    
    compound_df = pd.read_csv(compound_file)
    
    # Extract all unique GVFKs using consistent method
    all_gvfks = _extract_unique_gvfk_names(compound_df)
    
    if not all_gvfks:
        print("Warning: No GVFKs found in compound results")
        return None
    
    # Create GVFK summary
    gvfk_summary = []
    
    # Process each GVFK
    for gvfk in all_gvfks:
        # Find all rows that reference this GVFK
        gvfk_rows = []
        
        # Check in All_Affected_GVFKs
        if 'All_Affected_GVFKs' in compound_df.columns:
            for idx, row in compound_df.iterrows():
                gvfk_list = str(row.get('All_Affected_GVFKs', ''))
                if gvfk_list and gvfk_list != 'nan':
                    gvfks = [g.strip() for g in gvfk_list.split(';') if g.strip()]
                    if gvfk in gvfks:
                        gvfk_rows.append(row)
        
        # If nothing found, check Closest_GVFK
        if not gvfk_rows and 'Closest_GVFK' in compound_df.columns:
            gvfk_data = compound_df[compound_df['Closest_GVFK'] == gvfk]
            gvfk_rows = [row for _, row in gvfk_data.iterrows()]
        
        if gvfk_rows:
            # Convert to DataFrame for easier processing
            gvfk_data = pd.DataFrame(gvfk_rows)
            
            # Count sites and categories
            category_counts = gvfk_data['Qualifying_Category'].value_counts()
            unique_sites = gvfk_data['Lokalitet_ID'].nunique()
            
            summary_row = {
                'GVFK': gvfk,
                'Total_Sites': unique_sites,
                'Total_Combinations': len(gvfk_data)
            }
            
            # Add counts for each category
            for category in category_counts.index:
                summary_row[category] = category_counts[category]
            
            gvfk_summary.append(summary_row)
    
    # Convert to DataFrame and sort
    if gvfk_summary:
        gvfk_df = pd.DataFrame(gvfk_summary).fillna(0)
        gvfk_df = gvfk_df.sort_values('Total_Sites', ascending=False)
        
        # Save to CSV
        output_path = get_output_path('step5_gvfk_risk_summary')
        gvfk_df.to_csv(output_path, index=False)
        
        print(f"\n✓ GVFK risk summary saved: {output_path}")
        print(f"  Total GVFKs at risk: {len(gvfk_df)}")
        print(f"  Top 5 GVFKs by site count: {', '.join(gvfk_df.head()['GVFK'].tolist())}")
        
        return gvfk_df
    
    return None

def _separate_sites_by_substance_data(distance_results):
    """
    Separate sites into those with and without substance data.
    
    Args:
        distance_results (DataFrame): All sites from Step 4
        
    Returns:
        tuple: (sites_with_substances, sites_without_substances)
    """
    # Check which sites have substance data
    has_substances = distance_results['Lokalitetensstoffer'].notna() & \
                     (distance_results['Lokalitetensstoffer'].astype(str).str.strip() != '') & \
                     (distance_results['Lokalitetensstoffer'].astype(str) != 'nan')
    
    sites_with_substances = distance_results[has_substances].copy()
    sites_without_substances = distance_results[~has_substances].copy()
    
    print(f"Data separation: {len(sites_with_substances)} sites with substances, {len(sites_without_substances)} sites without substances")
    
    return sites_with_substances, sites_without_substances

def _handle_unknown_substance_sites(sites_without_substances):
    """
    Handle sites without substance data separately.
    These sites are "parked" for separate analysis.
    
    Args:
        sites_without_substances (DataFrame): Sites without substance data
        
    Returns:
        DataFrame: Sites without substances (unchanged, just documented)
    """
    if sites_without_substances.empty:
        print("No sites without substance data found.")
        return sites_without_substances
    
    print(f"\nUnknown Substance Sites Analysis:")
    print(f"  Total sites without substance data: {len(sites_without_substances)}")
    
    # Save these sites separately
    if len(sites_without_substances) > 0:
        unknown_path = get_output_path('step5_unknown_substance_sites')
        sites_without_substances.to_csv(unknown_path, index=False)
        print(f"  ✓ Saved to: {unknown_path}")
        
        # Basic statistics
        if 'Final_Distance_m' in sites_without_substances.columns:
            mean_dist = sites_without_substances['Final_Distance_m'].mean()
            median_dist = sites_without_substances['Final_Distance_m'].median()
            within_500m = (sites_without_substances['Final_Distance_m'] <= 500).sum()
            print(f"  Distance statistics: mean={mean_dist:.0f}m, median={median_dist:.0f}m")
            print(f"  Sites within 500m: {within_500m} ({within_500m/len(sites_without_substances)*100:.1f}%)")
        
        # Branch information if available
        if 'Lokalitetensbranche' in sites_without_substances.columns:
            branches = sites_without_substances['Lokalitetensbranche'].value_counts()
            print(f"  Top branches: {', '.join(branches.head(3).index.tolist())}")
    
    return sites_without_substances

if __name__ == "__main__":
    # Run Step 5 risk assessment
    results = run_step5()
    
    if results['success']:
        print(f"\nStep 5 completed successfully:")
        print(f"  General assessment: {results['general_results'][1]['total_sites']} sites")
        print(f"  Compound-specific: {results['compound_results'][1]['unique_sites']} sites")
        print(f"  Branch analysis: {results['branch_analysis_results'][1]['status']}")
        
        # Generate GVFK summary
        gvfk_summary = generate_gvfk_risk_summary()