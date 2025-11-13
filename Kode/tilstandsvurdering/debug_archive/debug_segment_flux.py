"""
Debug script to check segment_flux for duplicates that could cause merge issues
"""
import pandas as pd

# Load the segment flux file
flux_file = r"C:\Users\s194420\OneDrive - Danmarks Tekniske Universitet\Poul Løgstrup Bjergs filer - Work_Projects_Oliver Lund\Beslutningstræ - Grundvands projekt\Resultater\step6_flux_by_segment.csv"

print("Loading segment flux file...")
flux_df = pd.read_csv(flux_file)

print(f"\nShape: {flux_df.shape}")
print(f"Columns: {list(flux_df.columns)}")

# Check for duplicate (segment, category, substance) combinations
print("\n" + "="*80)
print("Checking for duplicate segment-category-substance combinations:")
print("="*80)

group_cols = ["Nearest_River_ov_id", "Qualifying_Category", "Qualifying_Substance"]
duplicates = flux_df.groupby(group_cols).size()
duplicates = duplicates[duplicates > 1]

if len(duplicates) > 0:
    print(f"\nFOUND {len(duplicates)} duplicate combinations!")
    print("\nFirst 10:")
    for idx, (keys, count) in enumerate(duplicates.head(10).items()):
        print(f"\n{idx+1}. {keys[0]} - {keys[1]}__via_{keys[2]}")
        print(f"   Appears {count} times")

        # Show the duplicate rows
        dup_rows = flux_df[
            (flux_df["Nearest_River_ov_id"] == keys[0]) &
            (flux_df["Qualifying_Category"] == keys[1]) &
            (flux_df["Qualifying_Substance"] == keys[2])
        ]
        print(f"   Contributing_Site_IDs:")
        for _, row in dup_rows.iterrows():
            print(f"     - {row['Contributing_Site_IDs']}")
else:
    print("\nNo duplicates found - each (segment, category, substance) appears exactly once")

# Check DKRIVER115 specifically
print("\n" + "="*80)
print("Example: DKRIVER115 - ANDRE")
print("="*80)

dkriver115 = flux_df[
    (flux_df["Nearest_River_ov_id"] == "DKRIVER115") &
    (flux_df["Qualifying_Category"] == "ANDRE")
]

print(f"\nFound {len(dkriver115)} rows")
for idx, row in dkriver115.iterrows():
    print(f"\nRow {idx}:")
    print(f"  Qualifying_Substance: {row['Qualifying_Substance']}")
    print(f"  Contributing_Site_Count: {row['Contributing_Site_Count']}")
    print(f"  Contributing_Site_IDs: {row['Contributing_Site_IDs']}")

# Check the Qualifying_Substance column for weird values
print("\n" + "="*80)
print("Checking Qualifying_Substance values:")
print("="*80)

substance_counts = flux_df['Qualifying_Substance'].value_counts()
print(f"\nTotal unique substances: {len(substance_counts)}")
print("\nSubstances that appear weird or duplicated:")
weird_substances = [s for s in substance_counts.index if '__via_' in str(s) or 'Branch' in str(s)]
if weird_substances:
    for s in weird_substances[:10]:
        print(f"  {s}: {substance_counts[s]} rows")
else:
    print("  None found")

# Look at all ANDRE category rows
print("\n" + "="*80)
print("All ANDRE category rows (first 20):")
print("="*80)
andre_rows = flux_df[flux_df["Qualifying_Category"] == "ANDRE"]
print(f"\nTotal ANDRE rows: {len(andre_rows)}")
print(andre_rows[["Nearest_River_ov_id", "Qualifying_Substance", "Contributing_Site_Count", "Contributing_Site_IDs"]].head(20))
