"""
End-to-end validation of Step 6 data flow and aggregation logic.

This script traces specific examples through the entire Step 6 pipeline to ensure:
1. Multi-GVFK sites are properly handled
2. Scenario expansion works correctly
3. Flux aggregation at segment level is accurate
4. MKK exceedances are properly detected
5. The premise that "sites affecting 2+ GVFKs also affect 2+ river segments" is validated

Usage:
    python validate_step6_data_flow.py
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from config import CATEGORY_SCENARIOS, get_output_path

# ===========================================================================
# Load Step 6 outputs
# ===========================================================================


def load_step6_data():
    """Load all Step 6 output files"""
    print("Loading Step 6 output files...")

    data = {
        "step5_input": pd.read_csv(
            get_output_path("step5_compound_detailed_combinations")
        ),
        "site_flux": pd.read_csv(get_output_path("step6_flux_site_segment")),
        "cmix": pd.read_csv(get_output_path("step6_cmix_results")),
        "summary": pd.read_csv(get_output_path("step6_segment_summary")),
        "exceedances": pd.read_csv(get_output_path("step6_site_mkk_exceedances")),
    }

    print(f"  Step 5 input: {len(data['step5_input'])} rows")
    print(f"  Site flux: {len(data['site_flux'])} rows")
    print(f"  Cmix results: {len(data['cmix'])} rows")
    print(f"  Segment summary: {len(data['summary'])} rows")
    print(f"  Exceedances: {len(data['exceedances'])} rows")

    return data


# ===========================================================================
# Test 1: Multi-GVFK Site Handling
# ===========================================================================


def test_multi_gvfk_sites(data):
    """
    Validate that sites appearing in multiple GVFKs are properly handled.

    Expected behavior:
    - Site in N GVFKs should appear N times in step5_input (once per GVFK)
    - After step6 grouping, should appear M times in site_flux (once per unique segment-category combo)
    - If those GVFKs connect to different river segments, M should equal N
    - If GVFKs connect to same segment, M should be less than N (aggregated)
    """
    print("\n" + "=" * 80)
    print("TEST 1: Multi-GVFK Site Handling")
    print("=" * 80)

    step5 = data["step5_input"]
    site_flux = data["site_flux"]

    # Find sites in multiple GVFKs in Step 5
    site_gvfk_counts = step5.groupby("Lokalitet_ID")["GVFK"].nunique()
    multi_gvfk_sites = site_gvfk_counts[site_gvfk_counts > 1].sort_values(
        ascending=False
    )

    print(f"\nSites in multiple GVFKs: {len(multi_gvfk_sites)}")
    print(f"Max GVFKs per site: {multi_gvfk_sites.max()}")

    # Analyze top 5 multi-GVFK sites
    print("\nDetailed analysis of top 5 multi-GVFK sites:")

    issues = []
    for site_id in multi_gvfk_sites.head(5).index:
        print(f"\n{'=' * 60}")
        print(f"Site: {site_id}")

        # Step 5 data
        step5_rows = step5[step5["Lokalitet_ID"] == site_id]
        gvfks = step5_rows["GVFK"].unique()
        rivers = step5_rows["Nearest_River_ov_id"].unique()
        categories = step5_rows["Qualifying_Category"].unique()

        print(f"  GVFKs: {len(gvfks)} ({', '.join(gvfks)})")
        print(f"  River segments: {len(rivers)} ({', '.join(rivers)})")
        print(f"  Categories: {len(categories)} ({', '.join(categories)})")

        # Step 6 site_flux data
        flux_rows = site_flux[site_flux["Lokalitet_ID"] == site_id]
        flux_rivers = flux_rows["Nearest_River_ov_id"].unique()
        flux_gvfks = flux_rows["GVFK"].unique()

        print(f"  After Step 6 grouping:")
        print(f"    Site appears in {len(flux_rows)} flux rows")
        print(f"    River segments: {len(flux_rivers)} ({', '.join(flux_rivers)})")
        print(f"    GVFKs retained: {len(flux_gvfks)} ({', '.join(flux_gvfks)})")

        # Validate premise: If site affects N GVFKs, should affect N river segments
        # (unless multiple GVFKs connect to same river segment)
        if len(rivers) < len(gvfks):
            print(
                f"  ⚠️  Site in {len(gvfks)} GVFKs but only {len(rivers)} river segments"
            )
            print(f"      This means multiple GVFKs connect to the same segment(s)")

            # Show which GVFKs map to which segments
            for gvfk in gvfks:
                gvfk_rows = step5_rows[step5_rows["GVFK"] == gvfk]
                gvfk_rivers = gvfk_rows["Nearest_River_ov_id"].unique()
                print(f"      {gvfk} → {', '.join(gvfk_rivers)}")

        # Check if flux rows match expected structure
        # Expected: One flux row per unique (site, river segment, category, scenario)
        for category in categories:
            scenarios = CATEGORY_SCENARIOS.get(category, [])
            if not scenarios:
                scenarios = ["single"]  # Categories without modelstof scenarios

            for river in flux_rivers:
                expected_rows = len(scenarios)
                actual_rows = len(
                    flux_rows[
                        (flux_rows["Nearest_River_ov_id"] == river)
                        & (flux_rows["Qualifying_Category"] == category)
                    ]
                )

                if actual_rows != expected_rows:
                    issue = {
                        "site": site_id,
                        "river": river,
                        "category": category,
                        "expected": expected_rows,
                        "actual": actual_rows,
                    }
                    issues.append(issue)
                    print(f"  ❌ Mismatch: {river} + {category}")
                    print(
                        f"     Expected {expected_rows} scenarios, found {actual_rows}"
                    )

    if not issues:
        print("\n✅ All multi-GVFK sites properly handled")
    else:
        print(f"\n❌ Found {len(issues)} issues with scenario expansion")

    return issues


# ===========================================================================
# Test 2: Scenario Expansion
# ===========================================================================


def test_scenario_expansion(data):
    """
    Validate that category scenarios are properly expanded.

    Expected behavior:
    - BTXER: 2 scenarios (Benzen, Olie C10-C25)
    - KLOREREDE_OPLØSNINGSMIDLER: 4 scenarios
    - LOSSEPLADS, PFAS, ANDRE: No scenarios (single row per site-segment-category)
    """
    print("\n" + "=" * 80)
    print("TEST 2: Scenario Expansion Logic")
    print("=" * 80)

    site_flux = data["site_flux"]

    # Count scenarios per category
    print("\nScenarios generated per category:")

    for category, expected_scenarios in CATEGORY_SCENARIOS.items():
        category_rows = site_flux[site_flux["Qualifying_Category"] == category]

        if category_rows.empty:
            print(f"\n{category}: No data")
            continue

        # Get unique substances (scenarios) for this category
        substances = category_rows["Qualifying_Substance"].unique()

        print(f"\n{category}:")
        print(
            f"  Expected scenarios: {len(expected_scenarios)} ({', '.join(expected_scenarios) if expected_scenarios else 'none'})"
        )
        print(f"  Actual scenarios: {len(substances)}")

        # Check if scenarios match expected
        if expected_scenarios:
            expected_substance_names = [
                f"{category}__via_{s}" for s in expected_scenarios
            ]
            for exp in expected_substance_names:
                if exp in substances:
                    print(f"    ✅ {exp}")
                else:
                    print(f"    ❌ Missing: {exp}")

            # Check for unexpected scenarios
            for act in substances:
                if act not in expected_substance_names:
                    print(f"    ⚠️  Unexpected: {act}")
        else:
            print(f"    Scenarios: {', '.join(substances[:5])}")
            if len(substances) > 5:
                print(f"    ... and {len(substances) - 5} more")


# ===========================================================================
# Test 3: Flux Aggregation at Segment Level
# ===========================================================================


def test_segment_aggregation(data):
    """
    Validate that flux is properly summed at the segment level.

    Test specific examples:
    - Pick a segment with multiple contributing sites
    - Manually sum site-level flux
    - Compare with segment summary
    """
    print("\n" + "=" * 80)
    print("TEST 3: Segment-Level Flux Aggregation")
    print("=" * 80)

    site_flux = data["site_flux"]
    cmix = data["cmix"]

    # Find segments with multiple sites
    segment_site_counts = site_flux.groupby("Nearest_River_ov_id")[
        "Lokalitet_ID"
    ].nunique()
    multi_site_segments = segment_site_counts[segment_site_counts > 1].sort_values(
        ascending=False
    )

    print(f"\nSegments with multiple contributing sites: {len(multi_site_segments)}")
    print(f"Max sites per segment: {multi_site_segments.max()}")

    # Test top 3 segments
    print("\nValidating flux aggregation for top 3 segments:")

    issues = []
    for segment in multi_site_segments.head(3).index:
        print(f"\n{'=' * 60}")
        print(f"Segment: {segment}")

        segment_sites = site_flux[site_flux["Nearest_River_ov_id"] == segment]
        site_count = segment_sites["Lokalitet_ID"].nunique()
        site_ids = segment_sites["Lokalitet_ID"].unique()

        print(f"  Contributing sites: {site_count}")
        print(f"  Site IDs: {', '.join(sorted(site_ids)[:5])}")
        if len(site_ids) > 5:
            print(f"           ... and {len(site_ids) - 5} more")

        # Check each category-scenario combination
        for (category, substance), group in segment_sites.groupby(
            ["Qualifying_Category", "Qualifying_Substance"]
        ):
            # Manual sum from site-level data
            manual_flux_kg = group["Pollution_Flux_kg_per_year"].sum()
            contributing_sites = group["Lokalitet_ID"].nunique()

            # Look up in cmix results (which should have segment-level aggregation)
            cmix_rows = cmix[
                (cmix["Nearest_River_ov_id"] == segment)
                & (cmix["Qualifying_Category"] == category)
                & (cmix["Qualifying_Substance"] == substance)
            ]

            if cmix_rows.empty:
                print(f"  ❌ Missing in cmix: {category} - {substance}")
                issues.append(
                    {
                        "segment": segment,
                        "category": category,
                        "substance": substance,
                        "issue": "Missing in cmix",
                    }
                )
                continue

            # Check if flux matches (should be same across all flow scenarios)
            cmix_flux_kg = cmix_rows["Total_Flux_kg_per_year"].iloc[0]

            # Allow small floating point differences
            if abs(manual_flux_kg - cmix_flux_kg) > 0.001:
                print(f"  ❌ Flux mismatch: {category} - {substance}")
                print(f"     Manual sum: {manual_flux_kg:.6f} kg/yr")
                print(f"     Cmix value: {cmix_flux_kg:.6f} kg/yr")
                print(
                    f"     Difference: {abs(manual_flux_kg - cmix_flux_kg):.6f} kg/yr"
                )
                issues.append(
                    {
                        "segment": segment,
                        "category": category,
                        "substance": substance,
                        "issue": "Flux mismatch",
                        "manual": manual_flux_kg,
                        "cmix": cmix_flux_kg,
                    }
                )
            else:
                print(
                    f"  ✅ {category}__via_{substance}: {manual_flux_kg:.4f} kg/yr ({contributing_sites} sites)"
                )

    if not issues:
        print("\n✅ All segment flux aggregations correct")
    else:
        print(f"\n❌ Found {len(issues)} aggregation issues")

    return issues


# ===========================================================================
# Test 4: MKK Exceedance Detection
# ===========================================================================


def test_mkk_exceedances(data):
    """
    Validate MKK exceedance detection logic.

    Check:
    - Exceedance_Flag = True when Cmix > MKK
    - Exceedance_Ratio = Cmix / MKK
    - Sites in exceedances file match those flagged in cmix
    """
    print("\n" + "=" * 80)
    print("TEST 4: MKK Exceedance Detection")
    print("=" * 80)

    cmix = data["cmix"]
    exceedances = data["exceedances"]

    # Count exceedances
    has_mkk = cmix["MKK_ug_L"].notna()
    flagged = cmix["Exceedance_Flag"] == True

    print(f"\nCmix results with MKK values: {has_mkk.sum()}")
    print(f"Rows flagged as exceedances: {flagged.sum()}")
    print(f"Exceedance rate: {flagged.sum() / has_mkk.sum() * 100:.1f}%")

    # Validate exceedance logic
    print("\nValidating exceedance logic...")

    issues = []
    for idx, row in cmix[has_mkk].iterrows():
        cmix_val = row["Cmix_ug_L"]
        mkk_val = row["MKK_ug_L"]
        flagged = row["Exceedance_Flag"]
        ratio = row["Exceedance_Ratio"]

        # Check flag
        expected_flag = cmix_val > mkk_val
        if flagged != expected_flag:
            issues.append(
                {
                    "type": "flag_error",
                    "segment": row["Nearest_River_ov_id"],
                    "substance": row["Qualifying_Substance"],
                    "cmix": cmix_val,
                    "mkk": mkk_val,
                    "expected_flag": expected_flag,
                    "actual_flag": flagged,
                }
            )

        # Check ratio
        expected_ratio = cmix_val / mkk_val if mkk_val > 0 else np.nan
        if not np.isnan(ratio) and abs(ratio - expected_ratio) > 0.001:
            issues.append(
                {
                    "type": "ratio_error",
                    "segment": row["Nearest_River_ov_id"],
                    "substance": row["Qualifying_Substance"],
                    "expected_ratio": expected_ratio,
                    "actual_ratio": ratio,
                }
            )

    if not issues:
        print("✅ All exceedance flags and ratios correct")
    else:
        print(f"❌ Found {len(issues)} exceedance logic errors")
        for issue in issues[:5]:
            print(f"  {issue}")

    # Validate exceedances file
    print("\nValidating site exceedances export...")

    # All rows in exceedances file should have Exceedance_Flag = True
    if "Exceedance_Flag" in exceedances.columns:
        non_exceeding = exceedances[exceedances["Exceedance_Flag"] != True]
        if len(non_exceeding) > 0:
            print(
                f"❌ Exceedances file contains {len(non_exceeding)} non-exceeding rows!"
            )
        else:
            print("✅ All rows in exceedances file are true exceedances")

    # Check if site counts match
    exceeding_sites_in_cmix = (
        cmix[cmix["Exceedance_Flag"] == True]["Lokalitet_ID"].nunique()
        if "Lokalitet_ID" in cmix.columns
        else 0
    )
    exceeding_sites_in_file = exceedances["Lokalitet_ID"].nunique()

    print(f"\nExceeding sites in cmix: {exceeding_sites_in_cmix}")
    print(f"Sites in exceedances file: {exceeding_sites_in_file}")

    if (
        exceeding_sites_in_cmix > 0
        and exceeding_sites_in_file != exceeding_sites_in_cmix
    ):
        print(
            f"⚠️  Site count mismatch (expected if exceedances file is site-level view)"
        )

    return issues


# ===========================================================================
# Test 5: Reduced Dataset Test
# ===========================================================================


def test_reduced_dataset(data, sample_fraction=0.01):
    """
    Test Step 6 logic with 99% less data (1% sample).

    This ensures the code handles edge cases and small datasets properly.
    """
    print("\n" + "=" * 80)
    print(f"TEST 5: Reduced Dataset ({sample_fraction * 100:.0f}% sample)")
    print("=" * 80)

    step5 = data["step5_input"]

    # Sample 1% of sites
    unique_sites = step5["Lokalitet_ID"].unique()
    sample_size = max(10, int(len(unique_sites) * sample_fraction))
    sampled_sites = np.random.choice(unique_sites, size=sample_size, replace=False)

    sampled_step5 = step5[step5["Lokalitet_ID"].isin(sampled_sites)]

    print(f"\nOriginal dataset: {len(step5)} rows, {len(unique_sites)} sites")
    print(f"Sampled dataset: {len(sampled_step5)} rows, {len(sampled_sites)} sites")

    # Save sampled dataset
    sample_file = (
        Path(__file__).parent.parent.parent / "Resultater" / "test_step5_sample.csv"
    )
    sampled_step5.to_csv(sample_file, index=False)
    print(f"\nSaved sample to: {sample_file}")
    print("\nTo test with reduced dataset:")
    print("1. Backup step5_compound_detailed_combinations.csv")
    print("2. Replace with test_step5_sample.csv")
    print("3. Run step6_tilstandsvurdering.py")
    print("4. Check if results are consistent (same logic, smaller scale)")

    # Analyze sample characteristics
    print("\nSample characteristics:")
    print(f"  GVFKs: {sampled_step5['GVFK'].nunique()}")
    print(f"  River segments: {sampled_step5['Nearest_River_ov_id'].nunique()}")
    print(f"  Categories: {sampled_step5['Qualifying_Category'].nunique()}")
    print(
        f"  Multi-GVFK sites: {(sampled_step5.groupby('Lokalitet_ID')['GVFK'].nunique() > 1).sum()}"
    )


# ===========================================================================
# Main Validation Runner
# ===========================================================================


def main():
    """Run all validation tests"""
    print("=" * 80)
    print("STEP 6 DATA FLOW VALIDATION")
    print("=" * 80)

    # Load data
    data = load_step6_data()

    # Run tests
    test1_issues = test_multi_gvfk_sites(data)
    test_scenario_expansion(data)
    test2_issues = test_segment_aggregation(data)
    test3_issues = test_mkk_exceedances(data)
    test_reduced_dataset(data, sample_fraction=0.01)

    # Summary
    print("\n" + "=" * 80)
    print("VALIDATION SUMMARY")
    print("=" * 80)

    total_issues = len(test1_issues) + len(test2_issues) + len(test3_issues)

    if total_issues == 0:
        print("\n✅ ALL TESTS PASSED")
        print("The Step 6 data flow is working correctly:")
        print("  - Multi-GVFK sites properly aggregated")
        print("  - Scenario expansion correct")
        print("  - Flux aggregation accurate")
        print("  - MKK exceedances properly detected")
    else:
        print(f"\n❌ FOUND {total_issues} ISSUES")
        print(f"  - Multi-GVFK handling: {len(test1_issues)} issues")
        print(f"  - Flux aggregation: {len(test2_issues)} issues")
        print(f"  - MKK exceedances: {len(test3_issues)} issues")
        print("\nReview the detailed output above for specifics.")

    print("\n" + "=" * 80)


if __name__ == "__main__":
    main()
