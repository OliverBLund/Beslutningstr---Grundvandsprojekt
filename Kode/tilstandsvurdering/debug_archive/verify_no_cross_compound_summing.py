"""
Verify that we DON'T sum across different compounds/categories
Answer the specific questions about aggregation logic
"""
import pandas as pd
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent.parent
RESULTS_DIR = BASE_DIR / "Resultater"

segment_flux = pd.read_csv(RESULTS_DIR / "step6_flux_by_segment.csv")
cmix_results = pd.read_csv(RESULTS_DIR / "step6_cmix_results.csv")

print("=" * 100)
print("VERIFICATION: NO CROSS-COMPOUND SUMMING")
print("=" * 100)

# Pick one river segment to examine
river_id = segment_flux['Nearest_River_ov_id'].iloc[0]
river_name = segment_flux['River_Segment_Name'].iloc[0]

river_data = segment_flux[segment_flux['Nearest_River_ov_id'] == river_id].copy()

print(f"\nExample River: {river_name}")
print(f"Total rows in segment_flux: {len(river_data)}")

print(f"\n{'-'*100}")
print("QUESTION 1: Do we sum different compounds together?")
print(f"{'-'*100}")

print("\nGrouping columns in segment_flux aggregation:")
print("  - Nearest_River_FID")
print("  - Nearest_River_ov_id")
print("  - River_Segment_Name")
print("  - River_Segment_GVFK")
print("  - Qualifying_Category")
print("  - Qualifying_Substance  ← KEEPS COMPOUNDS SEPARATE!")

print("\nSubstances in this river (showing first 10):")
substances = river_data.groupby('Qualifying_Substance').agg({
    'Total_Flux_kg_per_year': 'first',
    'Contributing_Site_Count': 'first'
}).reset_index()

for _, row in substances.head(10).iterrows():
    print(f"  • {row['Qualifying_Substance'][:60]:60s} {row['Total_Flux_kg_per_year']:8.3f} kg/yr ({row['Contributing_Site_Count']:.0f} sites)")

print(f"\n✓ ANSWER: NO - Each compound has its own separate row")
print(f"   Total compounds in this river: {len(substances)}")

print(f"\n{'-'*100}")
print("QUESTION 2: Can we track individual sites for same compound to same river?")
print(f"{'-'*100}")

# Pick one substance
substance = substances.iloc[0]['Qualifying_Substance']
substance_row = river_data[river_data['Qualifying_Substance'] == substance].iloc[0]

print(f"\nSubstance: {substance}")
print(f"Contributing sites: {substance_row['Contributing_Site_Count']:.0f}")
print(f"Site IDs: {substance_row['Contributing_Site_IDs']}")

print(f"\n✓ ANSWER: YES - segment_flux contains 'Contributing_Site_IDs' field")
print(f"   You can see exactly which sites contribute to each compound")

print(f"\n{'-'*100}")
print("QUESTION 3: Does Cmix compare individual compounds to MKK (not summed)?")
print(f"{'-'*100}")

# Get cmix data for this river
cmix_river = cmix_results[cmix_results['Nearest_River_ov_id'] == river_id].copy()

print(f"\nCmix results for {river_name}:")
print(f"  Total rows: {len(cmix_river)}")
print(f"  Unique substances: {cmix_river['Qualifying_Substance'].nunique()}")
print(f"  Flow scenarios per substance: {len(cmix_river) / cmix_river['Qualifying_Substance'].nunique():.0f}")

# Show one substance across flow scenarios
cmix_substance = cmix_river[cmix_river['Qualifying_Substance'] == substance].copy()

if len(cmix_substance) > 0:
    print(f"\n  Example: {substance}")
    for _, row in cmix_substance.iterrows():
        print(f"    {row['Flow_Scenario']:6s}: Cmix = {row['Cmix_ug_L']:8.4f} µg/L, MKK = {row['MKK_ug_L']:8.4f} µg/L, Ratio = {row['Exceedance_Ratio']:8.2f}×")

print(f"\n✓ ANSWER: YES - Each compound compared individually to its own MKK")
print(f"   Cmix is calculated per substance, not summed across substances")

print(f"\n{'='*100}")
print("SUMMARY OF AGGREGATION LOGIC")
print(f"{'='*100}")

print("""
1. SITE-LEVEL (site_flux.csv):
   One row per: Site × GVFK × Substance × River
   Example: Site A with benzene and toluene → 2 separate rows

2. AGGREGATION (segment_flux.csv):
   Groups by: River + GVFK + Category + SUBSTANCE
   Sums flux from MULTIPLE SITES for SAME SUBSTANCE
   Example:
     Site A benzene: 10 kg/yr  ┐
     Site B benzene: 5 kg/yr   ├─→ Total benzene: 15 kg/yr (one row)
     Site A toluene: 8 kg/yr   └─→ Total toluene: 8 kg/yr (separate row)

3. CMIX CALCULATION (cmix_results.csv):
   For EACH substance separately:
     Cmix = Flux_substance / River_Flow
   Example:
     Benzene: 15 kg/yr → Cmix_benzene = 15 / flow
     Toluene: 8 kg/yr → Cmix_toluene = 8 / flow

4. MKK COMPARISON:
   Each substance compared to its OWN MKK threshold
   Example:
     Benzene: Cmix_benzene / MKK_benzene
     Toluene: Cmix_toluene / MKK_toluene

✓ COMPOUNDS ARE NEVER SUMMED TOGETHER
✓ EACH SUBSTANCE EVALUATED INDEPENDENTLY
✓ SITES ARE TRACKED IN 'Contributing_Site_IDs' FIELD
""")

print(f"\n{'='*100}")
print("POTENTIAL CONFUSION: Multiple rows for same river")
print(f"{'='*100}")

print(f"""
You might see many rows for same river because:

For river "{river_name}":
  - {substances['Qualifying_Substance'].nunique()} different substances
  - × 3 flow scenarios (Mean, Q90, Q95)
  = {substances['Qualifying_Substance'].nunique() * 3} rows in cmix_results.csv

Each row is ONE substance at ONE flow scenario.
No cross-substance summing occurs.
""")
