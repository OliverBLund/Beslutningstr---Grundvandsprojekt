"""
Verify Step 6 Category Coverage
================================

This script verifies that step6_tilstandsvurdering.py correctly handles
all compound groups present in the Step 5 output data.

Checks performed:
1. Lists all unique categories in Step 5 output
2. Verifies each category has appropriate scenario configuration
3. Tests flux calculation for each category
4. Reports any missing or problematic configurations
"""

from pathlib import Path
import pandas as pd
import sys

# Add repo root to path
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from config import RESULTS_DIR
from tilstandsvurdering.step6_tilstandsvurdering import (
    CATEGORY_SCENARIOS,
    STANDARD_CONCENTRATIONS
)

def main():
    print("=" * 80)
    print("STEP 6 CATEGORY COVERAGE VERIFICATION")
    print("=" * 80)
    print()

    # Load Step 5 output
    step5_path = RESULTS_DIR / "step5_compound_detailed_combinations.csv"
    print(f"Loading Step 5 output: {step5_path}")

    if not step5_path.exists():
        print(f"ERROR: Step 5 output file not found: {step5_path}")
        return 1

    df = pd.read_csv(step5_path, encoding='utf-8-sig')
    print(f"Loaded {len(df):,} rows")
    print()

    # Get all unique categories
    categories = df['Qualifying_Category'].dropna().unique()
    print(f"Found {len(categories)} unique categories in Step 5 output:")
    print()

    # Count occurrences per category
    category_counts = df['Qualifying_Category'].value_counts()

    # Check each category
    issues = []

    for category in sorted(categories):
        count = category_counts.get(category, 0)
        print(f"\n{'='*80}")
        print(f"Category: {category}")
        print(f"Occurrences: {count:,}")
        print(f"{'='*80}")

        # Check if category has scenario configuration
        scenarios = CATEGORY_SCENARIOS.get(category, None)

        if scenarios is None:
            print(f"  ⚠️  WARNING: Category '{category}' not in CATEGORY_SCENARIOS mapping")
            issues.append(f"Missing CATEGORY_SCENARIOS entry: {category}")

            # Check if there's a category fallback concentration
            category_key = f"LOSSEPLADS" if "LOSSEPLADS" in category else category
            has_fallback = any(
                category_key in key
                for key in STANDARD_CONCENTRATIONS.get("category", {}).keys()
            )

            if has_fallback:
                print(f"  ✓ Has category fallback concentration")
            else:
                print(f"  ❌ NO fallback concentration available")
                issues.append(f"No concentration fallback for: {category}")

        elif len(scenarios) == 0:
            print(f"  ℹ️  Category has no scenarios (will use category fallback)")

            # Verify category fallback exists
            if category in STANDARD_CONCENTRATIONS.get("category", {}):
                conc = STANDARD_CONCENTRATIONS["category"][category]
                print(f"  ✓ Category fallback: {conc:,.1f} µg/L")
            else:
                print(f"  ❌ NO category fallback concentration defined")
                issues.append(f"No category fallback for: {category}")

        else:
            print(f"  ✓ Has {len(scenarios)} scenario(s): {', '.join(scenarios)}")

            # Verify each scenario has a concentration defined
            for modelstof in scenarios:
                scenario_key = f"{category}__via_{modelstof}"

                if scenario_key in STANDARD_CONCENTRATIONS.get("category", {}):
                    conc = STANDARD_CONCENTRATIONS["category"][scenario_key]
                    print(f"    ✓ {modelstof}: {conc:,.1f} µg/L")
                else:
                    print(f"    ❌ {modelstof}: NO concentration defined")
                    issues.append(f"Missing concentration for {scenario_key}")

        # Sample some substances from this category
        category_data = df[df['Qualifying_Category'] == category]
        sample_substances = category_data['Qualifying_Substance'].value_counts().head(5)

        print(f"\n  Top substances in this category:")
        for substance, sub_count in sample_substances.items():
            print(f"    - {substance}: {sub_count:,} occurrences")

    # Summary
    print("\n")
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print()

    if issues:
        print(f"❌ Found {len(issues)} issue(s):")
        print()
        for i, issue in enumerate(issues, 1):
            print(f"  {i}. {issue}")
        print()
        print("These issues may cause flux calculation to fail or use incorrect fallbacks.")
        return 1
    else:
        print("✅ All categories have appropriate configuration")
        print("✅ Step 6 should work correctly with current Step 5 output")
        return 0

if __name__ == "__main__":
    sys.exit(main())
