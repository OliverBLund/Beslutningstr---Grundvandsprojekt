"""
Step 3: Find GVFKs with river contact that have V1 and/or V2 sites.

This step uses a hybrid CSV+shapefile approach to preserve one-to-many site-GVFK
relationships while maintaining accurate spatial geometries. It includes proper
deduplication to ensure each lokalitet-GVFK combination appears only once.

FROM LUC:

Kobling af informationer om lokation, forurening, branche, aktivitet og forureningsstatus for forurenede grunde, som truer grundvand.
For at koble yderligere informationer til de grundvandsforekomstspecifikke forurenende V1 og V2 lokaliteter er der udarbejdet et python script, vedlagt som Bilag 1.
Det endelige datasæt indeholder således 110814 unikke forurenede grunde, der fordeler sig på følgende Lokalitetetsforureningsstatus:
•	Udgået inden kortlægning    53441
•	V1 kortlagt                 19603
•	V2 kortlagt                 17660
•	Udgået efter kortlægning    12788
•	Lokaliseret (uafklaret)      3714
•	V1 og V2 kortlagt            3608


"""

import geopandas as gpd
import pandas as pd
import warnings
warnings.filterwarnings("ignore", category=UserWarning, module="pyogrio.raw")
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
    
    print("\nSTEP 3: V1/V2 CONTAMINATION SITES ANALYSIS")
    print("=" * 60)
    
    # Load CSV files with complete site-GVFK relationships
    v1_csv_raw = pd.read_csv(V1_CSV_PATH)
    v2_csv_raw = pd.read_csv(V2_CSV_PATH)
    
    # Section 1: Initial Data Loading
    print("\n1. INITIAL DATA LOADING")
    print("-" * 30)
    print(f"Data sources:")
    print(f"  V1 CSV: {V1_CSV_PATH}")
    print(f"  V2 CSV: {V2_CSV_PATH}")
    v1_unique_initial = v1_csv_raw['Lokalitetsnr'].nunique() if 'Lokalitetsnr' in v1_csv_raw.columns else 0
    v2_unique_initial = v2_csv_raw['Lokalitetsnr'].nunique() if 'Lokalitetsnr' in v2_csv_raw.columns else 0
    
    print(f"V1 dataset: {len(v1_csv_raw):,} rows, {v1_unique_initial:,} unique localities")
    print(f"V2 dataset: {len(v2_csv_raw):,} rows, {v2_unique_initial:,} unique localities")
    
    # Check for initial overlap and total unique localities
    if 'Lokalitetsnr' in v1_csv_raw.columns and 'Lokalitetsnr' in v2_csv_raw.columns:
        v1_lokaliteter = set(v1_csv_raw['Lokalitetsnr'].dropna())
        v2_lokaliteter = set(v2_csv_raw['Lokalitetsnr'].dropna())
        overlap_initial = len(v1_lokaliteter.intersection(v2_lokaliteter))
        total_unique_localities = len(v1_lokaliteter | v2_lokaliteter)
        
        print(f"Overlap: {overlap_initial:,} localities present in BOTH datasets")
        print(f"Total unique localities (V1 ∪ V2): {total_unique_localities:,}")
        
        # Compare with reference documentation  
        print(f"\nValidation against reference documentation:")
        print(f"  Reference V1 localities: 19,603")
        print(f"  Reference V2 localities: 17,660") 
        print(f"  Reference V1∩V2 overlap: 3,608")
        print(f"  Reference total unique: 110,814 (includes expired/unclear sites)")
        print(f"")
        print(f"  Current V1 localities: {v1_unique_initial:,}")
        print(f"  Current V2 localities: {v2_unique_initial:,}")
        print(f"  Current V1∩V2 overlap: {overlap_initial:,}")  
        print(f"  Current total unique: {total_unique_localities:,}")
        print(f"")
        print(f"NOTE: Current dataset appears to be a subset focused on active contamination.")
    
    # Section 2: Contamination Filtering
    print("\n2. CONTAMINATION FILTERING (sites with active contamination only)")
    print("-" * 65)
    
    # Filter V1 to only sites with active contaminations
    if 'Lokalitetensstoffer' not in v1_csv_raw.columns:
        raise ValueError("'Lokalitetensstoffer' column not found in V1 CSV")
    
    v1_csv = v1_csv_raw.dropna(subset=['Lokalitetensstoffer'])
    v1_csv = v1_csv[v1_csv['Lokalitetensstoffer'].str.strip() != '']
    
    # Filter V2 to only sites with active contaminations
    if 'Lokalitetensstoffer' not in v2_csv_raw.columns:
        raise ValueError("'Lokalitetensstoffer' column not found in V2 CSV")
    
    v2_csv = v2_csv_raw.dropna(subset=['Lokalitetensstoffer'])
    v2_csv = v2_csv[v2_csv['Lokalitetensstoffer'].str.strip() != '']
    
    # Report filtered results
    v1_unique_filtered = v1_csv['Lokalitetsnr'].nunique() if 'Lokalitetsnr' in v1_csv.columns else 0
    v2_unique_filtered = v2_csv['Lokalitetsnr'].nunique() if 'Lokalitetsnr' in v2_csv.columns else 0
    
    print(f"After contamination filtering:")
    print(f"V1 dataset: {len(v1_csv):,} rows, {v1_unique_filtered:,} localities ({v1_unique_filtered/v1_unique_initial:.1%} retained)")
    print(f"V2 dataset: {len(v2_csv):,} rows, {v2_unique_filtered:,} localities ({v2_unique_filtered/v2_unique_initial:.1%} retained)")
    
    # Check post-filtering overlap
    if not v1_csv.empty and not v2_csv.empty:
        v1_lokaliteter_filtered = set(v1_csv['Lokalitetsnr'].dropna())
        v2_lokaliteter_filtered = set(v2_csv['Lokalitetsnr'].dropna())
        overlap_filtered = len(v1_lokaliteter_filtered.intersection(v2_lokaliteter_filtered))
        print(f"Overlap after filtering: {overlap_filtered:,} localities in BOTH datasets")
    
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
    
    # Process V2 geometries
    v2_shp = gpd.read_file(V2_SHP_PATH)
    
    # Dissolve V2 geometries by locality
    v2_geom = v2_shp.dissolve(by=locality_col, as_index=False)
    
    # Section 3: River-Contact GVFK Filtering & Geometry Processing
    print("\n3. RIVER-CONTACT GVFK FILTERING & GEOMETRY PROCESSING")
    print("-" * 55)
    print(f"Geometry sources:")
    print(f"  V1 SHP: {V1_SHP_PATH}")
    print(f"  V2 SHP: {V2_SHP_PATH}")
    print(f"Geometry processing: Dissolved {len(v1_geom):,} V1 + {len(v2_geom):,} V2 locality polygons")
    
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
    # Track unique localities in river-contact GVFKs
    unique_lokaliteter_in_river_gvfks = filtered_csv['Lokalitet_'].nunique() if not filtered_csv.empty else 0
    print(f"{site_type}: {len(filtered_csv):,} rows → {unique_lokaliteter_in_river_gvfks:,} unique localities in river-contact GVFKs")
    
    if filtered_csv.empty:
        return []
    
    # Aggregate by lokalitet-GVFK combination, preserving all substances
    # Group and aggregate to ensure all substances are preserved
    agg_dict = {}
    
    # Always aggregate substances with semicolon separation
    agg_dict['Lokalitetensstoffer'] = lambda x: '; '.join(x.dropna().astype(str).unique())
    
    # For other columns, take first value (should be identical within each group)
    for col in filtered_csv.columns:
        if col not in ['Lokalitet_', 'Navn', 'Lokalitetensstoffer']:
            agg_dict[col] = 'first'
    
    unique_csv = filtered_csv.groupby(['Lokalitet_', 'Navn'], as_index=False).agg(agg_dict)
    print(f"{site_type}: {len(unique_csv):,} unique lokalitet-GVFK combinations (substances aggregated)")
    
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
    
    # Final deduplication to handle sites in both V1 and V2
    duplicates = v1v2_combined_raw.groupby(['Lokalitet_', 'Navn']).size()
    duplicate_combinations = duplicates[duplicates > 1]
    
    if len(duplicate_combinations) > 0:
        # For duplicate combinations, keep one record but update site type to 'V1 og V2'
        v1v2_deduped_list = []
        
        for (lokalitet_id, gvfk_name), count in duplicates.items():
            subset = v1v2_combined_raw[
                (v1v2_combined_raw['Lokalitet_'] == lokalitet_id) & 
                (v1v2_combined_raw['Navn'] == gvfk_name)
            ]
            
            if count > 1:
                # Aggregate substances from both V1 and V2 records
                aggregated_record = subset.iloc[0:1].copy()  # Start with first record
                
                # Aggregate substances from all duplicate records
                all_substances = []
                for _, row in subset.iterrows():
                    substances_str = str(row.get('Lokalitetensstoffer', ''))
                    if pd.notna(substances_str) and substances_str.strip() != '' and substances_str != 'nan':
                        # Split existing semicolon-separated substances and add to list
                        substances = [s.strip() for s in substances_str.split(';') if s.strip()]
                        all_substances.extend(substances)
                
                # Combine unique substances
                if all_substances:
                    unique_substances = list(dict.fromkeys(all_substances))  # Preserves order while removing duplicates
                    aggregated_record['Lokalitetensstoffer'] = '; '.join(unique_substances)
                
                aggregated_record['Lokalitete'] = 'V1 og V2'
                v1v2_deduped_list.append(aggregated_record)
            else:
                # Keep single record as is
                v1v2_deduped_list.append(subset)
        
        v1v2_combined = pd.concat(v1v2_deduped_list, ignore_index=True)
        
    else:
        v1v2_combined = v1v2_combined_raw.copy()
    
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
    
    # Section 4: Final Summary
    print("\n4. FINAL SUMMARY")
    print("-" * 20)
    
    unique_sites = v1v2_combined['Lokalitet_'].nunique()
    total_site_gvfk_combinations = len(v1v2_combined)
    
    # Properly count V1-only, V2-only, and Both localities
    if 'Lokalitete' in v1v2_combined.columns:
        # Get all unique localities and their site types across all combinations
        locality_types = v1v2_combined.groupby('Lokalitet_')['Lokalitete'].apply(set).reset_index()
        locality_types['type_summary'] = locality_types['Lokalitete'].apply(
            lambda x: 'V1 og V2' if len(x) > 1 else list(x)[0]
        )
        
        # Count unique localities by final type
        type_counts = locality_types['type_summary'].value_counts()
        
        print(f"Unique localities (Lokalitetsnr): {unique_sites:,}")
        v1_only = type_counts.get('V1', 0)
        v2_only = type_counts.get('V2', 0) 
        both = type_counts.get('V1 og V2', 0)
        
        print(f"  • V1 only: {v1_only:,} localities")
        print(f"  • V2 only: {v2_only:,} localities") 
        print(f"  • Both V1 & V2: {both:,} localities")
        print(f"  • TOTAL: {v1_only + v2_only + both:,} localities")
        
        print(f"\nLokalitet-GVFK combinations: {total_site_gvfk_combinations:,}")
        print(f"GVFKs containing V1/V2 sites: {len(gvfk_with_v1v2_names):,}")
    else:
        print(f"Unique V1/V2 sites: {unique_sites:,}")
        print(f"Site-GVFK combinations: {total_site_gvfk_combinations:,}")
        print(f"GVFKs with V1/V2 sites: {len(gvfk_with_v1v2_names):,}")
    
    # Save V1/V2 site-GVFK combinations
    v1v2_sites_path = get_output_path('step3_v1v2_sites')
    v1v2_combined.to_file(v1v2_sites_path)
    
    # Save GVFK polygons that contain V1/V2 sites
    gvf = gpd.read_file(GRUNDVAND_PATH)
    gvfk_with_v1v2_polygons = gvf[gvf['Navn'].isin(gvfk_with_v1v2_names)]
    
    gvfk_polygons_path = get_output_path('step3_gvfk_polygons')
    gvfk_with_v1v2_polygons.to_file(gvfk_polygons_path)
    print(f"Saved GVFK polygons: {len(gvfk_with_v1v2_polygons)} records")
    
    # Note: Detailed relationships CSV removed - data is passed directly to Step 4

if __name__ == "__main__":
    # Allow running this step independently
    # Note: This requires results from Step 2
    print("This step requires results from Step 2. Run main_workflow.py instead.")
    print("To test independently, provide a list of rivers_gvfk manually.") 