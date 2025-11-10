"""Trace exactly how GVD rasters are used for a specific example"""
import pandas as pd
import geopandas as gpd
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent.parent
RESULTS_DIR = BASE_DIR / "Resultater"

# Load Step 5 output - use the site flux which has what we need
site_flux = pd.read_csv(RESULTS_DIR / "step6_flux_site_segment.csv")

# Pick a concrete example site
example_site = "101-00002"  # From the flux results

print("=" * 80)
print("GVD RASTER USAGE - CONCRETE EXAMPLE")
print("=" * 80)

# Get all rows for this site
site_flux_ex = site_flux[site_flux['Lokalitet_ID'] == example_site].copy()

print(f"\nSite: {example_site}")
print(f"Name: {site_flux_ex.iloc[0]['Lokalitetsnavn']}")
print(f"Total rows: {len(site_flux_ex)}")

# Show unique GVFKs and their layers
gvfk_layers = site_flux_ex[['GVFK', 'DK-modellag']].drop_duplicates()
print(f"\nGVFK-Layer combinations for this site:")
print(gvfk_layers.to_string(index=False))

print("\n" + "=" * 80)
print("HOW IT WORKS:")
print("=" * 80)

print("""
STEP-BY-STEP PROCESS:

1. Site location: Get site centroid coordinates (X, Y in UTM32/EPSG:25832)

2. For each GVFK the site affects:
   - Step 5 tells us which DK-modellag (e.g., "ks2", "ps1")

3. For each substance at that site:
   - Create one row per (Site, GVFK, ModelLag, Substance, River)

4. Sample GVD raster:
   - Open raster: GVD_RASTER_DIR/DKM_gvd_{modellag}.tif
   - Example: DKM_gvd_ks2.tif for modellag="ks2"
   - Sample at site coordinates (X, Y)
   - Get value = Infiltration in mm/year

5. Calculate flux:
   Flux = Site Area (m²) × Infiltration (mm/year) × Concentration (µg/L)

EXAMPLE for site """ + example_site + """:
""")

# Show actual values
for idx, row in site_flux_ex.head(3).iterrows():
    print(f"\nRow {idx}:")
    print(f"  GVFK: {row['GVFK']}")
    print(f"  ModelLag: {row['DK-modellag']}")
    print(f"  Raster used: DKM_gvd_{row['DK-modellag']}.tif")
    print(f"  Site area: {row['Area_m2']:.1f} m²")
    print(f"  Infiltration sampled: {row['Infiltration_mm_per_year']:.2f} mm/year")
    print(f"  Concentration: {row['Standard_Concentration_ug_L']:.1f} µg/L")
    print(f"  Substance: {row['Qualifying_Substance']}")
    print(f"  Flux: {row['Pollution_Flux_kg_per_year']:.2f} kg/year")

print("\n" + "=" * 80)
print("KEY POINTS:")
print("=" * 80)
print("""
- ONE site centroid (X,Y) but MULTIPLE GVFKs (each with own modellag)
- Each GVFK has a DK-modellag (ks1, ks2, ps1, etc.)
- We sample the corresponding raster at the SAME coordinates
- Different modellags = different infiltration values at same location
- This represents different aquifer layers beneath the site

Example: Site 101-00002 is at ONE location but affects TWO GVFKs:
  - dkms_3307_ks (layer ks2): infiltration = 76.76 mm/year
  - dkms_3645_ks (layer ks2): infiltration = 169.32 mm/year

Wait... both are ks2 but different infiltration values?
Let me check if this is possible...
""")

# Check if same modellag gives different values
same_layer = site_flux_ex.groupby('DK-modellag')['Infiltration_mm_per_year'].nunique()
print("\nNumber of unique infiltration values per modellag:")
print(same_layer)

if (same_layer > 1).any():
    print("\n⚠️ FINDING: Same modellag gives different infiltration values!")
    print("This shouldn't happen if we're sampling at same coordinates.")
    print("Possible reasons:")
    print("  1. Site centroid varies by GVFK (shouldn't happen)")
    print("  2. Raster sampling has issues")
    print("  3. Data inconsistency")
else:
    print("\n✓ Confirmed: Same modellag = same infiltration value")
    print("  This is correct - same raster + same coordinates = same value")
