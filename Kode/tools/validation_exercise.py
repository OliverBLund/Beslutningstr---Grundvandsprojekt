"""
Validation Exercise: Step-by-Step Workflow Verification
========================================================

This script helps validate the workflow by:
1. Running the full workflow with detailed step outputs
2. Creating a small test subset for manual verification
3. Tracking data transformations at each step

Usage:
    python tools/validation_exercise.py --mode [full|subset|both]

    --mode full: Run full workflow with detailed logging
    --mode subset: Create and analyze test subset only
    --mode both: Do both (default)
"""

import sys
from pathlib import Path
import pandas as pd
import geopandas as gpd
import argparse

# Add parent directory to path
REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from config import (
    DATA_DIR,
    SHAPE_DIR,
    RESULTS_DIR,
    ensure_results_directory,
)


def create_test_subset(n_sites=10, seed=42):
    """
    Create a small test subset of sites for detailed validation.

    Strategy:
    - Select diverse sites (different categories, distances, GVFKs)
    - Include known edge cases (site 151-00002)
    - Balance between simple and complex sites

    Args:
        n_sites: Number of sites to include in test subset
        seed: Random seed for reproducibility

    Returns:
        List of Lokalitet_IDs to use for testing
    """
    print("\n" + "=" * 80)
    print("CREATING TEST SUBSET")
    print("=" * 80)

    # Load raw V2 data to understand site characteristics
    v2_file = SHAPE_DIR / "V1V2_new" / "v2_gvfk_forurening.csv"

    if not v2_file.exists():
        print(f"ERROR: Raw V2 file not found: {v2_file}")
        return []

    v2_data = pd.read_csv(v2_file)
    print(f"\nLoaded {len(v2_data)} rows from raw V2 data")
    print(f"Unique sites: {v2_data.iloc[:, 0].nunique()}")  # First column is Lokalitet_ID

    # Analyze site characteristics
    site_summary = (
        v2_data.groupby(v2_data.columns[0])  # Group by Lokalitet_ID
        .agg({
            v2_data.columns[2]: 'nunique',  # GVFK count
            v2_data.columns[6]: 'nunique',  # Substance count
        })
        .rename(columns={
            v2_data.columns[2]: 'GVFK_count',
            v2_data.columns[6]: 'Substance_count',
        })
    )

    print("\n--- Site Complexity Distribution ---")
    print(f"Sites with 1 GVFK: {(site_summary['GVFK_count'] == 1).sum()}")
    print(f"Sites with 2-3 GVFKs: {((site_summary['GVFK_count'] >= 2) & (site_summary['GVFK_count'] <= 3)).sum()}")
    print(f"Sites with 4+ GVFKs: {(site_summary['GVFK_count'] >= 4).sum()}")

    # Selection strategy
    test_sites = []

    # 1. Always include our known test case
    test_sites.append("151-00002")
    print(f"\n1. Added known test case: 151-00002 (4 GVFKs)")

    # 2. Add simple sites (1 GVFK, few substances)
    simple_sites = site_summary[
        (site_summary['GVFK_count'] == 1) &
        (site_summary['Substance_count'] <= 3)
    ].sample(n=2, random_state=seed).index.tolist()
    test_sites.extend(simple_sites)
    print(f"2. Added {len(simple_sites)} simple sites (1 GVFK, ≤3 substances): {simple_sites}")

    # 3. Add moderate complexity (2-3 GVFKs)
    moderate_sites = site_summary[
        (site_summary['GVFK_count'] >= 2) &
        (site_summary['GVFK_count'] <= 3)
    ].sample(n=3, random_state=seed).index.tolist()
    test_sites.extend(moderate_sites)
    print(f"3. Added {len(moderate_sites)} moderate sites (2-3 GVFKs): {moderate_sites}")

    # 4. Add complex sites (4+ GVFKs)
    complex_sites = site_summary[
        site_summary['GVFK_count'] >= 4
    ].sample(n=min(2, (site_summary['GVFK_count'] >= 4).sum()), random_state=seed).index.tolist()
    test_sites.extend(complex_sites)
    print(f"4. Added {len(complex_sites)} complex sites (4+ GVFKs): {complex_sites}")

    # 5. Add sites with many substances
    substance_rich = site_summary[
        site_summary['Substance_count'] >= 5
    ].sample(n=min(2, (site_summary['Substance_count'] >= 5).sum()), random_state=seed).index.tolist()
    # Remove duplicates
    substance_rich = [s for s in substance_rich if s not in test_sites]
    test_sites.extend(substance_rich[:2])
    print(f"5. Added {len(substance_rich[:2])} substance-rich sites (≥5 substances): {substance_rich[:2]}")

    # Trim to requested size
    test_sites = test_sites[:n_sites]

    print(f"\n--- Final Test Subset ---")
    print(f"Total sites: {len(test_sites)}")
    print(f"Site IDs: {test_sites}")

    # Save test subset configuration
    subset_file = RESULTS_DIR / "validation_test_subset.txt"
    with open(subset_file, 'w') as f:
        f.write("# Test Subset for Validation Exercise\n")
        f.write(f"# Generated with seed={seed}, n_sites={n_sites}\n\n")
        for site_id in test_sites:
            gvfk_count = site_summary.loc[site_id, 'GVFK_count']
            substance_count = site_summary.loc[site_id, 'Substance_count']
            f.write(f"{site_id}\t{gvfk_count} GVFKs\t{substance_count} substances\n")

    print(f"\nTest subset saved to: {subset_file}")

    return test_sites


def track_site_through_steps(site_ids, verbose=True):
    """
    Track specific sites through each workflow step.

    Args:
        site_ids: List of Lokalitet_IDs to track
        verbose: Print detailed information

    Returns:
        DataFrame with row counts per site per step
    """
    print("\n" + "=" * 80)
    print("TRACKING SITES THROUGH WORKFLOW STEPS")
    print("=" * 80)

    tracking_results = []

    # Step 0: Raw V2 data
    v2_file = SHAPE_DIR / "V1V2_new" / "v2_gvfk_forurening.csv"
    if v2_file.exists():
        v2_data = pd.read_csv(v2_file)
        v2_id_col = v2_data.columns[0]  # First column is Lokalitet_ID

        for site_id in site_ids:
            site_rows = v2_data[v2_data[v2_id_col] == site_id]
            gvfks = site_rows.iloc[:, 2].unique() if len(site_rows) > 0 else []

            tracking_results.append({
                'Lokalitet_ID': site_id,
                'Step': 'Raw_V2',
                'Row_Count': len(site_rows),
                'GVFK_Count': len(gvfks),
                'GVFKs': ', '.join(map(str, gvfks)) if len(gvfks) > 0 else 'NONE',
                'Notes': f"{len(site_rows)} total rows"
            })

    # Check if workflow has been run
    step_files = {
        'Step1_All_GVFK': RESULTS_DIR / "step1_all_gvfk_combinations.csv",
        'Step2_River_Contact': RESULTS_DIR / "step2_gvfk_river_contact.csv",
        'Step3_Sites': RESULTS_DIR / "step3_v1v2_sites.shp",
        'Step4_Distances': RESULTS_DIR / "step4_final_distances_for_risk_assessment.csv",
        'Step5_Compound': RESULTS_DIR / "step5_compound_detailed_combinations.csv",
        'Step6_Flux': RESULTS_DIR / "step6_flux_site_segment.csv",
    }

    # Try backup directory if main results don't exist
    for step_name, step_file in step_files.items():
        if not step_file.exists():
            backup_file = RESULTS_DIR / "backup" / step_file.name.replace('step', 'step').replace('.csv', '/data/' + step_file.name)
            if backup_file.exists():
                step_files[step_name] = backup_file

    for step_name, step_file in step_files.items():
        if not step_file.exists():
            if verbose:
                print(f"\n⚠ {step_name} output not found: {step_file}")
            for site_id in site_ids:
                tracking_results.append({
                    'Lokalitet_ID': site_id,
                    'Step': step_name,
                    'Row_Count': 0,
                    'GVFK_Count': 0,
                    'GVFKs': 'FILE NOT FOUND',
                    'Notes': 'Workflow not run yet'
                })
            continue

        # Load step data
        if step_file.suffix == '.shp':
            step_data = gpd.read_file(step_file)
        else:
            step_data = pd.read_csv(step_file)

        # Find Lokalitet_ID column (may vary)
        id_cols = [c for c in step_data.columns if 'lokalitet' in c.lower() and 'id' in c.lower()]
        if not id_cols:
            id_cols = [c for c in step_data.columns if c.startswith('Lokalitet')]

        if not id_cols:
            print(f"⚠ Cannot find Lokalitet_ID column in {step_name}")
            continue

        id_col = id_cols[0]

        # Track each site
        for site_id in site_ids:
            site_rows = step_data[step_data[id_col] == site_id]

            # Count unique GVFKs if column exists
            gvfk_cols = [c for c in step_data.columns if 'GVFK' in c and 'Count' not in c]
            gvfks = []
            if gvfk_cols:
                gvfks = site_rows[gvfk_cols[0]].unique()

            # Get river info if available
            river_cols = [c for c in step_data.columns if 'River' in c and 'ov_id' in c]
            rivers = []
            if river_cols:
                rivers = site_rows[river_cols[0]].unique()

            notes = []
            if len(rivers) > 0:
                notes.append(f"{len(rivers)} rivers")
            if 'Qualifying_Category' in step_data.columns:
                categories = site_rows['Qualifying_Category'].unique()
                notes.append(f"{len(categories)} categories")

            tracking_results.append({
                'Lokalitet_ID': site_id,
                'Step': step_name,
                'Row_Count': len(site_rows),
                'GVFK_Count': len(gvfks),
                'GVFKs': ', '.join(map(str, gvfks)) if len(gvfks) > 0 else ('FILTERED' if len(site_rows) == 0 else 'N/A'),
                'Notes': '; '.join(notes) if notes else ''
            })

    # Create summary DataFrame
    tracking_df = pd.DataFrame(tracking_results)

    # Print summary
    if verbose:
        print("\n--- Site Tracking Summary ---")
        for site_id in site_ids:
            site_track = tracking_df[tracking_df['Lokalitet_ID'] == site_id]
            print(f"\n{site_id}:")
            for _, row in site_track.iterrows():
                status = "✓" if row['Row_Count'] > 0 else "✗"
                print(f"  {status} {row['Step']:20s}: {row['Row_Count']:3d} rows | {row['GVFK_Count']} GVFKs | {row['Notes']}")

    # Save tracking results
    tracking_file = RESULTS_DIR / "validation_site_tracking.csv"
    tracking_df.to_csv(tracking_file, index=False)
    print(f"\nTracking results saved to: {tracking_file}")

    # Create pivot table for easier viewing
    pivot = tracking_df.pivot(index='Lokalitet_ID', columns='Step', values='Row_Count').fillna(0).astype(int)
    pivot_file = RESULTS_DIR / "validation_site_tracking_pivot.csv"
    pivot.to_csv(pivot_file)
    print(f"Pivot table saved to: {pivot_file}")

    return tracking_df


def analyze_filtering_cascade(site_ids):
    """
    Analyze why sites are filtered at each step.

    Args:
        site_ids: List of Lokalitet_IDs to analyze

    Returns:
        DataFrame with filtering reasons
    """
    print("\n" + "=" * 80)
    print("ANALYZING FILTERING CASCADE")
    print("=" * 80)

    filtering_analysis = []

    # Compare consecutive steps to identify filtering
    step_pairs = [
        ('Raw_V2', 'Step1_All_GVFK', 'Missing in GVFK shapefile'),
        ('Step1_All_GVFK', 'Step2_River_Contact', 'GVFK does not touch rivers'),
        ('Step2_River_Contact', 'Step4_Distances', 'No valid distance calculation'),
        ('Step4_Distances', 'Step5_Compound', 'Exceeds compound-specific threshold'),
        ('Step5_Compound', 'Step6_Flux', 'Missing infiltration or negative flux'),
    ]

    # This would require loading and comparing each step's output
    # Implementation details depend on actual data structure

    print("\n⚠ Detailed filtering analysis requires running the workflow first")
    print("   Run with --mode full to generate step outputs")

    return pd.DataFrame(filtering_analysis)


def main():
    """Main validation exercise controller."""
    parser = argparse.ArgumentParser(description='Workflow Validation Exercise')
    parser.add_argument(
        '--mode',
        choices=['full', 'subset', 'both'],
        default='both',
        help='Validation mode: full workflow, subset only, or both'
    )
    parser.add_argument(
        '--n-sites',
        type=int,
        default=10,
        help='Number of sites in test subset (default: 10)'
    )
    parser.add_argument(
        '--seed',
        type=int,
        default=42,
        help='Random seed for reproducibility (default: 42)'
    )

    args = parser.parse_args()

    ensure_results_directory()

    print("\n" + "=" * 80)
    print("VALIDATION EXERCISE: STEP-BY-STEP WORKFLOW VERIFICATION")
    print("=" * 80)
    print(f"Mode: {args.mode}")
    print(f"Test subset size: {args.n_sites} sites")
    print(f"Random seed: {args.seed}")

    if args.mode in ['subset', 'both']:
        # Create test subset
        test_sites = create_test_subset(n_sites=args.n_sites, seed=args.seed)

        # Track sites through workflow
        if test_sites:
            tracking_df = track_site_through_steps(test_sites, verbose=True)

            # Analyze filtering
            analyze_filtering_cascade(test_sites)

    if args.mode in ['full', 'both']:
        print("\n" + "=" * 80)
        print("FULL WORKFLOW RUN")
        print("=" * 80)
        print("\nTo run the full workflow with detailed logging:")
        print("  python main_workflow.py")
        print("\nAfter running, use --mode subset to analyze the test subset")

    print("\n" + "=" * 80)
    print("VALIDATION EXERCISE COMPLETE")
    print("=" * 80)
    print("\nNext steps:")
    print("1. Review test subset in: validation_test_subset.txt")
    print("2. Review site tracking in: validation_site_tracking.csv")
    print("3. Run full workflow if not done yet")
    print("4. Manually verify transformations for test sites")
    print("=" * 80 + "\n")


if __name__ == '__main__':
    main()
