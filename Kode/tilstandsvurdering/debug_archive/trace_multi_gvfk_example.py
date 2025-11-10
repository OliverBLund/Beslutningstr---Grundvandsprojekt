"""Trace what happens when a site affects multiple GVFKs in different layers"""
import pandas as pd
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent.parent
RESULTS_DIR = BASE_DIR / "Resultater"

site_flux = pd.read_csv(RESULTS_DIR / "step6_flux_site_segment.csv")

print("=" * 80)
print("MULTI-GVFK SITE EXAMPLE")
print("=" * 80)

# Find a site with multiple GVFKs in different layers
multi_gvfk = site_flux.groupby('Lokalitet_ID').agg({
    'GVFK': 'nunique',
    'DK-modellag': 'nunique'
})
multi_gvfk = multi_gvfk[(multi_gvfk['GVFK'] > 1) & (multi_gvfk['DK-modellag'] > 1)]

if len(multi_gvfk) > 0:
    example_site = multi_gvfk.index[0]
else:
    # Fallback: any site with multiple GVFKs
    multi = site_flux.groupby('Lokalitet_ID')['GVFK'].nunique()
    example_site = multi[multi > 1].index[0]

site_data = site_flux[site_flux['Lokalitet_ID'] == example_site].copy()

print(f"\nSite ID: {example_site}")
print(f"Site Name: {site_data.iloc[0]['Lokalitetsnavn']}")
print(f"Site Area: {site_data.iloc[0]['Area_m2']:.1f} m²")
print(f"Total rows (all combinations): {len(site_data)}")

# Show GVFK-Layer combinations
gvfk_info = site_data.groupby(['GVFK', 'DK-modellag']).agg({
    'Infiltration_mm_per_year': 'first',
    'Qualifying_Substance': 'count'
}).reset_index()
gvfk_info.columns = ['GVFK', 'Layer', 'Infiltration_mm/yr', 'Num_Substances']

print(f"\n{'-'*80}")
print("GVFK-LAYER COMBINATIONS:")
print(f"{'-'*80}")
print(gvfk_info.to_string(index=False))

# Show which rivers each GVFK connects to
rivers = site_data.groupby(['GVFK', 'DK-modellag']).agg({
    'Nearest_River_ov_id': lambda x: x.iloc[0],
    'Nearest_River_ov_navn': lambda x: x.iloc[0],
    'Distance_to_River_m': lambda x: x.iloc[0]
}).reset_index()

print(f"\n{'-'*80}")
print("RIVERS CONNECTED TO EACH GVFK:")
print(f"{'-'*80}")
print(rivers.to_string(index=False))

# Show flux calculation for one substance across different GVFKs
substance_example = site_data['Qualifying_Substance'].iloc[0]
substance_rows = site_data[site_data['Qualifying_Substance'] == substance_example].copy()

print(f"\n{'-'*80}")
print(f"FLUX CALCULATION FOR: {substance_example}")
print(f"{'-'*80}")
for idx, row in substance_rows.iterrows():
    print(f"\nGVFK: {row['GVFK']} (Layer: {row['DK-modellag']})")
    print(f"  River: {row['Nearest_River_ov_navn']}")
    print(f"  Area: {row['Area_m2']:.1f} m²")
    print(f"  Infiltration: {row['Infiltration_mm_per_year']:.2f} mm/year")
    print(f"  Concentration: {row['Standard_Concentration_ug_L']:.1f} µg/L")
    print(f"  → Flux: {row['Pollution_Flux_kg_per_year']:.3f} kg/year")

print(f"\n{'='*80}")
print("KEY INSIGHT:")
print(f"{'='*80}")
print("""
When a site affects multiple GVFKs in different layers:

1. SAME site location (same X,Y coordinates, same Area)
2. DIFFERENT layers → sample DIFFERENT rasters → DIFFERENT infiltration
3. SAME concentration for each substance
4. Result: DIFFERENT flux to DIFFERENT rivers through DIFFERENT aquifers

This represents the reality that:
- Contamination can travel through multiple aquifer layers
- Each layer has different infiltration rates
- Each layer may discharge to different river segments
""")

# Check if the rivers shapefile has flux info
print(f"\n{'='*80}")
print("RIVERS SHAPEFILE FLUX COLUMNS (from description):")
print(f"{'='*80}")
print("""
The rivers shapefile contains UPWARD flux from aquifer to river:
- flux_dkmlag: Upward flux from contact aquifer [mm/year]
- flux_lag12: Upward flux to top layer [mm/year]
- Aq2r_dkmlag: Direct flux from contact aquifer to river section
- Aq2r_all: Direct flux from all layers to river section

These represent GAINING STREAMS (groundwater → river).
We calculate DOWNWARD flux (contaminated site → groundwater → river).

The river shapefile also has:
- dkmlag: Which layer the river contacts
- GVForekom: Which GVFK the river segment is in

So the rivers file tells us which aquifer layer each river segment "taps into".
""")
