"""Gather statistics for Tilstandsvurdering results summary"""
import sys
sys.path.insert(0, '.')
import pandas as pd
from config import get_output_path

# Load Step 6 outputs
flux = pd.read_csv(get_output_path('step6_flux_site_segment'))
cmix = pd.read_csv(get_output_path('step6_cmix_results'))
seg_summary = pd.read_csv(get_output_path('step6_segment_summary'))
exceedances = pd.read_csv(get_output_path('step6_site_mkk_exceedances'))

print("="*70)
print("TILSTANDSVURDERING RESULTS SUMMARY")
print("="*70)

# Overall impact
print("\n### Overall Impact (all scenarios)")
print(f"Input from risikovurdering: {flux['Lokalitet_ID'].nunique():,} sites")
print(f"River segments analyzed: {flux['Nearest_River_FID'].nunique():,}")
print(f"GVFKs analyzed: {flux['GVFK'].nunique():,}")

# MKK Exceedances
print("\n### MKK Exceedances")
exc_segments = seg_summary[seg_summary['Has_MKK_Exceedance'] == True]
print(f"Segments with MKK exceedance: {len(exc_segments):,}")
print(f"Sites contributing to exceedances: {exceedances['Lokalitet_ID'].nunique():,}")
print(f"GVFKs with exceedances: {exceedances['GVFK'].nunique():,}")

# By flow scenario
print("\n### Exceedances by Flow Scenario")
q95_exc = cmix[(cmix['Flow_Scenario'] == 'Q95') & (cmix['Exceedance_Flag'] == True)]
q50_exc = cmix[(cmix['Flow_Scenario'] == 'Q50') & (cmix['Exceedance_Flag'] == True)]
q05_exc = cmix[(cmix['Flow_Scenario'] == 'Q05') & (cmix['Exceedance_Flag'] == True)]

print(f"Q95 (low flow): {q95_exc['Nearest_River_FID'].nunique():,} segments exceed MKK")
print(f"Q50 (median flow): {q50_exc['Nearest_River_FID'].nunique():,} segments exceed MKK")
print(f"Q05 (high flow): {q05_exc['Nearest_River_FID'].nunique():,} segments exceed MKK")

# By category
print("\n### Exceedances by Category (Q95 scenario)")
q95_by_cat = q95_exc.groupby('Qualifying_Category').agg({
    'Nearest_River_FID': 'nunique',
    'Exceedance_Ratio': ['max', 'median']
}).reset_index()
q95_by_cat.columns = ['Category', 'Segments', 'Max_Ratio', 'Median_Ratio']
q95_by_cat = q95_by_cat.sort_values('Segments', ascending=False)
print(q95_by_cat.to_string(index=False))

# Extreme ratios
print("\n### Extreme Exceedance Ratios")
max_ratio = cmix['Exceedance_Ratio'].max()
median_ratio = cmix[cmix['Exceedance_Flag'] == True]['Exceedance_Ratio'].median()
print(f"Maximum exceedance ratio: {max_ratio:,.0f}x MKK")
print(f"Median exceedance ratio: {median_ratio:,.1f}x MKK")

# Note about low flow
print("\n### Note on Low Flow Impact")
low_flow_segments = q95_exc['Nearest_River_FID'].unique()
not_in_q05 = set(low_flow_segments) - set(q05_exc['Nearest_River_FID'].unique())
print(f"Segments exceeding only at Q95 (low flow): {len(not_in_q05):,}")
print(f"Segments exceeding at all flow scenarios: {len(set(low_flow_segments) & set(q05_exc['Nearest_River_FID'].unique())):,}")

# Summary table data
print("\n" + "="*70)
print("SUGGESTED TABLE FOR REPORT:")
print("="*70)
print("""
| Metrik | Værdi |
|--------|-------|
| Vandløbssegmenter med stofpåvirkning | {segments} |
| Segmenter med MKK-overskridelse (Q95) | {exc_segments} |
| Bidragende lokaliteter | {sites} |
| Påvirkede GVF'er | {gvfks} |
| Højeste Cmix/MKK-forhold | {max_ratio:,.0f}× |
| Median Cmix/MKK-forhold | {median_ratio:.1f}× |
""".format(
    segments=flux['Nearest_River_FID'].nunique(),
    exc_segments=len(exc_segments),
    sites=exceedances['Lokalitet_ID'].nunique(),
    gvfks=exceedances['GVFK'].nunique(),
    max_ratio=max_ratio,
    median_ratio=median_ratio,
))
