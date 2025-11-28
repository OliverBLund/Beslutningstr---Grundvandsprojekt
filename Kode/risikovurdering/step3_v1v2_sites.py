"""
Step 3: Find GVFKs with river contact that have V1 and/or V2 sites.

This step uses a hybrid CSV+shapefile approach to preserve one-to-many site-GVFK
relationships while maintaining accurate spatial geometries. It includes proper
deduplication to ensure each lokalitet-GVFK combination appears only once.

FROM LUC:

Kobling af informationer om lokation, forurening, branche, aktivitet og forureningsstatus for forurenede grunde, som truer grundvand.
For at koble yderligere informationer til de grundvandsforekomstspecifikke forurenende V1 og V2 lokaliteter er der udarbejdet et python script, vedlagt som Bilag 1.
Det endelige datasÃ¦t indeholder sÃ¥ledes 110814 unikke forurenede grunde, der fordeler sig pÃ¥ fÃ¸lgende Lokalitetetsforureningsstatus:
â€¢	UdgÃ¥et inden kortlÃ¦gning    53441
â€¢	V1 kortlagt                 19603
â€¢	V2 kortlagt                 17660
â€¢	UdgÃ¥et efter kortlÃ¦gning    12788
â€¢	Lokaliseret (uafklaret)      3714
â€¢	V1 og V2 kortlagt            3608


"""

import geopandas as gpd
import pandas as pd
import warnings
warnings.filterwarnings("ignore", category=UserWarning, module="pyogrio.raw")
from shapely.errors import ShapelyDeprecationWarning
from config import (
    V1_CSV_PATH, V2_CSV_PATH, V1_SHP_PATH, V2_SHP_PATH,
    get_output_path, ensure_results_directory, ensure_cache_directory,
    V1_DISSOLVED_CACHE, V2_DISSOLVED_CACHE, is_cache_valid, GRUNDVAND_PATH,
    COLUMN_MAPPINGS
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

    # Get column names from mappings
    site_id_col = COLUMN_MAPPINGS['contamination_csv']['site_id']
    gvfk_id_col = COLUMN_MAPPINGS['contamination_csv']['gvfk_id']
    substances_col = COLUMN_MAPPINGS['contamination_csv']['substances']
    branch_col = COLUMN_MAPPINGS['contamination_csv']['branch']
    activity_col = COLUMN_MAPPINGS['contamination_csv']['activity']
    site_name_col = COLUMN_MAPPINGS['contamination_csv']['site_name']
    status_col = COLUMN_MAPPINGS['contamination_csv']['status']
    region_col = COLUMN_MAPPINGS['contamination_csv']['region']
    municipality_col = COLUMN_MAPPINGS['contamination_csv']['municipality']
    site_id_shp_col = COLUMN_MAPPINGS['contamination_shp']['site_id']
    grundvand_gvfk_col = COLUMN_MAPPINGS['grundvand']['gvfk_id']

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
    v1_unique_initial = v1_csv_raw[site_id_col].nunique() if site_id_col in v1_csv_raw.columns else 0
    v2_unique_initial = v2_csv_raw[site_id_col].nunique() if site_id_col in v2_csv_raw.columns else 0
    
    print(f"V1 dataset: {len(v1_csv_raw):,} rows, {v1_unique_initial:,} unique localities")
    print(f"V2 dataset: {len(v2_csv_raw):,} rows, {v2_unique_initial:,} unique localities")
    
    # Check for initial overlap and total unique localities
    if site_id_col in v1_csv_raw.columns and site_id_col in v2_csv_raw.columns:
        v1_lokaliteter = set(v1_csv_raw[site_id_col].dropna())
        v2_lokaliteter = set(v2_csv_raw[site_id_col].dropna())
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
    
    # Filter V1 to sites with either contamination substances OR branch data
    if substances_col not in v1_csv_raw.columns:
        raise ValueError(f"'{substances_col}' column not found in V1 CSV")
    if branch_col not in v1_csv_raw.columns:
        raise ValueError(f"'{branch_col}' column not found in V1 CSV")
    
    # Analyze data breakdown in detail - using UNIQUE LOCALITIES
    print(f"\nDetailed V1 Data Analysis (UNIQUE LOCALITIES):")
    v1_has_substances = (v1_csv_raw[substances_col].notna() &
                         (v1_csv_raw[substances_col].astype(str).str.strip() != ''))
    v1_has_branch = (v1_csv_raw[branch_col].notna() &
                     (v1_csv_raw[branch_col].astype(str).str.strip() != ''))
    
    # Create unique locality analysis
    v1_localities = v1_csv_raw.groupby(site_id_col).agg({
        substances_col: lambda x: (x.notna() & (x.astype(str).str.strip() != '')).any(),
        branch_col: lambda x: (x.notna() & (x.astype(str).str.strip() != '')).any()
    }).reset_index()
    
    v1_substance_only_localities = (v1_localities[substances_col] & ~v1_localities[branch_col]).sum()
    v1_branch_only_localities = (~v1_localities[substances_col] & v1_localities[branch_col]).sum()
    v1_both_localities = (v1_localities[substances_col] & v1_localities[branch_col]).sum()
    v1_neither_localities = (~v1_localities[substances_col] & ~v1_localities[branch_col]).sum()
    v1_total_localities = len(v1_localities)
    
    print(f"  Unique localities with substances only: {v1_substance_only_localities:,} ({v1_substance_only_localities/v1_total_localities*100:.1f}%)")
    print(f"  Unique localities with branch only: {v1_branch_only_localities:,} ({v1_branch_only_localities/v1_total_localities*100:.1f}%)")
    print(f"  Unique localities with both: {v1_both_localities:,} ({v1_both_localities/v1_total_localities*100:.1f}%)")
    print(f"  Unique localities with neither: {v1_neither_localities:,} ({v1_neither_localities/v1_total_localities*100:.1f}%)")
    print(f"  Total qualified unique localities (substance OR branch): {v1_substance_only_localities + v1_branch_only_localities + v1_both_localities:,}")
    
    # COMPARATIVE ANALYSIS: Old approach (substance-only) vs New approach (substance OR branch)
    print(f"\n{'='*60}")
    print(f"COMPARATIVE ANALYSIS: Impact of Including Branch-Only Sites")
    print(f"{'='*60}")
    
    # Old approach: Only sites with substance data
    v1_old_approach = v1_csv_raw[v1_has_substances]
    v1_old_sites = len(v1_old_approach)
    v1_old_localities = v1_old_approach[site_id_col].nunique()
    
    # New approach: Sites with substance OR branch data
    v1_new_approach = v1_csv_raw[v1_has_substances | v1_has_branch]
    v1_new_sites = len(v1_new_approach)
    v1_new_localities = v1_new_approach[site_id_col].nunique()
    
    # Calculate differences
    v1_added_sites = v1_new_sites - v1_old_sites
    v1_added_localities = v1_new_localities - v1_old_localities
    
    print(f"V1 Dataset Comparison:")
    print(f"  Old approach (substance-only):")
    print(f"    Sites: {v1_old_sites:,}")
    print(f"    Unique localities: {v1_old_localities:,}")
    print(f"  New approach (substance OR branch):")
    print(f"    Sites: {v1_new_sites:,}")
    print(f"    Unique localities: {v1_new_localities:,}")
    print(f"  Net addition from branch-only sites:")
    print(f"    Additional sites: +{v1_added_sites:,} ({v1_added_sites/v1_old_sites*100:.1f}%)")
    print(f"    Additional localities: +{v1_added_localities:,} ({v1_added_localities/v1_old_localities*100:.1f}%)")
    
    # Keep sites that have either substance data OR branch data (not both required)
    v1_csv = v1_csv_raw[v1_has_substances | v1_has_branch]
    
    # Filter V2 to sites with either contamination substances OR branch data
    if substances_col not in v2_csv_raw.columns:
        raise ValueError(f"'{substances_col}' column not found in V2 CSV")
    if branch_col not in v2_csv_raw.columns:
        raise ValueError(f"'{branch_col}' column not found in V2 CSV")
    
    # Analyze V2 data breakdown - using UNIQUE LOCALITIES
    print(f"\nDetailed V2 Data Analysis (UNIQUE LOCALITIES):")
    v2_has_substances = (v2_csv_raw[substances_col].notna() &
                         (v2_csv_raw[substances_col].astype(str).str.strip() != ''))
    v2_has_branch = (v2_csv_raw[branch_col].notna() &
                     (v2_csv_raw[branch_col].astype(str).str.strip() != ''))
    
    # Create unique locality analysis
    v2_localities = v2_csv_raw.groupby(site_id_col).agg({
        substances_col: lambda x: (x.notna() & (x.astype(str).str.strip() != '')).any(),
        branch_col: lambda x: (x.notna() & (x.astype(str).str.strip() != '')).any()
    }).reset_index()
    
    v2_substance_only_localities = (v2_localities[substances_col] & ~v2_localities[branch_col]).sum()
    v2_branch_only_localities = (~v2_localities[substances_col] & v2_localities[branch_col]).sum()
    v2_both_localities = (v2_localities[substances_col] & v2_localities[branch_col]).sum()
    v2_neither_localities = (~v2_localities[substances_col] & ~v2_localities[branch_col]).sum()
    v2_total_localities = len(v2_localities)
    
    print(f"  Unique localities with substances only: {v2_substance_only_localities:,} ({v2_substance_only_localities/v2_total_localities*100:.1f}%)")
    print(f"  Unique localities with branch only: {v2_branch_only_localities:,} ({v2_branch_only_localities/v2_total_localities*100:.1f}%)")
    print(f"  Unique localities with both: {v2_both_localities:,} ({v2_both_localities/v2_total_localities*100:.1f}%)")
    print(f"  Unique localities with neither: {v2_neither_localities:,} ({v2_neither_localities/v2_total_localities*100:.1f}%)")
    print(f"  Total qualified unique localities (substance OR branch): {v2_substance_only_localities + v2_branch_only_localities + v2_both_localities:,}")
    
    # V2 Comparative analysis
    v2_old_approach = v2_csv_raw[v2_has_substances]
    v2_old_sites = len(v2_old_approach)
    v2_old_localities = v2_old_approach[site_id_col].nunique()
    
    v2_new_approach = v2_csv_raw[v2_has_substances | v2_has_branch]
    v2_new_sites = len(v2_new_approach)
    v2_new_localities = v2_new_approach[site_id_col].nunique()
    
    v2_added_sites = v2_new_sites - v2_old_sites
    v2_added_localities = v2_new_localities - v2_old_localities
    
    print(f"\nV2 Dataset Comparison:")
    print(f"  Old approach (substance-only):")
    print(f"    Sites: {v2_old_sites:,}")
    print(f"    Unique localities: {v2_old_localities:,}")
    print(f"  New approach (substance OR branch):")
    print(f"    Sites: {v2_new_sites:,}")
    print(f"    Unique localities: {v2_new_localities:,}")
    print(f"  Net addition from branch-only sites:")
    print(f"    Additional sites: +{v2_added_sites:,} ({v2_added_sites/v2_old_sites*100:.1f}%)")
    print(f"    Additional localities: +{v2_added_localities:,} ({v2_added_localities/v2_old_localities*100:.1f}%)")

    # DEBUG: Let's understand the V2 discrepancy
    print(f"\n  DEBUG - V2 Math Check:")
    print(f"    Branch-only localities: {v2_branch_only_localities:,} (19.3% of new total)")
    print(f"    Expected increase if only branch-only added: {v2_branch_only_localities}")
    print(f"    Actual increase: {v2_added_localities}")
    print(f"    Difference: {v2_added_localities - v2_branch_only_localities}")
    if v2_added_localities != v2_branch_only_localities:
        print(f"    → This suggests overlap or filtering effects!")

    # Let's check if the old approach calculation is correct
    v2_old_recalc = v2_csv_raw[v2_has_substances][site_id_col].nunique()
    print(f"    V2 old localities (recalculated): {v2_old_recalc}")
    if v2_old_localities != v2_old_recalc:
        print(f"    → Mismatch in old calculation: {v2_old_localities} vs {v2_old_recalc}")
    
    # Keep sites that have either substance data OR branch data (not both required)
    v2_csv = v2_csv_raw[v2_has_substances | v2_has_branch]
    
    # Show the impact of the new filtering approach - UNIQUE LOCALITIES
    print(f"\nFiltering Impact Comparison (UNIQUE LOCALITIES):")
    
    # Calculate old approach unique localities (substances only)
    v1_old_unique = v1_localities[v1_localities[substances_col]][site_id_col].nunique()
    v2_old_unique = v2_localities[v2_localities[substances_col]][site_id_col].nunique()

    # Calculate new approach unique localities (substances OR branch)
    v1_new_unique = v1_localities[v1_localities[substances_col] | v1_localities[branch_col]][site_id_col].nunique()
    v2_new_unique = v2_localities[v2_localities[substances_col] | v2_localities[branch_col]][site_id_col].nunique()
    
    print(f"  OLD approach (substances only):")
    print(f"    V1 unique localities: {v1_old_unique:,}")
    print(f"    V2 unique localities: {v2_old_unique:,}")
    print(f"  NEW approach (substances OR branch):")
    print(f"    V1 unique localities: {v1_new_unique:,} (+{v1_new_unique - v1_old_unique:,})")
    print(f"    V2 unique localities: {v2_new_unique:,} (+{v2_new_unique - v2_old_unique:,})")
    
    # Show which additional localities we're gaining
    if v1_branch_only_localities > 0:
        v1_branch_only_ids = v1_localities[(~v1_localities[substances_col] & v1_localities[branch_col])][site_id_col].tolist()
        print(f"    V1 additional branch-only localities (first 10): {v1_branch_only_ids[:10]}")

    if v2_branch_only_localities > 0:
        v2_branch_only_ids = v2_localities[(~v2_localities[substances_col] & v2_localities[branch_col])][site_id_col].tolist()
        print(f"    V2 additional branch-only localities (first 10): {v2_branch_only_ids[:10]}")
    
    # COMBINED IMPACT SUMMARY
    total_old_sites = v1_old_sites + v2_old_sites  
    total_new_sites = v1_new_sites + v2_new_sites
    total_added_sites = total_new_sites - total_old_sites
    
    total_old_localities = v1_old_localities + v2_old_localities
    total_new_localities = v1_new_localities + v2_new_localities  
    total_added_localities = total_new_localities - total_old_localities
    
    print(f"\n{'='*60}")
    print(f"COMBINED IMPACT SUMMARY")
    print(f"{'='*60}")
    print(f"Total sites (V1 + V2):")
    print(f"  Old approach (substance-only): {total_old_sites:,}")
    print(f"  New approach (substance OR branch): {total_new_sites:,}")
    print(f"  Net sites added: +{total_added_sites:,} ({total_added_sites/total_old_sites*100:.1f}%)")
    print(f"")
    print(f"Total localities (V1 + V2):")
    print(f"  Old approach (substance-only): {total_old_localities:,}")
    print(f"  New approach (substance OR branch): {total_new_localities:,}")
    print(f"  Net localities added: +{total_added_localities:,} ({total_added_localities/total_old_localities*100:.1f}%)")
    print(f"{'='*60}")
    
    # Report filtered results
    v1_unique_filtered = v1_csv[site_id_col].nunique() if site_id_col in v1_csv.columns else 0
    v2_unique_filtered = v2_csv[site_id_col].nunique() if site_id_col in v2_csv.columns else 0
    
    print(f"After contamination filtering:")
    print(f"V1 dataset: {len(v1_csv):,} rows, {v1_unique_filtered:,} localities ({v1_unique_filtered/v1_unique_initial:.1%} retained)")
    print(f"V2 dataset: {len(v2_csv):,} rows, {v2_unique_filtered:,} localities ({v2_unique_filtered/v2_unique_initial:.1%} retained)")
    
    # Check post-filtering overlap
    if not v1_csv.empty and not v2_csv.empty:
        v1_lokaliteter_filtered = set(v1_csv[site_id_col].dropna())
        v2_lokaliteter_filtered = set(v2_csv[site_id_col].dropna())
        overlap_filtered = len(v1_lokaliteter_filtered.intersection(v2_lokaliteter_filtered))
        print(f"Overlap after filtering: {overlap_filtered:,} localities in BOTH datasets")
    
    if v1_csv.empty and v2_csv.empty:
        raise ValueError("No sites with contamination found in V1 or V2 data")
    
    # Load shapefile geometries and dissolve by locality
    # Process V1 geometries
    v1_shp = gpd.read_file(V1_SHP_PATH)

    # Find locality ID column in actual shapefile
    locality_col_actual = None
    for col in [site_id_shp_col, 'Lokalitets', 'Lokalitetsnr', 'LokNr']:
        if col in v1_shp.columns:
            locality_col_actual = col
            break

    if locality_col_actual is None:
        raise ValueError(f"No locality column found in V1 shapefile (looking for {site_id_shp_col})")

    # Load or create dissolved V1 geometries with caching
    v1_geom = _load_or_dissolve_geometries(v1_shp, V1_DISSOLVED_CACHE, V1_SHP_PATH, locality_col_actual, 'V1')

    # Process V2 geometries
    v2_shp = gpd.read_file(V2_SHP_PATH)

    # Find locality ID column in V2 shapefile (may be same or different)
    locality_col_v2 = None
    for col in [site_id_shp_col, 'Lokalitets', 'Lokalitetsnr', 'LokNr']:
        if col in v2_shp.columns:
            locality_col_v2 = col
            break

    if locality_col_v2 is None:
        raise ValueError(f"No locality column found in V2 shapefile (looking for {site_id_shp_col})")

    # Load or create dissolved V2 geometries with caching
    v2_geom = _load_or_dissolve_geometries(v2_shp, V2_DISSOLVED_CACHE, V2_SHP_PATH, locality_col_v2, 'V2')
    
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
            v1_csv, v1_geom, rivers_gvfk, locality_col_actual, 'V1', site_id_col, gvfk_id_col, substances_col
        )

    # Process V2 data
    v2_combined_list = []
    if not v2_csv.empty and not v2_geom.empty:
        v2_combined_list = _process_v1v2_data(
            v2_csv, v2_geom, rivers_gvfk, locality_col_v2, 'V2', site_id_col, gvfk_id_col, substances_col
        )
    
    # Combine and deduplicate V1 and V2 results
    v1v2_combined = _combine_and_deduplicate_v1v2(v1_combined_list, v2_combined_list)
    
    # Get unique GVFKs with V1/V2 sites
    gvfk_with_v1v2_names = set()
    if not v1v2_combined.empty:
        gvfk_with_v1v2_names = set(v1v2_combined[gvfk_id_col].unique())
    
    # DIAGNOSTIC: Check if branch-only sites contribute to new GVFKs
    print(f"\nGVFK Impact Analysis:")
    print(f"  Total GVFKs with V1/V2 sites: {len(gvfk_with_v1v2_names):,}")
    
    if not v1v2_combined.empty and substances_col in v1v2_combined.columns:
        # Check GVFKs from sites with substances only
        substance_sites = v1v2_combined[
            v1v2_combined[substances_col].notna() &
            (v1v2_combined[substances_col].astype(str).str.strip() != '') &
            (v1v2_combined[substances_col].astype(str) != 'nan')
        ]
        gvfk_from_substance_sites = set(substance_sites[gvfk_id_col].unique()) if not substance_sites.empty else set()

        # Check GVFKs from branch-only sites (sites without substances)
        branch_only_sites = v1v2_combined[
            ~(v1v2_combined[substances_col].notna() &
              (v1v2_combined[substances_col].astype(str).str.strip() != '') &
              (v1v2_combined[substances_col].astype(str) != 'nan'))
        ]
        gvfk_from_branch_only_sites = set(branch_only_sites[gvfk_id_col].unique()) if not branch_only_sites.empty else set()
        
        print(f"  GVFKs from substance-containing sites: {len(gvfk_from_substance_sites):,}")
        print(f"  GVFKs from branch-only sites: {len(gvfk_from_branch_only_sites):,}")
        print(f"  NEW GVFKs added by branch-only sites: {len(gvfk_from_branch_only_sites - gvfk_from_substance_sites):,}")
        
        if gvfk_from_branch_only_sites - gvfk_from_substance_sites:
            new_gvfks = list(gvfk_from_branch_only_sites - gvfk_from_substance_sites)[:5]
            print(f"  Examples of new GVFKs from branch-only sites: {new_gvfks}")
    
    # Generate summary statistics and save results
    _save_step3_results(v1v2_combined, gvfk_with_v1v2_names, site_id_shp_col, gvfk_id_col, grundvand_gvfk_col)

    return gvfk_with_v1v2_names, v1v2_combined

def _load_or_dissolve_geometries(shp_data, cache_path, source_path, locality_col, dataset_name):
    """
    Load dissolved geometries from cache or create and cache them.
    
    Args:
        shp_data (GeoDataFrame): Raw shapefile data
        cache_path (str): Path to cache file
        source_path (str): Path to source shapefile
        locality_col (str): Column name for dissolving
        dataset_name (str): 'V1' or 'V2' for logging
        
    Returns:
        GeoDataFrame: Dissolved geometries
    """
    # Ensure cache directory exists
    ensure_cache_directory()
    
    # Check if cache is valid
    if is_cache_valid(cache_path, source_path):
        print(f"Loading {dataset_name} dissolved geometries from cache: {cache_path}")
        try:
            dissolved_geom = gpd.read_file(cache_path)
            print(f"✓ {dataset_name}: Loaded {len(dissolved_geom):,} dissolved geometries from cache")
            return dissolved_geom
        except Exception as e:
            print(f"Warning: Could not load {dataset_name} cache ({e}), recreating...")
    
    # Cache invalid or doesn't exist - dissolve and save
    print(f"Dissolving {dataset_name} geometries by locality (this may take a few minutes)...")
    dissolved_geom = shp_data.dissolve(by=locality_col, as_index=False)
    
    # Save to cache
    try:
        dissolved_geom.to_file(cache_path, encoding="utf-8")
        print(f"✓ {dataset_name}: Dissolved {len(shp_data):,} → {len(dissolved_geom):,} geometries and saved to cache")
    except Exception as e:
        print(f"Warning: Could not save {dataset_name} cache ({e}), continuing without caching")
    
    return dissolved_geom

def _process_v1v2_data(csv_data, geom_data, rivers_gvfk, locality_col, site_type, site_id_col, gvfk_id_col, substances_col):
    """
    Process V1 or V2 data by combining CSV relationships with dissolved geometries.

    Args:
        csv_data (DataFrame): CSV file with site-GVFK relationships
        geom_data (GeoDataFrame): Dissolved geometries by locality
        rivers_gvfk (list): List of GVFK names with river contact
        locality_col (str): Name of locality column in shapefile
        site_type (str): 'V1' or 'V2'
        site_id_col (str): Name of site ID column in CSV
        gvfk_id_col (str): Name of GVFK ID column
        substances_col (str): Name of substances column

    Returns:
        list: List containing processed GeoDataFrame if successful, empty list otherwise
    """
    # Standardize locality column name (CSV uses site_id_col, shapefile uses locality_col)
    csv_lokalitet_col = 'Lokalitet_'  # Target column name for joining
    if site_id_col in csv_data.columns and csv_lokalitet_col not in csv_data.columns:
        csv_data = csv_data.rename(columns={site_id_col: csv_lokalitet_col})

    # Filter CSV to only GVFKs with river contact
    rivers_gvfk_set = set(rivers_gvfk)
    filtered_csv = csv_data[csv_data[gvfk_id_col].isin(rivers_gvfk_set)].copy()
    # Track unique localities in river-contact GVFKs
    unique_lokaliteter_in_river_gvfks = filtered_csv[csv_lokalitet_col].nunique() if not filtered_csv.empty else 0
    print(f"{site_type}: {len(filtered_csv):,} rows → {unique_lokaliteter_in_river_gvfks:,} unique localities in river-contact GVFKs")
    
    if filtered_csv.empty:
        return []
    
    # Aggregate by lokalitet-GVFK combination, preserving all substances
    # Group and aggregate to ensure all substances are preserved
    agg_dict = {}

    # Always aggregate substances with semicolon separation
    agg_dict[substances_col] = lambda x: '; '.join(x.dropna().astype(str).unique())

    # For other columns, take first value (should be identical within each group)
    for col in filtered_csv.columns:
        if col not in [csv_lokalitet_col, gvfk_id_col, substances_col]:
            agg_dict[col] = 'first'

    unique_csv = filtered_csv.groupby([csv_lokalitet_col, gvfk_id_col], as_index=False).agg(agg_dict)
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
        left_on=csv_lokalitet_col,
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

def _save_step3_results(v1v2_combined, gvfk_with_v1v2_names, site_id_shp_col, gvfk_id_col, grundvand_gvfk_col):
    """
    Save Step 3 results and generate summary statistics.

    Args:
        v1v2_combined (GeoDataFrame): Combined and deduplicated V1/V2 data
        gvfk_with_v1v2_names (set): Set of GVFK names with V1/V2 sites
        site_id_shp_col (str): Name of site ID column in shapefile
        gvfk_id_col (str): Name of GVFK ID column
        grundvand_gvfk_col (str): Name of GVFK ID column in grundvand shapefile
    """
    if v1v2_combined.empty:
        print("No V1/V2 sites found with river contact.")
        return

    # Section 4: Final Summary
    print("\n4. FINAL SUMMARY")
    print("-" * 20)

    unique_sites = v1v2_combined[site_id_shp_col].nunique()
    total_site_gvfk_combinations = len(v1v2_combined)
    
    # Properly count V1-only, V2-only, and Both localities
    if 'Lokalitete' in v1v2_combined.columns:
        # Get all unique localities and their site types across all combinations
        locality_types = v1v2_combined.groupby(site_id_shp_col)['Lokalitete'].apply(set).reset_index()
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
    v1v2_combined.to_file(v1v2_sites_path, encoding="utf-8")
    
    # Save GVFK polygons that contain V1/V2 sites
    gvf = gpd.read_file(GRUNDVAND_PATH)
    gvfk_with_v1v2_polygons = gvf[gvf[grundvand_gvfk_col].isin(gvfk_with_v1v2_names)]
    
    gvfk_polygons_path = get_output_path('step3_gvfk_polygons')
    gvfk_with_v1v2_polygons.to_file(gvfk_polygons_path, encoding="utf-8")
    print(f"Saved GVFK polygons: {len(gvfk_with_v1v2_polygons)} records")
    
    # Note: Detailed relationships CSV removed - data is passed directly to Step 4

if __name__ == "__main__":
    # Allow running this step independently
    # Note: This requires results from Step 2
    print("This step requires results from Step 2. Run main_workflow.py instead.")
    print("To test independently, provide a list of rivers_gvfk manually.") 

