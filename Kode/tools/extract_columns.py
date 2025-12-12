"""Extract column information from Step 4-6 output files for documentation"""
import sys
sys.path.insert(0, '.')
import pandas as pd
from config import get_output_path

files = [
    ('step4_final_distances_for_risk_assessment', 'Step 4: Distance thresholds'),
    ('step5a_high_risk_sites', 'Step 5a: High-risk combinations'),
    ('step5b_compound_combinations', 'Step 5b: Compound-specific'),
    ('step6_flux_site_segment', 'Step 6: Flux per site-segment'),
    ('step6_cmix_results', 'Step 6: Cmix results'),
    ('step6_segment_summary', 'Step 6: Segment summary'),
    ('step6_site_mkk_exceedances', 'Step 6: Site exceedances'),
]

for file_key, description in files:
    try:
        df = pd.read_csv(get_output_path(file_key), nrows=5)
        print(f"\n{'='*70}")
        print(f"{description}")
        print(f"File: {file_key}.csv")
        print(f"Columns ({len(df.columns)}):")
        for col in df.columns:
            sample = df[col].dropna().iloc[0] if not df[col].dropna().empty else 'N/A'
            dtype = df[col].dtype
            print(f"  - {col} ({dtype}): e.g. {str(sample)[:40]}")
    except Exception as e:
        print(f"\n{description}: Error - {e}")
