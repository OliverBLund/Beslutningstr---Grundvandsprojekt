"""
Workflow Validation Script: Step 1-6 Verification
==================================================

This script provides a comprehensive "seal of approval" for the groundwater
contamination assessment workflow by verifying:

1. GVFK Integrity: Counts decrease monotonically through steps (funnel effect)
2. Site Integrity: No site appears in Step N+1 if not in Step N  
3. Combination Consistency: Site-GVFK pairs are correctly carried forward
4. Compound Logic: Thresholds are correctly applied per category
5. Filtering Cascade: Each filter step correctly reduces the dataset

Run after main_workflow.py completes:
    python tools/validation_exercise.py

"""

import sys
from pathlib import Path
import pandas as pd
import geopandas as gpd

# Add parent directory to path
REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from config import (
    get_output_path,
    get_visualization_path,
    RESULTS_DIR,
    COLUMN_MAPPINGS,
)


class ValidationResult:
    """Container for validation check results."""
    def __init__(self, name, passed, details="", critical=True):
        self.name = name
        self.passed = passed
        self.details = details
        self.critical = critical  # If False, it's a warning not an error
    
    def __str__(self):
        status = "âœ“ PASS" if self.passed else ("âœ— FAIL" if self.critical else "âš  WARN")
        return f"{status}: {self.name}\n       {self.details}"


def load_step_data():
    """Load all step outputs into a dictionary."""
    print("\n" + "=" * 80)
    print("LOADING WORKFLOW OUTPUTS")
    print("=" * 80)
    
    data = {}
    
    # Step 1: All GVFKs (loaded from original source - not a workflow output)
    from config import GRUNDVAND_PATH, GRUNDVAND_LAYER_NAME
    if GRUNDVAND_PATH.exists():
        try:
            data['step1_gvfk'] = gpd.read_file(GRUNDVAND_PATH, layer=GRUNDVAND_LAYER_NAME)
            print(f"âœ“ Step 1 GVFKs (source): {len(data['step1_gvfk'])} polygon rows")
        except Exception as e:
            print(f"âœ— Step 1 load error: {e}")
    else:
        print(f"âœ— Step 1 source not found: {GRUNDVAND_PATH}")
    
    # Step 2: River contact GVFKs
    step2_path = get_output_path("step2_river_gvfk")
    if step2_path.exists():
        data['step2_river'] = gpd.read_file(step2_path)
        print(f"âœ“ Step 2 River Contact: {len(data['step2_river'])} polygon rows")
    else:
        print(f"âœ— Step 2 not found: {step2_path}")
    
    # Step 3: V1/V2 sites and GVFKs with sites
    step3_sites_path = get_output_path("step3_v1v2_sites")
    if step3_sites_path.exists():
        data['step3_sites'] = gpd.read_file(step3_sites_path)
        print(f"âœ“ Step 3 Sites: {len(data['step3_sites'])} sites")
    else:
        print(f"âœ— Step 3 sites not found: {step3_sites_path}")
    
    step3_gvfk_path = get_output_path("step3_gvfk_polygons")
    if step3_gvfk_path.exists():
        data['step3_gvfk'] = gpd.read_file(step3_gvfk_path)
        print(f"âœ“ Step 3 GVFKs: {len(data['step3_gvfk'])} polygon rows")
    else:
        print(f"âœ— Step 3 GVFKs not found: {step3_gvfk_path}")
    
    # Step 3b: Infiltration-filtered sites
    step3b_path = get_output_path("step3b_filtered_sites")
    if step3b_path.exists():
        data['step3b_filtered'] = gpd.read_file(step3b_path)
        print(f"âœ“ Step 3b Filtered Sites: {len(data['step3b_filtered'])} site-GVFK combinations")
    else:
        print(f"âœ— Step 3b not found: {step3b_path}")
    
    # Step 4: Distance calculations
    step4_path = get_output_path("step4_final_distances_for_risk_assessment")
    if step4_path.exists():
        data['step4_distances'] = pd.read_csv(step4_path)
        print(f"âœ“ Step 4 Distances: {len(data['step4_distances'])} site-GVFK combinations")
    else:
        print(f"âœ— Step 4 not found: {step4_path}")
    
    # Step 5a: High-risk sites (general)
    step5a_path = get_output_path("step5_high_risk_sites")
    if step5a_path.exists():
        data['step5a_general'] = pd.read_csv(step5a_path)
        print(f"âœ“ Step 5a General: {len(data['step5a_general'])} rows")
    else:
        print(f"âœ— Step 5a not found: {step5a_path}")
    
    # Step 5b: Compound-specific (PRE-filter)
    step5b_path = get_output_path("step5b_compound_combinations")
    if step5b_path.exists():
        data['step5b_compound'] = pd.read_csv(step5b_path)
        print(f"âœ“ Step 5b Compound: {len(data['step5b_compound'])} site-GVFK-compound combinations")
    else:
        print(f"âœ— Step 5b not found: {step5b_path}")
    
    # Note: Step 5c is DEPRECATED - infiltration filtering now happens at Step 3b
    # Keeping for backward compatibility with old output files
    step5c_path = get_output_path("step5c_filtered_combinations")
    if step5c_path.exists():
        data['step5c_filtered'] = pd.read_csv(step5c_path)
        print(f"âœ“ Step 5c Filtered (LEGACY): {len(data['step5c_filtered'])} rows")
    else:
        print(f"  Step 5c not found (expected - now deprecated)")
    
    # Step 6: MKK exceedances
    step6_path = get_output_path("step6_site_mkk_exceedances")
    if step6_path.exists():
        data['step6_mkk'] = pd.read_csv(step6_path)
        print(f"âœ“ Step 6 MKK: {len(data['step6_mkk'])} rows with MKK exceedances")
    else:
        print(f"âœ— Step 6 not found: {step6_path}")
    
    return data


def validate_gvfk_funnel(data):
    """
    Verify that GVFK counts decrease monotonically through the workflow.
    Each step should have fewer or equal GVFKs than the previous step.
    """
    print("\n" + "=" * 80)
    print("CHECK 1: GVFK FUNNEL (counts should decrease through steps)")
    print("=" * 80)
    
    results = []
    gvfk_col = COLUMN_MAPPINGS['grundvand']['gvfk_id']
    
    # Count unique GVFKs at each step
    counts = {}
    
    if 'step1_gvfk' in data:
        counts['Step 1: All GVFKs'] = data['step1_gvfk'][gvfk_col].nunique()
    
    if 'step2_river' in data:
        counts['Step 2: River Contact'] = data['step2_river'][gvfk_col].nunique()
    
    if 'step3b_filtered' in data:
        # Step 3b uses different column names (Lokalitet_, Navn)
        data_3b = data['step3b_filtered']
        if 'Navn' in data_3b.columns:
            counts['Step 3b: Infiltration Filtered'] = data_3b['Navn'].nunique()
        elif 'GVFK' in data_3b.columns:
            counts['Step 3b: Infiltration Filtered'] = data_3b['GVFK'].nunique()
    
    if 'step4_distances' in data and 'GVFK' in data['step4_distances'].columns:
        counts['Step 4: With Distances'] = data['step4_distances']['GVFK'].nunique()
    
    if 'step5a_general' in data and 'GVFK' in data['step5a_general'].columns:
        counts['Step 5a: General Risk'] = data['step5a_general']['GVFK'].nunique()
    
    if 'step5b_compound' in data and 'GVFK' in data['step5b_compound'].columns:
        counts['Step 5b: Compound-Specific'] = data['step5b_compound']['GVFK'].nunique()
    
    # Skip step5c in funnel (deprecated)
    
    if 'step6_mkk' in data and 'GVFK' in data['step6_mkk'].columns:
        counts['Step 6: MKK Exceedances'] = data['step6_mkk']['GVFK'].nunique()
    
    # Print counts
    print("\nGVFK counts per step:")
    prev_count = None
    prev_step = None
    all_decreasing = True
    
    for step, count in counts.items():
        arrow = ""
        if prev_count is not None:
            if count <= prev_count:
                arrow = f" (â†“ {prev_count - count})"
            else:
                arrow = f" (â†‘ +{count - prev_count} âš  UNEXPECTED INCREASE!)"
                all_decreasing = False
        print(f"  {step}: {count:,}{arrow}")
        prev_count = count
        prev_step = step
    
    # Overall result
    result = ValidationResult(
        "GVFK Funnel",
        all_decreasing,
        f"GVFKs correctly decrease from {list(counts.values())[0]:,} â†’ {list(counts.values())[-1]:,}" 
        if all_decreasing else "GVFK counts increased unexpectedly!"
    )
    results.append(result)
    print(f"\n{result}")
    
    return results


def validate_site_consistency(data):
    """
    Verify that sites don't appear in Step N+1 if not in Step N.
    A site can only progress forward if it was present in the previous step.
    """
    print("\n" + "=" * 80)
    print("CHECK 2: SITE CONSISTENCY (no orphan sites)")
    print("=" * 80)
    
    results = []
    
    # Get site IDs at each step
    site_sets = {}
    
    if 'step4_distances' in data and 'Lokalitet_ID' in data['step4_distances'].columns:
        site_sets['Step 4'] = set(data['step4_distances']['Lokalitet_ID'].unique())
    
    if 'step5a_general' in data and 'Lokalitet_ID' in data['step5a_general'].columns:
        site_sets['Step 5a'] = set(data['step5a_general']['Lokalitet_ID'].unique())
    
    if 'step5b_compound' in data and 'Lokalitet_ID' in data['step5b_compound'].columns:
        site_sets['Step 5b'] = set(data['step5b_compound']['Lokalitet_ID'].unique())
    
    if 'step5c_filtered' in data and 'Lokalitet_ID' in data['step5c_filtered'].columns:
        site_sets['Step 5c'] = set(data['step5c_filtered']['Lokalitet_ID'].unique())
    
    if 'step6_mkk' in data and 'Lokalitet_ID' in data['step6_mkk'].columns:
        site_sets['Step 6'] = set(data['step6_mkk']['Lokalitet_ID'].unique())
    
    # Check each step's sites are subset of previous step
    print("\nSite counts per step:")
    steps = list(site_sets.keys())
    all_consistent = True
    
    for i, step in enumerate(steps):
        count = len(site_sets[step])
        orphans = 0
        
        if i > 0:
            prev_step = steps[i-1]
            orphans = len(site_sets[step] - site_sets[prev_step])
            if orphans > 0:
                all_consistent = False
        
        status = "âœ“" if orphans == 0 else "âœ—"
        orphan_note = f" (âš  {orphans} orphan sites!)" if orphans > 0 else ""
        print(f"  {status} {step}: {count:,} sites{orphan_note}")
    
    result = ValidationResult(
        "Site Consistency",
        all_consistent,
        "All sites properly inherited from previous steps" if all_consistent 
        else "Some sites appear without being in previous step!"
    )
    results.append(result)
    print(f"\n{result}")
    
    return results


def validate_combination_logic(data):
    """
    Verify that site-GVFK combinations are handled correctly.
    Step 4 creates Site-GVFK pairs, Step 5b adds compounds.
    """
    print("\n" + "=" * 80)
    print("CHECK 3: COMBINATION LOGIC (Site-GVFK and Site-GVFK-Compound)")
    print("=" * 80)
    
    results = []
    
    # Check Step 4 â†’ Step 5a: Site-GVFK pairs should be subset
    if 'step4_distances' in data and 'step5a_general' in data:
        step4_pairs = set(zip(
            data['step4_distances']['Lokalitet_ID'],
            data['step4_distances']['GVFK']
        ))
        step5a_pairs = set(zip(
            data['step5a_general']['Lokalitet_ID'],
            data['step5a_general']['GVFK']
        ))
        
        orphan_pairs = step5a_pairs - step4_pairs
        is_subset = len(orphan_pairs) == 0
        
        print(f"\nStep 4 â†’ Step 5a (Site-GVFK pairs):")
        print(f"  Step 4 pairs: {len(step4_pairs):,}")
        print(f"  Step 5a pairs: {len(step5a_pairs):,}")
        print(f"  Orphan pairs: {len(orphan_pairs)}")
        
        result = ValidationResult(
            "Step 4â†’5a Pair Consistency",
            is_subset,
            f"All {len(step5a_pairs):,} Step 5a pairs exist in Step 4" if is_subset
            else f"{len(orphan_pairs)} pairs in Step 5a not found in Step 4!"
        )
        results.append(result)
        print(f"\n{result}")
    
    # Check Step 5b compound combinations
    if 'step5b_compound' in data:
        df = data['step5b_compound']
        
        # Count unique combinations at different levels
        site_count = df['Lokalitet_ID'].nunique()
        pair_count = df.groupby(['Lokalitet_ID', 'GVFK']).ngroups
        
        if 'Qualifying_Category' in df.columns:
            triplet_count = df.groupby(['Lokalitet_ID', 'GVFK', 'Qualifying_Category']).ngroups
            row_count = len(df)
            
            print(f"\nStep 5b Combination Breakdown:")
            print(f"  Unique sites: {site_count:,}")
            print(f"  Site-GVFK pairs: {pair_count:,}")
            print(f"  Site-GVFK-Category triplets: {triplet_count:,}")
            print(f"  Total rows (with substances): {row_count:,}")
            
            # Verify expansion makes sense
            expansion_ok = site_count <= pair_count <= triplet_count <= row_count
            
            result = ValidationResult(
                "Step 5b Combination Expansion",
                expansion_ok,
                f"Correct hierarchy: sites({site_count}) â‰¤ pairs({pair_count}) â‰¤ triplets({triplet_count}) â‰¤ rows({row_count})"
                if expansion_ok else "Combination hierarchy violated!"
            )
            results.append(result)
            print(f"\n{result}")
    
    return results


def validate_threshold_application(data):
    """
    Verify that compound-specific thresholds are correctly applied.
    """
    print("\n" + "=" * 80)
    print("CHECK 4: THRESHOLD APPLICATION (compound-specific filtering)")
    print("=" * 80)
    
    results = []
    
    if 'step5b_compound' in data:
        df = data['step5b_compound']
        
        if 'Category_Threshold_m' in df.columns and 'Distance_to_River_m' in df.columns:
            # All distances should be <= threshold for their category
            violators = df[df['Distance_to_River_m'] > df['Category_Threshold_m']]
            threshold_ok = len(violators) == 0
            
            print(f"\nThreshold compliance in Step 5b:")
            print(f"  Total combinations: {len(df):,}")
            print(f"  Violations (distance > threshold): {len(violators)}")
            
            if len(violators) > 0:
                print("\n  Sample violations:")
                for _, row in violators.head(5).iterrows():
                    print(f"    {row['Lokalitet_ID']} | {row['Qualifying_Category']} | "
                          f"Distance: {row['Distance_to_River_m']:.0f}m > Threshold: {row['Category_Threshold_m']:.0f}m")
            
            result = ValidationResult(
                "Threshold Compliance",
                threshold_ok,
                f"All {len(df):,} combinations satisfy distance â‰¤ threshold" if threshold_ok
                else f"{len(violators)} combinations violate their threshold!"
            )
            results.append(result)
            print(f"\n{result}")
        else:
            print("  âš  Missing threshold or distance columns")
    
    return results


def validate_step3b_filtering(data):
    """
    Verify that Step 3b (infiltration filter) correctly reduces the dataset.
    This is where infiltration filtering now happens (moved from Step 5c).
    """
    print("\n" + "=" * 80)
    print("CHECK 5: INFILTRATION FILTER (Step 3 â†’ Step 3b)")
    print("=" * 80)
    
    results = []
    
    if 'step3_sites' in data and 'step3b_filtered' in data:
        pre_count = len(data['step3_sites'])
        post_count = len(data['step3b_filtered'])
        removed = pre_count - post_count
        
        print(f"\nInfiltration filtering at Step 3b:")
        print(f"  Step 3 (before): {pre_count:,} site-GVFK combinations")
        print(f"  Step 3b (after): {post_count:,} site-GVFK combinations")
        print(f"  Removed by filter: {removed:,} ({removed/pre_count*100:.1f}%)")
        
        # Filtering should not add rows
        filter_ok = post_count <= pre_count
        
        # Step 3b should be subset of Step 3
        # Get site IDs (column names differ between steps)
        site_col_3 = 'Lokalitet_' if 'Lokalitet_' in data['step3_sites'].columns else 'Lokalitet_ID'
        gvfk_col_3 = 'Navn' if 'Navn' in data['step3_sites'].columns else 'GVFK'
        site_col_3b = 'Lokalitet_' if 'Lokalitet_' in data['step3b_filtered'].columns else 'Lokalitet_ID'
        gvfk_col_3b = 'Navn' if 'Navn' in data['step3b_filtered'].columns else 'GVFK'
        
        pre_pairs = set(zip(
            data['step3_sites'][site_col_3],
            data['step3_sites'][gvfk_col_3]
        ))
        post_pairs = set(zip(
            data['step3b_filtered'][site_col_3b],
            data['step3b_filtered'][gvfk_col_3b]
        ))
        orphans = post_pairs - pre_pairs
        subset_ok = len(orphans) == 0
        filter_ok = filter_ok and subset_ok
        
        # Check unique sites and GVFKs
        pre_sites = data['step3_sites'][site_col_3].nunique()
        post_sites = data['step3b_filtered'][site_col_3b].nunique()
        pre_gvfks = data['step3_sites'][gvfk_col_3].nunique()
        post_gvfks = data['step3b_filtered'][gvfk_col_3b].nunique()
        
        print(f"\n  Site-level impact:")
        print(f"    Sites: {pre_sites:,} â†’ {post_sites:,} (-{pre_sites - post_sites:,})")
        print(f"    GVFKs: {pre_gvfks:,} â†’ {post_gvfks:,} (-{pre_gvfks - post_gvfks:,})")
        
        if len(orphans) > 0:
            print(f"\n  âš  {len(orphans)} orphan pairs found in Step 3b!")
        
        result = ValidationResult(
            "Step 3b Infiltration Filter",
            filter_ok,
            f"Correctly filtered from {pre_count:,} to {post_count:,} combinations ({pre_sites:,} to {post_sites:,} sites)" if filter_ok
            else "Filter added rows or created orphan pairs!"
        )
        results.append(result)
        print(f"\n{result}")
    else:
        print("  âš  Step 3 or Step 3b data not available for validation")
    
    return results


def validate_step6_mkk(data):
    """
    Verify Step 6 MKK exceedances are properly derived from Step 5b.
    (Note: Previously checked Step 5c, but infiltration now happens at Step 3b)
    """
    print("\n" + "=" * 80)
    print("CHECK 6: MKK EXCEEDANCES (Step 6 derives from Step 5b)")
    print("=" * 80)
    
    results = []
    
    # Use Step 5b as the reference (Step 5c is deprecated)
    reference_key = 'step5b_compound'
    reference_name = 'Step 5b'
    
    if reference_key in data and 'step6_mkk' in data:
        ref_sites = set(data[reference_key]['Lokalitet_ID'].unique())
        step6_sites = set(data['step6_mkk']['Lokalitet_ID'].unique())
        
        orphan_sites = step6_sites - ref_sites
        derivation_ok = len(orphan_sites) == 0
        
        print(f"\nStep 6 derivation from {reference_name}:")
        print(f"  {reference_name} sites: {len(ref_sites):,}")
        print(f"  Step 6 sites: {len(step6_sites):,}")
        print(f"  Orphan sites (in 6 but not {reference_name}): {len(orphan_sites)}")
        
        if len(orphan_sites) > 0:
            print(f"\n  Sample orphan sites: {list(orphan_sites)[:5]}")
        
        if 'Exceedance_Ratio' in data['step6_mkk'].columns:
            # Check that all rows have exceedance ratio >= 1 (that's the definition of MKK exceedance file)
            has_ratio = data['step6_mkk']['Exceedance_Ratio'].notna()
            if has_ratio.any():
                all_exceed = (data['step6_mkk'].loc[has_ratio, 'Exceedance_Ratio'] >= 1).all()
                print(f"  All have Exceedance_Ratio â‰¥ 1: {all_exceed}")
                derivation_ok = derivation_ok and all_exceed
        
        result = ValidationResult(
            "MKK Derivation",
            derivation_ok,
            f"All {len(step6_sites):,} Step 6 sites properly derived from {reference_name}" if derivation_ok
            else f"Step 6 contains sites not in {reference_name} or invalid exceedances!"
        )
        results.append(result)
        print(f"\n{result}")
    else:
        print(f"  âš  {reference_name} or Step 6 data not available")
    
    return results


def generate_summary(all_results):
    """Generate final validation summary."""
    print("\n" + "=" * 80)
    print("VALIDATION SUMMARY")
    print("=" * 80)
    
    passed = sum(1 for r in all_results if r.passed)
    failed = sum(1 for r in all_results if not r.passed and r.critical)
    warnings = sum(1 for r in all_results if not r.passed and not r.critical)
    
    print(f"\nTotal checks: {len(all_results)}")
    print(f"  âœ“ Passed: {passed}")
    print(f"  âœ— Failed: {failed}")
    print(f"  âš  Warnings: {warnings}")
    
    if failed == 0:
        print("\n" + "=" * 80)
        print("ðŸŽ‰ ALL CRITICAL CHECKS PASSED - WORKFLOW VALIDATED!")
        print("=" * 80)
    else:
        print("\n" + "=" * 80)
        print("âŒ VALIDATION FAILED - REVIEW ISSUES ABOVE")
        print("=" * 80)
    
    # Save summary to file
    summary_path = RESULTS_DIR / "workflow_summary" / "validation_report.txt"
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(summary_path, 'w', encoding='utf-8') as f:
        f.write("WORKFLOW VALIDATION REPORT\n")
        f.write("=" * 50 + "\n\n")
        f.write(f"Total checks: {len(all_results)}\n")
        f.write(f"Passed: {passed}\n")
        f.write(f"Failed: {failed}\n")
        f.write(f"Warnings: {warnings}\n\n")
        
        f.write("DETAILED RESULTS:\n")
        f.write("-" * 50 + "\n")
        for r in all_results:
            f.write(f"\n{r}\n")
    
    print(f"\nReport saved to: {summary_path}")
    
    return failed == 0


def main():
    """Run all validation checks."""
    print("\n" + "=" * 80)
    print("WORKFLOW VALIDATION: STEP 1-6 VERIFICATION")
    print("=" * 80)
    print("This script verifies the entire groundwater contamination workflow")
    print("to ensure data integrity and correct filtering at each step.")
    
    # Load all data
    data = load_step_data()
    
    if not data:
        print("\nâŒ No workflow outputs found. Run main_workflow.py first!")
        return False
    
    # Run all validation checks
    all_results = []
    
    all_results.extend(validate_gvfk_funnel(data))
    all_results.extend(validate_site_consistency(data))
    all_results.extend(validate_combination_logic(data))
    all_results.extend(validate_threshold_application(data))
    all_results.extend(validate_step3b_filtering(data))
    all_results.extend(validate_step6_mkk(data))
    
    # Generate summary
    success = generate_summary(all_results)
    
    return success


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)

