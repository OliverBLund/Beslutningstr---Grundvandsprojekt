"""
COMPREHENSIVE STEP 5 VALIDATION
===============================

Validate that the landfill override system is working correctly by checking:
1. Data integrity and file outputs
2. Logic correctness with specific examples
3. End-to-end workflow verification
4. Edge cases and error conditions
"""

import pandas as pd
import os
from config import get_output_path

def validate_data_integrity():
    """Validate that output files contain expected data structure."""
    print("1. DATA INTEGRITY VALIDATION")
    print("=" * 40)

    # Check that files exist
    files_to_check = [
        ('step5_compound_detailed_combinations', 'Detailed combinations'),
        ('step5_compound_specific_sites', 'Unique sites'),
        ('step4_final_distances_for_risk_assessment', 'Input distances')
    ]

    for file_key, description in files_to_check:
        file_path = get_output_path(file_key)
        if os.path.exists(file_path):
            df = pd.read_csv(file_path)
            print(f"✓ {description}: {len(df)} rows")
        else:
            print(f"✗ {description}: FILE NOT FOUND")

    # Load detailed combinations for further checks
    detailed_file = get_output_path('step5_compound_detailed_combinations')
    if not os.path.exists(detailed_file):
        print("Cannot continue - detailed combinations file missing")
        return None

    df = pd.read_csv(detailed_file)

    # Check required columns exist
    required_columns = [
        'Lokalitet_ID', 'Qualifying_Category', 'Qualifying_Substance',
        'Losseplads_Subcategory', 'Original_Category', 'Landfill_Override_Applied'
    ]

    print(f"\nColumn validation:")
    for col in required_columns:
        if col in df.columns:
            print(f"✓ {col} exists")
        else:
            print(f"✗ {col} MISSING")

    # Basic data validation
    print(f"\nBasic data validation:")
    print(f"Total combinations: {len(df)}")
    print(f"Unique sites: {df['Lokalitet_ID'].nunique()}")
    print(f"Overridden combinations: {df['Landfill_Override_Applied'].sum()}")
    print(f"LOSSEPLADS combinations: {(df['Qualifying_Category'] == 'LOSSEPLADS').sum()}")

    return df

def validate_logic_with_examples(df):
    """Test specific logic scenarios with real data."""
    print(f"\n2. LOGIC VALIDATION WITH REAL EXAMPLES")
    print("=" * 40)

    # Test 1: Sites that were overridden
    overridden = df[df['Landfill_Override_Applied'] == True]
    print(f"\nTest 1 - Overridden sites analysis:")
    print(f"Total overridden: {len(overridden)}")

    if len(overridden) > 0:
        # Check that all overridden sites are now LOSSEPLADS
        all_losseplads = (overridden['Qualifying_Category'] == 'LOSSEPLADS').all()
        print(f"All overridden are LOSSEPLADS: {'✓' if all_losseplads else '✗'}")

        # Check that all have subcategory info
        has_subcategory = overridden['Losseplads_Subcategory'].notna().all()
        print(f"All have subcategory info: {'✓' if has_subcategory else '✗'}")

        # Check that all have original category
        has_original = overridden['Original_Category'].notna().all()
        print(f"All have original category: {'✓' if has_original else '✗'}")

    # Test 2: Sites that were NOT overridden at landfills
    landfill_sites = df[
        (df['Lokalitetensaktivitet'].str.contains('losseplads', case=False, na=False)) |
        (df['Lokalitetensbranche'].str.contains('affald', case=False, na=False))
    ]
    not_overridden_at_landfills = landfill_sites[df['Landfill_Override_Applied'] == False]

    print(f"\nTest 2 - Sites at landfills NOT overridden:")
    print(f"Total landfill sites: {len(landfill_sites)}")
    print(f"Not overridden: {len(not_overridden_at_landfills)}")

    if len(not_overridden_at_landfills) > 0:
        categories_not_overridden = not_overridden_at_landfills['Qualifying_Category'].value_counts()
        print("Categories that stayed original:")
        for cat, count in categories_not_overridden.head().items():
            print(f"  {cat}: {count}")

    # Test 3: Threshold compliance
    print(f"\nTest 3 - Threshold compliance check:")

    # Define thresholds
    LANDFILL_THRESHOLDS = {
        'BTXER': 70,
        'KLOREREDE_OPLØSNINGSMIDLER': 100,
        'PHENOLER': 35,
        'PESTICIDER': 110,
        'UORGANISKE_FORBINDELSER': 50,
    }

    threshold_violations = 0
    for category, threshold in LANDFILL_THRESHOLDS.items():
        subcategory = f'LOSSEPLADS_{category}'
        cat_data = overridden[overridden['Losseplads_Subcategory'] == subcategory]

        if len(cat_data) > 0:
            violations = (cat_data['Final_Distance_m'] > threshold).sum()
            threshold_violations += violations
            print(f"  {subcategory}: {len(cat_data)} sites, {violations} violations")

    print(f"Total threshold violations: {'✗ ' + str(threshold_violations) if threshold_violations > 0 else '✓ 0'}")

def validate_multi_substance_logic(df):
    """Validate multi-substance site handling."""
    print(f"\n3. MULTI-SUBSTANCE LOGIC VALIDATION")
    print("=" * 40)

    # Find sites with multiple combinations
    site_combination_counts = df.groupby('Lokalitet_ID').size()
    multi_combination_sites = site_combination_counts[site_combination_counts > 1]

    print(f"Sites with multiple combinations: {len(multi_combination_sites)}")
    print(f"Max combinations per site: {site_combination_counts.max()}")

    # Analyze a specific multi-substance site
    if len(multi_combination_sites) > 0:
        example_site = multi_combination_sites.index[0]
        site_data = df[df['Lokalitet_ID'] == example_site]

        print(f"\nExample multi-substance site: {example_site}")
        print(f"Total combinations: {len(site_data)}")
        print(f"Distance: {site_data['Final_Distance_m'].iloc[0]:.0f}m")

        print("Combinations breakdown:")
        for _, row in site_data.iterrows():
            override_status = "OVERRIDDEN" if row['Landfill_Override_Applied'] else "ORIGINAL"
            print(f"  {row['Qualifying_Substance']} → {row['Qualifying_Category']} ({override_status})")

def validate_end_to_end_counts(df):
    """Validate that counts match between terminal output and files."""
    print(f"\n4. END-TO-END COUNT VALIDATION")
    print("=" * 40)

    # Terminal output said:
    # - Total combinations checked: 4602
    # - Combinations overridden to LOSSEPLADS: 680

    print(f"File contains {len(df)} total combinations")
    overridden_count = df['Landfill_Override_Applied'].sum()
    print(f"File contains {overridden_count} overridden combinations")

    # Expected from terminal output
    expected_total = 4602
    expected_overridden = 680

    print(f"\nCount verification:")
    print(f"Total combinations: {len(df)} (expected: {expected_total}) {'✓' if len(df) == expected_total else '✗'}")
    print(f"Overridden combinations: {overridden_count} (expected: {expected_overridden}) {'✓' if overridden_count == expected_overridden else '✗'}")

    # Category counts
    print(f"\nCategory distribution:")
    category_counts = df['Qualifying_Category'].value_counts()
    for cat, count in category_counts.items():
        print(f"  {cat}: {count}")

def validate_edge_cases(df):
    """Test edge cases and error conditions."""
    print(f"\n5. EDGE CASES VALIDATION")
    print("=" * 40)

    # Edge case 1: Sites that were already LOSSEPLADS before override
    original_losseplads = df[
        (df['Qualifying_Category'] == 'LOSSEPLADS') &
        (df['Landfill_Override_Applied'] == False)
    ]
    print(f"Sites originally LOSSEPLADS (not overridden): {len(original_losseplads)}")

    # Edge case 2: Sites with missing distance data
    missing_distance = df[df['Final_Distance_m'].isna()]
    print(f"Sites with missing distance: {len(missing_distance)}")

    # Edge case 3: Sites with zero distance
    zero_distance = df[df['Final_Distance_m'] == 0]
    print(f"Sites at zero distance: {len(zero_distance)}")

    # Edge case 4: Consistency check - overridden sites should have subcategory
    overridden = df[df['Landfill_Override_Applied'] == True]
    if len(overridden) > 0:
        missing_subcategory = overridden[overridden['Losseplads_Subcategory'].isna()]
        print(f"Overridden sites missing subcategory: {'✗ ' + str(len(missing_subcategory)) if len(missing_subcategory) > 0 else '✓ 0'}")

def create_summary_report(df):
    """Create final summary report."""
    print(f"\n" + "="*60)
    print("FINAL VALIDATION SUMMARY")
    print("="*60)

    total_sites = df['Lokalitet_ID'].nunique()
    total_combinations = len(df)
    overridden = df['Landfill_Override_Applied'].sum()
    losseplads_total = (df['Qualifying_Category'] == 'LOSSEPLADS').sum()

    print(f"OVERALL STATISTICS:")
    print(f"  Unique sites qualifying: {total_sites:,}")
    print(f"  Total site-substance combinations: {total_combinations:,}")
    print(f"  Combinations overridden to LOSSEPLADS: {overridden:,}")
    print(f"  Total LOSSEPLADS combinations: {losseplads_total:,}")

    print(f"\nLANDFILL OVERRIDE IMPACT:")
    if overridden > 0:
        override_pct = (overridden / total_combinations) * 100
        print(f"  {override_pct:.1f}% of combinations were overridden")

        # Show subcategory breakdown
        overridden_data = df[df['Landfill_Override_Applied'] == True]
        subcategories = overridden_data['Losseplads_Subcategory'].value_counts()
        print(f"  Subcategory breakdown:")
        for subcat, count in subcategories.items():
            print(f"    {subcat}: {count}")

def main():
    """Run comprehensive validation."""
    print("COMPREHENSIVE STEP 5 LANDFILL OVERRIDE VALIDATION")
    print("="*60)

    # Load and validate data
    df = validate_data_integrity()
    if df is None:
        return

    # Run all validation tests
    validate_logic_with_examples(df)
    validate_multi_substance_logic(df)
    validate_end_to_end_counts(df)
    validate_edge_cases(df)
    create_summary_report(df)

    print(f"\n" + "="*60)
    print("VALIDATION COMPLETE")
    print("="*60)

if __name__ == "__main__":
    main()