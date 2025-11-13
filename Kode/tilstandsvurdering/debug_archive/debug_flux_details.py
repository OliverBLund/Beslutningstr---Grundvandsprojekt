"""
Debug script to check flux_details for the root cause of duplicates
"""
import pandas as pd

# Load the site-level flux file
flux_file = r"C:\Users\s194420\OneDrive - Danmarks Tekniske Universitet\Poul Løgstrup Bjergs filer - Work_Projects_Oliver Lund\Beslutningstræ - Grundvands projekt\Resultater\step6_flux_site_segment.csv"

print("Loading site-level flux file...")
flux_df = pd.read_csv(flux_file)

print(f"\nShape: {flux_df.shape}")

# Check DKRIVER115 - ANDRE
print("\n" + "="*80)
print("Example: DKRIVER115 - ANDRE__via_Branch/Activity: ANDRE")
print("="*80)

dkriver115 = flux_df[
    (flux_df["Nearest_River_ov_id"] == "DKRIVER115") &
    (flux_df["Qualifying_Category"] == "ANDRE") &
    (flux_df["Qualifying_Substance"] == "Branch/Activity: ANDRE")
]

print(f"\nFound {len(dkriver115)} site-level rows")
print("\nSites contributing:")
for site_id in dkriver115["Lokalitet_ID"].unique():
    site_rows = dkriver115[dkriver115["Lokalitet_ID"] == site_id]
    print(f"\n  Site {site_id}: {len(site_rows)} rows")
    for idx, row in site_rows.iterrows():
        print(f"    River_Segment_Count: {row['River_Segment_Count']}")
        print(f"    Distance_to_River_m: {row['Distance_to_River_m']:.1f}")

# Now check what the aggregation should produce
print("\n" + "="*80)
print("Expected aggregation result:")
print("="*80)

group_cols = [
    "Nearest_River_FID",
    "Nearest_River_ov_id",
    "River_Segment_Name",
    "River_Segment_Length_m",
    "River_Segment_GVFK",
    "Qualifying_Category",
    "Qualifying_Substance",
]

for group_keys, group_df in dkriver115.groupby(group_cols, dropna=False):
    print(f"\nGroup:")
    print(f"  Segment: {group_keys[1]}")
    print(f"  Category: {group_keys[5]}")
    print(f"  Substance: {group_keys[6]}")
    print(f"  Contributing sites: {group_df['Lokalitet_ID'].unique().tolist()}")
    print(f"  Total flux: {group_df['Pollution_Flux_kg_per_year'].sum():.6f} kg/year")

# Check if there are sites that contribute to DKRIVER115 from multiple entries
print("\n" + "="*80)
print("Checking for sites with multiple rows contributing to same segment:")
print("="*80)

for site_id in dkriver115["Lokalitet_ID"].unique():
    site_rows = dkriver115[dkriver115["Lokalitet_ID"] == site_id]
    if len(site_rows) > 1:
        print(f"\nSite {site_id} has {len(site_rows)} rows:")
        print(site_rows[["Nearest_River_ov_id", "Qualifying_Substance", "River_Segment_Count", "Distance_to_River_m"]])
