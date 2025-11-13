"""
Debug script to identify where Contributing_Site_IDs gets corrupted.
Comparing step6_flux_by_segment.csv vs step6_cmix_results.csv
"""
import pandas as pd

# Load both files
# Note: We aggregate site-level flux data ourselves since segment-level is not exported
site_flux_file = r"C:\Users\s194420\OneDrive - Danmarks Tekniske Universitet\Poul Løgstrup Bjergs filer - Work_Projects_Oliver Lund\Beslutningstræ - Grundvands projekt\Resultater\step6_flux_site_segment.csv"
cmix_file = r"C:\Users\s194420\OneDrive - Danmarks Tekniske Universitet\Poul Løgstrup Bjergs filer - Work_Projects_Oliver Lund\Beslutningstræ - Grundvands projekt\Resultater\step6_cmix_results.csv"

print("Loading files...")
site_flux_df = pd.read_csv(site_flux_file)

# Aggregate to segment level to match cmix structure
group_columns = [
    "Nearest_River_FID",
    "Nearest_River_ov_id",
    "River_Segment_Name",
    "Qualifying_Category",
    "Qualifying_Substance",
]

flux_records = []
for group_keys, group_df in site_flux_df.groupby(group_columns, dropna=False):
    record = dict(zip(group_columns, group_keys))
    record["Total_Flux_kg_per_year"] = group_df["Pollution_Flux_kg_per_year"].sum()
    record["Contributing_Site_Count"] = group_df["Lokalitet_ID"].nunique()
    record["Contributing_Site_IDs"] = ", ".join(sorted(group_df["Lokalitet_ID"].unique()))
    flux_records.append(record)

flux_df = pd.DataFrame(flux_records)
cmix_df = pd.read_csv(cmix_file)

print(f"\nFlux file: {len(flux_df)} rows")
print(f"Cmix file: {len(cmix_df)} rows")
print(f"Expected ratio: 1:3 (each flux row should generate 3 cmix rows for Mean/Q90/Q95)")
print(f"Actual ratio: 1:{len(cmix_df)/len(flux_df):.2f}")

# Check DKRIVER3164 example
print("\n" + "="*80)
print("DKRIVER3164 - KLOREREDE_OPLØSNINGSMIDLER__via_Trichlorethylen")
print("="*80)

segment = "DKRIVER3164"
scenario = "KLOREREDE_OPLØSNINGSMIDLER__via_Trichlorethylen"

flux_row = flux_df[
    (flux_df["Nearest_River_ov_id"] == segment) &
    (flux_df["Qualifying_Category"] == "KLOREREDE_OPLØSNINGSMIDLER") &
    (flux_df["Qualifying_Substance"] == "Trichlorethylen")
]

cmix_rows = cmix_df[
    (cmix_df["Nearest_River_ov_id"] == segment) &
    (cmix_df["Qualifying_Category"] == "KLOREREDE_OPLØSNINGSMIDLER") &
    (cmix_df["Qualifying_Substance"] == "Trichlorethylen")
]

if not flux_row.empty:
    print("\nFLUX file (step6_flux_by_segment.csv):")
    print(f"  Contributing_Site_Count: {flux_row.iloc[0]['Contributing_Site_Count']}")
    print(f"  Contributing_Site_IDs: {flux_row.iloc[0]['Contributing_Site_IDs']}")
    flux_sites = set(flux_row.iloc[0]['Contributing_Site_IDs'].split(", "))
    print(f"  Site count from IDs: {len(flux_sites)}")
else:
    print("\nFLUX: Not found")

if not cmix_rows.empty:
    print(f"\nCMIX file (step6_cmix_results.csv): {len(cmix_rows)} rows")
    for idx, row in cmix_rows.iterrows():
        flow_scenario = row['Flow_Scenario']
        site_ids = row['Contributing_Site_IDs']
        site_count = row['Contributing_Site_Count']
        cmix_sites = set(site_ids.split(", ")) if pd.notna(site_ids) and site_ids else set()
        print(f"  Flow scenario {flow_scenario}:")
        print(f"    Contributing_Site_Count: {site_count}")
        print(f"    Contributing_Site_IDs: {site_ids}")
        print(f"    Site count from IDs: {len(cmix_sites)}")
else:
    print("\nCMIX: Not found")

# Check if Contributing_Site_IDs is consistent across flow scenarios
print("\n" + "="*80)
print("Checking if Contributing_Site_IDs varies across flow scenarios")
print("="*80)

# Group cmix by segment and scenario, check if Contributing_Site_IDs is the same
issues = []
for (segment, category, substance), group in cmix_df.groupby(
    ["Nearest_River_ov_id", "Qualifying_Category", "Qualifying_Substance"]
):
    unique_site_ids = group["Contributing_Site_IDs"].unique()
    if len(unique_site_ids) > 1:
        issues.append({
            "segment": segment,
            "category": category,
            "substance": substance,
            "unique_values": len(unique_site_ids),
            "site_ids": unique_site_ids.tolist()
        })

if issues:
    print(f"\nFOUND {len(issues)} segment-scenarios with inconsistent Contributing_Site_IDs!")
    print("\nFirst 5 examples:")
    for issue in issues[:5]:
        print(f"\n{issue['segment']} - {issue['category']}__via_{issue['substance']}")
        print(f"  Has {issue['unique_values']} different values across flow scenarios:")
        for idx, val in enumerate(issue['site_ids'][:3]):
            print(f"    Value {idx+1}: {val}")
else:
    print("\nNo inconsistencies found - Contributing_Site_IDs is the same across all flow scenarios")

# Compare flux vs cmix for all rows
print("\n" + "="*80)
print("Comparing Contributing_Site_IDs between flux and cmix files")
print("="*80)

mismatches = []
for idx, flux_row in flux_df.iterrows():
    segment = flux_row["Nearest_River_ov_id"]
    category = flux_row["Qualifying_Category"]
    substance = flux_row["Qualifying_Substance"]
    flux_site_ids = flux_row["Contributing_Site_IDs"]

    # Get corresponding cmix rows (should be 3: Mean, Q90, Q95)
    cmix_rows = cmix_df[
        (cmix_df["Nearest_River_ov_id"] == segment) &
        (cmix_df["Qualifying_Category"] == category) &
        (cmix_df["Qualifying_Substance"] == substance)
    ]

    if cmix_rows.empty:
        mismatches.append({
            "segment": segment,
            "scenario": f"{category}__via_{substance}",
            "issue": "Missing in cmix",
            "flux_sites": flux_site_ids,
            "cmix_sites": "N/A"
        })
    else:
        # Check if all cmix rows have the same Contributing_Site_IDs as flux
        for _, cmix_row in cmix_rows.iterrows():
            cmix_site_ids = cmix_row["Contributing_Site_IDs"]
            if flux_site_ids != cmix_site_ids:
                mismatches.append({
                    "segment": segment,
                    "scenario": f"{category}__via_{substance}",
                    "flow_scenario": cmix_row["Flow_Scenario"],
                    "issue": "Site IDs mismatch",
                    "flux_sites": flux_site_ids,
                    "cmix_sites": cmix_site_ids
                })

if mismatches:
    print(f"\nFOUND {len(mismatches)} mismatches!")
    print("\nFirst 10 examples:")
    for match in mismatches[:10]:
        print(f"\n{match['segment']} - {match['scenario']}")
        if 'flow_scenario' in match:
            print(f"  Flow scenario: {match['flow_scenario']}")
        print(f"  Issue: {match['issue']}")
        print(f"  Flux sites: {match['flux_sites']}")
        print(f"  Cmix sites: {match['cmix_sites']}")
else:
    print("\nNo mismatches found - all Contributing_Site_IDs match perfectly!")

print("\n" + "="*80)
print("Summary:")
print(f"Total flux rows: {len(flux_df)}")
print(f"Total cmix rows: {len(cmix_df)}")
print(f"Mismatches found: {len(mismatches)}")
print(f"Mismatch rate: {len(mismatches)/len(cmix_df)*100:.1f}%")
print("="*80)
