"""
Step 5: Risk Assessment and Analysis of High-Risk V1/V2 Sites

This step filters the distance results to identify localities within 500m of rivers
and performs detailed analysis of contamination characteristics for risk assessment.
"""

import pandas as pd
import geopandas as gpd
import numpy as np
import os
from config import get_output_path, ensure_results_directory, GRUNDVAND_PATH

def run_step5():
    """
    Execute Step 5: Risk assessment of V1/V2 localities within 500m of rivers.
    
    Returns:
        tuple: (high_risk_sites_df, analysis_summary)
    """
    print("\nStep 5: Risk Assessment of High-Risk V1/V2 Sites")
    print("Filtering to localities within 500m of rivers and analyzing contamination characteristics")
    
    # Ensure output directory exists
    ensure_results_directory()
    
    # Load Step 4 results
    step4_file = get_output_path('step4_final_distances_for_risk_assessment')
    
    if not os.path.exists(step4_file):
        print(f"ERROR: Step 4 results not found at {step4_file}")
        print("Please run Step 4 first to generate distance data.")
        return None, None
    
    try:
        distance_results = pd.read_csv(step4_file)
        print(f"Loaded Step 4 results: {len(distance_results)} unique localities")
    except Exception as e:
        print(f"Error loading Step 4 results: {e}")
        return None, None
    
    # Apply 500m distance filter
    risk_threshold_m = 500
    high_risk_sites = distance_results[
        distance_results['Final_Distance_m'] <= risk_threshold_m
    ].copy()
    
    print(f"\nRisk filtering results:")
    print(f"Total localities with distances: {len(distance_results)}")
    print(f"High-risk localities (≤{risk_threshold_m}m): {len(high_risk_sites)}")
    print(f"Percentage high-risk: {len(high_risk_sites)/len(distance_results)*100:.1f}%")
    
    if high_risk_sites.empty:
        print("No high-risk sites found within 500m threshold.")
        return high_risk_sites, {}
    
    # Perform contamination analysis
    analysis_summary = _analyze_contamination_characteristics(high_risk_sites, risk_threshold_m)
    
    # Save high-risk sites and create filtered GVFK shapefile
    high_risk_gvfk_names = _save_step5_results(high_risk_sites, analysis_summary, risk_threshold_m)
    
    return high_risk_sites, analysis_summary

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
    
    # Contamination analysis with proper handling of semicolon-separated values
    contamination_cols = ['Lokalitetensbranche', 'Lokalitetensaktivitet', 'Lokalitetensstoffer']
    
    for col in contamination_cols:
        if col in high_risk_sites.columns:
            # Count non-null values
            non_null_count = high_risk_sites[col].notna().sum()
            
            if non_null_count > 0:
                # Handle semicolon-separated values properly
                if col in ['Lokalitetensbranche', 'Lokalitetensaktivitet']:
                    # These columns contain semicolon-separated multiple values
                    all_categories = []
                    sites_with_category = {}  # Track which sites have each category
                    
                    for idx, value in high_risk_sites[col].dropna().items():
                        if pd.notna(value) and str(value).strip():
                            # Split by semicolon and clean up
                            categories = [cat.strip() for cat in str(value).split(';') if cat.strip()]
                            all_categories.extend(categories)
                            
                            # Track sites for each category (to avoid double counting sites)
                            for cat in categories:
                                if cat not in sites_with_category:
                                    sites_with_category[cat] = set()
                                sites_with_category[cat].add(idx)
                    
                    # Count occurrences and unique sites per category
                    category_counts = pd.Series(all_categories).value_counts()
                    category_site_counts = {cat: len(sites) for cat, sites in sites_with_category.items()}
                    
                    analysis['contamination_analysis'][col] = {
                        'total_sites_with_data': non_null_count,
                        'total_category_instances': len(all_categories),
                        'unique_categories': len(category_counts),
                        'top_categories_by_occurrence': category_counts.head(10).to_dict(),
                        'top_categories_by_sites': dict(sorted(category_site_counts.items(), 
                                                             key=lambda x: x[1], reverse=True)[:10])
                    }
                    
                    print(f"\n{col} analysis (semicolon-separated values):")
                    print(f"  Sites with data: {non_null_count}/{len(high_risk_sites)} ({non_null_count/len(high_risk_sites)*100:.1f}%)")
                    print(f"  Total category instances: {len(all_categories)}")
                    print(f"  Unique categories: {len(category_counts)}")
                    print(f"  Average categories per site: {len(all_categories)/non_null_count:.1f}")
                    print(f"  Top 5 categories by occurrence:")
                    for category, count in category_counts.head(5).items():
                        sites_count = category_site_counts[category]
                        print(f"    {category}: {count} instances ({sites_count} sites)")
                
                else:
                    # Handle single-value columns (like Lokalitetensstoffer) as before but also check for separators
                    if ';' in str(high_risk_sites[col].dropna().iloc[0]) or ',' in str(high_risk_sites[col].dropna().iloc[0]):
                        # This column also has separated values
                        all_substances = []
                        sites_with_substance = {}
                        
                        for idx, value in high_risk_sites[col].dropna().items():
                            if pd.notna(value) and str(value).strip():
                                # Split by semicolon or comma and clean up
                                substances = [s.strip() for s in str(value).replace(';', ',').split(',') if s.strip()]
                                all_substances.extend(substances)
                                
                                for substance in substances:
                                    if substance not in sites_with_substance:
                                        sites_with_substance[substance] = set()
                                    sites_with_substance[substance].add(idx)
                        
                        substance_counts = pd.Series(all_substances).value_counts()
                        substance_site_counts = {sub: len(sites) for sub, sites in sites_with_substance.items()}
                        
                        analysis['contamination_analysis'][col] = {
                            'total_sites_with_data': non_null_count,
                            'total_substance_instances': len(all_substances),
                            'unique_substances': len(substance_counts),
                            'top_substances_by_occurrence': substance_counts.head(10).to_dict(),
                            'top_substances_by_sites': dict(sorted(substance_site_counts.items(), 
                                                                 key=lambda x: x[1], reverse=True)[:10])
                        }
                        
                        print(f"\n{col} analysis (separated values):")
                        print(f"  Sites with data: {non_null_count}/{len(high_risk_sites)} ({non_null_count/len(high_risk_sites)*100:.1f}%)")
                        print(f"  Total substance instances: {len(all_substances)}")
                        print(f"  Unique substances: {len(substance_counts)}")
                        print(f"  Average substances per site: {len(all_substances)/non_null_count:.1f}")
                        print(f"  Top 5 substances by occurrence:")
                        for substance, count in substance_counts.head(5).items():
                            sites_count = substance_site_counts[substance]
                            print(f"    {substance}: {count} instances ({sites_count} sites)")
                    
                    else:
                        # Handle as single value column (legacy approach)
                        unique_values = high_risk_sites[col].nunique()
                        top_categories = high_risk_sites[col].value_counts().head(10)
                        
                        analysis['contamination_analysis'][col] = {
                            'total_with_data': non_null_count,
                            'unique_categories': unique_values,
                            'top_categories': top_categories.to_dict()
                        }
                        
                        print(f"\n{col} analysis:")
                        print(f"  Sites with data: {non_null_count}/{len(high_risk_sites)} ({non_null_count/len(high_risk_sites)*100:.1f}%)")
                        print(f"  Unique categories: {unique_values}")
                        print(f"  Top 5 categories:")
                        for category, count in top_categories.head(5).items():
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