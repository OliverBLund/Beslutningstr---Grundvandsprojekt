"""
Quick check: Examine GVFK with both positive and negative infiltration.
"""
import pandas as pd
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from config import get_output_path

# Load the outputs from the last step6 run
kept = pd.read_csv(get_output_path('step6_flux_site_segment'), encoding='utf-8')
print(f"Kept rows: {len(kept)}")
print(f"Kept GVFK: {kept['GVFK'].nunique()}")
print(f"Infiltration range in kept data: {kept['Infiltration_mm_per_year'].min():.1f} to {kept['Infiltration_mm_per_year'].max():.1f} mm/year")
print()

# Check: Are there any negative values in the kept data?
negative_in_kept = kept[kept['Infiltration_mm_per_year'] < 0]
if len(negative_in_kept) > 0:
    print(f"ERROR: Found {len(negative_in_kept)} negative infiltration rows in kept data!")
    print("This should not happen - all negative should be filtered out.")
else:
    print("OK: No negative infiltration in kept data (correct!)")
print()

# Load negative infiltration validation table (created by visualization)
validation_path = Path(get_output_path('step6_segment_summary')).parent / 'Figures' / 'step6' / 'negative_infiltration' / 'step6_negative_infiltration_validation.csv'

if validation_path.exists():
    removed = pd.read_csv(validation_path, encoding='utf-8')
    print(f"Removed rows: {len(removed)}")
    print(f"Removed GVFK: {removed['GVFK'].nunique()}")
    print(f"Infiltration range in removed data: {removed['Infiltration_mm_per_year'].min():.1f} to {removed['Infiltration_mm_per_year'].max():.1f} mm/year")
    print()

    # Check: Are there any positive values in removed data?
    positive_in_removed = removed[removed['Infiltration_mm_per_year'] >= 0]
    if len(positive_in_removed) > 0:
        print(f"ERROR: Found {len(positive_in_removed)} non-negative infiltration rows in removed data!")
        print("This should not happen - only negative should be removed.")
    else:
        print("OK: All removed rows have negative infiltration (correct!)")
    print()

    # Find GVFK in both datasets (partially affected)
    kept_gvfk = set(kept['GVFK'].unique())
    removed_gvfk = set(removed['GVFK'].unique())
    partial_gvfk = kept_gvfk.intersection(removed_gvfk)
    complete_removal = removed_gvfk - kept_gvfk

    print("="*80)
    print("GVFK ANALYSIS")
    print("="*80)
    print(f"Total GVFK in kept data: {len(kept_gvfk)}")
    print(f"Total GVFK in removed data: {len(removed_gvfk)}")
    print(f"GVFK partially affected (in both datasets): {len(partial_gvfk)}")
    print(f"GVFK completely removed (only in removed): {len(complete_removal)}")
    print()

    # Examine one example of partial GVFK
    if partial_gvfk:
        example = sorted(partial_gvfk)[0]
        print(f"Example partially affected GVFK: {example}")
        print("-"*80)

        kept_ex = kept[kept['GVFK'] == example]
        removed_ex = removed[removed['GVFK'] == example]

        print(f"In KEPT data:")
        print(f"  Rows: {len(kept_ex)}")
        print(f"  Sites: {kept_ex['Lokalitet_ID'].nunique()} unique")
        print(f"  Infiltration: {kept_ex['Infiltration_mm_per_year'].min():.1f} to {kept_ex['Infiltration_mm_per_year'].max():.1f} mm/year")
        print()

        print(f"In REMOVED data:")
        print(f"  Rows: {len(removed_ex)}")
        print(f"  Sites: {removed_ex['Lokalitet_ID'].nunique()} unique")
        print(f"  Infiltration: {removed_ex['Infiltration_mm_per_year'].min():.1f} to {removed_ex['Infiltration_mm_per_year'].max():.1f} mm/year")
        print()

        # Check if same sites appear in both
        kept_sites = set(kept_ex['Lokalitet_ID'].unique())
        removed_sites = set(removed_ex['Lokalitet_ID'].unique())
        overlap = kept_sites.intersection(removed_sites)

        if overlap:
            print(f"  Sites appearing in BOTH kept and removed: {len(overlap)}")
            print(f"    This means these sites have different rows with different infiltration values")
            print(f"    (e.g., different layers or substances)")
            print(f"    Example site: {list(overlap)[0]}")
        else:
            print(f"  No site overlap - different sites within same GVFK have different infiltration")

        print()
        print("CONCLUSION:")
        print("  This is CORRECT behavior! A GVFK (groundwater body) covers a geographic area.")
        print("  Different locations or layers within that area can have different infiltration.")
        print("  Some areas may recharge (positive) while areas near rivers discharge (negative).")

else:
    print("NOTE: Negative infiltration validation file not found.")
    print(f"Expected at: {validation_path}")
