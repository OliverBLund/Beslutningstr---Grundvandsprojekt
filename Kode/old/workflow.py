import geopandas as gpd
import pandas as pd
import numpy as np
import os
import warnings
from shapely.errors import ShapelyDeprecationWarning
import folium
from shapely.geometry import LineString
import random
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
import seaborn as sns

# Suppress shapely deprecation warnings
warnings.filterwarnings("ignore", category=ShapelyDeprecationWarning)

# Define paths to the input files
BASE_PATH = os.path.join(".", "Data", "shp files")
GRUNDVAND_PATH = os.path.join(BASE_PATH, "VP3Genbesøg_grundvand_geometri.shp")
RIVERS_PATH = os.path.join(BASE_PATH, "Rivers_gvf_rev20230825_kontakt.shp")

# Updated paths for CSV and shapefile combinations
V1_CSV_PATH = os.path.join(BASE_PATH, "V1V2_new", "v1_gvfk_forurening_csv.csv")
V2_CSV_PATH = os.path.join(BASE_PATH, "V1V2_new", "v2_gvfk_forurening.csv")
V1_SHP_PATH = os.path.join(BASE_PATH, "V1FLADER.shp")
V2_SHP_PATH = os.path.join(BASE_PATH, "V2FLADER.shp")

# Create output directory
RESULTS_PATH = os.path.join(".", "Resultater")
os.makedirs(RESULTS_PATH, exist_ok=True)

def step1_count_total_gvfk():
    """
    Step 1: Count total unique groundwater aquifers (gvfk) in the base file.
    """
    print("Step 1: Counting total unique groundwater aquifers (gvfk)")
    
    # Read the base shapefile
    gvf = gpd.read_file(GRUNDVAND_PATH)
    
    # Count unique gvfk based on ID column
    unique_gvfk = gvf["Navn"].nunique()
    print(f"Total number of unique groundwater aquifers (gvfk): {unique_gvfk}")
    
    # Save all GVFK for visualization
    gvf.to_file(os.path.join(RESULTS_PATH, "step1_all_gvfk.shp"))
    print(f"Saved all GVFK to: {os.path.join(RESULTS_PATH, 'step1_all_gvfk.shp')}")
    
    return gvf, unique_gvfk

def step2_count_gvfk_with_river_contact():
    """
    Step 2: Count how many gvfk are in contact with targeted rivers.
    """
    print("\nStep 2: Counting gvfk in contact with targeted rivers")
    
    # Read the rivers contact shapefile
    rivers = gpd.read_file(RIVERS_PATH)
    
    # Count unique gvfk in the GVForekom column
    rivers_gvfk = [gvf for gvf in rivers["GVForekom"].unique() if gvf is not None and isinstance(gvf, str)]
    unique_rivers_gvfk = len(rivers_gvfk)
    print(f"Number of unique gvfk in contact with targeted rivers: {unique_rivers_gvfk}")
    
    # Get the base GVFK file and filter to only those with river contact
    gvf = gpd.read_file(GRUNDVAND_PATH)
    gvf_with_rivers = gvf[gvf["Navn"].isin(rivers_gvfk)]
    print(f"Found {len(gvf_with_rivers)} gvfk geometries with river contact")
    
    # Save GVFK with river contact for visualization
    gvf_with_rivers.to_file(os.path.join(RESULTS_PATH, "step2_gvfk_with_rivers.shp"))
    print(f"Saved GVFK with river contact to: {os.path.join(RESULTS_PATH, 'step2_gvfk_with_rivers.shp')}")
    
    return rivers_gvfk, unique_rivers_gvfk, gvf_with_rivers

def step3_count_gvfk_with_v1v2(rivers_gvfk):
    """
    Step 3: Find GVFKs with river contact that have V1 and/or V2 sites.
    Uses CSV files to preserve one-to-many site-GVFK relationships,
    combined with dissolved shapefile geometries for spatial data.
    """
    print("\nStep 3: Finding GVFKs with river contact that have V1 and/or V2 sites")
    print("Using hybrid CSV+shapefile approach to preserve site-GVFK relationships")
    
    # Load CSV files with complete site-GVFK relationships
    print("Loading V1 and V2 CSV files for relationships...")
    try:
        v1_csv = pd.read_csv(V1_CSV_PATH)
        print(f"V1 CSV loaded: {len(v1_csv)} site-GVFK combinations")
    except Exception as e:
        print(f"Error loading V1 CSV: {e}")
        v1_csv = pd.DataFrame()
    
    try:
        v2_csv = pd.read_csv(V2_CSV_PATH)
        print(f"V2 CSV loaded: {len(v2_csv)} site-GVFK combinations")
    except Exception as e:
        print(f"Error loading V2 CSV: {e}")
        v2_csv = pd.DataFrame()
    
    if v1_csv.empty and v2_csv.empty:
        print("No CSV data found. Cannot proceed.")
        return set(), gpd.GeoDataFrame()
    
    # Load shapefile geometries and dissolve by locality
    print("Loading and dissolving shapefile geometries by locality...")
    try:
        v1_shp = gpd.read_file(V1_SHP_PATH)
        print(f"V1 shapefile loaded: {len(v1_shp)} polygons")
        
        # Find locality ID column
        locality_col = None
        for col in ['Lokalitet_', 'Lokalitets', 'Lokalitetsnr', 'LokNr']:
            if col in v1_shp.columns:
                locality_col = col
                break
        
        if locality_col is None:
            print("ERROR: No locality column found in V1 shapefile")
            return set(), gpd.GeoDataFrame()
        
        # Dissolve V1 geometries by locality to handle multipolygons
        v1_geom = v1_shp.dissolve(by=locality_col, as_index=False)
        print(f"V1 geometries dissolved: {len(v1_geom)} unique localities")
        
    except Exception as e:
        print(f"Error loading V1 shapefile: {e}")
        v1_geom = gpd.GeoDataFrame()
    
    try:
        v2_shp = gpd.read_file(V2_SHP_PATH)
        print(f"V2 shapefile loaded: {len(v2_shp)} polygons")
        
        # Dissolve V2 geometries by locality
        v2_geom = v2_shp.dissolve(by=locality_col, as_index=False)
        print(f"V2 geometries dissolved: {len(v2_geom)} unique localities")
        
    except Exception as e:
        print(f"Error loading V2 shapefile: {e}")
        v2_geom = gpd.GeoDataFrame()
    
    # Process V1 data
    v1_combined_list = []
    if not v1_csv.empty and not v1_geom.empty:
        print("Combining V1 CSV relationships with dissolved geometries...")
        
        # Filter V1 CSV to only GVFKs with river contact
        rivers_gvfk_set = set(rivers_gvfk)
        v1_filtered = v1_csv[v1_csv['Navn'].isin(rivers_gvfk_set)].copy()
        print(f"V1 site-GVFK combinations in river-contact GVFKs: {len(v1_filtered)}")
        
        if not v1_filtered.empty:
            # IMPORTANT: Deduplicate by lokalitet-GVFK combination before processing
            print(f"Deduplicating V1 by unique lokalitet-GVFK combinations...")
            v1_unique = v1_filtered.drop_duplicates(subset=['Lokalitet_', 'Navn']).copy()
            print(f"V1 after deduplication: {len(v1_unique)} unique lokalitet-GVFK combinations (reduced from {len(v1_filtered)})")
            
            # Add site type column
            v1_unique['Lokalitete'] = 'V1'
            
            # Join with dissolved geometries
            v1_with_geom = v1_unique.merge(v1_geom[[locality_col, 'geometry']], 
                                         left_on='Lokalitet_', right_on=locality_col, how='inner')
            
            if not v1_with_geom.empty:
                v1_combined_gdf = gpd.GeoDataFrame(v1_with_geom, crs=v1_geom.crs)
                v1_combined_list.append(v1_combined_gdf)
                print(f"V1 site-GVFK combinations with geometry: {len(v1_combined_gdf)}")
    
    # Process V2 data
    v2_combined_list = []
    if not v2_csv.empty and not v2_geom.empty:
        print("Combining V2 CSV relationships with dissolved geometries...")
        
        # Filter V2 CSV to only GVFKs with river contact
        v2_filtered = v2_csv[v2_csv['Navn'].isin(rivers_gvfk_set)].copy()
        print(f"V2 site-GVFK combinations in river-contact GVFKs: {len(v2_filtered)}")
        
        if not v2_filtered.empty:
            # IMPORTANT: Deduplicate by lokalitet-GVFK combination before processing
            print(f"Deduplicating V2 by unique lokalitet-GVFK combinations...")
            v2_unique = v2_filtered.drop_duplicates(subset=['Lokalitet_', 'Navn']).copy()
            print(f"V2 after deduplication: {len(v2_unique)} unique lokalitet-GVFK combinations (reduced from {len(v2_filtered)})")
            
            # Add site type column
            v2_unique['Lokalitete'] = 'V2'
            
            # Join with dissolved geometries
            v2_with_geom = v2_unique.merge(v2_geom[[locality_col, 'geometry']], 
                                         left_on='Lokalitet_', right_on=locality_col, how='inner')
            
            if not v2_with_geom.empty:
                v2_combined_gdf = gpd.GeoDataFrame(v2_with_geom, crs=v2_geom.crs)
                v2_combined_list.append(v2_combined_gdf)
                print(f"V2 site-GVFK combinations with geometry: {len(v2_combined_gdf)}")
    
    # Combine V1 and V2 results
    if v1_combined_list or v2_combined_list:
        all_combined = []
        if v1_combined_list:
            all_combined.extend(v1_combined_list)
        if v2_combined_list:
            all_combined.extend(v2_combined_list)
        
        v1v2_combined_raw = pd.concat(all_combined, ignore_index=True)
        print(f"Combined V1 and V2 data: {len(v1v2_combined_raw)} total rows")
        
        # CRITICAL FIX: Final deduplication to handle sites in both V1 and V2
        print("Performing final deduplication of lokalitet-GVFK combinations...")
        
        # First, identify which sites appear in both V1 and V2 for same GVFK
        duplicates = v1v2_combined_raw.groupby(['Lokalitet_', 'Navn']).size()
        duplicate_combinations = duplicates[duplicates > 1]
        
        if len(duplicate_combinations) > 0:
            print(f"Found {len(duplicate_combinations)} lokalitet-GVFK combinations that appear in both V1 and V2")
            
            # For duplicate combinations, keep one record but update site type to 'V1 og V2'
            v1v2_deduped_list = []
            
            for (lokalitet_id, gvfk_name), count in duplicates.items():
                subset = v1v2_combined_raw[(v1v2_combined_raw['Lokalitet_'] == lokalitet_id) & 
                                         (v1v2_combined_raw['Navn'] == gvfk_name)]
                
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
            print("No duplicate lokalitet-GVFK combinations found")
            v1v2_combined = v1v2_combined_raw.copy()
        
        print(f"After final deduplication: {len(v1v2_combined)} unique lokalitet-GVFK combinations")
        
        # Verify no duplicates remain
        final_check = v1v2_combined.groupby(['Lokalitet_', 'Navn']).size()
        remaining_duplicates = (final_check > 1).sum()
        if remaining_duplicates > 0:
            print(f"ERROR: {remaining_duplicates} duplicate combinations still remain!")
        else:
            print("✓ All lokalitet-GVFK combinations are now unique")
            
    else:
        v1v2_combined = gpd.GeoDataFrame()
    
    # Get unique GVFKs with V1/V2 sites
    gvfk_with_v1v2_names = set()
    if not v1v2_combined.empty:
        gvfk_with_v1v2_names = set(v1v2_combined['Navn'].unique())
    
    # Summary statistics
    if not v1v2_combined.empty:
        unique_sites = v1v2_combined['Lokalitet_'].nunique()
        total_site_gvfk_combinations = len(v1v2_combined)
        
        print(f"\nSummary:")
        print(f"Unique V1/V2 sites (localities): {unique_sites}")
        print(f"Total site-GVFK combinations: {total_site_gvfk_combinations}")
        print(f"Average GVFKs per site: {total_site_gvfk_combinations/unique_sites:.1f}")
        print(f"GVFKs with V1/V2 sites: {len(gvfk_with_v1v2_names)}")
        
        # Count by site type
        if 'Lokalitete' in v1v2_combined.columns:
            # Count unique sites by type (not site-GVFK combinations)
            site_type_counts = v1v2_combined.drop_duplicates('Lokalitet_')['Lokalitete'].value_counts()
            print("\nUnique sites by type:")
            for site_type, count in site_type_counts.items():
                print(f"- {site_type}: {count}")
        
        # Save results
        v1v2_combined.to_file(os.path.join(RESULTS_PATH, "step3_v1v2_sites.shp"))
        print(f"\nSaved V1/V2 site-GVFK combinations to: {os.path.join(RESULTS_PATH, 'step3_v1v2_sites.shp')}")
        
        # Save GVFK polygons that contain V1/V2 sites
        gvf = gpd.read_file(GRUNDVAND_PATH)
        gvfk_with_v1v2_polygons = gvf[gvf['Navn'].isin(gvfk_with_v1v2_names)]
        gvfk_with_v1v2_polygons.to_file(os.path.join(RESULTS_PATH, "step3_gvfk_with_v1v2.shp"))
        print(f"Saved GVFK polygons with V1/V2 sites to: {os.path.join(RESULTS_PATH, 'step3_gvfk_with_v1v2.shp')}")
        
        # Save CSV with detailed relationships
        csv_output = v1v2_combined.drop('geometry', axis=1) if 'geometry' in v1v2_combined.columns else v1v2_combined
        csv_output.to_csv(os.path.join(RESULTS_PATH, "step3_site_gvfk_relationships.csv"), index=False)
        print(f"Saved detailed site-GVFK relationships to: {os.path.join(RESULTS_PATH, 'step3_site_gvfk_relationships.csv')}")
    
    return gvfk_with_v1v2_names, v1v2_combined

def step4_calculate_distances_to_rivers(v1v2_combined):
    """
    Step 4: Calculate distances between V1/V2 sites and river segments with contact.
    Now handles one-to-many site-GVFK relationships: calculates distances for each
    lokalitet-GVFK combination separately.
    """
    print("\nStep 4: Calculating distances between V1/V2 sites and river segments")
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
        
        # Site-level analysis
        print(f"\nPer-site analysis:")
        site_distance_stats = valid_results.groupby('Lokalitet_ID').agg({
            'Distance_to_River_m': ['min', 'max', 'mean', 'count'],
            'GVFK': lambda x: list(x),
            'Site_Type': 'first'
        }).reset_index()
        
        site_distance_stats.columns = ['Lokalitet_ID', 'Min_Distance_m', 'Max_Distance_m', 'Mean_Distance_m', 'GVFK_Count', 'Associated_GVFKs', 'Site_Type']
        
        print(f"Sites with multiple GVFK distances: {(site_distance_stats['GVFK_Count'] > 1).sum()}")
        if (site_distance_stats['GVFK_Count'] > 1).any():
            multi_gvfk_sites = site_distance_stats[site_distance_stats['GVFK_Count'] > 1]
            print(f"Average GVFKs per multi-GVFK site: {multi_gvfk_sites['GVFK_Count'].mean():.1f}")
            print(f"Max GVFKs for a single site: {multi_gvfk_sites['GVFK_Count'].max()}")
            
            # Show range of distances for multi-GVFK sites
            distance_ranges = multi_gvfk_sites['Max_Distance_m'] - multi_gvfk_sites['Min_Distance_m']
            print(f"Average distance range for multi-GVFK sites: {distance_ranges.mean():.1f}m")
            print(f"Maximum distance range for a single site: {distance_ranges.max():.1f}m")
    
    # Save results
    results_df.to_csv(os.path.join(RESULTS_PATH, "step4_distance_results.csv"), index=False)
    valid_results.to_csv(os.path.join(RESULTS_PATH, "step4_valid_distances.csv"), index=False)
    
    print(f"\nResults saved to:")
    print(f"- All results: {os.path.join(RESULTS_PATH, 'step4_distance_results.csv')}")
    print(f"- Valid distances only: {os.path.join(RESULTS_PATH, 'step4_valid_distances.csv')}")
    
    # Create and save final distances for risk assessment (minimum per site)
    if len(valid_results) > 0:
        final_distances = valid_results[valid_results['Is_Min_Distance'] == True].copy()
        final_distances_clean = final_distances[['Lokalitet_ID', 'GVFK', 'Site_Type', 'Distance_to_River_m', 'Min_Distance_m']].copy()
        final_distances_clean.columns = ['Lokalitet_ID', 'Closest_GVFK', 'Site_Type', 'Final_Distance_m', 'Final_Distance_m_Verify']
        final_distances_clean = final_distances_clean.drop('Final_Distance_m_Verify', axis=1)
        
        # Add count of total GVFKs affected per site
        gvfk_counts = valid_results.groupby('Lokalitet_ID').size().reset_index()
        gvfk_counts.columns = ['Lokalitet_ID', 'Total_GVFKs_Affected']
        final_distances_clean = final_distances_clean.merge(gvfk_counts, on='Lokalitet_ID', how='left')
        
        # Add list of all affected GVFKs per site
        all_gvfks = valid_results.groupby('Lokalitet_ID')['GVFK'].apply(lambda x: '; '.join(sorted(x.unique()))).reset_index()
        all_gvfks.columns = ['Lokalitet_ID', 'All_Affected_GVFKs']
        final_distances_clean = final_distances_clean.merge(all_gvfks, on='Lokalitet_ID', how='left')
        
        final_distances_clean.to_csv(os.path.join(RESULTS_PATH, "step4_final_distances_for_risk_assessment.csv"), index=False)
        print(f"- Final distances for risk assessment: {os.path.join(RESULTS_PATH, 'step4_final_distances_for_risk_assessment.csv')}")
        
        # Create unique lokalitet distances file for visualizations
        # This contains one row per lokalitet with the minimum distance and associated data
        unique_distances = final_distances_clean.copy()
        unique_distances = unique_distances.rename(columns={
            'Lokalitet_ID': 'Lokalitetsnr',
            'Final_Distance_m': 'Distance_to_River_m',
            'Closest_GVFK': 'GVFK'
        })
        
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
            unique_distances.to_csv(os.path.join(RESULTS_PATH, "unique_lokalitet_distances.csv"), index=False)
            print(f"- Unique lokalitet distances (for visualizations): {os.path.join(RESULTS_PATH, 'unique_lokalitet_distances.csv')}")
            
            # Save shapefile for GIS analysis
            unique_gdf.to_file(os.path.join(RESULTS_PATH, "unique_lokalitet_distances.shp"))
            print(f"- Unique lokalitet distances (shapefile): {os.path.join(RESULTS_PATH, 'unique_lokalitet_distances.shp')}")
        else:
            # Fallback - save CSV only
            unique_distances.to_csv(os.path.join(RESULTS_PATH, "unique_lokalitet_distances.csv"), index=False)
            print(f"- Unique lokalitet distances (CSV only): {os.path.join(RESULTS_PATH, 'unique_lokalitet_distances.csv')}")
    
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
    v1v2_shapefile_path = os.path.join(RESULTS_PATH, "v1v2_sites_with_distances.shp")
    v1v2_with_distances.to_file(v1v2_shapefile_path)
    print(f"- V1/V2 site-GVFK combinations with distances: {v1v2_shapefile_path}")
    
    # Create site-level summary (focusing on final minimum distances)
    if len(valid_results) > 0:
        site_summary = final_distances_clean.copy()
        site_summary.to_csv(os.path.join(RESULTS_PATH, "step4_site_level_summary.csv"), index=False)
        print(f"- Site-level summary (final distances): {os.path.join(RESULTS_PATH, 'step4_site_level_summary.csv')}")
    
    # Create interactive visualization using a sample of the data
    if len(valid_results) > 0:
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
        
        # Get corresponding site geometries
        sampled_combinations = v1v2_with_distances[
            v1v2_with_distances['Lokalitet_'].isin(sampled_results['Lokalitet_ID']) &
            v1v2_with_distances['Navn'].isin(sampled_results['GVFK'])
        ]
        
        if not sampled_combinations.empty:
            create_interactive_map(sampled_combinations, rivers_with_contact, sampled_results, 'Lokalitet_', relevant_gvfk_polygons)
    
    return results_df

def create_interactive_map(v1v2_with_distances, rivers_with_contact, valid_results, id_column, gvfk_polygons):
    """
    Create an interactive map showing GVFK polygons, V1/V2 sites, river segments, and distance connections.
    Now handles one-to-many site-GVFK relationships.
    """
    try:
        print("Creating interactive map...")
        
        # Convert to Web Mercator for better distance visualization
        v1v2_web = v1v2_with_distances.to_crs('EPSG:4326')
        rivers_web = rivers_with_contact.to_crs('EPSG:4326')
        gvfk_web = gvfk_polygons.to_crs('EPSG:4326')
        
        print(f"Using {len(valid_results)} site-GVFK combinations for visualization")
        
        if v1v2_web.empty:
            print("No valid sites for mapping")
            return
            
        # Get bounds for map centering
        bounds = v1v2_web.total_bounds
        center_lat = (bounds[1] + bounds[3]) / 2
        center_lon = (bounds[0] + bounds[2]) / 2
        
        # Create folium map
        m = folium.Map(
            location=[center_lat, center_lon],
            zoom_start=10,
            tiles='OpenStreetMap'
        )
        
        # Add GVFK polygons to map first (as background)
        sampled_gvfks = set(v1v2_web['Navn'].unique())
        relevant_gvfk_web = gvfk_web[gvfk_web['Navn'].isin(sampled_gvfks)]
        
        print(f"Adding {len(relevant_gvfk_web)} GVFK polygons for visualization")
        
        for idx, gvfk in relevant_gvfk_web.iterrows():
            gvfk_name = gvfk.get('Navn', 'Unknown')
            
            popup_text = f"""
            <b>GVFK Polygon</b><br>
            <b>GVFK:</b> {gvfk_name}<br>
            <b>Type:</b> Groundwater Body
            """
            
            folium.GeoJson(
                gvfk.geometry.__geo_interface__,
                style_function=lambda x: {
                    'fillColor': 'lightgray',
                    'color': 'black',
                    'weight': 1,
                    'fillOpacity': 0.3
                },
                popup=folium.Popup(popup_text, max_width=200)
            ).add_to(m)
        
        # Add V1/V2 sites to map (group by site to avoid overlapping identical geometries)
        unique_sites = v1v2_web.drop_duplicates(subset=['Lokalitet_'])
        
        for idx, site in unique_sites.iterrows():
            site_id = site['Lokalitet_']
            site_type = site.get('Lokalitete', 'Unknown')
            
            # Get all GVFKs for this site and their distances
            site_data = v1v2_web[v1v2_web['Lokalitet_'] == site_id]
            site_gvfks = sorted(list(set(site_data['Navn'].tolist())))  # Remove duplicates and sort
            site_distances = sorted(site_data['Distance_m'].dropna().tolist())  # Sort distances
            
            # Get minimum distance information
            min_distance = site_data['Min_Dist_m'].iloc[0] if 'Min_Dist_m' in site_data.columns and not site_data['Min_Dist_m'].isna().all() else None
            is_min_flags = site_data['Is_Min_Dist'].tolist() if 'Is_Min_Dist' in site_data.columns else []
            
            # Color by site type
            if 'V1 og V2' in site_type:
                color = 'purple'
            elif 'V1' in site_type:
                color = 'red'
            elif 'V2' in site_type:
                color = 'blue'
            else:
                color = 'gray'
            
            # Create enhanced popup with site info
            min_dist_text = f"{min_distance:.1f}m" if min_distance is not None else "N/A"
            popup_text = f"""
            <b>Site ID:</b> {site_id}<br>
            <b>Type:</b> {site_type}<br>
            <b>Associated GVFKs:</b> {len(site_gvfks)}<br>
            <b>GVFK Names:</b> {', '.join(site_gvfks[:3])}{('...' if len(site_gvfks) > 3 else '')}<br>
            <b>Distance Range:</b> {site_distances[0]:.1f}m - {site_distances[-1]:.1f}m<br>
            <b><span style="color: red;">MINIMUM Distance:</span></b> <b>{min_dist_text}</b>
            """
            
            # Add polygon to map
            folium.GeoJson(
                site.geometry.__geo_interface__,
                style_function=lambda x, color=color: {
                    'fillColor': color,
                    'color': color,
                    'weight': 2,
                    'fillOpacity': 0.7
                },
                popup=folium.Popup(popup_text, max_width=300)
            ).add_to(m)
        
        # Add river segments for the same GVFKs
        sampled_gvfks = set(v1v2_web['Navn'].unique())
        relevant_rivers = rivers_web[rivers_web['GVForekom'].isin(sampled_gvfks)]
        
        print(f"Adding {len(relevant_rivers)} river segments for visualization")
        
        for idx, river in relevant_rivers.iterrows():
            gvfk = river.get('GVForekom', 'Unknown')
            
            popup_text = f"""
            <b>River Segment</b><br>
            <b>GVFK:</b> {gvfk}<br>
            <b>Contact:</b> {river.get('Kontakt', 'Unknown')}
            """
            
            folium.GeoJson(
                river.geometry.__geo_interface__,
                style_function=lambda x: {
                    'color': 'darkblue',
                    'weight': 3,
                    'opacity': 0.8
                },
                popup=folium.Popup(popup_text, max_width=200)
            ).add_to(m)
        
        # Add distance lines - show ALL distances with minimum highlighted
        print("Adding distance connection lines...")
        
        # Separate minimum and non-minimum distances
        min_distance_results = valid_results[valid_results['Is_Min_Distance'] == True].copy()
        non_min_distance_results = valid_results[valid_results['Is_Min_Distance'] == False].copy()
        
        print(f"Total distance calculations to show: {len(valid_results)}")
        print(f"- Minimum distances (highlighted): {len(min_distance_results)}")
        print(f"- Non-minimum distances (lighter): {len(non_min_distance_results)}")
        
        # Process ALL distance calculations (both minimum and non-minimum)
        all_distances_to_show = valid_results.copy()
        
        for idx, result in all_distances_to_show.iterrows():
            lokalitet_id = result['Lokalitet_ID']
            gvfk = result['GVFK']
            distance = result['Distance_to_River_m']
            is_minimum = result['Is_Min_Distance']
            
            # Get the site geometry for this specific combination
            site_combo = v1v2_web[
                (v1v2_web['Lokalitet_'] == lokalitet_id) & 
                (v1v2_web['Navn'] == gvfk)
            ]
            
            if site_combo.empty:
                continue
                
            site_geom = site_combo.iloc[0].geometry
            
            # Find the closest river segment in the same GVFK
            matching_rivers = relevant_rivers[relevant_rivers['GVForekom'] == gvfk]
            
            if not matching_rivers.empty:
                min_distance_calc = float('inf')
                closest_point_on_site = None
                closest_point_on_river = None
                
                for _, river in matching_rivers.iterrows():
                    # Calculate closest points between site and river
                    try:
                        distance_calc = site_geom.distance(river.geometry)
                        if distance_calc < min_distance_calc:
                            min_distance_calc = distance_calc
                            
                            # Get closest points
                            from shapely.ops import nearest_points
                            closest_points = nearest_points(site_geom, river.geometry)
                            closest_point_on_site = closest_points[0]
                            closest_point_on_river = closest_points[1]
                    except Exception as e:
                        continue
                
                # Add line connecting closest points
                if closest_point_on_site and closest_point_on_river:
                    line_coords = [
                        [closest_point_on_site.y, closest_point_on_site.x],
                        [closest_point_on_river.y, closest_point_on_river.x]
                    ]
                    
                    # Style based on whether this is the minimum distance
                    if is_minimum:
                        # Highlight minimum distances
                        line_color = 'red'
                        line_weight = 3
                        line_opacity = 1.0
                        popup_prefix = "<b>⭐ MINIMUM DISTANCE</b>"
                        label_style = 'font-size: 10pt; color: red; font-weight: bold; background-color: white; padding: 2px; border: 1px solid red;'
                        label_text = f'{distance:.0f}m MIN'
                    else:
                        # Non-minimum distances (lighter styling)
                        line_color = 'orange'
                        line_weight = 1
                        line_opacity = 0.6
                        popup_prefix = "Additional Distance"
                        label_style = 'font-size: 8pt; color: orange; background-color: white; padding: 1px; border: 1px solid orange;'
                        label_text = f'{distance:.0f}m'
                    
                    folium.PolyLine(
                        line_coords,
                        color=line_color,
                        weight=line_weight,
                        opacity=line_opacity,
                        popup=f"{popup_prefix}<br>Lokalitet: {lokalitet_id}<br>GVFK: {gvfk}<br>Distance: {distance:.1f}m"
                    ).add_to(m)
                    
                    # Add distance label at midpoint (only for minimum distances to avoid clutter)
                    if is_minimum:
                        mid_lat = (line_coords[0][0] + line_coords[1][0]) / 2
                        mid_lon = (line_coords[0][1] + line_coords[1][1]) / 2
                        
                        folium.Marker(
                            location=[mid_lat, mid_lon],
                            icon=folium.DivIcon(
                                html=f'<div style="{label_style}">{label_text}</div>',
                                icon_size=(60, 20),
                                icon_anchor=(30, 10)
                            )
                        ).add_to(m)
        
        # Add legend
        legend_html = '''
        <div style="position: fixed; 
                    bottom: 50px; left: 50px; width: 320px; height: 200px; 
                    background-color: white; border:2px solid grey; z-index:9999; 
                    font-size:12px; padding: 10px">
        <b>Legend</b><br>
        <i class="fa fa-square" style="color:lightgray"></i> GVFK Polygons<br>
        <i class="fa fa-circle" style="color:red"></i> V1 Sites<br>
        <i class="fa fa-circle" style="color:blue"></i> V2 Sites<br>
        <i class="fa fa-circle" style="color:purple"></i> V1 & V2 Sites<br>
        <i class="fa fa-minus" style="color:darkblue"></i> River Segments<br>
        <i class="fa fa-minus" style="color:red"></i> <b>⭐ MINIMUM Distance Lines</b><br>
        <i class="fa fa-minus" style="color:orange"></i> Additional Distance Lines<br>
        <small><b>Red lines:</b> Shortest pathway per site (critical for risk)<br>
        <b>Orange lines:</b> Other pathways through different GVFKs<br>
        Showing ~1000 sites across Denmark with ALL calculations.</small>
        </div>
        '''
        m.get_root().html.add_child(folium.Element(legend_html))
        
        # Save map
        map_path = os.path.join(RESULTS_PATH, "interactive_distance_map.html")
        m.save(map_path)
        print(f"Interactive map saved to: {map_path}")
        print(f"Open the file in a web browser to explore the distance calculations!")
        
    except Exception as e:
        print(f"Error creating interactive map: {e}")
        print("Continuing without map visualization...")


def main():
    """
    Run the simplified groundwater analysis workflow.
    """
    print("Starting simplified groundwater analysis workflow")
    print("=" * 60)
    
    # Step 1: Count total gvfk
    gvf, total_gvfk = step1_count_total_gvfk()
    
    # Step 2: Count gvfk with river contact
    rivers_gvfk, river_contact_count, gvf_with_rivers = step2_count_gvfk_with_river_contact()
    
    # Step 3: Count gvfk with river contact and V1/V2 sites
    gvfk_with_v1v2_names, v1v2_sites = step3_count_gvfk_with_v1v2(rivers_gvfk)
    
    # Step 4: Calculate distances between V1/V2 sites and river segments
    distance_results = step4_calculate_distances_to_rivers(v1v2_sites)
    
    # Summary of results
    print("\n" + "=" * 60)
    print("WORKFLOW SUMMARY")
    print("=" * 60)
    print(f"Total unique groundwater aquifers (gvfk): {total_gvfk}")
    print(f"GVFKs in contact with targeted rivers: {river_contact_count} ({(river_contact_count/total_gvfk*100):.1f}%)")
    print(f"GVFKs with river contact AND V1/V2 sites: {len(gvfk_with_v1v2_names)} ({(len(gvfk_with_v1v2_names)/total_gvfk*100):.1f}%)")
    
    if not v1v2_sites.empty:
        unique_sites = v1v2_sites['Lokalitet_'].nunique()
        total_site_gvfk_combinations = len(v1v2_sites)
        print(f"Unique V1/V2 sites (localities): {unique_sites}")
        print(f"Total site-GVFK combinations: {total_site_gvfk_combinations}")
        print(f"Average GVFKs per site: {total_site_gvfk_combinations/unique_sites:.1f}")
    
    # Step 4 summary
    if distance_results is not None:
        valid_distances = distance_results[distance_results['Distance_to_River_m'].notna()]
        total_combinations = len(distance_results)
        print(f"Site-GVFK combinations with calculable distances: {len(valid_distances)} of {total_combinations} ({len(valid_distances)/total_combinations*100:.1f}%)")
        
        if len(valid_distances) > 0:
            # Site-level statistics (final distances for risk assessment)
            unique_sites_with_distances = valid_distances['Lokalitet_ID'].nunique()
            final_distances = valid_distances[valid_distances['Is_Min_Distance'] == True]
            
            print(f"Unique sites with at least one distance calculation: {unique_sites_with_distances}")
            print(f"Average distance to nearest river (all combinations): {valid_distances['Distance_to_River_m'].mean():.1f}m")
            print(f"FINAL: Average minimum distance per site (risk assessment): {final_distances['Distance_to_River_m'].mean():.1f}m")
            print(f"FINAL: Median minimum distance per site: {final_distances['Distance_to_River_m'].median():.1f}m")
    
    # Save summary
    summary_data = {
        'Step': [
            'Step 1: All GVFKs',
            'Step 2: GVFKs with River Contact',
            'Step 3: GVFKs with River Contact and V1/V2 Sites',
            'Step 3: Unique V1/V2 Sites (Localities)',
            'Step 3: Total Site-GVFK Combinations',
            'Step 4: Site-GVFK Combinations with Distances',
            'Step 4: Unique Sites with Final Distances',
            'Step 4: Average Final Distance per Site (m)',
            'Step 5: Visualizations Created'
        ],
        'Count': [
            total_gvfk,
            river_contact_count,
            len(gvfk_with_v1v2_names),
            v1v2_sites['Lokalitet_'].nunique() if not v1v2_sites.empty else 0,
            len(v1v2_sites) if not v1v2_sites.empty else 0,
            len(distance_results[distance_results['Distance_to_River_m'].notna()]) if distance_results is not None else 0,
            len(distance_results[distance_results['Is_Min_Distance'] == True]) if distance_results is not None else 0,
            f"{distance_results[distance_results['Is_Min_Distance'] == True]['Distance_to_River_m'].mean():.1f}" if distance_results is not None and len(distance_results[distance_results['Is_Min_Distance'] == True]) > 0 else "N/A",
            'Complete'
        ],
        'Percentage_of_Total_GVFKs': [
            '100.0%',
            f"{(river_contact_count/total_gvfk*100):.1f}%",
            f"{(len(gvfk_with_v1v2_names)/total_gvfk*100):.1f}%",
            'N/A (Site-level)',
            'N/A (Combination-level)',
            'N/A (Combination-level)',
            'N/A (Site-level)',
            'N/A (Distance metric)',
            'N/A'
        ]
    }
    
    workflow_summary = pd.DataFrame(summary_data)
    workflow_summary.to_csv(os.path.join(RESULTS_PATH, "workflow_summary.csv"), index=False)
    print(f"\nSummary saved to: {os.path.join(RESULTS_PATH, 'workflow_summary.csv')}")
    
    print("\n" + "=" * 60)
    print("ANALYSIS COMPLETE")
    print("=" * 60)

if __name__ == "__main__":
    main()
