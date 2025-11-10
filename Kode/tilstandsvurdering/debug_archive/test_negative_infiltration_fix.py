"""Test impact of setting negative infiltration to zero"""
import pandas as pd
import numpy as np
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent.parent
RESULTS_DIR = BASE_DIR / "Resultater"

# Load current results (with negative infiltration)
site_flux_old = pd.read_csv(RESULTS_DIR / "step6_flux_site_segment.csv")

print("=" * 80)
print("IMPACT OF NEGATIVE INFILTRATION FIX")
print("=" * 80)

# Apply the fix: set negative infiltration to zero
site_flux_fixed = site_flux_old.copy()
negative_mask = site_flux_fixed['Infiltration_mm_per_year'] < 0

print(f"\nRows with negative infiltration: {negative_mask.sum()} ({negative_mask.sum()/len(site_flux_fixed)*100:.1f}%)")

# Recalculate flux with zero infiltration for negative cases
site_flux_fixed.loc[negative_mask, 'Infiltration_mm_per_year'] = 0.0
site_flux_fixed['Pollution_Flux_kg_per_year_fixed'] = (
    site_flux_fixed['Area_m2'] *
    site_flux_fixed['Infiltration_mm_per_year'] *
    site_flux_fixed['Standard_Concentration_ug_L'] / 1e9
)

# Compare total fluxes
print("\n" + "=" * 80)
print("TOTAL FLUX COMPARISON")
print("=" * 80)

old_total = site_flux_old['Pollution_Flux_kg_per_year'].sum()
fixed_total = site_flux_fixed['Pollution_Flux_kg_per_year_fixed'].sum()

print(f"\nTotal flux BEFORE fix: {old_total:,.2f} kg/year")
print(f"Total flux AFTER fix:  {fixed_total:,.2f} kg/year")
print(f"Change: {fixed_total - old_total:+,.2f} kg/year ({(fixed_total/old_total - 1)*100:+.1f}%)")

# Breakdown by category
print("\n" + "=" * 80)
print("FLUX BY CATEGORY (BEFORE vs AFTER)")
print("=" * 80)

comparison = pd.DataFrame({
    'Before': site_flux_old.groupby('Qualifying_Category')['Pollution_Flux_kg_per_year'].sum(),
    'After': site_flux_fixed.groupby('Qualifying_Category')['Pollution_Flux_kg_per_year_fixed'].sum()
})
comparison['Change'] = comparison['After'] - comparison['Before']
comparison['Change_%'] = (comparison['After'] / comparison['Before'] - 1) * 100
comparison = comparison.sort_values('Change', ascending=False)

print(comparison.to_string())

# Sites most affected
print("\n" + "=" * 80)
print("SITES MOST AFFECTED BY FIX")
print("=" * 80)

site_flux_fixed['Flux_Change_kg'] = (
    site_flux_fixed['Pollution_Flux_kg_per_year_fixed'] -
    site_flux_old['Pollution_Flux_kg_per_year']
)

most_affected = site_flux_fixed[negative_mask].nlargest(10, 'Flux_Change_kg')[
    ['Lokalitet_ID', 'Lokalitetsnavn', 'DK-modellag',
     'Infiltration_mm_per_year', 'Pollution_Flux_kg_per_year_fixed', 'Flux_Change_kg']
]
most_affected.columns = ['Lokalitet_ID', 'Lokalitetsnavn', 'Layer',
                          'Infiltration_After', 'Flux_After', 'Flux_Change']

print("\nTop 10 sites with largest flux increase (discharge zones now = 0 flux):")
print(most_affected.to_string(index=False))

print("\n" + "=" * 80)
print("SUMMARY")
print("=" * 80)
print("\nThe fix:")
print("  - Eliminates all negative fluxes (unphysical)")
print("  - Increases total flux by removing negative contributions")
print("  - Physically represents discharge zones as non-contributing to surface water pollution")
print("  - Simplifies interpretation (all fluxes now >= 0)")
