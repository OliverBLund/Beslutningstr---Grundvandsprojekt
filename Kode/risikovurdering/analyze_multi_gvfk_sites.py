"""
Analyze and visualize sites that cause the GVFK increase due to one-to-many relationships.

This script identifies:
1. Sites that exist in multiple GVFKs
2. GVFKs that likely appeared due to "secondary associations" (non-minimum distances)
3. Creates an interactive map showing these multi-GVFK scenarios
"""

import pandas as pd
import geopandas as gpd
import numpy as np
from pathlib import Path
import sys

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).resolve().parents[1]))
from config import get_output_path, GRUNDVAND_PATH, RIVERS_PATH, RESULTS_DIR

print("="*80)
print("MULTI-GVFK SITE ANALYSIS")
print("="*80)
print("\nAnalyzing sites that cause the one-to-many GVFK increase...\n")

# ============================================================================
# PHASE 1: Load and prepare data
# ============================================================================
print("[PHASE 1] Loading Step 5b compound-specific data...")
step5b_data = pd.read_csv(get_output_path('step5_compound_detailed_combinations'))
print(f"  Loaded {len(step5b_data)} site-GVFK-substance combinations")
print(f"  → {step5b_data['Lokalitet_ID'].nunique()} unique sites")
print(f"  → {step5b_data['GVFK'].nunique()} unique GVFKs")

# ============================================================================
# PHASE 2: Calculate minimum distance per site and identify multi-GVFK sites
# ============================================================================
print("\n[PHASE 2] Calculating minimum distances per site...")

# For each site, find the minimum distance across all its GVFK associations
site_min_distances = (
    step5b_data.groupby('Lokalitet_ID')['Distance_to_River_m']
    .min()
    .reset_index()
    .rename(columns={'Distance_to_River_m': 'Min_Distance_m'})
)

# Merge back to add Is_Min_Distance flag
step5b_data = step5b_data.merge(site_min_distances, on='Lokalitet_ID', how='left')
step5b_data['Is_Min_Distance'] = (
    step5b_data['Distance_to_River_m'] == step5b_data['Min_Distance_m']
)

print(f"  Added Is_Min_Distance flag to all combinations")

# Count how many GVFKs each site is associated with
site_gvfk_counts = (
    step5b_data.groupby('Lokalitet_ID')['GVFK']
    .nunique()
    .reset_index()
    .rename(columns={'GVFK': 'GVFK_Count'})
)

# Identify multi-GVFK sites (sites in 2+ GVFKs)
multi_gvfk_sites = site_gvfk_counts[site_gvfk_counts['GVFK_Count'] > 1]['Lokalitet_ID'].tolist()

print(f"\n  Sites by GVFK count:")
print(f"    1 GVFK:  {len(site_gvfk_counts[site_gvfk_counts['GVFK_Count'] == 1])} sites")
print(f"    2 GVFKs: {len(site_gvfk_counts[site_gvfk_counts['GVFK_Count'] == 2])} sites")
print(f"    3 GVFKs: {len(site_gvfk_counts[site_gvfk_counts['GVFK_Count'] == 3])} sites")
print(f"    4+ GVFKs: {len(site_gvfk_counts[site_gvfk_counts['GVFK_Count'] >= 4])} sites")
print(f"  → Total multi-GVFK sites: {len(multi_gvfk_sites)}")

# ============================================================================
# PHASE 3: Identify "secondary association" GVFKs
# ============================================================================
print("\n[PHASE 3] Identifying secondary association GVFKs...")

# For each GVFK, count how many sites have it as their minimum distance GVFK
gvfk_analysis = []

for gvfk in step5b_data['GVFK'].unique():
    gvfk_data = step5b_data[step5b_data['GVFK'] == gvfk]

    # Get unique sites in this GVFK
    unique_sites = gvfk_data['Lokalitet_ID'].nunique()

    # Count how many are minimum distance sites vs secondary
    min_dist_sites = gvfk_data[gvfk_data['Is_Min_Distance'] == True]['Lokalitet_ID'].nunique()
    secondary_sites = unique_sites - min_dist_sites

    # Calculate percentage of sites that are secondary associations
    secondary_pct = (secondary_sites / unique_sites * 100) if unique_sites > 0 else 0

    gvfk_analysis.append({
        'GVFK': gvfk,
        'Total_Sites': unique_sites,
        'Min_Distance_Sites': min_dist_sites,
        'Secondary_Sites': secondary_sites,
        'Secondary_Percentage': secondary_pct
    })

gvfk_analysis_df = pd.DataFrame(gvfk_analysis).sort_values('Secondary_Percentage', ascending=False)

# Identify likely "secondary association GVFKs" (high percentage of secondary sites)
# These are GVFKs that likely wouldn't appear under the old minimum-distance-only approach
secondary_gvfks = gvfk_analysis_df[gvfk_analysis_df['Secondary_Percentage'] >= 50.0]

print(f"\n  GVFKs by association type:")
print(f"    Primary GVFKs (>50% min-distance sites): {len(gvfk_analysis_df) - len(secondary_gvfks)}")
print(f"    Secondary GVFKs (≥50% secondary sites): {len(secondary_gvfks)}")

print(f"\n  Top 10 GVFKs with highest secondary site percentage:")
print(secondary_gvfks.head(10).to_string(index=False))

# Save analysis results
analysis_path = RESULTS_DIR / 'step5b_gvfk_association_analysis.csv'
gvfk_analysis_df.to_csv(analysis_path, index=False, encoding="utf-8")
print(f"\n  Saved GVFK analysis to: {analysis_path}")

# ============================================================================
# PHASE 4: Prepare data for visualization
# ============================================================================
print("\n[PHASE 4] Preparing data for interactive map...")

# Filter to multi-GVFK sites only
multi_gvfk_data = step5b_data[step5b_data['Lokalitet_ID'].isin(multi_gvfk_sites)].copy()

print(f"  Multi-GVFK sites: {len(multi_gvfk_sites)}")
print(f"  Multi-GVFK combinations: {len(multi_gvfk_data)}")
print(f"  GVFKs involved: {multi_gvfk_data['GVFK'].nunique()}")

# Deduplicate site-GVFK combinations (multiple substances per combo)
multi_gvfk_unique = multi_gvfk_data.drop_duplicates(subset=['Lokalitet_ID', 'GVFK'])

print(f"  Unique site-GVFK pairs: {len(multi_gvfk_unique)}")

# Save multi-GVFK site list
multi_gvfk_summary = multi_gvfk_unique.groupby('Lokalitet_ID').agg({
    'GVFK': lambda x: ', '.join(sorted(x.tolist())),
    'Distance_to_River_m': ['min', 'max', 'count'],
    'Is_Min_Distance': 'sum'
}).reset_index()

multi_gvfk_summary.columns = ['Lokalitet_ID', 'Associated_GVFKs', 'Min_Distance_m', 'Max_Distance_m', 'GVFK_Count', 'Min_Distance_GVFK_Count']
sites_path = RESULTS_DIR / 'step5b_multi_gvfk_sites.csv'
multi_gvfk_summary.to_csv(sites_path, index=False, encoding="utf-8")
print(f"  Saved multi-GVFK site summary to: {sites_path}")

# ============================================================================
# PHASE 5: Load geometries and create interactive map
# ============================================================================
print("\n[PHASE 5] Creating interactive map...")

# Load spatial data
print("  Loading spatial data...")
gvfk_polygons = gpd.read_file(GRUNDVAND_PATH)
rivers = gpd.read_file(RIVERS_PATH)
rivers_with_contact = rivers[rivers['Kontakt'] == 1]

# Load site geometries from Step 4
step4_geometries = gpd.read_file(get_output_path('unique_lokalitet_distances_shp'))

# Shapefile truncates column names to 10 chars - 'Lokalitetsnr' becomes 'Lokalitets'
id_col = 'Lokalitets' if 'Lokalitets' in step4_geometries.columns else 'Lokalitetsnr'

# Filter to multi-GVFK sites
multi_gvfk_site_ids = multi_gvfk_sites
multi_gvfk_geometries = step4_geometries[step4_geometries[id_col].isin(multi_gvfk_site_ids)].copy()

print(f"  Loaded geometries for {len(multi_gvfk_geometries)} multi-GVFK sites")

# Get relevant GVFKs and rivers
relevant_gvfks = multi_gvfk_data['GVFK'].unique()
relevant_gvfk_polygons = gvfk_polygons[gvfk_polygons['Navn'].isin(relevant_gvfks)]
relevant_rivers = rivers_with_contact[rivers_with_contact['GVForekom'].isin(relevant_gvfks)]

print(f"  Relevant GVFKs: {len(relevant_gvfk_polygons)}")
print(f"  Relevant river segments: {len(relevant_rivers)}")

# Create a modified version of the site geometries with multi-GVFK info
multi_gvfk_geometries = multi_gvfk_geometries.rename(columns={id_col: 'Lokalitet_'})

# Add GVFK associations from step5b data
# For each site geometry, we need to duplicate it for each GVFK association
expanded_geometries = []

for _, site in multi_gvfk_geometries.iterrows():
    site_id = site['Lokalitet_']
    site_gvfk_data = multi_gvfk_unique[multi_gvfk_unique['Lokalitet_ID'] == site_id]

    for _, gvfk_row in site_gvfk_data.iterrows():
        site_copy = site.copy()
        site_copy['Navn'] = gvfk_row['GVFK']
        site_copy['Distance_m'] = gvfk_row['Distance_to_River_m']
        site_copy['Is_Min_Dist'] = gvfk_row['Is_Min_Distance']
        site_copy['Min_Dist_m'] = gvfk_row['Min_Distance_m']
        expanded_geometries.append(site_copy)

expanded_geometries_gdf = gpd.GeoDataFrame(expanded_geometries, crs=multi_gvfk_geometries.crs)

print(f"  Created {len(expanded_geometries_gdf)} site-GVFK geometry combinations")

# Prepare results for distance line drawing
distance_results = multi_gvfk_unique[['Lokalitet_ID', 'GVFK', 'Distance_to_River_m', 'Is_Min_Distance']].copy()

# Now use the existing create_interactive_map function
print("\n  Generating interactive map...")
from optional_analysis.create_interactive_map import create_map

create_map(
    v1v2_with_distances=expanded_geometries_gdf,
    rivers_with_contact=relevant_rivers,
    valid_results=distance_results,
    gvfk_polygons=relevant_gvfk_polygons
)

print("\n[OK] Interactive map created!")
print(f"Map file: {get_output_path('interactive_distance_map')}")
print("\nThe map shows:")
print("  - Sites that exist in multiple GVFKs (multi-GVFK sites)")
print("  - All GVFK associations for each site")
print("  - Minimum distance connections (red lines)")
print("  - Secondary distance connections (orange lines)")
print("  - River segments within each GVFK")

print("\n" + "="*80)
print("ANALYSIS COMPLETE")
print("="*80)
