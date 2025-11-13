"""
Debug DKRIVER2054 site-level flux to see why aggregation creates duplicates
"""
import pandas as pd

# Load site-level flux
site_flux_file = r"C:\Users\s194420\OneDrive - Danmarks Tekniske Universitet\Poul Løgstrup Bjergs filer - Work_Projects_Oliver Lund\Beslutningstræ - Grundvands projekt\Resultater\step6_flux_site_segment.csv"

print("Loading site-level flux...")
site_flux = pd.read_csv(site_flux_file)

# Check DKRIVER2054 KLOREREDE_OPLØSNINGSMIDLER
klorerede = site_flux[
    (site_flux["Nearest_River_ov_id"] == "DKRIVER2054") &
    (site_flux["Qualifying_Category"] == "KLOREREDE_OPLØSNINGSMIDLER")
]

print(f"\nTotal rows: {len(klorerede)}")
print(f"\nColumns that could cause different aggregation groups:")

# Check the grouping columns from _aggregate_flux_by_segment
group_columns = [
    "Nearest_River_FID",
    "Nearest_River_ov_id",
    "River_Segment_Name",
    "River_Segment_Length_m",
    "River_Segment_GVFK",
    "Qualifying_Category",
    "Qualifying_Substance",
]

print("\nChecking for variations in grouping columns:")
for col in group_columns:
    unique_vals = klorerede[col].nunique()
    if unique_vals > 1:
        print(f"  {col}: {unique_vals} unique values!")
        print(f"    Values: {klorerede[col].unique()}")
    else:
        print(f"  {col}: {unique_vals} unique value")

# Show all rows with key columns
print("\n" + "="*80)
print("All KLOREREDE_OPLØSNINGSMIDLER rows for DKRIVER2054:")
print("="*80)

display_cols = [
    "Lokalitet_ID",
    "GVFK",
    "Nearest_River_FID",
    "Nearest_River_ov_id",
    "River_Segment_Name",
    "River_Segment_GVFK",
    "Qualifying_Substance",
    "Distance_to_River_m"
]

pd.set_option('display.max_rows', None)
pd.set_option('display.max_columns', None)
pd.set_option('display.width', None)
print(klorerede[display_cols].sort_values(["Qualifying_Substance", "Lokalitet_ID"]))

# Manually aggregate to see what happens
print("\n" + "="*80)
print("Manual aggregation by substance:")
print("="*80)

for substance in sorted(klorerede['Qualifying_Substance'].unique()):
    substance_rows = klorerede[klorerede['Qualifying_Substance'] == substance]
    sites = sorted(substance_rows['Lokalitet_ID'].unique())
    print(f"\n{substance}:")
    print(f"  Sites: {', '.join(sites)}")
    print(f"  Expected: 1 aggregated row with all {len(sites)} sites")

    # Check if there are different values in grouping columns
    for col in group_columns[:-1]:  # Exclude Qualifying_Substance
        unique_vals = substance_rows[col].nunique()
        if unique_vals > 1:
            print(f"  WARNING: {col} has {unique_vals} different values:")
            for val in substance_rows[col].unique():
                sites_with_val = substance_rows[substance_rows[col] == val]['Lokalitet_ID'].tolist()
                print(f"    {val}: sites {', '.join(sites_with_val)}")
