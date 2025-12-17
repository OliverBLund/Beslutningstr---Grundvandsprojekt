"""
Diagnostic script to trace ANDRE_AROMATISKE_FORBINDELSER (chlorbenzen) 
through the entire pipeline: Raw Data → Step 4 → Step 5 → Step 6
"""
import pandas as pd
import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from risikovurdering.compound_categories import categorize_substance, COMPOUND_CATEGORIES
from config import get_output_path, V1_CSV_PATH, V2_CSV_PATH

print("=" * 80)
print("DIAGNOSTIC: Tracing ANDRE_AROMATISKE_FORBINDELSER Through Pipeline")
print("=" * 80)

chlorbenzen_keywords = ['chlorbenzen', 'chlorobenzene', 'monochlorbenzen', 'dichlorbenzen', 'trichlorbenzen']
cat_info = COMPOUND_CATEGORIES.get('ANDRE_AROMATISKE_FORBINDELSER', {})
threshold = cat_info.get('distance_m', 150)
print(f"\nCategory threshold: {threshold}m")
print(f"Keywords: {cat_info.get('keywords', [])}")

# ============================================================================
# 1. RAW DATA: How many chlorbenzen substances exist?
# ============================================================================
print("\n" + "=" * 80)
print("STEP 1: RAW V1/V2 DATA")
print("=" * 80)

raw_matches = []
for csv_path, label in [(V1_CSV_PATH, 'V1'), (V2_CSV_PATH, 'V2')]:
    if os.path.exists(csv_path):
        df = pd.read_csv(csv_path, encoding='utf-8')
        if 'Lokalitetensstoffer' in df.columns:
            mask = df['Lokalitetensstoffer'].str.lower().str.contains('|'.join(chlorbenzen_keywords), na=False)
            matched = df[mask][['Lokalitetsnr', 'Lokalitetensstoffer']].copy()
            matched['Source'] = label
            raw_matches.append(matched)
            print(f"  {label}: {len(matched)} rows with chlorbenzen substances")

if raw_matches:
    raw_df = pd.concat(raw_matches, ignore_index=True)
    print(f"\n  Total raw: {len(raw_df)} rows, {raw_df['Lokalitetsnr'].nunique()} unique sites")
    print(f"\n  Sample sites:")
    for _, row in raw_df.head(5).iterrows():
        print(f"    - {row['Lokalitetsnr']}: {row['Lokalitetensstoffer'][:60]}...")
else:
    raw_df = pd.DataFrame()
    print("  No raw matches found!")

# ============================================================================
# 2. STEP 4: Are these sites in the distance results?
# ============================================================================
print("\n" + "=" * 80)
print("STEP 4: DISTANCE RESULTS (After infiltration filter)")
print("=" * 80)

step4_path = get_output_path("step4_final_distances_for_risk_assessment")
if os.path.exists(step4_path):
    step4_df = pd.read_csv(step4_path)
    print(f"  Total Step 4 rows: {len(step4_df)}")
    
    # Find chlorbenzen sites in Step 4
    if not raw_df.empty:
        chlorbenzen_sites = raw_df['Lokalitetsnr'].unique()
        step4_chlorbenzen = step4_df[step4_df['Lokalitet_ID'].isin(chlorbenzen_sites)]
        print(f"  Chlorbenzen sites in Step 4: {len(step4_chlorbenzen)} rows, {step4_chlorbenzen['Lokalitet_ID'].nunique()} unique sites")
        
        if not step4_chlorbenzen.empty:
            print(f"\n  Distance statistics for chlorbenzen sites:")
            print(f"    Min: {step4_chlorbenzen['Distance_to_River_m'].min():.0f}m")
            print(f"    Max: {step4_chlorbenzen['Distance_to_River_m'].max():.0f}m")
            print(f"    Median: {step4_chlorbenzen['Distance_to_River_m'].median():.0f}m")
            
            within_threshold = step4_chlorbenzen[step4_chlorbenzen['Distance_to_River_m'] <= threshold]
            print(f"\n  Within {threshold}m threshold: {len(within_threshold)} rows, {within_threshold['Lokalitet_ID'].nunique()} unique sites")
            
            if len(within_threshold) > 0:
                print(f"\n  Sites within threshold:")
                for _, row in within_threshold.head(10).iterrows():
                    print(f"    - {row['Lokalitet_ID']}: {row['Distance_to_River_m']:.0f}m to river")
            else:
                print(f"\n  ⚠️  NO sites within {threshold}m threshold!")
                print(f"  Closest chlorbenzen sites:")
                closest = step4_chlorbenzen.nsmallest(5, 'Distance_to_River_m')
                for _, row in closest.iterrows():
                    print(f"    - {row['Lokalitet_ID']}: {row['Distance_to_River_m']:.0f}m")
else:
    print("  Step 4 file not found!")

# ============================================================================
# 3. STEP 5B: Did any make it through compound filtering?
# ============================================================================
print("\n" + "=" * 80)
print("STEP 5B: COMPOUND-SPECIFIC RESULTS")
print("=" * 80)

step5b_path = get_output_path("step5b_compound_combinations")
if os.path.exists(step5b_path):
    step5b_df = pd.read_csv(step5b_path)
    print(f"  Total Step 5b rows: {len(step5b_df)}")
    
    # Check for ANDRE_AROMATISKE_FORBINDELSER category
    andre_mask = step5b_df['Qualifying_Category'] == 'ANDRE_AROMATISKE_FORBINDELSER'
    andre_count = andre_mask.sum()
    print(f"  ANDRE_AROMATISKE_FORBINDELSER count: {andre_count}")
    
    if andre_count > 0:
        print(f"\n  ANDRE_AROMATISKE rows:")
        print(step5b_df[andre_mask][['Lokalitet_ID', 'Qualifying_Substance', 'Distance_to_River_m', 'Category_Threshold_m']])
    else:
        print(f"\n  ⚠️  NO ANDRE_AROMATISKE_FORBINDELSER entries in Step 5b!")
        
        # Check if any chlorbenzen-related substances exist under different categories
        if 'Qualifying_Substance' in step5b_df.columns:
            chlorbenzen_in_5b = step5b_df[step5b_df['Qualifying_Substance'].str.lower().str.contains('|'.join(chlorbenzen_keywords), na=False)]
            if len(chlorbenzen_in_5b) > 0:
                print(f"\n  Chlorbenzen substances found under OTHER categories:")
                print(chlorbenzen_in_5b[['Lokalitet_ID', 'Qualifying_Substance', 'Qualifying_Category', 'Distance_to_River_m']])
else:
    print("  Step 5b file not found!")

# ============================================================================
# 4. STEP 6: Any in flux/Cmix results?
# ============================================================================
print("\n" + "=" * 80)
print("STEP 6: TILSTANDSVURDERING RESULTS")
print("=" * 80)

step6_path = get_output_path("step6_flux_site_segment")
if os.path.exists(step6_path):
    step6_df = pd.read_csv(step6_path)
    print(f"  Total Step 6 flux rows: {len(step6_df)}")
    
    if 'Qualifying_Category' in step6_df.columns:
        andre_mask = step6_df['Qualifying_Category'] == 'ANDRE_AROMATISKE_FORBINDELSER'
        print(f"  ANDRE_AROMATISKE_FORBINDELSER in flux: {andre_mask.sum()}")
else:
    print("  Step 6 flux file not found!")

# ============================================================================
# SUMMARY
# ============================================================================
print("\n" + "=" * 80)
print("SUMMARY: Why no ANDRE_AROMATISKE_FORBINDELSER?")
print("=" * 80)

if not raw_df.empty:
    total_raw = len(raw_df)
    if 'step4_chlorbenzen' in dir() and not step4_chlorbenzen.empty:
        in_step4 = len(step4_chlorbenzen)
        within = len(within_threshold) if 'within_threshold' in dir() else 0
        print(f"  1. Raw data: {total_raw} chlorbenzen entries")
        print(f"  2. Survived to Step 4: {in_step4} entries")
        print(f"  3. Within {threshold}m threshold: {within} entries")
        
        if within == 0:
            print(f"\n  CONCLUSION: All chlorbenzen sites are too far (>{threshold}m) from rivers!")
            print(f"              Consider increasing threshold if appropriate.")
    else:
        print(f"  Chlorbenzen sites were filtered out before Step 4 (infiltration filter?)")

print("\n" + "=" * 80)

