"""
Main workflow orchestrator for groundwater contamination analysis.

This script runs the complete analysis workflow:
1. Count all GVFK
2. Identify GVFK with river contact  
3. Find GVFK with V1/V2 sites
4. Calculate distances to rivers
5. Create visualizations

Each step is modularized for easier maintenance and debugging.
"""

import pandas as pd
import os
import warnings
from shapely.errors import ShapelyDeprecationWarning
from config import validate_input_files, get_output_path, print_workflow_settings_summary, validate_workflow_settings

# Import step modules
from step1_all_gvfk import run_step1
from step2_river_contact import run_step2
from step3_v1v2_sites import run_step3
from step5_risk_assessment import run_step5, run_comprehensive_step5

# Suppress shapely deprecation warnings
warnings.filterwarnings("ignore", category=ShapelyDeprecationWarning)

def main():
    """
    Run the complete groundwater analysis workflow.
    """
    print("Groundwater Contamination Analysis Workflow")
    print("=" * 50)
    
    # Validate workflow settings
    is_valid, messages = validate_workflow_settings()
    if not is_valid:
        print("ERROR: Invalid workflow configuration detected:")
        for message in messages:
            if message.startswith("ERROR"):
                print(f"  {message}")
        print("Please fix configuration errors in config.py before proceeding.")
        return False
    
    # Validate input files before starting
    if not validate_input_files():
        print("ERROR: Some required input files are missing. Check file paths in config.py")
        return False
    
    # Initialize results storage
    results = {}
    
    try:
        # Step 1: Count total GVFK
        gvf, total_gvfk = run_step1()
        if gvf is None:
            print("ERROR: Step 1 failed. Cannot proceed.")
            return False
        
        results['step1'] = {'gvf': gvf, 'total_gvfk': total_gvfk}
        
        # Step 2: Count GVFK with river contact
        rivers_gvfk, river_contact_count, gvf_with_rivers = run_step2()
        if not rivers_gvfk:
            print("ERROR: Step 2 failed or found no GVFK with river contact. Cannot proceed.")
            return False
        
        results['step2'] = {
            'rivers_gvfk': rivers_gvfk, 
            'river_contact_count': river_contact_count,
            'gvf_with_rivers': gvf_with_rivers
        }
        
        # Step 3: Count GVFK with river contact and V1/V2 sites
        gvfk_with_v1v2_names, v1v2_sites = run_step3(rivers_gvfk)
        if v1v2_sites.empty:
            print("ERROR: Step 3 failed or found no V1/V2 sites. Cannot proceed to distance calculation.")
            return False
        
        results['step3'] = {
            'gvfk_with_v1v2_names': gvfk_with_v1v2_names,
            'v1v2_sites': v1v2_sites
        }
        
        # Step 4: Calculate distances (import dynamically as it's large)
        try:
            from step4_distances import run_step4
            distance_results = run_step4(v1v2_sites)
            if distance_results is None:
                print("ERROR: Step 4 failed. Distance calculation unsuccessful.")
                return False
            
            results['step4'] = {'distance_results': distance_results}
        
        except ImportError:
            print("WARNING: Step 4 module not found. Creating simplified workflow summary without distances.")
            results['step4'] = {'distance_results': None}
        
        # Step 5: Comprehensive Risk Assessment (General + Compound-Specific + Category Analysis)
        try:
            # Use comprehensive analysis that includes all Step 5 components
            comprehensive_results = run_comprehensive_step5()
            
            if not comprehensive_results['success']:
                print(f"ERROR: Step 5 failed - {comprehensive_results.get('error_message', 'Unknown error')}")
                results['step5'] = {
                    'general_high_risk_sites': None, 
                    'general_analysis': None, 
                    'compound_high_risk_sites': None,
                    'compound_analysis': None,
                    'category_results': None,
                    'high_risk_gvfk_count': 0
                }
            else:
                # Extract data from comprehensive results
                general_results = comprehensive_results['general_results']
                compound_results = comprehensive_results['compound_results']
                category_results = comprehensive_results['category_results']
                
                general_sites, general_analysis = general_results
                compound_sites, compound_analysis = compound_results
                
                # Use general results for backward compatibility in summary statistics
                high_risk_sites = general_sites if general_sites is not None else pd.DataFrame()
                
                # Extract GVFK count from general results for consistency
                high_risk_gvfk_count = 0
                if not high_risk_sites.empty:
                    if 'All_Affected_GVFKs' in high_risk_sites.columns:
                        all_gvfks = set()
                        for gvfk_list in high_risk_sites['All_Affected_GVFKs'].dropna():
                            if pd.isna(gvfk_list) or gvfk_list == '':
                                continue
                            gvfks = [gvfk.strip() for gvfk in str(gvfk_list).split(';') if gvfk.strip()]
                            all_gvfks.update(gvfks)
                        high_risk_gvfk_count = len(all_gvfks)
                    elif 'Closest_GVFK' in high_risk_sites.columns:
                        high_risk_gvfk_count = high_risk_sites['Closest_GVFK'].nunique()
                
                results['step5'] = {
                    'general_high_risk_sites': general_sites,
                    'general_analysis': general_analysis,
                    'compound_high_risk_sites': compound_sites,
                    'compound_analysis': compound_analysis,
                    'category_results': category_results,
                    'high_risk_gvfk_count': high_risk_gvfk_count,
                    'success': True,
                    # Backward compatibility
                    'high_risk_sites': high_risk_sites,
                    'risk_analysis': general_analysis
                }
                
        except ImportError:
            print("WARNING: Step 5 module not found.")
            results['step5'] = {'high_risk_sites': None, 'risk_analysis': None, 'high_risk_gvfk_count': 0}
        
        # Generate workflow summary
        generate_workflow_summary(results)
        
        # Create visualizations if requested
        create_visualizations_if_available(results)
        
        print("\nWorkflow completed successfully!")
        return True
        
    except Exception as e:
        print(f"\nWorkflow failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

def generate_workflow_summary(results):
    """
    Generate and save a comprehensive workflow summary.
    
    Args:
        results (dict): Dictionary containing results from all workflow steps
    """
    print("Generating workflow summary...")
    
    # Extract key statistics
    total_gvfk = results['step1']['total_gvfk']
    river_contact_count = results['step2']['river_contact_count']
    gvfk_with_v1v2_count = len(results['step3']['gvfk_with_v1v2_names'])
    
    # V1/V2 site statistics
    v1v2_sites = results['step3']['v1v2_sites']
    unique_sites = v1v2_sites['Lokalitet_'].nunique() if not v1v2_sites.empty else 0
    total_site_gvfk_combinations = len(v1v2_sites) if not v1v2_sites.empty else 0
    
    # Step 5 statistics
    high_risk_site_count = 0
    compound_high_risk_site_count = 0
    high_risk_gvfk_count = 0
    
    if 'step5' in results:
        # General assessment results
        if results['step5']['general_high_risk_sites'] is not None:
            high_risk_site_count = len(results['step5']['general_high_risk_sites'])
        
        # Compound-specific assessment results
        if results['step5']['compound_high_risk_sites'] is not None:
            compound_high_risk_site_count = len(results['step5']['compound_high_risk_sites'])
        
        # GVFK count (from general assessment for consistency)
        high_risk_gvfk_count = results['step5'].get('high_risk_gvfk_count', 0)
    
    # Distance statistics (if available) - load from corrected final distances file
    distance_stats = {}
    if results['step4']['distance_results'] is not None:
        # Use the corrected final distances file instead of raw results to avoid duplicates
        final_distances_path = get_output_path('step4_final_distances_for_risk_assessment')
        if os.path.exists(final_distances_path):
            try:
                corrected_final_distances = pd.read_csv(final_distances_path)
                
                # Get total combinations from raw results for comparison
                distance_results = results['step4']['distance_results']
                valid_distances = distance_results[distance_results['Distance_to_River_m'].notna()]
                
                distance_stats = {
                    'total_combinations_with_distances': len(valid_distances),
                    'unique_sites_with_distances': len(corrected_final_distances),  # Now uses deduplicated count
                    'average_final_distance_m': corrected_final_distances['Final_Distance_m'].mean(),
                    'median_final_distance_m': corrected_final_distances['Final_Distance_m'].median()
                }
            except Exception as e:
                print(f"Warning: Could not load corrected final distances file: {e}")
                # Fallback to old method with duplicate counting
                final_distances = valid_distances[valid_distances['Is_Min_Distance'] == True]
                distance_stats = {
                    'total_combinations_with_distances': len(valid_distances),
                    'unique_sites_with_distances': len(final_distances),
                    'average_final_distance_m': final_distances['Distance_to_River_m'].mean() if len(final_distances) > 0 else 0,
                    'median_final_distance_m': final_distances['Distance_to_River_m'].median() if len(final_distances) > 0 else 0
                }
    
    # Print summary to console
    print("WORKFLOW SUMMARY")
    print("=" * 60)
    print(f"Total unique groundwater aquifers (GVFK): {total_gvfk}")
    print(f"GVFKs in contact with targeted rivers: {river_contact_count} ({(river_contact_count/total_gvfk*100):.1f}%)")
    print(f"GVFKs with river contact AND V1/V2 sites: {gvfk_with_v1v2_count} ({(gvfk_with_v1v2_count/total_gvfk*100):.1f}%)")
    print(f"GVFKs with high-risk sites (≤500m from rivers): {high_risk_gvfk_count} ({(high_risk_gvfk_count/total_gvfk*100):.1f}% of total, {(high_risk_gvfk_count/gvfk_with_v1v2_count*100 if gvfk_with_v1v2_count > 0 else 0):.1f}% of V1/V2 GVFKs)")
    
    if unique_sites > 0:
        print(f"Unique V1/V2 sites (localities): {unique_sites}")
        print(f"Total site-GVFK combinations: {total_site_gvfk_combinations}")
        print(f"Average GVFKs per site: {total_site_gvfk_combinations/unique_sites:.1f}")
    
    if distance_stats:
        print(f"Site-GVFK combinations with distances: {distance_stats['total_combinations_with_distances']}")
        print(f"Unique sites with final distances: {distance_stats['unique_sites_with_distances']}")
        print(f"Average final distance per site: {distance_stats['average_final_distance_m']:.1f}m")
        print(f"Median final distance per site: {distance_stats['median_final_distance_m']:.1f}m")
    
    if high_risk_site_count > 0:
        print(f"High-risk sites - General assessment (≤500m): {high_risk_site_count} ({(high_risk_site_count/unique_sites*100 if unique_sites > 0 else 0):.1f}% of sites)")
    
    if compound_high_risk_site_count > 0:
        print(f"High-risk sites - Compound-specific assessment: {compound_high_risk_site_count} ({(compound_high_risk_site_count/unique_sites*100 if unique_sites > 0 else 0):.1f}% of sites)")
    
    # Report category analysis results if available
    if 'step5' in results and results['step5'].get('category_results') is not None:
        print(f"Category-based analysis: Completed with professional visualizations")
    
    if high_risk_site_count == 0 and compound_high_risk_site_count == 0:
        print("Step 5 risk assessment: Not completed successfully")
    
    # Create summary DataFrame
    summary_data = {
        'Step': [
            'Step 1: All GVFKs',
            'Step 2: GVFKs with River Contact',
            'Step 3: GVFKs with River Contact and V1/V2 Sites',
            'Step 3: Unique V1/V2 Sites (Localities)',
            'Step 3: Total Site-GVFK Combinations',
            'Step 5: GVFKs with High-Risk Sites (≤500m)',
            'Step 5: High-Risk Sites - General Assessment (≤500m)',
            'Step 5: High-Risk Sites - Compound-Specific Assessment'
        ],
        'Count': [
            total_gvfk,
            river_contact_count,
            gvfk_with_v1v2_count,
            unique_sites,
            total_site_gvfk_combinations,
            high_risk_gvfk_count,
            high_risk_site_count,
            compound_high_risk_site_count
        ],
        'Percentage_of_Total_GVFKs': [
            '100.0%',
            f"{(river_contact_count/total_gvfk*100):.1f}%",
            f"{(gvfk_with_v1v2_count/total_gvfk*100):.1f}%",
            'N/A (Site-level)',
            'N/A (Combination-level)',
            f"{(high_risk_gvfk_count/total_gvfk*100):.1f}%",
            f"{(high_risk_site_count/unique_sites*100 if unique_sites > 0 else 0):.1f}% of sites",
            f"{(compound_high_risk_site_count/unique_sites*100 if unique_sites > 0 else 0):.1f}% of sites"
        ]
    }
    
    # Add distance statistics if available
    if distance_stats:
        summary_data['Step'].extend([
            'Step 4: Site-GVFK Combinations with Distances',
            'Step 4: Unique Sites with Final Distances',
            'Step 4: Average Final Distance per Site (m)'
        ])
        summary_data['Count'].extend([
            distance_stats['total_combinations_with_distances'],
            distance_stats['unique_sites_with_distances'],
            f"{distance_stats['average_final_distance_m']:.1f}"
        ])
        summary_data['Percentage_of_Total_GVFKs'].extend([
            'N/A (Combination-level)',
            'N/A (Site-level)',
            'N/A (Distance metric)'
        ])
    
    # Save summary
    workflow_summary = pd.DataFrame(summary_data)
    summary_path = get_output_path('workflow_summary')
    workflow_summary.to_csv(summary_path, index=False)
    print(f"Summary saved to: {summary_path}")

def create_visualizations_if_available(results):
    """
    Create visualizations if the selected_visualizations module is available.
    
    Args:
        results (dict): Dictionary containing results from all workflow steps
    """
    print("Creating visualizations...")
    
    try:
        # Try to import and run selected visualizations
        from selected_visualizations import create_site_density_heatmap, create_distance_histogram_with_thresholds, create_progression_plot
        
        results_path = "Resultater"
        
        # Create density heatmap
        try:
            create_site_density_heatmap(results_path)
        except Exception as e:
            print(f"WARNING: Could not create density heatmap - {e}")
        
        # Create distance histogram if distance data is available
        if results['step4']['distance_results'] is not None:
            try:
                create_distance_histogram_with_thresholds(results_path)
            except Exception as e:
                print(f"WARNING: Could not create distance histogram - {e}")
        
        # Create GVFK progression plot
        try:
            import os
            from config import GRUNDVAND_PATH
            # Define required files for progression plot including Step 5
            required_files = {
                "all_gvfk": GRUNDVAND_PATH,  # Use original file since Step 1 no longer creates output
                "river_gvfk": os.path.join(results_path, "step2_gvfk_with_rivers.shp"),
                "v1v2_gvfk": os.path.join(results_path, "step3_gvfk_with_v1v2.shp"),
                "high_risk_gvfk": os.path.join(results_path, "step5_gvfk_high_risk_500m.shp")
            }
            figures_path = os.path.join(results_path, "Figures")
            os.makedirs(figures_path, exist_ok=True)
            create_progression_plot(figures_path, required_files)
        except Exception as e:
            print(f"WARNING: Could not create progression plot - {e}")
        
    except ImportError:
        print("WARNING: Selected visualizations module not found. Skipping visualization creation.")
        print("To create visualizations, run 'python selected_visualizations.py' manually.")
    
    # Create Step 5 visualizations if high-risk sites are available
    step5_has_results = False
    if 'step5' in results:
        general_sites = results['step5'].get('general_high_risk_sites')
        compound_sites = results['step5'].get('compound_high_risk_sites')
        if (general_sites is not None and not general_sites.empty) or (compound_sites is not None and not compound_sites.empty):
            step5_has_results = True
    
    if step5_has_results:
        try:
            from step5_visualizations import create_step5_visualizations
            create_step5_visualizations()
        except ImportError:
            print("WARNING: Step 5 visualization module not found.")
        except Exception as e:
            print(f"WARNING: Could not create Step 5 visualizations - {e}")

if __name__ == "__main__":
    success = main()
    if success:
        print("Check the 'Resultater' directory for output files.")
    else:
        print("Workflow failed. Check error messages above.") 