import geopandas as gpd
import pandas as pd
import numpy as np
import os

# Define paths
BASE_PATH = os.path.join(".", "Data", "shp files")
RIVERS_PATH = os.path.join(BASE_PATH, "Rivers_gvf_rev20230825_kontakt.shp")
V1_PATH = os.path.join(BASE_PATH, "V1FLADER.shp")
V2_PATH = os.path.join(BASE_PATH, "V2FLADER.shp")

def verify_data_structure():
    """
    Verify the structure of V1/V2 and rivers files to understand GVFK columns.
    """
    print("=== DATA STRUCTURE VERIFICATION ===\n")
    
    # Load and examine V1 file
    print("V1 file structure:")
    v1 = gpd.read_file(V1_PATH)
    print(f"Columns: {list(v1.columns)}")
    print(f"Sample 'Navn' values: {v1['Navn'].head().tolist()}")
    print(f"Unique 'Navn' count: {v1['Navn'].nunique()}")
    print(f"Any null 'Navn' values: {v1['Navn'].isna().sum()}")
    print()
    
    # Load and examine V2 file
    print("V2 file structure:")
    v2 = gpd.read_file(V2_PATH)
    print(f"Columns: {list(v2.columns)}")
    print(f"Sample 'Navn' values: {v2['Navn'].head().tolist()}")
    print(f"Unique 'Navn' count: {v2['Navn'].nunique()}")
    print(f"Any null 'Navn' values: {v2['Navn'].isna().sum()}")
    print()
    
    # Load and examine rivers file
    print("Rivers file structure:")
    rivers = gpd.read_file(RIVERS_PATH)
    print(f"Columns: {list(rivers.columns)}")
    print(f"Sample 'GVForekom' values: {rivers['GVForekom'].head().tolist()}")
    print(f"Unique 'GVForekom' count: {rivers['GVForekom'].nunique()}")
    print(f"Any null 'GVForekom' values: {rivers['GVForekom'].isna().sum()}")
    print()
    
    # Check Kontakt column
    print("Kontakt column analysis:")
    kontakt_counts = rivers['Kontakt'].value_counts()
    print(f"Kontakt values: {kontakt_counts.to_dict()}")
    print()
    
    # Check overlap between V1/V2 GVFK names and river GVFK names
    v1_gvfks = set(v1['Navn'].dropna().unique())
    v2_gvfks = set(v2['Navn'].dropna().unique())
    river_gvfks = set(rivers['GVForekom'].dropna().unique())
    
    print("GVFK overlap analysis:")
    print(f"V1 unique GVFKs: {len(v1_gvfks)}")
    print(f"V2 unique GVFKs: {len(v2_gvfks)}")
    print(f"River unique GVFKs: {len(river_gvfks)}")
    print(f"V1 ∩ Rivers: {len(v1_gvfks & river_gvfks)}")
    print(f"V2 ∩ Rivers: {len(v2_gvfks & river_gvfks)}")
    print(f"(V1 ∪ V2) ∩ Rivers: {len((v1_gvfks | v2_gvfks) & river_gvfks)}")
    print()

def verify_distance_calculation_sample():
    """
    Manually verify distance calculations for a small sample.
    """
    print("=== DISTANCE CALCULATION SAMPLE VERIFICATION ===\n")
    
    # Load data
    v1 = gpd.read_file(V1_PATH)
    rivers = gpd.read_file(RIVERS_PATH)
    
    # Take a small sample from V1
    sample_v1 = v1.head(5).copy()
    
    # Filter rivers to those with contact
    rivers_contact = rivers[rivers['Kontakt'] == 1]
    
    print(f"Sample V1 sites for verification:")
    for idx, site in sample_v1.iterrows():
        gvfk = site['Navn']
        print(f"\nSite {idx}: GVFK = {gvfk}")
        
        # Find matching rivers
        matching_rivers = rivers_contact[rivers_contact['GVForekom'] == gvfk]
        print(f"  Found {len(matching_rivers)} matching rivers with Kontakt=1")
        
        if len(matching_rivers) > 0:
            # Calculate distance to first matching river
            first_river = matching_rivers.iloc[0]
            distance = site.geometry.distance(first_river.geometry)
            print(f"  Distance to first river: {distance:.2f} meters")
            print(f"  River GVFK: {first_river['GVForekom']}")
            print(f"  River Kontakt: {first_river['Kontakt']}")
        else:
            print(f"  No matching rivers found!")
            # Check if this GVFK exists at all in rivers
            any_rivers = rivers[rivers['GVForekom'] == gvfk]
            print(f"  Any rivers with this GVFK (regardless of Kontakt): {len(any_rivers)}")
            if len(any_rivers) > 0:
                kontakt_values = any_rivers['Kontakt'].value_counts()
                print(f"  Kontakt values for this GVFK: {kontakt_values.to_dict()}")

def check_spatial_join_vs_attribute():
    """
    Compare results from spatial join approach vs. using original V1/V2 attributes.
    """
    print("=== SPATIAL JOIN VS ATTRIBUTE COMPARISON ===\n")
    
    # Load data from workflow results
    try:
        distance_results = pd.read_csv(os.path.join("..", "Resultater", "step4_distance_results.csv"))
        print(f"Loaded {len(distance_results)} distance results from workflow")
        
        # Check the GVFK distribution
        gvfk_counts = distance_results['GVFK'].value_counts()
        print(f"Top 10 GVFKs by site count:")
        print(gvfk_counts.head(10))
        print()
        
        # Check distance distribution
        valid_distances = distance_results['Distance_to_River_m'].dropna()
        print(f"Distance statistics:")
        print(f"  Count: {len(valid_distances)}")
        print(f"  Min: {valid_distances.min():.2f}m")
        print(f"  Max: {valid_distances.max():.2f}m")
        print(f"  Mean: {valid_distances.mean():.2f}m")
        print(f"  Median: {valid_distances.median():.2f}m")
        print()
        
        # Check for suspiciously low distances
        very_close = valid_distances[valid_distances < 10]
        print(f"Sites with distance < 10m: {len(very_close)} ({len(very_close)/len(valid_distances)*100:.1f}%)")
        
        zero_distance = valid_distances[valid_distances == 0]
        print(f"Sites with exactly 0m distance: {len(zero_distance)}")
        
    except FileNotFoundError:
        print("No workflow results found. Run the main workflow first.")

def main():
    """
    Run all verification checks.
    """
    print("STEP 4 VERIFICATION SCRIPT")
    print("=" * 50)
    
    verify_data_structure()
    verify_distance_calculation_sample()
    check_spatial_join_vs_attribute()
    
    print("=" * 50)
    print("VERIFICATION COMPLETE")
    print("\nLook for these potential issues:")
    print("1. Mismatched GVFK names between V1/V2 and rivers files")
    print("2. Incorrect Kontakt filtering")
    print("3. CRS projection issues affecting distance calculations")
    print("4. Spatial join creating incorrect GVFK associations")

if __name__ == "__main__":
    main() 