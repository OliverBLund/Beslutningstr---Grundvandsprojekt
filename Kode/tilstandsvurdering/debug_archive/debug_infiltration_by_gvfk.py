"""
Debug script to check if the same site has different infiltration values in different GVFKs
"""

import pandas as pd
import sys
sys.path.append('..')
from config import INPUT_STEP5_GVAERDIER_FILE, INPUT_STEP4_DISTANCES_FILE

def check_infiltration_differences():
    """Check if sites in multiple GVFKs have different infiltration values"""

    # Load data
    print("Loading Step 5 data...")
    step5 = pd.read_csv(INPUT_STEP5_GVAERDIER_FILE, sep=';', encoding='utf-8-sig')

    print(f"Total rows in Step 5: {len(step5)}")
    print(f"Unique sites: {step5['Lokalitet_ID'].nunique()}")

    # Find sites appearing in multiple GVFKs
    print("\n" + "="*80)
    print("Finding sites in multiple GVFKs...")
    site_gvfk_counts = step5.groupby('Lokalitet_ID')['GVFK'].nunique()
    multi_gvfk_sites = site_gvfk_counts[site_gvfk_counts > 1]

    print(f"Sites appearing in multiple GVFKs: {len(multi_gvfk_sites)}")

    if len(multi_gvfk_sites) == 0:
        print("No sites found in multiple GVFKs!")
        return

    # Check infiltration variation for these sites
    print("\n" + "="*80)
    print("Checking infiltration values for multi-GVFK sites...")

    infiltration_varies = 0
    infiltration_same = 0
    examples = []

    for site_id in multi_gvfk_sites.index[:20]:  # Check first 20
        site_data = step5[step5['Lokalitet_ID'] == site_id]

        # Get unique (GVFK, Infiltration) combinations
        gvfk_infilt = site_data[['GVFK', 'Infiltration_mm_per_year']].drop_duplicates()

        unique_infiltrations = gvfk_infilt['Infiltration_mm_per_year'].nunique()

        if unique_infiltrations > 1:
            infiltration_varies += 1
            if len(examples) < 3:
                examples.append((site_id, gvfk_infilt))
        else:
            infiltration_same += 1

    print(f"\nOut of {len(multi_gvfk_sites)} multi-GVFK sites:")
    print(f"  - Sites with DIFFERENT infiltration per GVFK: {infiltration_varies}")
    print(f"  - Sites with SAME infiltration across GVFKs: {infiltration_same}")

    # Show examples
    if examples:
        print("\n" + "="*80)
        print("EXAMPLES of sites with different infiltration values:")
        for site_id, gvfk_infilt in examples:
            print(f"\nSite: {site_id}")
            print(gvfk_infilt.to_string(index=False))

            # Check what river segments they connect to
            site_step5 = step5[step5['Lokalitet_ID'] == site_id]
            print(f"  Appears in {site_step5['GVFK'].nunique()} GVFKs")

            # Load distances to see which rivers
            distances = pd.read_csv(INPUT_STEP4_DISTANCES_FILE, sep=';', encoding='utf-8-sig')
            site_distances = distances[distances['Lokalitet_ID'] == site_id]
            if not site_distances.empty:
                river_info = site_distances[['GVFK', 'Nearest_River_ov_id', 'Distance_to_River_m']].drop_duplicates()
                print(f"  River connections:")
                print(river_info.to_string(index=False))

    # Calculate impact on flux
    print("\n" + "="*80)
    print("IMPACT ANALYSIS:")
    if infiltration_varies > 0:
        print(f"⚠️  {infiltration_varies} sites have different infiltration values in different GVFKs")
        print(f"   This means the current grouping by (Site, ov_id, Category) is INCORRECT")
        print(f"   because it discards the different infiltration values!")
        print(f"\n   Example: If Site A in GVFK1 has I=200 mm/yr and in GVFK2 has I=150 mm/yr,")
        print(f"   and both contribute to the same river, we should calculate:")
        print(f"     J1 = A × C × 200  (from GVFK1)")
        print(f"     J2 = A × C × 150  (from GVFK2)")
        print(f"     Total flux = J1 + J2")
        print(f"\n   But current code only uses one I value (whichever comes first)!")
    else:
        print(f"✓ All multi-GVFK sites have the SAME infiltration value across GVFKs")
        print(f"  The current grouping approach is acceptable.")

if __name__ == "__main__":
    check_infiltration_differences()
