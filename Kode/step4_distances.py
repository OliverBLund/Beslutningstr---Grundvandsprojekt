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
from config import RIVERS_PATH, GRUNDVAND_PATH, get_output_path

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
    print("Processing one-to-many site-GVFK relationships")
    
    if v1v2_combined.empty:
        print("No V1/V2 sites found from Step 3. Cannot proceed with distance calculation.")
        return None
    
    # Load rivers file
    print("Loading rivers file...")
    rivers = gpd.read_file(RIVERS_PATH)
    print(f"Loaded {len(rivers)} river segments")
    
    # Filter rivers to only those with contact (Kontakt = 1)
    rivers_with_contact = rivers[rivers['Kontakt'] == 1]
    print(f"Found {len(rivers_with_contact)} river segments with Kontakt = 1")
    
    if rivers_with_contact.empty:
        print("No river segments with Kontakt = 1 found. Cannot calculate distances.")
        return None
    
    # Ensure same CRS
    target_crs = v1v2_combined.crs
    if rivers_with_contact.crs != target_crs:
        rivers_with_contact = rivers_with_contact.to_crs(target_crs)
    
    print(f"Data summary:")
    print(f"- Unique localities: {v1v2_combined['Lokalitet_'].nunique()}")
    print(f"- Site-GVFK combinations: {len(v1v2_combined)}")
    print(f"- GVFKs involved: {v1v2_combined['Navn'].nunique()}")
    
    # Get unique GVFKs from V1/V2 data and rivers data
    v1v2_gvfks = set(v1v2_combined['Navn'].dropna().unique())
    river_gvfks = set(rivers_with_contact['GVForekom'].dropna().unique())
    
    print(f"Found {len(v1v2_gvfks)} unique GVFKs in V1/V2 data")
    print(f"Found {len(river_gvfks)} unique GVFKs in river segments with contact")
    
    # Check for GVFKs with V1/V2 sites but no rivers with contact
    gvfks_without_rivers = v1v2_gvfks - river_gvfks
    if gvfks_without_rivers:
        print(f"WARNING: {len(gvfks_without_rivers)} GVFKs have V1/V2 sites but no river segments with Kontakt = 1")
        print(f"First few GVFKs without rivers: {sorted(list(gvfks_without_rivers))[:5]}...")
    
    # Calculate distances for each lokalitet-GVFK combination
    print(f"\nCalculating distances for {len(v1v2_combined)} lokalitet-GVFK combinations...")
    
    # Initialize results lists
    results_data = []
    
    # Progress tracking
    total_combinations = len(v1v2_combined)
    print_interval = max(1, total_combinations // 10)  # Print progress every 10%
    
    for idx, row in v1v2_combined.iterrows():
        if idx % print_interval == 0:
            print(f"Processing combination {idx+1}/{total_combinations} ({(idx+1)/total_combinations*100:.1f}%)")
        
        # Get row properties
        lokalitet_id = row['Lokalitet_']
        gvfk_name = row['Navn']
        site_type = row.get('Lokalitete', 'Unknown')
        site_geom = row.geometry
        
        # Validate data
        if pd.isna(gvfk_name):
            print(f"Warning: Lokalitet {lokalitet_id} has no GVFK identifier. Skipping...")
            continue
        
        if site_geom is None or site_geom.is_empty:
            print(f"Warning: Lokalitet {lokalitet_id} has no valid geometry. Skipping...")
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
                try:
                    distance = site_geom.distance(river.geometry)
                    min_distance = min(min_distance, distance)
                except Exception as e:
                    print(f"Error calculating distance for lokalitet {lokalitet_id} to river: {e}")
                    continue
            
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
    print(f"\nDistance calculation results:")
    print(f"Total lokalitet-GVFK combinations processed: {len(results_df)}")
    print(f"Combinations with matching rivers: {len(valid_results)}")
    print(f"Combinations without matching rivers: {len(results_df) - len(valid_results)}")
    print(f"Percentage with matching rivers: {len(valid_results)/len(results_df)*100:.1f}%")
    
    # Site-level statistics
    unique_sites_with_distances = valid_results['Lokalitet_ID'].nunique()
    total_unique_sites = results_df['Lokalitet_ID'].nunique()
    print(f"Unique sites with at least one distance: {unique_sites_with_distances} of {total_unique_sites}")
    
    # Add minimum distance identification for each site
    print(f"\nIdentifying minimum distances per site...")
    site_min_distances = valid_results.groupby('Lokalitet_ID')['Distance_to_River_m'].min().reset_index()
    site_min_distances.columns = ['Lokalitet_ID', 'Min_Distance_m']
    
    # Add flag for minimum distance per site
    results_df = results_df.merge(site_min_distances, on='Lokalitet_ID', how='left')
    results_df['Is_Min_Distance'] = (results_df['Distance_to_River_m'] == results_df['Min_Distance_m']) & results_df['Distance_to_River_m'].notna()
    
    # Update valid_results with the new columns
    valid_results = results_df[results_df['Distance_to_River_m'].notna()].copy()
    
    if len(valid_results) > 0:
        print(f"\nDistance statistics for ALL combinations (meters):")
        print(f"Minimum distance: {valid_results['Distance_to_River_m'].min():.2f}")
        print(f"Maximum distance: {valid_results['Distance_to_River_m'].max():.2f}")
        print(f"Mean distance: {valid_results['Distance_to_River_m'].mean():.2f}")
        print(f"Median distance: {valid_results['Distance_to_River_m'].median():.2f}")
        
        # Statistics for MINIMUM distances per site (final distances for risk assessment)
        min_distances_only = valid_results[valid_results['Is_Min_Distance'] == True]['Distance_to_River_m']
        print(f"\nFINAL distance statistics (minimum per site, for risk assessment):")
        print(f"Number of sites with final distances: {len(min_distances_only)}")
        print(f"Minimum final distance: {min_distances_only.min():.2f}")
        print(f"Maximum final distance: {min_distances_only.max():.2f}")
        print(f"Mean final distance: {min_distances_only.mean():.2f}")
        print(f"Median final distance: {min_distances_only.median():.2f}")
        
        # Count by site type
        if 'Site_Type' in valid_results.columns:
            type_counts = valid_results['Site_Type'].value_counts()
            print(f"\nDistance calculations by site type:")
            for site_type, count in type_counts.items():
                print(f"- {site_type}: {count} lokalitet-GVFK combinations")
    
    # Save results
    _save_distance_results(results_df, valid_results, v1v2_combined)
    
    # Create interactive map
    if len(valid_results) > 0:
        _create_and_save_interactive_map(v1v2_combined, rivers_with_contact, valid_results)
    
    return results_df

def _save_distance_results(results_df, valid_results, v1v2_combined):
    """Save distance calculation results to various output formats."""
    
    # Save main results
    results_df.to_csv(get_output_path('step4_distance_results'), index=False)
    valid_results.to_csv(get_output_path('step4_valid_distances'), index=False)
    
    print(f"\nResults saved to:")
    print(f"- All results: {get_output_path('step4_distance_results')}")
    print(f"- Valid distances only: {get_output_path('step4_valid_distances')}")
    
    # Create and save final distances for risk assessment (minimum per site)
    if len(valid_results) > 0:
        # Get all minimum distance entries
        min_distance_entries = valid_results[valid_results['Is_Min_Distance'] == True].copy()
        
        # CRITICAL FIX: Ensure only ONE row per site, even if multiple GVFKs have same min distance
        # Use GVFK name as tiebreaker (alphabetically first) to ensure deterministic results
        final_distances = (min_distance_entries
                          .sort_values(['Lokalitet_ID', 'GVFK'])  # Sort by site ID, then GVFK name
                          .groupby('Lokalitet_ID')  # Group by unique site
                          .first()  # Take first (alphabetically first GVFK for ties)
                          .reset_index())
        
        print(f"Fixed duplicates: {len(min_distance_entries)} min-distance entries → {len(final_distances)} unique sites")
        
        # Base columns for final distances
        base_columns = ['Lokalitet_ID', 'GVFK', 'Site_Type', 'Distance_to_River_m']
        
        # Add Step 5 columns if available
        step5_columns = ['Lokalitetensbranche', 'Lokalitetensaktivitet', 'Lokalitetensstoffer', 
                         'Lokalitetsnavn', 'Lokalitetetsforureningsstatus', 'Regionsnavn', 'Kommunenavn']
        available_step5_columns = [col for col in step5_columns if col in final_distances.columns]
        
        # Select columns for final output
        output_columns = base_columns + available_step5_columns
        final_distances_clean = final_distances[output_columns].copy()
        final_distances_clean = final_distances_clean.rename(columns={
            'GVFK': 'Closest_GVFK', 
            'Distance_to_River_m': 'Final_Distance_m'
        })
        
        if available_step5_columns:
            print(f"Including Step 5 columns in final distances: {available_step5_columns}")
        
        # Add count of total GVFKs affected per site
        gvfk_counts = valid_results.groupby('Lokalitet_ID').size().reset_index()
        gvfk_counts.columns = ['Lokalitet_ID', 'Total_GVFKs_Affected']
        final_distances_clean = final_distances_clean.merge(gvfk_counts, on='Lokalitet_ID', how='left')
        
        # Add list of all affected GVFKs per site
        all_gvfks = valid_results.groupby('Lokalitet_ID')['GVFK'].apply(lambda x: '; '.join(sorted(x.unique()))).reset_index()
        all_gvfks.columns = ['Lokalitet_ID', 'All_Affected_GVFKs']
        final_distances_clean = final_distances_clean.merge(all_gvfks, on='Lokalitet_ID', how='left')
        
        final_distances_clean.to_csv(get_output_path('step4_final_distances_for_risk_assessment'), index=False)
        print(f"- Final distances for risk assessment: {get_output_path('step4_final_distances_for_risk_assessment')}")
        
        # Create unique lokalitet distances file for visualizations (includes Step 5 columns)
        unique_distances = final_distances_clean.copy()
        unique_distances = unique_distances.rename(columns={
            'Lokalitet_ID': 'Lokalitetsnr',
            'Final_Distance_m': 'Distance_to_River_m',
            'Closest_GVFK': 'GVFK'
        })
        
        print(f"Unique distances will include {len(unique_distances.columns)} columns (including Step 5 data)")
        
        # Add geometry information by merging with site data
        if not v1v2_combined.empty:
            # Get geometry for each unique lokalitet (take first occurrence)
            site_geometries = v1v2_combined.drop_duplicates('Lokalitet_')[['Lokalitet_', 'geometry']]
            site_geometries = site_geometries.rename(columns={'Lokalitet_': 'Lokalitetsnr'})
            
            # Merge with unique distances
            unique_distances_with_geom = unique_distances.merge(
                site_geometries, on='Lokalitetsnr', how='left'
            )
            
            # Create GeoDataFrame and save both CSV and shapefile
            unique_gdf = gpd.GeoDataFrame(unique_distances_with_geom, crs=v1v2_combined.crs)
            
            # Save CSV for visualizations (without geometry column)
            unique_distances.to_csv(get_output_path('unique_lokalitet_distances'), index=False)
            print(f"- Unique lokalitet distances (for visualizations): {get_output_path('unique_lokalitet_distances')}")
            
            # Save shapefile for GIS analysis
            unique_gdf.to_file(get_output_path('unique_lokalitet_distances_shp'))
            print(f"- Unique lokalitet distances (shapefile): {get_output_path('unique_lokalitet_distances_shp')}")
        else:
            # Fallback - save CSV only
            unique_distances.to_csv(get_output_path('unique_lokalitet_distances'), index=False)
            print(f"- Unique lokalitet distances (CSV only): {get_output_path('unique_lokalitet_distances')}")
    
    # Export enhanced shapefiles with distance data
    print(f"\nExporting shapefiles with distance data...")
    
    # Add distance data back to the original GeoDataFrame
    v1v2_with_distances = v1v2_combined.copy()
    
    # Create a lookup for distance data (using lokalitet + GVFK as key)
    v1v2_with_distances['lookup_key'] = v1v2_with_distances['Lokalitet_'] + '_' + v1v2_with_distances['Navn']
    results_df['lookup_key'] = results_df['Lokalitet_ID'] + '_' + results_df['GVFK']
    
    # Merge distance data
    distance_lookup = dict(zip(results_df['lookup_key'], results_df['Distance_to_River_m']))
    has_rivers_lookup = dict(zip(results_df['lookup_key'], results_df['Has_Matching_Rivers']))
    river_count_lookup = dict(zip(results_df['lookup_key'], results_df['River_Count']))
    is_min_lookup = dict(zip(results_df['lookup_key'], results_df['Is_Min_Distance']))
    min_dist_lookup = dict(zip(results_df['lookup_key'], results_df['Min_Distance_m']))
    
    v1v2_with_distances['Distance_m'] = v1v2_with_distances['lookup_key'].map(distance_lookup)
    v1v2_with_distances['Has_Rivers'] = v1v2_with_distances['lookup_key'].map(has_rivers_lookup)
    v1v2_with_distances['River_Count'] = v1v2_with_distances['lookup_key'].map(river_count_lookup)
    v1v2_with_distances['Is_Min_Dist'] = v1v2_with_distances['lookup_key'].map(is_min_lookup)
    v1v2_with_distances['Min_Dist_m'] = v1v2_with_distances['lookup_key'].map(min_dist_lookup)
    
    # Remove temporary lookup column
    v1v2_with_distances = v1v2_with_distances.drop('lookup_key', axis=1)
    
    # Export to shapefile
    v1v2_shapefile_path = get_output_path('v1v2_sites_with_distances_shp')
    v1v2_with_distances.to_file(v1v2_shapefile_path)
    print(f"- V1/V2 site-GVFK combinations with distances: {v1v2_shapefile_path}")
    
    # Create site-level summary (focusing on final minimum distances)
    if len(valid_results) > 0:
        # Get all minimum distance entries and deduplicate (same fix as above)
        min_distance_entries = valid_results[valid_results['Is_Min_Distance'] == True].copy()
        final_distances_unique = (min_distance_entries
                                 .sort_values(['Lokalitet_ID', 'GVFK'])
                                 .groupby('Lokalitet_ID')
                                 .first()
                                 .reset_index())
        
        final_distances_clean = final_distances_unique[['Lokalitet_ID', 'GVFK', 'Site_Type', 'Distance_to_River_m']].copy()
        final_distances_clean.columns = ['Lokalitet_ID', 'Closest_GVFK', 'Site_Type', 'Final_Distance_m']
        
        # Add count of total GVFKs affected per site
        gvfk_counts = valid_results.groupby('Lokalitet_ID').size().reset_index()
        gvfk_counts.columns = ['Lokalitet_ID', 'Total_GVFKs_Affected']
        final_distances_clean = final_distances_clean.merge(gvfk_counts, on='Lokalitet_ID', how='left')
        
        final_distances_clean.to_csv(get_output_path('step4_site_level_summary'), index=False)
        print(f"- Site-level summary (final distances): {get_output_path('step4_site_level_summary')}")

def _create_and_save_interactive_map(v1v2_combined, rivers_with_contact, valid_results):
    """Create interactive map visualization using sampled data."""
    
    print(f"\nCreating interactive map visualization...")
    
    # Sample data for visualization - aim for ~1000 sites across Denmark
    total_sites = valid_results['Lokalitet_ID'].nunique()
    if total_sites <= 1000:
        # Use all sites if we have 1000 or fewer
        sampled_site_ids = valid_results['Lokalitet_ID'].unique()
    else:
        # Sample ~1000 sites randomly
        sampled_site_ids = np.random.choice(
            valid_results['Lokalitet_ID'].unique(), 
            size=1000, 
            replace=False
        )
    
    # Get ALL distance calculations for the sampled sites
    sampled_results = valid_results[valid_results['Lokalitet_ID'].isin(sampled_site_ids)].copy()
    
    print(f"Sampled {len(sampled_site_ids)} sites with {len(sampled_results)} total distance calculations")
    
    # Get GVFK polygons for visualization
    gvf = gpd.read_file(GRUNDVAND_PATH)
    sampled_gvfks = set(sampled_results['GVFK'].unique())
    relevant_gvfk_polygons = gvf[gvf['Navn'].isin(sampled_gvfks)]
    
    # Add distance data back to the combined data for mapping
    v1v2_with_distances = v1v2_combined.copy()
    
    # Create a lookup for distance data (using lokalitet + GVFK as key)
    lookup_data = {}
    for _, row in sampled_results.iterrows():
        key = f"{row['Lokalitet_ID']}_{row['GVFK']}"
        lookup_data[key] = {
            'Distance_m': row['Distance_to_River_m'],
            'Is_Min_Dist': row['Is_Min_Distance'],
            'Min_Dist_m': row.get('Min_Distance_m', row['Distance_to_River_m'])
        }
    
    # Apply lookup to combined data
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
        # Import and use the interactive map creation function
        try:
            from create_interactive_map import create_map
            create_map(sampled_combinations, rivers_with_contact, sampled_results, relevant_gvfk_polygons)
        except ImportError:
            print("Interactive map module not found. Skipping map creation.") 