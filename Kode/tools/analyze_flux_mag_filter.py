"""Analyze impact of filtering rivers by Flux_mag > 0"""
import pandas as pd
import geopandas as gpd
import sys
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent.parent
sys.path.insert(0, str(BASE_DIR / "Kode"))

from config import RIVERS_PATH, get_output_path

print("=" * 80)
print("FLUX_MAG FILTER ANALYSIS")
print("=" * 80)

# Load rivers
rivers = gpd.read_file(RIVERS_PATH)
rivers['River_FID'] = rivers.index

print(f"\nTotal river segments: {len(rivers)}")
print(f"Segments WITH GW contact (Flux_mag > 0): {(rivers['Flux_mag'] > 0).sum()}")
print(f"Segments WITHOUT GW contact (Flux_mag <= 0): {(rivers['Flux_mag'] <= 0).sum()}")

# Load Step 4 output (site-to-river assignments)
step4_output = get_output_path("step4_final_distances_for_risk_assessment")
sites_rivers = pd.read_csv(step4_output)

print(f"\nStep 4 site-river assignments: {len(sites_rivers)}")
print(f"Unique sites: {sites_rivers['Lokalitet_ID'].nunique()}")

# Merge with river Flux_mag
sites_rivers_flux = sites_rivers.merge(
    rivers[['River_FID', 'Flux_mag', 'ov_navn']],
    left_on='Nearest_River_FID',
    right_on='River_FID',
    how='left'
)

no_contact_sites = sites_rivers_flux[sites_rivers_flux['Flux_mag'] <= 0]

print(f"\n{'-'*80}")
print("SITES ASSIGNED TO RIVERS WITHOUT GW CONTACT:")
print(f"{'-'*80}")
print(f"Total sites: {len(no_contact_sites)}")
print(f"Unique sites: {no_contact_sites['Lokalitet_ID'].nunique()}")

if len(no_contact_sites) > 0:
    print("\nSample sites assigned to rivers without GW contact:")
    sample = no_contact_sites[['Lokalitet_ID', 'Lokalitetsnavn', 'ov_navn',
                                'Distance_to_River_m', 'Flux_mag']].head(10)
    print(sample.to_string(index=False))

# Load Step 6 results to see if these sites made it through
flux_results = pd.read_csv(BASE_DIR / "Resultater" / "step6_flux_site_segment.csv")

sites_in_step6 = flux_results['Lokalitet_ID'].unique()
no_contact_site_ids = no_contact_sites['Lokalitet_ID'].unique()

sites_filtered_out = [s for s in no_contact_site_ids if s not in sites_in_step6]

print(f"\n{'-'*80}")
print("IMPACT ON STEP 6:")
print(f"{'-'*80}")
print(f"Sites assigned to no-contact rivers: {len(no_contact_site_ids)}")
print(f"Of these, made it to Step 6: {len([s for s in no_contact_site_ids if s in sites_in_step6])}")
print(f"Filtered out somewhere: {len(sites_filtered_out)}")

# Check current Step 6 usage
step6_rivers = flux_results['Nearest_River_FID'].unique()
step6_rivers_info = rivers[rivers['River_FID'].isin(step6_rivers)]
no_contact_in_step6 = step6_rivers_info[step6_rivers_info['Flux_mag'] <= 0]

print(f"\n{'-'*80}")
print("RIVERS IN CURRENT STEP 6 RESULTS:")
print(f"{'-'*80}")
print(f"Total unique rivers: {len(step6_rivers)}")
print(f"Rivers WITH GW contact: {(step6_rivers_info['Flux_mag'] > 0).sum()}")
print(f"Rivers WITHOUT GW contact: {len(no_contact_in_step6)} (should be 0!)")

if len(no_contact_in_step6) > 0:
    print("\nRivers WITHOUT GW contact in Step 6:")
    print(no_contact_in_step6[['ov_id', 'ov_navn', 'Flux_mag']].to_string(index=False))

    # Which sites use these rivers?
    problem_rivers = no_contact_in_step6['River_FID'].values
    problem_sites = flux_results[flux_results['Nearest_River_FID'].isin(problem_rivers)]
    print(f"\nSites using these rivers: {problem_sites['Lokalitet_ID'].nunique()}")
    print(f"Total flux from these sites: {problem_sites['Pollution_Flux_kg_per_year'].sum():.2f} kg/year")

print(f"\n{'='*80}")
print("RECOMMENDATION:")
print(f"{'='*80}")
print("""
We should filter rivers in Step 4 to ONLY include segments with Flux_mag > 0.

WHY:
- Only these segments have groundwater contact
- Contamination can only reach rivers through groundwater pathway
- The Flux_mag value represents aquifer-to-river discharge

HOW:
- Filter rivers shapefile before nearest neighbor search in Step 4
- This ensures sites are assigned to rivers they can actually affect

IMPACT:
- Current: 14 river segments without GW contact in results
- After fix: 0 river segments without GW contact
- May reassign some sites to different (more appropriate) rivers
""")
