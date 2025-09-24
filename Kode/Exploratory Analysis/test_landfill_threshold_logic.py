"""
Test Landfill Threshold Logic with Concrete Examples
===================================================

Verify that the Step 5 logic correctly applies compound-specific landfill thresholds
by tracing through specific scenarios.
"""

import pandas as pd
import os
from config import get_output_path

# Simulate the landfill thresholds from step5_risk_assessment.py
LANDFILL_THRESHOLDS = {
    'BTXER': 70,                           # Benzen representative at landfills
    'KLOREREDE_OPLØSNINGSMIDLER': 100,     # TCE representative at landfills
    'PHENOLER': 35,                        # Phenol representative at landfills
    'PESTICIDER': 110,                     # Atrazin representative at landfills
    'UORGANISKE_FORBINDELSER': 50,         # Arsen representative at landfills
}

def test_threshold_logic():
    """Test the threshold logic with concrete examples."""
    print("TESTING LANDFILL THRESHOLD LOGIC")
    print("=" * 50)

    # Test scenarios
    scenarios = [
        {
            'name': 'BTEX site at landfill - 60m distance',
            'distance': 60,
            'substances': 'Benzen; Toluene',
            'activity': 'Losseplads, deponering',
            'expected_normal': 'BTXER (50m) - qualifies',
            'expected_landfill': 'LOSSEPLADS_BTXER (70m) - qualifies'
        },
        {
            'name': 'Pesticide site at landfill - 150m distance',
            'distance': 150,
            'substances': 'Atrazin; MCPP',
            'activity': 'Losseplads, deponering',
            'expected_normal': 'PESTICIDER (500m) - qualifies',
            'expected_landfill': 'LOSSEPLADS_PESTICIDER (110m) - FAILS threshold'
        },
        {
            'name': 'Heavy metals at landfill - 40m distance',
            'distance': 40,
            'substances': 'Arsen; Bly',
            'activity': 'Losseplads, deponering',
            'expected_normal': 'UORGANISKE_FORBINDELSER (150m) - qualifies',
            'expected_landfill': 'LOSSEPLADS_UORGANISKE_FORBINDELSER (50m) - qualifies'
        },
        {
            'name': 'PAH at landfill - 40m distance',
            'distance': 40,
            'substances': 'Benz[a]pyren; Naftalen',
            'activity': 'Losseplads, deponering',
            'expected_normal': 'PAH_FORBINDELSER (30m) - FAILS threshold',
            'expected_landfill': 'PAH_FORBINDELSER (no override) - FAILS, keeps original'
        },
        {
            'name': 'Chlorinated solvents at landfill - 80m distance',
            'distance': 80,
            'substances': 'TCE; Tetrachlorethylen',
            'activity': 'Losseplads, deponering',
            'expected_normal': 'KLOREREDE_OPLØSNINGSMIDLER (500m) - qualifies',
            'expected_landfill': 'LOSSEPLADS_KLOREREDE_OPLØSNINGSMIDLER (100m) - qualifies'
        },
        {
            'name': 'Multi-substance site at landfill - 90m distance',
            'distance': 90,
            'substances': 'Benzen; Atrazin; Arsen',
            'activity': 'Losseplads, deponering',
            'expected_normal': 'BTXER (50m) FAILS + PESTICIDER (500m) qualifies + UORGANISKE (150m) qualifies',
            'expected_landfill': 'LOSSEPLADS_PESTICIDER (110m) qualifies + LOSSEPLADS_UORGANISKE (50m) FAILS'
        }
    ]

    for i, scenario in enumerate(scenarios, 1):
        print(f"\n{i}. {scenario['name']}")
        print("-" * 50)
        print(f"Distance: {scenario['distance']}m")
        print(f"Substances: {scenario['substances']}")
        print(f"Activity: {scenario['activity']}")
        print(f"Normal logic: {scenario['expected_normal']}")
        print(f"Landfill logic: {scenario['expected_landfill']}")

def verify_actual_results():
    """Verify against actual Step 5 results."""
    print(f"\n" + "="*60)
    print("VERIFICATION AGAINST ACTUAL STEP 5 RESULTS")
    print("="*60)

    # Load actual results
    compound_file = get_output_path('step5_compound_detailed_combinations')
    if not os.path.exists(compound_file):
        print("❌ No Step 5 results found. Run Step 5 first.")
        return

    results = pd.read_csv(compound_file)
    print(f"Loaded {len(results)} combinations from Step 5")

    # Analyze overridden vs non-overridden cases
    overridden = results[results['Landfill_Override_Applied'] == True]
    normal = results[results['Landfill_Override_Applied'] == False]

    print(f"\nOVERRIDDEN TO LOSSEPLADS: {len(overridden)} combinations")
    print(f"KEPT ORIGINAL CATEGORY: {len(normal)} combinations")

    # Show distance statistics for overridden categories
    print(f"\nDISTANCE STATISTICS FOR OVERRIDDEN CATEGORIES:")
    for category in LANDFILL_THRESHOLDS.keys():
        subcategory = f'LOSSEPLADS_{category}'
        cat_data = overridden[overridden['Losseplads_Subcategory'] == subcategory]

        if len(cat_data) > 0:
            threshold = LANDFILL_THRESHOLDS[category]
            distances = cat_data['Final_Distance_m']
            max_dist = distances.max()
            min_dist = distances.min()
            mean_dist = distances.mean()

            print(f"\n{subcategory} (threshold: {threshold}m):")
            print(f"  Count: {len(cat_data)} combinations")
            print(f"  Distance range: {min_dist:.0f}m - {max_dist:.0f}m")
            print(f"  Mean distance: {mean_dist:.0f}m")

            # Verify all are within threshold
            over_threshold = (distances > threshold).sum()
            if over_threshold > 0:
                print(f"  ERROR: {over_threshold} combinations exceed threshold!")
            else:
                print(f"  OK: All combinations within {threshold}m threshold")

    # Check some specific examples from actual data
    print(f"\nSAMPLE ACTUAL CASES:")
    print("-" * 30)

    # Find examples of each overridden category
    for category in LANDFILL_THRESHOLDS.keys():
        subcategory = f'LOSSEPLADS_{category}'
        examples = overridden[overridden['Losseplads_Subcategory'] == subcategory].head(2)

        if len(examples) > 0:
            print(f"\n{subcategory} examples:")
            for _, row in examples.iterrows():
                print(f"  Site {row['Lokalitet_ID']}: {row['Final_Distance_m']:.0f}m")
                print(f"    Activity: {row.get('Lokalitetensaktivitet', 'N/A')}")
                print(f"    Original: {row['Original_Category']} -> LOSSEPLADS")

    # Look for cases that should have been overridden but weren't
    print(f"\nCATEGORIES NOT OVERRIDDEN (no threshold defined):")
    losseplads_sites = results[
        (results['Lokalitetensaktivitet'].str.contains('losseplads', case=False, na=False)) |
        (results['Lokalitetensbranche'].str.contains('affald', case=False, na=False))
    ]

    not_overridden_at_landfills = losseplads_sites[
        (losseplads_sites['Landfill_Override_Applied'] == False) &
        (losseplads_sites['Qualifying_Category'] != 'LOSSEPLADS')
    ]

    if len(not_overridden_at_landfills) > 0:
        skipped_categories = not_overridden_at_landfills['Qualifying_Category'].value_counts()
        print("Categories that stayed at landfill sites (no override threshold):")
        for cat, count in skipped_categories.items():
            print(f"  {cat}: {count} combinations")

if __name__ == "__main__":
    test_threshold_logic()
    verify_actual_results()