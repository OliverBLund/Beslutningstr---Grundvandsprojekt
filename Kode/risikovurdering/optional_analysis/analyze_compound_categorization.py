"""
Compound Categorization Analysis - Excel Export Tool

This is a one-off analysis tool to review how compounds are being categorized.
NOT part of the main workflow - run manually when you need to review categorization.

Usage:
    python -m risikovurdering.optional_analysis.analyze_compound_categorization

Outputs:
    - Excel file: compound_categorization_review.xlsx
    - Summary statistics in terminal
"""

import pandas as pd
import sys
from pathlib import Path

# Add parent directories to path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from config import V1_CSV_PATH, V2_CSV_PATH
from risikovurdering.compound_categories import (
    categorize_substance,
    COMPOUND_CATEGORIES,
    COMPOUND_SPECIFIC_DISTANCES,
)


def analyze_and_export_compounds():
    """Analyze V1/V2 compounds and export detailed Excel report."""
    print("=" * 70)
    print("COMPOUND CATEGORIZATION ANALYSIS")
    print("=" * 70)
    print(f"Categories: {len(COMPOUND_CATEGORIES)} + ANDRE catch-all")
    print()

    # Load data
    try:
        v1_data = pd.read_csv(V1_CSV_PATH, encoding='utf-8')
        v2_data = pd.read_csv(V2_CSV_PATH, encoding='utf-8')
        print(f"Loaded V1: {len(v1_data):,} rows")
        print(f"Loaded V2: {len(v2_data):,} rows")
    except Exception as e:
        print(f"ERROR loading data: {e}")
        return

    # Combine datasets
    v1_data['dataset'] = 'V1'
    v2_data['dataset'] = 'V2'
    combined_data = pd.concat([v1_data, v2_data], ignore_index=True)

    # Get contamination substances
    substances = combined_data['Lokalitetensstoffer'].dropna()
    print(f"Total contamination records: {len(substances):,}")

    # Categorize all substances
    print("\nCategorizing...")
    results = []
    compound_specific_count = 0

    for idx, substance in enumerate(substances):
        if idx % 10000 == 0:
            print(f"  {idx:,}/{len(substances):,}")

        category, distance = categorize_substance(substance)

        # Check if this used a compound-specific distance
        used_specific_distance = False
        if distance is not None:
            substance_lower = substance.lower().strip()
            for compound, specific_distance in COMPOUND_SPECIFIC_DISTANCES.items():
                if compound in substance_lower and distance == specific_distance:
                    used_specific_distance = True
                    compound_specific_count += 1
                    break

        results.append({
            'substance': substance,
            'category': category,
            'distance_m': distance,
            'used_specific_distance': used_specific_distance,
            'dataset': combined_data.loc[substances.index[idx], 'dataset']
        })

    # Convert to DataFrame
    results_df = pd.DataFrame(results)

    # Print summary
    print("\n" + "=" * 70)
    print("CATEGORIZATION SUMMARY")
    print("=" * 70)

    category_counts = results_df['category'].value_counts()
    total_substances = len(results_df)

    for category, count in category_counts.items():
        pct = count / total_substances * 100
        if category in COMPOUND_CATEGORIES:
            distance = COMPOUND_CATEGORIES[category]['distance_m']
            print(f"{category:28} : {count:6,} ({pct:5.1f}%) - {distance}m")
        else:
            print(f"{category:28} : {count:6,} ({pct:5.1f}%) - Default")

    print(f"\nCompound-specific overrides: {compound_specific_count:,} uses")
    if compound_specific_count > 0:
        for compound, distance in COMPOUND_SPECIFIC_DISTANCES.items():
            compound_uses = results_df[results_df['used_specific_distance']]['substance'].apply(
                lambda x: compound in x.lower()
            ).sum()
            if compound_uses > 0:
                print(f"  '{compound}': {distance}m ({compound_uses:,} uses)")

    # Export to Excel
    excel_file = "compound_categorization_review.xlsx"

    with pd.ExcelWriter(excel_file, engine='openpyxl') as writer:
        # Sheet 1: Summary
        summary_data = []
        for category, count in category_counts.items():
            if category in COMPOUND_CATEGORIES:
                info = COMPOUND_CATEGORIES[category]
                summary_data.append({
                    'Category': category,
                    'Count': count,
                    'Percentage': round(count / total_substances * 100, 1),
                    'Distance_m': info['distance_m'],
                    'Description': info['description'],
                })
            else:
                summary_data.append({
                    'Category': category,
                    'Count': count,
                    'Percentage': round(count / total_substances * 100, 1),
                    'Distance_m': 'DEFAULT',
                    'Description': 'Catch-all category',
                })

        summary_df = pd.DataFrame(summary_data)
        summary_df.to_excel(writer, sheet_name='Summary', index=False)

        # Sheet 2-N: Detailed breakdown by category
        for category in category_counts.index:
            cat_data = results_df[results_df['category'] == category]
            cat_substances = cat_data.groupby('substance').agg({
                'distance_m': 'first',
                'substance': 'count'
            }).rename(columns={'substance': 'Frequency'})

            cat_df = pd.DataFrame({
                'Substance': cat_substances.index,
                'Frequency': cat_substances['Frequency'].values,
                'Category': category,
                'Distance_m': cat_substances['distance_m'].values
            })
            sheet_name = category[:31]  # Excel sheet name limit
            cat_df.to_excel(writer, sheet_name=sheet_name, index=False)

        # Last sheet: Raw data
        results_df.to_excel(writer, sheet_name='Raw_Data', index=False)

    print(f"\n✓ Excel file created: {excel_file}")
    print("\nUse this file to review:")
    print("  - Which substances are in each category")
    print("  - ANDRE category substances (need manual review)")
    print("  - Compound-specific distance overrides")

    return results_df, excel_file


if __name__ == "__main__":
    analyze_and_export_compounds()
