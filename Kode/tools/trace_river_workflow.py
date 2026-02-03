"""
Workflow Tracing Tool
=====================

Traces a specific river (by ov_id) or site (by Lokalitet_ID) through the
entire workflow to understand how segments and sites are handled at each step.

Example usage:
    # Trace a river
    python tools/trace_river_workflow.py --river DKRIVER726
    python tools/trace_river_workflow.py --river DKRIVER726 --verbose

    # Trace a site
    python tools/trace_river_workflow.py --site 731-00045
    python tools/trace_river_workflow.py --site 731-00045 --verbose

    # List available IDs
    python tools/trace_river_workflow.py --list-rivers
    python tools/trace_river_workflow.py --list-sites

This helps answer questions like:
- How many segments does this river have?
- Which segments have GVFK contact?
- Which GVFKs are connected to each segment?
- Which sites are within distance thresholds of each segment?
- What happens to each segment in Step 6 (flux/Cmix)?
- Which GVFKs is a site located in?
- Which river segments are nearest to a site?
- Does the site pass risk thresholds and reach Step 6?
"""

import sys
from pathlib import Path
import pandas as pd
import geopandas as gpd
import argparse

# Add parent directory to path
REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from config import (
    get_output_path,
    RESULTS_DIR,
    COLUMN_MAPPINGS,
    RIVERS_PATH,
    RIVERS_LAYER_NAME,
    GRUNDVAND_PATH,
    GRUNDVAND_LAYER_NAME,
)


def load_rivers():
    """Load the raw rivers dataset."""
    rivers = gpd.read_file(RIVERS_PATH, layer=RIVERS_LAYER_NAME)
    rivers = rivers.reset_index().rename(columns={"index": "River_FID"})
    return rivers


def load_workflow_data():
    """Load all workflow output files."""
    data = {}

    # Step 2: River contact GVFKs
    step2_path = get_output_path("step2_river_gvfk")
    if step2_path.exists():
        data['step2'] = gpd.read_file(step2_path)

    # Step 3: Sites
    step3_path = get_output_path("step3_v1v2_sites")
    if step3_path.exists():
        data['step3'] = gpd.read_file(step3_path)

    # Step 3b: Infiltration filtered
    step3b_path = get_output_path("step3b_filtered_sites")
    if step3b_path.exists():
        data['step3b'] = gpd.read_file(step3b_path)

    # Step 4: Distances
    step4_path = get_output_path("step4_final_distances_for_risk_assessment")
    if step4_path.exists():
        data['step4'] = pd.read_csv(step4_path)

    # Step 5b: Compound combinations
    step5b_path = get_output_path("step5b_compound_combinations")
    if step5b_path.exists():
        data['step5b'] = pd.read_csv(step5b_path)

    # Step 5 detailed (with river FID)
    step5_detail_path = get_output_path("step5_compound_detailed_combinations")
    if step5_detail_path.exists():
        data['step5_detail'] = pd.read_csv(step5_detail_path)

    # Step 6: Flux details
    step6_flux_path = get_output_path("step6_flux_site_segment")
    if step6_flux_path.exists():
        data['step6_flux'] = pd.read_csv(step6_flux_path)

    # Step 6: Cmix results
    step6_cmix_path = get_output_path("step6_cmix_results")
    if step6_cmix_path.exists():
        data['step6_cmix'] = pd.read_csv(step6_cmix_path)

    # Step 6: Segment summary
    step6_summary_path = get_output_path("step6_segment_summary")
    if step6_summary_path.exists():
        data['step6_summary'] = pd.read_csv(step6_summary_path)

    return data


def trace_river(ov_id: str, verbose: bool = False):
    """
    Trace a specific river through the entire workflow.

    Args:
        ov_id: The river identifier (e.g., "DKRIVER726")
        verbose: Print additional details
    """
    print("\n" + "=" * 80)
    print(f"TRACING RIVER: {ov_id}")
    print("=" * 80)

    # Load raw rivers data
    rivers = load_rivers()
    river_gvfk_col = COLUMN_MAPPINGS["rivers"]["gvfk_id"]

    # Filter to this river
    river_segments = rivers[rivers["ov_id"] == ov_id].copy()

    if river_segments.empty:
        print(f"\n❌ River '{ov_id}' not found in rivers dataset!")
        print(f"   Available rivers (sample): {rivers['ov_id'].unique()[:10].tolist()}")
        return

    # =========================================================================
    # SECTION 1: RAW RIVER DATA
    # =========================================================================
    print("\n" + "-" * 80)
    print("1. RAW RIVER DATA (Source)")
    print("-" * 80)

    total_segments = len(river_segments)
    print(f"\nTotal segments in raw data: {total_segments}")

    # Show segment details
    print(f"\nSegment breakdown:")
    print(f"{'FID':<8} {'GVFK':<25} {'Length (m)':<12} {'Has Contact':<12}")
    print("-" * 60)

    for _, seg in river_segments.iterrows():
        fid = seg["River_FID"]
        gvfk = seg.get(river_gvfk_col, "")
        gvfk_str = str(gvfk) if pd.notna(gvfk) and gvfk != "" else "(none)"
        length = seg.get("ov_laengde", seg.get("length", 0))
        has_contact = gvfk_str != "(none)"
        print(f"{fid:<8} {gvfk_str:<25} {length:<12.1f} {str(has_contact):<12}")

    # Segments with GVFK contact
    segments_with_contact = river_segments[
        river_segments[river_gvfk_col].notna() &
        (river_segments[river_gvfk_col] != "")
    ]
    print(f"\nSegments with GVFK contact: {len(segments_with_contact)} / {total_segments}")

    # Unique GVFKs
    unique_gvfks = segments_with_contact[river_gvfk_col].unique().tolist()
    print(f"Connected GVFKs: {unique_gvfks}")

    # Load GVFK metadata to get dkmlag
    try:
        gvfk_data = gpd.read_file(GRUNDVAND_PATH, layer=GRUNDVAND_LAYER_NAME)
        gvfk_col = COLUMN_MAPPINGS["grundvand"]["gvfk_id"]

        print(f"\nGVFK details (from Grunddata):")
        print(f"{'GVFK':<25} {'dkmlag':<15} {'dknr':<10}")
        print("-" * 50)

        for gvfk in unique_gvfks:
            gvfk_row = gvfk_data[gvfk_data[gvfk_col] == gvfk]
            if not gvfk_row.empty:
                dkmlag = gvfk_row.iloc[0].get("dkmlag", "N/A")
                dknr = gvfk_row.iloc[0].get("dknr", "N/A")
                print(f"{gvfk:<25} {str(dkmlag):<15} {str(dknr):<10}")
            else:
                print(f"{gvfk:<25} (not found in Grunddata)")
    except Exception as e:
        print(f"  Could not load GVFK metadata: {e}")

    # =========================================================================
    # SECTION 2: WORKFLOW STEPS
    # =========================================================================
    data = load_workflow_data()

    segment_fids = set(river_segments["River_FID"].tolist())

    # Step 2: River Contact
    print("\n" + "-" * 80)
    print("2. STEP 2: River Contact Filter")
    print("-" * 80)

    if 'step2' in data:
        gvfk_col = COLUMN_MAPPINGS["grundvand"]["gvfk_id"]
        step2_gvfks = set(data['step2'][gvfk_col].unique())
        matching_gvfks = [g for g in unique_gvfks if g in step2_gvfks]
        print(f"GVFKs passing Step 2 filter: {len(matching_gvfks)} / {len(unique_gvfks)}")
        print(f"  Passing: {matching_gvfks}")
        filtered_out = [g for g in unique_gvfks if g not in step2_gvfks]
        if filtered_out:
            print(f"  Filtered out: {filtered_out}")
    else:
        print("  Step 2 data not available")

    # Step 3 & 3b: Sites in these GVFKs
    print("\n" + "-" * 80)
    print("3. STEP 3 & 3b: Sites in Connected GVFKs")
    print("-" * 80)

    if 'step3' in data:
        site_col = 'Lokalitet_' if 'Lokalitet_' in data['step3'].columns else 'Lokalitet_ID'
        gvfk_col = 'Navn' if 'Navn' in data['step3'].columns else 'GVFK'

        step3_in_gvfks = data['step3'][data['step3'][gvfk_col].isin(unique_gvfks)]
        print(f"\nStep 3 - Site-GVFK combinations in river's GVFKs: {len(step3_in_gvfks)}")
        print(f"  Unique sites: {step3_in_gvfks[site_col].nunique()}")

        if verbose and not step3_in_gvfks.empty:
            print(f"\n  Site-GVFK pairs:")
            for _, row in step3_in_gvfks.iterrows():
                print(f"    {row[site_col]} -> {row[gvfk_col]}")

    if 'step3b' in data:
        site_col = 'Lokalitet_' if 'Lokalitet_' in data['step3b'].columns else 'Lokalitet_ID'
        gvfk_col = 'Navn' if 'Navn' in data['step3b'].columns else 'GVFK'

        step3b_in_gvfks = data['step3b'][data['step3b'][gvfk_col].isin(unique_gvfks)]
        print(f"\nStep 3b (after infiltration filter) - Combinations: {len(step3b_in_gvfks)}")
        print(f"  Unique sites: {step3b_in_gvfks[site_col].nunique()}")

        if 'step3' in data:
            removed = len(step3_in_gvfks) - len(step3b_in_gvfks)
            print(f"  Removed by infiltration filter: {removed}")

    # Step 4: Distance calculations
    print("\n" + "-" * 80)
    print("4. STEP 4: Distance Calculations")
    print("-" * 80)

    if 'step4' in data:
        # Filter by either ov_id or segment FID
        step4_by_ov = data['step4'][data['step4']['Nearest_River_ov_id'] == ov_id]
        step4_by_fid = data['step4'][data['step4']['Nearest_River_FID'].isin(segment_fids)]

        print(f"\nCombinations with nearest river = {ov_id}: {len(step4_by_ov)}")
        print(f"Combinations by segment FID match: {len(step4_by_fid)}")

        if not step4_by_ov.empty:
            print(f"\nSegment-level breakdown:")
            print(f"{'FID':<8} {'GVFK':<25} {'Sites':<8} {'Min Dist (m)':<15}")
            print("-" * 60)

            for fid in sorted(step4_by_ov['Nearest_River_FID'].unique()):
                fid_data = step4_by_ov[step4_by_ov['Nearest_River_FID'] == fid]
                gvfks = fid_data['GVFK'].unique()
                gvfk_str = ", ".join(gvfks[:2]) + ("..." if len(gvfks) > 2 else "")
                sites = fid_data['Lokalitet_ID'].nunique()
                min_dist = fid_data['Distance_to_River_m'].min()
                print(f"{int(fid):<8} {gvfk_str:<25} {sites:<8} {min_dist:<15.1f}")

            if verbose:
                print(f"\n  All site-GVFK-segment combinations:")
                for _, row in step4_by_ov.iterrows():
                    print(f"    Site {row['Lokalitet_ID']} | GVFK {row['GVFK']} | "
                          f"FID {int(row['Nearest_River_FID'])} | {row['Distance_to_River_m']:.1f}m")
    else:
        print("  Step 4 data not available")

    # Step 5: Risk Assessment
    print("\n" + "-" * 80)
    print("5. STEP 5: Risk Assessment (Compound-Specific)")
    print("-" * 80)

    step5_data = data.get('step5_detail') if 'step5_detail' in data else data.get('step5b')
    if step5_data is not None:
        if 'Nearest_River_ov_id' in step5_data.columns:
            step5_river = step5_data[step5_data['Nearest_River_ov_id'] == ov_id]
        elif 'Nearest_River_FID' in step5_data.columns:
            step5_river = step5_data[step5_data['Nearest_River_FID'].isin(segment_fids)]
        else:
            step5_river = pd.DataFrame()

        print(f"\nCombinations passing risk thresholds for {ov_id}: {len(step5_river)}")

        if not step5_river.empty:
            print(f"  Unique sites: {step5_river['Lokalitet_ID'].nunique()}")

            if 'Qualifying_Category' in step5_river.columns:
                print(f"\n  Category breakdown:")
                for cat, count in step5_river['Qualifying_Category'].value_counts().items():
                    print(f"    {cat}: {count}")

            if 'Nearest_River_FID' in step5_river.columns:
                print(f"\n  Per-segment breakdown:")
                for fid in sorted(step5_river['Nearest_River_FID'].unique()):
                    fid_data = step5_river[step5_river['Nearest_River_FID'] == fid]
                    sites = fid_data['Lokalitet_ID'].nunique()
                    categories = fid_data['Qualifying_Category'].unique() if 'Qualifying_Category' in fid_data.columns else []
                    print(f"    FID {int(fid)}: {sites} sites, categories: {list(categories)}")
    else:
        print("  Step 5 data not available")

    # Step 6: Flux and Cmix
    print("\n" + "-" * 80)
    print("6. STEP 6: Flux Calculation and Cmix")
    print("-" * 80)

    if 'step6_flux' in data:
        step6_flux = data['step6_flux']

        if 'Nearest_River_ov_id' in step6_flux.columns:
            flux_river = step6_flux[step6_flux['Nearest_River_ov_id'] == ov_id]
        elif 'Nearest_River_FID' in step6_flux.columns:
            flux_river = step6_flux[step6_flux['Nearest_River_FID'].isin(segment_fids)]
        else:
            flux_river = pd.DataFrame()

        print(f"\nFlux records for {ov_id}: {len(flux_river)}")

        if not flux_river.empty:
            print(f"  Unique sites contributing: {flux_river['Lokalitet_ID'].nunique()}")
            total_flux = flux_river['Pollution_Flux_kg_per_year'].sum()
            print(f"  Total flux: {total_flux:.4f} kg/year")

            if 'Nearest_River_FID' in flux_river.columns:
                print(f"\n  Flux by segment:")
                print(f"  {'FID':<8} {'Sites':<8} {'Flux (kg/yr)':<15} {'Categories'}")
                print("  " + "-" * 60)

                for fid in sorted(flux_river['Nearest_River_FID'].unique()):
                    fid_flux = flux_river[flux_river['Nearest_River_FID'] == fid]
                    sites = fid_flux['Lokalitet_ID'].nunique()
                    flux = fid_flux['Pollution_Flux_kg_per_year'].sum()
                    cats = fid_flux['Qualifying_Category'].unique() if 'Qualifying_Category' in fid_flux.columns else []
                    cats_str = ", ".join(cats[:2]) + ("..." if len(cats) > 2 else "")
                    print(f"  {int(fid):<8} {sites:<8} {flux:<15.6f} {cats_str}")
    else:
        print("  Step 6 flux data not available")

    # Step 6: Cmix results
    if 'step6_cmix' in data:
        step6_cmix = data['step6_cmix']

        if 'Nearest_River_ov_id' in step6_cmix.columns:
            cmix_river = step6_cmix[step6_cmix['Nearest_River_ov_id'] == ov_id]
        elif 'Nearest_River_FID' in step6_cmix.columns:
            cmix_river = step6_cmix[step6_cmix['Nearest_River_FID'].isin(segment_fids)]
        else:
            cmix_river = pd.DataFrame()

        print(f"\n  Cmix scenarios for {ov_id}: {len(cmix_river)}")

        if not cmix_river.empty and 'Exceedance_Flag' in cmix_river.columns:
            exceedances = cmix_river[cmix_river['Exceedance_Flag'] == True]
            print(f"  MKK exceedances: {len(exceedances)}")

            if not exceedances.empty:
                print(f"\n  Exceedance details:")
                print(f"  {'FID':<8} {'Scenario':<10} {'Category':<20} {'Cmix (µg/L)':<12} {'MKK':<10} {'Ratio'}")
                print("  " + "-" * 80)

                for _, row in exceedances.head(10).iterrows():
                    fid = int(row.get('Nearest_River_FID', 0))
                    scenario = row.get('Flow_Scenario', 'N/A')
                    cat = row.get('Qualifying_Category', 'N/A')
                    cmix = row.get('Cmix_ug_L', 0)
                    mkk = row.get('MKK_ug_L', 0)
                    ratio = row.get('Exceedance_Ratio', 0)
                    print(f"  {fid:<8} {scenario:<10} {cat:<20} {cmix:<12.4f} {mkk:<10.2f} {ratio:.2f}x")

    # Step 6: Segment summary
    if 'step6_summary' in data:
        step6_summary = data['step6_summary']

        if 'Nearest_River_ov_id' in step6_summary.columns:
            summary_river = step6_summary[step6_summary['Nearest_River_ov_id'] == ov_id]
        elif 'Nearest_River_FID' in step6_summary.columns:
            summary_river = step6_summary[step6_summary['Nearest_River_FID'].isin(segment_fids)]
        else:
            summary_river = pd.DataFrame()

        if not summary_river.empty:
            print(f"\n  Segment summary:")
            print(f"  {'FID':<8} {'Sites':<8} {'Flux (kg/yr)':<15} {'Max Cmix':<12} {'Exceeds MKK'}")
            print("  " + "-" * 60)

            for _, row in summary_river.iterrows():
                fid = int(row.get('Nearest_River_FID', 0))
                sites = row.get('Site_Count', 0)
                flux = row.get('Total_Flux_kg_per_year', 0)
                max_cmix = row.get('Max_Cmix_ug_L', 0)
                exceeds = row.get('Has_MKK_Exceedance', False)
                print(f"  {fid:<8} {sites:<8} {flux:<15.6f} {max_cmix:<12.4f} {str(exceeds)}")

    # =========================================================================
    # SUMMARY
    # =========================================================================
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)

    print(f"\nRiver {ov_id}:")
    print(f"  Total segments in raw data: {total_segments}")
    print(f"  Segments with GVFK contact: {len(segments_with_contact)}")
    print(f"  Connected GVFKs: {len(unique_gvfks)}")

    if 'step6_summary' in data and not summary_river.empty:
        segments_in_step6 = summary_river['Nearest_River_FID'].nunique()
        total_sites = summary_river['Site_Count'].sum() if 'Site_Count' in summary_river.columns else 0
        has_exceedance = summary_river['Has_MKK_Exceedance'].any() if 'Has_MKK_Exceedance' in summary_river.columns else False
        print(f"\n  Segments reaching Step 6: {segments_in_step6}")
        print(f"  Total contributing sites: {int(total_sites)}")
        print(f"  Has MKK exceedance: {has_exceedance}")


def trace_site(lokalitet_id: str, verbose: bool = False):
    """
    Trace a specific site through the entire workflow.

    Args:
        lokalitet_id: The site identifier (e.g., "731-00045")
        verbose: Print additional details
    """
    print("\n" + "=" * 80)
    print(f"TRACING SITE: {lokalitet_id}")
    print("=" * 80)

    data = load_workflow_data()
    rivers = load_rivers()

    # =========================================================================
    # SECTION 1: STEP 3 - Site in GVFKs
    # =========================================================================
    print("\n" + "-" * 80)
    print("1. STEP 3: Site Location (GVFKs)")
    print("-" * 80)

    if 'step3' in data:
        site_col = 'Lokalitet_' if 'Lokalitet_' in data['step3'].columns else 'Lokalitet_ID'
        gvfk_col = 'Navn' if 'Navn' in data['step3'].columns else 'GVFK'

        site_step3 = data['step3'][data['step3'][site_col] == lokalitet_id]

        if site_step3.empty:
            print(f"\n  Site '{lokalitet_id}' not found in Step 3!")
            print("  (Site may not be V1/V2 or not located in any GVFK with river contact)")
            return

        gvfks = site_step3[gvfk_col].unique().tolist()
        print(f"\n  Site is located in {len(gvfks)} GVFK(s): {gvfks}")

        # Load GVFK metadata
        try:
            gvfk_data = gpd.read_file(GRUNDVAND_PATH, layer=GRUNDVAND_LAYER_NAME)
            gvfk_id_col = COLUMN_MAPPINGS["grundvand"]["gvfk_id"]

            print(f"\n  GVFK details:")
            print(f"  {'GVFK':<25} {'dkmlag':<15} {'dknr':<10}")
            print("  " + "-" * 50)

            for gvfk in gvfks:
                gvfk_row = gvfk_data[gvfk_data[gvfk_id_col] == gvfk]
                if not gvfk_row.empty:
                    dkmlag = gvfk_row.iloc[0].get("dkmlag", "N/A")
                    dknr = gvfk_row.iloc[0].get("dknr", "N/A")
                    print(f"  {gvfk:<25} {str(dkmlag):<15} {str(dknr):<10}")
        except Exception as e:
            print(f"  Could not load GVFK metadata: {e}")
    else:
        print("  Step 3 data not available")
        return

    # =========================================================================
    # SECTION 2: STEP 3b - After Infiltration Filter
    # =========================================================================
    print("\n" + "-" * 80)
    print("2. STEP 3b: Infiltration Filter")
    print("-" * 80)

    if 'step3b' in data:
        site_col = 'Lokalitet_' if 'Lokalitet_' in data['step3b'].columns else 'Lokalitet_ID'
        gvfk_col = 'Navn' if 'Navn' in data['step3b'].columns else 'GVFK'

        site_step3b = data['step3b'][data['step3b'][site_col] == lokalitet_id]

        gvfks_before = set(gvfks)
        gvfks_after = set(site_step3b[gvfk_col].unique()) if not site_step3b.empty else set()
        gvfks_removed = gvfks_before - gvfks_after

        print(f"\n  Before filter: {len(gvfks_before)} GVFK(s)")
        print(f"  After filter: {len(gvfks_after)} GVFK(s)")

        if gvfks_removed:
            print(f"  Removed (upward flow): {list(gvfks_removed)}")

        if site_step3b.empty:
            print(f"\n  Site filtered out completely (all GVFKs had upward flow)")
            return
    else:
        print("  Step 3b data not available")

    # =========================================================================
    # SECTION 3: STEP 4 - Distance Calculations
    # =========================================================================
    print("\n" + "-" * 80)
    print("3. STEP 4: Distance to Rivers")
    print("-" * 80)

    if 'step4' in data:
        site_step4 = data['step4'][data['step4']['Lokalitet_ID'] == lokalitet_id]

        if site_step4.empty:
            print(f"\n  Site not found in Step 4 (no valid distances calculated)")
            return

        print(f"\n  Site-GVFK combinations with distances: {len(site_step4)}")

        print(f"\n  {'GVFK':<20} {'Nearest River':<15} {'FID':<8} {'Distance (m)':<15} {'Segments in GVFK'}")
        print("  " + "-" * 75)

        for _, row in site_step4.iterrows():
            gvfk = row['GVFK']
            ov_id = row.get('Nearest_River_ov_id', 'N/A')
            fid = int(row['Nearest_River_FID'])
            dist = row['Distance_to_River_m']
            seg_count = row.get('River_Segment_Count', 'N/A')
            print(f"  {gvfk:<20} {ov_id:<15} {fid:<8} {dist:<15.1f} {seg_count}")

        if verbose:
            print(f"\n  All matching segment FIDs per GVFK:")
            for _, row in site_step4.iterrows():
                gvfk = row['GVFK']
                fids = row.get('River_Segment_FIDs', '')
                print(f"    {gvfk}: {fids[:80]}{'...' if len(str(fids)) > 80 else ''}")
    else:
        print("  Step 4 data not available")

    # =========================================================================
    # SECTION 4: STEP 5 - Risk Assessment
    # =========================================================================
    print("\n" + "-" * 80)
    print("4. STEP 5: Risk Assessment (Compound-Specific)")
    print("-" * 80)

    step5_data = data.get('step5_detail') if 'step5_detail' in data else data.get('step5b')
    if step5_data is not None:
        site_step5 = step5_data[step5_data['Lokalitet_ID'] == lokalitet_id]

        if site_step5.empty:
            print(f"\n  Site did not pass compound-specific thresholds")
            print("  (Distance exceeds threshold for all compound categories)")
            return

        print(f"\n  Combinations passing thresholds: {len(site_step5)}")

        if 'Qualifying_Category' in site_step5.columns:
            print(f"\n  Categories: {site_step5['Qualifying_Category'].unique().tolist()}")

        if 'Qualifying_Substance' in site_step5.columns and verbose:
            print(f"  Substances: {site_step5['Qualifying_Substance'].unique().tolist()}")

        print(f"\n  {'GVFK':<20} {'Category':<25} {'Threshold (m)':<15} {'Distance (m)'}")
        print("  " + "-" * 75)

        for _, row in site_step5.drop_duplicates(['GVFK', 'Qualifying_Category']).iterrows():
            gvfk = row['GVFK']
            cat = row.get('Qualifying_Category', 'N/A')
            threshold = row.get('Category_Threshold_m', 'N/A')
            dist = row.get('Distance_to_River_m', 'N/A')
            print(f"  {gvfk:<20} {cat:<25} {threshold:<15} {dist}")
    else:
        print("  Step 5 data not available")

    # =========================================================================
    # SECTION 5: STEP 6 - Flux and Cmix
    # =========================================================================
    print("\n" + "-" * 80)
    print("5. STEP 6: Flux and Cmix")
    print("-" * 80)

    if 'step6_flux' in data:
        site_flux = data['step6_flux'][data['step6_flux']['Lokalitet_ID'] == lokalitet_id]

        if site_flux.empty:
            print(f"\n  Site has no flux records in Step 6")
            print("  (May have been filtered by infiltration or missing concentration data)")
            return

        print(f"\n  Flux records: {len(site_flux)}")

        total_flux = site_flux['Pollution_Flux_kg_per_year'].sum()
        print(f"  Total flux from site: {total_flux:.6f} kg/year")

        print(f"\n  {'GVFK':<20} {'River':<15} {'FID':<8} {'Category':<20} {'Flux (kg/yr)'}")
        print("  " + "-" * 80)

        for _, row in site_flux.iterrows():
            gvfk = row.get('GVFK', 'N/A')
            ov_id = row.get('Nearest_River_ov_id', 'N/A')
            fid = int(row.get('Nearest_River_FID', 0))
            cat = row.get('Qualifying_Category', 'N/A')
            flux = row.get('Pollution_Flux_kg_per_year', 0)
            print(f"  {gvfk:<20} {ov_id:<15} {fid:<8} {cat:<20} {flux:.6f}")

        if verbose:
            print(f"\n  Detailed flux parameters:")
            for _, row in site_flux.head(3).iterrows():
                print(f"    GVFK: {row.get('GVFK')}")
                print(f"      Area: {row.get('Area_m2', 'N/A')} m²")
                print(f"      Infiltration: {row.get('Infiltration_mm_per_year', 'N/A')} mm/yr")
                print(f"      Concentration: {row.get('Standard_Concentration_ug_L', 'N/A')} µg/L")
    else:
        print("  Step 6 flux data not available")

    # Check for MKK exceedances
    if 'step6_cmix' in data:
        # Find segments this site contributes to
        if 'step6_flux' in data and not site_flux.empty:
            site_fids = site_flux['Nearest_River_FID'].unique()
            site_cmix = data['step6_cmix'][data['step6_cmix']['Nearest_River_FID'].isin(site_fids)]

            if not site_cmix.empty and 'Exceedance_Flag' in site_cmix.columns:
                exceedances = site_cmix[site_cmix['Exceedance_Flag'] == True]

                print(f"\n  MKK Exceedances on segments this site contributes to:")
                if exceedances.empty:
                    print("    None")
                else:
                    print(f"  {'FID':<8} {'Scenario':<10} {'Cmix (µg/L)':<12} {'MKK':<10} {'Ratio'}")
                    print("  " + "-" * 50)
                    for _, row in exceedances.iterrows():
                        fid = int(row.get('Nearest_River_FID', 0))
                        scenario = row.get('Flow_Scenario', 'N/A')
                        cmix = row.get('Cmix_ug_L', 0)
                        mkk = row.get('MKK_ug_L', 0)
                        ratio = row.get('Exceedance_Ratio', 0)
                        print(f"  {fid:<8} {scenario:<10} {cmix:<12.4f} {mkk:<10.2f} {ratio:.2f}x")

    # =========================================================================
    # SUMMARY
    # =========================================================================
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)

    print(f"\nSite {lokalitet_id}:")
    print(f"  GVFKs in Step 3: {len(gvfks)}")
    if 'step3b' in data:
        print(f"  GVFKs after infiltration filter: {len(gvfks_after)}")
    if 'step4' in data and not site_step4.empty:
        print(f"  Combinations with distances: {len(site_step4)}")
        min_dist = site_step4['Distance_to_River_m'].min()
        print(f"  Minimum distance to river: {min_dist:.1f} m")
    if step5_data is not None and not site_step5.empty:
        print(f"  Passed risk thresholds: Yes ({len(site_step5)} combinations)")
    else:
        print(f"  Passed risk thresholds: No")
    if 'step6_flux' in data and not site_flux.empty:
        print(f"  In Step 6: Yes (flux: {total_flux:.6f} kg/yr)")
    else:
        print(f"  In Step 6: No")


def main():
    parser = argparse.ArgumentParser(
        description="Trace a specific river or site through the workflow",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Trace a river
    python tools/trace_river_workflow.py --river DKRIVER726
    python tools/trace_river_workflow.py --river DKRIVER726 --verbose

    # Trace a site
    python tools/trace_river_workflow.py --site 731-00045
    python tools/trace_river_workflow.py --site 731-00045 --verbose

    # List available IDs
    python tools/trace_river_workflow.py --list-rivers
    python tools/trace_river_workflow.py --list-sites
        """
    )
    parser.add_argument("--river", "-r", help="River ID to trace (e.g., DKRIVER726)")
    parser.add_argument("--site", "-s", help="Site ID to trace (e.g., 731-00045)")
    parser.add_argument("--verbose", "-v", action="store_true", help="Print detailed output")
    parser.add_argument("--list-rivers", action="store_true", help="List available river IDs")
    parser.add_argument("--list-sites", action="store_true", help="List available site IDs")

    # Legacy support: positional argument as river ID
    parser.add_argument("ov_id", nargs="?", help="(Legacy) River ID to trace")

    args = parser.parse_args()

    if args.list_rivers:
        rivers = load_rivers()
        print("\nAvailable river IDs (showing first 50):")
        for ov_id in sorted(rivers["ov_id"].unique())[:50]:
            count = len(rivers[rivers["ov_id"] == ov_id])
            print(f"  {ov_id} ({count} segments)")
        print(f"\nTotal unique rivers: {rivers['ov_id'].nunique()}")
        return

    if args.list_sites:
        data = load_workflow_data()
        if 'step4' in data:
            sites = sorted(data['step4']['Lokalitet_ID'].unique())
            print(f"\nAvailable site IDs in Step 4 (showing first 50 of {len(sites)}):")
            for site_id in sites[:50]:
                print(f"  {site_id}")
            print(f"\nTotal unique sites: {len(sites)}")
        else:
            print("Step 4 data not available")
        return

    # Determine what to trace
    if args.site:
        trace_site(args.site, verbose=args.verbose)
    elif args.river:
        trace_river(args.river, verbose=args.verbose)
    elif args.ov_id:
        # Legacy support
        trace_river(args.ov_id, verbose=args.verbose)
    else:
        parser.print_help()
        print("\nError: Please provide --river or --site to trace")


if __name__ == "__main__":
    main()
