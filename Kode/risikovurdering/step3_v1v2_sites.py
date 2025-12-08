"""
Step 3: Find GVFKs with river contact that have V1 and/or V2 sites.

This step uses a hybrid CSV+shapefile approach to preserve one-to-many site-GVFK
relationships while maintaining accurate spatial geometries. It includes proper
deduplication to ensure each lokalitet-GVFK combination appears only once.

CLEAN VERSION - Focused reporting with essential information only.
"""

import geopandas as gpd
import pandas as pd
import warnings
warnings.filterwarnings("ignore", category=UserWarning, module="pyogrio.raw")
from shapely.errors import ShapelyDeprecationWarning
from tqdm import tqdm
from config import (
    COLUMN_MAPPINGS,
    GRUNDVAND_LAYER_NAME,
    GRUNDVAND_PATH,
    V1_CSV_PATH,
    V1_DISSOLVED_CACHE,
    V1_SHP_PATH,
    V2_CSV_PATH,
    V2_DISSOLVED_CACHE,
    V2_SHP_PATH,
    apply_sampling,
    ensure_cache_directory,
    ensure_results_directory,
    get_output_path,
    is_cache_valid,
)
from step_reporter import (
    report_step_header,
    report_subsection,
    report_counts,
    report_breakdown,
    report_completion,
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
    report_step_header(3, "Identify V1/V2 Contaminated Sites in GVFKs")

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

    ensure_results_directory()

    # ========================================================================
    # SECTION 1: Load contamination data
    # ========================================================================
    print("\nLoading contamination data...")
    v1_csv_raw = pd.read_csv(V1_CSV_PATH)
    v2_csv_raw = pd.read_csv(V2_CSV_PATH)

    # Apply sampling if enabled
    v1_csv_raw = apply_sampling(v1_csv_raw, id_column=site_id_col)
    v2_csv_raw = apply_sampling(v2_csv_raw, id_column=site_id_col)

    v1_unique_initial = v1_csv_raw[site_id_col].nunique()
    v2_unique_initial = v2_csv_raw[site_id_col].nunique()
    overlap_initial = len(set(v1_csv_raw[site_id_col]) & set(v2_csv_raw[site_id_col]))

    report_counts("V1", sites=v1_unique_initial, combinations=len(v1_csv_raw), indent=1)
    report_counts("V2", sites=v2_unique_initial, combinations=len(v2_csv_raw), indent=1)
    print(f"  Overlap: {overlap_initial:,} sites in both datasets")

    # ========================================================================
    # SECTION 2: Contamination filtering (substance OR branch/activity data)
    # ========================================================================
    report_subsection("Contamination filtering (substance OR branch/activity data)")

    # Analyze V1
    v1_has_substances = (v1_csv_raw[substances_col].notna() &
                         (v1_csv_raw[substances_col].astype(str).str.strip() != ''))
    v1_has_branch = (v1_csv_raw[branch_col].notna() &
                     (v1_csv_raw[branch_col].astype(str).str.strip() != ''))

    v1_localities = v1_csv_raw.groupby(site_id_col).agg({
        substances_col: lambda x: (x.notna() & (x.astype(str).str.strip() != '')).any(),
        branch_col: lambda x: (x.notna() & (x.astype(str).str.strip() != '')).any()
    }).reset_index()

    v1_substance_only = (v1_localities[substances_col] & ~v1_localities[branch_col]).sum()
    v1_branch_only = (~v1_localities[substances_col] & v1_localities[branch_col]).sum()
    v1_both = (v1_localities[substances_col] & v1_localities[branch_col]).sum()
    v1_neither = (~v1_localities[substances_col] & ~v1_localities[branch_col]).sum()
    v1_qualified = v1_substance_only + v1_branch_only + v1_both

    print(f"  V1: {v1_qualified:,} sites qualified ({v1_qualified/len(v1_localities)*100:.1f}%)")
    print(f"    ├─ Substance only: {v1_substance_only} ({v1_substance_only/len(v1_localities)*100:.1f}%)")
    print(f"    ├─ Branch only: {v1_branch_only} ({v1_branch_only/len(v1_localities)*100:.1f}%)")
    print(f"    ├─ Both: {v1_both} ({v1_both/len(v1_localities)*100:.1f}%)")
    print(f"    └─ Neither (filtered): {v1_neither} ({v1_neither/len(v1_localities)*100:.1f}%)")

    # Analyze V2
    v2_has_substances = (v2_csv_raw[substances_col].notna() &
                         (v2_csv_raw[substances_col].astype(str).str.strip() != ''))
    v2_has_branch = (v2_csv_raw[branch_col].notna() &
                     (v2_csv_raw[branch_col].astype(str).str.strip() != ''))

    v2_localities = v2_csv_raw.groupby(site_id_col).agg({
        substances_col: lambda x: (x.notna() & (x.astype(str).str.strip() != '')).any(),
        branch_col: lambda x: (x.notna() & (x.astype(str).str.strip() != '')).any()
    }).reset_index()

    v2_substance_only = (v2_localities[substances_col] & ~v2_localities[branch_col]).sum()
    v2_branch_only = (~v2_localities[substances_col] & v2_localities[branch_col]).sum()
    v2_both = (v2_localities[substances_col] & v2_localities[branch_col]).sum()
    v2_neither = (~v2_localities[substances_col] & ~v2_localities[branch_col]).sum()
    v2_qualified = v2_substance_only + v2_branch_only + v2_both

    print(f"\n  V2: {v2_qualified:,} sites qualified ({v2_qualified/len(v2_localities)*100:.1f}%)")
    print(f"    ├─ Substance only: {v2_substance_only} ({v2_substance_only/len(v2_localities)*100:.1f}%)")
    print(f"    ├─ Branch only: {v2_branch_only} ({v2_branch_only/len(v2_localities)*100:.1f}%)")
    print(f"    ├─ Both: {v2_both} ({v2_both/len(v2_localities)*100:.1f}%)")
    print(f"    └─ Neither (filtered): {v2_neither} ({v2_neither/len(v2_localities)*100:.1f}%)")

    # Filter to qualified sites
    v1_csv = v1_csv_raw[v1_has_substances | v1_has_branch]
    v2_csv = v2_csv_raw[v2_has_substances | v2_has_branch]

    # ========================================================================
    # SECTION 3: Load geometries and filter to river-contact GVFKs
    # ========================================================================
    report_subsection(f"Filtering to river-contact GVFKs ({len(rivers_gvfk)} GVFKs from Step 2)")

    # Load dissolved geometries (using cache if available)
    v1_shp_raw = gpd.read_file(V1_SHP_PATH)
    v2_shp_raw = gpd.read_file(V2_SHP_PATH)

    # Find actual locality column names in shapefiles
    locality_col_v1 = None
    for col in [site_id_shp_col, 'Lokalitets', 'Lokalitetsnr', 'LokNr']:
        if col in v1_shp_raw.columns:
            locality_col_v1 = col
            break
    if locality_col_v1 is None:
        raise ValueError(f"No locality column found in V1 shapefile (looking for {site_id_shp_col})")

    locality_col_v2 = None
    for col in [site_id_shp_col, 'Lokalitets', 'Lokalitetsnr', 'LokNr']:
        if col in v2_shp_raw.columns:
            locality_col_v2 = col
            break
    if locality_col_v2 is None:
        raise ValueError(f"No locality column found in V2 shapefile (looking for {site_id_shp_col})")

    v1_shp = _load_or_dissolve_geometries(
        v1_shp_raw, V1_DISSOLVED_CACHE, V1_SHP_PATH, locality_col_v1, 'V1'
    )
    v2_shp = _load_or_dissolve_geometries(
        v2_shp_raw, V2_DISSOLVED_CACHE, V2_SHP_PATH, locality_col_v2, 'V2'
    )

    # Process V1 and V2 data
    v1_processed = _process_v1v2_data(
        v1_csv, v1_shp, rivers_gvfk, locality_col_v1, 'V1',
        site_id_col, gvfk_id_col, substances_col
    )
    v2_processed = _process_v1v2_data(
        v2_csv, v2_shp, rivers_gvfk, locality_col_v2, 'V2',
        site_id_col, gvfk_id_col, substances_col
    )

    # ========================================================================
    # SECTION 4: Combine and deduplicate
    # ========================================================================
    v1v2_combined = _combine_and_deduplicate_v1v2(v1_processed, v2_processed)

    # Get GVFKs with sites
    if 'Navn' in v1v2_combined.columns:
        gvfk_with_v1v2_names = set(v1v2_combined['Navn'].unique())
    elif gvfk_id_col in v1v2_combined.columns:
        gvfk_with_v1v2_names = set(v1v2_combined[gvfk_id_col].unique())
    else:
        gvfk_with_v1v2_names = set()

    # ========================================================================
    # SECTION 5: Save results and print summary
    # ========================================================================
    _save_step3_results(v1v2_combined, gvfk_with_v1v2_names, site_id_shp_col,
                       gvfk_id_col, grundvand_gvfk_col, len(rivers_gvfk))

    report_completion(3)

    return gvfk_with_v1v2_names, v1v2_combined


def _load_or_dissolve_geometries(shp_data, cache_path, source_path, locality_col, dataset_name):
    """Load dissolved geometries from cache or create and cache them."""
    ensure_cache_directory()

    if is_cache_valid(cache_path, source_path):
        try:
            dissolved_geom = gpd.read_file(cache_path)
            print(f"  {dataset_name}: Loaded {len(dissolved_geom):,} dissolved geometries from cache")
            return dissolved_geom
        except Exception:
            pass  # Fall through to recreate

    # Dissolve and save to cache
    dissolved_geom = shp_data.dissolve(by=locality_col, as_index=False)
    try:
        dissolved_geom.to_file(cache_path, encoding="utf-8")
        print(f"  {dataset_name}: Dissolved and cached {len(dissolved_geom):,} geometries")
    except Exception:
        print(f"  WARNING: {dataset_name}: Could not cache geometries, continuing...")

    return dissolved_geom


def _process_v1v2_data(csv_data, geom_data, rivers_gvfk, locality_col, site_type,
                       site_id_col, gvfk_id_col, substances_col):
    """Process V1 or V2 data by combining CSV relationships with dissolved geometries."""
    # Standardize locality column name
    csv_lokalitet_col = 'Lokalitet_'
    if site_id_col in csv_data.columns and csv_lokalitet_col not in csv_data.columns:
        csv_data = csv_data.rename(columns={site_id_col: csv_lokalitet_col})

    # Filter to river-contact GVFKs
    rivers_gvfk_set = set(rivers_gvfk)
    filtered_csv = csv_data[csv_data[gvfk_id_col].isin(rivers_gvfk_set)].copy()

    unique_sites = filtered_csv[csv_lokalitet_col].nunique() if not filtered_csv.empty else 0

    if filtered_csv.empty:
        print(f"  {site_type}: No sites in river-contact GVFKs")
        return []

    # Aggregate by lokalitet-GVFK combination
    agg_dict = {substances_col: lambda x: '; '.join(x.dropna().astype(str).unique())}
    for col in filtered_csv.columns:
        if col not in [csv_lokalitet_col, gvfk_id_col, substances_col]:
            agg_dict[col] = 'first'

    unique_csv = filtered_csv.groupby([csv_lokalitet_col, gvfk_id_col], as_index=False).agg(agg_dict)

    report_counts(f"{site_type}", sites=unique_sites, gvfks=len(filtered_csv[gvfk_id_col].unique()),
                 combinations=len(unique_csv), indent=1)

    # Join with geometries
    result = geom_data.merge(unique_csv, left_on=locality_col, right_on=csv_lokalitet_col, how='inner')

    if not result.empty:
        result['Lokalitete'] = site_type
        return [result]
    return []


def _combine_and_deduplicate_v1v2(v1_processed, v2_processed):
    """Combine V1 and V2 data and handle duplicate lokalitet-GVFK combinations."""
    if not v1_processed and not v2_processed:
        return gpd.GeoDataFrame()

    datasets = v1_processed + v2_processed
    if not datasets:
        return gpd.GeoDataFrame()

    v1v2_combined_raw = pd.concat(datasets, ignore_index=True)

    # Check for duplicates (same site in both V1 and V2)
    all_combinations = v1v2_combined_raw.groupby(['Lokalitet_', 'Navn']).size()
    duplicate_combinations = all_combinations[all_combinations > 1]

    if len(duplicate_combinations) > 0:
        # For duplicates, aggregate substances and mark as 'V1 og V2'
        v1v2_deduped_list = []

        # Iterate over ALL combinations (not just duplicates)
        print(f"  Processing {len(all_combinations):,} site-GVFK combinations...")
        for (lokalitet_id, gvfk_name), count in tqdm(all_combinations.items(), desc="  Deduplicating", unit="combo"):
            subset = v1v2_combined_raw[
                (v1v2_combined_raw['Lokalitet_'] == lokalitet_id) &
                (v1v2_combined_raw['Navn'] == gvfk_name)
            ]

            if count > 1:
                # Handle duplicates: aggregate substances
                aggregated_record = subset.iloc[0:1].copy()

                all_substances = []
                for _, row in subset.iterrows():
                    substances_str = str(row.get('Lokalitetensstoffer', ''))
                    if pd.notna(substances_str) and substances_str.strip() and substances_str != 'nan':
                        substances = [s.strip() for s in substances_str.split(';') if s.strip()]
                        all_substances.extend(substances)

                if all_substances:
                    unique_substances = list(dict.fromkeys(all_substances))
                    aggregated_record['Lokalitetensstoffer'] = '; '.join(unique_substances)

                aggregated_record['Lokalitete'] = 'V1 og V2'
                v1v2_deduped_list.append(aggregated_record)
            else:
                # Keep single record as is (V1-only or V2-only)
                v1v2_deduped_list.append(subset)

        v1v2_combined = pd.concat(v1v2_deduped_list, ignore_index=True)
    else:
        v1v2_combined = v1v2_combined_raw.copy()

    return v1v2_combined


def _save_step3_results(v1v2_combined, gvfk_with_v1v2_names, site_id_shp_col,
                       gvfk_id_col, grundvand_gvfk_col, input_gvfk_count):
    """Save Step 3 results and generate summary statistics."""
    if v1v2_combined.empty:
        print("\n⚠ No V1/V2 sites found with river contact")
        return

    report_subsection("OUTPUT")

    unique_sites = v1v2_combined[site_id_shp_col].nunique()
    total_combinations = len(v1v2_combined)
    output_gvfk_count = len(gvfk_with_v1v2_names)

    report_counts("Final results", sites=unique_sites, gvfks=output_gvfk_count,
                 combinations=total_combinations, indent=1)

    # Site type breakdown
    if 'Lokalitete' in v1v2_combined.columns:
        locality_types = v1v2_combined.groupby(site_id_shp_col)['Lokalitete'].apply(set).reset_index()
        locality_types['type_summary'] = locality_types['Lokalitete'].apply(
            lambda x: 'V1 og V2' if len(x) > 1 else list(x)[0]
        )
        type_counts = locality_types['type_summary'].value_counts()

        report_breakdown("Site type distribution", {
            "V1 only": type_counts.get('V1', 0),
            "V2 only": type_counts.get('V2', 0),
            "Both V1 & V2": type_counts.get('V1 og V2', 0),
        }, indent=1)

    # GVFKs filtered
    filtered_gvfks = input_gvfk_count - output_gvfk_count
    print(f"\n  Filtered: {filtered_gvfks} GVFKs (no contaminated sites)")

    # Save results
    v1v2_sites_path = get_output_path('step3_v1v2_sites')
    v1v2_combined.to_file(v1v2_sites_path, encoding="utf-8")

    gvf = gpd.read_file(GRUNDVAND_PATH, layer=GRUNDVAND_LAYER_NAME)
    gvfk_with_v1v2_polygons = gvf[gvf[grundvand_gvfk_col].isin(gvfk_with_v1v2_names)]

    gvfk_polygons_path = get_output_path('step3_gvfk_polygons')
    gvfk_with_v1v2_polygons.to_file(gvfk_polygons_path, encoding="utf-8")

    print(f"  Saved: {len(gvfk_with_v1v2_polygons)} GVFK polygon features")


if __name__ == "__main__":
    # Test run (requires Step 2 results)
    from step2_river_contact import run_step2
    rivers_gvfk, _, _ = run_step2()
    run_step3(rivers_gvfk)
