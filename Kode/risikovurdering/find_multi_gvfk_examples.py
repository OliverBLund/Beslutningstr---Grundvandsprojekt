"""
Find clear examples of sites that add multiple GVFKs.

This script identifies specific sites that exist in 2+ GVFKs and shows
how ONE site can cause multiple GVFKs to appear in the final results.
"""

import pandas as pd
import geopandas as gpd
from pathlib import Path
import sys

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).resolve().parents[1]))
from config import get_output_path, GRUNDVAND_PATH, RIVERS_PATH, RESULTS_DIR

print("="*80)
print("FINDING MULTI-GVFK SITE EXAMPLES")
print("="*80)

# Load Step 5b data
print("\nLoading Step 5b data...")
step5b_data = pd.read_csv(get_output_path('step5_compound_detailed_combinations'))

# Calculate minimum distance per site
site_min_distances = (
    step5b_data.groupby('Lokalitet_ID')['Distance_to_River_m']
    .min()
    .reset_index()
    .rename(columns={'Distance_to_River_m': 'Min_Distance_m'})
)

step5b_data = step5b_data.merge(site_min_distances, on='Lokalitet_ID', how='left')
step5b_data['Is_Min_Distance'] = (
    step5b_data['Distance_to_River_m'] == step5b_data['Min_Distance_m']
)

# Get unique site-GVFK pairs
site_gvfk_pairs = step5b_data[['Lokalitet_ID', 'GVFK', 'Distance_to_River_m', 'Is_Min_Distance']].drop_duplicates()

# Find sites in multiple GVFKs
site_gvfk_counts = site_gvfk_pairs.groupby('Lokalitet_ID').size().reset_index(name='GVFK_Count')
multi_gvfk_sites = site_gvfk_counts[site_gvfk_counts['GVFK_Count'] >= 2].sort_values('GVFK_Count', ascending=False)

print(f"\nFound {len(multi_gvfk_sites)} sites in 2+ GVFKs")
print(f"  Sites in 2 GVFKs: {len(multi_gvfk_sites[multi_gvfk_sites['GVFK_Count'] == 2])}")
print(f"  Sites in 3 GVFKs: {len(multi_gvfk_sites[multi_gvfk_sites['GVFK_Count'] == 3])}")
print(f"  Sites in 4+ GVFKs: {len(multi_gvfk_sites[multi_gvfk_sites['GVFK_Count'] >= 4])}")

# Show detailed examples
print("\n" + "="*80)
print("EXAMPLE CASES: Sites Adding Multiple GVFKs")
print("="*80)

examples = []

# Get top 10 examples (prefer sites with 3 GVFKs for clearest demonstration)
for site_id in multi_gvfk_sites.head(15)['Lokalitet_ID']:
    site_data = site_gvfk_pairs[site_gvfk_pairs['Lokalitet_ID'] == site_id].sort_values('Distance_to_River_m')

    gvfks = site_data['GVFK'].tolist()
    distances = site_data['Distance_to_River_m'].tolist()
    is_min = site_data['Is_Min_Distance'].tolist()

    # Get substance info
    site_substances = step5b_data[step5b_data['Lokalitet_ID'] == site_id]['Qualifying_Category'].unique()

    example = {
        'Site_ID': site_id,
        'GVFK_Count': len(gvfks),
        'GVFKs': ', '.join(gvfks),
        'Distances_m': ', '.join([f"{d:.1f}" for d in distances]),
        'Min_Distance_m': min(distances),
        'Max_Distance_m': max(distances),
        'Substances': ', '.join(site_substances[:3]) + ('...' if len(site_substances) > 3 else ''),
        'GVFK_Details': []
    }

    for i, (gvfk, dist, is_minimum) in enumerate(zip(gvfks, distances, is_min), 1):
        example['GVFK_Details'].append({
            'GVFK': gvfk,
            'Distance_m': dist,
            'Is_Primary': is_minimum,
            'Type': 'PRIMARY (minimum)' if is_minimum else 'SECONDARY'
        })

    examples.append(example)

# Display examples
print("\nShowing top 10 examples:\n")

for i, ex in enumerate(examples[:10], 1):
    print(f"\nEXAMPLE {i}: Site {ex['Site_ID']}")
    print(f"  This ONE site affects {ex['GVFK_Count']} different GVFKs!")
    print(f"  Substances: {ex['Substances']}")
    print(f"  Distance range: {ex['Min_Distance_m']:.1f}m - {ex['Max_Distance_m']:.1f}m")
    print(f"\n  GVFK Associations:")
    for detail in ex['GVFK_Details']:
        marker = "★" if detail['Is_Primary'] else "○"
        print(f"    {marker} {detail['GVFK']}: {detail['Distance_m']:.1f}m ({detail['Type']})")
    print(f"\n  → Old approach: Only 1 GVFK counted (the primary/minimum)")
    print(f"  → New approach: ALL {ex['GVFK_Count']} GVFKs counted")
    print(f"  → Net increase: +{ex['GVFK_Count'] - 1} GVFK(s) from this single site")

# Save detailed examples
examples_df = pd.DataFrame([
    {
        'Site_ID': ex['Site_ID'],
        'GVFK_Count': ex['GVFK_Count'],
        'GVFKs': ex['GVFKs'],
        'Min_Distance_m': ex['Min_Distance_m'],
        'Max_Distance_m': ex['Max_Distance_m'],
        'Substances': ex['Substances'],
        'Net_GVFK_Increase': ex['GVFK_Count'] - 1
    }
    for ex in examples
])

examples_path = RESULTS_DIR / 'multi_gvfk_examples.csv'
examples_df.to_csv(examples_path, index=False)
print(f"\n\nSaved detailed examples to: {examples_path}")

# Calculate total theoretical GVFK increase from multi-GVFK sites
total_extra_gvfks = (multi_gvfk_sites['GVFK_Count'] - 1).sum()
print(f"\n" + "="*80)
print(f"SUMMARY")
print("="*80)
print(f"Total multi-GVFK sites: {len(multi_gvfk_sites)}")
print(f"Theoretical max GVFK increase from multi-GVFK sites: +{total_extra_gvfks}")
print(f"  (Each site contributes GVFK_Count - 1 to the increase)")
print(f"\nActual GVFK increase observed: +22 (from 218 to 240)")
print(f"\nNote: Not all secondary GVFKs are 'new' - some may have had")
print(f"other sites as their primary association already.")

# Now create a focused map on just 2-3 good examples
print(f"\n" + "="*80)
print("Creating focused map for best examples...")
print("="*80)

# Pick 3 good examples: one with 2 GVFKs, one with 3 GVFKs
example_sites = []
if len([ex for ex in examples if ex['GVFK_Count'] == 2]) > 0:
    example_sites.append([ex for ex in examples if ex['GVFK_Count'] == 2][0]['Site_ID'])
if len([ex for ex in examples if ex['GVFK_Count'] == 3]) > 0:
    example_sites.append([ex for ex in examples if ex['GVFK_Count'] == 3][0]['Site_ID'])
if len(example_sites) < 3 and len(examples) > 0:
    example_sites.append(examples[0]['Site_ID'])

print(f"\nCreating map for example sites: {example_sites}")

# Filter data to these examples only
example_data = site_gvfk_pairs[site_gvfk_pairs['Lokalitet_ID'].isin(example_sites)]
example_gvfks = example_data['GVFK'].unique()

print(f"  {len(example_sites)} sites")
print(f"  {len(example_gvfks)} GVFKs involved")

# Load geometries
print("\nLoading geometries...")
step4_geometries = gpd.read_file(get_output_path('unique_lokalitet_distances_shp'))
gvfk_polygons = gpd.read_file(GRUNDVAND_PATH)
rivers = gpd.read_file(RIVERS_PATH)
rivers_with_contact = rivers[rivers['Kontakt'] == 1]

# Get geometries for example sites
id_col = 'Lokalitets' if 'Lokalitets' in step4_geometries.columns else 'Lokalitetsnr'
example_geometries = step4_geometries[step4_geometries[id_col].isin(example_sites)].copy()
example_geometries = example_geometries.rename(columns={id_col: 'Lokalitet_'})

# Get GVFKs and rivers for these examples
example_gvfk_polygons = gvfk_polygons[gvfk_polygons['Navn'].isin(example_gvfks)]
example_rivers = rivers_with_contact[rivers_with_contact['GVForekom'].isin(example_gvfks)]

print(f"  Loaded {len(example_geometries)} site geometries")
print(f"  Loaded {len(example_gvfk_polygons)} GVFK polygons")
print(f"  Loaded {len(example_rivers)} river segments")

# Expand geometries for each GVFK association
expanded_geometries = []
for _, site in example_geometries.iterrows():
    site_id = site['Lokalitet_']
    site_gvfk_data = example_data[example_data['Lokalitet_ID'] == site_id]

    for _, gvfk_row in site_gvfk_data.iterrows():
        site_copy = site.copy()
        site_copy['Navn'] = gvfk_row['GVFK']
        site_copy['Distance_m'] = gvfk_row['Distance_to_River_m']
        site_copy['Is_Min_Dist'] = gvfk_row['Is_Min_Distance']
        site_copy['Min_Dist_m'] = gvfk_row['Distance_to_River_m'] if gvfk_row['Is_Min_Distance'] else None
        expanded_geometries.append(site_copy)

expanded_geometries_gdf = gpd.GeoDataFrame(expanded_geometries, crs=example_geometries.crs)

# Create map
print("\nGenerating interactive map...")
from optional_analysis.create_interactive_map import create_map

create_map(
    v1v2_with_distances=expanded_geometries_gdf,
    rivers_with_contact=example_rivers,
    valid_results=example_data,
    gvfk_polygons=example_gvfk_polygons
)

print("\n✓ Focused map created!")
print(f"  Open: {get_output_path('interactive_distance_map')}")
print(f"\nThis map shows {len(example_sites)} clear examples where ONE site affects MULTIPLE GVFKs")
print(f"  - Red lines = PRIMARY association (minimum distance)")
print(f"  - Orange lines = SECONDARY associations (cause the GVFK increase)")

print("\n" + "="*80)
print("ANALYSIS COMPLETE")
print("="*80)
