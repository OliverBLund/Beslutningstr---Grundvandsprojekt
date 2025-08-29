"""
Step 4: Calculate distances between V1/V2 sites and river segments.

This module calculates distances for each lokalitet-GVFK combination,
identifies minimum distances per site, and creates output files for
risk assessment and visualization.
"""

import geopandas as gpd
import pandas as pd
import numpy as np
import os
from config import RIVERS_PATH, GRUNDVAND_PATH, get_output_path, WORKFLOW_SETTINGS

def run_step4(v1v2_combined):
    """
    Step 4: Calculate distances between V1/V2 sites and river segments with contact.
    Handles one-to-many site-GVFK relationships: calculates distances for each
    lokalitet-GVFK combination separately.
    
    Args:
        v1v2_combined (GeoDataFrame): V1/V2 sites with GVFK relationships from Step 3
    
    Returns:
        DataFrame: Distance calculation results with minimum distance flags
    """
    print("Step 4: Calculating distances between V1/V2 sites and river segments")
    
    if v1v2_combined.empty:
        print("No V1/V2 sites found from Step 3. Cannot proceed with distance calculation.")
        return None
    
    # Load rivers file
    rivers = gpd.read_file(RIVERS_PATH)
    rivers_with_contact = rivers[rivers['Kontakt'] == 1]
    
    if rivers_with_contact.empty:
        print("No river segments with Kontakt = 1 found. Cannot calculate distances.")
        return None
    
    # Ensure same CRS
    target_crs = v1v2_combined.crs
    if rivers_with_contact.crs != target_crs:
        rivers_with_contact = rivers_with_contact.to_crs(target_crs)
    
    print(f"Processing {v1v2_combined['Lokalitet_'].nunique()} unique sites in {len(v1v2_combined)} site-GVFK combinations")
    
    # Calculate distances for each lokalitet-GVFK combination
    
    # Initialize results lists
    results_data = []
    
    # Progress tracking
    total_combinations = len(v1v2_combined)
    progress_percent = WORKFLOW_SETTINGS['progress_interval_percent']
    print_interval = max(1, total_combinations * progress_percent // 100)  # Print progress based on config
    
    for idx, row in v1v2_combined.iterrows():
        if idx % print_interval == 0:
            print(f"Processing combination {idx+1}/{total_combinations} ({(idx+1)/total_combinations*100:.1f}%)")
        
        # Get row properties
        lokalitet_id = row['Lokalitet_']
        gvfk_name = row['Navn']
        site_type = row.get('Lokalitete', 'Unknown')
        site_geom = row.geometry
        
        # Validate data
        if pd.isna(gvfk_name) or site_geom is None or site_geom.is_empty:
            continue
        
        # Find river segments in the same GVFK with contact
        matching_rivers = rivers_with_contact[rivers_with_contact['GVForekom'] == gvfk_name]
        
        # Initialize result for this combination
        result = {
            'Lokalitet_ID': lokalitet_id,
            'GVFK': gvfk_name,
            'Site_Type': site_type,
            'Has_Matching_Rivers': len(matching_rivers) > 0,
            'River_Count': len(matching_rivers),
            'Distance_to_River_m': None
        }
        
        # Preserve Step 5 columns if available
        step5_columns = ['Lokalitetensbranche', 'Lokalitetensaktivitet', 'Lokalitetensstoffer', 
                         'Lokalitetsnavn', 'Lokalitetetsforureningsstatus', 'Regionsnavn', 'Kommunenavn']
        for col in step5_columns:
            if col in row.index:
                result[col] = row[col]
        
        if matching_rivers.empty:
            # No rivers with contact in this GVFK
            result['Distance_to_River_m'] = None
        else:
            # Calculate minimum distance to all matching river segments
            min_distance = float('inf')
            
            for _, river in matching_rivers.iterrows():
                distance = site_geom.distance(river.geometry)
                min_distance = min(min_distance, distance)
            
            if min_distance == float('inf'):
                result['Distance_to_River_m'] = None
            else:
                result['Distance_to_River_m'] = min_distance
        
        results_data.append(result)
    
    # Create results DataFrame
    if not results_data:
        print("No distances could be calculated.")
        return None
    
    results_df = pd.DataFrame(results_data)
    
    # Filter to only combinations with valid distances
    valid_results = results_df[results_df['Distance_to_River_m'].notna()].copy()
    
    if valid_results.empty:
        print("No valid distances calculated.")
        return None
    
    # Calculate statistics
    unique_sites_with_distances = valid_results['Lokalitet_ID'].nunique()
    total_unique_sites = results_df['Lokalitet_ID'].nunique()
    print(f"Distance calculation completed: {unique_sites_with_distances} of {total_unique_sites} sites have distances to rivers")
    
    # Add minimum distance identification for each site
    site_min_distances = valid_results.groupby('Lokalitet_ID')['Distance_to_River_m'].min().reset_index()
    site_min_distances.columns = ['Lokalitet_ID', 'Min_Distance_m']
    
    # Add flag for minimum distance per site
    results_df = results_df.merge(site_min_distances, on='Lokalitet_ID', how='left')
    results_df['Is_Min_Distance'] = (results_df['Distance_to_River_m'] == results_df['Min_Distance_m']) & results_df['Distance_to_River_m'].notna()
    
    # Update valid_results with the new columns
    valid_results = results_df[results_df['Distance_to_River_m'].notna()].copy()
    
    if len(valid_results) > 0:
        # Statistics for final distances per site (for risk assessment)
        min_distances_only = valid_results[valid_results['Is_Min_Distance'] == True]['Distance_to_River_m']
        print(f"Final distance statistics: {len(min_distances_only)} sites, mean={min_distances_only.mean():.0f}m, median={min_distances_only.median():.0f}m")
    
    # Save results
    _save_distance_results(results_df, valid_results, v1v2_combined)
    
    # Create interactive map
    if len(valid_results) > 0:
        _create_interactive_map(v1v2_combined, rivers_with_contact, valid_results)
    
    return results_df

def _save_distance_results(results_df, valid_results, v1v2_combined):
    """Save distance calculation results - only essential files."""
    
    if len(valid_results) == 0:
        return
    
    # Save valid distances (used by visualizations)
    valid_results.to_csv(get_output_path('step4_valid_distances'), index=False)
    
    # Create final distances for risk assessment (minimum per site)
    min_distance_entries = valid_results[valid_results['Is_Min_Distance'] == True].copy()
    
    # Ensure only ONE row per site (use GVFK name as tiebreaker)
    final_distances = (min_distance_entries
                      .sort_values(['Lokalitet_ID', 'GVFK'])
                      .groupby('Lokalitet_ID')
                      .first()
                      .reset_index())
    
    # Prepare final distances with essential columns
    base_columns = ['Lokalitet_ID', 'GVFK', 'Site_Type', 'Distance_to_River_m']
    step5_columns = ['Lokalitetensbranche', 'Lokalitetensaktivitet', 'Lokalitetensstoffer', 
                     'Lokalitetsnavn', 'Lokalitetetsforureningsstatus', 'Regionsnavn', 'Kommunenavn']
    available_step5_columns = [col for col in step5_columns if col in final_distances.columns]
    
    output_columns = base_columns + available_step5_columns
    final_distances_clean = final_distances[output_columns].copy()
    final_distances_clean = final_distances_clean.rename(columns={
        'GVFK': 'Closest_GVFK', 
        'Distance_to_River_m': 'Final_Distance_m'
    })
    
    # Add GVFK count and list per site
    gvfk_counts = valid_results.groupby('Lokalitet_ID').size().reset_index()
    gvfk_counts.columns = ['Lokalitet_ID', 'Total_GVFKs_Affected']
    final_distances_clean = final_distances_clean.merge(gvfk_counts, on='Lokalitet_ID', how='left')
    
    all_gvfks = valid_results.groupby('Lokalitet_ID')['GVFK'].apply(lambda x: '; '.join(sorted(x.unique()))).reset_index()
    all_gvfks.columns = ['Lokalitet_ID', 'All_Affected_GVFKs']
    final_distances_clean = final_distances_clean.merge(all_gvfks, on='Lokalitet_ID', how='left')
    
    # Save final distances for Step 5
    final_distances_clean.to_csv(get_output_path('step4_final_distances_for_risk_assessment'), index=False)
    
    # Create unique distances file (used by visualizations)  
    unique_distances = final_distances_clean.copy()
    unique_distances = unique_distances.rename(columns={
        'Lokalitet_ID': 'Lokalitetsnr',
        'Final_Distance_m': 'Distance_to_River_m',
        'Closest_GVFK': 'GVFK'
    })
    unique_distances.to_csv(get_output_path('unique_lokalitet_distances'), index=False)
    
    # Create shapefile version with geometry (for visualizations that need geometries)
    if not v1v2_combined.empty:
        # Get geometry for each unique lokalitet (take first occurrence)
        site_geometries = v1v2_combined.drop_duplicates('Lokalitet_')[['Lokalitet_', 'geometry']]
        site_geometries = site_geometries.rename(columns={'Lokalitet_': 'Lokalitetsnr'})
        
        # Merge with unique distances
        unique_distances_with_geom = unique_distances.merge(
            site_geometries, on='Lokalitetsnr', how='left'
        )
        
        # Create GeoDataFrame and save shapefile
        unique_gdf = gpd.GeoDataFrame(unique_distances_with_geom, crs=v1v2_combined.crs)
        unique_gdf.to_file(get_output_path('unique_lokalitet_distances_shp'))
    
    print(f"Step 4 results saved: {len(final_distances_clean)} sites with final distances")

def _create_interactive_map(v1v2_combined, rivers_with_contact, valid_results):
    """Create interactive map visualization using sampled data."""
    
    # Sample data for visualization - limit to 1000 sites for performance
    total_sites = valid_results['Lokalitet_ID'].nunique()
    if total_sites <= 1000:
        sampled_site_ids = valid_results['Lokalitet_ID'].unique()
    else:
        sampled_site_ids = np.random.choice(
            valid_results['Lokalitet_ID'].unique(), 
            size=1000, 
            replace=False
        )
    
    sampled_results = valid_results[valid_results['Lokalitet_ID'].isin(sampled_site_ids)].copy()
    
    # Get GVFK polygons for visualization
    gvf = gpd.read_file(GRUNDVAND_PATH)
    sampled_gvfks = set(sampled_results['GVFK'].unique())
    relevant_gvfk_polygons = gvf[gvf['Navn'].isin(sampled_gvfks)]
    
    # Add distance data to combined data for mapping
    v1v2_with_distances = v1v2_combined.copy()
    lookup_data = {}
    for _, row in sampled_results.iterrows():
        key = f"{row['Lokalitet_ID']}_{row['GVFK']}"
        lookup_data[key] = {
            'Distance_m': row['Distance_to_River_m'],
            'Is_Min_Dist': row['Is_Min_Distance'],
            'Min_Dist_m': row.get('Min_Distance_m', row['Distance_to_River_m'])
        }
    
    v1v2_with_distances['lookup_key'] = v1v2_with_distances['Lokalitet_'] + '_' + v1v2_with_distances['Navn']
    
    for key, data in lookup_data.items():
        mask = v1v2_with_distances['lookup_key'] == key
        v1v2_with_distances.loc[mask, 'Distance_m'] = data['Distance_m']
        v1v2_with_distances.loc[mask, 'Is_Min_Dist'] = data['Is_Min_Dist']
        v1v2_with_distances.loc[mask, 'Min_Dist_m'] = data['Min_Dist_m']
    
    # Filter to sampled combinations
    sampled_combinations = v1v2_with_distances[
        v1v2_with_distances['Lokalitet_'].isin(sampled_results['Lokalitet_ID']) &
        v1v2_with_distances['Navn'].isin(sampled_results['GVFK'])
    ]
    
    if not sampled_combinations.empty:
        try:
            from create_interactive_map import create_map
            create_map(sampled_combinations, rivers_with_contact, sampled_results, relevant_gvfk_polygons)
            print(f"Interactive map created: {get_output_path('interactive_distance_map')}")
        except ImportError:
            print("Warning: create_interactive_map module not found, skipping map creation")
        except Exception as e:
            import warnings
            warnings.filterwarnings("ignore", category=UserWarning, module="pyogrio.raw")

    