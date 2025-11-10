"""Trace how flux is summed for multi-GVFK sites"""
import pandas as pd
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent.parent
RESULTS_DIR = BASE_DIR / "Resultater"

site_flux = pd.read_csv(RESULTS_DIR / "step6_flux_site_segment.csv")
segment_flux = pd.read_csv(RESULTS_DIR / "step6_flux_by_segment.csv")

print("=" * 100)
print("HOW FLUX IS SUMMED FOR MULTI-GVFK SITES")
print("=" * 100)

# Example site with multiple GVFKs
site_id = '151-00001'
substance = 'Landfill Override: UORGANISKE_FORBINDELSER'

site_data = site_flux[site_flux['Lokalitet_ID'] == site_id]
sub_data = site_data[site_data['Qualifying_Substance'] == substance]

print(f"\nSite: {site_id}")
print(f"Substance: {substance}")
print(f"\n{'-'*100}")
print("STEP 1: INDIVIDUAL PATHWAYS (site_flux file)")
print(f"{'-'*100}")

pathway_summary = sub_data.groupby(['GVFK', 'DK-modellag', 'Nearest_River_FID']).agg({
    'Infiltration_mm_per_year': 'first',
    'Pollution_Flux_kg_per_year': 'sum',
    'Nearest_River_ov_navn': 'first'
}).reset_index()

print("\nEach GVFK-Layer combination creates a separate flux:")
for _, row in pathway_summary.iterrows():
    print(f"  GVFK: {row['GVFK']:20s} | Layer: {row['DK-modellag']:5s} | River: {row['Nearest_River_ov_navn']:30s} | Flux: {row['Pollution_Flux_kg_per_year']:7.3f} kg/yr")

print(f"\nTotal flux from this site for this substance: {sub_data['Pollution_Flux_kg_per_year'].sum():.3f} kg/yr")

print(f"\n{'-'*100}")
print("STEP 2: AGGREGATION BY RIVER SEGMENT (segment_flux file)")
print(f"{'-'*100}")

# Get the river segments this substance reaches
river_fids = sub_data['Nearest_River_FID'].unique()

print("\nFlux is summed by River + GVFK + Substance:")
for fid in river_fids:
    # Get all entries for this river and substance (across all GVFKs)
    seg_data = segment_flux[
        (segment_flux['Nearest_River_FID'] == fid) &
        (segment_flux['Qualifying_Substance'] == substance)
    ]

    if len(seg_data) > 0:
        river_name = seg_data.iloc[0]['River_Segment_Name']

        # Group by GVFK to see contribution from each
        by_gvfk = seg_data.groupby('River_Segment_GVFK').agg({
            'Total_Flux_kg_per_year': 'first'
        }).reset_index()

        print(f"\n  River: {river_name} (FID {fid})")
        for _, gvfk_row in by_gvfk.iterrows():
            print(f"    └─ From GVFK {gvfk_row['River_Segment_GVFK']}: {gvfk_row['Total_Flux_kg_per_year']:.3f} kg/yr")

        total_to_river = seg_data['Total_Flux_kg_per_year'].sum()
        print(f"    → Total to this river segment: {total_to_river:.3f} kg/yr")

print(f"\n{'='*100}")
print("KEY POINT:")
print(f"{'='*100}")
print("""
YES, we sum flux across multiple GVFKs for the same substance!

Physical meaning:
- Contamination infiltrates through MULTIPLE aquifer layers simultaneously
- ks1 layer: One flux pathway to river
- ks2 layer: Another flux pathway to river
- Total impact = Sum of both pathways

This represents the reality that:
1. Site sits above multiple aquifer layers
2. Contamination enters each layer at different rates (different infiltration)
3. Each layer may discharge to same or different river segments
4. Total pollution flux = sum across all pathways
""")

# Show a case where different layers go to different rivers
print(f"\n{'='*100}")
print("EXAMPLE: DIFFERENT LAYERS → DIFFERENT RIVERS")
print(f"{'='*100}")

# Find a site where different GVFKs go to different rivers
multi_river_sites = site_flux.groupby('Lokalitet_ID').agg({
    'Nearest_River_FID': 'nunique',
    'GVFK': 'nunique'
})
multi_river_sites = multi_river_sites[(multi_river_sites['Nearest_River_FID'] > 1) & (multi_river_sites['GVFK'] > 1)]

if len(multi_river_sites) > 0:
    example_site = multi_river_sites.index[0]
    site_data = site_flux[site_flux['Lokalitet_ID'] == example_site]

    print(f"\nSite: {example_site}")
    print(f"Name: {site_data.iloc[0]['Lokalitetsnavn']}")

    # Show which GVFK goes to which river
    gvfk_river = site_data.groupby(['GVFK', 'DK-modellag']).agg({
        'Nearest_River_ov_navn': lambda x: ', '.join(x.unique()),
        'Pollution_Flux_kg_per_year': 'sum'
    }).reset_index()

    print("\nEach aquifer layer discharges to different river segments:")
    for _, row in gvfk_river.iterrows():
        print(f"  {row['GVFK']} ({row['DK-modellag']}) → {row['Nearest_River_ov_navn']}: {row['Pollution_Flux_kg_per_year']:.3f} kg/yr")

    print("\n  → Flux is NOT summed across rivers, kept separate")
else:
    print("\n(No example found where different layers discharge to completely different rivers)")

print(f"\n{'='*100}")
