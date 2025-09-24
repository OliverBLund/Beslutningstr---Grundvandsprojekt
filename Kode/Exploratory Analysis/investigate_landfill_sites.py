#!/usr/bin/env python3
"""
Investigate if branch-only sites could add new LOSSEPLADS qualifying sites.
"""

import pandas as pd
from config import get_output_path

def main():
    # Load Step 4 results
    step4_file = get_output_path('step4_final_distances_for_risk_assessment')
    df = pd.read_csv(step4_file)

    print(f'Total sites in Step 4: {len(df):,}')
    print(f'Sites within 500m: {(df["Final_Distance_m"] <= 500).sum():,}')

    # Separate sites with and without substances
    has_substances = (df['Lokalitetensstoffer'].notna() & 
                     (df['Lokalitetensstoffer'].astype(str).str.strip() != '') &
                     (df['Lokalitetensstoffer'].astype(str) != 'nan'))

    sites_with_substances = df[has_substances]
    sites_without_substances = df[~has_substances]

    print(f'\nSites WITH substances: {len(sites_with_substances):,}')
    print(f'  Within 500m: {(sites_with_substances["Final_Distance_m"] <= 500).sum():,}')

    print(f'\nSites WITHOUT substances: {len(sites_without_substances):,}')  
    print(f'  Within 500m: {(sites_without_substances["Final_Distance_m"] <= 500).sum():,}')

    # Get branch-only sites within 500m
    branch_only_500m = df[(~has_substances) & (df['Final_Distance_m'] <= 500)]
    print(f'\nBranch-only sites within 500m: {len(branch_only_500m):,}')

    # Check for landfill keywords
    landfill_keywords = ['losseplads', 'affald', 'deponi', 'fyld', 'skraldeplads']

    def contains_landfill_terms(text):
        if pd.isna(text):
            return False
        text_lower = str(text).lower()
        return any(keyword in text_lower for keyword in landfill_keywords)

    # Check branch data for landfill terms
    landfill_branch = branch_only_500m[branch_only_500m['Lokalitetensbranche'].apply(contains_landfill_terms)]
    print(f'\nPotential landfill sites by BRANCH: {len(landfill_branch):,}')

    # Check activity data for landfill terms  
    landfill_activity = branch_only_500m[branch_only_500m['Lokalitetensaktivitet'].apply(contains_landfill_terms)]
    print(f'Potential landfill sites by ACTIVITY: {len(landfill_activity):,}')

    # Combined (either branch OR activity has landfill terms)
    landfill_combined = branch_only_500m[
        branch_only_500m['Lokalitetensbranche'].apply(contains_landfill_terms) |
        branch_only_500m['Lokalitetensaktivitet'].apply(contains_landfill_terms)
    ]
    print(f'Total potential landfill sites (branch OR activity): {len(landfill_combined):,}')

    # Show examples if any found
    if len(landfill_combined) > 0:
        print(f'\n=== SAMPLE LANDFILL SITES ===')
        for i, (_, row) in enumerate(landfill_combined.head(5).iterrows()):
            print(f'{i+1}. Lokalitet_ID: {row["Lokalitet_ID"]}')
            print(f'   Branch: {row["Lokalitetensbranche"]}')
            print(f'   Activity: {row["Lokalitetensaktivitet"]}')
            print(f'   Distance: {row["Final_Distance_m"]:.0f}m')
            print(f'   GVFK: {row["Closest_GVFK"]}')
            print()
        
        # Show branch/activity breakdown
        print(f'=== LANDFILL BRANCH BREAKDOWN ===')
        branch_counts = {}
        for _, row in landfill_combined.iterrows():
            if pd.notna(row['Lokalitetensbranche']):
                branches = str(row['Lokalitetensbranche']).split(';')
                for branch in branches:
                    branch = branch.strip()
                    if any(kw in branch.lower() for kw in landfill_keywords):
                        branch_counts[branch] = branch_counts.get(branch, 0) + 1
        
        for branch, count in sorted(branch_counts.items(), key=lambda x: x[1], reverse=True)[:10]:
            print(f'  {branch}: {count:,} sites')
            
        print(f'\n=== LANDFILL ACTIVITY BREAKDOWN ===') 
        activity_counts = {}
        for _, row in landfill_combined.iterrows():
            if pd.notna(row['Lokalitetensaktivitet']):
                activities = str(row['Lokalitetensaktivitet']).split(';')
                for activity in activities:
                    activity = activity.strip()
                    if any(kw in activity.lower() for kw in landfill_keywords):
                        activity_counts[activity] = activity_counts.get(activity, 0) + 1
        
        for activity, count in sorted(activity_counts.items(), key=lambda x: x[1], reverse=True)[:10]:
            print(f'  {activity}: {count:,} sites')
    
    print(f'\n=== CONCLUSION ===')
    print(f'Current substance-only sites ≤500m: {(sites_with_substances["Final_Distance_m"] <= 500).sum():,}')
    print(f'Potential additional landfill sites: {len(landfill_combined):,}')
    total_potential = (sites_with_substances["Final_Distance_m"] <= 500).sum() + len(landfill_combined)
    print(f'Total potential qualifying sites: {total_potential:,}')
    
    if len(landfill_combined) > 0:
        increase = len(landfill_combined) / (sites_with_substances["Final_Distance_m"] <= 500).sum() * 100
        print(f'Potential increase: +{increase:.1f}%')
    
if __name__ == "__main__":
    main()