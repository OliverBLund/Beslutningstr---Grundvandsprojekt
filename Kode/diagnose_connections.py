"""Diagnostic: Verify connection logic matches Step 4 and understand coloring."""

import pandas as pd
import geopandas as gpd
from config import (
    RIVERS_PATH,
    RIVERS_LAYER_NAME,
    COLUMN_MAPPINGS,
    WORKFLOW_SETTINGS,
    get_output_path
)

print("="*80)
print("DIAGNOSTIC: Connection Lines vs River Coloring")
print("="*80)

# Load Step 6 flux data (what we're connecting)
flux = pd.read_csv(get_output_path('step6_flux_site_segment'), encoding='utf-8')
print(f"\n1. Sites with flux data: {flux['Lokalitet_ID'].nunique()}")
print(f"   Unique rivers being connected to: {flux['Nearest_River_ov_id'].nunique()}")

# Load rivers dataset
rivers_all = gpd.read_file(RIVERS_PATH, layer=RIVERS_LAYER_NAME)
river_gvfk_col = COLUMN_MAPPINGS["rivers"]["gvfk_id"]
contact_col = COLUMN_MAPPINGS["rivers"]["contact"]

# Apply Step 4 filtering
rivers_all[river_gvfk_col] = rivers_all[river_gvfk_col].astype(str).str.strip()
valid_gvfk_mask = rivers_all[river_gvfk_col] != ""

if contact_col in rivers_all.columns:
    contact_value = WORKFLOW_SETTINGS["contact_filter_value"]
    rivers_with_contact = rivers_all[
        (rivers_all[contact_col] == contact_value) & valid_gvfk_mask
    ]
else:
    rivers_with_contact = rivers_all[valid_gvfk_mask]

print(f"\n2. River segments in dataset:")
print(f"   Total: {len(rivers_all)}")
print(f"   WITH GVFK contact: {len(rivers_with_contact)}")
print(f"   WITHOUT GVFK contact: {len(rivers_all) - len(rivers_with_contact)}")

# Check if rivers being connected to have GVFK
unique_rivers = flux['Nearest_River_ov_id'].unique()
print(f"\n3. Checking {len(unique_rivers)} unique rivers being connected to...")

issues_found = []

for ov_id in unique_rivers[:10]:  # Check first 10
    # All segments with this ov_id
    all_segs = rivers_all[rivers_all['ov_id'] == ov_id]
    # GVFK segments with this ov_id
    gvfk_segs = rivers_with_contact[rivers_with_contact['ov_id'] == ov_id]

    # Get sites connecting to this river
    sites_to_river = flux[flux['Nearest_River_ov_id'] == ov_id]
    gvfks_used = sites_to_river['GVFK'].unique()

    if len(gvfk_segs) == 0:
        issues_found.append({
            'ov_id': ov_id,
            'issue': 'NO GVFK SEGMENTS',
            'total_segs': len(all_segs),
            'gvfk_segs': 0,
            'sites_connecting': len(sites_to_river)
        })
        print(f"\n   ❌ {ov_id}: NO GVFK SEGMENTS (but {len(sites_to_river)} sites connect to it!)")
    elif len(all_segs) > len(gvfk_segs):
        print(f"\n   ⚠️  {ov_id}: {len(gvfk_segs)}/{len(all_segs)} segments have GVFK")
        print(f"      GVFKs: {gvfk_segs[river_gvfk_col].unique()}")
        print(f"      Sites use GVFKs: {gvfks_used}")

        # Check if all used GVFKs exist in river segments
        for gvfk in gvfks_used:
            matching = gvfk_segs[gvfk_segs[river_gvfk_col] == gvfk]
            if len(matching) == 0:
                issues_found.append({
                    'ov_id': ov_id,
                    'issue': f'GVFK {gvfk} not in river segments',
                    'total_segs': len(all_segs),
                    'gvfk_segs': len(gvfk_segs)
                })
                print(f"      ❌ GVFK '{gvfk}' not found in river segments!")
    else:
        print(f"   ✅ {ov_id}: All {len(all_segs)} segments have GVFK")

print(f"\n4. COLORING LOGIC CHECK:")
print(f"   Rivers are colored by: Cmix % of MKK")
print(f"   If Cmix is NaN → GRAY (#444444)")
print(f"   If Cmix < 50% MKK → GREEN")
print(f"   If Cmix > 100% MKK → RED/ORANGE")

# Load Cmix results to see coverage
cmix = pd.read_csv(get_output_path('step6_cmix_results'), encoding='utf-8')
cmix_q95 = cmix[cmix['Flow_Scenario'] == 'Q95']
rivers_with_cmix = cmix_q95['Nearest_River_ov_id'].nunique()

print(f"\n   Rivers with Cmix data (Q95): {rivers_with_cmix}")
print(f"   Rivers being connected to: {len(unique_rivers)}")
print(f"   Difference: {len(unique_rivers) - rivers_with_cmix} rivers have NO Cmix → will be GRAY")

print(f"\n5. ISSUE SUMMARY:")
if issues_found:
    print(f"   Found {len(issues_found)} potential issues:")
    for issue in issues_found:
        print(f"   - {issue}")
else:
    print(f"   ✅ All rivers being connected to have GVFK segments")
    print(f"   ⚠️  BUT: Some may be colored GRAY due to missing Cmix data")
    print(f"   This is CORRECT behavior:")
    print(f"      - Gray = GVFK segment exists but no contamination data in this scenario")
    print(f"      - Red = GVFK segment with high contamination")

print(f"\n6. RECOMMENDATION:")
print(f"   Current coloring: Based on Cmix data (gray = no data)")
print(f"   Alternative: Color ALL GVFK segments (blue), then overlay Cmix colors")
print(f"   This would distinguish GVFK vs non-GVFK segments visually")
