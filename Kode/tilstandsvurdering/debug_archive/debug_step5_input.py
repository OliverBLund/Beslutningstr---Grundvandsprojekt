"""
Check Step 5 input to understand why site 813-00736 appears twice for DKRIVER115
"""
import pandas as pd
import sys
sys.path.append(r"C:\Users\s194420\OneDrive - Danmarks Tekniske Universitet\Poul Løgstrup Bjergs filer - Work_Projects_Oliver Lund\Beslutningstræ - Grundvands projekt\Kode")

from data_loaders import load_step5_results

print("Loading Step 5 results...")
step5 = load_step5_results()

print(f"\nTotal rows: {len(step5)}")
print(f"Columns: {list(step5.columns)}")

# Check site 813-00736
print("\n" + "="*80)
print("Site 813-00736 - all entries")
print("="*80)

site_data = step5[step5["Lokalitet_ID"] == "813-00736"]
print(f"\nTotal rows for this site: {len(site_data)}")
print(f"Unique GVFK: {site_data['GVFK'].nunique()}")
print(f"Unique Nearest_River_ov_id: {site_data['Nearest_River_ov_id'].nunique()}")
print(f"Unique Qualifying_Category: {site_data['Qualifying_Category'].nunique()}")

# Check DKRIVER115 entries specifically
print("\n" + "="*80)
print("Site 813-00736 - DKRIVER115 entries")
print("="*80)

dkriver115_entries = site_data[site_data["Nearest_River_ov_id"] == "DKRIVER115"]
print(f"\nRows contributing to DKRIVER115: {len(dkriver115_entries)}")

if len(dkriver115_entries) > 0:
    print("\nDetailed breakdown:")
    for idx, row in dkriver115_entries.iterrows():
        print(f"\nRow {idx}:")
        print(f"  GVFK: {row['GVFK']}")
        print(f"  Nearest_River_ov_id: {row['Nearest_River_ov_id']}")
        print(f"  Nearest_River_FID: {row['Nearest_River_FID']}")
        print(f"  Distance_to_River_m: {row['Distance_to_River_m']:.1f}")
        print(f"  River_Segment_Count: {row['River_Segment_Count']}")
        print(f"  Qualifying_Category: {row['Qualifying_Category']}")
        print(f"  Qualifying_Substance: {row['Qualifying_Substance']}")

# Check if there are other sites with same issue
print("\n" + "="*80)
print("Looking for other sites with multiple rows for same segment-category")
print("="*80)

# Group by site, segment, category and check for duplicates
grouped = step5.groupby(["Lokalitet_ID", "Nearest_River_ov_id", "Qualifying_Category"]).size()
duplicates = grouped[grouped > 1]

print(f"\nFound {len(duplicates)} (site, segment, category) combinations with multiple rows")
print("\nFirst 10 examples:")
for idx, (keys, count) in enumerate(duplicates.head(10).items()):
    site_id, segment, category = keys
    print(f"\n{idx+1}. Site {site_id}, Segment {segment}, Category {category}: {count} rows")

    # Show the rows
    rows = step5[
        (step5["Lokalitet_ID"] == site_id) &
        (step5["Nearest_River_ov_id"] == segment) &
        (step5["Qualifying_Category"] == category)
    ]
    for _, row in rows.iterrows():
        print(f"    GVFK: {row['GVFK']}, Distance: {row['Distance_to_River_m']:.1f}m, " +
              f"River_Segment_Count: {row['River_Segment_Count']}, " +
              f"Substance: {row['Qualifying_Substance']}")
