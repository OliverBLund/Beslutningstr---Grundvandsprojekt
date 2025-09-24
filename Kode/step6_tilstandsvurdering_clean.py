"""
Step 6: Tilstandsvurdering (State Assessment)
===========================================

Calculates pollution flux using the formula: J = A × C × I

Where:
- A = Area of contamination site (from Step 3 geometries)
- C = Standard concentration by contamination category  
- I = Raster value from GVD files based on DK-modellag
"""

import pandas as pd
import geopandas as gpd
import rasterio
import os
import numpy as np
from config import get_output_path, ensure_results_directory
from step6_visualizations import analyze_and_visualize_step6

# Standard concentrations (C) by contamination category [μg/L]
# Converted from literature values in mg/L to μg/L (multiply by 1000)
STANDARD_CONCENTRATIONS = {
    'LOSSEPLADS': 1000.0,                    # 1.0 mg/L → 1000 μg/L
    'PAH_FORBINDELSER': 2000.0,              # 2.0 mg/L → 2000 μg/L       
    'BTXER': 1500.0,                         # 1.5 mg/L → 1500 μg/L       
    'PHENOLER': 1200.0,                      # 1.2 mg/L → 1200 μg/L    
    'UORGANISKE_FORBINDELSER': 1800.0,       # 1.8 mg/L → 1800 μg/L
    'POLARE_FORBINDELSER': 1300.0,           # 1.3 mg/L → 1300 μg/L      
    'KLOREREDE_OPLØSNINGSMIDLER': 2500.0,    # 2.5 mg/L → 2500 μg/L
    'PESTICIDER': 800.0,                     # 0.8 mg/L → 800 μg/L  
    'ANDRE': 1000.0,                         # 1.0 mg/L → 1000 μg/L
    'KLOREDE_KULBRINTER': 2200.0             # 2.2 mg/L → 2200 μg/L        
}

# File paths
GVFK_LAYER_MAPPING_PATH = r"C:\Users\s194420\OneDrive - Danmarks Tekniske Universitet\Poul Løgstrup Bjergs filer - Work_Projects_Oliver Lund\Beslutningstræ - Grundvands projekt\Data\vp3_h1_grundvandsforekomster_VP3Genbesøg.csv"
GVD_RASTER_PATH = r"C:\Users\s194420\OneDrive - Danmarks Tekniske Universitet\Poul Løgstrup Bjergs filer - Work_Projects_Oliver Lund\Beslutningstræ - Grundvands projekt\Data\dkm2019_vp3_GVD"

def run_step6():
    """Execute Step 6: Calculate pollution flux for qualified sites."""
    print("Step 6: Tilstandsvurdering - Calculating pollution flux (J = A × C × I)")
    
    ensure_results_directory()
    
    # 1. Load Step 5 qualified sites
    step5_file = get_output_path('step5_compound_detailed_combinations')
    qualified_sites = pd.read_csv(step5_file)
    print(f"Loaded {len(qualified_sites):,} qualified combinations")
    
    # 2. Load GVFK to layer mapping
    gvfk_mapping = pd.read_csv(GVFK_LAYER_MAPPING_PATH, sep=';', encoding='latin-1')
    print(f"Loaded {len(gvfk_mapping):,} GVFK mappings")
    
    # 3. Match sites with layers
    sites_with_layers = qualified_sites.merge(
        gvfk_mapping[['GVForekom', 'DK-modellag']], 
        left_on='Closest_GVFK', 
        right_on='GVForekom', 
        how='left'
    )
    print(f"Matched {sites_with_layers['DK-modellag'].notna().sum():,} sites to layers")
    
    # 4. Calculate areas from Step 3 geometries
    step3_geometries = gpd.read_file(get_output_path('step3_v1v2_sites'))
    step3_geometries['Area_m2'] = step3_geometries.geometry.area
    area_lookup = dict(zip(step3_geometries['Lokalitet_'], step3_geometries['Area_m2']))
    sites_with_layers['Area_m2'] = sites_with_layers['Lokalitet_ID'].map(area_lookup)
    sites_with_layers = sites_with_layers.copy()
    sites_with_layers.loc[:, 'Area_m2'] = sites_with_layers['Area_m2'].fillna(1000.0)
    print(f"Calculated areas: Mean={sites_with_layers['Area_m2'].mean():.0f}m²")
    
    # 5. Sample raster I values
    sites_with_layers['I_Value'] = sites_with_layers['DK-modellag'].apply(_get_i_value)
    print(f"Sampled I values: Mean={sites_with_layers['I_Value'].mean():.3f}")
    
    # 6. Calculate flux J = A × C × I with proper units
    sites_with_layers['Standard_Concentration_ug_L'] = sites_with_layers['Qualifying_Category'].map(STANDARD_CONCENTRATIONS)
    
    # Calculate base flux: A (m²) × C (μg/L) × I (mm/år) = μg/år
    # Note: mm/år = 0.001 m/år, μg/L = μg/(0.001 m³) = 1000 μg/m³
    # So: m² × 1000 μg/m³ × 0.001 m/år = μg/år
    sites_with_layers['Pollution_Flux_ug_per_year'] = (
        sites_with_layers['Area_m2'] * 
        sites_with_layers['Standard_Concentration_ug_L'] * 
        sites_with_layers['I_Value']
    )
    
    # Add alternative unit columns for easier interpretation
    sites_with_layers['Pollution_Flux_mg_per_year'] = sites_with_layers['Pollution_Flux_ug_per_year'] / 1000.0
    sites_with_layers['Pollution_Flux_g_per_year'] = sites_with_layers['Pollution_Flux_ug_per_year'] / 1000000.0
    sites_with_layers['Pollution_Flux_kg_per_year'] = sites_with_layers['Pollution_Flux_ug_per_year'] / 1000000000.0
    
    # 7. Save results
    output_path = get_output_path('step4_final_distances_for_risk_assessment').replace('step4_final_distances.csv', 'step6_flux_results.csv')
    sites_with_layers.to_csv(output_path, index=False)
    
    print(f"Calculated flux for {len(sites_with_layers):,} sites")
    print(f"Mean flux: {sites_with_layers['Pollution_Flux_ug_per_year'].mean():.2e} μg/år")
    print(f"Mean flux: {sites_with_layers['Pollution_Flux_kg_per_year'].mean():.2e} kg/år")
    print(f"Results saved to: {output_path}")
    
    # 8. Generate analysis and visualizations
    match_stats = {
        'gvfk_match_rate': sites_with_layers['DK-modellag'].notna().mean() * 100,
        'geometry_match_rate': (sites_with_layers['Area_m2'] != 1000.0).mean() * 100,
        'raster_match_rate': (sites_with_layers['I_Value'] != 0.5).mean() * 100
    }
    
    analyze_and_visualize_step6(sites_with_layers, match_stats)
        
    return sites_with_layers

def _parse_dk_modellag(dk_modellag):
    """Parse DK-modellag entry into list of layers."""
    if pd.isna(dk_modellag):
        return []
    
    dk_modellag = str(dk_modellag).strip()
    
    # Handle range entries like 'ks1 - ks2'
    if ' - ' in dk_modellag:
        start, end = dk_modellag.split(' - ')
        start, end = start.strip(), end.strip()
        
        if start[:2] == end[:2]:  # Same prefix
            prefix = start[:2]
            start_num = int(start[2:]) if start[2:].isdigit() else 0
            end_num = int(end[2:]) if end[2:].isdigit() else 0
            return [f"{prefix}{i}" for i in range(start_num, end_num + 1)]
    
    return [dk_modellag]

def _get_i_value(dk_modellag):
    """Get I value by sampling rasters for DK-modellag."""
    layers = _parse_dk_modellag(dk_modellag)
    
    if not layers:
        return 0.5  # Default
    
    values = []
    for layer in layers:
        raster_path = os.path.join(GVD_RASTER_PATH, f"DKM_gvd_{layer}.tif")
        
        if os.path.exists(raster_path):
            with rasterio.open(raster_path) as src:
                # Sample at raster center for now
                bounds = src.bounds
                x = (bounds.left + bounds.right) / 2
                y = (bounds.bottom + bounds.top) / 2
                
                sampled = list(src.sample([(x, y)]))
                if sampled and sampled[0][0] != src.nodata:
                    values.append(float(sampled[0][0]))
    
    return np.mean(values) if values else 0.5

if __name__ == "__main__":
    run_step6()