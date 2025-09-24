"""
Step 5 Risk Assessment - Analysis and Reporting Functions
========================================================

Analysis, summary, and reporting functions for Step 5 risk assessment.
"""

import pandas as pd
import os
from collections import Counter
from config import get_output_path
from step5_utils import _extract_unique_gvfk_names, get_keyword_stats


def print_keyword_summary():
    """Print summary of keyword matching statistics."""
    keyword_stats = get_keyword_stats()

    print(f"\nLOSSEPLADS KEYWORD MATCHING SUMMARY:")
    print("=" * 50)
    print(f"Total sites checked: {keyword_stats['total_checks']:,}")

    # Branch keyword stats
    branch_total = sum(keyword_stats['branch'].values())
    print(f"\nBranch keyword matches: {branch_total:,}")
    for keyword, count in sorted(keyword_stats['branch'].items(), key=lambda x: x[1], reverse=True):
        print(f"  {keyword}: {count:,} matches")

    # Activity keyword stats
    activity_total = sum(keyword_stats['activity'].values())
    print(f"\nActivity keyword matches: {activity_total:,}")
    for keyword, count in sorted(keyword_stats['activity'].items(), key=lambda x: x[1], reverse=True):
        print(f"  {keyword}: {count:,} matches")

    # Combined stats
    total_matches = branch_total + activity_total
    if keyword_stats['total_checks'] > 0:
        print(f"\nTotal keyword matches: {total_matches:,}")
        print(f"Percentage of sites with landfill keywords: {total_matches/keyword_stats['total_checks']*100:.1f}%")


def print_summary(distance_results, general_sites, compound_combinations, compound_sites):
    """Print comprehensive summary of risk assessment results."""
    total_sites = len(distance_results)
    general_count = len(general_sites)
    compound_unique = len(compound_sites)
    compound_total = len(compound_combinations)

    print(f"\n" + "="*80)
    print(f"STEP 5: COMPREHENSIVE RISK ASSESSMENT RESULTS")
    print(f"="*80)
    print(f"Input: {total_sites:,} sites analyzed from Step 4")

    # GENERAL ASSESSMENT
    print(f"\nGENERAL ASSESSMENT (500m universal threshold):")
    print(f"- Sites within 500m: {general_count:,} ({general_count/total_sites*100:.1f}%)")

    # Top categories from general assessment
    if not general_sites.empty:
        print(f"\nTop Categories (General Assessment):")

        # Industries
        if 'Lokalitetensbranche' in general_sites.columns:
            all_industries = []
            for ind_str in general_sites['Lokalitetensbranche'].dropna():
                industries = [i.strip() for i in str(ind_str).split(';') if i.strip()]
                all_industries.extend(industries)
            if all_industries:
                ind_counts = pd.Series(all_industries).value_counts().head(3)
                ind_str = ', '.join([f'{k} ({v})' for k, v in ind_counts.items()])
                print(f"  Industries: {ind_str}")

        # Activities
        if 'Lokalitetensaktivitet' in general_sites.columns:
            all_activities = []
            for act_str in general_sites['Lokalitetensaktivitet'].dropna():
                activities = [a.strip() for a in str(act_str).split(';') if a.strip()]
                all_activities.extend(activities)
            if all_activities:
                act_counts = pd.Series(all_activities).value_counts().head(3)
                act_str = ', '.join([f'{k} ({v})' for k, v in act_counts.items()])
                print(f"  Activities: {act_str}")

        # Substances
        if 'Lokalitetensstoffer' in general_sites.columns:
            all_substances = []
            for sub_str in general_sites['Lokalitetensstoffer'].dropna():
                substances = [s.strip() for s in str(sub_str).split(';') if s.strip()]
                all_substances.extend(substances)
            if all_substances:
                sub_counts = pd.Series(all_substances).value_counts().head(3)
                sub_str = ', '.join([f'{k} ({v})' for k, v in sub_counts.items()])
                print(f"  Substances: {sub_str}")

    # COMPOUND-SPECIFIC ASSESSMENT
    print(f"\nCOMPOUND-SPECIFIC ASSESSMENT (literature-based thresholds):")
    print(f"- Unique sites qualifying: {compound_unique:,} ({compound_unique/total_sites*100:.1f}%)")
    print(f"- Total site-substance combinations: {compound_total:,}")

    if compound_unique > 0:
        avg_substances = compound_total / compound_unique
        print(f"- Average qualifying substances per site: {avg_substances:.1f}")

    # Multi-substance distribution
    if not compound_combinations.empty:
        substances_per_site = compound_combinations.groupby('Lokalitet_ID').size()

        print(f"\nMulti-Substance Site Distribution:")
        for i in range(1, 4):
            count = (substances_per_site == i).sum()
            if count > 0:
                print(f"  {i} substance{'s' if i > 1 else ''}: {count:,} sites")

        # 4+ substances
        count_4plus = (substances_per_site >= 4).sum()
        if count_4plus > 0:
            print(f"  4+ substances: {count_4plus:,} sites")
            max_substances = substances_per_site.max()
            max_site = substances_per_site.idxmax()
            print(f"  Maximum: {max_substances} substances (Site: {max_site})")

    # Category breakdown with thresholds
    if not compound_combinations.empty:
        print(f"\nCategory Breakdown (by occurrences):")
        print(f"{'Category':<25} {'Threshold':<10} {'Occur.':<8} {'Sites':<8}")
        print(f"{'-'*25} {'-'*10} {'-'*8} {'-'*8}")

        # Get category statistics
        category_stats = {}
        for category in compound_combinations['Qualifying_Category'].unique():
            cat_data = compound_combinations[compound_combinations['Qualifying_Category'] == category]
            threshold = cat_data['Category_Threshold_m'].iloc[0] if not cat_data.empty else 500
            unique_sites = cat_data['Lokalitet_ID'].nunique()
            category_stats[category] = {
                'threshold': threshold,
                'occurrences': len(cat_data),
                'sites': unique_sites
            }

        # Sort by occurrences and print
        sorted_cats = sorted(category_stats.items(), key=lambda x: x[1]['occurrences'], reverse=True)
        for category, stats in sorted_cats[:8]:  # Top 8 categories
            threshold_str = f"{stats['threshold']:.1f}m"
            print(f"{category:<25} {threshold_str:<10} {stats['occurrences']:<8,} {stats['sites']:<8,}")

    # GVFK CASCADE
    print(f"\nGVFK FILTERING CASCADE:")
    print(f"{'Step':<45} {'GVFK':<8} {'% of Total':<10}")
    print(f"{'-'*45} {'-'*8} {'-'*10}")
    print(f"{'Total GVFK in Denmark':<45} {'2,043':<8} {'100.0%':<10}")
    print(f"{'With river contact (Step 2)':<45} {'593':<8} {'29.0%':<10}")
    print(f"{'With V1/V2 sites (Step 3)':<45} {'432':<8} {'21.1%':<10}")

    # Count unique GVFKs at each filtering stage
    # General assessment (500m)
    if not general_sites.empty and 'Closest_GVFK' in general_sites.columns:
        general_gvfks = general_sites['Closest_GVFK'].dropna().nunique()
        general_pct = (general_gvfks / 2043) * 100
        print(f"{'With sites ≤500m (General)':<45} {general_gvfks:<8,} {general_pct:<10.1f}%")

    # Compound-specific assessment
    if not compound_sites.empty and 'Closest_GVFK' in compound_sites.columns:
        compound_gvfks = compound_sites['Closest_GVFK'].dropna().nunique()
        compound_pct = (compound_gvfks / 2043) * 100
        print(f"{'With compound-specific risk (Step 5)':<45} {compound_gvfks:<8,} {compound_pct:<10.1f}%")

    # Difference explanation
    if general_count > 0:
        reduction = general_count - compound_unique
        print(f"\nDifference Analysis ({general_count:,} → {compound_unique:,} sites):")
        print(f"- {reduction:,} sites excluded due to stricter compound-specific thresholds")
        print(f"- Main exclusions: Sites with PAH (30m), BTEX (50m), or other low-mobility compounds")


def generate_gvfk_risk_summary():
    """
    Generate a summary table of GVFKs at risk with compound breakdown.
    This should be called after run_step5() completes.
    """
    # Load compound results
    compound_file = get_output_path('step5_compound_detailed_combinations')
    if not os.path.exists(compound_file):
        print("No compound-specific results found. Run Step 5 first.")
        return None

    compound_df = pd.read_csv(compound_file)

    # Extract all unique GVFKs using consistent method
    all_gvfks = _extract_unique_gvfk_names(compound_df)

    if not all_gvfks:
        print("Warning: No GVFKs found in compound results")
        return None

    # Create GVFK summary
    gvfk_summary = []

    # Process each GVFK
    for gvfk in all_gvfks:
        # Find all rows that reference this GVFK
        gvfk_rows = []

        # Check in All_Affected_GVFKs
        if 'All_Affected_GVFKs' in compound_df.columns:
            for idx, row in compound_df.iterrows():
                gvfk_list = str(row.get('All_Affected_GVFKs', ''))
                if gvfk_list and gvfk_list != 'nan':
                    gvfks = [g.strip() for g in gvfk_list.split(';') if g.strip()]
                    if gvfk in gvfks:
                        gvfk_rows.append(row)

        # If nothing found, check Closest_GVFK
        if not gvfk_rows and 'Closest_GVFK' in compound_df.columns:
            gvfk_data = compound_df[compound_df['Closest_GVFK'] == gvfk]
            gvfk_rows = [row for _, row in gvfk_data.iterrows()]

        if gvfk_rows:
            # Convert to DataFrame for easier processing
            gvfk_data = pd.DataFrame(gvfk_rows)

            # Count sites and categories
            category_counts = gvfk_data['Qualifying_Category'].value_counts()
            unique_sites = gvfk_data['Lokalitet_ID'].nunique()

            summary_row = {
                'GVFK': gvfk,
                'Total_Sites': unique_sites,
                'Total_Combinations': len(gvfk_data)
            }

            # Add counts for each category
            for category in category_counts.index:
                summary_row[category] = category_counts[category]

            gvfk_summary.append(summary_row)

    # Convert to DataFrame and sort
    if gvfk_summary:
        gvfk_df = pd.DataFrame(gvfk_summary).fillna(0)
        gvfk_df = gvfk_df.sort_values('Total_Sites', ascending=False)

        # Save to CSV
        output_path = get_output_path('step5_gvfk_risk_summary')
        gvfk_df.to_csv(output_path, index=False)

        print(f"\n✓ GVFK risk summary saved: {output_path}")
        print(f"  Total GVFKs at risk: {len(gvfk_df)}")
        print(f"  Top 5 GVFKs by site count: {', '.join(gvfk_df.head()['GVFK'].tolist())}")

        return gvfk_df

    return None


def handle_unknown_substance_sites(sites_without_substances):
    """
    Handle sites without substance data separately.
    These sites are "parked" for separate analysis.

    Args:
        sites_without_substances (DataFrame): Sites without substance data

    Returns:
        DataFrame: Sites without substances (unchanged, just documented)
    """
    if sites_without_substances.empty:
        print("No sites without substance data found.")
        return sites_without_substances

    print(f"\nUnknown Substance Sites Analysis:")
    print(f"  Total sites without substance data: {len(sites_without_substances)}")

    # Save these sites separately
    if len(sites_without_substances) > 0:
        unknown_path = get_output_path('step5_unknown_substance_sites')
        sites_without_substances.to_csv(unknown_path, index=False)
        print(f"  ✓ Saved to: {unknown_path}")

        # Basic statistics
        if 'Final_Distance_m' in sites_without_substances.columns:
            mean_dist = sites_without_substances['Final_Distance_m'].mean()
            median_dist = sites_without_substances['Final_Distance_m'].median()
            within_500m = (sites_without_substances['Final_Distance_m'] <= 500).sum()
            print(f"  Distance statistics: mean={mean_dist:.0f}m, median={median_dist:.0f}m")
            print(f"  Sites within 500m: {within_500m} ({within_500m/len(sites_without_substances)*100:.1f}%)")

        # Branch information if available
        if 'Lokalitetensbranche' in sites_without_substances.columns:
            branches = sites_without_substances['Lokalitetensbranche'].value_counts()
            print(f"  Top branches: {', '.join(branches.head(3).index.tolist())}")

    return sites_without_substances