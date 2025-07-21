import geopandas as gpd
import pandas as pd
import os
import warnings
from shapely.errors import ShapelyDeprecationWarning

# Suppress shapely deprecation warnings
warnings.filterwarnings("ignore", category=ShapelyDeprecationWarning)

# Define paths to the input shapefiles
BASE_PATH = os.path.join(".", "Data", "shp files")
GRUNDVAND_PATH = os.path.join(BASE_PATH, "VP3Genbesøg_grundvand_geometri.shp")
RIVERS_PATH = os.path.join(BASE_PATH, "Rivers_gvf_rev20230825_kontakt.shp")
V1_PATH = os.path.join(BASE_PATH, "V1_gvfk_forurening.shp")
V2_PATH = os.path.join(BASE_PATH, "V2_gvfk_forurening.shp")

# Create output directory
RESULTS_PATH = os.path.join(".", "Resultater")
SKIP_STEP2_PATH = os.path.join(RESULTS_PATH, "Extra_Analysis_Skip_Step2")
os.makedirs(SKIP_STEP2_PATH, exist_ok=True)

def skip_step2_analysis():
    """
    Extra analysis: Skip step 2 and directly find how many GVFKs contain V1/V2 sites
    without filtering for river contact first.
    """
    print("\n=== EXTRA ANALYSIS: Skipping Step 2 (River Contact Filter) ===")
    print("This analysis shows how many GVFKs have V1/V2 sites without restricting to those with river contact.")
    
    # Get all GVFKs from step 1
    print("Loading all GVFK polygons...")
    gvf = gpd.read_file(GRUNDVAND_PATH)
    print(f"Starting with all {len(gvf)} GVFK polygons")
    
    # Read V1 and V2 shapefiles
    print("Loading V1 and V2 polygon files...")
    v1 = gpd.read_file(V1_PATH)
    v2 = gpd.read_file(V2_PATH)
    
    # Print initial counts
    print(f"Initial V1 polygons: {len(v1)}")
    print(f"Initial V2 polygons: {len(v2)}")
    
    # Ensure all geometries use the same CRS
    target_crs = gvf.crs
    if v1.crs != target_crs:
        v1 = v1.to_crs(target_crs)
    if v2.crs != target_crs:
        v2 = v2.to_crs(target_crs)
    
    # Find locality ID column
    id_column = 'Lokalitets'  # Default to this column
    if id_column not in v1.columns:
        # Try other possible names
        for col in ['Lokalitetsnr', 'LokNr', 'Lokalitet_']:
            if col in v1.columns:
                id_column = col
                break
        else:
            print("WARNING: No locality ID column found. Using index instead.")
            v1['TempID'] = v1.index.astype(str)
            v2['TempID'] = v2.index.astype(str)
            id_column = 'TempID'
    
    # Merge polygons with the same Lokalitetsnr
    print(f"\nMerging polygons for each unique {id_column}...")
    v1_merged = v1.dissolve(by=id_column, as_index=False) if id_column in v1.columns else v1.copy()
    v2_merged = v2.dissolve(by=id_column, as_index=False) if id_column in v2.columns else v2.copy()
    print(f"After merging:")
    print(f"V1 unique sites: {len(v1_merged)} (reduced from {len(v1)} polygons)")
    print(f"V2 unique sites: {len(v2_merged)} (reduced from {len(v2)} polygons)")
    
    print("\nPerforming spatial join to find V1/V2 polygons within GVFK polygons...")
    
    # Perform spatial join between merged V1/V2 polygons and all GVFK polygons
    v1_in_gvfk = gpd.sjoin(v1_merged, gvf, how='inner', predicate='intersects')
    v2_in_gvfk = gpd.sjoin(v2_merged, gvf, how='inner', predicate='intersects')
    print(f"Found {len(v1_in_gvfk)} V1 sites intersecting with GVFKs")
    print(f"Found {len(v2_in_gvfk)} V2 sites intersecting with GVFKs")
    
    # Save individual V1 and V2 results
    v1_in_gvfk.to_file(os.path.join(SKIP_STEP2_PATH, "v1_in_all_gvfk.shp"))
    v2_in_gvfk.to_file(os.path.join(SKIP_STEP2_PATH, "v2_in_all_gvfk.shp"))
    
    # Combine V1 and V2 results
    v1v2_combined = pd.concat([v1_in_gvfk, v2_in_gvfk], ignore_index=True)
    
    if not v1v2_combined.empty:
        print(f"Total V1/V2 polygons: {len(v1v2_combined)}")
        
        # IMPORTANT: Get unique GVFKs that contain V1/V2 sites BEFORE deduplication
        # This ensures we count all GVFKs that have any V1/V2 site
        all_gvfk_with_v1v2 = v1v2_combined['Navn'].unique()
        print(f"\nTotal GVFKs containing V1/V2 sites (without river contact filter): {len(all_gvfk_with_v1v2)}")
        
        # Deduplicate based on Lokalitetsnr for site counting (not for GVFK counting)
        if id_column in v1v2_combined.columns:
            v1v2_unique = v1v2_combined.drop_duplicates(subset=[id_column])
            print(f"Unique V1/V2 locations: {len(v1v2_unique)}")
        else:
            print("\nWarning: locality ID column not found. Cannot deduplicate locations.")
            v1v2_unique = v1v2_combined.copy()
        
        # Get the full GVFK polygons that contain V1/V2 sites
        gvfk_with_v1v2_polygons = gvf[gvf['Navn'].isin(all_gvfk_with_v1v2)]
        
        # Save shapefiles
        gvfk_with_v1v2_polygons.to_file(os.path.join(SKIP_STEP2_PATH, "all_gvfk_with_v1v2.shp"))
        v1v2_unique.to_file(os.path.join(SKIP_STEP2_PATH, "all_v1v2_sites_in_gvfk.shp"))
        
        # Save basic summary as CSV
        summary_data = {
            'Metric': [
                'Total GVFKs',
                'GVFKs with V1/V2 Sites (No River Filter)',
                'Percentage with V1/V2 Sites',
                'Total V1 Polygons in GVFKs',
                'Total V2 Polygons in GVFKs',
                'Total V1+V2 Polygons',
                'Unique V1/V2 Sites (by locality ID)'
            ],
            'Value': [
                len(gvf),
                len(all_gvfk_with_v1v2),
                f"{(len(all_gvfk_with_v1v2)/len(gvf)*100):.1f}%",
                len(v1_in_gvfk),
                len(v2_in_gvfk),
                len(v1v2_combined),
                len(v1v2_unique)
            ]
        }
        pd.DataFrame(summary_data).to_csv(os.path.join(SKIP_STEP2_PATH, "skip_step2_summary.csv"), index=False)
        
        # Get the river-contact GVFKs for comparison
        try:
            rivers = gpd.read_file(RIVERS_PATH)
            rivers_gvfk = [gvf for gvf in rivers["GVForekom"].unique() if gvf is not None and isinstance(gvf, str)]
            
            # Compare sets
            river_contact_gvfk_set = set(rivers_gvfk)
            all_gvfk_with_v1v2_set = set(all_gvfk_with_v1v2)
            
            # GVFKs with V1/V2 sites that don't have river contact
            gvfk_v1v2_no_river = all_gvfk_with_v1v2_set - river_contact_gvfk_set
            
            print(f"\nComparison between approaches:")
            print(f"GVFKs with river contact: {len(river_contact_gvfk_set)}")
            print(f"GVFKs with V1/V2 sites (no river filter): {len(all_gvfk_with_v1v2_set)}")
            print(f"GVFKs with V1/V2 sites that have river contact: {len(river_contact_gvfk_set & all_gvfk_with_v1v2_set)}")
            print(f"GVFKs with V1/V2 sites that don't have river contact: {len(gvfk_v1v2_no_river)}")
            
            # Save the comparison to CSV
            comparison_data = {
                'Approach': [
                    'A: GVFKs with River Contact',
                    'B: GVFKs with V1/V2 Sites (No River Filter)',
                    'C: GVFKs with V1/V2 Sites and River Contact (A ∩ B)',
                    'D: GVFKs with V1/V2 Sites but No River Contact (B - A)'
                ],
                'Count': [
                    len(river_contact_gvfk_set),
                    len(all_gvfk_with_v1v2_set),
                    len(river_contact_gvfk_set & all_gvfk_with_v1v2_set),
                    len(gvfk_v1v2_no_river)
                ]
            }
            pd.DataFrame(comparison_data).to_csv(os.path.join(SKIP_STEP2_PATH, "approach_comparison.csv"), index=False)
            
            # Save GVFKs with V1/V2 but no river contact
            if gvfk_v1v2_no_river:
                pd.DataFrame({'GVFK_Name': sorted(list(gvfk_v1v2_no_river))}).to_csv(
                    os.path.join(SKIP_STEP2_PATH, "v1v2_no_river.csv"), index=False)
            
            print(f"\nSaved approach comparison to {SKIP_STEP2_PATH}")
            
        except Exception as e:
            print(f"Error performing comparison: {e}")
        
        return all_gvfk_with_v1v2, v1v2_unique
    else:
        print("No V1/V2 polygons found within any GVFK polygons.")
        return [], None

def main():
    """
    Run the skip step 2 analysis as a standalone script.
    """
    print("Running Skip Step 2 Analysis")
    print("=" * 60)
    
    all_gvfk_with_v1v2, v1v2_unique = skip_step2_analysis()
    
    print("\n" + "=" * 60)
    print("SKIP STEP 2 ANALYSIS COMPLETE")
    print("=" * 60)
    print(f"Results saved to: {SKIP_STEP2_PATH}")

if __name__ == "__main__":
    main() 