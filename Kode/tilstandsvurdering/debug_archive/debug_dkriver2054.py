"""
Debug DKRIVER2054 to understand why Contributing_Site_IDs varies across flow scenarios
"""
import pandas as pd

# Load files
site_flux_file = r"C:\Users\s194420\OneDrive - Danmarks Tekniske Universitet\Poul Løgstrup Bjergs filer - Work_Projects_Oliver Lund\Beslutningstræ - Grundvands projekt\Resultater\step6_flux_site_segment.csv"
cmix_file = r"C:\Users\s194420\OneDrive - Danmarks Tekniske Universitet\Poul Løgstrup Bjergs filer - Work_Projects_Oliver Lund\Beslutningstræ - Grundvands projekt\Resultater\step6_cmix_results.csv"

print("Loading files...")
site_flux = pd.read_csv(site_flux_file)
cmix = pd.read_csv(cmix_file)

# Check DKRIVER2054
print("\n" + "="*80)
print("DKRIVER2054 - Site-level flux (all categories)")
print("="*80)

dkriver2054_sites = site_flux[site_flux["Nearest_River_ov_id"] == "DKRIVER2054"]
print(f"\nTotal site-level rows: {len(dkriver2054_sites)}")
print(f"Unique sites: {dkriver2054_sites['Lokalitet_ID'].nunique()}")
print(f"Unique categories: {dkriver2054_sites['Qualifying_Category'].nunique()}")

# Focus on KLOREREDE_OPLØSNINGSMIDLER
print("\n" + "="*80)
print("DKRIVER2054 - KLOREREDE_OPLØSNINGSMIDLER category (site-level)")
print("="*80)

klorerede = dkriver2054_sites[dkriver2054_sites["Qualifying_Category"] == "KLOREREDE_OPLØSNINGSMIDLER"]
print(f"\nTotal rows: {len(klorerede)}")
print(f"Unique sites: {klorerede['Lokalitet_ID'].nunique()}")
print(f"Unique substances: {klorerede['Qualifying_Substance'].nunique()}")

print("\nSites and their substances:")
for site_id in sorted(klorerede['Lokalitet_ID'].unique()):
    site_rows = klorerede[klorerede['Lokalitet_ID'] == site_id]
    substances = site_rows['Qualifying_Substance'].unique()
    print(f"  {site_id}: {len(substances)} substances - {', '.join(substances[:3])}{'...' if len(substances) > 3 else ''}")

# Check Cmix results
print("\n" + "="*80)
print("DKRIVER2054 - KLOREREDE_OPLØSNINGSMIDLER category (Cmix results)")
print("="*80)

cmix_klorerede = cmix[
    (cmix["Nearest_River_ov_id"] == "DKRIVER2054") &
    (cmix["Qualifying_Category"] == "KLOREREDE_OPLØSNINGSMIDLER")
]

print(f"\nTotal Cmix rows: {len(cmix_klorerede)}")
print(f"Unique substances: {cmix_klorerede['Qualifying_Substance'].nunique()}")

for substance in sorted(cmix_klorerede['Qualifying_Substance'].unique()):
    substance_rows = cmix_klorerede[cmix_klorerede['Qualifying_Substance'] == substance]
    print(f"\n  Substance: {substance}")
    print(f"  Rows: {len(substance_rows)} (should be 3: Mean, Q90, Q95)")

    for _, row in substance_rows.iterrows():
        flow_scenario = row['Flow_Scenario']
        site_ids = row['Contributing_Site_IDs']
        print(f"    {flow_scenario}: {site_ids}")
