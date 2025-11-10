"""Investigate negative infiltration values"""
import pandas as pd
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent.parent
RESULTS_DIR = BASE_DIR / "Resultater"

# Load site flux data
site_flux = pd.read_csv(RESULTS_DIR / "step6_flux_site_segment.csv")

print("=" * 80)
print("NEGATIVE INFILTRATION INVESTIGATION")
print("=" * 80)

# Identify negative infiltration
negative_inf = site_flux['Infiltration_mm_per_year'] < 0
positive_inf = site_flux['Infiltration_mm_per_year'] >= 0

print(f"\nTotal rows: {len(site_flux)}")
print(f"Negative infiltration: {negative_inf.sum()} ({negative_inf.sum()/len(site_flux)*100:.1f}%)")
print(f"Positive infiltration: {positive_inf.sum()} ({positive_inf.sum()/len(site_flux)*100:.1f}%)")

# Statistics on negative infiltration
if negative_inf.any():
    print("\nNegative infiltration statistics:")
    print(f"  Min: {site_flux.loc[negative_inf, 'Infiltration_mm_per_year'].min():.2f} mm/year")
    print(f"  Max: {site_flux.loc[negative_inf, 'Infiltration_mm_per_year'].max():.2f} mm/year")
    print(f"  Mean: {site_flux.loc[negative_inf, 'Infiltration_mm_per_year'].mean():.2f} mm/year")
    print(f"  Median: {site_flux.loc[negative_inf, 'Infiltration_mm_per_year'].median():.2f} mm/year")

# Statistics on positive infiltration
print("\nPositive infiltration statistics:")
print(f"  Min: {site_flux.loc[positive_inf, 'Infiltration_mm_per_year'].min():.2f} mm/year")
print(f"  Max: {site_flux.loc[positive_inf, 'Infiltration_mm_per_year'].max():.2f} mm/year")
print(f"  Mean: {site_flux.loc[positive_inf, 'Infiltration_mm_per_year'].mean():.2f} mm/year")
print(f"  Median: {site_flux.loc[positive_inf, 'Infiltration_mm_per_year'].median():.2f} mm/year")

# Check distribution by DK-modellag
print("\n" + "=" * 80)
print("NEGATIVE INFILTRATION BY MODEL LAYER")
print("=" * 80)
layer_analysis = site_flux.groupby('DK-modellag').agg({
    'Infiltration_mm_per_year': ['count', lambda x: (x < 0).sum(), 'mean', 'min', 'max']
})
layer_analysis.columns = ['Total', 'Negative_Count', 'Mean_Inf', 'Min_Inf', 'Max_Inf']
layer_analysis['Negative_%'] = layer_analysis['Negative_Count'] / layer_analysis['Total'] * 100
layer_analysis = layer_analysis.sort_values('Negative_%', ascending=False)
print(layer_analysis)

# Check distribution by region
print("\n" + "=" * 80)
print("NEGATIVE INFILTRATION BY REGION")
print("=" * 80)
region_analysis = site_flux.groupby('Regionsnavn').agg({
    'Infiltration_mm_per_year': ['count', lambda x: (x < 0).sum(), 'mean']
})
region_analysis.columns = ['Total', 'Negative_Count', 'Mean_Inf']
region_analysis['Negative_%'] = region_analysis['Negative_Count'] / region_analysis['Total'] * 100
region_analysis = region_analysis.sort_values('Negative_%', ascending=False)
print(region_analysis)

# Sample negative infiltration sites
print("\n" + "=" * 80)
print("SAMPLE NEGATIVE INFILTRATION SITES")
print("=" * 80)
neg_sample = site_flux[negative_inf].head(20)[
    ['Lokalitet_ID', 'Lokalitetsnavn', 'DK-modellag', 'Infiltration_mm_per_year',
     'Area_m2', 'Standard_Concentration_ug_L', 'Pollution_Flux_kg_per_year',
     'Regionsnavn', 'Kommunenavn']
]
print(neg_sample.to_string(index=False))

# Check if negative infiltration correlates with site characteristics
print("\n" + "=" * 80)
print("SPATIAL CHARACTERISTICS OF NEGATIVE INFILTRATION")
print("=" * 80)

# Unique sites with negative infiltration
neg_sites = site_flux[negative_inf]['Lokalitet_ID'].unique()
print(f"\nUnique sites with negative infiltration: {len(neg_sites)}")

# Check site types
print("\nSite types with negative infiltration:")
site_type_neg = site_flux[negative_inf].groupby('Site_Type').size().sort_values(ascending=False)
print(site_type_neg)

# Check GVFK
print("\nTop GVFKs with negative infiltration:")
gvfk_neg = site_flux[negative_inf].groupby('GVFK').size().sort_values(ascending=False).head(10)
print(gvfk_neg)

print("\n" + "=" * 80)
print("CONCLUSION")
print("=" * 80)
print("\nNegative infiltration values suggest:")
print("  1. Discharge zones where groundwater flows upward")
print("  2. Areas with high evapotranspiration exceeding recharge")
print("  3. Potential modeling artifacts in Step 4 infiltration calculation")
print("\nRecommendation: Review Step 4 infiltration methodology and decide on")
print("handling policy (set to zero, use absolute value, or keep as-is).")
