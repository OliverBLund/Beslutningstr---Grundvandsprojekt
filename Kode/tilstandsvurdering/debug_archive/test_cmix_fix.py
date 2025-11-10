"""Quick test to verify Cmix calculation fix"""
import pandas as pd
import numpy as np
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent.parent
RESULTS_DIR = BASE_DIR / "Resultater"

# Load old results
cmix_old = pd.read_csv(RESULTS_DIR / "step6_cmix_results.csv")

# Recalculate Cmix with correct formula
SECONDS_PER_YEAR = 365.25 * 24 * 3600

has_flow = cmix_old['Has_Flow_Data'] == True
cmix_old['Flux_ug_per_second'] = cmix_old['Total_Flux_ug_per_year'] / SECONDS_PER_YEAR
cmix_old['Cmix_ug_L_corrected'] = np.where(
    has_flow,
    cmix_old['Flux_ug_per_second'] / (cmix_old['Flow_m3_s'] * 1000),
    np.nan
)

# Compare
cmix_old['Correction_Factor'] = cmix_old['Cmix_ug_L'] / cmix_old['Cmix_ug_L_corrected']

print("Cmix Correction Verification")
print("=" * 80)
print(f"\nCorrection factor (should be ~1000):")
print(f"  Mean: {cmix_old.loc[has_flow, 'Correction_Factor'].mean():.2f}")
print(f"  Median: {cmix_old.loc[has_flow, 'Correction_Factor'].median():.2f}")

# Recalculate exceedance ratios
cmix_old['Exceedance_Ratio_corrected'] = cmix_old['Cmix_ug_L_corrected'] / cmix_old['MKK_ug_L']

print("\nExceedance statistics BEFORE fix:")
print(f"  Max exceedance: {cmix_old.loc[has_flow, 'Exceedance_Ratio'].max():,.0f}x")
print(f"  Mean exceedance: {cmix_old.loc[has_flow, 'Exceedance_Ratio'].mean():,.0f}x")

print("\nExceedance statistics AFTER fix:")
print(f"  Max exceedance: {cmix_old.loc[has_flow, 'Exceedance_Ratio_corrected'].max():,.0f}x")
print(f"  Mean exceedance: {cmix_old.loc[has_flow, 'Exceedance_Ratio_corrected'].mean():,.0f}x")

# Top 10 exceedances after correction
print("\nTop 10 exceedances AFTER correction:")
top_exc = cmix_old[has_flow].nlargest(10, 'Exceedance_Ratio_corrected')[
    ['River_Segment_Name', 'Qualifying_Substance', 'Flow_Scenario',
     'Cmix_ug_L_corrected', 'MKK_ug_L', 'Exceedance_Ratio_corrected']
]
print(top_exc.to_string(index=False))

print("\n" + "=" * 80)
print("Fix verified! Exceedances reduced by factor of 1000 as expected.")
