"""
Test Step 6 Flux Calculation
=============================

Quick test to verify that flux calculation works correctly with all categories
from Step 5 output, without running the full visualization pipeline.
"""

from pathlib import Path
import pandas as pd
import sys

# Add repo root to path
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from config import RESULTS_DIR

def test_flux_calculation():
    """Test that flux calculation can be imported and has correct configuration"""

    print("=" * 80)
    print("TESTING STEP 6 FLUX CALCULATION")
    print("=" * 80)
    print()

    # Import flux calculation components
    try:
        from tilstandsvurdering.step6_tilstandsvurdering import (
            CATEGORY_SCENARIOS,
            STANDARD_CONCENTRATIONS,
            _lookup_concentration_for_scenario
        )
        print("✓ Successfully imported Step 6 components")
    except Exception as e:
        print(f"✗ Failed to import Step 6 components: {e}")
        return False

    print()

    # Load Step 5 data
    step5_path = RESULTS_DIR / "step5_compound_detailed_combinations.csv"
    print(f"Loading Step 5 data: {step5_path}")

    if not step5_path.exists():
        print(f"✗ Step 5 output not found")
        return False

    df = pd.read_csv(step5_path, encoding='utf-8-sig')
    print(f"✓ Loaded {len(df):,} rows")
    print()

    # Test concentration lookup for each category
    categories = df['Qualifying_Category'].dropna().unique()
    print(f"Testing concentration lookup for {len(categories)} categories...")
    print()

    test_results = []

    for category in sorted(categories):
        scenarios = CATEGORY_SCENARIOS.get(category, [])

        # Get a sample row from this category
        sample_row = df[df['Qualifying_Category'] == category].iloc[0]

        if len(scenarios) == 0:
            # Test category fallback
            try:
                # Simulate lookup without scenario
                if category in STANDARD_CONCENTRATIONS.get("category", {}):
                    conc = STANDARD_CONCENTRATIONS["category"][category]
                    test_results.append({
                        'category': category,
                        'scenario': 'N/A (fallback)',
                        'concentration': conc,
                        'status': 'PASS'
                    })
                else:
                    test_results.append({
                        'category': category,
                        'scenario': 'N/A',
                        'concentration': None,
                        'status': 'FAIL: No fallback'
                    })
            except Exception as e:
                test_results.append({
                    'category': category,
                    'scenario': 'N/A',
                    'concentration': None,
                    'status': f'ERROR: {e}'
                })
        else:
            # Test each scenario
            for modelstof in scenarios:
                try:
                    conc = _lookup_concentration_for_scenario(
                        scenario_modelstof=modelstof,
                        category=category,
                        original_substance=sample_row.get('Qualifying_Substance'),
                        row=sample_row
                    )
                    test_results.append({
                        'category': category,
                        'scenario': modelstof,
                        'concentration': conc,
                        'status': 'PASS'
                    })
                except Exception as e:
                    test_results.append({
                        'category': category,
                        'scenario': modelstof,
                        'concentration': None,
                        'status': f'ERROR: {e}'
                    })

    # Display results
    results_df = pd.DataFrame(test_results)

    print("Concentration Lookup Test Results:")
    print("=" * 80)

    for _, row in results_df.iterrows():
        status_symbol = "✓" if row['status'] == 'PASS' else "✗"
        conc_str = f"{row['concentration']:,.1f} µg/L" if row['concentration'] is not None else "N/A"
        print(f"{status_symbol} {row['category']:30s} | {row['scenario']:25s} | {conc_str:15s} | {row['status']}")

    print()
    print("=" * 80)

    # Summary
    passed = (results_df['status'] == 'PASS').sum()
    failed = (results_df['status'] != 'PASS').sum()

    print(f"Results: {passed} passed, {failed} failed out of {len(results_df)} tests")

    if failed > 0:
        print()
        print("✗ Some concentration lookups failed")
        return False
    else:
        print()
        print("✅ All concentration lookups successful")
        print("✅ Step 6 flux calculation should work correctly")
        return True

if __name__ == "__main__":
    success = test_flux_calculation()
    sys.exit(0 if success else 1)
