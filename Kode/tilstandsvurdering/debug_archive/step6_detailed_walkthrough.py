"""
Detailed walkthrough of Step 6 with real data examples
Shows exactly what happens for sites with multiple GVFKs and compounds
"""
import pandas as pd
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent.parent
RESULTS_DIR = BASE_DIR / "Resultater"

# Load Step 6 outputs
site_flux = pd.read_csv(RESULTS_DIR / "step6_flux_site_segment.csv")
segment_flux = pd.read_csv(RESULTS_DIR / "step6_flux_by_segment.csv")
cmix_results = pd.read_csv(RESULTS_DIR / "step6_cmix_results.csv")

print("=" * 100)
print("STEP 6 DETAILED WALKTHROUGH WITH REAL DATA")
print("=" * 100)

# EXAMPLE 1: Site with multiple GVFKs and multiple compounds
print("\n" + "=" * 100)
print("EXAMPLE 1: MULTI-GVFK, MULTI-COMPOUND SITE")
print("=" * 100)

# Find a good example
multi_gvfk = site_flux.groupby('Lokalitet_ID').agg({
    'GVFK': 'nunique',
    'Qualifying_Substance': 'nunique'
})
multi_gvfk = multi_gvfk[(multi_gvfk['GVFK'] > 1) & (multi_gvfk['Qualifying_Substance'] > 3)]

if len(multi_gvfk) > 0:
    example_site = multi_gvfk.index[0]
else:
    example_site = site_flux['Lokalitet_ID'].iloc[0]

site_data = site_flux[site_flux['Lokalitet_ID'] == example_site].copy()

print(f"\nSite ID: {example_site}")
print(f"Site Name: {site_data.iloc[0]['Lokalitetsnavn']}")
print(f"Region: {site_data.iloc[0]['Regionsnavn']}")
print(f"Site Area: {site_data.iloc[0]['Area_m2']:.1f} m²")

print(f"\n{'─'*100}")
print("STEP 6 CREATES ONE ROW PER: Site × GVFK × Substance × River")
print(f"{'─'*100}")

print(f"\nTotal rows for this site: {len(site_data)}")
print(f"Number of GVFKs: {site_data['GVFK'].nunique()}")
print(f"Number of substances: {site_data['Qualifying_Substance'].nunique()}")
print(f"Number of rivers: {site_data['Nearest_River_ov_id'].nunique()}")

# Show the structure
print(f"\n{'─'*100}")
print("SITE DATA STRUCTURE:")
print(f"{'─'*100}")

structure = site_data.groupby(['GVFK', 'DK-modellag']).agg({
    'Infiltration_mm_per_year': 'first',
    'Nearest_River_ov_navn': 'first',
    'Qualifying_Substance': 'count'
}).reset_index()
structure.columns = ['GVFK', 'Layer', 'Infiltration_mm/yr', 'River', 'Num_Substances']
print(structure.to_string(index=False))

# DETAILED EXAMPLE: Follow one substance through both GVFKs
print(f"\n{'='*100}")
print("DETAILED CALCULATION: ONE SUBSTANCE THROUGH MULTIPLE GVFKs")
print(f"{'='*100}")

substance = site_data['Qualifying_Substance'].iloc[0]
substance_rows = site_data[site_data['Qualifying_Substance'] == substance].copy()

print(f"\nSubstance: {substance}")
print(f"Category: {substance_rows.iloc[0]['Qualifying_Category']}")
print(f"Concentration: {substance_rows.iloc[0]['Standard_Concentration_ug_L']:.1f} µg/L")

print(f"\n{'─'*100}")
print("CALCULATION FOR EACH GVFK:")
print(f"{'─'*100}")

for idx, row in substance_rows.iterrows():
    print(f"\n▸ GVFK: {row['GVFK']} (Layer: {row['DK-modellag']})")
    print(f"  ├─ Raster sampled: DKM_gvd_{row['DK-modellag']}.tif")
    print(f"  ├─ Infiltration: {row['Infiltration_mm_per_year']:.2f} mm/year")
    print(f"  ├─ River: {row['Nearest_River_ov_navn']}")
    print(f"  ├─ Distance: {row['Distance_to_River_m']:.1f} m")
    print(f"  └─ Formula: {row['Area_m2']:.1f} m² × {row['Infiltration_mm_per_year']:.2f} mm/yr × {row['Standard_Concentration_ug_L']:.1f} µg/L")
    print(f"     → Flux: {row['Pollution_Flux_kg_per_year']:.3f} kg/year")

print(f"\n{'─'*100}")
print(f"Total flux for '{substance}': {substance_rows['Pollution_Flux_kg_per_year'].sum():.3f} kg/year")
print(f"(Sum across {len(substance_rows)} pathways)")

# AGGREGATION TO RIVER SEGMENT LEVEL
print(f"\n{'='*100}")
print("STEP 6 AGGREGATION: SITE → RIVER SEGMENT")
print(f"{'='*100}")

# Get aggregated flux for this site's rivers
site_rivers = site_data['Nearest_River_FID'].unique()
site_segment_flux = segment_flux[segment_flux['Nearest_River_FID'].isin(site_rivers)]

print(f"\nThis site affects {len(site_rivers)} river segment(s)")

for river_fid in site_rivers[:3]:  # Show first 3
    river_data = segment_flux[segment_flux['Nearest_River_FID'] == river_fid].copy()
    if len(river_data) == 0:
        continue

    print(f"\n{'─'*100}")
    print(f"River: {river_data.iloc[0]['River_Segment_Name']}")
    print(f"{'─'*100}")

    # Show flux by substance
    by_substance = river_data.groupby('Qualifying_Substance').agg({
        'Total_Flux_kg_per_year': 'first',
        'Contributing_Site_Count': 'first'
    }).reset_index()

    print(f"\nTop 5 substances contributing to this river:")
    top_5 = by_substance.nlargest(5, 'Total_Flux_kg_per_year')
    for _, sub_row in top_5.iterrows():
        print(f"  • {sub_row['Qualifying_Substance'][:50]:50s} {sub_row['Total_Flux_kg_per_year']:8.3f} kg/yr ({sub_row['Contributing_Site_Count']:.0f} sites)")

# CMIX CALCULATION
print(f"\n{'='*100}")
print("STEP 6 CMIX: DILUTION IN RIVER")
print(f"{'='*100}")

# Get Cmix for one substance at one river
if len(substance_rows) > 0:
    river_id = substance_rows.iloc[0]['Nearest_River_ov_id']

    cmix_example = cmix_results[
        (cmix_results['Nearest_River_ov_id'] == river_id) &
        (cmix_results['Qualifying_Substance'] == substance)
    ].copy()

    if len(cmix_example) > 0:
        print(f"\nSubstance: {substance}")
        print(f"River: {cmix_example.iloc[0]['River_Segment_Name']}")

        # Show for each flow scenario
        for flow_scenario in ['Mean', 'Q90', 'Q95']:
            scenario_data = cmix_example[cmix_example['Flow_Scenario'] == flow_scenario]
            if len(scenario_data) > 0:
                row = scenario_data.iloc[0]
                print(f"\n▸ Flow Scenario: {flow_scenario}")
                print(f"  ├─ Total flux: {row['Total_Flux_kg_per_year']:.3f} kg/year")
                print(f"  ├─ River flow: {row['Flow_m3_s']:.4f} m³/s")
                print(f"  ├─ Formula: {row['Total_Flux_ug_per_year']:.0f} µg/yr ÷ (365.25×24×3600 s/yr) ÷ ({row['Flow_m3_s']:.4f} m³/s × 1000 L/m³)")
                print(f"  ├─ Cmix: {row['Cmix_ug_L']:.4f} µg/L")
                print(f"  ├─ MKK: {row['MKK_ug_L']:.4f} µg/L")
                if row['Cmix_ug_L'] > 0 and row['MKK_ug_L'] > 0:
                    print(f"  └─ Exceedance: {row['Exceedance_Ratio']:.2f}× MKK")
                else:
                    print(f"  └─ Exceedance: N/A")

# SHOW COMPLETE DATA FLOW
print(f"\n{'='*100}")
print("COMPLETE DATA FLOW SUMMARY")
print(f"{'='*100}")

print(f"""
INPUT (Step 5):
  Site {example_site} with:
    - {site_data['GVFK'].nunique()} GVFK(s) in different aquifer layers
    - {site_data['Qualifying_Substance'].nunique()} substance(s)

↓ STEP 6 PROCESSING

1. FLUX CALCULATION (step6_flux_site_segment.csv):
   - Total rows: {len(site_data)}
   - One row per: Site × GVFK × Substance × River
   - Each row: Sample GVD raster → Calculate flux

2. AGGREGATION (step6_flux_by_segment.csv):
   - Group by: River × GVFK × Substance × Category
   - Sum flux from all contributing sites

3. DILUTION (step6_cmix_results.csv):
   - For each river segment × substance:
   - Calculate Cmix for 3 flow scenarios (Mean, Q90, Q95)
   - Compare to MKK threshold

OUTPUT:
  - Site flux: {len(site_data)} rows
  - Segment flux: {len(site_segment_flux)} river-substance combinations
  - Cmix results: {len(cmix_example) * 3} scenarios (3 flows × substances)
""")

print("=" * 100)
print("END OF WALKTHROUGH")
print("=" * 100)
