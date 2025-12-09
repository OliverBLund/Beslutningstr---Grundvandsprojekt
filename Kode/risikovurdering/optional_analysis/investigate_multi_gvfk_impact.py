"""
Investigate the impact of multi-GVFK approach on Step 5b results
"""

import pandas as pd
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import get_output_path

print("=" * 80)
print("MULTI-GVFK IMPACT ANALYSIS - STEP 5B")
print("=" * 80)

# Load Step 5b compound-specific results
step5b_file = get_output_path("step5_compound_detailed_combinations")
df_compound = pd.read_csv(step5b_file)

print("\n1. CURRENT STEP 5B RESULTS (NEW MULTI-GVFK APPROACH):")
print("-" * 80)
total_combinations = len(df_compound)
unique_sites = df_compound["Lokalitet_ID"].nunique()
unique_gvfks = df_compound["GVFK"].dropna().nunique()

print(f"Total site-GVFK-substance combinations: {total_combinations:,}")
print(f"Unique sites: {unique_sites:,}")
print(f"Unique GVFKs: {unique_gvfks:,}")

# Analyze multi-GVFK sites in Step 5b
print("\n2. MULTI-GVFK SITE DISTRIBUTION IN STEP 5B:")
print("-" * 80)

gvfks_per_site = df_compound.groupby("Lokalitet_ID")["GVFK"].nunique()

single_gvfk_sites = (gvfks_per_site == 1).sum()
multi_gvfk_sites = (gvfks_per_site > 1).sum()

print(
    f"Sites associated with only 1 GVFK: {single_gvfk_sites:,} ({single_gvfk_sites / unique_sites * 100:.1f}%)"
)
print(
    f"Sites associated with 2+ GVFKs: {multi_gvfk_sites:,} ({multi_gvfk_sites / unique_sites * 100:.1f}%)"
)

distribution = {
    "1 GVFK": (gvfks_per_site == 1).sum(),
    "2 GVFKs": (gvfks_per_site == 2).sum(),
    "3 GVFKs": (gvfks_per_site == 3).sum(),
    "4+ GVFKs": (gvfks_per_site >= 4).sum(),
}

print("\nDetailed distribution:")
for category, count in distribution.items():
    pct = (count / unique_sites * 100) if unique_sites > 0 else 0
    print(f"  {category:<10} {count:>6,} sites ({pct:>5.1f}%)")

# Calculate what OLD approach would have produced
print("\n3. SIMULATING OLD APPROACH (MINIMUM DISTANCE ONLY):")
print("-" * 80)

# For each site, find the combination with minimum distance
old_approach_combos = []
for site_id in df_compound["Lokalitet_ID"].unique():
    site_data = df_compound[df_compound["Lokalitet_ID"] == site_id]

    # Find minimum distance for this site
    min_dist = site_data["Distance_to_River_m"].min()

    # Get all combinations at minimum distance (could be multiple GVFKs)
    min_dist_combos = site_data[site_data["Distance_to_River_m"] == min_dist]

    # OLD approach would take just the first one (e.g., alphabetically by GVFK)
    old_combo = min_dist_combos.sort_values("GVFK").iloc[0]
    old_approach_combos.append(old_combo)

old_approach_df = pd.DataFrame(old_approach_combos)
old_unique_sites = old_approach_df["Lokalitet_ID"].nunique()
old_unique_gvfks = old_approach_df["GVFK"].nunique()
old_combinations = len(old_approach_df)

print(f"Old approach would have kept:")
print(f"  Combinations: {old_combinations:,} (1 per site)")
print(f"  Unique sites: {old_unique_sites:,}")
print(f"  Unique GVFKs: {old_unique_gvfks:,}")

# Calculate the gain
print("\n4. GAIN FROM MULTI-GVFK APPROACH:")
print("-" * 80)

combination_gain = total_combinations - old_combinations
gvfk_gain = unique_gvfks - old_unique_gvfks
site_gain = unique_sites - old_unique_sites

print(f"Additional combinations retained: +{combination_gain:,}")
print(
    f"Additional GVFKs identified: +{gvfk_gain:,} ({gvfk_gain / old_unique_gvfks * 100:.1f}% gain)"
)
print(f"Additional sites identified: +{site_gain:,}")

# Find GVFKs that are ONLY identified through multi-GVFK approach
old_gvfks = set(old_approach_df["GVFK"].unique())
new_gvfks = set(df_compound["GVFK"].unique())
exclusive_new_gvfks = new_gvfks - old_gvfks

if exclusive_new_gvfks:
    print(f"\nNew GVFKs found ONLY via multi-GVFK approach: {len(exclusive_new_gvfks)}")
    print(f"(These would have been missed by old minimum-distance approach)")

    # Show examples
    examples = list(exclusive_new_gvfks)[:10]
    for gvfk in examples:
        # Find sites contributing to this GVFK
        gvfk_sites = df_compound[df_compound["GVFK"] == gvfk]["Lokalitet_ID"].unique()

        if len(gvfk_sites) > 0:
            example_site = gvfk_sites[0]

            # Get distance to this GVFK
            dist_here = df_compound[
                (df_compound["GVFK"] == gvfk)
                & (df_compound["Lokalitet_ID"] == example_site)
            ]["Distance_to_River_m"].iloc[0]

            # Get minimum distance for this site (to any GVFK)
            min_dist = df_compound[df_compound["Lokalitet_ID"] == example_site][
                "Distance_to_River_m"
            ].min()

            min_gvfk = df_compound[
                (df_compound["Lokalitet_ID"] == example_site)
                & (df_compound["Distance_to_River_m"] == min_dist)
            ]["GVFK"].iloc[0]

            print(f"  • {gvfk}: Site {example_site}")
            print(
                f"      {dist_here:.0f}m to this GVFK, but min={min_dist:.0f}m to {min_gvfk}"
            )

# Investigate sites that appear in Step 5b but might not in old approach
print("\n5. CHECKING: ARE THERE NEW UNIQUE SITES IN STEP 5B?")
print("-" * 80)

# The question: does multi-GVFK approach find sites that OLD approach would miss entirely?
# This would happen if a site meets compound-specific threshold for GVFK #2 but not GVFK #1 (minimum)

# Load Step 4 results to check all combinations
step4_file = get_output_path("step4_final_distances_for_risk_assessment")
df_step4 = pd.read_csv(step4_file)

# For sites in Step 5b, check if their minimum distance would have qualified
sites_analysis = []

for site_id in df_compound["Lokalitet_ID"].unique():
    # Get all Step 4 combinations for this site
    site_step4 = df_step4[df_step4["Lokalitet_ID"] == site_id]

    # Get minimum distance across ALL GVFKs for this site
    min_dist_overall = site_step4["Distance_to_River_m"].min()

    # Get Step 5b combinations for this site
    site_step5b = df_compound[df_compound["Lokalitet_ID"] == site_id]

    # Check if site qualifies at minimum distance
    # This is complex because Step 5b uses compound-specific thresholds
    # We need to check if the site would qualify at its minimum distance

    # For simplicity, let's check if site has combinations at non-minimum distances
    min_dist_in_step5b = site_step5b["Distance_to_River_m"].min()
    max_dist_in_step5b = site_step5b["Distance_to_River_m"].max()

    has_non_min = (
        min_dist_in_step5b < min_dist_overall or max_dist_in_step5b > min_dist_in_step5b
    )

    sites_analysis.append(
        {
            "Lokalitet_ID": site_id,
            "Min_Dist_Overall": min_dist_overall,
            "Min_Dist_in_Step5b": min_dist_in_step5b,
            "Max_Dist_in_Step5b": max_dist_in_step5b,
            "Num_GVFKs_Step5b": len(site_step5b["GVFK"].unique()),
            "Has_Non_Min_Distance": has_non_min,
        }
    )

sites_df = pd.DataFrame(sites_analysis)

# Count sites where Step 5b includes non-minimum distances
sites_with_non_min = sites_df[sites_df["Has_Non_Min_Distance"] == True]

print(
    f"Sites with combinations beyond their minimum distance: {len(sites_with_non_min):,}"
)
print(f"Percentage: {len(sites_with_non_min) / len(sites_df) * 100:.1f}%")

# Key insight: The +32 sites difference (1711 → 1743)
print("\n6. EXPLAINING THE +32 SITES DIFFERENCE (1,711 → 1,743):")
print("-" * 80)
print(f"This suggests that the old slide (1,711) was calculated using the")
print(
    f"old minimum-distance approach, which would have given: {old_unique_sites:,} sites"
)
print(f"")
print(f"The difference is: {unique_sites - old_unique_sites:,} sites")
print(f"")
if unique_sites == old_unique_sites:
    print(f"✓ The unique site count hasn't changed!")
    print(f"  (Multi-GVFK approach finds more combinations and GVFKs, but same sites)")
    print(f"")
    print(f"This means the slide number 1,711 might have been from:")
    print(f"  - A different filtering approach")
    print(f"  - An earlier version of the data")
    print(f"  - A different threshold configuration")
else:
    print(
        f"The multi-GVFK approach found {unique_sites - old_unique_sites:,} additional sites"
    )

print("\n" + "=" * 80)
