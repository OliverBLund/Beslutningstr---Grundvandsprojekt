"""
Step 3: Find GVFKs with river contact that have V1 and/or V2 sites.

This step uses a hybrid CSV+shapefile approach to preserve one-to-many site-GVFK
relationships while maintaining accurate spatial geometries. It includes proper
deduplication to ensure each lokalitet-GVFK combination appears only once.
"""

import geopandas as gpd
import pandas as pd
import warnings
from shapely.errors import ShapelyDeprecationWarning
from config import (
    V1_CSV_PATH, V2_CSV_PATH, V1_SHP_PATH, V2_SHP_PATH,
    get_output_path, ensure_results_directory, GRUNDVAND_PATH
)

# Suppress shapely deprecation warnings
warnings.filterwarnings("ignore", category=ShapelyDeprecationWarning)

def run_step3(rivers_gvfk):
    """
    Execute Step 3: Find GVFKs with river contact that have V1 and/or V2 sites with active contaminations.
    
    Only includes sites with documented contamination substances (Lokalitetensstoffer),
    ensuring focus on locations with actual contamination risk.
    
    Args:
        rivers_gvfk (list): List of GVFK names with river contact from Step 2
    
    Returns:
        tuple: (gvfk_with_v1v2_names_set, v1v2_combined_geodataframe)
    """
    print("Step 3: Finding GVFKs with V1/V2 sites (active contaminations only)")
    
    # Ensure output directory exists
    ensure_results_directory()
    
    # Load CSV files with complete site-GVFK relationships
    v1_csv = pd.read_csv(V1_CSV_PATH)
    
    # Filter to only sites with active contaminations (documented contamination substances)
    if 'Lokalitetensstoffer' in v1_csv.columns:
        v1_csv_before = len(v1_csv)
        v1_csv = v1_csv.dropna(subset=['Lokalitetensstoffer'])
        v1_csv = v1_csv[v1_csv['Lokalitetensstoffer'].str.strip() != '']  # Remove empty strings
        print(f"V1 sites with contamination: {len(v1_csv)} (filtered from {v1_csv_before})")
    else:
        raise ValueError("'Lokalitetensstoffer' column not found in V1 CSV")
    
    v2_csv = pd.read_csv(V2_CSV_PATH)
    
    # Filter to only sites with active contaminations (documented contamination substances)
    if 'Lokalitetensstoffer' in v2_csv.columns:
        v2_csv_before = len(v2_csv)
        v2_csv = v2_csv.dropna(subset=['Lokalitetensstoffer'])
        v2_csv = v2_csv[v2_csv['Lokalitetensstoffer'].str.strip() != '']  # Remove empty strings
        print(f"V2 sites with contamination: {len(v2_csv)} (filtered from {v2_csv_before})")
    else:
        raise ValueError("'Lokalitetensstoffer' column not found in V2 CSV")
    
    if v1_csv.empty and v2_csv.empty:
        raise ValueError("No sites with contamination found in V1 or V2 data")
    
    # Load shapefile geometries and dissolve by locality
    locality_col = None
    
    # Process V1 geometries
    v1_shp = gpd.read_file(V1_SHP_PATH)
    
    # Find locality ID column
    for col in ['Lokalitet_', 'Lokalitets', 'Lokalitetsnr', 'LokNr']:
        if col in v1_shp.columns:
            locality_col = col
            break
    
    if locality_col is None:
        raise ValueError("No locality column found in V1 shapefile")
    
    # Dissolve V1 geometries by locality to handle multipolygons
    v1_geom = v1_shp.dissolve(by=locality_col, as_index=False)
    print(f"V1 geometries: {len(v1_geom)} unique localities")
    
    # Process V2 geometries
    v2_shp = gpd.read_file(V2_SHP_PATH)
    
    # Dissolve V2 geometries by locality
    v2_geom = v2_shp.dissolve(by=locality_col, as_index=False)
    print(f"V2 geometries: {len(v2_geom)} unique localities")
    
    # Process V1 data
    v1_combined_list = []
    if not v1_csv.empty and not v1_geom.empty:
        v1_combined_list = _process_v1v2_data(
            v1_csv, v1_geom, rivers_gvfk, locality_col, 'V1'
        )
    
    # Process V2 data
    v2_combined_list = []
    if not v2_csv.empty and not v2_geom.empty:
        v2_combined_list = _process_v1v2_data(
            v2_csv, v2_geom, rivers_gvfk, locality_col, 'V2'
        )
    
    # Combine and deduplicate V1 and V2 results
    v1v2_combined = _combine_and_deduplicate_v1v2(v1_combined_list, v2_combined_list)
    
    # Get unique GVFKs with V1/V2 sites
    gvfk_with_v1v2_names = set()
    if not v1v2_combined.empty:
        gvfk_with_v1v2_names = set(v1v2_combined['Navn'].unique())
    
    # Generate summary statistics and save results
    _save_step3_results(v1v2_combined, gvfk_with_v1v2_names)
    
    return gvfk_with_v1v2_names, v1v2_combined

def _process_v1v2_data(csv_data, geom_data, rivers_gvfk, locality_col, site_type):
    """
    Process V1 or V2 data by combining CSV relationships with dissolved geometries.
    
    Args:
        csv_data (DataFrame): CSV file with site-GVFK relationships
        geom_data (GeoDataFrame): Dissolved geometries by locality
        rivers_gvfk (list): List of GVFK names with river contact
        locality_col (str): Name of locality column
        site_type (str): 'V1' or 'V2'
    
    Returns:
        list: List containing processed GeoDataFrame if successful, empty list otherwise
    """
    # Standardize locality column name (CSV uses 'Lokalitetsnr', we need 'Lokalitet_')
    if 'Lokalitetsnr' in csv_data.columns and 'Lokalitet_' not in csv_data.columns:
        csv_data = csv_data.rename(columns={'Lokalitetsnr': 'Lokalitet_'})
    
    # Filter CSV to only GVFKs with river contact
    rivers_gvfk_set = set(rivers_gvfk)
    filtered_csv = csv_data[csv_data['Navn'].isin(rivers_gvfk_set)].copy()
    print(f"{site_type} sites in river-contact GVFKs: {len(filtered_csv)}")
    
    if filtered_csv.empty:
        return []
    
    # Deduplicate by lokalitet-GVFK combination before processing
    unique_csv = filtered_csv.drop_duplicates(subset=['Lokalitet_', 'Navn']).copy()
    print(f"{site_type} unique lokalitet-GVFK combinations: {len(unique_csv)}")
    
    # Add site type column
    unique_csv['Lokalitete'] = site_type
    
    # Preserve important columns for Step 5 (if they exist)
    step5_columns = ['Lokalitetensbranche', 'Lokalitetensaktivitet', 'Lokalitetensstoffer', 
                     'Lokalitetsnavn', 'Lokalitetetsforureningsstatus', 'Regionsnavn', 'Kommunenavn']
    available_step5_columns = [col for col in step5_columns if col in unique_csv.columns]
    
    # Join with dissolved geometries
    csv_with_geom = unique_csv.merge(
        geom_data[[locality_col, 'geometry']], 
        left_on='Lokalitet_', 
        right_on=locality_col, 
        how='inner'
    )
    
    if not csv_with_geom.empty:
        combined_gdf = gpd.GeoDataFrame(csv_with_geom, crs=geom_data.crs)
        print(f"{site_type} site-GVFK combinations with geometry: {len(combined_gdf)}")
        return [combined_gdf]
    
    return []

def _combine_and_deduplicate_v1v2(v1_combined_list, v2_combined_list):
    """
    Combine V1 and V2 results and perform final deduplication.
    
    Args:
        v1_combined_list (list): List of V1 GeoDataFrames
        v2_combined_list (list): List of V2 GeoDataFrames
    
    Returns:
        GeoDataFrame: Combined and deduplicated V1/V2 data
    """
    # Combine V1 and V2 results
    if not v1_combined_list and not v2_combined_list:
        return gpd.GeoDataFrame()
    
    all_combined = []
    if v1_combined_list:
        all_combined.extend(v1_combined_list)
    if v2_combined_list:
        all_combined.extend(v2_combined_list)
    
    v1v2_combined_raw = pd.concat(all_combined, ignore_index=True)
    print(f"Combined V1 and V2 data: {len(v1v2_combined_raw)} total rows")
    
    # Final deduplication to handle sites in both V1 and V2
    duplicates = v1v2_combined_raw.groupby(['Lokalitet_', 'Navn']).size()
    duplicate_combinations = duplicates[duplicates > 1]
    
    if len(duplicate_combinations) > 0:
        print(f"Sites in both V1 and V2: {len(duplicate_combinations)} combinations")
        
        # For duplicate combinations, keep one record but update site type to 'V1 og V2'
        v1v2_deduped_list = []
        
        for (lokalitet_id, gvfk_name), count in duplicates.items():
            subset = v1v2_combined_raw[
                (v1v2_combined_raw['Lokalitet_'] == lokalitet_id) & 
                (v1v2_combined_raw['Navn'] == gvfk_name)
            ]
            
            if count > 1:
                # Take first record and update site type
                first_record = subset.iloc[0:1].copy()
                first_record['Lokalitete'] = 'V1 og V2'
                v1v2_deduped_list.append(first_record)
            else:
                # Keep single record as is
                v1v2_deduped_list.append(subset)
        
        v1v2_combined = pd.concat(v1v2_deduped_list, ignore_index=True)
        
    else:
        v1v2_combined = v1v2_combined_raw.copy()
    
    print(f"Unique lokalitet-GVFK combinations: {len(v1v2_combined)}")
    
    # Verify no duplicates remain
    final_check = v1v2_combined.groupby(['Lokalitet_', 'Navn']).size()
    remaining_duplicates = (final_check > 1).sum()
    if remaining_duplicates > 0:
        print(f"ERROR: {remaining_duplicates} duplicate combinations still remain!")
    
    return v1v2_combined

def _save_step3_results(v1v2_combined, gvfk_with_v1v2_names):
    """
    Save Step 3 results and generate summary statistics.
    
    Args:
        v1v2_combined (GeoDataFrame): Combined and deduplicated V1/V2 data
        gvfk_with_v1v2_names (set): Set of GVFK names with V1/V2 sites
    """
    if v1v2_combined.empty:
        print("No V1/V2 sites found with river contact.")
        return
    
    # Summary statistics
    unique_sites = v1v2_combined['Lokalitet_'].nunique()
    total_site_gvfk_combinations = len(v1v2_combined)
    
    print(f"Unique V1/V2 sites: {unique_sites}")
    print(f"Site-GVFK combinations: {total_site_gvfk_combinations}")
    print(f"GVFKs with V1/V2 sites: {len(gvfk_with_v1v2_names)}")
    
    # Count by site type
    if 'Lokalitete' in v1v2_combined.columns:
        # Count unique sites by type (not site-GVFK combinations)
        site_type_counts = v1v2_combined.drop_duplicates('Lokalitet_')['Lokalitete'].value_counts()
        for site_type, count in site_type_counts.items():
            print(f"- {site_type} sites: {count}")
    
    # Save V1/V2 site-GVFK combinations
    v1v2_sites_path = get_output_path('step3_v1v2_sites')
    v1v2_combined.to_file(v1v2_sites_path)
    print(f"Saved V1/V2 site-GVFK combinations: {len(v1v2_combined)} records")
    
    # Save GVFK polygons that contain V1/V2 sites
    gvf = gpd.read_file(GRUNDVAND_PATH)
    gvfk_with_v1v2_polygons = gvf[gvf['Navn'].isin(gvfk_with_v1v2_names)]
    
    gvfk_polygons_path = get_output_path('step3_gvfk_polygons')
    gvfk_with_v1v2_polygons.to_file(gvfk_polygons_path)
    print(f"Saved GVFK polygons: {len(gvfk_with_v1v2_polygons)} records")
    
    # Save CSV with detailed relationships
    csv_output = v1v2_combined.drop('geometry', axis=1) if 'geometry' in v1v2_combined.columns else v1v2_combined
    relationships_path = get_output_path('step3_relationships')
    csv_output.to_csv(relationships_path, index=False)
    print(f"Saved detailed relationships: {len(csv_output)} records")

if __name__ == "__main__":
    # Allow running this step independently
    # Note: This requires results from Step 2
    print("This step requires results from Step 2. Run main_workflow.py instead.")
    print("To test independently, provide a list of rivers_gvfk manually.") 