"""
Comprehensive Workflow Validation Tool
======================================

Tracks sites AND GVFKs through the entire workflow, analyzing:
- How many sites enter/exit each step
- How many unique GVFKs are involved at each step
- Why sites/GVFKs are filtered (with detailed reasons)
- Site-GVFK combination explosion/collapse

Usage:
    python tools/comprehensive_validation.py --sample-size 50 --seed 42
"""

import sys
from pathlib import Path
import pandas as pd
import numpy as np
import argparse
from collections import defaultdict

# Add parent directory to path
REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from config import DATA_DIR, SHAPE_DIR, RESULTS_DIR


class WorkflowTracker:
    """Tracks data transformations through the workflow."""

    def __init__(self):
        self.step_data = {}
        self.sample_sites = []

    def load_raw_v2(self):
        """Load raw V2 contamination data."""
        v2_file = SHAPE_DIR / "V1V2_new" / "v2_gvfk_forurening.csv"
        if not v2_file.exists():
            print(f"❌ Raw V2 file not found: {v2_file}")
            return None

        df = pd.read_csv(v2_file)

        # Column structure: Lokalitet_, ID, Navn (GVFK name), ...
        site_col = df.columns[0]  # Lokalitet_
        gvfk_col = df.columns[2]  # Navn (GVFK name)
        substance_col = df.columns[6]  # Forureni_1 (substance name)

        return {
            'data': df,
            'site_col': site_col,
            'gvfk_col': gvfk_col,
            'substance_col': substance_col,
            'total_rows': len(df),
            'unique_sites': df[site_col].nunique(),
            'unique_gvfks': df[gvfk_col].nunique(),
            'site_gvfk_combinations': df.groupby([site_col, gvfk_col]).size().shape[0],
        }

    def load_step4(self):
        """Load Step 4 distance calculations."""
        step4_file = RESULTS_DIR / "backup" / "step4_distances" / "data" / "step4_final_distances.csv"
        if not step4_file.exists():
            step4_file = RESULTS_DIR / "step4_final_distances_for_risk_assessment.csv"

        if not step4_file.exists():
            print(f"❌ Step 4 file not found")
            return None

        df = pd.read_csv(step4_file)

        return {
            'data': df,
            'site_col': 'Lokalitet_ID',
            'gvfk_col': 'GVFK',
            'total_rows': len(df),
            'unique_sites': df['Lokalitet_ID'].nunique(),
            'unique_gvfks': df['GVFK'].nunique(),
            'site_gvfk_combinations': df.groupby(['Lokalitet_ID', 'GVFK']).size().shape[0],
        }

    def load_step5(self):
        """Load Step 5 compound-specific filtered data."""
        step5_file = RESULTS_DIR / "backup" / "step5_risk_assessment" / "data" / "step5_compound_detailed_combinations.csv"
        if not step5_file.exists():
            step5_file = RESULTS_DIR / "step5_compound_detailed_combinations.csv"

        if not step5_file.exists():
            print(f"❌ Step 5 file not found")
            return None

        df = pd.read_csv(step5_file)

        return {
            'data': df,
            'site_col': 'Lokalitet_ID',
            'gvfk_col': 'GVFK',
            'category_col': 'Qualifying_Category',
            'substance_col': 'Qualifying_Substance',
            'total_rows': len(df),
            'unique_sites': df['Lokalitet_ID'].nunique(),
            'unique_gvfks': df['GVFK'].nunique(),
            'site_gvfk_combinations': df.groupby(['Lokalitet_ID', 'GVFK']).size().shape[0],
            'unique_categories': df['Qualifying_Category'].nunique() if 'Qualifying_Category' in df.columns else 0,
        }

    def load_step6(self):
        """Load Step 6 flux calculations."""
        step6_file = RESULTS_DIR / "backup" / "step6_tilstandsvurdering" / "data" / "step6_flux_site_segment.csv"
        if not step6_file.exists():
            step6_file = RESULTS_DIR / "step6_flux_site_segment.csv"

        if not step6_file.exists():
            print(f"❌ Step 6 file not found")
            return None

        df = pd.read_csv(step6_file)

        return {
            'data': df,
            'site_col': 'Lokalitet_ID' if 'Lokalitet_ID' in df.columns else df.columns[0],
            'gvfk_col': 'GVFK',
            'total_rows': len(df),
            'unique_sites': df['Lokalitet_ID'].nunique() if 'Lokalitet_ID' in df.columns else 0,
            'unique_gvfks': df['GVFK'].nunique() if 'GVFK' in df.columns else 0,
        }

    def select_sample(self, raw_data, n_sites=50, seed=42):
        """Randomly select a stratified sample of sites."""
        df = raw_data['data']
        site_col = raw_data['site_col']
        gvfk_col = raw_data['gvfk_col']

        # Characterize sites by complexity
        site_complexity = (
            df.groupby(site_col)
            .agg({
                gvfk_col: 'nunique',
                raw_data['substance_col']: 'nunique',
            })
            .rename(columns={
                gvfk_col: 'gvfk_count',
                raw_data['substance_col']: 'substance_count',
            })
        )

        # Stratified sampling
        np.random.seed(seed)
        sample_sites = []

        # Simple sites (1 GVFK, ≤3 substances): 30%
        simple = site_complexity[(site_complexity['gvfk_count'] == 1) & (site_complexity['substance_count'] <= 3)]
        if len(simple) > 0:
            n_simple = min(int(n_sites * 0.3), len(simple))
            sample_sites.extend(simple.sample(n=n_simple, random_state=seed).index.tolist())

        # Moderate (2-3 GVFKs): 30%
        moderate = site_complexity[(site_complexity['gvfk_count'] >= 2) & (site_complexity['gvfk_count'] <= 3)]
        if len(moderate) > 0:
            n_moderate = min(int(n_sites * 0.3), len(moderate))
            sample_sites.extend(moderate.sample(n=n_moderate, random_state=seed+1).index.tolist())

        # Complex (4+ GVFKs): 20%
        complex_sites = site_complexity[site_complexity['gvfk_count'] >= 4]
        if len(complex_sites) > 0:
            n_complex = min(int(n_sites * 0.2), len(complex_sites))
            sample_sites.extend(complex_sites.sample(n=n_complex, random_state=seed+2).index.tolist())

        # Substance-rich (≥5 substances): 20%
        substance_rich = site_complexity[site_complexity['substance_count'] >= 5]
        substance_rich = substance_rich[~substance_rich.index.isin(sample_sites)]
        if len(substance_rich) > 0:
            n_rich = min(int(n_sites * 0.2), len(substance_rich))
            sample_sites.extend(substance_rich.sample(n=n_rich, random_state=seed+3).index.tolist())

        # Fill remaining with random
        remaining = n_sites - len(sample_sites)
        if remaining > 0:
            available = site_complexity[~site_complexity.index.isin(sample_sites)]
            if len(available) > 0:
                n_fill = min(remaining, len(available))
                sample_sites.extend(available.sample(n=n_fill, random_state=seed+4).index.tolist())

        self.sample_sites = sample_sites[:n_sites]
        return self.sample_sites

    def analyze_step_transition(self, step_before, step_after, step_name):
        """Analyze what happens between two steps."""
        if step_before is None or step_after is None:
            return None

        df_before = step_before['data']
        df_after = step_after['data']

        site_col_before = step_before['site_col']
        site_col_after = step_after['site_col']
        gvfk_col_before = step_before['gvfk_col']
        gvfk_col_after = step_after['gvfk_col']

        # Track sample sites
        sample_results = []
        for site_id in self.sample_sites:
            rows_before = df_before[df_before[site_col_before] == site_id]
            rows_after = df_after[df_after[site_col_after] == site_id]

            gvfks_before = set(rows_before[gvfk_col_before].unique()) if len(rows_before) > 0 else set()
            gvfks_after = set(rows_after[gvfk_col_after].unique()) if len(rows_after) > 0 else set()

            lost_gvfks = gvfks_before - gvfks_after

            sample_results.append({
                'site_id': site_id,
                'rows_before': len(rows_before),
                'rows_after': len(rows_after),
                'gvfks_before': len(gvfks_before),
                'gvfks_after': len(gvfks_after),
                'gvfks_lost': list(lost_gvfks),
                'filtered': len(rows_after) == 0,
            })

        return {
            'step_name': step_name,
            'sites_before': step_before['unique_sites'],
            'sites_after': step_after['unique_sites'],
            'sites_lost': step_before['unique_sites'] - step_after['unique_sites'],
            'gvfks_before': step_before['unique_gvfks'],
            'gvfks_after': step_after['unique_gvfks'],
            'gvfks_lost': step_before['unique_gvfks'] - step_after['unique_gvfks'],
            'rows_before': step_before['total_rows'],
            'rows_after': step_after['total_rows'],
            'sample_details': pd.DataFrame(sample_results),
        }

    def run_full_analysis(self, n_sites=50, seed=42):
        """Run complete workflow validation."""
        print("\n" + "=" * 80)
        print("COMPREHENSIVE WORKFLOW VALIDATION")
        print("=" * 80)
        print(f"Sample size: {n_sites} sites")
        print(f"Random seed: {seed}")

        # Load all steps
        print("\n[1/5] Loading workflow outputs...")
        raw = self.load_raw_v2()
        step4 = self.load_step4()
        step5 = self.load_step5()
        step6 = self.load_step6()

        if raw is None:
            print("❌ Cannot proceed without raw data")
            return

        # Select sample
        print(f"\n[2/5] Selecting stratified sample of {n_sites} sites...")
        self.select_sample(raw, n_sites=n_sites, seed=seed)
        print(f"✓ Selected {len(self.sample_sites)} sites")

        # Analyze transitions
        print(f"\n[3/5] Analyzing step transitions...")

        transitions = {}

        if step4:
            transitions['raw_to_step4'] = self.analyze_step_transition(raw, step4, "Raw → Step 4")

        if step4 and step5:
            transitions['step4_to_step5'] = self.analyze_step_transition(step4, step5, "Step 4 → Step 5")

        if step5 and step6:
            transitions['step5_to_step6'] = self.analyze_step_transition(step5, step6, "Step 5 → Step 6")

        # Print summary
        print(f"\n[4/5] Generating summary report...")
        self.print_summary(raw, step4, step5, step6, transitions)

        # Save detailed results
        print(f"\n[5/5] Saving detailed results...")
        self.save_results(raw, step4, step5, step6, transitions)

        print("\n" + "=" * 80)
        print("VALIDATION COMPLETE")
        print("=" * 80)

    def print_summary(self, raw, step4, step5, step6, transitions):
        """Print summary statistics."""
        print("\n" + "=" * 80)
        print("WORKFLOW OVERVIEW")
        print("=" * 80)

        print(f"\n{'Step':<15} {'Rows':<12} {'Sites':<10} {'GVFKs':<10} {'Site-GVFK':<15}")
        print("-" * 80)

        if raw:
            print(f"{'Raw V2':<15} {raw['total_rows']:<12,} {raw['unique_sites']:<10,} {raw['unique_gvfks']:<10,} {raw['site_gvfk_combinations']:<15,}")

        if step4:
            print(f"{'Step 4':<15} {step4['total_rows']:<12,} {step4['unique_sites']:<10,} {step4['unique_gvfks']:<10,} {step4['site_gvfk_combinations']:<15,}")

        if step5:
            print(f"{'Step 5':<15} {step5['total_rows']:<12,} {step5['unique_sites']:<10,} {step5['unique_gvfks']:<10,} {step5['site_gvfk_combinations']:<15,}")

        if step6:
            print(f"{'Step 6':<15} {step6['total_rows']:<12,} {step6['unique_sites']:<10,} {step6['unique_gvfks']:<10,} {'N/A':<15}")

        # Attrition rates
        if raw and step5:
            print(f"\n{'OVERALL ATTRITION (Raw → Step 5)':<50}")
            print("-" * 80)
            site_retention = (step5['unique_sites'] / raw['unique_sites']) * 100
            gvfk_retention = (step5['unique_gvfks'] / raw['unique_gvfks']) * 100
            print(f"  Sites retained: {step5['unique_sites']:,} / {raw['unique_sites']:,} ({site_retention:.1f}%)")
            print(f"  GVFKs retained: {step5['unique_gvfks']:,} / {raw['unique_gvfks']:,} ({gvfk_retention:.1f}%)")

        # Transition details
        for trans_name, trans_data in transitions.items():
            if trans_data:
                print(f"\n{trans_data['step_name']}")
                print("-" * 80)
                print(f"  Sites: {trans_data['sites_before']:,} → {trans_data['sites_after']:,} (lost {trans_data['sites_lost']:,})")
                print(f"  GVFKs: {trans_data['gvfks_before']:,} → {trans_data['gvfks_after']:,} (lost {trans_data['gvfks_lost']:,})")

                # Sample filtering stats
                sample_df = trans_data['sample_details']
                filtered_count = sample_df['filtered'].sum()
                print(f"  Sample: {filtered_count}/{len(sample_df)} sites filtered ({filtered_count/len(sample_df)*100:.1f}%)")

    def save_results(self, raw, step4, step5, step6, transitions):
        """Save detailed results to CSV files."""
        output_dir = RESULTS_DIR / "validation_output"
        output_dir.mkdir(exist_ok=True)

        # Save sample list
        if self.sample_sites:
            sample_df = pd.DataFrame({'Lokalitet_ID': self.sample_sites})
            sample_df.to_csv(output_dir / "sample_sites.csv", index=False)
            print(f"✓ Saved sample list: {output_dir / 'sample_sites.csv'}")

        # Save transition details
        for trans_name, trans_data in transitions.items():
            if trans_data and trans_data['sample_details'] is not None:
                filename = f"transition_{trans_name}.csv"
                trans_data['sample_details'].to_csv(output_dir / filename, index=False)
                print(f"✓ Saved transition: {output_dir / filename}")


def main():
    parser = argparse.ArgumentParser(description='Comprehensive Workflow Validation')
    parser.add_argument('--sample-size', type=int, default=50, help='Number of sites to sample (default: 50)')
    parser.add_argument('--seed', type=int, default=42, help='Random seed for reproducibility (default: 42)')

    args = parser.parse_args()

    tracker = WorkflowTracker()
    tracker.run_full_analysis(n_sites=args.sample_size, seed=args.seed)


if __name__ == '__main__':
    main()
