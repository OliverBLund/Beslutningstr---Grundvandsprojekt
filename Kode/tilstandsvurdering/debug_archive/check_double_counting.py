"""
Check for potential double counting in Step 6 flux calculations
"""
import pandas as pd
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent.parent
RESULTS_DIR = BASE_DIR / "Resultater"

site_flux = pd.read_csv(RESULTS_DIR / "step6_flux_site_segment.csv")
segment_flux = pd.read_csv(RESULTS_DIR / "step6_flux_by_segment.csv")
cmix_results = pd.read_csv(RESULTS_DIR / "step6_cmix_results.csv")

print("=" * 100)
print("CHECKING FOR DOUBLE COUNTING")
print("=" * 100)

# Example site
site_id = '151-00001'
site_data = site_flux[site_flux['Lokalitet_ID'] == site_id].copy()

print(f"\nAnalyzing Site: {site_id}")
print(f"Name: {site_data.iloc[0]['Lokalitetsnavn']}")

print(f"\n{'-'*100}")
print("QUESTION 1: Are we using the SAME AREA multiple times?")
print(f"{'-'*100}")

area = site_data.iloc[0]['Area_m2']
print(f"\nSite area: {area:.1f} m²")
print(f"Number of flux calculations: {len(site_data)}")

print("\nEach flux calculation uses:")
gvfk_summary = site_data.groupby(['GVFK', 'DK-modellag']).agg({
    'Area_m2': 'first',
    'Infiltration_mm_per_year': 'first',
    'Qualifying_Substance': 'count'
}).reset_index()
gvfk_summary.columns = ['GVFK', 'Layer', 'Area_m2', 'Infiltration', 'Num_Calcs']

for _, row in gvfk_summary.iterrows():
    print(f"  GVFK {row['GVFK']} ({row['Layer']}): Area = {row['Area_m2']:.1f} m² × {row['Num_Calcs']:.0f} substances")

print("\n⚠️  POTENTIAL ISSUE:")
print(f"  Same area ({area:.1f} m²) is used {gvfk_summary['Num_Calcs'].sum():.0f} times in flux calculations!")

print(f"\n{'-'*100}")
print("QUESTION 2: Is this physically correct?")
print(f"{'-'*100}")

print("""
Physical interpretation:

Scenario: Site with area 100 m² above two aquifer layers (ks1, ks2)

CURRENT APPROACH:
  ks1: 100 m² × infiltration_ks1 × concentration → Flux_ks1
  ks2: 100 m² × infiltration_ks2 × concentration → Flux_ks2
  Total: Flux_ks1 + Flux_ks2

QUESTION: Does water infiltrate through 100 m² into ks1 AND 100 m² into ks2?

Two possible interpretations:

A) PARALLEL PATHWAYS (Current assumption):
   - Water infiltrates through the SAME 100 m² surface
   - Some water reaches ks1 (upper layer)
   - Some water continues down to ks2 (lower layer)
   - Total infiltration = infiltration_ks1 + infiltration_ks2
   - ⚠️  Problem: Are we double counting the same water?

B) SEPARATE PATHWAYS (Alternative):
   - Each GVFK represents a different location/zone
   - Different 100 m² areas for each GVFK
   - No double counting, but then why same site coordinates?

C) VERTICAL PARTITIONING:
   - Total infiltration should be MAX(infiltration_ks1, infiltration_ks2)
   - Water goes through surface once, then splits to layers
   - Currently we ADD them, which may overestimate
""")

print(f"\n{'-'*100}")
print("QUESTION 3: What does GVD raster actually represent?")
print(f"{'-'*100}")

print("""
GVD (Grundvandsdannelse) raster values:

Option A: NET RECHARGE to that specific aquifer layer
  - DKM_gvd_ks1.tif = net recharge specifically entering ks1 layer
  - DKM_gvd_ks2.tif = net recharge specifically entering ks2 layer
  - If this: Adding them makes sense (different layers get different amounts)

Option B: TOTAL INFILTRATION at land surface
  - Each raster shows same surface infiltration
  - Layer designation just for mapping purposes
  - If this: Adding them is WRONG (double counting surface water)

We need to check what GVD actually represents!
""")

print(f"\n{'-'*100}")
print("QUESTION 4: Let's check the actual GVD values")
print(f"{'-'*100}")

print("\nFor our example site:")
for _, row in gvfk_summary.iterrows():
    print(f"  {row['Layer']}: {row['Infiltration']:.2f} mm/year")

total_inf = gvfk_summary['Infiltration'].sum()
max_inf = gvfk_summary['Infiltration'].max()

print(f"\nIf we ADD: {total_inf:.2f} mm/year")
print(f"If we take MAX: {max_inf:.2f} mm/year")
print(f"Difference: {total_inf - max_inf:.2f} mm/year ({(total_inf/max_inf - 1)*100:.1f}% increase)")

print(f"\n{'-'*100}")
print("QUESTION 5: Check if GVD values are similar or very different")
print(f"{'-'*100}")

# Check all sites with multiple GVFKs
multi_gvfk_sites = site_flux.groupby('Lokalitet_ID').agg({
    'GVFK': 'nunique',
    'DK-modellag': lambda x: list(x.unique())
})
multi_gvfk_sites = multi_gvfk_sites[multi_gvfk_sites['GVFK'] > 1]

print(f"\nSites with multiple GVFKs: {len(multi_gvfk_sites)}")

# Sample a few and compare infiltration values
print("\nSample infiltration comparisons (first 5 multi-GVFK sites):")
for site_id in multi_gvfk_sites.index[:5]:
    site_data = site_flux[site_flux['Lokalitet_ID'] == site_id]
    inf_by_layer = site_data.groupby('DK-modellag')['Infiltration_mm_per_year'].first()

    print(f"\n  Site {site_id}:")
    for layer, inf in inf_by_layer.items():
        print(f"    {layer}: {inf:8.2f} mm/year")

    if len(inf_by_layer) > 1:
        inf_vals = inf_by_layer.values
        ratio = inf_vals.max() / inf_vals.min() if inf_vals.min() > 0 else float('inf')
        print(f"    Ratio max/min: {ratio:.2f}x")

print(f"\n{'='*100}")
print("CONCLUSION & RECOMMENDATION:")
print(f"{'='*100}")

print("""
POTENTIAL DOUBLE COUNTING ISSUE:

Current approach sums flux across multiple GVFKs for the same site:
  Total_Flux = Flux_ks1 + Flux_ks2 + ...

This assumes:
  - Each aquifer layer receives independent infiltration
  - Same surface area contributes to multiple layers simultaneously

CONCERNS:
1. Are we counting the same water entering the ground multiple times?
2. GVD rasters may represent net recharge to EACH LAYER, not total surface infiltration
3. Or they may represent same surface infiltration, mapped to different layers

NEED TO VERIFY:
□ What does GVD raster physically represent?
  - Layer-specific recharge? → Current approach OK
  - Total surface infiltration? → Current approach WRONG (double counting)

□ Check DK-model documentation
□ Contact GEUS about GVD raster interpretation
□ Check if sum of GVD values matches water balance

TEMPORARY OPTIONS:
A) Keep current approach (sum across layers) - Conservative, may overestimate
B) Use MAX infiltration across layers - Takes highest pathway only
C) Weight by layer thickness/properties - More complex but realistic
""")
