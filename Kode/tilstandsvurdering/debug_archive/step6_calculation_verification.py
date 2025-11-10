"""
Step 6 Calculation Verification Script

This script thoroughly examines the calculated fluxes, Cmix values, and MKK comparisons
to verify the approach is sound and identify any potential issues.
"""

import pandas as pd
import numpy as np
from pathlib import Path

# File paths
BASE_DIR = Path(__file__).parent.parent.parent
RESULTS_DIR = BASE_DIR / "Resultater"

def load_data():
    """Load all Step 6 output files"""
    site_flux = pd.read_csv(RESULTS_DIR / "step6_flux_site_segment.csv")
    segment_flux = pd.read_csv(RESULTS_DIR / "step6_flux_by_segment.csv")
    cmix_results = pd.read_csv(RESULTS_DIR / "step6_cmix_results.csv")
    segment_summary = pd.read_csv(RESULTS_DIR / "step6_segment_summary.csv")

    return site_flux, segment_flux, cmix_results, segment_summary

def analyze_flux_calculations(site_flux):
    """Verify flux calculations: Flux = Area * Infiltration * Standard_Concentration"""
    print("=" * 80)
    print("FLUX CALCULATION VERIFICATION")
    print("=" * 80)
    print("\nFormula: Flux (ug/year) = Area (m2) * Infiltration (mm/year) * Concentration (ug/L)")
    print("         Flux (ug/year) = Area (m2) * (Infiltration_mm/1000) (m/year) * Concentration (ug/L)")
    print("         Flux (ug/year) = Area * Infiltration_mm/1000 * Concentration * 1000 L/m3")
    print("         Flux (ug/year) = Area * Infiltration_mm * Concentration")

    # Recalculate flux for verification
    site_flux['Calculated_Flux_ug_per_year'] = (
        site_flux['Area_m2'] *
        site_flux['Infiltration_mm_per_year'] *
        site_flux['Standard_Concentration_ug_L']
    )

    site_flux['Flux_Difference'] = (
        site_flux['Pollution_Flux_ug_per_year'] - site_flux['Calculated_Flux_ug_per_year']
    )

    site_flux['Flux_Relative_Error'] = (
        site_flux['Flux_Difference'] / site_flux['Calculated_Flux_ug_per_year'].abs()
    )

    # Check for discrepancies
    max_error = site_flux['Flux_Relative_Error'].abs().max()
    print(f"\nMax relative error in flux calculation: {max_error:.2e}")

    if max_error > 1e-6:
        print(f"WARNING: Found {(site_flux['Flux_Relative_Error'].abs() > 1e-6).sum()} rows with calculation errors")
        problem_rows = site_flux[site_flux['Flux_Relative_Error'].abs() > 1e-6].head()
        print("\nSample problematic rows:")
        print(problem_rows[['Lokalitet_ID', 'Area_m2', 'Infiltration_mm_per_year',
                            'Standard_Concentration_ug_L', 'Pollution_Flux_ug_per_year',
                            'Calculated_Flux_ug_per_year', 'Flux_Difference']])
    else:
        print("✓ All flux calculations verified correctly")

    # Check for negative fluxes
    negative_count = (site_flux['Pollution_Flux_ug_per_year'] < 0).sum()
    print(f"\nNegative flux count: {negative_count} ({negative_count/len(site_flux)*100:.1f}%)")

    if negative_count > 0:
        print("\nSample negative fluxes:")
        neg_sample = site_flux[site_flux['Pollution_Flux_ug_per_year'] < 0].head(10)
        print(neg_sample[['Lokalitet_ID', 'Qualifying_Substance', 'Area_m2',
                         'Infiltration_mm_per_year', 'Standard_Concentration_ug_L',
                         'Pollution_Flux_ug_per_year']])

    # Statistical summary
    print("\n" + "=" * 80)
    print("FLUX STATISTICS")
    print("=" * 80)
    print(f"\nTotal rows: {len(site_flux)}")
    print(f"Total flux (kg/year): {site_flux['Pollution_Flux_kg_per_year'].sum():,.2f}")
    print(f"Mean flux (kg/year): {site_flux['Pollution_Flux_kg_per_year'].mean():,.2f}")
    print(f"Median flux (kg/year): {site_flux['Pollution_Flux_kg_per_year'].median():,.4f}")
    print(f"Min flux (kg/year): {site_flux['Pollution_Flux_kg_per_year'].min():,.2f}")
    print(f"Max flux (kg/year): {site_flux['Pollution_Flux_kg_per_year'].max():,.2f}")

    # Flux by category
    print("\nFlux by category:")
    flux_by_cat = site_flux.groupby('Qualifying_Category')['Pollution_Flux_kg_per_year'].agg(['sum', 'mean', 'count'])
    flux_by_cat = flux_by_cat.sort_values('sum', ascending=False)
    print(flux_by_cat)

def analyze_cmix_calculations(cmix_results):
    """Verify Cmix calculations: Cmix = Flux / Flow"""
    print("\n" + "=" * 80)
    print("CMIX CALCULATION VERIFICATION")
    print("=" * 80)
    print("\nFormula: Cmix (ug/L) = Total_Flux (ug/year) / Flow (m3/s) / (365.25 * 24 * 3600) (s/year) / 1000 (L/m3)")
    print("         Cmix (ug/L) = Flux_ug_per_second / (Flow_m3_s * 1000)")

    # Recalculate Cmix
    cmix_results['Flux_ug_per_second_calc'] = cmix_results['Total_Flux_ug_per_year'] / (365.25 * 24 * 3600)
    cmix_results['Cmix_ug_L_calc'] = cmix_results['Flux_ug_per_second_calc'] / (cmix_results['Flow_m3_s'] * 1000)

    # Handle cases with no flow data
    has_flow = cmix_results['Has_Flow_Data'] == True

    # Check flux_ug_per_second
    flux_diff = (cmix_results.loc[has_flow, 'Flux_ug_per_second'] -
                 cmix_results.loc[has_flow, 'Flux_ug_per_second_calc']).abs()
    max_flux_error = (flux_diff / cmix_results.loc[has_flow, 'Flux_ug_per_second_calc'].abs()).max()

    print(f"\nMax relative error in flux_ug_per_second: {max_flux_error:.2e}")

    # Check Cmix
    cmix_diff = (cmix_results.loc[has_flow, 'Cmix_ug_L'] -
                 cmix_results.loc[has_flow, 'Cmix_ug_L_calc']).abs()
    max_cmix_error = (cmix_diff / cmix_results.loc[has_flow, 'Cmix_ug_L_calc'].abs()).max()

    print(f"Max relative error in Cmix: {max_cmix_error:.2e}")

    if max_cmix_error > 1e-6:
        print(f"WARNING: Found calculation errors in Cmix")
        problem_rows = cmix_results[has_flow & ((cmix_diff / cmix_results['Cmix_ug_L_calc'].abs()) > 1e-6)].head()
        print("\nSample problematic rows:")
        print(problem_rows[['River_Segment_Name', 'Flow_Scenario', 'Total_Flux_ug_per_year',
                           'Flow_m3_s', 'Cmix_ug_L', 'Cmix_ug_L_calc']])
    else:
        print("✓ All Cmix calculations verified correctly")

    # Check negative Cmix values
    negative_cmix = (cmix_results['Cmix_ug_L'] < 0).sum()
    print(f"\nNegative Cmix count: {negative_cmix} ({negative_cmix/len(cmix_results)*100:.1f}%)")

    if negative_cmix > 0:
        print("\nSample negative Cmix values:")
        neg_sample = cmix_results[cmix_results['Cmix_ug_L'] < 0].head(10)
        print(neg_sample[['River_Segment_Name', 'Qualifying_Substance', 'Total_Flux_ug_per_year',
                         'Flow_m3_s', 'Cmix_ug_L']])

    # Statistical summary
    print("\n" + "=" * 80)
    print("CMIX STATISTICS (rows with flow data)")
    print("=" * 80)
    cmix_with_flow = cmix_results[has_flow]
    print(f"\nTotal rows: {len(cmix_with_flow)}")
    print(f"Mean Cmix (ug/L): {cmix_with_flow['Cmix_ug_L'].mean():,.2f}")
    print(f"Median Cmix (ug/L): {cmix_with_flow['Cmix_ug_L'].median():,.4f}")
    print(f"Min Cmix (ug/L): {cmix_with_flow['Cmix_ug_L'].min():,.2f}")
    print(f"Max Cmix (ug/L): {cmix_with_flow['Cmix_ug_L'].max():,.2f}")

    # Cmix by flow scenario
    print("\nCmix by flow scenario:")
    cmix_by_scenario = cmix_with_flow.groupby('Flow_Scenario')['Cmix_ug_L'].agg(['mean', 'median', 'count'])
    print(cmix_by_scenario)

def analyze_mkk_comparisons(cmix_results):
    """Analyze MKK threshold comparisons and exceedance ratios"""
    print("\n" + "=" * 80)
    print("MKK THRESHOLD ANALYSIS")
    print("=" * 80)

    # Check MKK coverage
    has_mkk = cmix_results['MKK_ug_L'].notna()
    print(f"\nMKK coverage: {has_mkk.sum()}/{len(cmix_results)} ({has_mkk.sum()/len(cmix_results)*100:.1f}%)")

    if not has_mkk.all():
        print(f"\nWARNING: {(~has_mkk).sum()} rows missing MKK values")
        missing_mkk = cmix_results[~has_mkk][['Qualifying_Substance', 'Qualifying_Category']].drop_duplicates()
        print("\nSubstances/categories missing MKK:")
        print(missing_mkk)

    # Verify exceedance calculation
    has_flow_and_mkk = cmix_results['Has_Flow_Data'] & has_mkk
    cmix_data = cmix_results[has_flow_and_mkk].copy()

    cmix_data['Exceedance_Ratio_calc'] = cmix_data['Cmix_ug_L'] / cmix_data['MKK_ug_L']

    ratio_diff = (cmix_data['Exceedance_Ratio'] - cmix_data['Exceedance_Ratio_calc']).abs()
    max_ratio_error = (ratio_diff / cmix_data['Exceedance_Ratio_calc'].abs()).max()

    print(f"\nMax relative error in exceedance ratio: {max_ratio_error:.2e}")

    if max_ratio_error > 1e-6:
        print(f"WARNING: Found calculation errors in exceedance ratio")
    else:
        print("✓ All exceedance ratio calculations verified correctly")

    # Exceedance statistics
    print("\n" + "=" * 80)
    print("EXCEEDANCE STATISTICS")
    print("=" * 80)

    exceedances = cmix_data[cmix_data['Exceedance_Ratio'] > 1]
    print(f"\nTotal exceedances: {len(exceedances)}/{len(cmix_data)} ({len(exceedances)/len(cmix_data)*100:.1f}%)")
    print(f"Max exceedance ratio: {cmix_data['Exceedance_Ratio'].max():,.2f}x")
    print(f"Mean exceedance ratio (all): {cmix_data['Exceedance_Ratio'].mean():,.2f}x")
    print(f"Mean exceedance ratio (exceedances only): {exceedances['Exceedance_Ratio'].mean():,.2f}x")

    # Exceedances by category
    print("\nExceedances by category:")
    exc_by_cat = cmix_data.groupby('Qualifying_Category').agg({
        'Exceedance_Ratio': ['count', lambda x: (x > 1).sum(), 'max', 'mean']
    })
    exc_by_cat.columns = ['Total', 'Exceedances', 'Max_Ratio', 'Mean_Ratio']
    exc_by_cat['Exceedance_Rate_%'] = exc_by_cat['Exceedances'] / exc_by_cat['Total'] * 100
    exc_by_cat = exc_by_cat.sort_values('Exceedances', ascending=False)
    print(exc_by_cat)

    # Top exceedances
    print("\nTop 10 exceedances:")
    top_exc = cmix_data.nlargest(10, 'Exceedance_Ratio')[
        ['River_Segment_Name', 'Qualifying_Substance', 'Qualifying_Category',
         'Flow_Scenario', 'Cmix_ug_L', 'MKK_ug_L', 'Exceedance_Ratio']
    ]
    print(top_exc.to_string())

    # Negative exceedance ratios (from negative fluxes)
    negative_exc = cmix_data[cmix_data['Exceedance_Ratio'] < 0]
    print(f"\nNegative exceedance ratios: {len(negative_exc)}")
    if len(negative_exc) > 0:
        print("\nSample negative exceedances:")
        print(negative_exc.head(10)[['River_Segment_Name', 'Qualifying_Substance',
                                     'Cmix_ug_L', 'MKK_ug_L', 'Exceedance_Ratio']])

def analyze_aggregation_consistency(site_flux, segment_flux):
    """Verify that segment-level aggregations are consistent with site-level data"""
    print("\n" + "=" * 80)
    print("AGGREGATION CONSISTENCY CHECK")
    print("=" * 80)

    # Aggregate site_flux to segment level
    site_aggregated = site_flux.groupby(
        ['Nearest_River_FID', 'Nearest_River_ov_id', 'Qualifying_Category', 'Qualifying_Substance']
    ).agg({
        'Pollution_Flux_ug_per_year': 'sum',
        'Lokalitet_ID': 'count'
    }).reset_index()

    site_aggregated.rename(columns={
        'Pollution_Flux_ug_per_year': 'Site_Agg_Flux',
        'Lokalitet_ID': 'Site_Count'
    }, inplace=True)

    # Merge with segment_flux
    comparison = segment_flux.merge(
        site_aggregated,
        on=['Nearest_River_FID', 'Nearest_River_ov_id', 'Qualifying_Category', 'Qualifying_Substance'],
        how='outer',
        indicator=True
    )

    # Check for discrepancies
    both = comparison['_merge'] == 'both'
    comparison.loc[both, 'Flux_Diff'] = (
        comparison.loc[both, 'Total_Flux_ug_per_year'] - comparison.loc[both, 'Site_Agg_Flux']
    )
    comparison.loc[both, 'Flux_Rel_Error'] = (
        comparison.loc[both, 'Flux_Diff'] / comparison.loc[both, 'Site_Agg_Flux'].abs()
    )

    max_agg_error = comparison.loc[both, 'Flux_Rel_Error'].abs().max()
    print(f"\nMax relative error in aggregation: {max_agg_error:.2e}")

    if max_agg_error > 1e-6:
        print(f"WARNING: Found aggregation errors")
        problem_rows = comparison[both & (comparison['Flux_Rel_Error'].abs() > 1e-6)].head()
        print("\nSample problematic aggregations:")
        print(problem_rows[['River_Segment_Name', 'Qualifying_Substance', 'Total_Flux_ug_per_year',
                           'Site_Agg_Flux', 'Flux_Diff']])
    else:
        print("✓ All aggregations verified correctly")

    # Check for missing data
    left_only = (comparison['_merge'] == 'left_only').sum()
    right_only = (comparison['_merge'] == 'right_only').sum()

    if left_only > 0:
        print(f"\nWARNING: {left_only} rows in segment_flux not found in site_flux")
    if right_only > 0:
        print(f"\nWARNING: {right_only} rows in site_flux aggregation not found in segment_flux")

def check_unrealistic_values(site_flux, cmix_results):
    """Check for unrealistic or suspicious values"""
    print("\n" + "=" * 80)
    print("UNREALISTIC VALUES CHECK")
    print("=" * 80)

    # Very high concentrations
    high_conc = site_flux[site_flux['Standard_Concentration_ug_L'] > 100000]
    print(f"\nVery high standard concentrations (>100,000 ug/L): {len(high_conc)}")
    if len(high_conc) > 0:
        print(high_conc[['Qualifying_Substance', 'Qualifying_Category', 'Standard_Concentration_ug_L']].drop_duplicates())

    # Very large fluxes
    large_flux = site_flux[site_flux['Pollution_Flux_kg_per_year'] > 1000]
    print(f"\nVery large fluxes (>1000 kg/year): {len(large_flux)}")
    if len(large_flux) > 0:
        print(large_flux[['Lokalitet_ID', 'Lokalitetsnavn', 'Qualifying_Substance',
                         'Area_m2', 'Standard_Concentration_ug_L',
                         'Pollution_Flux_kg_per_year']].head(10))

    # Very high Cmix values
    has_flow = cmix_results['Has_Flow_Data'] == True
    high_cmix = cmix_results[has_flow & (cmix_results['Cmix_ug_L'] > 10000)]
    print(f"\nVery high Cmix values (>10,000 ug/L): {len(high_cmix)}")
    if len(high_cmix) > 0:
        print(high_cmix[['River_Segment_Name', 'Qualifying_Substance', 'Flow_Scenario',
                        'Total_Flux_ug_per_year', 'Flow_m3_s', 'Cmix_ug_L']].head(10))

    # Very low flow values
    low_flow = cmix_results[has_flow & (cmix_results['Flow_m3_s'] < 0.001)]
    print(f"\nVery low flow values (<0.001 m3/s): {len(low_flow)}")
    if len(low_flow) > 0:
        unique_segments = low_flow[['River_Segment_Name', 'Flow_Scenario', 'Flow_m3_s']].drop_duplicates()
        print(unique_segments.head(10))

def main():
    print("Loading data...")
    site_flux, segment_flux, cmix_results, segment_summary = load_data()

    print(f"\nData loaded:")
    print(f"  - Site flux: {len(site_flux)} rows")
    print(f"  - Segment flux: {len(segment_flux)} rows")
    print(f"  - Cmix results: {len(cmix_results)} rows")
    print(f"  - Segment summary: {len(segment_summary)} rows")

    # Run all analyses
    analyze_flux_calculations(site_flux)
    analyze_cmix_calculations(cmix_results)
    analyze_mkk_comparisons(cmix_results)
    analyze_aggregation_consistency(site_flux, segment_flux)
    check_unrealistic_values(site_flux, cmix_results)

    print("\n" + "=" * 80)
    print("VERIFICATION COMPLETE")
    print("=" * 80)

if __name__ == "__main__":
    main()
